from datetime import datetime
import json
from pathlib import Path
import unicodedata
from typing import Any

from .config import get_settings
from .financial_study_engine import build_financeiro
from .models import EstudoRequest
from .sheets_client import get_service

RUNTIME_DIR = Path(__file__).resolve().parent / "runtime_data"
STUDIES_FILE = RUNTIME_DIR / "studies.json"
STUDIES_SHEET_NAME = "Historico de Estudos"
STUDIES_HEADERS = [
    "estudo_id",
    "proposal_id",
    "criado_em",
    "status",
    "operador",
    "grupo_id",
    "cliente_nome",
    "administradora",
    "tipo_bem",
    "estrategia",
    "cliente_json",
    "grupo_json",
    "cenario_json",
    "financeiro_json",
    "template_campos_json",
    "cancelado_em",
]


def load_studies_from_disk() -> dict[str, dict]:
    if not STUDIES_FILE.exists():
        return {}
    try:
        data = json.loads(STUDIES_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def initial_counter(studies: dict[str, dict]) -> int:
    counters = []
    for estudo_id in studies:
        try:
            counters.append(int(str(estudo_id).rsplit("-", 1)[-1]))
        except ValueError:
            continue
    return max(counters, default=0)


def initial_proposal_counter(studies: dict[str, dict]) -> int:
    counters = []
    for item in studies.values():
        value = str(item.get("proposal_id") or "")
        if value.upper().startswith("ID "):
            try:
                counters.append(int(value[3:]))
            except ValueError:
                continue
    return max(counters, default=0)


def save_studies_to_disk() -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    STUDIES_FILE.write_text(json.dumps(_studies, ensure_ascii=False, indent=2), encoding="utf-8")


_studies: dict[str, dict] = load_studies_from_disk()
_counter = initial_counter(_studies)
_proposal_counter = initial_proposal_counter(_studies)


def sheets_enabled() -> bool:
    settings = get_settings()
    return bool(settings.google_sheets_id and settings.google_service_account_json)


def dumps_cell(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def loads_cell(raw_value: Any, default: Any) -> Any:
    text = str(raw_value or "").strip()
    if not text:
        return default
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return default


def ensure_studies_sheet() -> None:
    if not sheets_enabled():
        return
    settings = get_settings()
    service = get_service()
    spreadsheet = service.spreadsheets().get(spreadsheetId=settings.google_sheets_id).execute()
    sheets = spreadsheet.get("sheets", [])
    titles = {sheet.get("properties", {}).get("title", "") for sheet in sheets}
    if STUDIES_SHEET_NAME not in titles:
        service.spreadsheets().batchUpdate(
            spreadsheetId=settings.google_sheets_id,
            body={"requests": [{"addSheet": {"properties": {"title": STUDIES_SHEET_NAME}}}]},
        ).execute()
    result = service.spreadsheets().values().get(
        spreadsheetId=settings.google_sheets_id,
        range=f"'{STUDIES_SHEET_NAME}'!A1:P2",
    ).execute()
    rows = result.get("values", [])
    if not rows or rows[0] != STUDIES_HEADERS:
        service.spreadsheets().values().update(
            spreadsheetId=settings.google_sheets_id,
            range=f"'{STUDIES_SHEET_NAME}'!A1:P1",
            valueInputOption="RAW",
            body={"values": [STUDIES_HEADERS]},
        ).execute()


def normalize_study_item(item: dict[str, Any]) -> dict[str, Any]:
    normalized = {
        "estudo_id": str(item.get("estudo_id") or ""),
        "proposal_id": str(item.get("proposal_id") or ""),
        "criado_em": str(item.get("criado_em") or ""),
        "status": str(item.get("status") or "Concluido"),
        "operador": str(item.get("operador") or "Não informado"),
        "grupo_id": str(item.get("grupo_id") or ""),
        "grupo": item.get("grupo") or {},
        "cliente": item.get("cliente") or {},
        "cenario": item.get("cenario") or None,
        "financeiro": item.get("financeiro") or {},
        "template_campos": item.get("template_campos") or {},
        "estrategia": str(item.get("estrategia") or "Lance Total"),
    }
    if item.get("cancelado_em"):
        normalized["cancelado_em"] = str(item.get("cancelado_em"))
    return normalized


def study_item_to_row(item: dict[str, Any]) -> list[str]:
    normalized = normalize_study_item(item)
    grupo = normalized["grupo"]
    cliente = normalized["cliente"]
    return [
        normalized["estudo_id"],
        normalized["proposal_id"],
        normalized["criado_em"],
        normalized["status"],
        normalized["operador"],
        normalized["grupo_id"],
        str(cliente.get("nome") or ""),
        str(grupo.get("administradora") or ""),
        str(grupo.get("tipo_bem") or ""),
        normalized["estrategia"],
        dumps_cell(cliente),
        dumps_cell(grupo),
        dumps_cell(normalized["cenario"]),
        dumps_cell(normalized["financeiro"]),
        dumps_cell(normalized["template_campos"]),
        str(normalized.get("cancelado_em") or ""),
    ]


def study_item_from_row(row: list[Any]) -> dict[str, Any]:
    padded = list(row[: len(STUDIES_HEADERS)]) + [""] * max(0, len(STUDIES_HEADERS) - len(row))
    payload = dict(zip(STUDIES_HEADERS, padded))
    return normalize_study_item(
        {
            "estudo_id": payload["estudo_id"],
            "proposal_id": payload["proposal_id"],
            "criado_em": payload["criado_em"],
            "status": payload["status"],
            "operador": payload["operador"],
            "grupo_id": payload["grupo_id"],
            "cliente": loads_cell(payload["cliente_json"], {}),
            "grupo": loads_cell(payload["grupo_json"], {}),
            "cenario": loads_cell(payload["cenario_json"], None),
            "financeiro": loads_cell(payload["financeiro_json"], {}),
            "template_campos": loads_cell(payload["template_campos_json"], {}),
            "estrategia": payload["estrategia"],
            "cancelado_em": payload["cancelado_em"],
        }
    )


def read_studies_from_sheet() -> list[tuple[int, dict[str, Any]]]:
    ensure_studies_sheet()
    settings = get_settings()
    service = get_service()
    result = service.spreadsheets().values().get(
        spreadsheetId=settings.google_sheets_id,
        range=f"'{STUDIES_SHEET_NAME}'!A:P",
    ).execute()
    values = result.get("values", [])
    if not values:
        return []
    rows = []
    for row_number, row in enumerate(values[1:], start=2):
        if not any(str(cell or "").strip() for cell in row):
            continue
        item = study_item_from_row(row)
        if item.get("estudo_id"):
            rows.append((row_number, item))
    return rows


def write_study_row_to_sheet(row_number: int, item: dict[str, Any]) -> None:
    ensure_studies_sheet()
    settings = get_settings()
    service = get_service()
    service.spreadsheets().values().update(
        spreadsheetId=settings.google_sheets_id,
        range=f"'{STUDIES_SHEET_NAME}'!A{row_number}:P{row_number}",
        valueInputOption="RAW",
        body={"values": [study_item_to_row(item)]},
    ).execute()


def append_study_row_to_sheet(item: dict[str, Any]) -> None:
    ensure_studies_sheet()
    settings = get_settings()
    service = get_service()
    service.spreadsheets().values().append(
        spreadsheetId=settings.google_sheets_id,
        range=f"'{STUDIES_SHEET_NAME}'!A:P",
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values": [study_item_to_row(item)]},
    ).execute()


def next_study_identifiers(existing_items: list[dict[str, Any]]) -> tuple[str, str]:
    year = datetime.now().year
    estudo_counter = initial_counter({item.get("estudo_id", ""): item for item in existing_items})
    proposal_counter = initial_proposal_counter({item.get("estudo_id", ""): item for item in existing_items})
    return f"EST-{year}-{estudo_counter + 1:05d}", f"ID {proposal_counter + 1:04d}"


def create_estudo(payload: EstudoRequest, grupo: dict | None = None, operador: str = "") -> dict:
    global _counter, _proposal_counter
    criado_em = datetime.now().isoformat(timespec="seconds")
    grupo_data = grupo or {}
    financeiro = build_financeiro(payload, grupo_data)
    if sheets_enabled():
        existing_items = [item for _, item in read_studies_from_sheet()]
        estudo_id, proposal_id = next_study_identifiers(existing_items)
    else:
        _counter += 1
        _proposal_counter += 1
        estudo_id = f"EST-{datetime.now().year}-{_counter:05d}"
        proposal_id = f"ID {_proposal_counter:04d}"
    study_item = {
        "estudo_id": estudo_id,
        "proposal_id": proposal_id,
        "cliente": payload.cliente.model_dump(),
        "grupo_id": payload.grupo_id,
        "grupo": grupo_data,
        "cenario": payload.cenario,
        "financeiro": financeiro,
        "template_campos": payload.template_campos,
        "estrategia": financeiro["estrategia_recomendada"],
        "status": "Concluido",
        "operador": operador or "Não informado",
        "criado_em": criado_em,
    }
    if sheets_enabled():
        append_study_row_to_sheet(study_item)
    else:
        _studies[estudo_id] = study_item
        save_studies_to_disk()
    return {"estudo_id": estudo_id, "proposal_id": proposal_id, "success": True}


def list_estudos() -> list[dict]:
    if sheets_enabled():
        items = [item for _, item in read_studies_from_sheet()]
    else:
        items = list(_studies.values())
    return sorted(items, key=lambda item: item["criado_em"], reverse=True)


def get_estudo(estudo_id: str) -> dict | None:
    if sheets_enabled():
        for _, item in read_studies_from_sheet():
            if item.get("estudo_id") == estudo_id:
                return item
        return None
    return _studies.get(estudo_id)


def delete_estudo(estudo_id: str) -> bool:
    cancelado_em = datetime.now().isoformat(timespec="seconds")
    if sheets_enabled():
        for row_number, item in read_studies_from_sheet():
            if item.get("estudo_id") != estudo_id:
                continue
            item["status"] = "Cancelado"
            item["cancelado_em"] = cancelado_em
            write_study_row_to_sheet(row_number, item)
            return True
        return False
    estudo = _studies.get(estudo_id)
    if not estudo:
        return False
    estudo["status"] = "Cancelado"
    estudo["cancelado_em"] = cancelado_em
    save_studies_to_disk()
    return True


def ascii_text(value) -> str:
    text = str(value or "")
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in normalized if ord(ch) < 128)


def money(value) -> str:
    try:
        return f"R$ {float(value):,.2f}"
    except (TypeError, ValueError):
        return "-"


def percent(value) -> str:
    try:
        return f"{float(value) * 100:.2f}%"
    except (TypeError, ValueError):
        return "-"


def pdf_escape(text: str) -> str:
    return ascii_text(text).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def build_pdf_bytes(lines: list[str]) -> bytes:
    content_lines = ["BT", "/F1 11 Tf", "50 780 Td", "14 TL"]
    for line in lines[:48]:
        content_lines.append(f"({pdf_escape(line)}) Tj")
        content_lines.append("T*")
    content_lines.append("ET")
    stream = "\n".join(content_lines).encode("latin1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("ascii"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")
    xref_position = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_position}\n%%EOF\n".encode("ascii"))
    return bytes(pdf)


def study_pdf_lines(estudo: dict) -> list[str]:
    cliente = estudo.get("cliente") or {}
    grupo = estudo.get("grupo") or {}
    financeiro = estudo.get("financeiro") or {}
    historico = financeiro.get("historico_12_meses") or {}
    lines = [
        "Crediclass Dashboard V3 - Estudo Financeiro",
        f"Estudo: {estudo.get('estudo_id', '-')}",
        f"Status: {estudo.get('status', '-')}",
        f"Operador: {estudo.get('operador', '-')}",
        f"Criado em: {estudo.get('criado_em', '-')}",
        "",
        "Cliente",
        f"Nome: {cliente.get('nome', '-')}",
        f"Objetivo: {cliente.get('objetivo', '-')}",
        f"Credito desejado: {money(cliente.get('credito_desejado'))}",
        f"Prazo desejado: {cliente.get('prazo_desejado') or '-'} meses",
        f"Lance proprio: {money(cliente.get('lance_proprio'))}",
        f"FGTS: {money(cliente.get('fgts'))}",
        "",
        "Grupo",
        f"Administradora: {grupo.get('administradora', '-')}",
        f"Grupo: {grupo.get('grupo') or estudo.get('grupo_id', '-')}",
        f"Tipo de bem: {grupo.get('tipo_bem', '-')}",
        f"Status: {grupo.get('status', '-')}",
        "",
        "Resumo Financeiro",
        f"Carta de credito: {money(financeiro.get('credito_original') or financeiro.get('credito'))}",
        f"Lance embutido: {money(financeiro.get('lance_embutido'))}",
        f"Recurso proprio: {money(financeiro.get('recurso_proprio'))}",
        f"Valor total do lance: {money(financeiro.get('valor_total_lance'))}",
        f"Percentual lance total: {percent(financeiro.get('percentual_lance_total'))}",
        f"Parcela inicial: {money(financeiro.get('parcela_inicial'))}",
        f"Parcela apos contemplacao: {money(financeiro.get('parcela_apos_contemplacao'))}",
        f"Chance: {financeiro.get('chance_contemplacao', '-')}",
        f"Total contemplacoes 12m: {historico.get('total_contemplacoes', '-')}",
        "",
        "Campos do Operador",
    ]
    template_campos = estudo.get("template_campos") or {}
    for label, value in template_campos.items():
        lines.append(f"{label}: {value or '-'}")
    lines.extend([
        "",
        "Estrategias",
    ])
    for strategy in financeiro.get("estrategias", [])[:8]:
        lines.append(
            f"{strategy.get('estrategia', '-')}: {percent(strategy.get('percentual_lance'))} | "
            f"Lance proprio {money(strategy.get('lance_proprio'))} | Chance {strategy.get('chance_contemplacao', '-')}"
        )
    return lines


def export_estudo_pdf(estudo_id: str, output_dir: Path) -> str | None:
    estudo = get_estudo(estudo_id)
    if not estudo:
        return None
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{estudo_id}.pdf"
    path = output_dir / filename
    path.write_bytes(build_pdf_bytes(study_pdf_lines(estudo)))
    return filename
