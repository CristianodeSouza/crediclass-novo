from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
import textwrap
import unicodedata
from pathlib import Path
from typing import Any
from uuid import uuid4


RUNTIME_DIR = Path(__file__).resolve().parent / "runtime_data"
AUDIT_FILE = RUNTIME_DIR / "auditorias_motor_360.json"


def new_audit_id(now: datetime | None = None) -> str:
    moment = now or datetime.now(timezone.utc)
    return f"AUD-{moment.strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:8].upper()}"


def _load_all() -> dict[str, dict[str, Any]]:
    if not AUDIT_FILE.exists():
        return {}
    try:
        payload = json.loads(AUDIT_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _save_all(data: dict[str, dict[str, Any]]) -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    AUDIT_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def save_motor360_audit(audit: dict[str, Any]) -> dict[str, Any]:
    snapshot = deepcopy(audit)
    audit_id = str(snapshot["metadata"]["audit_id"])
    records = _load_all()
    records[audit_id] = snapshot
    _save_all(records)
    return deepcopy(snapshot)


def get_motor360_audit(audit_id: str) -> dict[str, Any] | None:
    record = _load_all().get(str(audit_id))
    return deepcopy(record) if isinstance(record, dict) else None


def audit_to_markdown(audit: dict[str, Any]) -> str:
    metadata = audit.get("metadata", {})
    client = audit.get("client_snapshot", {})
    summary = audit.get("summary", {})
    lines = [
        "# Auditoria da Análise - Motor 360",
        "",
        f"- **Identificador:** {metadata.get('audit_id', '-')}",
        f"- **Executada em:** {metadata.get('completed_at', '-')}",
        f"- **Duração:** {metadata.get('duration_ms', 0)} ms",
        f"- **Versão do motor:** {metadata.get('engine_version', '-')}",
        f"- **Versão das regras:** {metadata.get('rules_version', '-')}",
        f"- **Ambiente:** {metadata.get('environment', '-')}",
        "",
        "## Dados consolidados do perfil",
        "",
    ]
    source = audit.get("data_source", {})
    snapshot = source.get("base_snapshot", {})
    if snapshot:
        lines.extend([
            f"- **Linhas da base na execucao:** {snapshot.get('row_count', source.get('total_rows', 0))}",
            f"- **Hash da base ({snapshot.get('fingerprint_algorithm', 'sha256')}):** `{snapshot.get('fingerprint', '-')}`",
            "",
        ])
    for key, value in client.get("consolidated_values", {}).items():
        lines.append(f"- **{key}:** {value}")
    lines.extend(["", "## Etapas de filtro", ""])
    for step in audit.get("execution_steps", []):
        lines.extend([
            f"### {step.get('order', '-')}. {step.get('name', '-')}",
            f"- Regra: {step.get('formula_or_rule', '-')}",
            f"- Entrada: {step.get('input_count', 0)}",
            f"- Aprovados: {step.get('approved_count', 0)}",
            f"- Eliminados: {step.get('rejected_count', 0)}",
        ])
    lines.extend([
        "",
        "## Resumo final",
        "",
        f"- Grupos carregados: {summary.get('total_loaded', 0)}",
        f"- Grupos analisados: {summary.get('total_analyzed', 0)}",
        f"- Compatíveis por crédito: {summary.get('total_credit_compatible', 0)}",
        f"- Pré-selecionados: {summary.get('total_preselected', 0)}",
        f"- Eliminados por crédito: {summary.get('total_credit_rejected', 0)}",
        f"- Eliminados por prazo/renda: {summary.get('total_term_income_rejected', 0)}",
        f"- Grupos com dados incompletos: {summary.get('groups_with_incomplete_data', 0)}",
        f"- Ocorrências de campos incompletos: {summary.get('incomplete_field_occurrences', 0)}",
        f"- Excluídos: {summary.get('total_rejected', 0)}",
        "",
        "## Ordenação",
        "",
    ])
    lines.extend(f"{index}. {rule}" for index, rule in enumerate(audit.get("final_ordering", {}).get("rules", []), 1))
    column_notes = audit.get("schema_notes", {}).get("columns_used", {})
    lines.extend([
        "",
        "## Contrato das colunas",
        "",
        f"- Campo oficial para uso em decisão: `{column_notes.get('official_decision_field', 'used_in_decision')}`.",
        f"- Campo de compatibilidade: `{column_notes.get('compatibility_field', 'used')}`. {column_notes.get('compatibility_note', '')}",
    ])
    lines.extend(["", "## Alertas", ""])
    warnings = audit.get("warnings", [])
    lines.extend(f"- [{item.get('level', 'info')}] {item.get('message', '-') }" for item in warnings) if warnings else lines.append("- Nenhum alerta global registrado.")
    return "\n".join(lines) + "\n"


def _pdf_text(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value if value is not None else "-"))
    return text.encode("ascii", "ignore").decode("ascii")


def _pdf_escape(value: Any) -> str:
    return _pdf_text(value).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _audit_pdf_lines(audit: dict[str, Any]) -> list[tuple[str, int, bool]]:
    metadata = audit.get("metadata", {})
    client = audit.get("client_snapshot", {})
    summary = audit.get("summary", {})
    source = audit.get("data_source", {})
    lines: list[tuple[str, int, bool]] = []

    def heading(value: Any) -> None:
        lines.append((_pdf_text(value), 12, True))

    def line(value: Any = "", size: int = 8) -> None:
        for part in textwrap.wrap(_pdf_text(value), width=142, break_long_words=False, break_on_hyphens=False) or [""]:
            lines.append((part, size, False))

    heading("CREDICLASS - RELATORIO DA ANALISE DO MOTOR 360")
    line(f"Auditoria: {metadata.get('audit_id', '-')} | Executada em: {metadata.get('completed_at', '-')} | Motor: {metadata.get('engine_version', '-')} | Regras: {metadata.get('rules_version', '-')} | Ambiente: {metadata.get('environment', '-')}")
    heading("1. Dados do cliente")
    for field in client.get("raw_fields", []):
        line(f"{field.get('field_name', '-')}: {field.get('normalized_value', '-')} | Origem: {field.get('source_reference', field.get('source', '-'))}")
    line(f"Valores consolidados: {client.get('consolidated_values', {})}")
    heading("2. Base e resumo da execucao")
    line(f"Base: {source.get('source_name', '-')} | Linhas lidas: {source.get('total_rows', 0)} | Hash: {source.get('base_snapshot', {}).get('fingerprint', '-')}")
    for key, value in summary.items():
        line(f"{key}: {value}")
    heading("3. Sequencia de filtros")
    for step in audit.get("execution_steps", []):
        line(f"{step.get('order', '-')}. {step.get('name', '-')}: {step.get('formula_or_rule', '-')} | Entrada {step.get('input_count', 0)} | Aprovados {step.get('approved_count', 0)} | Eliminados {step.get('rejected_count', 0)} | Incompletos {step.get('incomplete_count', 0)}")
    heading("4. Formulas utilizadas")
    for formula in audit.get("formulas", []):
        line(f"{formula.get('name', '-')}: {formula.get('expression', '-')} | Resultado: {formula.get('result', 'calculado por grupo')}")
    heading("5. Auditoria detalhada dos grupos")
    line("Cada grupo abaixo preserva os dois cenarios e os mesmos dados apresentados no botao Ver.")
    for item in audit.get("group_results", []):
        heading(f"Grupo {item.get('grupo', '-')} | {item.get('administradora', '-')} | Resultado: {item.get('result', '-')}")
        line(f"Linha de origem: {item.get('source_row', '-')} | Identificador original: {item.get('grupo_raw', item.get('grupo', '-'))}")
        for scenario in item.get("scenarios", []):
            title = "Credito contratado com lance embutido" if scenario.get("id") == "with_embedded" else "Credito contratado sem lance embutido"
            line(f"{title}: status {scenario.get('creation_status', '-')} | Credito contratado {scenario.get('credito_contratado', '-')} | Lance total {scenario.get('lance_total', '-')} ({scenario.get('percentual_lance', '-')})")
            line(f"Saldo devedor: {scenario.get('saldo_devedor', '-')} | Prazo remanescente: {scenario.get('prazo_remanescente', '-')} | Prazo apos lance: {scenario.get('prazo_apos_lance_limite_renda_meses', '-')}")
            parcela = scenario.get("parcela_inicial")
            line(f"Parcela inicial: {parcela if parcela is not None else '-'} | Formula: {scenario.get('parcela_inicial_formula', 'saldo devedor / prazo remanescente (coluna F)')}")
            if parcela is not None:
                line(f"Calculo auditavel: {scenario.get('saldo_devedor', '-')} / {scenario.get('prazo_remanescente', '-')} = {parcela}")
            line(f"Credito: {'Aprovado' if scenario.get('credit_compatible') else 'Reprovado'} | Prazo: {'Compativel' if scenario.get('term_compatible') else 'Nao compativel'} | Liquidez: {'Preservada' if scenario.get('liquidez_preservada') else 'Nao preservada'}")
        line(f"Justificativa: {', '.join(item.get('justification', [])) or 'Nenhuma'}")
    heading("6. Regras e alertas")
    for warning in audit.get("warnings", []):
        line(f"[{warning.get('level', 'info')}] {warning.get('message', '-')}")
    return lines


def audit_to_pdf(audit: dict[str, Any]) -> bytes:
    """Build a readable landscape PDF without external runtime dependencies."""
    page_width, page_height = 842, 595
    left, top, bottom = 28, 565, 28
    line_height = 11
    pages: list[list[tuple[str, int, bool]]] = [[]]
    used = 0
    for text, size, is_heading in _audit_pdf_lines(audit):
        height = 18 if is_heading else line_height
        if used + height > top - bottom:
            pages.append([])
            used = 0
        pages[-1].append((text, size, is_heading))
        used += height

    objects: list[bytes] = [b"<< /Type /Catalog /Pages 2 0 R >>", b"", b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    page_refs: list[int] = []
    content_refs: list[int] = []
    for page in pages:
        commands = ["BT"]
        y = top
        for text, size, is_heading in page:
            commands.append(f"/F1 {size} Tf")
            commands.append(f"1 0 0 1 {left} {y} Tm")
            commands.append(f"({_pdf_escape(text)}) Tj")
            y -= 18 if is_heading else line_height
        commands.append("ET")
        stream = "\n".join(commands).encode("latin1", "replace")
        content_refs.append(len(objects) + 1)
        objects.append(b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream")
        page_refs.append(len(objects) + 1)
        objects.append(b"")

    objects[1] = f"<< /Type /Pages /Kids [{' '.join(f'{ref} 0 R' for ref in page_refs)}] /Count {len(page_refs)} >>".encode("ascii")
    for page_ref, content_ref in zip(page_refs, content_refs):
        objects[page_ref - 1] = f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {page_width} {page_height}] /Resources << /Font << /F1 3 0 R >> >> /Contents {content_ref} 0 R >>".encode("ascii")

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("ascii"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")
    xref = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("ascii"))
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("ascii"))
    return bytes(pdf)
