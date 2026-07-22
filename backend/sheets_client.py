import copy
import csv
import io
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
from googleapiclient.errors import HttpError

from .config import get_settings

logger = logging.getLogger("crediclass.sheets")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
CACHE_TTL_SECONDS = 300
METADATA_CACHE_TTL_SECONDS = 900
SHEETS_READ_ATTEMPTS = 3
MAX_CREDIT_VALUE = 100_000_000
_grupos_cache: dict[str, Any] = {
    "with_history": {"expires_at": 0.0, "items": None},
    "light": {"expires_at": 0.0, "items": None},
}
_grupos_detalhe_cache: dict[str, Any] = {"expires_at": 0.0, "items": None}
_grupos_defasagem_cache: dict[str, Any] = {"expires_at": 0.0, "items": None}
_sheet_rows_cache: dict[str, Any] = {"expires_at": 0.0, "rows": None}
_sheet_metadata_cache: dict[str, Any] = {"expires_at": 0.0, "headers": None}
_group_row_index: dict[str, int] = {}
_grupo_detail_cache: dict[str, tuple[float, dict[str, Any]]] = {}
_cache_lock = threading.RLock()
_detail_build_lock = threading.Lock()
_defasagem_warm_lock = threading.Lock()

SUMMARY_FIELDS = [
    "administradora",
    "grupo",
    "tipo_bem",
    "credito_minimo",
    "credito_maximo",
    "indexador",
    "taxa_adm",
    "fundo_reserva",
    "fundo_reserva_ano",
    "modalidades_assembleia",
    "base_calculo_embutido",
    "modalidades_embutido",
    "seguro_obrigatorio",
    "idade_maxima_seguro",
    "aliquota_seguro",
    "parcela_inicial_grupo",
    "parcela_apos_lance_grupo",
    "prazo_total",
    "prazo_restante",
    "taxa_adm_ano",
    "parcela_reduzida",
    "primeira_assembleia",
    "ultima_assembleia",
    "lance_embutido",
    "fgts",
    "percentual_lance_embutido",
    "percentual_lance_fixo",
    # BL:BP are the official historical thresholds used by Motor 360.
    "lance_investidor",
    "lance_conservador_24m",
    "lance_moderado_12m",
    "lance_agressivo_6m",
    "lance_super_agressivo_3m",
    "lance_super_conservador",
    "lance_conservador",
    "lance_moderado",
    "lance_agressivo",
    "lance_super_agressivo_3m",
    "lance_agressivo_6m",
    "lance_moderado_12m",
    "lance_conservador_24m",
    "status",
]

# The Itaú motor uses the column contract from the new group base.  These
# positions are intentionally explicit so a renamed sheet header cannot move
# a financial parameter to a different field silently.
MAPA_GRUPOS_COLUMN_INDEXES = {
    "administradora": 0,  # A
    "grupo": 1,  # B
    "tipo_bem": 2,  # C
    "prazo_restante": 5,  # F
    "seguro_obrigatorio": 11,  # L
    "idade_maxima_seguro": 12,  # M
    "aliquota_seguro": 13,  # N
    "credito_minimo": 14,  # O
    "credito_maximo": 20,  # U
    "indexador": 21,  # V
    "modalidades_assembleia": 22,  # W
    "percentual_lance_embutido": 23,  # X
    "base_calculo_embutido": 24,  # Y
    "modalidades_embutido": 25,  # Z
    "fundo_reserva": 26,  # AA
    "fundo_reserva_ano": 27,  # AB
    "taxa_adm": 28,  # AC
    "taxa_adm_ano": 29,  # AD
    "parcela_inicial_grupo": 35,  # AJ
    "parcela_apos_lance_grupo": 36,  # AK
    "parcela_reduzida": 37,  # AL
    "lance_investidor": 63,  # BL
    "lance_conservador_24m": 64,  # BM
    "lance_moderado_12m": 65,  # BN
    "lance_agressivo_6m": 66,  # BO
    "lance_super_agressivo_3m": 67,  # BP
}

MAPA_GRUPOS_FALLBACK_COLUMN_INDEXES: dict[str, int] = {}


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
        "id grupo",
        "id do grupo",
        "id de grupo",
        "id",
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
    "indexador": ["indexador"],
    "taxa_adm": ["taxa administracao", "taxa adm", "taxa adm original", "taxa de administracao", "taxa administrativa", "tx adm", "tx administracao"],
    "taxa_adm_ano": ["taxa administracao ao ano", "taxa adm ao ano", "taxa adm ano", "taxa anual administracao"],
    "fundo_reserva": ["fundo reserva", "fundo de reserva", "fundo rsv"],
    "fundo_reserva_ano": ["fundo reserva ao ano", "fundo rsv ao ano"],
    "modalidades_assembleia": ["assembleias modalidades", "modalidades assembleia", "permite participar do lance fixo fidelidade e livre"],
    "base_calculo_embutido": ["base calculo embutido", "calculo do embutido", "lance embutido calculo"],
    "modalidades_embutido": ["modalidades embutido", "permite utilizar em quais modalidades"],
    "seguro_obrigatorio": ["seguro obrigatorio"],
    "idade_maxima_seguro": ["idade maxima seguro", "idade maxima para seguro"],
    "aliquota_seguro": ["aliquota seguro", "aliquota seguro mensal sobre saldo devedor"],
    "parcela_inicial_grupo": ["parcela inicial"],
    "parcela_apos_lance_grupo": ["parcela apos lance", "parcela apos o lance"],
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
    "lance_super_conservador": ["lance super conservador", "super conservador", "s cons", "s conservador"],
    "lance_conservador": ["lance conservador", "conservador", "cons"],
    "lance_moderado": ["lance moderado", "moderado", "mod"],
    "lance_agressivo": ["lance agressivo", "agressivo", "agr"],
    "lance_investidor": ["lance investidor", "investidor"],
    "lance_super_agressivo_3m": ["lance super agressivo 3m", "super agressivo 3 meses"],
    "lance_agressivo_6m": ["lance agressivo 6m", "agressivo 6 meses"],
    "lance_moderado_12m": ["lance moderado 12m", "moderado 12 meses"],
    "lance_conservador_24m": ["lance conservador 24m", "conservador 24 meses"],
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


def execute_sheets_read(request_factory, operation: str) -> dict[str, Any]:
    """Execute a read request with a fresh Sheets client after transient failures."""
    last_error: Exception | None = None
    for attempt in range(1, SHEETS_READ_ATTEMPTS + 1):
        try:
            return request_factory().execute()
        except (AttributeError, OSError, TimeoutError, HttpError) as error:
            last_error = error
            is_server_error = isinstance(error, HttpError) and getattr(error.resp, "status", 0) >= 500
            is_transient = not isinstance(error, HttpError) or is_server_error
            if not is_transient or attempt == SHEETS_READ_ATTEMPTS:
                break
            logger.warning(
                "Falha temporaria ao %s na planilha (tentativa %s/%s): %s",
                operation,
                attempt,
                SHEETS_READ_ATTEMPTS,
                error,
            )
            get_service.cache_clear()
            time.sleep(0.25 * attempt)
    if last_error:
        raise last_error
    raise RuntimeError(f"Falha inesperada ao {operation} na planilha")


def clear_rows_cache() -> None:
    with _cache_lock:
        for cache in _grupos_cache.values():
            cache["expires_at"] = 0.0
            cache["items"] = None
        _grupos_detalhe_cache["expires_at"] = 0.0
        _grupos_detalhe_cache["items"] = None
        _grupos_defasagem_cache["expires_at"] = 0.0
        _grupos_defasagem_cache["items"] = None
        _sheet_rows_cache["expires_at"] = 0.0
        _sheet_rows_cache["rows"] = None
        _sheet_metadata_cache["expires_at"] = 0.0
        _sheet_metadata_cache["headers"] = None
        _group_row_index.clear()
        _grupo_detail_cache.clear()


def canonical_field_header(field: str) -> str:
    return f"__{field}"


def apply_mapa_grupos_fixed_columns(row: dict[str, Any], values: list[Any]) -> None:
    for field, index in MAPA_GRUPOS_COLUMN_INDEXES.items():
        row[canonical_field_header(field)] = fixed_column_value(field, values)


def fixed_column_value(field: str, values: list[Any], base_index: int = 0) -> Any:
    index = MAPA_GRUPOS_COLUMN_INDEXES[field] - base_index
    value = values[index] if 0 <= index < len(values) else ""
    if value in (None, "") and field in MAPA_GRUPOS_FALLBACK_COLUMN_INDEXES:
        fallback_index = MAPA_GRUPOS_FALLBACK_COLUMN_INDEXES[field] - base_index
        value = values[fallback_index] if 0 <= fallback_index < len(values) else ""
    return value


def read_sheet_headers(force_reload: bool = False) -> list[str]:
    now = time.time()
    with _cache_lock:
        headers = _sheet_metadata_cache["headers"]
        if not force_reload and headers is not None and now < _sheet_metadata_cache["expires_at"]:
            return list(headers)

        settings = get_settings()
        result = execute_sheets_read(
            lambda: get_service().spreadsheets().values().get(
                spreadsheetId=settings.google_sheets_id,
                range=f"'{settings.google_sheet_name}'!A1:ZZ1",
            ),
            "ler os cabecalhos",
        )
        values = result.get("values", [])
        headers = [str(header).strip() for header in (values[0] if values else [])]
        _sheet_metadata_cache["headers"] = headers
        _sheet_metadata_cache["expires_at"] = now + METADATA_CACHE_TTL_SECONDS
        return list(headers)


def read_summary_rows(force_reload: bool = False, include_history: bool = True) -> list[dict[str, Any]]:
    headers = read_sheet_headers(force_reload=force_reload)
    if not headers:
        return []

    selected: list[tuple[str, str, int]] = []
    header_positions = headers_index(headers)
    for field in SUMMARY_FIELDS:
        fixed_index = MAPA_GRUPOS_COLUMN_INDEXES.get(field)
        if fixed_index is not None:
            selected.append((field, canonical_field_header(field), fixed_index))
        else:
            header = find_header(headers, field)
            if header is None:
                continue
            index = header_positions[header]
            selected.append((field, header, index))
    selected_indexes = {index for _, _, index in selected}
    if include_history:
        for header, index in header_positions.items():
            if index in selected_indexes or not history_key_from_header(header):
                continue
            selected.append(("historico", header, index))
            selected_indexes.add(index)

    validate_required_headers(headers, ["administradora", "grupo", "tipo_bem"])
    settings = get_settings()
    rows: list[dict[str, Any]] = []
    row_index: dict[str, int] = {}

    if include_history:
        min_index = min(index for _, _, index in selected)
        max_index = max(index for _, _, index in selected)
        result = execute_sheets_read(
            lambda: get_service().spreadsheets().values().get(
                spreadsheetId=settings.google_sheets_id,
                range=f"'{settings.google_sheet_name}'!{column_letter(min_index)}2:{column_letter(max_index)}",
            ),
            "ler a base resumida",
        )
        values = result.get("values", [])
        for offset, row_values in enumerate(values):
            row: dict[str, Any] = {}
            for field, header, index in selected:
                relative_index = index - min_index
                row[header] = fixed_column_value(field, row_values, min_index) if field in MAPA_GRUPOS_COLUMN_INDEXES else row_values[relative_index] if relative_index < len(row_values) else ""
            if not any(str(value).strip() for value in row.values()):
                continue
            rows.append(row)
            grupo_id = build_grupo_id(row)
            if grupo_id:
                row_index[grupo_id.upper()] = offset + 2
    else:
        ranges = [
            f"'{settings.google_sheet_name}'!{column_letter(index)}2:{column_letter(index)}"
            for _, _, index in selected
        ]
        result = execute_sheets_read(
            lambda: get_service().spreadsheets().values().batchGet(
                spreadsheetId=settings.google_sheets_id,
                ranges=ranges,
            ),
            "ler a base resumida",
        )
        value_ranges = result.get("valueRanges", [])
        columns = [item.get("values", []) for item in value_ranges]
        row_count = max((len(column) for column in columns), default=0)

        for offset in range(row_count):
            row: dict[str, Any] = {}
            for (field, header, _), column in zip(selected, columns):
                cell = column[offset] if offset < len(column) else []
                value = cell[0] if cell else ""
                if value in (None, "") and field in MAPA_GRUPOS_FALLBACK_COLUMN_INDEXES:
                    fallback_header = canonical_field_header(field)
                    fallback_index = MAPA_GRUPOS_FALLBACK_COLUMN_INDEXES[field]
                    if fallback_header == header and fallback_index < len(columns):
                        fallback_cell = columns[fallback_index][offset] if offset < len(columns[fallback_index]) else []
                        value = fallback_cell[0] if fallback_cell else ""
                row[header] = value
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
        apply_mapa_grupos_fixed_columns(row_dict, row)
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


def export_sheet_csv() -> str:
    values = read_sheet_values()
    max_columns = max((len(row) for row in values), default=0)
    output = io.StringIO(newline="")
    writer = csv.writer(output, delimiter=";", lineterminator="\n")

    for row in values:
        normalized = [str(value) if value is not None else "" for value in row]
        normalized.extend([""] * (max_columns - len(normalized)))
        writer.writerow(normalized)

    return output.getvalue()


def find_header(headers: list[str], field: str) -> str | None:
    normalized = {normalize_header(header): header for header in headers}
    for alias in FIELD_ALIASES[field]:
        value = normalized.get(normalize_header(alias))
        if value is not None:
            return value
    return None


def headers_index(headers: list[str]) -> dict[str, int]:
    return {str(header): index for index, header in enumerate(headers)}


def field_name_for_header(header: str) -> str | None:
    normalized = normalize_header(header)
    for field, aliases in FIELD_ALIASES.items():
        if normalized in {normalize_header(alias) for alias in aliases}:
            return field
    return None


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

    raw_fields = payload.get("campos_planilha")
    if isinstance(raw_fields, dict):
        index_by_header = headers_index(headers)
        for header, value in raw_fields.items():
            header_name = str(header).strip()
            if not header_name or header_name not in index_by_header:
                continue
            if field_name_for_header(header_name) in {"administradora", "grupo"}:
                continue
            values[index_by_header[header_name]] = "" if value is None else str(value)
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
    canonical = row.get(canonical_field_header(field))
    if canonical_field_header(field) in row:
        return canonical
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
    text = "" if value is None else str(value).strip()
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


def history_month_has_full_update(item: dict[str, Any]) -> bool:
    return all(item.get(field) is not None for field in ("maior_lance", "menor_lance", "qtd_contemplacoes"))


def latest_updated_history_month(historico: dict[str, dict[str, Any]]) -> str | None:
    valid_months = [month for month, item in (historico or {}).items() if history_month_has_full_update(item)]
    return max(valid_months) if valid_months else None


def short_history_month_label(month_key: str | None) -> str:
    if not month_key:
        return "-"
    try:
        year, month = month_key.split("-")
        return f"{MONTH_ABBR_BY_NUMBER[month].capitalize()}-{year[-2:]}"
    except (ValueError, KeyError):
        return month_key


def history_last_12_rows(historico: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    months = sorted((month for month in (historico or {}) if re.fullmatch(r"\d{4}-\d{2}", str(month))))[-12:]
    return [
        {
            "mes": month,
            "label": short_history_month_label(month),
            "maior_lance": historico[month].get("maior_lance"),
            "menor_lance": historico[month].get("menor_lance"),
            "qtd_contemplacoes": historico[month].get("qtd_contemplacoes"),
            "atualizado": history_month_has_full_update(historico[month]),
        }
        for month in months
    ]


def build_grupo_id(row: dict[str, Any]) -> str:
    grupo = clean_text(get_field(row, "grupo")).upper().replace(" ", "-")
    return grupo


def build_administradora_id(row: dict[str, Any]) -> str:
    name = clean_text(get_field(row, "administradora"))
    normalized = unicodedata.normalize("NFKD", name)
    ascii_name = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return re.sub(r"[^A-Za-z0-9]+", "-", ascii_name).strip("-").upper()


def row_to_grupo(row: dict[str, Any]) -> dict[str, Any]:
    from .lance_reference import calculate_lance_references

    historico = build_historico(row)
    lance_references = calculate_lance_references(historico)
    lance_investidor = parse_percent(get_optional_field(row, "lance_investidor"))
    lance_conservador_24m = parse_percent(get_optional_field(row, "lance_conservador_24m"))
    lance_moderado_12m = parse_percent(get_optional_field(row, "lance_moderado_12m"))
    lance_agressivo_6m = parse_percent(get_optional_field(row, "lance_agressivo_6m"))
    lance_super_agressivo_3m = parse_percent(get_optional_field(row, "lance_super_agressivo_3m"))
    missing = [
        field for field in ("credito_minimo", "credito_maximo", "taxa_adm", "fundo_reserva")
        if get_field(row, field) in (None, "")
    ]
    origins = {
        "credito_minimo": "planilha",
        "credito_maximo": "planilha",
        "taxa_adm": "planilha",
        "fundo_reserva": "planilha",
        "prazo_remanescente": "planilha",
        "percentual_embutido": "planilha",
        "seguro_obrigatorio": "planilha",
        "indices_perfil": "planilha",
    }
    updated_month = latest_updated_history_month(historico)
    return {
        "grupo_id": build_grupo_id(row),
        "administradora_id": build_administradora_id(row),
        "administradora": clean_text(get_field(row, "administradora")),
        "grupo": clean_text(get_field(row, "grupo")),
        "tipo_bem": clean_text(get_field(row, "tipo_bem")),
        "credito_minimo": parse_credit(get_field(row, "credito_minimo")),
        "credito_maximo": parse_credit(get_field(row, "credito_maximo")),
        "indexador": clean_text(get_optional_field(row, "indexador")),
        "taxa_adm": parse_percent(get_field(row, "taxa_adm")),
        "taxa_adm_ano": parse_percent(get_optional_field(row, "taxa_adm_ano")),
        "fundo_reserva": parse_percent(get_optional_field(row, "fundo_reserva")),
        "fundo_reserva_ano": parse_percent(get_optional_field(row, "fundo_reserva_ano")),
        "modalidades_assembleia": clean_text(get_optional_field(row, "modalidades_assembleia")),
        "base_calculo_embutido": clean_text(get_optional_field(row, "base_calculo_embutido")),
        "modalidades_embutido": clean_text(get_optional_field(row, "modalidades_embutido")),
        "seguro_obrigatorio": parse_bool(get_optional_field(row, "seguro_obrigatorio")),
        "idade_maxima_seguro": parse_int(get_optional_field(row, "idade_maxima_seguro")),
        "aliquota_seguro": parse_percent(get_optional_field(row, "aliquota_seguro")),
        "parcela_inicial_grupo": parse_number(get_optional_field(row, "parcela_inicial_grupo")),
        "parcela_apos_lance_grupo": parse_number(get_optional_field(row, "parcela_apos_lance_grupo")),
        "parcela_reduzida": parse_number(get_optional_field(row, "parcela_reduzida")),
        "prazo_total": parse_int(get_field(row, "prazo_total")),
        "prazo_restante": parse_int(get_optional_field(row, "prazo_restante")),
        "atualizado": short_history_month_label(updated_month),
        "historico_12_meses": history_last_12_rows(historico),
        "primeira_assembleia": clean_text(get_field(row, "primeira_assembleia")),
        "ultima_assembleia": clean_text(get_field(row, "ultima_assembleia")),
        "status": clean_text(get_field(row, "status") or "Ativo"),
        "lance_embutido": parse_bool(get_optional_field(row, "lance_embutido")) if get_optional_field(row, "lance_embutido") not in (None, "") else bool(parse_percent(get_optional_field(row, "percentual_lance_embutido") or 0) > 0),
        "fgts": parse_bool(get_optional_field(row, "fgts")),
        "percentual_lance_embutido": parse_percent(get_optional_field(row, "percentual_lance_embutido")),
        "percentual_lance_fixo": parse_percent(get_optional_field(row, "percentual_lance_fixo")),
        "lance_investidor": lance_investidor,
        "lance_conservador_24m": lance_conservador_24m,
        "lance_moderado_12m": lance_moderado_12m,
        "lance_agressivo_6m": lance_agressivo_6m,
        "lance_super_agressivo_3m": lance_super_agressivo_3m,
        # Legacy aliases remain available to older consumers; the Itaú motor
        # uses the explicit 3/6/12/24 month fields above.
        "lance_super_conservador": lance_references["lance_super_conservador"],
        "lance_conservador": lance_references["lance_conservador"],
        "lance_moderado": lance_references["lance_moderado"],
        "lance_agressivo": lance_references["lance_agressivo"],
        "idade_maxima": parse_int(get_optional_field(row, "idade_maxima")) or parse_int(get_optional_field(row, "idade_maxima_seguro")),
        "dados_incompletos": missing,
        "origens": origins,
    }


def row_to_grupo_detalhe(row: dict[str, Any]) -> dict[str, Any]:
    from .lance_reference import calculate_lance_references

    detalhe = row_to_grupo(row)
    historico = build_historico(row)
    detalhe.update({
        "fundo_reserva": parse_percent(get_optional_field(row, "fundo_reserva")),
        "taxa_adm_ano": parse_percent(get_optional_field(row, "taxa_adm_ano")),
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
        "parcela_reduzida": parse_number(get_optional_field(row, "parcela_reduzida")),
        "percentual_parcela_reduzida": parse_percent(get_optional_field(row, "percentual_parcela_reduzida")),
        "idade_maxima": parse_int(get_optional_field(row, "idade_maxima")) or parse_int(get_optional_field(row, "idade_maxima_seguro")),
        "observacoes": clean_text(get_optional_field(row, "observacoes")),
        "indice_correcao": str(get_optional_field(row, "indice_correcao")),
        "vencimento_parcela": str(get_optional_field(row, "vencimento_parcela")),
        "vencimento_lance": str(get_optional_field(row, "vencimento_lance")),
        "regras_especiais": str(get_optional_field(row, "regras_especiais")),
        "cadastrado_por": str(get_optional_field(row, "cadastrado_por")),
        "ultima_atualizacao": str(get_optional_field(row, "ultima_atualizacao")),
        "campos_planilha": {str(header): "" if value is None else str(value) for header, value in row.items()},
        "historico": historico,
        "auditoria": [],
    })
    detalhe.update(calculate_lance_references(
        historico,
        detalhe.get("percentual_lance_fixo"),
    ))
    return detalhe


def list_grupos(include_history: bool = True) -> list[dict[str, Any]]:
    now = time.time()
    cache_key = "with_history" if include_history else "light"
    with _cache_lock:
        cache = _grupos_cache[cache_key]
        cached_items = cache["items"]
        if cached_items is not None and now < cache["expires_at"]:
            logger.info("Usando cache de grupos (%s)", cache_key)
            return list(cached_items)

    try:
        items = [row_to_grupo(row) for row in read_summary_rows(include_history=include_history)]
    except (AttributeError, OSError, TimeoutError, HttpError):
        if cached_items is None:
            raise
        logger.exception("Falha ao atualizar grupos; mantendo o ultimo cache valido (%s)", cache_key)
        return list(cached_items)
    with _cache_lock:
        cache = _grupos_cache[cache_key]
        cache["items"] = items
        cache["expires_at"] = time.time() + CACHE_TTL_SECONDS
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


def read_defasagem_rows() -> list[dict[str, Any]]:
    headers = read_sheet_headers()
    if not headers:
        return []

    selected_headers: list[tuple[str, int]] = []
    required_fields = ["administradora", "grupo", "tipo_bem", "status"]
    header_positions = headers_index(headers)
    for field in required_fields:
        header = find_header(headers, field)
        if header is not None:
            selected_headers.append((header, header_positions[header]))

    for index, header in enumerate(headers):
        if history_key_from_header(header):
            selected_headers.append((header, index))

    seen: set[str] = set()
    unique_headers: list[tuple[str, int]] = []
    for header, index in selected_headers:
        if header in seen:
            continue
        seen.add(header)
        unique_headers.append((header, index))

    settings = get_settings()
    ranges = [
        f"'{settings.google_sheet_name}'!{column_letter(index)}2:{column_letter(index)}"
        for _, index in unique_headers
    ]
    result = get_service().spreadsheets().values().batchGet(
        spreadsheetId=settings.google_sheets_id,
        ranges=ranges,
    ).execute()
    columns = [item.get("values", []) for item in result.get("valueRanges", [])]
    row_count = max((len(column) for column in columns), default=0)
    rows: list[dict[str, Any]] = []

    for offset in range(row_count):
        row: dict[str, Any] = {}
        for (header, _), column in zip(unique_headers, columns):
            cell = column[offset] if offset < len(column) else []
            row[header] = cell[0] if cell else ""
        if any(str(value).strip() for value in row.values()):
            rows.append(row)
    return rows


def list_grupos_defasagem() -> list[dict[str, Any]]:
    now = time.time()
    with _cache_lock:
        items = _grupos_defasagem_cache["items"]
        if items is not None and now < _grupos_defasagem_cache["expires_at"]:
            logger.info("Usando cache de defasagem de grupos")
            return copy.deepcopy(items)

    rows = read_defasagem_rows()
    items = []
    for row in rows:
        grupo = row_to_grupo(row)
        grupo["historico"] = build_historico(row)
        items.append(grupo)

    with _cache_lock:
        _grupos_defasagem_cache["items"] = items
        _grupos_defasagem_cache["expires_at"] = time.time() + CACHE_TTL_SECONDS
    return copy.deepcopy(items)


def get_cached_grupos_defasagem() -> list[dict[str, Any]] | None:
    now = time.time()
    with _cache_lock:
        items = _grupos_defasagem_cache["items"]
        if items is not None and now < _grupos_defasagem_cache["expires_at"]:
            return copy.deepcopy(items)
    return None


def warm_grupos_defasagem_cache_async() -> bool:
    settings = get_settings()
    if not settings.google_sheets_id or not settings.google_service_account_json:
        return False
    if get_cached_grupos_defasagem() is not None:
        return False
    if not _defasagem_warm_lock.acquire(blocking=False):
        return False

    def warm() -> None:
        try:
            list_grupos_defasagem()
        except Exception:
            logger.exception("Nao foi possivel aquecer o cache de defasagem")
        finally:
            _defasagem_warm_lock.release()

    threading.Thread(target=warm, name="warm-grupos-defasagem-cache", daemon=True).start()
    return True


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
            id_by_row = {row_number: wanted for wanted, row_number in row_numbers.items() if row_number is not None}
            blocks = row_blocks(sorted(id_by_row))
            ranges = [
                f"'{settings.google_sheet_name}'!A{start}:{last_column}{end}"
                for start, end in blocks
            ]
            if ranges:
                result = get_service().spreadsheets().values().batchGet(
                    spreadsheetId=settings.google_sheets_id,
                    ranges=ranges,
                ).execute()
                value_ranges = result.get("valueRanges", [])
                fetched_items: dict[str, dict[str, Any]] = {}
                for (start, _), value_range in zip(blocks, value_ranges):
                    values = value_range.get("values", [])
                    if not values:
                        continue
                    for offset, row in enumerate(values):
                        row_number = start + offset
                        wanted = id_by_row.get(row_number)
                        if not wanted:
                            continue
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


def row_blocks(row_numbers: list[int], max_gap: int = 2) -> list[tuple[int, int]]:
    if not row_numbers:
        return []
    blocks: list[tuple[int, int]] = []
    start = row_numbers[0]
    previous = row_numbers[0]
    for row_number in row_numbers[1:]:
        if row_number - previous <= max_gap + 1:
            previous = row_number
            continue
        blocks.append((start, previous))
        start = row_number
        previous = row_number
    blocks.append((start, previous))
    return blocks


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
