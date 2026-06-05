import copy
import json
import logging
import re
import threading
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
METADATA_CACHE_TTL_SECONDS = 900
MAX_CREDIT_VALUE = 100_000_000
_grupos_cache: dict[str, Any] = {"expires_at": 0.0, "items": None}
_grupos_detalhe_cache: dict[str, Any] = {"expires_at": 0.0, "items": None}
_sheet_rows_cache: dict[str, Any] = {"expires_at": 0.0, "rows": None}
_sheet_metadata_cache: dict[str, Any] = {"expires_at": 0.0, "headers": None}
_group_row_index: dict[str, int] = {}
_grupo_detail_cache: dict[str, tuple[float, dict[str, Any]]] = {}
_cache_lock = threading.RLock()
_detail_build_lock = threading.Lock()

SUMMARY_FIELDS = [
    "administradora",
    "grupo",
    "tipo_bem",
    "credito_minimo",
    "credito_maximo",
    "taxa_adm",
    "prazo_total",
    "primeira_assembleia",
    "ultima_assembleia",
    "status",
]


def normalize_header(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-zA-Z0-9]+", " ", text).strip().lower()
    return re.sub(r"\s+", " ", text)


def clean_text(value: Any) -> str:
    text = str(value or "").strip()
    if "Ã" in text or "Â" in text:
        try:
            return text.encode("latin1").decode("utf-8")
        except UnicodeError:
            return text
    return text


FIELD_ALIASES = {
    "administradora": [
        "adm",
        "administradora",
        "administradoras",
        "admin",
        "consorciadora",
        "operadora",
        "empresa",
        "banco",
        "instituicao financeira",
    ],
    "grupo": [
        "grupo",
        "grup0",
        "grupos",
        "numero grupo",
        "numero do grupo",
        "n grupo",
        "n do grupo",
        "no grupo",
        "codigo grupo",
        "codigo do grupo",
        "cod grupo",
        "grupo cota",
    ],
    "tipo_bem": ["tipo de bem", "tipo bem", "bem", "segmento", "categoria bem"],
    "credito_minimo": ["credito minimo", "menor credito", "credito min", "carta minima", "valor minimo"],
    "credito_maximo": ["credito maximo", "maior credito", "credito max", "carta maxima", "valor maximo"],
    "taxa_adm": ["taxa administracao", "taxa adm", "taxa adm original", "taxa de administracao", "taxa administrativa", "tx adm", "tx administracao"],
    "fundo_reserva": ["fundo reserva", "fundo de reserva", "fundo rsv"],
    "prazo_total": ["prazo total", "prazo do grupo", "prazo grupo"],
    "prazo_restante": ["prazo restante"],
    "primeira_assembleia": ["primeira assembleia", "1 assembleia", "1a assembleia"],
    "ultima_assembleia": ["ultima assembleia"],
    "data_termino": ["data termino", "data de termino", "termino"],
    "proxima_assembleia": ["proxima assembleia", "data proxima assembleia"],
    "limite_adesao": ["limite adesao", "limite de adesao", "data limite adesao"],
    "vencimento_primeira_parcela": [
        "vencimento primeira parcela",
        "vencimento da primeira parcela",
        "1 vencimento parcela",
        "1a parcela",
    ],
    "seguro_garantia": ["seguro garantia"],
    "meia_parcela": ["meia parcela", "meia reduzida"],
    "lance_embutido": ["lance embutido"],
    "fgts": ["fgts", "fgts permitido"],
    "categoria": ["categoria"],
    "percentual_lance_embutido": ["percentual lance embutido", "lance embutido percentual", "lance embutido maximo"],
    "percentual_lance_fixo": ["percentual lance fixo", "lance fixo", "lance quitacao"],
    "investidor": ["investidor"],
    "conservador": ["conservador"],
    "moderado": ["moderado"],
    "agressivo": ["agressivo"],
    "super_agressivo": ["super agressivo", "superagressivo"],
    "parcela_reduzida": ["parcela reduzida"],
    "percentual_parcela_reduzida": [
        "percentual parcela reduzida",
        "parcela reduzida percentual",
        "percentual de reducao da parcela",
    ],
    "idade_maxima": ["idade maxima", "limite idade", "idade limite"],
    "observacoes": ["observacoes", "observacao", "obs"],
    "indice_correcao": ["indice correcao", "indice de correcao"],
    "vencimento_parcela": ["vencimento parcela", "vencimento da parcela", "venc"],
    "vencimento_lance": ["vencimento lance", "vencimento do lance"],
    "regras_especiais": ["regras especiais"],
    "cadastrado_por": ["cadastrado por"],
    "ultima_atualizacao": ["ultima atualizacao", "ultima atualizacao em", "atualizacao de grupos", "data atualizacao"],
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

MONTH_ABBR_BY_NUMBER = {
    "01": "JAN",
    "02": "FEV",
    "03": "MAR",
    "04": "ABR",
    "05": "MAI",
    "06": "JUN",
    "07": "JUL",
    "08": "AGO",
    "09": "SET",
    "10": "OUT",
    "11": "NOV",
    "12": "DEZ",
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
    with _cache_lock:
        _grupos_cache["expires_at"] = 0.0
        _grupos_cache["items"] = None
        _grupos_detalhe_cache["expires_at"] = 0.0
        _grupos_detalhe_cache["items"] = None
        _sheet_rows_cache["expires_at"] = 0.0
        _sheet_rows_cache["rows"] = None
        _sheet_metadata_cache["expires_at"] = 0.0
        _sheet_metadata_cache["headers"] = None
        _group_row_index.clear()
        _grupo_detail_cache.clear()


def read_sheet_headers(force_reload: bool = False) -> list[str]:
    now = time.time()
    with _cache_lock:
        headers = _sheet_metadata_cache["headers"]
        if not force_reload and headers is not None and now < _sheet_metadata_cache["expires_at"]:
            return list(headers)

        settings = get_settings()
        result = get_service().spreadsheets().values().get(
            spreadsheetId=settings.google_sheets_id,
            range=f"'{settings.google_sheet_name}'!A1:ZZ1",
        ).execute()
        values = result.get("values", [])
        headers = [str(header).strip() for header in (values[0] if values else [])]
        _sheet_metadata_cache["headers"] = headers
        _sheet_metadata_cache["expires_at"] = now + METADATA_CACHE_TTL_SECONDS
        return list(headers)


def read_summary_rows(force_reload: bool = False) -> list[dict[str, Any]]:
    headers = read_sheet_headers(force_reload=force_reload)
    if not headers:
        return []

    selected: list[tuple[str, str, int]] = []
    header_positions = headers_index(headers)
    for field in SUMMARY_FIELDS:
        header = find_header(headers, field)
        if header is None:
            continue
        index = header_positions[header]
        selected.append((field, header, index))

    validate_required_headers(headers, ["administradora", "grupo", "tipo_bem"])
    settings = get_settings()
    ranges = [
        f"'{settings.google_sheet_name}'!{column_letter(index)}2:{column_letter(index)}"
        for _, _, index in selected
    ]
    result = get_service().spreadsheets().values().batchGet(
        spreadsheetId=settings.google_sheets_id,
        ranges=ranges,
    ).execute()
    value_ranges = result.get("valueRanges", [])
    columns = [item.get("values", []) for item in value_ranges]
    row_count = max((len(column) for column in columns), default=0)
    rows: list[dict[str, Any]] = []
    row_index: dict[str, int] = {}

    for offset in range(row_count):
        row: dict[str, Any] = {}
        for (_, header, _), column in zip(selected, columns):
            cell = column[offset] if offset < len(column) else []
            row[header] = cell[0] if cell else ""
        if not any(str(value).strip() for value in row.values()):
            continue
        rows.append(row)
        grupo_id = build_grupo_id(row)
        if grupo_id:
            row_index[grupo_id.upper()] = offset + 2

    with _cache_lock:
        _group_row_index.clear()
        _group_row_index.update(row_index)
    return rows


def read_sheet_rows(force_reload: bool = False) -> list[dict[str, Any]]:
    now = time.time()
    with _cache_lock:
        cached_rows = _sheet_rows_cache["rows"]
        if not force_reload and cached_rows is not None and now < _sheet_rows_cache["expires_at"]:
            logger.info("Usando cache de linhas completas da planilha")
            return copy.deepcopy(cached_rows)

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

    with _cache_lock:
        _sheet_rows_cache["rows"] = rows
        _sheet_rows_cache["expires_at"] = time.time() + CACHE_TTL_SECONDS
    return copy.deepcopy(rows)


def read_sheet_values() -> list[list[Any]]:
    settings = get_settings()
    result = get_service().spreadsheets().values().get(
        spreadsheetId=settings.google_sheets_id,
        range=f"'{settings.google_sheet_name}'!A:ZZ",
    ).execute()
    return result.get("values", [])


def find_header(headers: list[str], field: str) -> str | None:
    normalized = {normalize_header(header): header for header in headers}
    for alias in FIELD_ALIASES[field]:
        value = normalized.get(normalize_header(alias))
        if value is not None:
            return value
    return None


def headers_index(headers: list[str]) -> dict[str, int]:
    return {str(header): index for index, header in enumerate(headers)}


def column_letter(index: int) -> str:
    number = index + 1
    letters = ""
    while number:
        number, remainder = divmod(number - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def format_sheet_value(field: str, value: Any) -> str:
    if value is None:
        return ""
    if field in {
        "taxa_adm",
        "fundo_reserva",
        "percentual_lance_embutido",
        "percentual_lance_fixo",
        "percentual_parcela_reduzida",
    }:
        return format_decimal_value(float(value) * 100, minimum_decimals=1)
    if isinstance(value, float):
        return str(value).replace(".", ",")
    return str(value)


def format_decimal_value(value: float, minimum_decimals: int = 0, maximum_decimals: int = 8) -> str:
    text = f"{round(float(value), maximum_decimals):.{maximum_decimals}f}".rstrip("0").rstrip(".")
    if minimum_decimals:
        integer, separator, decimals = text.partition(".")
        text = f"{integer}.{decimals.ljust(minimum_decimals, '0')}" if separator else f"{integer}.{''.ljust(minimum_decimals, '0')}"
    return text.replace(".", ",")


def payload_to_row_values(headers: list[str], payload: dict[str, Any], existing: list[Any] | None = None) -> list[Any]:
    values = list(existing or [])
    while len(values) < len(headers):
        values.append("")

    for field, value in payload.items():
        if value is None or field not in FIELD_ALIASES:
            continue
        header = find_header(headers, field)
        if header is None:
            continue
        values[headers_index(headers)[header]] = format_sheet_value(field, value)
    return values


def validate_required_headers(headers: list[str], fields: list[str]) -> None:
    missing = [field for field in fields if find_header(headers, field) is None]
    if missing:
        raise RuntimeError(f"Cabecalhos obrigatorios ausentes: {', '.join(missing)}")


def find_group_row(values: list[list[Any]], grupo_id: str) -> tuple[int, list[Any]] | None:
    if not values:
        return None
    headers = [str(header).strip() for header in values[0]]
    wanted = grupo_id.strip().upper()
    for row_number, row in enumerate(values[1:], start=2):
        row_dict = {header: row[index] if index < len(row) else "" for index, header in enumerate(headers)}
        if build_grupo_id(row_dict).upper() == wanted:
            return row_number, row
    return None


def create_grupo(payload: dict[str, Any]) -> dict[str, Any]:
    values = read_sheet_values()
    if not values:
        raise RuntimeError("Planilha sem cabecalhos")
    headers = [str(header).strip() for header in values[0]]

    row_payload = {**payload, "status": payload.get("status") or "Ativo"}
    row_values = payload_to_row_values(headers, row_payload)
    settings = get_settings()
    get_service().spreadsheets().values().append(
        spreadsheetId=settings.google_sheets_id,
        range=f"'{settings.google_sheet_name}'!A:ZZ",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": [row_values]},
    ).execute()
    clear_rows_cache()
    return {"success": True, "grupo_id": build_grupo_id(dict(zip(headers, row_values)))}


def update_grupo(grupo_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    values = read_sheet_values()
    if not values:
        raise RuntimeError("Planilha sem cabecalhos")
    headers = [str(header).strip() for header in values[0]]
    found = find_group_row(values, grupo_id)
    if not found:
        raise KeyError("Grupo nao encontrado")

    row_number, current_row = found
    updated_values = payload_to_row_values(headers, payload, current_row)
    settings = get_settings()
    get_service().spreadsheets().values().update(
        spreadsheetId=settings.google_sheets_id,
        range=f"'{settings.google_sheet_name}'!A{row_number}:ZZ{row_number}",
        valueInputOption="USER_ENTERED",
        body={"values": [updated_values]},
    ).execute()
    clear_rows_cache()
    return {"success": True}


def delete_grupo(grupo_id: str) -> dict[str, Any]:
    update_grupo(grupo_id, {"status": "Excluido"})
    return {"success": True, "status": "Excluido"}


def find_history_headers(headers: list[str], month_key: str) -> dict[str, str]:
    wanted = {
        "maior_lance": None,
        "menor_lance": None,
        "qtd_contemplacoes": None,
    }
    for header in headers:
        parsed = history_key_from_header(header)
        if not parsed:
            continue
        parsed_month, metric = parsed
        if parsed_month == month_key and metric in wanted:
            wanted[metric] = header

    return {metric: header for metric, header in wanted.items() if header}


def history_label_from_key(month_key: str) -> str:
    if len(month_key) == 7 and "-" in month_key:
        year, month = month_key.split("-")
        return f"{MONTH_ABBR_BY_NUMBER.get(month, month)}-{year[-2:]}"
    return month_key


def history_header_name(month_key: str, metric: str) -> str:
    metric_label = {
        "maior_lance": "Maior Lance",
        "menor_lance": "Menor Lance",
        "qtd_contemplacoes": "Qtd Contemplacoes",
    }[metric]
    return f"{history_label_from_key(month_key)} {metric_label}"


def ensure_history_headers(headers: list[str], month_key: str, metrics: list[str]) -> tuple[list[str], dict[str, str], bool]:
    history_headers = find_history_headers(headers, month_key)
    updated_headers = list(headers)
    changed = False

    for metric in metrics:
        if metric in history_headers:
            continue
        new_header = history_header_name(month_key, metric)
        updated_headers.append(new_header)
        history_headers[metric] = new_header
        changed = True

    return updated_headers, history_headers, changed


def format_history_value(metric: str, value: Any) -> str:
    if value is None:
        return ""
    if metric in {"maior_lance", "menor_lance"}:
        return format_decimal_value(float(value) * 100, minimum_decimals=1)
    return str(int(value))


def history_updates_for_payload(headers: list[str], row_number: int, payload: dict[str, Any], sheet_name: str) -> tuple[list[str], list[dict[str, Any]], str]:
    month_key = str(payload.get("mes") or "")
    sent_metrics = [metric for metric in ("maior_lance", "menor_lance", "qtd_contemplacoes") if metric in payload]
    if not sent_metrics:
        raise RuntimeError("Nenhum campo de historico enviado")
    headers, history_headers, headers_changed = ensure_history_headers(headers, month_key, sent_metrics)
    index_by_header = headers_index(headers)
    updates = []

    if headers_changed:
        for metric in sent_metrics:
            header = history_headers[metric]
            col = column_letter(index_by_header[header])
            updates.append({
                "range": f"'{sheet_name}'!{col}1",
                "values": [[header]],
            })

    for metric in sent_metrics:
        header = history_headers[metric]
        col = column_letter(index_by_header[header])
        updates.append({
            "range": f"'{sheet_name}'!{col}{row_number}",
            "values": [[format_history_value(metric, payload[metric])]],
        })
    return headers, updates, month_key


def update_historico_mensal(grupo_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    values = read_sheet_values()
    if not values:
        raise RuntimeError("Planilha sem cabecalhos")
    headers = [str(header).strip() for header in values[0]]
    found = find_group_row(values, grupo_id)
    if not found:
        raise KeyError("Grupo nao encontrado")

    settings = get_settings()
    row_number, _ = found
    _, updates, month_key = history_updates_for_payload(headers, row_number, payload, settings.google_sheet_name)

    get_service().spreadsheets().values().batchUpdate(
        spreadsheetId=settings.google_sheets_id,
        body={"valueInputOption": "USER_ENTERED", "data": updates},
    ).execute()
    clear_rows_cache()
    return {"success": True, "mes": month_key}


def update_historico_mensal_lote(grupo_id: str, payloads: list[dict[str, Any]]) -> dict[str, Any]:
    if not payloads:
        raise RuntimeError("Nenhum historico enviado")
    values = read_sheet_values()
    if not values:
        raise RuntimeError("Planilha sem cabecalhos")
    headers = [str(header).strip() for header in values[0]]
    found = find_group_row(values, grupo_id)
    if not found:
        raise KeyError("Grupo nao encontrado")

    settings = get_settings()
    row_number, _ = found
    updates = []
    months = []
    for payload in payloads:
        headers, payload_updates, month_key = history_updates_for_payload(headers, row_number, payload, settings.google_sheet_name)
        updates.extend(payload_updates)
        months.append(month_key)

    get_service().spreadsheets().values().batchUpdate(
        spreadsheetId=settings.google_sheets_id,
        body={"valueInputOption": "USER_ENTERED", "data": updates},
    ).execute()
    clear_rows_cache()
    return {"success": True, "meses": months}


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


def parse_credit(value: Any) -> float | None:
    number = parse_number(value)
    if number is None or number > MAX_CREDIT_VALUE:
        return None
    return number


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
    match = re.search(r"\b([A-Z]{3})\s*(?:-|/|\s)?\s*(\d{2})\b", normalized)
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
    grupo = clean_text(get_field(row, "grupo")).upper().replace(" ", "-")
    return grupo


def build_administradora_id(row: dict[str, Any]) -> str:
    name = clean_text(get_field(row, "administradora"))
    normalized = unicodedata.normalize("NFKD", name)
    ascii_name = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return re.sub(r"[^A-Za-z0-9]+", "-", ascii_name).strip("-").upper()


def row_to_grupo(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "grupo_id": build_grupo_id(row),
        "administradora_id": build_administradora_id(row),
        "administradora": clean_text(get_field(row, "administradora")),
        "grupo": clean_text(get_field(row, "grupo")),
        "tipo_bem": clean_text(get_field(row, "tipo_bem")),
        "credito_minimo": parse_credit(get_field(row, "credito_minimo")),
        "credito_maximo": parse_credit(get_field(row, "credito_maximo")),
        "taxa_adm": parse_percent(get_field(row, "taxa_adm")),
        "prazo_total": parse_int(get_field(row, "prazo_total")),
        "primeira_assembleia": clean_text(get_field(row, "primeira_assembleia")),
        "ultima_assembleia": clean_text(get_field(row, "ultima_assembleia")),
        "status": clean_text(get_field(row, "status") or "Ativo"),
    }


def row_to_grupo_detalhe(row: dict[str, Any]) -> dict[str, Any]:
    from .lance_reference import calculate_lance_references

    detalhe = row_to_grupo(row)
    historico = build_historico(row)
    detalhe.update({
        "fundo_reserva": parse_percent(get_optional_field(row, "fundo_reserva")),
        "prazo_restante": parse_int(get_optional_field(row, "prazo_restante")),
        "data_termino": str(get_optional_field(row, "data_termino")),
        "proxima_assembleia": clean_text(get_optional_field(row, "proxima_assembleia")),
        "limite_adesao": clean_text(get_optional_field(row, "limite_adesao")),
        "vencimento_primeira_parcela": clean_text(get_optional_field(row, "vencimento_primeira_parcela")),
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
        "percentual_parcela_reduzida": parse_percent(get_optional_field(row, "percentual_parcela_reduzida")),
        "idade_maxima": parse_int(get_optional_field(row, "idade_maxima")),
        "observacoes": clean_text(get_optional_field(row, "observacoes")),
        "indice_correcao": str(get_optional_field(row, "indice_correcao")),
        "vencimento_parcela": str(get_optional_field(row, "vencimento_parcela")),
        "vencimento_lance": str(get_optional_field(row, "vencimento_lance")),
        "regras_especiais": str(get_optional_field(row, "regras_especiais")),
        "cadastrado_por": str(get_optional_field(row, "cadastrado_por")),
        "ultima_atualizacao": str(get_optional_field(row, "ultima_atualizacao")),
        "historico": historico,
        "auditoria": [],
    })
    detalhe.update(calculate_lance_references(
        historico,
        detalhe.get("percentual_lance_fixo"),
    ))
    return detalhe


def list_grupos() -> list[dict[str, Any]]:
    now = time.time()
    with _cache_lock:
        if _grupos_cache["items"] is not None and now < _grupos_cache["expires_at"]:
            logger.info("Usando cache de grupos")
            return list(_grupos_cache["items"])

        items = [row_to_grupo(row) for row in read_summary_rows()]
        _grupos_cache["items"] = items
        _grupos_cache["expires_at"] = time.time() + CACHE_TTL_SECONDS
        return list(items)


def list_grupos_detalhe() -> list[dict[str, Any]]:
    now = time.time()
    with _cache_lock:
        items = _grupos_detalhe_cache["items"]
        if items is not None and now < _grupos_detalhe_cache["expires_at"]:
            logger.info("Usando cache de grupos detalhados")
            return copy.deepcopy(items)

    with _detail_build_lock:
        now = time.time()
        with _cache_lock:
            items = _grupos_detalhe_cache["items"]
            if items is not None and now < _grupos_detalhe_cache["expires_at"]:
                logger.info("Usando cache de grupos detalhados")
                return copy.deepcopy(items)

        items = [row_to_grupo_detalhe(row) for row in read_sheet_rows()]
        with _cache_lock:
            _grupos_detalhe_cache["items"] = items
            _grupos_detalhe_cache["expires_at"] = time.time() + CACHE_TTL_SECONDS
        return copy.deepcopy(items)


def list_grupos_detalhe_by_ids(grupo_ids: list[str]) -> list[dict[str, Any]]:
    wanted_ids = [str(grupo_id or "").strip().upper() for grupo_id in grupo_ids if str(grupo_id or "").strip()]
    if not wanted_ids:
        return []

    now = time.time()
    cached_items: dict[str, dict[str, Any]] = {}
    missing_ids: list[str] = []
    with _cache_lock:
        for wanted in wanted_ids:
            cached = _grupo_detail_cache.get(wanted)
            if cached and now < cached[0]:
                cached_items[wanted] = cached[1]
            else:
                missing_ids.append(wanted)

    if missing_ids:
        list_grupos()
        with _cache_lock:
            row_numbers = {wanted: _group_row_index.get(wanted) for wanted in missing_ids}

        headers = read_sheet_headers()
        if headers:
            settings = get_settings()
            last_column = column_letter(len(headers) - 1)
            ranges = [
                f"'{settings.google_sheet_name}'!A{row_number}:{last_column}{row_number}"
                for row_number in row_numbers.values()
                if row_number is not None
            ]
            if ranges:
                result = get_service().spreadsheets().values().batchGet(
                    spreadsheetId=settings.google_sheets_id,
                    ranges=ranges,
                ).execute()
                value_ranges = result.get("valueRanges", [])
                fetched_items: dict[str, dict[str, Any]] = {}
                for value_range in value_ranges:
                    values = value_range.get("values", [])
                    if not values:
                        continue
                    row = values[0]
                    row_dict = {header: row[index] if index < len(row) else "" for index, header in enumerate(headers)}
                    item = row_to_grupo_detalhe(row_dict)
                    fetched_items[item["grupo_id"].upper()] = item

                with _cache_lock:
                    for wanted, item in fetched_items.items():
                        if len(_grupo_detail_cache) >= 64:
                            oldest_key = min(_grupo_detail_cache, key=lambda key: _grupo_detail_cache[key][0])
                            _grupo_detail_cache.pop(oldest_key, None)
                        _grupo_detail_cache[wanted] = (time.time() + CACHE_TTL_SECONDS, item)
                cached_items.update(fetched_items)

    return [copy.deepcopy(cached_items[wanted]) for wanted in wanted_ids if wanted in cached_items]


def warm_grupos_detalhe_cache_async() -> None:
    def warm() -> None:
        try:
            total = len(list_grupos_detalhe())
            logger.info("Cache de grupos detalhados aquecido total=%s", total)
        except Exception:
            logger.exception("Nao foi possivel aquecer o cache de grupos detalhados")

    threading.Thread(target=warm, name="warm-grupos-detalhe-cache", daemon=True).start()


def get_grupo(grupo_id: str, _retry_on_stale_index: bool = True) -> dict[str, Any] | None:
    wanted = grupo_id.strip().upper()
    now = time.time()
    with _cache_lock:
        cached = _grupo_detail_cache.get(wanted)
        if cached and now < cached[0]:
            logger.info("Usando cache de detalhes do grupo %s", wanted)
            return copy.deepcopy(cached[1])

        row_number = _group_row_index.get(wanted)
        if row_number is None:
            list_grupos()
            row_number = _group_row_index.get(wanted)
    if row_number is None:
        return None

    headers = read_sheet_headers()
    if not headers:
        return None
    settings = get_settings()
    last_column = column_letter(len(headers) - 1)
    result = get_service().spreadsheets().values().get(
        spreadsheetId=settings.google_sheets_id,
        range=f"'{settings.google_sheet_name}'!A{row_number}:{last_column}{row_number}",
    ).execute()
    values = result.get("values", [])
    if not values:
        return None
    row = values[0]
    row_dict = {header: row[index] if index < len(row) else "" for index, header in enumerate(headers)}
    item = row_to_grupo_detalhe(row_dict)
    if item["grupo_id"].upper() != wanted:
        if not _retry_on_stale_index:
            return None
        clear_rows_cache()
        return get_grupo(grupo_id, _retry_on_stale_index=False)

    with _cache_lock:
        if len(_grupo_detail_cache) >= 32:
            oldest_key = min(_grupo_detail_cache, key=lambda key: _grupo_detail_cache[key][0])
            _grupo_detail_cache.pop(oldest_key, None)
        _grupo_detail_cache[wanted] = (time.time() + CACHE_TTL_SECONDS, item)
    return copy.deepcopy(item)
