from pathlib import Path
import base64
from functools import lru_cache
import hashlib
import hmac
import json
import logging
import math
import os
import time
import copy
from typing import Annotated
from uuid import uuid4

from fastapi import FastAPI, Query, Request, Response
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from .auditoria import list_auditoria, record_auditoria
from .motor360_auditoria import audit_to_markdown, audit_to_pdf, get_motor360_audit, save_motor360_audit
from .administrator_rules import normalize_admin_name, rules_by_administradora
from .config import get_settings
from .configuracoes import get_configuracoes, update_configuracoes
from .consortium_viability_engine import analyze_client_consortium_viability
from .defasagem import build_defasagem_report, update_defasagem_task
from .estudos import create_estudo, delete_estudo, export_estudo_pdf, get_estudo, list_estudos
from .models import EstudoCreateResponse, EstudoRequest, EstudosResponse, GrupoCreateRequest, GrupoCreateResponse, GrupoDetalhe, GrupoUpdateRequest, GruposResponse, HistoricoBatchUpdateRequest, HistoricoUpdateRequest, SuccessResponse, ViabilidadeRequest
from .sheets_client import clear_rows_cache, create_grupo, delete_grupo, export_sheet_csv, get_cached_grupos_defasagem, get_grupo, list_grupos, list_grupos_detalhe, list_grupos_detalhe_by_ids, update_grupo, update_historico_mensal, update_historico_mensal_lote, warm_grupos_defasagem_cache_async

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
FILES_DIR = BASE_DIR / "generated_files"
DATA_DIR = BASE_DIR / "data"
FILES_DIR.mkdir(exist_ok=True)
logger = logging.getLogger("crediclass.api")

app = FastAPI(title="Crediclass Dashboard V3")


@lru_cache(maxsize=1)
def _assembly_calendar_payload() -> dict:
    """Carrega o calendario uma vez por processo para manter a tela responsiva."""
    source = DATA_DIR / "assembly_calendar_2026.json"
    if not source.exists():
        raise FileNotFoundError(source)
    payload = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(payload.get("schedules"), list) or not isinstance(payload.get("rules"), list):
        raise ValueError("Estrutura do calendario de assembleias invalida.")
    enriched_payload = copy.deepcopy(payload)
    try:
        groups = list_grupos(include_history=False)
        due_dates_by_administrator: dict[str, list[int]] = {}
        for group in groups:
            administrator = str(group.get("administradora") or "").strip()
            due_date = str(group.get("vencimento_parcela") or "").strip()
            if not administrator or not due_date.isdigit():
                continue
            due_dates_by_administrator.setdefault(administrator, [])
            value = int(due_date)
            if value not in due_dates_by_administrator[administrator]:
                due_dates_by_administrator[administrator].append(value)
        for administrator, values in due_dates_by_administrator.items():
            values.sort()
        schedules_by_administrator: dict[str, list[dict]] = {}
        for schedule in enriched_payload.get("schedules", []):
            administrator = str(schedule.get("administrator") or "").strip()
            if not administrator:
                continue
            schedules_by_administrator.setdefault(administrator, []).append(schedule)
        for administrator, schedules in schedules_by_administrator.items():
            due_dates = due_dates_by_administrator.get(administrator, [])
            if not due_dates:
                continue
            ordered_schedules = sorted(
                schedules,
                key=lambda item: (
                    int(item.get("faixa") or 0),
                    int(item.get("source_row") or 0),
                ),
            )
            for schedule, due_date in zip(ordered_schedules, due_dates):
                for month in schedule.get("months", []):
                    for event in month.get("events", []):
                        if event.get("id") != "vencimento_parcela":
                            continue
                        event["display"] = str(due_date)
                        event["value"] = due_date
    except Exception:
        logger.exception("Nao foi possivel enriquecer vencimentos do Mapa Assembleia com a base de grupos.")
    return enriched_payload


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


@app.middleware("http")
async def prevent_stale_frontend_assets(request: Request, call_next):
    response = await call_next(request)
    if request.url.path == "/" or request.url.path == "/index.html" or request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


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


@app.get("/api/mapa-assembleia")
def mapa_assembleia():
    """Retorna o calendario importado e versionado, sem consultar fonte externa."""
    try:
        return _assembly_calendar_payload()
    except (FileNotFoundError, json.JSONDecodeError, ValueError):
        logger.exception("Falha ao carregar o calendario de assembleias")
        return JSONResponse(status_code=503, content={"success": False, "error": "Calendario de assembleias indisponivel."})


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


@app.post("/api/viabilidade-360/analisar")
def viabilidade_360_analisar(payload: ViabilidadeRequest):
    """Single entry point: declared objective is a presentation preference, never an exclusion."""
    request_id = f"REQ-{uuid4().hex[:12].upper()}"
    logger.info("POST /api/viabilidade-360/analisar request_id=%s credito=%s", request_id, payload.credito_desejado)
    try:
        # O histórico completo alimenta o tooltip do Motor 360. A leitura é
        # cacheada pelo cliente da planilha, portanto não há uma nova consulta
        # ao Google Sheets para cada grupo exibido.
        groups = list_grupos(include_history=True)
        result = analyze_client_consortium_viability(payload, groups, mode=payload.base_mode, request_id=request_id)
        audit = save_motor360_audit(result.pop("audit"))
        result["audit_id"] = audit["metadata"]["audit_id"]
        result["request_id"] = request_id
        return result
    except ValueError as error:
        logger.warning("Motor 360 recusou a entrada request_id=%s error=%s", request_id, error)
        return JSONResponse(status_code=422, content={"success": False, "error": str(error), "request_id": request_id})
    except Exception as error:
        logger.exception("Erro no motor 360 de viabilidade request_id=%s", request_id)
        return JSONResponse(status_code=503, content={"success": False, "error": "Falha interna ao calcular o Motor 360.", "request_id": request_id})


@app.get("/api/viabilidade-360/auditorias/{audit_id}")
def viabilidade_360_auditoria(audit_id: str):
    audit = get_motor360_audit(audit_id)
    if audit is None:
        return JSONResponse(status_code=404, content={"success": False, "error": "Auditoria não encontrada."})
    return audit


@app.get("/api/viabilidade-360/auditorias/{audit_id}/exportar.md")
def viabilidade_360_auditoria_markdown(audit_id: str):
    audit = get_motor360_audit(audit_id)
    if audit is None:
        return JSONResponse(status_code=404, content={"success": False, "error": "Auditoria não encontrada."})
    headers = {"Content-Disposition": f'attachment; filename="{audit_id}.md"'}
    return PlainTextResponse(audit_to_markdown(audit), headers=headers)


@app.get("/api/viabilidade-360/auditorias/{audit_id}/exportar.pdf")
def viabilidade_360_auditoria_pdf(audit_id: str):
    audit = get_motor360_audit(audit_id)
    if audit is None:
        return JSONResponse(status_code=404, content={"success": False, "error": "Auditoria não encontrada."})
    headers = {"Content-Disposition": f'attachment; filename="{audit_id}-motor-360.pdf"'}
    return Response(content=audit_to_pdf(audit), media_type="application/pdf", headers=headers)


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
def estudos_criar(payload: EstudoRequest, request: Request):
    logger.info("POST /api/estudos grupo_id=%s", payload.grupo_id)
    try:
        item = get_grupo(payload.grupo_id)
        if not item:
            return JSONResponse(status_code=404, content={"success": False, "error": "Grupo nao encontrado"})
        username = getattr(request.state, "auth_user", "")
        operador = AUTH_USERS.get(username, {}).get("name", username)
        result = create_estudo(payload, item, operador)
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
