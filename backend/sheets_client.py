import json
import logging
import re
import time
import unicodedata
from functools import lru_cache
from typing import Any

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from .config import get_settings

logger = logging.getLogger("crediclass.sheets")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
CACHE_TTL_SECONDS = 300
_rows_cache: dict[str, Any] = {"expires_at": 0.0, "rows": None}
_grupos_cache: dict[str, Any] = {"source_expires_at": 0.0, "items": None}
_detalhes_cache: dict[str, Any] = {"source_expires_at": 0.0, "items": None}


def normalize_header(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-zA-Z0-9]+", " ", text).strip().lower()
    return re.sub(r"\s+", " ", text)


FIELD_ALIASES = {
    "administradora": ["administradora"],
    "grupo": ["grupo"],
    "tipo_bem": ["tipo de bem", "tipo bem"],
    "credito_minimo": ["credito minimo", "menor credito", "credito min"],
    "credito_maximo": ["credito maximo", "maior credito", "credito max"],
    "taxa_adm": ["taxa administracao", "taxa adm", "taxa de administracao"],
    "fundo_reserva": ["fundo reserva", "fundo de reserva"],
    "prazo_total": ["prazo total", "prazo do grupo", "prazo grupo"],
    "prazo_restante": ["prazo restante"],
    "primeira_assembleia": ["primeira assembleia", "1 assembleia", "1a assembleia"],
    "ultima_assembleia": ["ultima assembleia"],
    "data_termino": ["data termino", "data de termino", "termino"],
    "seguro_garantia": ["seguro garantia"],
    "meia_parcela": ["meia parcela"],
    "lance_embutido": ["lance embutido"],
    "fgts": ["fgts", "fgts permitido"],
    "categoria": ["categoria"],
    "percentual_lance_embutido": ["percentual lance embutido", "lance embutido percentual", "lance embutido maximo"],
    "percentual_lance_fixo": ["percentual lance fixo", "lance fixo"],
    "investidor": ["investidor"],
    "conservador": ["conservador"],
    "moderado": ["moderado"],
    "agressivo": ["agressivo"],
    "super_agressivo": ["super agressivo", "superagressivo"],
    "parcela_reduzida": ["parcela reduzida"],
    "indice_correcao": ["indice correcao", "indice de correcao"],
    "vencimento_parcela": ["vencimento parcela", "vencimento da parcela"],
    "vencimento_lance": ["vencimento lance", "vencimento do lance"],
    "regras_especiais": ["regras especiais"],
    "cadastrado_por": ["cadastrado por"],
    "ultima_atualizacao": ["ultima atualizacao", "ultima atualizacao em"],
    "status": ["status"],
}

MONTH_MAP = {
    "JAN": "01",
    "FEV": "02",
    "FEB": "02",
    "MAR": "03",
    "ABR": "04",
    "APR": "04",
    "MAI": "05",
    "MAY": "05",
    "JUN": "06",
    "JUL": "07",
    "AGO": "08",
    "AUG": "08",
    "SET": "09",
    "SEP": "09",
    "OUT": "10",
    "OCT": "10",
    "NOV": "11",
    "DEZ": "12",
    "DEC": "12",
}


@lru_cache
def get_service():
    settings = get_settings()
    if not settings.google_sheets_id:
        raise RuntimeError("GOOGLE_SHEETS_ID nao configurado")
    if not settings.google_service_account_json:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON nao configurado")

    credentials_info = json.loads(settings.google_service_account_json)
    credentials = Credentials.from_service_account_info(credentials_info, scopes=SCOPES)
    return build("sheets", "v4", credentials=credentials, cache_discovery=False)


def clear_rows_cache() -> None:
    _rows_cache["expires_at"] = 0.0
    _rows_cache["rows"] = None
    _grupos_cache["source_expires_at"] = 0.0
    _grupos_cache["items"] = None
    _detalhes_cache["source_expires_at"] = 0.0
    _detalhes_cache["items"] = None


def read_sheet_rows(force_reload: bool = False) -> list[dict[str, Any]]:
    now = time.time()
    if not force_reload and _rows_cache["rows"] is not None and now < _rows_cache["expires_at"]:
        logger.info("Usando cache da Google Sheets")
        return list(_rows_cache["rows"])

    settings = get_settings()
    logger.info("Lendo Google Sheets: %s", settings.google_sheet_name)
    result = get_service().spreadsheets().values().get(
        spreadsheetId=settings.google_sheets_id,
        range=f"'{settings.google_sheet_name}'!A:ZZ",
    ).execute()
    values = result.get("values", [])
    if not values:
        return []

    headers = values[0]
    rows = []
    for row in values[1:]:
        row_dict = {}
        for index, header in enumerate(headers):
            row_dict[str(header).strip()] = row[index] if index < len(row) else ""
        if any(str(value).strip() for value in row_dict.values()):
            rows.append(row_dict)

    _rows_cache["rows"] = rows
    _rows_cache["expires_at"] = now + CACHE_TTL_SECONDS
    return rows


def get_field(row: dict[str, Any], field: str) -> Any:
    normalized = {normalize_header(key): value for key, value in row.items()}
    for alias in FIELD_ALIASES[field]:
        value = normalized.get(normalize_header(alias))
        if value not in (None, ""):
            return value
    return ""


def get_optional_field(row: dict[str, Any], field: str) -> Any:
    if field not in FIELD_ALIASES:
        return ""
    return get_field(row, field)


def parse_number(value: Any) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    text = text.replace("R$", "").replace("%", "").replace(" ", "")
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def parse_int(value: Any) -> int | None:
    number = parse_number(value)
    if number is None:
        return None
    return int(number)


def parse_percent(value: Any) -> float | None:
    number = parse_number(value)
    if number is None:
        return None
    return number / 100 if number > 1 else number


def parse_bool(value: Any) -> bool | None:
    text = normalize_header(str(value or ""))
    if not text:
        return None
    if text in {"sim", "s", "true", "1", "ativo", "permitido"}:
        return True
    if text in {"nao", "n", "false", "0"}:
        return False
    return None


def history_key_from_header(header: str) -> tuple[str, str] | None:
    normalized = normalize_header(header).upper()
    match = re.search(r"\b([A-Z]{3})\s*(?:-|/|\s)?\s*(24|25|26)\b", normalized)
    if not match:
        return None

    month = MONTH_MAP.get(match.group(1))
    if not month:
        return None

    year = f"20{match.group(2)}"
    key = f"{year}-{month}"
    metric_header = normalize_header(header)
    if "maior lance" in metric_header:
        return key, "maior_lance"
    if "menor lance" in metric_header:
        return key, "menor_lance"
    if "qtd" in metric_header or "contemplac" in metric_header:
        return key, "qtd_contemplacoes"
    return None


def build_historico(row: dict[str, Any]) -> dict[str, dict[str, Any]]:
    historico: dict[str, dict[str, Any]] = {}
    for header, value in row.items():
        parsed = history_key_from_header(header)
        if not parsed:
            continue
        month_key, metric = parsed
        historico.setdefault(month_key, {"maior_lance": None, "menor_lance": None, "qtd_contemplacoes": None})
        if metric == "qtd_contemplacoes":
            historico[month_key][metric] = parse_int(value)
        else:
            historico[month_key][metric] = parse_percent(value)
    return dict(sorted(historico.items()))


def build_grupo_id(row: dict[str, Any]) -> str:
    administradora = str(get_field(row, "administradora")).strip().upper().replace(" ", "-")
    grupo = str(get_field(row, "grupo")).strip().upper().replace(" ", "-")
    tipo_bem = str(get_field(row, "tipo_bem")).strip().upper().replace(" ", "-")
    return "-".join(part for part in [administradora, grupo, tipo_bem] if part)


def row_to_grupo(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "grupo_id": build_grupo_id(row),
        "administradora": str(get_field(row, "administradora")),
        "grupo": str(get_field(row, "grupo")),
        "tipo_bem": str(get_field(row, "tipo_bem")),
        "credito_minimo": parse_number(get_field(row, "credito_minimo")),
        "credito_maximo": parse_number(get_field(row, "credito_maximo")),
        "taxa_adm": parse_percent(get_field(row, "taxa_adm")),
        "prazo_total": parse_int(get_field(row, "prazo_total")),
        "primeira_assembleia": str(get_field(row, "primeira_assembleia")),
        "ultima_assembleia": str(get_field(row, "ultima_assembleia")),
        "status": str(get_field(row, "status") or "Ativo"),
    }


def row_to_grupo_detalhe(row: dict[str, Any]) -> dict[str, Any]:
    detalhe = row_to_grupo(row)
    detalhe.update({
        "fundo_reserva": parse_percent(get_optional_field(row, "fundo_reserva")),
        "prazo_restante": parse_int(get_optional_field(row, "prazo_restante")),
        "data_termino": str(get_optional_field(row, "data_termino")),
        "seguro_garantia": parse_bool(get_optional_field(row, "seguro_garantia")),
        "meia_parcela": parse_bool(get_optional_field(row, "meia_parcela")),
        "lance_embutido": parse_bool(get_optional_field(row, "lance_embutido")),
        "fgts": parse_bool(get_optional_field(row, "fgts")),
        "categoria": str(get_optional_field(row, "categoria")),
        "percentual_lance_embutido": parse_percent(get_optional_field(row, "percentual_lance_embutido")),
        "percentual_lance_fixo": parse_percent(get_optional_field(row, "percentual_lance_fixo")),
        "investidor": parse_percent(get_optional_field(row, "investidor")),
        "conservador": parse_percent(get_optional_field(row, "conservador")),
        "moderado": parse_percent(get_optional_field(row, "moderado")),
        "agressivo": parse_percent(get_optional_field(row, "agressivo")),
        "super_agressivo": parse_percent(get_optional_field(row, "super_agressivo")),
        "parcela_reduzida": str(get_optional_field(row, "parcela_reduzida")),
        "indice_correcao": str(get_optional_field(row, "indice_correcao")),
        "vencimento_parcela": str(get_optional_field(row, "vencimento_parcela")),
        "vencimento_lance": str(get_optional_field(row, "vencimento_lance")),
        "regras_especiais": str(get_optional_field(row, "regras_especiais")),
        "cadastrado_por": str(get_optional_field(row, "cadastrado_por")),
        "ultima_atualizacao": str(get_optional_field(row, "ultima_atualizacao")),
        "historico": build_historico(row),
        "auditoria": [],
    })
    return detalhe


def list_grupos() -> list[dict[str, Any]]:
    if _grupos_cache["items"] is not None and _grupos_cache["source_expires_at"] == _rows_cache["expires_at"]:
        logger.info("Usando cache de grupos")
        return list(_grupos_cache["items"])

    items = [row_to_grupo(row) for row in read_sheet_rows()]
    _grupos_cache["items"] = items
    _grupos_cache["source_expires_at"] = _rows_cache["expires_at"]
    return items


def list_grupos_detalhe() -> list[dict[str, Any]]:
    if _detalhes_cache["items"] is not None and _detalhes_cache["source_expires_at"] == _rows_cache["expires_at"]:
        logger.info("Usando cache de detalhes dos grupos")
        return list(_detalhes_cache["items"])

    items = [row_to_grupo_detalhe(row) for row in read_sheet_rows()]
    _detalhes_cache["items"] = items
    _detalhes_cache["source_expires_at"] = _rows_cache["expires_at"]
    return items


def get_grupo(grupo_id: str) -> dict[str, Any] | None:
    wanted = grupo_id.strip().upper()
    for detalhe in list_grupos_detalhe():
        if detalhe["grupo_id"].upper() == wanted:
            return detalhe
    return None
