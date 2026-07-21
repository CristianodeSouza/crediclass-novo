from pathlib import Path
import base64
import hashlib
import hmac
import logging
import math
import os
import time
from typing import Annotated

from fastapi import FastAPI, Query, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .auditoria import list_auditoria, record_auditoria
from .administrator_feasibility import analyze_administradoras
from .administrator_rules import normalize_admin_name, rules_by_administradora
from .config import get_settings
from .configuracoes import get_configuracoes, update_configuracoes
from .contemplar_engine import analyze_contemplar_groups, is_contemplar_objective
from .defasagem import build_defasagem_report, update_defasagem_task
from .estudos import create_estudo, delete_estudo, export_estudo_pdf, get_estudo, list_estudos
from .investor_engine import analyze_investor_groups, is_investor_objective
from .models import EstudoCreateResponse, EstudoRequest, EstudosResponse, GrupoCreateRequest, GrupoCreateResponse, GrupoDetalhe, GrupoUpdateRequest, GruposResponse, HistoricoBatchUpdateRequest, HistoricoUpdateRequest, SuccessResponse, ViabilidadeRequest, ViabilidadeResponse
from .scenario_builder import analyze_scenarios
from .sheets_client import clear_rows_cache, create_grupo, delete_grupo, export_sheet_csv, get_cached_grupos_defasagem, get_grupo, list_grupos, list_grupos_detalhe, list_grupos_detalhe_by_ids, update_grupo, update_historico_mensal, update_historico_mensal_lote, warm_grupos_defasagem_cache_async
from .viabilidade import analyze_viabilidade, compatible_tipo_bem, normalize_text

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
FILES_DIR = BASE_DIR / "generated_files"
FILES_DIR.mkdir(exist_ok=True)
logger = logging.getLogger("crediclass.api")

app = FastAPI(title="Crediclass Dashboard V3")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/files", StaticFiles(directory=FILES_DIR), name="files")

AUTH_COOKIE = "crediclass_session"
AUTH_USERS = {
    "adm": {"password": "cristiano", "name": "Administrador", "role": "Administrador"},
    "operador1": {"password": "teste123", "name": "Operador 1", "role": "Operador"},
    "operador2": {"password": "teste123", "name": "Operador 2", "role": "Operador"},
}
AUTH_SECRET = os.getenv("AUTH_SECRET", "crediclass-dashboard-v3-local-login")


def _sign_session(username: str, issued_at: int) -> str:
    payload = f"{username}:{issued_at}"
    signature = hmac.new(AUTH_SECRET.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return base64.urlsafe_b64encode(f"{payload}:{signature}".encode("utf-8")).decode("ascii")


def _verify_session(token: str | None) -> str | None:
    if not token:
        return None
    try:
        decoded = base64.urlsafe_b64decode(token.encode("ascii")).decode("utf-8")
        username, issued_at_text, signature = decoded.rsplit(":", 2)
        issued_at = int(issued_at_text)
    except (ValueError, UnicodeDecodeError):
        return None
    if username not in AUTH_USERS:
        return None
    expected = hmac.new(AUTH_SECRET.encode("utf-8"), f"{username}:{issued_at}".encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return None
    if time.time() - issued_at > 60 * 60 * 12:
        return None
    return username


def _public_auth_path(path: str) -> bool:
    return path in {"/api/auth/login", "/api/auth/logout", "/api/auth/me", "/api/health"}


@app.middleware("http")
async def require_authenticated_session(request: Request, call_next):
    path = request.url.path
    if path.startswith("/api/") and not _public_auth_path(path):
        username = _verify_session(request.cookies.get(AUTH_COOKIE))
        if not username:
            return JSONResponse(status_code=401, content={"success": False, "error": "Acesso restrito. Faca login para continuar."})
        request.state.auth_user = username
    if path.startswith("/files/"):
        username = _verify_session(request.cookies.get(AUTH_COOKIE))
        if not username:
            return JSONResponse(status_code=401, content={"success": False, "error": "Acesso restrito. Faca login para continuar."})
    return await call_next(request)


@app.get("/")
def index():
    return FileResponse(
        STATIC_DIR / "index.html",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
        },
    )


@app.get("/api/health")
def health():
    settings = get_settings()
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.version,
        "environment": settings.environment,
    }


@app.post("/api/reload")
def reload_data():
    logger.info("POST /api/reload")
    try:
        clear_rows_cache()
        total = len(list_grupos(include_history=True))
    except Exception as error:
        logger.exception("Erro ao recarregar dados da planilha")
        return JSONResponse(status_code=503, content={"success": False, "error": str(error)})

    logger.info("POST /api/reload recarregou total=%s", total)
    return {"success": True, "total": total}


@app.get("/api/grupos", response_model=GruposResponse)
def grupos(
    administradora: str | None = None,
    tipo_bem: str | None = None,
    status: str | None = None,
    busca: str | None = None,
    credito_minimo: float | None = None,
    credito_maximo: float | None = None,
    prazo_minimo: int | None = None,
    prazo_maximo: int | None = None,
    sort_lance: str | None = None,
    sort_order: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
):
    logger.info("GET /api/grupos page=%s page_size=%s busca=%s", page, page_size, busca)
    try:
        items = list_grupos(include_history=True)
        warm_grupos_defasagem_cache_async()
    except Exception as error:
        logger.exception("Erro ao listar grupos")
        return JSONResponse(status_code=503, content={"success": False, "error": str(error)})

    administradoras = sorted({item["administradora"] for item in items if item["administradora"]})
    tipos_bem = sorted({item["tipo_bem"] for item in items if item["tipo_bem"]})

    if administradora:
        items = [item for item in items if item["administradora"].lower() == administradora.lower()]
    if tipo_bem:
        items = [item for item in items if item["tipo_bem"].lower() == tipo_bem.lower()]
    if status:
        items = [item for item in items if item["status"].lower() == status.lower()]
    if busca:
        needle = busca.lower()
        items = [
            item for item in items
            if needle in item["grupo_id"].lower()
            or needle in item["grupo"].lower()
            or needle in item["administradora"].lower()
        ]
    if credito_minimo is not None:
        items = [item for item in items if item["credito_minimo"] is not None and item["credito_minimo"] >= credito_minimo]
    if credito_maximo is not None:
        items = [item for item in items if item["credito_maximo"] is not None and item["credito_maximo"] <= credito_maximo]
    if prazo_minimo is not None:
        items = [item for item in items if item.get("prazo_restante") is not None and item["prazo_restante"] >= prazo_minimo]
    if prazo_maximo is not None:
        items = [item for item in items if item.get("prazo_restante") is not None and item["prazo_restante"] <= prazo_maximo]

    lance_sort_fields = {
        "agressivo": "lance_agressivo",
        "moderado": "lance_moderado",
        "conservador": "lance_conservador",
        "super_conservador": "lance_super_conservador",
    }
    sort_field = lance_sort_fields.get((sort_lance or "").lower())
    sort_direction = (sort_order or "").lower()
    if sort_field and sort_direction in {"asc", "desc"}:
        missing_rank = math.inf if sort_direction == "asc" else -math.inf
        items = sorted(
            items,
            key=lambda item: item.get(sort_field) if item.get(sort_field) is not None else missing_rank,
            reverse=sort_direction == "desc",
        )

    total = len(items)
    total_administradoras = len({item["administradora"] for item in items if item["administradora"]})
    start = (page - 1) * page_size
    end = start + page_size
    logger.info("GET /api/grupos retornou total=%s page=%s", total, page)
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_administradoras": total_administradoras,
        "administradoras": administradoras,
        "tipos_bem": tipos_bem,
        "items": items[start:end],
    }


@app.get("/api/grupos/exportar-planilha")
def grupos_exportar_planilha():
    logger.info("GET /api/grupos/exportar-planilha")
    try:
        csv_content = export_sheet_csv()
    except Exception as error:
        logger.exception("Erro ao exportar planilha oficial")
        return JSONResponse(status_code=503, content={"success": False, "error": str(error)})

    filename = f"crediclass-planilha-oficial-{time.strftime('%Y-%m-%d')}.csv"
    return Response(
        content="\ufeff" + csv_content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/grupos/defasagem")
def grupos_defasagem():
    logger.info("GET /api/grupos/defasagem")
    try:
        groups = get_cached_grupos_defasagem()
        if groups is None:
            warm_grupos_defasagem_cache_async()
            return {
                "preparando": True,
                "message": "Preparando dados de defasagem. Tente novamente em alguns segundos.",
            }
        report = build_defasagem_report(groups)
    except Exception as error:
        logger.exception("Erro ao calcular defasagem de grupos")
        return JSONResponse(status_code=503, content={"success": False, "error": str(error)})
    return report


@app.put("/api/grupos/defasagem/{grupo_id}")
async def grupos_defasagem_atualizar(grupo_id: str, request: Request):
    logger.info("PUT /api/grupos/defasagem/%s", grupo_id)
    payload = await request.json()
    operador = getattr(request.state, "auth_user", "")
    try:
        task = update_defasagem_task(grupo_id, payload, operador=operador)
    except Exception as error:
        logger.exception("Erro ao atualizar tarefa de defasagem")
        return JSONResponse(status_code=503, content={"success": False, "error": str(error)})
    return {"success": True, "item": task}


@app.get("/api/grupos/{grupo_id}", response_model=GrupoDetalhe)
def grupo_detalhe(grupo_id: str):
    logger.info("GET /api/grupos/%s", grupo_id)
    try:
        item = get_grupo(grupo_id)
    except Exception as error:
        logger.exception("Erro ao obter grupo")
        return JSONResponse(status_code=503, content={"success": False, "error": str(error)})

    if not item:
        return JSONResponse(status_code=404, content={"success": False, "error": "Grupo nao encontrado"})
    item["auditoria"] = list_auditoria(item["grupo_id"])
    return item


@app.post("/api/grupos", response_model=GrupoCreateResponse)
def grupo_criar(payload: GrupoCreateRequest):
    logger.info("POST /api/grupos grupo=%s tipo=%s", payload.grupo, payload.tipo_bem)
    try:
        result = create_grupo(payload.model_dump())
        record_auditoria(result["grupo_id"], "Criacao de grupo", "Grupo criado na Google Sheets", payload.model_dump())
    except Exception as error:
        logger.exception("Erro ao criar grupo")
        return JSONResponse(status_code=503, content={"success": False, "error": str(error)})
    return result


@app.put("/api/grupos/{grupo_id}", response_model=SuccessResponse)
def grupo_atualizar(grupo_id: str, payload: GrupoUpdateRequest):
    logger.info("PUT /api/grupos/%s", grupo_id)
    data = payload.model_dump(exclude_unset=True)
    if not data:
        return JSONResponse(status_code=400, content={"success": False, "error": "Nenhum campo enviado"})
    try:
        result = update_grupo(grupo_id, data)
        record_auditoria(data.get("grupo") or grupo_id, "Atualizacao de grupo", "Grupo atualizado na Google Sheets", data)
        return result
    except KeyError:
        return JSONResponse(status_code=404, content={"success": False, "error": "Grupo nao encontrado"})
    except Exception as error:
        logger.exception("Erro ao atualizar grupo")
        return JSONResponse(status_code=503, content={"success": False, "error": str(error)})


@app.delete("/api/grupos/{grupo_id}")
def grupo_excluir(grupo_id: str):
    logger.info("DELETE /api/grupos/%s", grupo_id)
    try:
        result = delete_grupo(grupo_id)
        record_auditoria(grupo_id, "Exclusao logica", "Status alterado para Excluido", {"status": "Excluido"})
        return result
    except KeyError:
        return JSONResponse(status_code=404, content={"success": False, "error": "Grupo nao encontrado"})
    except Exception as error:
        logger.exception("Erro ao excluir grupo")
        return JSONResponse(status_code=503, content={"success": False, "error": str(error)})


@app.put("/api/grupos/{grupo_id}/historico", response_model=SuccessResponse)
def grupo_historico_atualizar(grupo_id: str, payload: HistoricoUpdateRequest):
    logger.info("PUT /api/grupos/%s/historico mes=%s", grupo_id, payload.mes)
    data = payload.model_dump(exclude_unset=True)
    try:
        result = update_historico_mensal(grupo_id, data)
        record_auditoria(grupo_id, "Atualizacao de historico", f"Historico mensal atualizado: {payload.mes}", data)
        return result
    except KeyError:
        return JSONResponse(status_code=404, content={"success": False, "error": "Grupo nao encontrado"})
    except Exception as error:
        logger.exception("Erro ao atualizar historico mensal")
        return JSONResponse(status_code=503, content={"success": False, "error": str(error)})


@app.put("/api/grupos/{grupo_id}/historico/lote", response_model=SuccessResponse)
def grupo_historico_lote_atualizar(grupo_id: str, payload: HistoricoBatchUpdateRequest):
    logger.info("PUT /api/grupos/%s/historico/lote total=%s", grupo_id, len(payload.items))
    try:
        items = [item.model_dump(exclude_unset=True) for item in payload.items]
        update_historico_mensal_lote(grupo_id, items)
        meses = [item.mes for item in payload.items]
        record_auditoria(grupo_id, "Atualizacao de historico", f"Historico mensal atualizado em lote: {', '.join(meses)}", {"items": [item.model_dump(exclude_unset=True) for item in payload.items]})
        return {"success": True}
    except KeyError:
        return JSONResponse(status_code=404, content={"success": False, "error": "Grupo nao encontrado"})
    except Exception as error:
        logger.exception("Erro ao atualizar historico mensal em lote")
        return JSONResponse(status_code=503, content={"success": False, "error": str(error)})


@app.post("/api/viabilidade/analisar", response_model=ViabilidadeResponse)
def viabilidade_analisar(payload: ViabilidadeRequest):
    logger.info(
        "POST /api/viabilidade/analisar credito=%s prazo=%s",
        payload.credito_desejado,
        payload.prazo_desejado,
    )
    try:
        summary_groups = list_grupos(include_history=True)
        config = get_configuracoes()
        administrator_rules = config.get("administradoras_regras") or []
        administradoras = sorted({item["administradora"] for item in summary_groups if item.get("administradora")})
        administradoras_viabilidade = analyze_administradoras(payload, administradoras, administrator_rules)
        administradoras_com_regra = {
            normalize_admin_name(item["administradora"])
            for item in administradoras_viabilidade
        }
        administradoras_elegiveis = {
            normalize_admin_name(item["administradora"])
            for item in administradoras_viabilidade
            if item["elegivel"]
        }
        administradoras_sem_regra = {
            normalize_admin_name(administradora)
            for administradora in administradoras
            if normalize_admin_name(administradora) not in administradoras_com_regra
        }
        modo_preliminar = bool(administradoras_sem_regra)
        administradoras_para_busca = administradoras_elegiveis | administradoras_sem_regra
        candidate_ids = [
            item["grupo_id"]
            for item in summary_groups
            if normalize_admin_name(item.get("administradora", "")) in administradoras_para_busca
            and (item.get("credito_maximo") or 0) >= payload.credito_desejado
            and normalize_text(str(item.get("status") or "")) == "ativo"
            and compatible_tipo_bem(payload.objetivo, str(item.get("tipo_bem") or ""), payload.tipo_bem)
        ]
        groups = list_grupos_detalhe_by_ids(candidate_ids) if candidate_ids else []
        rules_map = rules_by_administradora(administrator_rules)
        for group in groups:
            rule = rules_map.get(normalize_admin_name(str(group.get("administradora") or "")))
            if rule and rule.idade_maxima is not None and group.get("idade_maxima") is None:
                group["idade_maxima"] = rule.idade_maxima
        result = analyze_viabilidade(payload, groups, modo_preliminar=modo_preliminar)
        result["total_grupos_analisados"] = len(summary_groups)
        result["total_administradoras_analisadas"] = len(administradoras_viabilidade)
        result["total_administradoras_elegiveis"] = len(administradoras_para_busca)
        result["administradoras_viabilidade"] = administradoras_viabilidade
        if administradoras_sem_regra:
            result["motivos_reprovacao"].append("regras_administradoras_pendentes_analise_humana")
    except Exception as error:
        logger.exception("Erro ao analisar viabilidade")
        return JSONResponse(status_code=503, content={"success": False, "error": str(error)})

    logger.info(
        "POST /api/viabilidade/analisar retornou total=%s perfil=%s",
        result["total_grupos_encontrados"],
        result["perfil"],
    )
    return result


@app.post("/api/viabilidade/administradoras")
def viabilidade_administradoras(payload: ViabilidadeRequest):
    logger.info(
        "POST /api/viabilidade/administradoras credito=%s prazo=%s",
        payload.credito_desejado,
        payload.prazo_desejado,
    )
    try:
        summary_groups = list_grupos(include_history=False)
        config = get_configuracoes()
        administrator_rules = config.get("administradoras_regras") or []
        administradoras = sorted({item["administradora"] for item in summary_groups if item.get("administradora")})
        items = analyze_administradoras(payload, administradoras, administrator_rules)
    except Exception as error:
        logger.exception("Erro ao analisar administradoras")
        return JSONResponse(status_code=503, content={"success": False, "error": str(error)})

    return {
        "total": len(items),
        "total_elegiveis": len([item for item in items if item["elegivel"]]),
        "items": items,
    }


@app.post("/api/cenarios/analisar")
def cenarios_analisar(payload: ViabilidadeRequest):
    logger.info(
        "POST /api/cenarios/analisar credito_liquido=%s prazo=%s",
        payload.credito_desejado,
        payload.prazo_desejado,
    )
    try:
        summary_groups = list_grupos(include_history=True)
        config = get_configuracoes()
        administrator_rules = config.get("administradoras_regras") or []
        administradoras = sorted({item["administradora"] for item in summary_groups if item.get("administradora")})
        administradoras_viabilidade = analyze_administradoras(payload, administradoras, administrator_rules)
        administradoras_com_regra = {
            normalize_admin_name(item["administradora"])
            for item in administradoras_viabilidade
        }
        administradoras_elegiveis = {
            normalize_admin_name(item["administradora"])
            for item in administradoras_viabilidade
            if item["elegivel"]
        }
        administradoras_sem_regra = {
            normalize_admin_name(administradora)
            for administradora in administradoras
            if normalize_admin_name(administradora) not in administradoras_com_regra
        }
        administradoras_para_busca = administradoras_elegiveis | administradoras_sem_regra
        summary_candidates = [
            item
            for item in summary_groups
            if normalize_admin_name(item.get("administradora", "")) == "ITAU"
            and normalize_text(str(item.get("status") or "")) == "ativo"
            and compatible_tipo_bem(payload.objetivo, str(item.get("tipo_bem") or ""), payload.tipo_bem)
        ]
        result = analyze_scenarios(payload, summary_candidates)
        result["total_grupos_base"] = len(summary_groups)
        result["total_administradoras_analisadas"] = len(administradoras_viabilidade)
        result["total_administradoras_elegiveis"] = 1 if summary_candidates else 0
        result["administradoras_viabilidade"] = administradoras_viabilidade
        if administradoras_sem_regra:
            result.setdefault("motivos_reprovacao", []).append("regras_administradoras_pendentes_analise_humana")
    except Exception as error:
        logger.exception("Erro ao montar cenarios")
        return JSONResponse(status_code=503, content={"success": False, "error": str(error)})
    return result


@app.post("/api/investidor/analisar")
def investidor_analisar(payload: ViabilidadeRequest):
    logger.info("POST /api/investidor/analisar credito=%s", payload.credito_desejado)
    if not is_investor_objective(payload.objetivo):
        return {
            "perfil_investidor": False,
            "objetivo": payload.objetivo,
            "items": [],
            "total_grupos_considerados": 0,
            "total_grupos_compativeis": 0,
            "total_grupos_exibidos": 0,
            "mensagem": "O objetivo selecionado pertence ao fluxo de contemplação.",
        }
    try:
        try:
            groups = list_grupos(include_history=False)
        except Exception as light_error:
            logger.warning("Falha na leitura leve do motor investidor; tentando leitura completa: %s", light_error)
            groups = list_grupos(include_history=True)
        return analyze_investor_groups(payload, groups)
    except Exception as error:
        logger.exception("Erro ao analisar grupos do perfil investidor")
        return JSONResponse(status_code=503, content={"success": False, "error": str(error)})


@app.post("/api/contemplar/analisar")
def contemplar_analisar(payload: ViabilidadeRequest):
    logger.info("POST /api/contemplar/analisar credito=%s", payload.credito_desejado)
    if not is_contemplar_objective(payload.objetivo):
        return {
            "perfil_contemplar": False,
            "objetivo": payload.objetivo,
            "items": [],
            "total_grupos_analisados": 0,
            "total_grupos_compativeis": 0,
            "mensagem": "O objetivo selecionado pertence ao fluxo Investidor.",
        }
    try:
        try:
            groups = list_grupos(include_history=False)
        except Exception as light_error:
            logger.warning("Falha na leitura leve do motor contemplar; tentando leitura completa: %s", light_error)
            groups = list_grupos(include_history=True)
        return analyze_contemplar_groups(payload, groups)
    except ValueError as error:
        return JSONResponse(status_code=422, content={"success": False, "error": str(error)})
    except Exception as error:
        logger.exception("Erro ao analisar grupos do perfil contemplar")
        return JSONResponse(status_code=503, content={"success": False, "error": str(error)})


@app.post("/api/auth/login")
async def auth_login(request: Request, response: Response):
    payload = await request.json()
    username = str(payload.get("usuario") or "").strip()
    password = str(payload.get("senha") or "")
    user = AUTH_USERS.get(username)
    if not user or not hmac.compare_digest(password, user["password"]):
        return JSONResponse(status_code=401, content={"success": False, "error": "Usuario ou senha invalidos."})
    token = _sign_session(username, int(time.time()))
    response.set_cookie(
        AUTH_COOKIE,
        token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 12,
        path="/",
    )
    return {
        "success": True,
        "user": {"usuario": username, "nome": user["name"], "perfil": user["role"]},
    }


@app.post("/api/auth/logout")
def auth_logout(response: Response):
    response.delete_cookie(AUTH_COOKIE, path="/")
    return {"success": True}


@app.get("/api/auth/me")
def auth_me(request: Request):
    username = _verify_session(request.cookies.get(AUTH_COOKIE))
    if not username:
        return JSONResponse(status_code=401, content={"success": False, "error": "Sessao nao autenticada."})
    user = AUTH_USERS[username]
    return {
        "success": True,
        "user": {"usuario": username, "nome": user["name"], "perfil": user["role"]},
    }


@app.post("/api/estudos", response_model=EstudoCreateResponse)
def estudos_criar(payload: EstudoRequest):
    logger.info("POST /api/estudos grupo_id=%s", payload.grupo_id)
    try:
        item = get_grupo(payload.grupo_id)
        if not item:
            return JSONResponse(status_code=404, content={"success": False, "error": "Grupo nao encontrado"})
        result = create_estudo(payload, item)
    except Exception as error:
        logger.exception("Erro ao criar estudo")
        return JSONResponse(status_code=503, content={"success": False, "error": str(error)})

    logger.info("POST /api/estudos criou estudo_id=%s", result["estudo_id"])
    return result


@app.get("/api/estudos", response_model=EstudosResponse)
def estudos_listar(
    cliente: str | None = None,
    grupo: str | None = None,
    administradora: str | None = None,
    tipo_bem: str | None = None,
    status: str | None = None,
    operador: str | None = None,
    estrategia: str | None = None,
    data_inicio: str | None = None,
    data_fim: str | None = None,
    credito_minimo: float | None = None,
    credito_maximo: float | None = None,
):
    logger.info("GET /api/estudos cliente=%s grupo=%s status=%s", cliente, grupo, status)
    items = list_estudos()

    if cliente:
        needle = cliente.lower()
        items = [item for item in items if needle in str(item.get("cliente", {}).get("nome", "")).lower()]
    if grupo:
        needle = grupo.lower()
        items = [item for item in items if needle in str(item.get("grupo_id", "")).lower()]
    if administradora:
        needle = administradora.lower()
        items = [item for item in items if needle in str(item.get("grupo", {}).get("administradora", "")).lower()]
    if tipo_bem:
        needle = tipo_bem.lower()
        items = [item for item in items if needle in str(item.get("grupo", {}).get("tipo_bem", "")).lower()]
    if status:
        items = [item for item in items if str(item.get("status", "")).lower() == status.lower()]
    if operador:
        items = [item for item in items if str(item.get("operador", "")).lower() == operador.lower()]
    if estrategia:
        items = [item for item in items if str(item.get("estrategia", "")).lower() == estrategia.lower()]
    if data_inicio:
        items = [item for item in items if str(item.get("criado_em", ""))[:10] >= data_inicio]
    if data_fim:
        items = [item for item in items if str(item.get("criado_em", ""))[:10] <= data_fim]
    if credito_minimo is not None:
        items = [
            item for item in items
            if float(item.get("cliente", {}).get("credito_desejado") or item.get("financeiro", {}).get("credito") or 0) >= credito_minimo
        ]
    if credito_maximo is not None:
        items = [
            item for item in items
            if float(item.get("cliente", {}).get("credito_desejado") or item.get("financeiro", {}).get("credito") or 0) <= credito_maximo
        ]

    return {"total": len(items), "items": items}


@app.get("/api/estudos/{estudo_id}")
def estudos_obter(estudo_id: str):
    logger.info("GET /api/estudos/%s", estudo_id)
    item = get_estudo(estudo_id)
    if not item:
        return JSONResponse(status_code=404, content={"success": False, "error": "Estudo nao encontrado"})
    return item


@app.delete("/api/estudos/{estudo_id}")
def estudos_excluir(estudo_id: str):
    logger.info("DELETE /api/estudos/%s", estudo_id)
    if not delete_estudo(estudo_id):
        return JSONResponse(status_code=404, content={"success": False, "error": "Estudo nao encontrado"})
    return {"success": True}


@app.post("/api/estudos/{estudo_id}/exportar-pdf")
def estudos_exportar_pdf(estudo_id: str):
    logger.info("POST /api/estudos/%s/exportar-pdf", estudo_id)
    filename = export_estudo_pdf(estudo_id, FILES_DIR)
    if not filename:
        return JSONResponse(status_code=404, content={"success": False, "error": "Estudo nao encontrado"})
    return {"success": True, "download_url": f"/files/{filename}"}


@app.get("/api/configuracoes")
def configuracoes_obter():
    logger.info("GET /api/configuracoes")
    settings = get_settings()
    data = get_configuracoes()
    data["sistema"] = {
        "app": settings.app_name,
        "version": settings.version,
        "environment": settings.environment,
        "debug": settings.debug,
        "google_sheet_name": settings.google_sheet_name,
        "google_sheets_configurado": bool(settings.google_sheets_id and settings.google_service_account_json),
    }
    return data


@app.put("/api/configuracoes")
def configuracoes_salvar(payload: dict):
    logger.info("PUT /api/configuracoes")
    try:
        return update_configuracoes(payload)
    except Exception as error:
        logger.exception("Erro ao salvar configuracoes")
        return JSONResponse(status_code=400, content={"success": False, "error": str(error)})
