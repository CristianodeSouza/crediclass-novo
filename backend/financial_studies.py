"""Google Sheets persistence for immutable approved financial-study snapshots."""

from __future__ import annotations

import base64
import hashlib
import json
import math
import os
import re
import secrets
import threading
import zlib
from datetime import datetime, timedelta, timezone
from uuid import UUID

from cryptography.fernet import Fernet, InvalidToken

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
SHARE_COLUMNS = {
    "token_hash": "financial_study_public_token_sha256",
    "expires_at": "financial_study_public_expires_at",
    "revoked": "financial_study_public_revoked",
}
PUBLIC_LINK_VALIDITY_DAYS = 30
_study_id_lock = threading.Lock()


def _quoted_sheet() -> str:
    return "'" + SHEET_NAME.replace("'", "''") + "'"


def _ensure_sheet_grid_columns(required_column_count: int) -> None:
    """Expand the history tab grid before writing new columns past its current edge."""
    settings = get_settings()
    service = get_service()
    spreadsheet = service.spreadsheets().get(
        spreadsheetId=settings.google_sheets_id,
        fields="sheets(properties(sheetId,title,gridProperties(columnCount)))",
    ).execute()
    sheet = next(
        (item.get("properties", {}) for item in spreadsheet.get("sheets", [])
         if item.get("properties", {}).get("title") == SHEET_NAME),
        None,
    )
    if sheet is None:
        raise RuntimeError(f"A aba {SHEET_NAME!r} não foi encontrada.")
    current_count = int(sheet.get("gridProperties", {}).get("columnCount", 0))
    if required_column_count <= current_count:
        return
    service.spreadsheets().batchUpdate(
        spreadsheetId=settings.google_sheets_id,
        body={"requests": [{
            "updateSheetProperties": {
                "properties": {
                    "sheetId": sheet["sheetId"],
                    "gridProperties": {"columnCount": required_column_count},
                },
                "fields": "gridProperties.columnCount",
            }
        }]},
    ).execute()


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
    _ensure_sheet_grid_columns(last_column)
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
    column_name = ARCHIVE_COLUMNS.get(field, SHARE_COLUMNS.get(field, field))
    return indexes.get(normalize_header(column_name))


def _ensure_share_columns(headers: list[str], indexes: dict[str, int]) -> tuple[list[str], dict[str, int]]:
    missing = [name for name in SHARE_COLUMNS.values() if normalize_header(name) not in indexes]
    if not missing:
        return headers, indexes
    settings = get_settings()
    first_column = len(headers) + 1
    last_column = first_column + len(missing) - 1
    _ensure_sheet_grid_columns(last_column)
    get_service().spreadsheets().values().update(
        spreadsheetId=settings.google_sheets_id,
        range=f"{_quoted_sheet()}!{column_letter(first_column - 1)}1:{column_letter(last_column - 1)}1",
        valueInputOption="RAW",
        body={"values": [missing]},
    ).execute()
    headers.extend(missing)
    indexes.update({normalize_header(name): len(headers) - len(missing) + offset for offset, name in enumerate(missing)})
    return headers, indexes


def _update_row_fields(row_number: int, indexes: dict[str, int], values: dict[str, str]) -> None:
    settings = get_settings()
    service = get_service()
    updates = []
    for field, value in values.items():
        column = _optional_index(indexes, field)
        if column is None:
            raise RuntimeError(f"Coluna {field!r} não encontrada na aba de Histórico de Estudos.")
        letter = column_letter(column)
        updates.append({"range": f"{_quoted_sheet()}!{letter}{row_number}", "values": [[value]]})
    service.spreadsheets().values().batchUpdate(
        spreadsheetId=settings.google_sheets_id,
        body={"valueInputOption": "RAW", "data": updates},
    ).execute()


def _find_study_row(study_id: str) -> tuple[list[str], dict[str, int], int] | None:
    headers, indexes = _headers()
    ids = _read_column(_index(indexes, "study_id"))
    row_number = next((index for index, row in enumerate(ids, start=2) if row and str(row[0]).strip() == study_id), None)
    return (headers, indexes, row_number) if row_number is not None else None


def _share_state(row: list[str], indexes: dict[str, int]) -> dict:
    value = lambda field: str(row[indexes[field]] if indexes.get(field) is not None and indexes[field] < len(row) else "")
    token_storage = value(normalize_header(SHARE_COLUMNS["token_hash"]))
    token_hash, separator, token_ciphertext = token_storage.partition(".")
    expires_at = value(normalize_header(SHARE_COLUMNS["expires_at"]))
    revoked = value(normalize_header(SHARE_COLUMNS["revoked"])).strip().casefold() == "true"
    try:
        expires = datetime.fromisoformat(expires_at)
        active = bool(token_hash) and not revoked and expires > datetime.now(timezone.utc)
    except ValueError:
        active = False
    token = None
    if active and separator and token_ciphertext:
        try:
            token = _share_cipher().decrypt(token_ciphertext.encode("ascii")).decode("utf-8")
        except (InvalidToken, UnicodeDecodeError, ValueError):
            token = None
    return {"active": active, "expires_at": expires_at or None, "revoked": revoked, "token": token}


def _share_cipher() -> Fernet:
    secret = os.getenv("SHARE_TOKEN_SECRET") or os.getenv("AUTH_SECRET") or "crediclass-dashboard-v3-local-login"
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode("utf-8")).digest())
    return Fernet(key)


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


def _next_study_id(now: datetime, approval_key: str, existing_ids: list[list[str]]) -> str:
    sequence = 999
    for row in existing_ids:
        if not row:
            continue
        match = re.match(r"^EF-(\d+)(0[1-9]|1[0-2])(\d{4})-", str(row[0]).strip(), re.IGNORECASE)
        if match:
            sequence = max(sequence, int(match.group(1)))
    # Brazil has observed UTC-03:00 year-round since the 2019 DST change.
    local_date = now.astimezone(timezone(timedelta(hours=-3)))
    return f"EF-{sequence + 1:04d}{local_date:%m%Y}-{approval_key[:10].upper()}"


def _decompress_archive(value: str) -> dict | None:
    if not value:
        return None
    if not value.startswith("gz1:"):
        raise RuntimeError("O snapshot arquivado usa um formato desconhecido.")
    raw = zlib.decompress(base64.b64decode(value[4:]))
    return json.loads(raw.decode("utf-8"))


def _validate_selected_credit_basis(snapshot: dict) -> None:
    """Reject new-format studies with incomplete or inconsistent credit selections."""
    for group in snapshot.get("groups", []):
        if group.get("study_credit_basis") != "credito_escolhido_por_cenario":
            continue
        quotas = group.get("quotas_by_scenario") or {}
        selected = group.get("selected_credit_by_scenario") or {}
        options = group.get("available_credit_options") or []
        allowed_values = set()
        for option in options:
            raw_value = option.get("value") if isinstance(option, dict) else option
            try:
                value = float(raw_value)
            except (TypeError, ValueError):
                continue
            if math.isfinite(value) and value > 0:
                allowed_values.add(round(value, 2))
        scenarios = {str(item.get("id")): item for item in group.get("selected_scenarios") or []}
        contracts = group.get("contracts") or []
        for scenario_id in ("without_embedded", "with_embedded"):
            try:
                count = max(0, int(quotas.get(scenario_id, 0)))
            except (TypeError, ValueError):
                raise ValueError("A quantidade de cotas do estudo é inválida.") from None
            if count <= 0:
                continue
            try:
                credit = float(selected.get(scenario_id))
            except (TypeError, ValueError):
                credit = math.nan
            if not math.isfinite(credit) or credit <= 0:
                raise ValueError("Escolha um crédito válido para cada cenário com cotas antes de aprovar o estudo.")
            if not allowed_values or round(credit, 2) not in allowed_values:
                raise ValueError("O crédito escolhido não corresponde às opções carregadas do grupo.")
            maximum = group.get("credit_max")
            if maximum is not None and float(maximum) > 0 and credit > float(maximum) + 0.01:
                raise ValueError("O crédito escolhido excede o Maior Crédito informado para o grupo.")
            scenario = scenarios.get(scenario_id)
            if not scenario or abs(float(scenario.get("selected_credit") or 0) - credit) > 0.01:
                raise ValueError("Os dados financeiros do cenário não correspondem ao crédito selecionado.")
            scenario_contracts = [contract for contract in contracts if contract.get("scenario") == scenario_id]
            if len(scenario_contracts) != count or any(abs(float(contract.get("contracted_credit") or 0) - credit) > 0.01 for contract in scenario_contracts):
                raise ValueError("A quantidade ou o crédito dos contratos do cenário não corresponde à seleção.")


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
    _validate_selected_credit_basis(snapshot)
    archive = _compress_archive(snapshot, document_html, app_version)
    settings = get_settings()
    headers, indexes = _headers()
    headers, indexes = _ensure_archive_columns(headers, indexes)

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    created_at = datetime.fromisoformat(now)
    groups = snapshot["groups"]
    group_ids = list(dict.fromkeys(str(group.get("group") or group.get("group_key") or "").strip() for group in groups))
    administrators = list(dict.fromkeys(str(group.get("administrator") or "").strip() for group in groups if str(group.get("administrator") or "").strip()))
    values = [""] * len(headers)
    field_values = {
        "study_id": "",
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
    with _study_id_lock:
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

        study_ids = _read_column(_index(indexes, "study_id"))
        study_id = _next_study_id(created_at, approval_key, study_ids)
        for field, value in field_values.items():
            values[_index(indexes, field)] = study_id if field == "study_id" else value
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
    found = _find_study_row(study_id)
    if found is None:
        return None
    _, indexes, row_number = found
    settings = get_settings()
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
            "document_html": archive.get("document_html") if archive else None,
            "public_link": _share_state(row, indexes)}


def create_public_link(study_id: str) -> dict | None:
    found = _find_study_row(study_id)
    if found is None:
        return None
    headers, indexes, row_number = found
    headers, indexes = _ensure_archive_columns(headers, indexes)
    headers, indexes = _ensure_share_columns(headers, indexes)
    settings = get_settings()
    row = get_service().spreadsheets().values().get(
        spreadsheetId=settings.google_sheets_id,
        range=f"{_quoted_sheet()}!A{row_number}:ZZ{row_number}",
    ).execute().get("values", [[]])[0]
    archive_index = _optional_index(indexes, "archive")
    if archive_index is None or archive_index >= len(row) or not row[archive_index]:
        raise ValueError("Este estudo não possui snapshot completo para compartilhar.")
    archive = _decompress_archive(str(row[archive_index]))
    if not archive or not archive.get("document_html"):
        raise ValueError("Este estudo não possui documento visual para compartilhar.")

    token = secrets.token_urlsafe(32)
    expires_at = (datetime.now(timezone.utc) + timedelta(days=PUBLIC_LINK_VALIDITY_DAYS)).isoformat(timespec="seconds")
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    token_ciphertext = _share_cipher().encrypt(token.encode("utf-8")).decode("ascii")
    _update_row_fields(row_number, indexes, {
        # Keep the validator and encrypted recovery token in the existing field.
        # Legacy rows contain only the digest and remain valid as-is.
        "token_hash": f"{token_hash}.{token_ciphertext}",
        "expires_at": expires_at,
        "revoked": "FALSE",
    })
    return {"token": token, "expires_at": expires_at, "validity_days": PUBLIC_LINK_VALIDITY_DAYS}


def revoke_public_link(study_id: str) -> dict | None:
    found = _find_study_row(study_id)
    if found is None:
        return None
    headers, indexes, row_number = found
    headers, indexes = _ensure_share_columns(headers, indexes)
    settings = get_settings()
    row = get_service().spreadsheets().values().get(
        spreadsheetId=settings.google_sheets_id,
        range=f"{_quoted_sheet()}!A{row_number}:ZZ{row_number}",
    ).execute().get("values", [[]])[0]
    _update_row_fields(row_number, indexes, {"revoked": "TRUE"})
    return _share_state(row, indexes) | {"active": False, "revoked": True}


def get_public_study(token: str) -> dict | None:
    if not token or len(token) > 256:
        return None
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    found = _find_study_row_by_token_hash(token_hash)
    if found is None:
        return None
    indexes, row = found
    if not _share_state(row, indexes)["active"]:
        return None
    archive = _decompress_archive(str(row[_index(indexes, "archive")]))
    if not archive or not archive.get("document_html"):
        return None
    return {
        "id": str(row[_index(indexes, "study_id")]),
        "client_name": str(row[_index(indexes, "client_name")]),
        "approved_at": str(row[_index(indexes, "created_at")]),
        "app_version": archive.get("app_version", ""),
        "document_html": archive["document_html"],
    }


def _find_study_row_by_token_hash(token_hash: str) -> tuple[dict[str, int], list[str]] | None:
    headers, indexes = _headers()
    hash_index = _optional_index(indexes, "token_hash")
    archive_index = _optional_index(indexes, "archive")
    if hash_index is None or archive_index is None:
        return None
    hashes = _read_column(hash_index)
    row_number = next((
        index for index, row in enumerate(hashes, start=2)
        if row and secrets.compare_digest(str(row[0]).strip().partition(".")[0], token_hash)
    ), None)
    if row_number is None:
        return None
    settings = get_settings()
    row = get_service().spreadsheets().values().get(
        spreadsheetId=settings.google_sheets_id,
        range=f"{_quoted_sheet()}!A{row_number}:ZZ{row_number}",
    ).execute().get("values", [[]])[0]
    return indexes, row
