from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
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
