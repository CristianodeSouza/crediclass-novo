from pathlib import Path
import platform
import sys
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
from html import escape as html_escape
from threading import Lock
from typing import Annotated
from uuid import uuid4

from fastapi import FastAPI, Query, Request, Response
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from .auditoria import list_auditoria, record_auditoria
from .motor360_auditoria import audit_to_markdown, audit_to_pdf, get_motor360_audit, save_motor360_audit
from .administrator_rules import normalize_admin_name, rules_by_administradora
from .config import get_settings
from .configuracoes import get_configuracoes, update_configuracoes
from .templates_estudos import get_template, list_templates
from .consortium_viability_engine import analyze_client_consortium_viability
from .defasagem import build_defasagem_report, update_defasagem_task
from .estudos import build_estudo_audit_payload, build_estudo_preview, clear_all_estudos, create_estudo, delete_estudo, export_estudo_pdf, get_estudo, list_estudos, normalize_editor_content, restore_estudo_editor, update_estudo_editor
from .pdf_bridge import build_react_pdf_payload, react_pdf_service_status, render_react_study_pdf
from .piperun import fetch_opportunities_preview, fetch_opportunity_notes
from .models import EstudoCreateResponse, EstudoPreviewRequest, EstudoRequest, EstudosResponse, GrupoCreateRequest, GrupoCreateResponse, GrupoDetalhe, GrupoUpdateRequest, GruposResponse, HistoricoBatchUpdateRequest, HistoricoUpdateRequest, SuccessResponse, ViabilidadeRequest
from .sheets_client import clear_rows_cache, create_grupo, delete_grupo, export_sheet_csv, get_cached_grupos_defasagem, get_grupo, list_grupos, list_grupos_detalhe, list_grupos_detalhe_by_ids, update_grupo, update_historico_mensal, update_historico_mensal_lote, warm_grupos_defasagem_cache_async

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
FILES_DIR = BASE_DIR / "generated_files"
DATA_DIR = BASE_DIR / "data"
ITAU_TEMPLATE_PATH = BASE_DIR / "templates" / "itau-estudo-financeiro.html"
FILES_DIR.mkdir(exist_ok=True)
logger = logging.getLogger("crediclass.api")
PDF_RENDER_LOCK = Lock()

app = FastAPI(title="Crediclass Dashboard V3")
PIPERUN_EXECUTIONS: set[str] = set()


@app.get("/api/piperun/{opportunity_id}")
async def buscar_oportunidade_piperun(opportunity_id: str):
    try:
        return await fetch_opportunity_notes(opportunity_id)
    except ValueError as error:
        return JSONResponse(status_code=422, content={"success": False, "error": str(error)})
    except LookupError as error:
        return JSONResponse(status_code=404, content={"success": False, "error": str(error)})
    except RuntimeError as error:
        return JSONResponse(status_code=502, content={"success": False, "error": str(error)})
    except Exception as error:
        logger.exception("Falha ao importar oportunidade PipeRun %s", opportunity_id)
        return JSONResponse(status_code=502, content={"success": False, "error": str(error)})


@app.get("/api/piperun-preview")
async def preview_oportunidades_piperun(limit: int = Query(default=25, ge=1, le=50)):
    """MVP: leitura temporária de oportunidades e notas, sem escrita no PipeRun."""
    try:
        return {"success": True, "temporary": True, "items": await fetch_opportunities_preview(limit)}
    except Exception as error:
        logger.exception("Falha ao carregar preview PipeRun")
        return JSONResponse(status_code=502, content={"success": False, "error": str(error)})


@app.post("/api/piperun/{opportunity_id}/sync-plan")
async def gerar_plano_sincronizacao_piperun(opportunity_id: str):
    """Gera um plano de alterações sem executar escritas no PipeRun."""
    try:
        preview = await fetch_opportunity_notes(opportunity_id)
        dados = preview.get("dados") or {}
        credito = float(dados.get("credito_desejado") or 0)
        required = {"nome": "Nome do titular", "credito_desejado": "Crédito desejado"}
        missing = [label for key, label in required.items() if not dados.get(key)]
        steps = [
            {"order": 1, "name": "Atualizar responsável", "method": "PUT", "endpoint": f"/v1/deals/{opportunity_id}", "payload": {"owner_id": 2609 if credito >= 1000000 else 2602}, "status": "simulação"},
            {"order": 2, "name": "Atualizar cliente principal", "method": "PUT", "endpoint": "/v1/persons/{person_id}", "payload": {"name": dados.get("nome"), "cpf": dados.get("cpf"), "contactEmails": [dados.get("email")], "contactPhones": [dados.get("celular")]}, "status": "simulação"},
            {"order": 3, "name": "Localizar ou criar empresa parceira", "method": "GET/POST", "endpoint": "/v1/companies?cnpj={cnpj}", "payload": {"cnpj": dados.get("cnpj_parceiro")}, "status": "simulação"},
            {"order": 4, "name": "Localizar ou criar contatos relacionados", "method": "GET/POST", "endpoint": "/v1/persons", "payload": {"tipos": ["assessor", "gestor", "apoio"]}, "status": "simulação"},
            {"order": 5, "name": "Vincular contatos à oportunidade", "method": "PUT", "endpoint": f"/v1/deals/{opportunity_id}/persons/{{person_id}}", "payload": {}, "status": "simulação"},
            {"order": 6, "name": "Mover oportunidade para etapa destino", "method": "PUT", "endpoint": f"/v1/deals/{opportunity_id}", "payload": {"stage_id": 262860}, "status": "simulação"},
        ]
        return {"success": True, "simulation": True, "can_execute": not missing, "missing_fields": missing, "opportunity_id": opportunity_id, "extraction": preview, "steps": steps}
    except Exception as error:
        logger.exception("Falha ao gerar plano PipeRun %s", opportunity_id)
        return JSONResponse(status_code=502, content={"success": False, "error": str(error)})

@app.post("/api/piperun/{opportunity_id}/sync")
async def executar_sincronizacao_piperun(opportunity_id: str, confirm: bool = Query(default=False)):
    if not confirm:
        return JSONResponse(status_code=400, content={"success": False, "error": "Confirmação obrigatória."})
    if opportunity_id in PIPERUN_EXECUTIONS:
        return JSONResponse(status_code=409, content={"success": False, "error": "Esta oportunidade já foi executada nesta sessão."})
    PIPERUN_EXECUTIONS.add(opportunity_id)
    return {"success": True, "controlled": True, "opportunity_id": opportunity_id, "message": "Executor controlado preparado. WhatsApp e Toggl permanecem desativados."}


class ReleaseStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope: dict):
        response = await super().get_response(path, scope)
        if path.endswith((".js", ".css", ".html")):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        return response



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
        group_due_dates: dict[str, dict[str, int]] = {}
        for group in groups:
            administrator = str(group.get("administradora") or "").strip()
            group_id = str(group.get("grupo") or group.get("grupo_id") or "").strip()
            due_date = str(group.get("vencimento_parcela") or "").strip()
            if not administrator or not due_date.isdigit():
                continue
            due_dates_by_administrator.setdefault(administrator, [])
            value = int(due_date)
            if value not in due_dates_by_administrator[administrator]:
                due_dates_by_administrator[administrator].append(value)
            if group_id:
                group_due_dates.setdefault(administrator, {})[group_id] = value
        for administrator, values in due_dates_by_administrator.items():
            values.sort()
        enriched_payload["group_due_dates"] = group_due_dates
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


app.mount("/static", ReleaseStaticFiles(directory=STATIC_DIR), name="static")
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
    return path in {"/api/auth/login", "/api/auth/logout", "/api/auth/me", "/api/health", "/api/health/pdf-engine"} or path.startswith("/api/public-estudos/")


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


@app.middleware("http")
async def public_study_mobile_layout(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/estudo/") and response.headers.get("content-type", "").startswith("text/html"):
        body = b""
        async for chunk in response.body_iterator:
            body += chunk
        mobile_css = b"""
<style id="crediclass-public-mobile">
@media (max-width:700px) {
  html,body { overflow-x:hidden !important; }
  main { width:100% !important; margin:0 !important; box-shadow:none !important; }
  header { padding:18px 12px !important; }
  header h1 { font-size:22px !important; }
  .meta { grid-template-columns:repeat(2,minmax(0,1fr)) !important; gap:8px !important; font-size:11px !important; }
  section { margin:10px 6px !important; }
  section h2 { padding:8px 10px !important; font-size:13px !important; }
  .content { padding:10px !important; }
  .cards { grid-template-columns:1fr !important; gap:6px !important; }
  .table-wrap { overflow:visible !important; }
  table, thead, tbody, tbody tr, tbody td { display:block !important; width:100% !important; }
  thead { display:none !important; }
  tbody tr { display:grid !important; grid-template-columns:1fr 1fr !important; gap:0 8px !important; padding:6px 0 !important; }
  tbody td { display:flex !important; justify-content:space-between !important; gap:6px !important; padding:6px 3px !important; white-space:normal !important; overflow-wrap:anywhere !important; text-align:right !important; font-size:11px !important; }
  tbody td::before { content:attr(data-label); color:#68787b; font-weight:700; text-align:left; }
  tbody td:first-child { grid-column:1 / -1; text-align:left !important; font-weight:700; }
  tbody td:first-child::before { display:none; }
  footer { padding:12px !important; font-size:10px !important; }
}
@media (max-width:380px) { .meta { grid-template-columns:1fr !important; } }
</style>
"""
        body = body.replace(b"</head>", mobile_css + b"</head>", 1)
        headers = dict(response.headers)
        headers.pop("content-length", None)
        return Response(content=body, status_code=response.status_code, headers=headers, media_type="text/html")
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


def _react_pdf_status_or_error() -> dict:
    status = react_pdf_service_status()
    if not status["available"]:
        raise RuntimeError("React-pdf indisponivel neste ambiente. O motor PDF canonico nao esta operacional.")
    return status


def _render_study_pdf_file(estudo: dict, filename: str) -> dict:
    # O renderer React-PDF inicia um processo Node. Serializar esse trecho
    # evita que cliques, abas ou operadores diferentes derrubem a instância.
    with PDF_RENDER_LOCK:
        status = _react_pdf_status_or_error()
        path = FILES_DIR / filename
        path.write_bytes(render_react_study_pdf(estudo, get_settings().version))
    return {
        "success": True,
        "download_url": f"/files/{filename}",
        "engine": "react-pdf",
        "engine_status": status,
        "filename": filename,
    }


@app.get("/api/estudos/{estudo_id}/pdf")
def estudos_pdf_estavel(estudo_id: str):
    """Regenera o PDF sob demanda; não depende do disco efêmero do Render."""
    estudo = get_estudo(estudo_id)
    if not estudo:
        return JSONResponse(status_code=404, content={"success": False, "error": "Estudo nao encontrado"})
    try:
        version = int(estudo.get("final_pdf_version") or estudo.get("editor_version") or 1)
        rendered = _render_study_pdf_file(estudo, f"{estudo_id}-final-v{version}.pdf")
        return FileResponse(FILES_DIR / rendered["filename"], media_type="application/pdf", filename=rendered["filename"])
    except Exception as error:
        logger.exception("Falha ao regenerar PDF do estudo %s", estudo_id)
        return JSONResponse(status_code=503, content={"success": False, "error": str(error)})


def _write_preview_audit(payload: EstudoPreviewRequest, estudo: dict, rendered: dict, operador: str) -> dict:
    filename = str(rendered["filename"])
    pdf_path = FILES_DIR / filename
    audit = build_estudo_audit_payload(
        payload,
        grupo=estudo["grupo"],
        operador=operador,
        motor360_audit=get_motor360_audit(payload.motor360_audit_id) if payload.motor360_audit_id else None,
        group_audit=list_auditoria(payload.grupo_id),
        pdf_engine_status=rendered["engine_status"],
    )
    audit["pdf_generation"] = {
        "filename": filename,
        "sha256": hashlib.sha256(pdf_path.read_bytes()).hexdigest(),
        "engine": rendered["engine"],
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "renderer_entrypoint": rendered["engine_status"].get("entrypoint"),
    }
    audit_filename = f"audit-{Path(filename).stem}.json"
    (FILES_DIR / audit_filename).write_text(json.dumps(audit, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return {"audit": audit, "audit_url": f"/files/{audit_filename}"}


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
def estudos_criar(payload: EstudoRequest, request: Request = None):
    logger.info("POST /api/estudos grupo_id=%s", payload.grupo_id)
    try:
        item = get_grupo(payload.grupo_id)
        if not item:
            return JSONResponse(status_code=404, content={"success": False, "error": "Grupo nao encontrado"})
        username = getattr(getattr(request, "state", None), "auth_user", "")
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

    for item in items:
        item.setdefault("public_url", f"/estudo/{item.get('estudo_id')}" if item.get("estudo_id") else None)
        item.setdefault("template_version", get_settings().version)
    return {"total": len(items), "items": items}


@app.get("/api/estudos/{estudo_id}")
def estudos_obter(estudo_id: str):
    logger.info("GET /api/estudos/%s", estudo_id)
    item = get_estudo(estudo_id)
    if not item:
        return JSONResponse(status_code=404, content={"success": False, "error": "Estudo nao encontrado"})
    return item


@app.get("/api/public-estudos/{estudo_id}")
def estudo_publico_dados(estudo_id: str):
    """Leitura pública do snapshot publicado, sem expor as APIs administrativas."""
    item = get_estudo(estudo_id)
    if not item:
        return JSONResponse(status_code=404, content={"success": False, "error": "Estudo não encontrado ou link expirado."})
    return {"success": True, "estudo": _public_study_payload(item), "public_url": f"/estudo/{estudo_id}"}


def _public_study_payload(item: dict) -> dict:
    cliente = item.get("cliente") or {}
    public_cliente = {key: cliente.get(key) for key in ("nome", "credito_desejado", "objetivo", "renda_total", "parcela_desejada")}
    public_groups = []
    for group in item.get("grupos_selecionados") or [item.get("grupo") or {}]:
        public_group = {key: group.get(key) for key in ("grupo", "grupo_id", "administradora", "credito_maximo", "prazo_restante")}
        public_group["cenarios"] = [
            {key: scenario.get(key) for key in ("id", "credito_contratado", "parcela_inicial", "parcela_pos_contemplacao", "saldo_devedor")}
            for scenario in (group.get("cenarios") or []) if isinstance(scenario, dict)
        ]
        public_groups.append(public_group)
    return {
        "estudo_id": item.get("estudo_id"),
        "proposal_id": item.get("proposal_id"),
        "criado_em": item.get("criado_em"),
        "cliente": public_cliente,
        "grupo": {key: (item.get("grupo") or {}).get(key) for key in ("administradora", "grupo", "grupo_id")},
        "grupos_selecionados": public_groups,
    }


@app.get("/estudo/{estudo_id}", response_class=HTMLResponse)
def estudo_publico_pagina(estudo_id: str):
    item = get_estudo(estudo_id)
    if not item:
        return HTMLResponse("<h1>Estudo não encontrado</h1><p>Solicite um novo link à Crediclass.</p>", status_code=404)
    cliente = html_escape(str((item.get("cliente") or {}).get("nome") or "Cliente"))
    grupo = item.get("grupo") or {}
    administradora = html_escape(str(grupo.get("administradora") or "Administradora"))
    if administradora.upper().replace("Ú", "U") == "ITAU" and ITAU_TEMPLATE_PATH.exists():
        template = ITAU_TEMPLATE_PATH.read_text(encoding="utf-8")
        template = template.replace("<title>Estudo Financeiro | Aquisição de Imóvel</title>", f"<title>Estudo Financeiro | {cliente}</title>")
        template = template.replace(">Prezado,</text>", f">Prezado, <tspan font-weight=\"700\">{cliente}</tspan></text>", 1)
        return HTMLResponse(template)
    estudo_json = json.dumps(_public_study_payload(item), ensure_ascii=False).replace("</", "<\\/")
    return HTMLResponse(f'''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><meta name="theme-color" content="#2d444c"><title>Estudo Financeiro · {cliente}</title><style>
*{{box-sizing:border-box}}html,body{{width:100%;min-width:0;overflow-x:hidden}}body{{margin:0;background:#f1f3f3;color:#26343a;font:15px Arial,sans-serif}}main{{width:min(1050px,100%);margin:24px auto;background:#fff;box-shadow:0 8px 28px #1e2d3230}}header{{padding:28px 34px;background:#2d444c;color:#fff}}header h1{{margin:10px 0;font-size:28px;line-height:1.15}}header p{{margin:6px 0;color:#dce5e8;overflow-wrap:anywhere}}.meta{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin-top:18px;padding-top:14px;border-top:1px solid #ffffff33}}.meta span{{min-width:0;overflow-wrap:anywhere}}.meta b{{display:block;margin-top:4px;overflow-wrap:anywhere}}section{{margin:18px 28px;border:1px solid #cfd7d8;min-width:0}}section h2{{margin:0;padding:9px 14px;background:#2d444c;color:#fff;font-size:15px;line-height:1.25}}.content{{padding:16px;min-width:0}}.cards{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}}.card{{min-width:0;padding:12px;background:#f6f7f7;border:1px solid #e0e5e5}}.card small{{display:block;color:#68787b}}.card b{{display:block;margin-top:5px;font-size:17px;overflow-wrap:anywhere}}.table-wrap{{width:100%;overflow-x:auto;-webkit-overflow-scrolling:touch}}table{{width:100%;border-collapse:collapse;font-size:13px}}th,td{{padding:9px 7px;border-bottom:1px solid #e0e5e5;text-align:right;white-space:nowrap}}th:first-child,td:first-child{{text-align:left}}th{{background:#ecefef}}footer{{padding:20px 34px;background:#2d444c;color:#fff;font-size:12px;overflow-wrap:anywhere}}@media(max-width:700px){{main{{margin:0;box-shadow:none}}header{{padding:22px 16px}}header h1{{font-size:25px}}.meta{{grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;font-size:13px}}section{{margin:12px 10px}}section h2{{font-size:14px}}.content{{padding:12px}}.cards{{grid-template-columns:1fr}}footer{{padding:16px}}}}@media(max-width:380px){{.meta{{grid-template-columns:1fr}}}}
</style></head><body><main><header><div>CREDICLASS · {administradora}</div><h1>Estudo Financeiro</h1><p>Estudo personalizado para {cliente}</p><div class="meta"><span>Cliente<b>{cliente}</b></span><span>Administradora<b>{administradora}</b></span><span>Gerado em<b>{html_escape(str(item.get("criado_em") or "-"))}</b></span><span>Estudo<b>{html_escape(str(item.get("proposal_id") or item.get("estudo_id")))}</b></span></div></header><div id="app"></div><footer>Informações de caráter informativo e ilustrativo. A decisão pela contratação é de responsabilidade do cliente.</footer></main><script>const study={estudo_json};const money=v=>new Intl.NumberFormat('pt-BR',{{style:'currency',currency:'BRL'}}).format(Number(v||0));const groups=study.grupos_selecionados||[];const rows=groups.map(g=>{{const s=(g.cenarios||[]).find(x=>x.id==='without_embedded')||{{}};return `<tr><td data-label="Grupo">Grupo ${{g.grupo||g.grupo_id||'-'}}</td><td data-label="Crédito máximo">${{money(g.credito_maximo)}}</td><td data-label="Crédito contratado">${{money(s.credito_contratado)}}</td><td data-label="Parcela inicial">${{money(s.parcela_inicial)}}</td><td data-label="Prazo">${{g.prazo_restante||'-'}} meses</td></tr>`}}).join('');const c=study.cliente||{{}};document.getElementById('app').innerHTML=`<section><h2>Simulação de investimento</h2><div class="content cards"><div class="card"><small>Crédito desejado</small><b>${{money(c.credito_desejado)}}</b></div><div class="card"><small>Parcela desejada</small><b>${{money(c.parcela_desejada)}}</b></div><div class="card"><small>Renda total</small><b>${{money(c.renda_total)}}</b></div></div></section><section><h2>Contratação</h2><div class="content table-wrap"><table><thead><tr><th>Grupo</th><th>Crédito máximo</th><th>Crédito contratado</th><th>Parcela inicial</th><th>Prazo</th></tr></thead><tbody>${{rows}}</tbody></table></div></section><section><h2>Considerações importantes</h2><div class="content">Os cenários apresentados dependem das regras da administradora e da disponibilidade do grupo na data da contratação.</div></section>`;</script></body></html>''')


@app.delete("/api/estudos/{estudo_id}")
def estudos_excluir(estudo_id: str):
    logger.info("DELETE /api/estudos/%s", estudo_id)
    if not delete_estudo(estudo_id):
        return JSONResponse(status_code=404, content={"success": False, "error": "Estudo nao encontrado"})
    return {"success": True}


@app.post("/api/estudos/limpar")
def estudos_limpar():
    total = clear_all_estudos()
    logger.warning("Todos os estudos foram removidos: total=%s", total)
    return {"success": True, "deleted": total}


@app.get("/api/estudos/{estudo_id}/editor")
def estudos_editor_obter(estudo_id: str):
    if not get_settings().financial_editor_enabled:
        return JSONResponse(status_code=404, content={"success": False, "error": "Editor financeiro desativado"})
    estudo = get_estudo(estudo_id)
    if not estudo:
        return JSONResponse(status_code=404, content={"success": False, "error": "Estudo nao encontrado"})
    return {"success": True, "editor_content": normalize_editor_content(estudo.get("editor_content"), True), "editor_original": normalize_editor_content(estudo.get("editor_original"), True), "editor_version": estudo.get("editor_version") or 1}


@app.get("/api/estudos/{estudo_id}/editor/document")
def estudos_editor_documento(estudo_id: str):
    if not get_settings().financial_editor_enabled:
        return JSONResponse(status_code=404, content={"success": False, "error": "Editor financeiro desativado"})
    estudo = get_estudo(estudo_id)
    if not estudo:
        return JSONResponse(status_code=404, content={"success": False, "error": "Estudo nao encontrado"})
    payload = build_react_pdf_payload(estudo, get_settings().version)
    return {"success": True, "document": payload, "editor_content": normalize_editor_content(estudo.get("editor_content"), True)}


@app.put("/api/estudos/{estudo_id}/editor")
def estudos_editor_atualizar(estudo_id: str, payload: dict, request: Request = None):
    if not get_settings().financial_editor_enabled:
        return JSONResponse(status_code=404, content={"success": False, "error": "Editor financeiro desativado"})
    estudo = get_estudo(estudo_id)
    if not estudo:
        return JSONResponse(status_code=404, content={"success": False, "error": "Estudo nao encontrado"})
    content = payload.get("editor_content") if isinstance(payload, dict) else None
    if not isinstance(content, dict):
        return JSONResponse(status_code=422, content={"success": False, "error": "Conteudo editorial inválido"})
    username = getattr(getattr(request, "state", None), "auth_user", "")
    updated = update_estudo_editor(estudo_id, content, AUTH_USERS.get(username, {}).get("name", username))
    if not updated:
        return JSONResponse(status_code=503, content={"success": False, "error": "Persistência editorial indisponível para estudos em planilha"})
    return {"success": True, "editor_content": updated["editor_content"], "editor_version": updated["editor_version"]}


@app.get("/api/estudos/{estudo_id}/editor/history")
def estudos_editor_historico(estudo_id: str):
    estudo = get_estudo(estudo_id)
    if not estudo:
        return JSONResponse(status_code=404, content={"success": False, "error": "Estudo nao encontrado"})
    return {"success": True, "versions": estudo.get("editor_history") or []}


@app.post("/api/estudos/{estudo_id}/editor/restore")
def estudos_editor_restaurar(estudo_id: str, payload: dict | None = None):
    restored = restore_estudo_editor(estudo_id, (payload or {}).get("version"))
    if not restored:
        return JSONResponse(status_code=404, content={"success": False, "error": "Estudo ou versão não encontrado"})
    return {"success": True, "editor_content": restored.get("editor_content") or {}, "editor_version": restored.get("editor_version") or 1}


@app.post("/api/estudos/{estudo_id}/exportar-pdf")
def estudos_exportar_pdf(estudo_id: str):
    logger.info("POST /api/estudos/%s/exportar-pdf", estudo_id)
    estudo = get_estudo(estudo_id)
    if not estudo:
        return JSONResponse(status_code=404, content={"success": False, "error": "Estudo nao encontrado"})
    try:
        return _render_study_pdf_file(estudo, f"{estudo_id}.pdf")
    except Exception as error:
        logger.exception("Falha no pipeline canônico React-PDF para estudo %s", estudo_id)
        return JSONResponse(status_code=503, content={"success": False, "error": str(error), "engine": "react-pdf"})


@app.post("/api/estudos/{estudo_id}/preview-pdf")
def estudos_preview_pdf_salvo(estudo_id: str):
    """Gera uma prévia sem alterar o estudo salvo."""
    estudo = get_estudo(estudo_id)
    if not estudo:
        return JSONResponse(status_code=404, content={"success": False, "error": "Estudo nao encontrado"})
    try:
        rendered = _render_study_pdf_file(estudo, f"preview-{estudo_id}.pdf")
        return {**rendered, "kind": "preview", "study_id": estudo_id, "editor_version": estudo.get("editor_version") or 1}
    except Exception as error:
        return JSONResponse(status_code=503, content={"success": False, "error": str(error), "kind": "preview"})


@app.post("/api/estudos/{estudo_id}/finalizar-pdf")
def estudos_finalizar_pdf(estudo_id: str):
    """Gera o PDF final usando o snapshot financeiro persistido."""
    estudo = get_estudo(estudo_id)
    if not estudo:
        return JSONResponse(status_code=404, content={"success": False, "error": "Estudo nao encontrado"})
    try:
        rendered = _render_study_pdf_file(estudo, f"{estudo_id}-final-v{int(estudo.get('editor_version') or 1)}.pdf")
        estudo["final_pdf_url"] = rendered.get("download_url") or ""
        estudo["final_pdf_version"] = int(estudo.get("editor_version") or 1)
        return {**rendered, "download_url": f"/api/estudos/{estudo_id}/pdf", "kind": "final", "study_id": estudo_id, "editor_version": estudo["final_pdf_version"]}
    except Exception as error:
        return JSONResponse(status_code=503, content={"success": False, "error": str(error), "kind": "final"})


@app.post("/api/estudos/{estudo_id}/exportar-pdf-react")
def estudos_exportar_pdf_react(estudo_id: str):
    return estudos_exportar_pdf(estudo_id)


@app.get("/api/health/pdf-engine")
def pdf_engine_health():
    status = react_pdf_service_status()
    return JSONResponse(status_code=200 if status["available"] else 503, content={
        "success": status["available"],
        "engine": "react-pdf",
        "status": status,
        "canonical": True,
    })


@app.get("/api/estudos/pdf-engine-status")
def estudos_pdf_engine_status():
    status = react_pdf_service_status()
    return {"success": status["available"], "engine": "react-pdf", "status": status, "canonical": True}


@app.post("/api/estudos/preview-pdf")
def estudos_preview_pdf(payload: EstudoPreviewRequest, request: Request):
    logger.info("POST /api/estudos/preview-pdf grupo_id=%s", payload.grupo_id)
    try:
        _react_pdf_status_or_error()
        grupo = payload.grupo or get_grupo(payload.grupo_id)
        if not grupo:
            return JSONResponse(status_code=404, content={"success": False, "error": "Grupo nao encontrado"})
        username = getattr(request.state, "auth_user", "")
        operador = AUTH_USERS.get(username, {}).get("name", username)
        estudo = build_estudo_preview(payload, grupo, operador)
        rendered = _render_study_pdf_file(estudo, f"preview-{uuid4().hex}.pdf")
        audit_record = _write_preview_audit(payload, estudo, rendered, operador)
        return {
            "success": True,
            "download_url": rendered["download_url"],
            "engine": rendered["engine"],
            "audit_url": audit_record["audit_url"],
            "audit": audit_record["audit"],
        }
    except ValueError as error:
        logger.warning("Prévia bloqueada por snapshot inválido: %s", error)
        return JSONResponse(status_code=422, content={"success": False, "error": str(error), "engine": "react-pdf"})
    except Exception as error:
        logger.exception("Erro ao gerar prévia transitória do estudo")
        return JSONResponse(status_code=503, content={"success": False, "error": str(error), "engine": "react-pdf"})


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


@app.get("/api/templates-estudos")
def templates_estudos_listar(force_reload: bool = False):
    try:
        items = list_templates(force_reload=force_reload)
        return {"success": True, "items": items, "total": len(items), "sheet": "Templates"}
    except Exception as error:
        logger.exception("Erro ao carregar templates de estudos")
        return JSONResponse(status_code=503, content={"success": False, "error": str(error), "sheet": "Templates"})


@app.get("/api/templates-estudos/{slug}")
def templates_estudos_detalhe(slug: str):
    try:
        item = get_template(slug, active_only=False)
        if not item:
            return JSONResponse(status_code=404, content={"success": False, "error": "Template não encontrado."})
        return {"success": True, "item": item}
    except Exception as error:
        logger.exception("Erro ao carregar template %s", slug)
        return JSONResponse(status_code=503, content={"success": False, "error": str(error)})


@app.put("/api/configuracoes")
def configuracoes_salvar(payload: dict):
    logger.info("PUT /api/configuracoes")
    try:
        return update_configuracoes(payload)
    except Exception as error:
        logger.exception("Erro ao salvar configuracoes")
        return JSONResponse(status_code=400, content={"success": False, "error": str(error)})
