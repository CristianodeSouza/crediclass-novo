"""Google Sheets persistence for immutable approved financial-study snapshots."""

from __future__ import annotations

import base64
import json
import zlib
from datetime import datetime, timezone
from uuid import UUID

from .config import get_settings
from .sheets_client import column_letter, get_service, normalize_header


# Keep this byte-for-byte aligned with the existing Google Sheets tab title.
SHEET_NAME = "Historico de Estudos"
ARCHIVE_LIMIT = 45_000  # Google Sheets limits a single cell to 50,000 characters.
REQUIRED_COLUMNS = {
    "study_id": ("estudo id", "study id", "estudo"),
    "created_at": ("criado em", "created at", "data estudo"),
    "status": ("status",),
    "operator": ("operador", "approved by"),
    "group_ids": ("grupo id", "grupo ids", "grupos"),
    "client_name": ("cliente nome", "nome cliente", "client name"),
    "administrator": ("administradora", "administrator"),
}
ARCHIVE_COLUMNS = {
    "group_count": "financial_study_group_count",
    "approval_key": "financial_study_approval_key",
    "archive": "financial_study_archive_v1",
}


def _quoted_sheet() -> str:
    return "'" + SHEET_NAME.replace("'", "''") + "'"


def _headers() -> tuple[list[str], dict[str, int]]:
    settings = get_settings()
    response = get_service().spreadsheets().values().get(
        spreadsheetId=settings.google_sheets_id,
        range=f"{_quoted_sheet()}!A1:ZZ1",
    ).execute()
    values = response.get("values", [])
    headers = [str(value).strip() for value in (values[0] if values else [])]
    if not headers or not any(headers):
        raise RuntimeError(f"A aba {SHEET_NAME!r} não foi encontrada ou não tem cabeçalho.")
    indexes = {normalize_header(header): index for index, header in enumerate(headers) if header}
    for field, aliases in REQUIRED_COLUMNS.items():
        if not any(normalize_header(alias) in indexes for alias in aliases):
            raise RuntimeError(f"A coluna obrigatória de {field} não foi encontrada na aba {SHEET_NAME!r}.")
    return headers, indexes


def _ensure_archive_columns(headers: list[str], indexes: dict[str, int]) -> tuple[list[str], dict[str, int]]:
    missing = [name for name in ARCHIVE_COLUMNS.values() if normalize_header(name) not in indexes]
    if not missing:
        return headers, indexes
    settings = get_settings()
    first_column = len(headers) + 1
    last_column = first_column + len(missing) - 1
    get_service().spreadsheets().values().update(
        spreadsheetId=settings.google_sheets_id,
        range=f"{_quoted_sheet()}!{column_letter(first_column - 1)}1:{column_letter(last_column - 1)}1",
        valueInputOption="RAW",
        body={"values": [missing]},
    ).execute()
    headers.extend(missing)
    indexes.update({normalize_header(name): len(headers) - len(missing) + offset for offset, name in enumerate(missing)})
    return headers, indexes


def _index(indexes: dict[str, int], field: str) -> int:
    aliases = REQUIRED_COLUMNS.get(field)
    if aliases:
        for alias in aliases:
            found = indexes.get(normalize_header(alias))
            if found is not None:
                return found
    found = indexes.get(normalize_header(ARCHIVE_COLUMNS.get(field, field)))
    if found is None:
        raise RuntimeError(f"Coluna {field!r} não encontrada na aba de Histórico de Estudos.")
    return found


def _optional_index(indexes: dict[str, int], field: str) -> int | None:
    return indexes.get(normalize_header(ARCHIVE_COLUMNS.get(field, field)))


def _read_column(index: int) -> list[list[str]]:
    settings = get_settings()
    column = column_letter(index)
    result = get_service().spreadsheets().values().get(
        spreadsheetId=settings.google_sheets_id,
        range=f"{_quoted_sheet()}!{column}2:{column}",
    ).execute()
    return result.get("values", [])


def _compress_archive(snapshot: dict, document_html: str, app_version: str) -> str:
    content = json.dumps({"snapshot": snapshot, "document_html": document_html, "app_version": app_version}, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    encoded = "gz1:" + base64.b64encode(zlib.compress(content, level=9)).decode("ascii")
    if len(encoded) > ARCHIVE_LIMIT:
        raise ValueError("O snapshot compactado excede o limite de armazenamento de uma célula do Google Sheets.")
    return encoded


def _decompress_archive(value: str) -> dict | None:
    if not value:
        return None
    if not value.startswith("gz1:"):
        raise RuntimeError("O snapshot arquivado usa um formato desconhecido.")
    raw = zlib.decompress(base64.b64decode(value[4:]))
    return json.loads(raw.decode("utf-8"))


def create_study(*, client_name: str, approved_by: str, app_version: str, snapshot: dict, document_html: str, approval_key: str) -> dict:
    try:
        approval_key = UUID(approval_key).hex
    except (ValueError, AttributeError):
        raise ValueError("A chave de aprovação do estudo é inválida.") from None
    client_name = client_name.strip()
    if not client_name:
        raise ValueError("Informe o nome do cliente para aprovar o estudo.")
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get("groups"), list) or not snapshot["groups"]:
        raise ValueError("O estudo precisa conter ao menos um grupo selecionado.")
    archive = _compress_archive(snapshot, document_html, app_version)
    settings = get_settings()
    headers, indexes = _headers()
    headers, indexes = _ensure_archive_columns(headers, indexes)

    key_column = _index(indexes, "approval_key")
    existing_keys = _read_column(key_column)
    for row_number, row in enumerate(existing_keys, start=2):
        if row and str(row[0]).strip() == approval_key:
            row_values = get_service().spreadsheets().values().get(
                spreadsheetId=settings.google_sheets_id,
                range=f"{_quoted_sheet()}!A{row_number}:ZZ{row_number}",
            ).execute().get("values", [[]])[0]
            return {
                "id": str(row_values[_index(indexes, "study_id")] or ""),
                "client_name": client_name,
                "approved_at": str(row_values[_index(indexes, "created_at")] or ""),
                "approved_by": str(row_values[_index(indexes, "operator")] or ""),
                "app_version": app_version,
            }

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    study_id = f"EF-{now[:10].replace('-', '')}-{approval_key[:10].upper()}"
    groups = snapshot["groups"]
    group_ids = list(dict.fromkeys(str(group.get("group") or group.get("group_key") or "").strip() for group in groups))
    administrators = list(dict.fromkeys(str(group.get("administrator") or "").strip() for group in groups if str(group.get("administrator") or "").strip()))
    values = [""] * len(headers)
    field_values = {
        "study_id": study_id,
        "created_at": now,
        "status": "Aprovado",
        "operator": approved_by,
        "group_ids": ", ".join(group_id for group_id in group_ids if group_id),
        "client_name": client_name,
        "administrator": ", ".join(administrators),
        "group_count": str(len(groups)),
        "approval_key": approval_key,
        "archive": archive,
    }
    for field, value in field_values.items():
        values[_index(indexes, field)] = value
    get_service().spreadsheets().values().append(
        spreadsheetId=settings.google_sheets_id,
        range=f"{_quoted_sheet()}!A:ZZ",
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values": [values]},
    ).execute()
    return {"id": study_id, "client_name": client_name, "approved_at": now, "approved_by": approved_by, "app_version": app_version}


def list_studies(*, query: str = "", limit: int = 100) -> list[dict]:
    _, indexes = _headers()
    fields = ["study_id", "created_at", "status", "operator", "client_name", "administrator", "group_count", "archive"]
    field_indexes = {field: (_optional_index(indexes, field) if field in ARCHIVE_COLUMNS else _index(indexes, field)) for field in fields}
    readable_fields = [field for field in fields if field_indexes[field] is not None]
    ranges = [f"{_quoted_sheet()}!{column_letter(field_indexes[field])}2:{column_letter(field_indexes[field])}" for field in readable_fields]
    settings = get_settings()
    response = get_service().spreadsheets().values().batchGet(spreadsheetId=settings.google_sheets_id, ranges=ranges).execute()
    columns = {field: value.get("values", []) for field, value in zip(readable_fields, response.get("valueRanges", []))}
    row_count = max((len(column) for column in columns.values()), default=0)
    normalized_query = query.strip().casefold()
    items = []
    for row_index in range(row_count):
        record = {field: (columns[field][row_index][0] if field in columns and row_index < len(columns[field]) and columns[field][row_index] else "") for field in fields}
        if not record["study_id"]:
            continue
        if normalized_query and normalized_query not in record["client_name"].casefold() and normalized_query not in record["study_id"].casefold():
            continue
        items.append({"id": record["study_id"], "client_name": record["client_name"], "approved_at": record["created_at"],
                      "approved_by": record["operator"], "administrator": record["administrator"],
                      "group_count": int(record["group_count"]) if str(record["group_count"]).isdigit() else 0,
                      "has_snapshot": bool(record["archive"]), "status": record["status"]})
    return list(reversed(items))[:max(1, min(int(limit), 200))]


def get_study(study_id: str) -> dict | None:
    settings = get_settings()
    headers, indexes = _headers()
    ids = _read_column(_index(indexes, "study_id"))
    row_number = next((index for index, row in enumerate(ids, start=2) if row and str(row[0]).strip() == study_id), None)
    if row_number is None:
        return None
    row = get_service().spreadsheets().values().get(
        spreadsheetId=settings.google_sheets_id,
        range=f"{_quoted_sheet()}!A{row_number}:ZZ{row_number}",
    ).execute().get("values", [[]])[0]
    field = lambda key: str(row[_index(indexes, key)] if _index(indexes, key) < len(row) else "")
    archive_column = _optional_index(indexes, "archive")
    archive = _decompress_archive(field("archive")) if archive_column is not None else None
    return {"id": study_id, "client_name": field("client_name"), "approved_at": field("created_at"),
            "approved_by": field("operator"), "status": field("status"),
            "app_version": archive.get("app_version", "") if archive else "",
            "snapshot": archive.get("snapshot") if archive else None,
            "document_html": archive.get("document_html") if archive else None}
