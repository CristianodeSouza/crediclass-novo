"""Leitura e validação da aba Templates da planilha operacional."""
from __future__ import annotations
import copy
import json
import threading
import time
from typing import Any
from .config import get_settings
from .sheets_client import get_service

TEMPLATES_SHEET_NAME = "Templates"
CACHE_TTL_SECONDS = 60
TEMPLATE_HEADERS = ["template_id", "administradora", "slug", "status", "versao", "logo_url", "cor_primaria", "cor_secundaria", "titulo_estudo", "texto_introducao", "texto_criterios", "texto_como_funciona", "texto_contemplacao", "texto_uso_credito", "texto_observacoes", "secoes_visiveis_json", "ordem_secoes_json", "imagens_json", "atualizado_em", "atualizado_por"]
INITIAL_DRIVE_TEMPLATE = {
    "template_id": "itau-estudo-imovel-v1",
    "administradora": "ITAU",
    "slug": "itau",
    "status": "Rascunho",
    "versao": "1.0",
    "nome_arquivo": "EF AQUISIÇÃO DE IMÓVEL - exemplo de estudo - Consorcio Itaú - 2M.pdf",
    "drive_file_id": "14YhzgJodBgK6EQzx906TG8I20b7wNWhp",
    "drive_url": "https://drive.google.com/file/d/14YhzgJodBgK6EQzx906TG8I20b7wNWhp/view?usp=drive_link",
    "source_type": "google_drive",
    "sections": [
        {"key": "intro", "title": "Estudo Financeiro", "kind": "institutional"},
        {"key": "investment_simulation", "title": "Simulação de investimento", "kind": "financial"},
        {"key": "selection_criteria", "title": "Simulação melhores consórcios", "kind": "institutional"},
        {"key": "contracting", "title": "Contratação", "kind": "groups_table"},
        {"key": "strategies", "title": "Estratégias de contemplação", "kind": "financial"},
        {"key": "bid_history", "title": "Histórico de lances contemplados", "kind": "history_table"},
        {"key": "projection", "title": "Projeção de contemplação", "kind": "scenarios"},
        {"key": "deadlines", "title": "Datas limites para adesão", "kind": "operational"},
        {"key": "legal", "title": "Considerações importantes", "kind": "legal"},
    ],
    "atualizado_por": "Administrador",
    "validation_errors": ["Registro inicial de referência; confirme a linha na aba Templates para publicar."],
    "is_valid": False,
}
_cache: dict[str, Any] = {"items": None, "expires_at": 0.0}
_cache_lock = threading.Lock()

def _clean(value: Any) -> str:
    return str(value or "").strip()

def _json_cell(value: Any, fallback: Any) -> Any:
    if isinstance(value, (list, dict)):
        return value
    text = _clean(value)
    if not text:
        return fallback
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return fallback

def normalize_template(row: dict[str, Any], row_number: int | None = None) -> dict[str, Any]:
    item = {key: _clean(row.get(key)) for key in TEMPLATE_HEADERS}
    item["secoes_visiveis"] = _json_cell(row.get("secoes_visiveis_json"), [])
    item["ordem_secoes"] = _json_cell(row.get("ordem_secoes_json"), [])
    item["imagens"] = _json_cell(row.get("imagens_json"), {})
    item["sections"] = _json_cell(row.get("secoes_json"), [])
    item["row_number"] = row_number
    errors = []
    if not item["administradora"]: errors.append("administradora obrigatória")
    if not item["slug"]: errors.append("slug obrigatório")
    if not item["status"]: errors.append("status obrigatório")
    if item["status"].lower() not in {"ativo", "inativo", "rascunho"}: errors.append("status deve ser Ativo, Inativo ou Rascunho")
    item["validation_errors"] = errors
    item["is_valid"] = not errors
    return item

def _read_rows() -> list[dict[str, Any]]:
    settings = get_settings()
    if not settings.google_sheets_id or not settings.google_service_account_json:
        raise RuntimeError("Google Sheets não configurado no ambiente.")
    result = get_service().spreadsheets().values().get(spreadsheetId=settings.google_sheets_id, range=f"'{TEMPLATES_SHEET_NAME}'!A:ZZ").execute()
    values = result.get("values", [])
    if not values: return []
    headers = [_clean(value) for value in values[0]]
    items = []
    for row_number, raw in enumerate(values[1:], start=2):
        if not any(_clean(cell) for cell in raw): continue
        row = {header: raw[index] if index < len(raw) else "" for index, header in enumerate(headers) if header}
        items.append(normalize_template(row, row_number))
    return items

def list_templates(force_reload: bool = False) -> list[dict[str, Any]]:
    now = time.time()
    with _cache_lock:
        if not force_reload and _cache["items"] is not None and now < _cache["expires_at"]:
            return copy.deepcopy(_cache["items"])
    items = _read_rows()
    if not any(item.get("is_valid") for item in items):
        items.append(copy.deepcopy(INITIAL_DRIVE_TEMPLATE))
    with _cache_lock:
        _cache["items"] = items
        _cache["expires_at"] = time.time() + CACHE_TTL_SECONDS
    return copy.deepcopy(items)

def get_template(slug: str, active_only: bool = True) -> dict[str, Any] | None:
    wanted = _clean(slug).lower()
    for item in list_templates():
        if item["slug"].lower() == wanted and (not active_only or item["status"].lower() == "ativo"):
            return item
    return None
