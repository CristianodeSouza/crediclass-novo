from pathlib import Path
from contextlib import asynccontextmanager
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
import re
import secrets
import shutil
import httpx
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import date
from html import escape as html_escape
from typing import Annotated
from urllib.parse import quote
from uuid import uuid4

from fastapi import FastAPI, Query, Request, Response
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .auditoria import list_auditoria, record_auditoria
from .motor360_auditoria import audit_to_markdown, audit_to_pdf, get_motor360_audit, save_motor360_audit
from .administrator_rules import normalize_admin_name, rules_by_administradora
from .config import get_settings
from .configuracoes import get_configuracoes, update_configuracoes
from .auth_store import activate_invitation, authenticate, audit_events, create_invitation, create_password_reset, create_session, get_session, get_user, init_auth_store, list_users, public_user, reset_password, resend_invitation, revoke_session, set_user_status, update_user
from .consortium_viability_engine import MOTOR_VERSION, RULES_VERSION, analyze_client_consortium_viability
from .credit_options import available_credit_options
from .defasagem import build_defasagem_report, update_defasagem_task
from . import financial_studies
from .piperun import activate_custom_form_public_link, create_opportunity_note, fetch_opportunities_preview, fetch_opportunity_notes, sync_partner_company, sync_spouse, update_opportunity_person
from .models import GrupoCreateRequest, GrupoCreateResponse, GrupoDetalhe, GrupoUpdateRequest, GruposResponse, HistoricoBatchUpdateRequest, HistoricoUpdateRequest, SuccessResponse, ViabilidadeRequest
from .sheets_client import clear_rows_cache, create_grupo, delete_grupo, export_sheet_csv, get_cached_grupos_defasagem, get_grupo, list_grupos, list_grupos_detalhe, list_grupos_detalhe_by_ids, motor360_cache_status, read_piperun_opportunities, update_grupo, update_historico_mensal, update_historico_mensal_lote, upsert_piperun_opportunities, warm_grupos_defasagem_cache_async, warm_motor360_cache_async
from .viabilidade import compatible_tipo_bem

# Uvicorn's default configuration does not attach a handler to the root
# logger. Configure application logs explicitly so Render captures them.
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    stream=sys.stdout,
)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
FILES_DIR = BASE_DIR / "generated_files"
DATA_DIR = BASE_DIR / "data"


FILES_DIR.mkdir(exist_ok=True)
logger = logging.getLogger("crediclass.api")

@asynccontextmanager
async def app_lifespan(_app: FastAPI):
    # Warm asynchronously so the web process becomes available immediately;
    # the cache worker refreshes before its five-minute TTL expires.
    warm_motor360_cache_async()
    yield


app = FastAPI(title="Crediclass Dashboard V3", lifespan=app_lifespan)
PDF_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="financial-study-pdf")
PDF_JOBS: dict[str, Future] = {}


def annotate_owner_eligibility(items: list[dict]) -> list[dict]:
    config = get_configuracoes()
    owners = config.get("piperun_owners", [])
    distribution_enabled = bool(config.get("piperun_owner_distribution_enabled"))
    ranges_configured = any(owner.get("credito_minimo") is not None or owner.get("credito_maximo") is not None for owner in owners if isinstance(owner, dict))
    for item in items:
        deal = item.get("oportunidade") or {}
        owner_id = str(deal.get("owner_id") or "").strip()
        if owner_id:
            item["owner_distribution"] = {"eligible": False, "reason": "owner_already_assigned", "owner_id": owner_id}
        elif not distribution_enabled:
            item["owner_distribution"] = {"eligible": False, "reason": "owner_distribution_disabled", "owner_id": ""}
        elif not ranges_configured:
            item["owner_distribution"] = {"eligible": False, "reason": "owner_ranges_not_configured", "owner_id": ""}
        else:
            item["owner_distribution"] = {"eligible": True, "reason": "eligible_without_owner", "owner_id": ""}
    return items


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    """Serve the legacy browser favicon path using the maintained SVG asset."""
    return FileResponse(STATIC_DIR / "favicon.svg", media_type="image/svg+xml", headers={"Cache-Control": "public, max-age=86400"})


class FinancialStudyApprovalRequest(BaseModel):
    client_name: str = Field(min_length=1, max_length=180)
    approval_key: str = Field(min_length=36, max_length=36)
    snapshot: dict
    document_html: str = Field(min_length=1, max_length=2_000_000)


class FinancialStudyPipeRunRequest(BaseModel):
    opportunity_id: str = Field(min_length=1, max_length=32)


class FinancialStudyShareRequest(BaseModel):
    opportunity_id: str | None = Field(default=None, max_length=32)


class FinancialStudyAgreementRequest(BaseModel):
    agreed: bool = True


@app.post("/api/financial-studies")
def approve_financial_study(payload: FinancialStudyApprovalRequest, request: Request):
    username = request.state.auth_user
    try:
        created = financial_studies.create_study(
            client_name=payload.client_name,
            approved_by=request.state.auth_session["name"],
            app_version=get_settings().version,
            snapshot=payload.snapshot,
            document_html=payload.document_html,
            approval_key=payload.approval_key,
        )
        return {"success": True, "study": created}
    except ValueError as error:
        return JSONResponse(status_code=422, content={"success": False, "error": str(error)})
    except RuntimeError as error:
        return JSONResponse(status_code=503, content={"success": False, "error": str(error)})
    except Exception:
        logger.exception("Falha ao persistir estudo financeiro aprovado")
        return JSONResponse(status_code=503, content={"success": False, "error": "Não foi possível salvar o estudo aprovado."})


@app.get("/api/financial-studies")
def list_financial_studies(request: Request, query: str = Query(default="", max_length=180), limit: int = Query(default=100, ge=1, le=200)):
    try:
        return {"success": True, "items": financial_studies.list_studies(query=query, limit=limit)}
    except RuntimeError as error:
        return JSONResponse(status_code=503, content={"success": False, "error": str(error)})
    except Exception:
        logger.exception("Falha ao listar estudos financeiros")
        return JSONResponse(status_code=503, content={"success": False, "error": "Não foi possível carregar o histórico de estudos."})


@app.get("/api/financial-studies/{study_id}/pdf")
def download_financial_study_pdf_route(study_id: str, request: Request, job: str | None = None):
    if job:
        future = PDF_JOBS.get(job)
        if future is None:
            return JSONResponse(status_code=404, content={"success": False, "error": "Tarefa de PDF não encontrada."})
        if not future.done():
            return JSONResponse(status_code=202, content={"success": True, "status": "processing", "job_id": job})
        PDF_JOBS.pop(job, None)
        try:
            return future.result()
        except Exception:
            logger.exception("Falha na tarefa de PDF %s", job)
            return JSONResponse(status_code=503, content={"success": False, "error": "O gerador de PDF está temporariamente indisponível."})

    job_id = uuid4().hex
    PDF_JOBS[job_id] = PDF_EXECUTOR.submit(download_financial_study_pdf, study_id, request)
    return JSONResponse(status_code=202, content={"success": True, "status": "processing", "job_id": job_id})


@app.get("/api/financial-studies/{study_id}")
def read_financial_study(study_id: str, request: Request):
    try:
        study = financial_studies.get_study(study_id)
    except RuntimeError as error:
        return JSONResponse(status_code=503, content={"success": False, "error": str(error)})
    except Exception:
        logger.exception("Falha ao carregar estudo financeiro %s", study_id)
        return JSONResponse(status_code=503, content={"success": False, "error": "Não foi possível carregar o estudo."})
    if study is None:
        return JSONResponse(status_code=404, content={"success": False, "error": "Estudo não encontrado."})
    public_link = study.get("public_link") or {}
    token = public_link.pop("token", None)
    if public_link.get("active") and token:
        public_link["url"] = str(request.base_url).rstrip("/") + f"/estudo-compartilhado/{token}"
    return {"success": True, "study": study}


def download_financial_study_pdf(study_id: str, request: Request):
    """Render the immutable study snapshot with server-side Chromium."""
    try:
        study = financial_studies.get_study(study_id)
    except RuntimeError as error:
        return JSONResponse(status_code=503, content={"success": False, "error": str(error)})
    except Exception:
        logger.exception("Falha ao carregar estudo para PDF %s", study_id)
        return JSONResponse(status_code=503, content={"success": False, "error": "Não foi possível carregar o estudo para gerar o PDF."})
    if study is None:
        return JSONResponse(status_code=404, content={"success": False, "error": "Estudo não encontrado."})

    return render_financial_study_pdf(study, request)


def safe_pdf_filename(client_name: str, fallback: str = "estudo-financeiro") -> str:
    filename = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', " ", str(client_name or ""))
    filename = re.sub(r"\s+", " ", filename).strip(" .")
    return filename or fallback


def render_financial_study_pdf(study: dict, request: Request):
    """Render a study snapshot and return it with a client-based download name."""
    study_id = str(study.get("id") or "estudo-financeiro")

    document_html = study.get("document_html")
    if not document_html:
        return JSONResponse(status_code=422, content={"success": False, "error": "Este registro não possui snapshot visual para gerar PDF."})

    # The snapshot is immutable application HTML. Remove executable content
    # before handing it to Chromium and inline the same stylesheet used by the
    # history preview so the PDF is independent of the Windows print driver.
    document_html = re.sub(r"<script\b[^>]*>.*?</script>", "", document_html, flags=re.IGNORECASE | re.DOTALL)
    stylesheet = (STATIC_DIR / "css" / "style.css").read_text(encoding="utf-8")
    base_url = str(request.base_url).rstrip("/") + "/"
    title = str(study.get("client_name") or f"Estudo Financeiro {study_id}")
    html = (
        "<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'>"
        f"<base href='{html_escape(base_url)}'><title>{html_escape(title)}</title>"
        f"<style>{stylesheet}</style><style>@page{{size:A4 portrait;margin:10mm}}"
        "html,body{width:190mm!important;min-width:190mm!important;margin:0!important;"
        "background:#fff!important;writing-mode:horizontal-tb!important}"
        ".financial-study-document{width:190mm!important;min-width:190mm!important;"
        "max-width:none!important;margin:0!important;transform:none!important}"
        "</style></head><body>"
        f"{document_html}</body></html>"
    )
    browser = None
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            launch_options = {
                "headless": True,
                "args": ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
            }
            # Render may expose a system Chromium even when the bundled
            # Playwright browser is unavailable after a cold deploy.
            system_browser = next(
                (shutil.which(name) for name in ("chromium", "chromium-browser", "google-chrome") if shutil.which(name)),
                None,
            )
            if system_browser:
                launch_options["executable_path"] = system_browser
            browser = playwright.chromium.launch(**launch_options)
            page = browser.new_page(viewport={"width": 1600, "height": 900}, device_scale_factor=1)
            page.set_content(html, wait_until="domcontentloaded", timeout=30000)
            page.emulate_media(media="print")
            pdf = page.pdf(format="A4", landscape=False, print_background=True, prefer_css_page_size=True, margin={"top": "10mm", "right": "10mm", "bottom": "10mm", "left": "10mm"})
    except Exception:
        logger.exception("Falha ao renderizar PDF do estudo %s", study_id)
        return JSONResponse(status_code=503, content={"success": False, "error": "O gerador de PDF está temporariamente indisponível."})
    finally:
        if browser is not None:
            try:
                browser.close()
            except Exception:
                logger.exception("Falha ao encerrar Chromium do estudo %s", study_id)

    filename = safe_pdf_filename(study.get("client_name"), fallback=study_id)
    ascii_filename = filename.encode("ascii", "ignore").decode("ascii").strip(" .") or "estudo-financeiro"
    encoded_filename = quote(f"{filename}.pdf")
    return Response(content=pdf, media_type="application/pdf", headers={
        "Content-Disposition": f'attachment; filename="{ascii_filename}.pdf"; filename*=UTF-8\'\'{encoded_filename}',
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
    })


@app.get("/estudo-compartilhado/{token}/pdf")
def download_public_financial_study_pdf(token: str, request: Request, job: str | None = None):
    """Generate the public study PDF without requiring an authenticated session."""
    study = financial_studies.get_public_study(token)
    if study is None:
        return JSONResponse(status_code=404, content={"success": False, "error": "Estudo não encontrado ou link expirado."})
    return download_financial_study_pdf_route(study["id"], request, job=job)


@app.post("/api/financial-studies/{study_id}/share")
async def generate_financial_study_share(study_id: str, payload: FinancialStudyShareRequest, request: Request):
    try:
        link = financial_studies.create_public_link(study_id)
    except ValueError as error:
        return JSONResponse(status_code=422, content={"success": False, "error": str(error)})
    except Exception:
        logger.exception("Falha ao gerar link público do estudo %s", study_id)
        return JSONResponse(status_code=503, content={"success": False, "error": "Não foi possível gerar o link público."})
    if link is None:
        return JSONResponse(status_code=404, content={"success": False, "error": "Estudo não encontrado."})
    result = {"success": True, "url": str(request.base_url).rstrip("/") + f"/estudo-compartilhado/{link['token']}",
              "expires_at": link["expires_at"], "validity_days": link["validity_days"],
              "piperun_form_url": "", "piperun_error": ""}
    try:
        study = financial_studies.get_study(study_id)
        opportunity_id = str(payload.opportunity_id or (study or {}).get("crm_opportunity_id") or "").strip()
        if opportunity_id:
            if not opportunity_id.isdigit():
                raise ValueError("O ID da oportunidade deve ser numérico.")
            existing_url = str((study or {}).get("piperun_form_url") or "").strip()
            existing_opportunity = str((study or {}).get("crm_opportunity_id") or "").strip()
            if existing_url and existing_opportunity == opportunity_id:
                result["piperun_form_url"] = existing_url
            else:
                pipe_form = await activate_custom_form_public_link(opportunity_id)
                financial_studies.set_piperun_form_url(study_id, opportunity_id, pipe_form["url"])
                result["piperun_form_url"] = pipe_form["url"]
    except Exception as error:
        logger.exception("Falha ao gerar link público do PipeRun para o estudo %s", study_id)
        result["piperun_error"] = str(error)
    return result


@app.delete("/api/financial-studies/{study_id}/share")
def revoke_financial_study_share(study_id: str, request: Request):
    try:
        result = financial_studies.revoke_public_link(study_id)
    except Exception:
        logger.exception("Falha ao revogar link público do estudo %s", study_id)
        return JSONResponse(status_code=503, content={"success": False, "error": "Não foi possível revogar o link público."})
    if result is None:
        return JSONResponse(status_code=404, content={"success": False, "error": "Estudo não encontrado."})
    return {"success": True, "public_link": result}


@app.post("/api/financial-studies/{study_id}/piperun")
async def send_financial_study_to_piperun(study_id: str, payload: FinancialStudyPipeRunRequest, request: Request):
    """Send only the active public study URL as a note linked to a PipeRun deal."""
    opportunity_id = payload.opportunity_id.strip()
    if not opportunity_id.isdigit():
        return JSONResponse(status_code=422, content={"success": False, "error": "O ID da oportunidade deve ser numérico."})
    try:
        study = financial_studies.get_study(study_id)
        if study is None:
            return JSONResponse(status_code=404, content={"success": False, "error": "Estudo não encontrado."})
        public_link = study.get("public_link") or {}
        token = str(public_link.get("token") or "").strip()
        if public_link.get("active") is not True or not token:
            return JSONResponse(status_code=409, content={"success": False, "error": "Gere um link público ativo antes de enviar o estudo ao PipeRun."})
        association = financial_studies.set_crm_opportunity_id(study_id, opportunity_id)
        if association is None:
            return JSONResponse(status_code=404, content={"success": False, "error": "Estudo não encontrado."})
        study_url = str(request.base_url).rstrip("/") + f"/estudo-compartilhado/{token}"
        operator = request.state.auth_session["name"]
        approved_at = str(study.get("approved_at") or "-")
        piperun_form_url = str(study.get("piperun_form_url") or "").strip()
        piperun_next_steps = (
            f"<p>Próximos passos: <a href=\"{html_escape(piperun_form_url, quote=True)}\" target=\"_blank\" rel=\"noopener noreferrer\">{html_escape(piperun_form_url)}</a></p>"
            if piperun_form_url
            else ""
        )
        note_text = (
            "<p><strong>ESTUDO FINANCEIRO — CSR Tecnologia</strong></p>"
            f"<p>Cliente: {html_escape(str(study.get('client_name') or '-'))}</p>"
            f"<p>Estudo: {html_escape(study_id)}</p>"
            f"<p>Data de geração: {html_escape(approved_at)}</p>"
            f"<p>Usuário responsável: {html_escape(operator)}</p>"
            f"<p>ID da oportunidade PipeRun: {html_escape(opportunity_id)}</p>"
            + piperun_next_steps
            + f"<p><strong>ABRIR ESTUDO FINANCEIRO</strong></p>"
            + f"<p><a href=\"{html_escape(study_url, quote=True)}\" target=\"_blank\" rel=\"noopener noreferrer\">{html_escape(study_url)}</a></p>"
        )
        note = await create_opportunity_note(opportunity_id, note_text)
        return {"success": True, "study_id": study_id, "opportunity_id": opportunity_id, "study_url": study_url, "note_id": note.get("note_id")}
    except ValueError as error:
        return JSONResponse(status_code=422, content={"success": False, "error": str(error)})
    except RuntimeError as error:
        return JSONResponse(status_code=502, content={"success": False, "error": str(error)})
    except Exception:
        logger.exception("Falha ao enviar estudo %s ao PipeRun", study_id)
        return JSONResponse(status_code=502, content={"success": False, "error": "Não foi possível enviar o estudo ao PipeRun."})


@app.get("/estudo-compartilhado/{token}")
def read_public_financial_study(token: str):
    try:
        study = financial_studies.get_public_study(token)
    except Exception:
        logger.exception("Falha ao carregar estudo financeiro compartilhado")
        return HTMLResponse(
            "<!doctype html><html lang='pt-BR'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<title>Estudo temporariamente indisponível | CrediClass</title><body style='font:16px system-ui;color:#2e3f47;max-width:680px;margin:12vh auto;padding:24px'>"
            "<h1>Estudo temporariamente indisponível</h1><p>Não foi possível carregar o estudo agora. Tente novamente em alguns minutos.</p></body></html>",
            status_code=503,
            headers={"Cache-Control": "no-store", "X-Robots-Tag": "noindex, nofollow, noarchive", "Referrer-Policy": "no-referrer"},
        )
    if study is None:
        return HTMLResponse(
            "<!doctype html><html lang='pt-BR'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<title>Estudo indisponível | CrediClass</title><body style='font:16px system-ui;color:#2e3f47;max-width:680px;margin:12vh auto;padding:24px'>"
            "<h1>Este link não está disponível</h1><p>Ele pode ter expirado, sido revogado ou estar incorreto. Solicite um novo link à CrediClass.</p></body></html>",
            status_code=404,
            headers={"Cache-Control": "no-store", "X-Robots-Tag": "noindex, nofollow, noarchive", "Referrer-Policy": "no-referrer"},
        )
    nonce = secrets.token_urlsafe(18)
    release_version = get_settings().version
    document = "<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
    document += f"<title>{html_escape(study['client_name'])}</title><link rel='icon' href='/static/favicon.svg?v={release_version}' type='image/svg+xml'><link rel='stylesheet' href='/static/css/style.css?v={release_version}'>"
    document += "<meta name='robots' content='noindex,nofollow,noarchive'></head><body class='shared-study-page'>"
    document += "<div class='shared-study-shell'>"
    document += "<header class='shared-study-header'><div class='shared-study-brand'>CREDICLASS <span>· Estudo Financeiro</span></div></header>"
    agreement_markup = (
        "<section id='publicStudyAgreement' class='public-study-agreement' aria-labelledby='publicStudyAgreementTitle' "
        f"data-study-token='{html_escape(token, quote=True)}' data-agreement-status='{html_escape(str((study.get('agreement') or {}).get('status') or 'pending'), quote=True)}'>"
        "<h2 id='publicStudyAgreementTitle'>13. DE ACORDO</h2>"
        "<div class='public-study-agreement-content'>"
        "<p>Declaro que li e estou de acordo com as informações, valores, projeções e condições apresentadas neste Estudo Financeiro.</p>"
        "<label class='public-study-agreement-check'><input id='publicStudyAgreementCheckbox' type='checkbox'> <span>Li e estou de acordo com o estudo apresentado.</span></label>"
        "<button id='publicStudyAgreementSubmit' type='button' disabled>Confirmar acordo</button>"
        "<p id='publicStudyAgreementStatus' class='public-study-agreement-status' role='status' aria-live='polite'></p>"
        "</div>"
        "</section>"
    )
    agreement = study.get("agreement") or {}
    agreement_is_done = str(agreement.get("status") or "") == "agreed"
    piperun_form_url = str(study.get("piperun_form_url") or "").strip()
    study_dates = study.get("study_dates") or {}
    next_assembly = " / ".join(str(value) for value in (study_dates.get("next_assembly") or [])) or "Não informado"
    reservation_deadline = " / ".join(str(value) for value in (study_dates.get("reservation_deadline") or [])) or "Não informado"
    piperun_link = (
        f"<a href='{html_escape(piperun_form_url, quote=True)}' target='_blank' rel='noopener noreferrer'>{html_escape(piperun_form_url)}</a>"
        if piperun_form_url else "<span>Não informado</span>"
    )
    followup_hidden = "" if agreement_is_done else " hidden"
    followup_markup = (
        f"<section id='publicStudyRegistration' class='public-study-followup'{followup_hidden} aria-labelledby='publicStudyRegistrationTitle'>"
        "<h2 id='publicStudyRegistrationTitle'>14. FICHA CADASTRAL</h2>"
        "<div class='public-study-followup-content'>"
        "<p>Agora, diante do aceite do estudo, será necessário complementar os dados da ficha cadastral abaixo:</p>"
        "<p><strong>Pontos Importantes</strong></p>"
        f"<p>- Próxima assembleia: <strong>{html_escape(next_assembly)}</strong><br>"
        f"- Vencimento vagas reservadas: <strong>{html_escape(reservation_deadline)}</strong><br>"
        f"- Para seguirmos vamos precisar da Ficha Cadastral no seguinte link: {piperun_link}</p>"
        "</div>"
        "</section>"
    )
    document += f"<main class='shared-study-content'>{study['document_html']}{agreement_markup}{followup_markup}</main></div>"
    document += f"<script nonce='{nonce}' src='/static/js/shared-study.js?v={release_version}' defer></script></body></html>"
    policy = f"default-src 'none'; script-src 'nonce-{nonce}'; connect-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self' data:; object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
    return HTMLResponse(document, headers={"Cache-Control": "no-store", "X-Robots-Tag": "noindex, nofollow, noarchive", "Referrer-Policy": "no-referrer", "X-Content-Type-Options": "nosniff", "Content-Security-Policy": policy})


@app.post("/api/estudo-compartilhado/{token}/acordo")
def record_public_financial_study_agreement(token: str, payload: FinancialStudyAgreementRequest, request: Request):
    if payload.agreed is not True:
        return JSONResponse(status_code=422, content={"success": False, "error": "É necessário confirmar o acordo."})
    try:
        result = financial_studies.record_public_agreement(
            token,
            ip_address=request.client.host if request.client else "",
            user_agent=request.headers.get("user-agent", ""),
        )
        if result is None:
            return JSONResponse(status_code=404, content={"success": False, "error": "Estudo não encontrado, expirado ou revogado."})
        return {"success": True, **result}
    except Exception:
        logger.exception("Falha ao registrar acordo do estudo público")
        return JSONResponse(status_code=503, content={"success": False, "error": "Não foi possível registrar o acordo agora."})


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


@app.post("/api/piperun/{opportunity_id}/titular")
async def atualizar_titular_piperun(opportunity_id: str, person_id: str = Query(...)):
    try:
        preview = await fetch_opportunity_notes(opportunity_id)
        result = await update_opportunity_person(opportunity_id, person_id, preview.get("dados") or {})
        spouse = await sync_spouse(opportunity_id, preview.get("dados") or {})
        partners = await sync_partner_company(opportunity_id, preview.get("dados") or {})
        stored = {**preview, "oportunidade": {"id": opportunity_id, "person_id": person_id}, **result, **spouse, **partners}
        upsert_piperun_opportunities([stored])
        return {"success": True, "result": stored}
    except (ValueError, RuntimeError) as error:
        return JSONResponse(status_code=422, content={"success": False, "error": str(error)})
    except Exception as error:
        logger.exception("Falha ao atualizar titular PipeRun %s", opportunity_id)
        return JSONResponse(status_code=502, content={"success": False, "error": str(error)})


async def _sync_people_for_new_items(items: list[dict]) -> list[dict]:
    """Complete people only while importing fresh PipeRun results; stored history remains read-only."""
    synced = []
    for item in items:
        deal = item.get("oportunidade") or {}
        person_id = str(deal.get("person_id") or "").strip()
        opportunity_id = str(deal.get("id") or item.get("crm_oportunidade_id") or "").strip()
        if person_id.isdigit() and opportunity_id.isdigit() and item.get("encontrado"):
            titular = await update_opportunity_person(opportunity_id, person_id, item.get("dados") or {})
            spouse = await sync_spouse(opportunity_id, item.get("dados") or {})
            partners = await sync_partner_company(opportunity_id, item.get("dados") or {})
            item = {**item, **titular, **spouse, **partners}
        synced.append(item)
    return synced


@app.get("/api/piperun-preview")
async def preview_oportunidades_piperun(limit: int = Query(default=0, ge=0, le=10000), created_at_start: str | None = None, created_at_end: str | None = None):
    """Leitura temporária de todas as oportunidades recentes e suas notas, sem escrita."""
    try:
        items = await _sync_people_for_new_items(await fetch_opportunities_preview(limit, created_at_start, created_at_end))
        items = annotate_owner_eligibility(items)
        sheets = upsert_piperun_opportunities(items)
        return {"success": True, "temporary": False, "items": items, "sheets": sheets}
    except Exception as error:
        logger.exception("Falha ao carregar preview PipeRun")
        return JSONResponse(status_code=502, content={"success": False, "error": str(error)})


@app.get("/api/piperun-stored")
async def oportunidades_piperun_salvas():
    try:
        return {"success": True, "stored": True, "items": annotate_owner_eligibility(read_piperun_opportunities())}
    except Exception as error:
        logger.exception("Falha ao carregar oportunidades salvas")
        return JSONResponse(status_code=502, content={"success": False, "error": str(error)})


@app.get("/api/piperun-search/{opportunity_id}")
async def buscar_oportunidade_para_crm(opportunity_id: str):
    try:
        token = os.getenv("PIPERUN_API_KEY", "").strip()
        if not opportunity_id.isdigit() or not token:
            raise ValueError("Informe um ID numérico de oportunidade.")
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(f"https://api.pipe.run/v1/deals/{opportunity_id}", headers={"token": token, "accept": "application/json"})
        if response.status_code >= 400:
            raise RuntimeError(f"PipeRun recusou a oportunidade (HTTP {response.status_code}).")
        payload = response.json()
        deal = payload.get("data", payload)
        item = {"oportunidade": deal, **await fetch_opportunity_notes(opportunity_id)}
        item = (await _sync_people_for_new_items([item]))[0]
        sheets = upsert_piperun_opportunities([item])
        return {"success": True, "items": annotate_owner_eligibility([item]), "sheets": sheets}
    except Exception as error:
        logger.exception("Falha na consulta manual PipeRun %s", opportunity_id)
        return JSONResponse(status_code=502, content={"success": False, "error": str(error)})


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
init_auth_store(AUTH_USERS)


def _is_administrator_request(request: Request) -> bool:
    username = getattr(request.state, "auth_user", None)
    return bool(username and getattr(request.state, "auth_session", {}).get("role") == "Administrador")


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
    if path.startswith("/api/estudo-compartilhado/") and path.endswith("/acordo"):
        return True
    return path in {"/api/auth/login", "/api/auth/logout", "/api/auth/me", "/api/auth/activate", "/api/auth/forgot-password", "/api/auth/reset-password", "/api/health"}


@app.middleware("http")
async def require_authenticated_session(request: Request, call_next):
    path = request.url.path
    if path.startswith("/api/") and not _public_auth_path(path):
        session = get_session(request.cookies.get(AUTH_COOKIE))
        if not session:
            return JSONResponse(status_code=401, content={"success": False, "error": "Acesso restrito. Faca login para continuar."})
        request.state.auth_user = session["username"]
        request.state.auth_session = dict(session)
    if path.startswith("/files/"):
        if not get_session(request.cookies.get(AUTH_COOKIE)):
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
    commit = (os.getenv("RENDER_GIT_COMMIT") or os.getenv("GIT_COMMIT") or os.getenv("SOURCE_VERSION") or "").strip()
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.version,
        "environment": settings.environment,
        "commit": commit[:40] or None,
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
    response: Response = None,
):
    request_started = time.perf_counter()
    logger.info("GET /api/grupos page=%s page_size=%s busca=%s", page, page_size, busca)
    try:
        source_started = time.perf_counter()
        items = list_grupos(include_history=True)
        source_duration_ms = (time.perf_counter() - source_started) * 1000
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
    total_duration_ms = (time.perf_counter() - request_started) * 1000
    if response is not None:
        response.headers["Server-Timing"] = f"sheet_cache;dur={source_duration_ms:.2f}, total;dur={total_duration_ms:.2f}"
    logger.info("GET /api/grupos retornou total=%s page=%s sheet_cache_ms=%.2f total_ms=%.2f", total, page, source_duration_ms, total_duration_ms)
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
def viabilidade_360_analisar(payload: ViabilidadeRequest, response: Response, request: Request, compact: bool = False):
    """Single entry point: declared objective is a presentation preference, never an exclusion."""
    request_started = time.perf_counter()
    request_id = f"REQ-{uuid4().hex[:12].upper()}"
    logger.info("POST /api/viabilidade-360/analisar request_id=%s credito=%s", request_id, payload.credito_desejado)
    try:
        cache_status = motor360_cache_status(include_history=True)
        if not cache_status["ready"] and (cache_status["refreshing"] or get_settings().environment == "production"):
            # The startup worker is the single owner of the cold refresh. Do
            # not make the request thread wait behind Google Sheets long enough
            # for Render's proxy to emit a misleading 502.
            if not cache_status["refreshing"]:
                warm_motor360_cache_async()
            logger.info(
                "Motor 360 aguardando cache request_id=%s ready=%s refreshing=%s",
                request_id, cache_status["ready"], cache_status["refreshing"],
            )
            return JSONResponse(
                status_code=202,
                content={
                    "success": False,
                    "status": "warming",
                    "retry_after_ms": 1500,
                    "error": "A base do Motor 360 está sendo preparada. Tente novamente em instantes.",
                    "request_id": request_id,
                },
                headers={"Retry-After": "2", "Cache-Control": "no-store"},
            )
        # O histórico completo alimenta o tooltip do Motor 360. A leitura é
        # cacheada pelo cliente da planilha, portanto não há uma nova consulta
        # ao Google Sheets para cada grupo exibido.
        source_started = time.perf_counter()
        groups = list_grupos(include_history=True)
        total_groups_in_base = len(groups)
        requested_type = str(payload.tipo_bem or "").strip()
        if payload.tipo_bem_explicit and requested_type:
            # Reduzir a entrada do motor antes de qualquer cálculo de cenário,
            # matriz de contemplação, crédito e composição. O campo tipo_bem
            # já vem mapeado da coluna C da planilha.
            groups = [
                group for group in groups
                if compatible_tipo_bem("", str(group.get("tipo_bem") or ""), requested_type)
            ]
        source_duration_ms = (time.perf_counter() - source_started) * 1000
        administrators_analyzed = sorted(
            {str(group.get("administradora") or "").strip() for group in groups if str(group.get("administradora") or "").strip()},
            key=str.casefold,
        )
        selected_administrator = str(payload.administradora or "").strip()
        if selected_administrator:
            groups = [group for group in groups if str(group.get("administradora") or "").strip().casefold() == selected_administrator.casefold()]
        engine_started = time.perf_counter()
        result = analyze_client_consortium_viability(payload, groups, mode=payload.base_mode, request_id=request_id)
        engine_duration_ms = (time.perf_counter() - engine_started) * 1000
        result["administradoras_analisadas"] = administrators_analyzed
        result["engine_version"] = MOTOR_VERSION
        result["rules_version"] = RULES_VERSION
        seen_item_ids = set()
        for collection_name in ("final_items", "items", "credit_items", "matrix_items", "composition_items"):
            for item in result.get(collection_name, []) or []:
                if id(item) in seen_item_ids:
                    continue
                seen_item_ids.add(id(item))
                item["available_credit_options"] = available_credit_options(item)
        result["administradora_selecionada"] = selected_administrator or None
        result["grupos_na_base"] = total_groups_in_base
        result["grupos_filtrados_por_tipo_bem"] = len(groups) if payload.tipo_bem_explicit and requested_type else None
        result["grupos_ignorados_por_tipo_bem"] = total_groups_in_base - len(groups) if payload.tipo_bem_explicit and requested_type else None
        audit_payload = result.pop("audit")
        audit_payload.setdefault("data_source", {})["load_duration_ms"] = round(source_duration_ms, 2)
        audit_payload["metadata"]["engine_duration_ms"] = round(engine_duration_ms, 2)
        audit_started = time.perf_counter()
        audit = save_motor360_audit(audit_payload)
        audit_save_duration_ms = (time.perf_counter() - audit_started) * 1000
        if compact:
            # The browser consumes final_items for cards and only a small
            # projection of matrix_items for the contemplation matrix. Avoid
            # serializing engine work queues and a second final_items alias.
            result["matrix_items"] = [
                {
                    "grupo": item.get("grupo"),
                    "grupo_id": item.get("grupo_id"),
                    "administradora": item.get("administradora"),
                    "eligible_scenarios": item.get("eligible_scenarios", []),
                    "cenarios": [
                        {
                            "id": scenario.get("id"),
                            "eligible": scenario.get("eligible"),
                            "credit_compatible": scenario.get("credit_compatible"),
                            "term_compatible": scenario.get("term_compatible"),
                            "perfis_contemplacao": [
                                {
                                    "id": profile.get("id"),
                                    "atinge_perfil": profile.get("atinge_perfil"),
                                    "percentual_referencia": profile.get("percentual_referencia"),
                                }
                                for profile in (scenario.get("perfis_contemplacao") or [])
                            ],
                        }
                        for scenario in (item.get("cenarios") or [])
                    ],
                }
                for item in result.get("matrix_items", [])
            ]
            # The compact list already carries the normalized fields used by
            # cards and calculations. Keep only the source-column provenance
            # needed by the financial-study traceability payload; raw source
            # snapshots and per-group history mappings remain in the audit API.
            study_mapping_fields = {
                "tipo_bem", "prazo_restante", "credito_minimo",
                "credito_intermediario_1", "credito_intermediario_2",
                "credito_intermediario_3", "credito_maximo", "taxa_adm",
                "taxa_adm_ano", "taxa_ano", "fundo_reserva",
                "fundo_reserva_ano", "percentual_lance_embutido",
                "vencimento_parcela", "lance_conservador_24m",
                "lance_moderado_12m", "lance_agressivo_6m",
                "lance_super_agressivo_3m",
            }
            for item in result.get("final_items", []) or []:
                raw_mapping = item.get("mapeamento_origem") or {}
                item["mapeamento_origem"] = {
                    field: raw_mapping[field]
                    for field in study_mapping_fields
                    if field in raw_mapping
                }
                item.pop("source_values", None)
            result.pop("items", None)
            result.pop("credit_items", None)
            result.pop("composition_items", None)
        total_duration_ms = (time.perf_counter() - request_started) * 1000
        response.headers["Server-Timing"] = (
            f"sheet_load;dur={source_duration_ms:.2f}, engine;dur={engine_duration_ms:.2f}, "
            f"audit_save;dur={audit_save_duration_ms:.2f}, total;dur={total_duration_ms:.2f}"
        )
        logger.info(
            "Motor 360 concluido request_id=%s grupos=%s sheet_load_ms=%.2f engine_ms=%.2f audit_save_ms=%.2f total_ms=%.2f",
            request_id, len(groups), source_duration_ms, engine_duration_ms, audit_save_duration_ms, total_duration_ms,
        )
        result["audit_id"] = audit["metadata"]["audit_id"]
        # Keep the audit attached to the execution result as a durable client
        # fallback. The runtime JSON store can be lost on a Render restart or
        # deploy, while the browser cache may still retain this result.
        if _is_administrator_request(request):
            result["audit"] = audit
        result["request_id"] = request_id
        return result
    except ValueError as error:
        logger.warning("Motor 360 recusou a entrada request_id=%s error=%s", request_id, error)
        return JSONResponse(status_code=422, content={"success": False, "error": str(error), "request_id": request_id})
    except Exception as error:
        logger.exception("Erro no motor 360 de viabilidade request_id=%s", request_id)
        return JSONResponse(status_code=503, content={"success": False, "error": "Falha interna ao calcular o Motor 360.", "request_id": request_id})


@app.get("/api/viabilidade-360/auditorias/{audit_id}")
def viabilidade_360_auditoria(audit_id: str, request: Request):
    if not _is_administrator_request(request):
        return JSONResponse(status_code=403, content={"success": False, "error": "A auditoria é restrita ao usuário administrador."})
    audit = get_motor360_audit(audit_id)
    if audit is None:
        return JSONResponse(status_code=404, content={"success": False, "error": "Auditoria não encontrada."})
    return audit


@app.get("/api/viabilidade-360/auditorias/{audit_id}/exportar.md")
def viabilidade_360_auditoria_markdown(audit_id: str, request: Request):
    if not _is_administrator_request(request):
        return JSONResponse(status_code=403, content={"success": False, "error": "A auditoria é restrita ao usuário administrador."})
    audit = get_motor360_audit(audit_id)
    if audit is None:
        return JSONResponse(status_code=404, content={"success": False, "error": "Auditoria não encontrada."})
    headers = {"Content-Disposition": f'attachment; filename="{audit_id}.md"'}
    return PlainTextResponse(audit_to_markdown(audit), headers=headers)


@app.get("/api/viabilidade-360/auditorias/{audit_id}/exportar.pdf")
def viabilidade_360_auditoria_pdf(audit_id: str, request: Request):
    if not _is_administrator_request(request):
        return JSONResponse(status_code=403, content={"success": False, "error": "A auditoria é restrita ao usuário administrador."})
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
    user = authenticate(username, password)
    if not user:
        return JSONResponse(status_code=401, content={"success": False, "error": "Usuario ou senha invalidos."})
    token = create_session(user["id"], request.client.host if request.client else "", request.headers.get("user-agent", ""))
    response.set_cookie(
        AUTH_COOKIE,
        token,
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
        max_age=60 * 60 * 12,
        path="/",
    )
    return {
        "success": True,
        "user": public_user(user),
    }


@app.post("/api/auth/logout")
def auth_logout(request: Request, response: Response):
    revoke_session(request.cookies.get(AUTH_COOKIE))
    response.delete_cookie(AUTH_COOKIE, path="/")
    return {"success": True}


@app.get("/api/auth/me")
def auth_me(request: Request):
    session = get_session(request.cookies.get(AUTH_COOKIE))
    if not session:
        return JSONResponse(status_code=401, content={"success": False, "error": "Sessao nao autenticada."})
    return {
        "success": True,
        "user": public_user(session),
    }


@app.post("/api/auth/activate")
async def auth_activate(request: Request):
    payload = await request.json()
    token = str(payload.get("token") or "").strip()
    password = str(payload.get("senha") or "")
    if len(password) < 10:
        return JSONResponse(status_code=422, content={"success": False, "error": "A senha deve ter pelo menos 10 caracteres."})
    user = activate_invitation(token, password)
    if not user:
        return JSONResponse(status_code=400, content={"success": False, "error": "Convite inválido, expirado ou já utilizado."})
    return {"success": True, "user": public_user(user)}


@app.post("/api/auth/forgot-password")
async def auth_forgot_password(request: Request):
    # A entrega do link depende do canal de comunicação escolhido pela equipe.
    # O endpoint não revela se o e-mail existe, evitando enumeração de usuários.
    return {"success": True, "message": "Se o e-mail estiver cadastrado, solicite ao administrador o link de redefinição."}


@app.post("/api/auth/reset-password")
async def auth_reset_password(request: Request):
    payload = await request.json()
    password = str(payload.get("senha") or "")
    if len(password) < 10:
        return JSONResponse(status_code=422, content={"success": False, "error": "A senha deve ter pelo menos 10 caracteres."})
    user = reset_password(str(payload.get("token") or ""), password)
    if not user:
        return JSONResponse(status_code=400, content={"success": False, "error": "Link de redefinição inválido ou expirado."})
    return {"success": True, "user": public_user(user)}


@app.get("/api/admin/users")
def admin_users(request: Request):
    if not _is_administrator_request(request):
        return JSONResponse(status_code=403, content={"success": False, "error": "Apenas administradores podem gerenciar acessos."})
    return {"success": True, "usuarios": list_users()}


@app.post("/api/admin/users")
async def admin_create_user(request: Request):
    if not _is_administrator_request(request):
        return JSONResponse(status_code=403, content={"success": False, "error": "Apenas administradores podem gerenciar acessos."})
    payload = await request.json()
    name = str(payload.get("nome") or "").strip()
    email = str(payload.get("email") or "").strip().lower()
    whatsapp = str(payload.get("whatsapp") or "").strip()
    role = str(payload.get("perfil") or "Operador").strip()
    if not name or not email or not whatsapp:
        return JSONResponse(status_code=422, content={"success": False, "error": "Nome, e-mail e WhatsApp são obrigatórios."})
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        return JSONResponse(status_code=422, content={"success": False, "error": "Informe um e-mail válido."})
    if role not in {"Operador", "Administrador"}:
        return JSONResponse(status_code=422, content={"success": False, "error": "Perfil inválido."})
    try:
        user, token = create_invitation(name, email, whatsapp, role, request.state.auth_session["user_id"])
        return {"success": True, "usuario": user, "invite_url": f"/?ativar={token}"}
    except ValueError as error:
        return JSONResponse(status_code=409, content={"success": False, "error": str(error)})


@app.post("/api/admin/users/{user_id}/status")
async def admin_change_user_status(user_id: int, request: Request):
    if not _is_administrator_request(request):
        return JSONResponse(status_code=403, content={"success": False, "error": "Apenas administradores podem gerenciar acessos."})
    payload = await request.json()
    try:
        user = set_user_status(user_id, str(payload.get("status") or ""), request.state.auth_session["user_id"])
    except ValueError as error:
        return JSONResponse(status_code=422, content={"success": False, "error": str(error)})
    if not user:
        return JSONResponse(status_code=404, content={"success": False, "error": "Usuário não encontrado."})
    return {"success": True, "usuario": user}


@app.patch("/api/admin/users/{user_id}")
async def admin_update_user(user_id: int, request: Request):
    if not _is_administrator_request(request):
        return JSONResponse(status_code=403, content={"success": False, "error": "Apenas administradores podem gerenciar acessos."})
    payload = await request.json()
    try:
        user = update_user(user_id, str(payload.get("nome") or ""), str(payload.get("email") or ""), str(payload.get("whatsapp") or ""), str(payload.get("perfil") or "Operador"), request.state.auth_session["user_id"])
    except ValueError as error:
        return JSONResponse(status_code=409, content={"success": False, "error": str(error)})
    if not user:
        return JSONResponse(status_code=404, content={"success": False, "error": "Usuário não encontrado."})
    return {"success": True, "usuario": user}


@app.post("/api/admin/users/{user_id}/invitation")
def admin_resend_invitation(user_id: int, request: Request):
    if not _is_administrator_request(request):
        return JSONResponse(status_code=403, content={"success": False, "error": "Apenas administradores podem reenviar convites."})
    token = resend_invitation(user_id, request.state.auth_session["user_id"])
    if not token:
        return JSONResponse(status_code=409, content={"success": False, "error": "O usuário não está aguardando ativação."})
    return {"success": True, "invite_url": f"/?ativar={token}"}


@app.post("/api/admin/users/{user_id}/password-reset")
def admin_password_reset(user_id: int, request: Request):
    if not _is_administrator_request(request):
        return JSONResponse(status_code=403, content={"success": False, "error": "Apenas administradores podem redefinir senhas."})
    token = create_password_reset(user_id, request.state.auth_session["user_id"])
    if not token:
        return JSONResponse(status_code=404, content={"success": False, "error": "Usuário não encontrado."})
    return {"success": True, "reset_url": f"/?redefinir={token}"}


@app.get("/api/admin/auth-audit")
def admin_auth_audit(request: Request):
    if not _is_administrator_request(request):
        return JSONResponse(status_code=403, content={"success": False, "error": "Apenas administradores podem consultar a auditoria."})
    return {"success": True, "eventos": audit_events()}


@app.get("/api/configuracoes")
def configuracoes_obter(request: Request):
    if not _is_administrator_request(request):
        return JSONResponse(status_code=403, content={"success": False, "error": "Apenas administradores podem consultar configurações."})
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
def configuracoes_salvar(payload: dict, request: Request):
    if not _is_administrator_request(request):
        return JSONResponse(status_code=403, content={"success": False, "error": "Apenas administradores podem alterar configurações."})
    logger.info("PUT /api/configuracoes")
    try:
        return update_configuracoes(payload)
    except Exception as error:
        logger.exception("Erro ao salvar configuracoes")
        return JSONResponse(status_code=400, content={"success": False, "error": str(error)})
