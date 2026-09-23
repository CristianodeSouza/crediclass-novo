from datetime import datetime
import json
from pathlib import Path
import unicodedata
import re
from typing import Any

from .config import get_settings
from .financial_study_engine import build_financeiro
from .models import EstudoPreviewRequest, EstudoRequest
from .sheets_client import get_service

EDITOR_DEFAULTS = {
    "study_financial": "<p><strong>Prezado,</strong></p><p>O presente Estudo Financeiro foi elaborado com base nas informações fornecidas e nas condições de mercado disponíveis na data de sua emissão e parâmetros abaixo.</p><p>O seu objetivo é apresentar cenários comparativos, auxiliando o cliente em seu processo de tomada de decisão.</p><p><em>As informações apresentadas possuem caráter informativo e ilustrativo, não constituindo garantia de resultado ou promessa de contemplação.</em></p>",
    "selection_criteria": "<p>Os grupos apresentados foram selecionados a partir de critérios técnicos definidos pela Crediclass, considerando indicadores históricos e condições disponíveis na data da análise.</p><ol><li><strong>Grupos antigos:</strong> mais participantes já contemplados, menor concorrência nos lances.</li><li><strong>Histórico de lance:</strong> concorrência de lances abaixo da média de mercado para grupos com prazo similar.</li><li><strong>Estabilidade nos lances:</strong> menor volatilidade nos últimos 11 meses.</li><li><strong>Saúde financeira:</strong> grupos saudáveis e com contemplações recorrentes.</li><li><strong>Lance embutido:</strong> permite utilizar parte da carta para o lance quando aplicável.</li></ol>",
    "how_consorcio_works": "<p>O consórcio é uma modalidade de crédito planejado que permite a aquisição de imóveis e outros bens por meio da formação de um fundo comum entre participantes.</p><p>Mensalmente, são realizadas contemplações por sorteio e lance, possibilitando o acesso à carta de crédito e oferecendo flexibilidade para diferentes objetivos patrimoniais.</p>",
    "strategy_explanation": "<p>As estratégias apresentadas foram construídas a partir do histórico dos grupos e servem como referência para a tomada de decisão do cliente.</p>",
    "important_considerations": "<p><strong>Cenários, projeções e simulações:</strong> Os cenários, projeções e simulações apresentados neste estudo foram elaborados com base nas informações fornecidas pelo cliente e nas condições observadas na data de emissão.</p><p><strong>Resultados demonstrados:</strong> Os resultados possuem caráter exclusivamente informativo e ilustrativo.</p><p><strong>Garantias:</strong> A Crediclass não garante rentabilidade, índices futuros, percentuais ou prazos de contemplação.</p><p><strong>Responsabilidade:</strong> A decisão pela contratação é de responsabilidade exclusiva do cliente.</p>",
    "custom_sections": [],
}

def default_editor_content() -> dict[str, Any]:
    return dict(EDITOR_DEFAULTS)

def normalize_editor_content(content: dict[str, Any] | None, fallback_defaults: bool = True) -> dict[str, Any]:
    incoming = content if isinstance(content, dict) else {}
    result = default_editor_content() if fallback_defaults else {key: "" for key in EDITOR_DEFAULTS}
    aliases = {"intro": "study_financial", "observacoes": "strategy_explanation", "consideracoes": "important_considerations"}
    for key, value in incoming.items():
        target = aliases.get(key, key)
        if target in result:
            result[target] = value
    result["custom_sections"] = result["custom_sections"] if isinstance(result["custom_sections"], list) else []
    return result

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
    "editor_content_json",
    "editor_original_json",
    "editor_history_json",
    "editor_version",
    "editor_updated_by",
    "editor_updated_at",
    "final_pdf_url",
    "final_pdf_version",
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
        range=f"'{STUDIES_SHEET_NAME}'!A1:X2",
    ).execute()
    rows = result.get("values", [])
    if not rows or rows[0] != STUDIES_HEADERS:
        service.spreadsheets().values().update(
            spreadsheetId=settings.google_sheets_id,
            range=f"'{STUDIES_SHEET_NAME}'!A1:X1",
            valueInputOption="RAW",
            body={"values": [STUDIES_HEADERS]},
        ).execute()


def normalize_study_item(item: dict[str, Any]) -> dict[str, Any]:
    template_campos = item.get("template_campos") or {}
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
        "template_campos": template_campos,
        "editor_content": item.get("editor_content") or template_campos.get("__editor_content") or {"intro": "", "observacoes": "", "consideracoes": "", "custom_sections": []},
        "editor_version": int(item.get("editor_version") or 1),
        "editor_history": item.get("editor_history") or template_campos.get("__editor_history") or [],
        "editor_original": item.get("editor_original") or template_campos.get("__editor_original") or {"intro": "", "observacoes": "", "consideracoes": "", "custom_sections": []},
        "editor_updated_by": str(item.get("editor_updated_by") or ""),
        "editor_updated_at": str(item.get("editor_updated_at") or ""),
        "final_pdf_url": str(item.get("final_pdf_url") or ""),
        "final_pdf_version": int(item.get("final_pdf_version") or 0),
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
        dumps_cell(normalized["editor_content"]),
        dumps_cell(normalized["editor_original"]),
        dumps_cell(normalized["editor_history"]),
        str(normalized["editor_version"]),
        normalized["editor_updated_by"],
        normalized["editor_updated_at"],
        normalized["final_pdf_url"],
        str(normalized["final_pdf_version"]),
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
            "editor_content": loads_cell(payload.get("editor_content_json"), {}),
            "editor_original": loads_cell(payload.get("editor_original_json"), {}),
            "editor_history": loads_cell(payload.get("editor_history_json"), []),
            "editor_version": payload.get("editor_version"),
            "editor_updated_by": payload.get("editor_updated_by"),
            "editor_updated_at": payload.get("editor_updated_at"),
            "final_pdf_url": payload.get("final_pdf_url"),
            "final_pdf_version": payload.get("final_pdf_version"),
        }
    )


def read_studies_from_sheet() -> list[tuple[int, dict[str, Any]]]:
    ensure_studies_sheet()
    settings = get_settings()
    service = get_service()
    result = service.spreadsheets().values().get(
        spreadsheetId=settings.google_sheets_id,
        range=f"'{STUDIES_SHEET_NAME}'!A:X",
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
        range=f"'{STUDIES_SHEET_NAME}'!A{row_number}:X{row_number}",
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
    raw_snapshot = payload.study_snapshot or ({"schema": "motor360-selection/v1", "groups": payload.grupos_selecionados} if payload.grupos_selecionados else None)
    selected_groups = []
    if raw_snapshot:
        selected_groups = raw_snapshot.get("groups") if isinstance(raw_snapshot, dict) else None
        if not isinstance(selected_groups, list) or not selected_groups:
            raise ValueError("Snapshot da composição ausente ou inválido.")
        for selected_group in selected_groups:
            group_id = str((selected_group or {}).get("grupo") or (selected_group or {}).get("grupo_id") or "").strip()
            scenarios = {str(item.get("id")) for item in (selected_group or {}).get("cenarios", []) if isinstance(item, dict)}
            if not group_id or not {"without_embedded", "with_embedded"}.issubset(scenarios):
                raise ValueError("Cada grupo do snapshot deve possuir os cenários sem e com lance embutido.")
        grupo_data = selected_groups[0]
        financeiro = _snapshot_financeiro({"schema": str(raw_snapshot.get("schema") or "motor360-selection/v1"), "groups": selected_groups})
        cenario = None
    else:
        cenario = payload.cenario
        financeiro = build_financeiro(payload, grupo_data)
    if sheets_enabled():
        existing_items = [item for _, item in read_studies_from_sheet()]
        estudo_id, proposal_id = next_study_identifiers(existing_items)
    else:
        _counter += 1
        _proposal_counter += 1
        estudo_id = f"EST-{datetime.now().year}-{_counter:05d}"
        proposal_id = f"ID {_proposal_counter:04d}"
    empty_editor = default_editor_content()
    study_item = {
        "estudo_id": estudo_id,
        "proposal_id": proposal_id,
        "cliente": payload.cliente.model_dump(),
        "grupo_id": payload.grupo_id,
        "grupo": grupo_data,
        "cenario": cenario,
        "study_snapshot": {"schema": str(raw_snapshot.get("schema") or "motor360-selection/v1"), "groups": selected_groups} if raw_snapshot else None,
        "grupos_selecionados": selected_groups,
        "financeiro": financeiro,
        "template_campos": {**payload.template_campos, "__editor_content": empty_editor, "__editor_original": empty_editor, "__editor_history": []},
        "editor_content": empty_editor,
        "editor_original": empty_editor,
        "editor_history": [],
        "editor_version": 1,
        "editor_updated_by": operador or "Não informado",
        "editor_updated_at": criado_em,
        "final_pdf_version": 0,
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


def _validated_study_snapshot(payload: EstudoPreviewRequest) -> dict[str, Any]:
    raw_snapshot = payload.study_snapshot or {"schema": "motor360-selection/v1", "groups": payload.grupos_selecionados}
    groups = raw_snapshot.get("groups") if isinstance(raw_snapshot, dict) else None
    if not isinstance(groups, list) or not groups:
        raise ValueError("Snapshot da composição ausente. Retorne aos Grupos Selecionados e avance novamente.")
    schema = str(raw_snapshot.get("schema") or "motor360-selection/v1")
    required_scenarios = {"without_embedded", "with_embedded"}
    for group in groups:
        group_id = str((group or {}).get("grupo") or (group or {}).get("grupo_id") or "").strip()
        scenarios = {str(item.get("id")) for item in (group or {}).get("cenarios", []) if isinstance(item, dict)}
        if not group_id or not required_scenarios.issubset(scenarios):
            raise ValueError("Snapshot da composição incompleto. Cada grupo deve possuir os cenários sem e com lance embutido.")
        if schema == "motor360-selection/v2" and str((group or {}).get("selected_scenario_id") or "") not in required_scenarios:
            raise ValueError("Escolha o cenário para contratação de cada grupo antes de gerar o estudo.")
    return json.loads(json.dumps({
        "schema": schema,
        "captured_at": str(raw_snapshot.get("capturedAt") or raw_snapshot.get("captured_at") or datetime.now().isoformat(timespec="seconds")),
        "groups": groups,
    }, ensure_ascii=False))


def _snapshot_financeiro(snapshot: dict[str, Any]) -> dict[str, Any]:
    summaries: dict[str, dict[str, float]] = {}
    for scenario_id in ("without_embedded", "with_embedded"):
        totals = {"credito_liquido": 0.0, "credito_contratado": 0.0, "lance_embutido": 0.0, "parcela_inicial": 0.0, "saldo_devedor": 0.0}
        for group in snapshot["groups"]:
            quota_count = max(1, int(group.get("quota_count") or 1))
            scenario = next((item for item in group.get("cenarios", []) if item.get("id") == scenario_id), {})
            for field in totals:
                totals[field] += float(scenario.get(field) or 0) * quota_count
        summaries[scenario_id] = totals
    return {
        "source": "motor360_selected_groups_snapshot",
        "scenario_summaries": summaries,
        "credito": summaries["without_embedded"]["credito_liquido"],
        "credito_original": summaries["without_embedded"]["credito_contratado"],
        "parcela_inicial": summaries["without_embedded"]["parcela_inicial"],
        "lance_embutido": 0.0,
        "estrategia_recomendada": "Comparativo por grupo e cenário",
        "estrategias": [],
        "historico_12_meses": {},
    }


def build_estudo_preview(payload: EstudoPreviewRequest, grupo: dict | None = None, operador: str = "") -> dict:
    has_snapshot = bool(payload.study_snapshot or payload.grupos_selecionados)
    if has_snapshot:
        snapshot = _validated_study_snapshot(payload)
        selected_groups = snapshot["groups"]
        grupo_data = selected_groups[0]
        financeiro = _snapshot_financeiro(snapshot)
        cenario = None
    else:
        # Compatibilidade exclusiva para prévias legadas de um grupo que trazem
        # grupo e cenário explicitamente; jamais é usada pela nova composição.
        grupo_data = payload.grupo or grupo or {}
        if not grupo_data or not payload.cenario:
            raise ValueError("Snapshot da composição ausente. Retorne aos Grupos Selecionados e avance novamente.")
        selected_groups = []
        snapshot = None
        estudo_payload = EstudoRequest(cliente=payload.cliente, grupo_id=payload.grupo_id, cenario=payload.cenario, template_campos=payload.template_campos)
        financeiro = build_financeiro(estudo_payload, grupo_data)
        cenario = payload.cenario
    return {
        "estudo_id": "PREVIEW",
        "proposal_id": "PREVIEW",
        "cliente": payload.cliente.model_dump(),
        "grupo_id": str(grupo_data.get("grupo") or grupo_data.get("grupo_id") or payload.grupo_id),
        "grupo": grupo_data,
        "cenario": cenario,
        "financeiro": financeiro,
        "template_campos": payload.template_campos,
        "estrategia": financeiro["estrategia_recomendada"],
        "status": "Previa",
        "operador": operador or "Não informado",
        "criado_em": datetime.now().isoformat(timespec="seconds"),
        "study_snapshot": snapshot,
        "grupos_selecionados": selected_groups,
    }


def build_estudo_audit_payload(
    payload: EstudoPreviewRequest,
    grupo: dict | None = None,
    operador: str = "",
    *,
    motor360_audit: dict[str, Any] | None = None,
    group_audit: list[dict[str, Any]] | None = None,
    pdf_engine_status: dict[str, Any] | None = None,
) -> dict[str, Any]:
    estudo = build_estudo_preview(payload, grupo=grupo, operador=operador)
    settings = get_settings()
    grupo_data = grupo or payload.grupo or {}
    return {
        "audit_type": "financial_study_runtime",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "system": {
            "app": settings.app_name,
            "version": settings.version,
            "environment": settings.environment,
        },
        "study": {
            "mode": "preview",
            "engine_target": "react-pdf",
            "operador": operador or "Não informado",
            "grupo_id": str(payload.grupo_id),
            "administradora": grupo_data.get("administradora") or grupo_data.get("adm") or "",
        },
        "request_payload": payload.model_dump(),
        "resolved_group": grupo_data,
        "study_preview": estudo,
        "pdf_engine_status": pdf_engine_status or {},
        "group_audit_trail": list(group_audit or []),
        "motor360_audit_id": payload.motor360_audit_id,
        "motor360_audit_snapshot": motor360_audit,
        "selected_groups_snapshot": payload.grupos_selecionados,
    }


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


def update_estudo_editor(estudo_id: str, editor_content: dict[str, Any], operador: str = "") -> dict | None:
    allowed = set(EDITOR_DEFAULTS)
    clean = normalize_editor_content(editor_content)
    clean["custom_sections"] = clean["custom_sections"] if isinstance(clean["custom_sections"], list) else []
    for key in ("study_financial", "selection_criteria", "how_consorcio_works", "strategy_explanation", "important_considerations"):
        clean[key] = re.sub(r"<(?!/?(?:strong|b|em|i|ul|ol|li|p|br)\b)[^>]*>", "", str(clean[key] or ""), flags=re.I)[:5000]
    clean["custom_sections"] = [
        {"title": re.sub(r"<[^>]+>", "", str(section.get("title") or ""))[:120], "text": re.sub(r"<(?!/?(?:strong|b|em|i|ul|ol|li|p|br)\b)[^>]*>", "", str(section.get("text") or ""), flags=re.I)[:3000]}
        for section in clean["custom_sections"] if isinstance(section, dict) and str(section.get("text") or "").strip()
    ]
    if sheets_enabled():
        for row_number, item in read_studies_from_sheet():
            if item.get("estudo_id") != estudo_id:
                continue
            history = list(item.get("editor_history") or [])
            version = int(item.get("editor_version") or 1) + 1
            edited_at = datetime.now().isoformat(timespec="seconds")
            original = normalize_editor_content(item.get("editor_original"), True)
            history.append({"version": version, "content": clean, "original": original, "edited_at": edited_at, "edited_by": operador or "Não informado"})
            item["template_campos"] = {**(item.get("template_campos") or {}), "__editor_content": clean, "__editor_original": original, "__editor_history": history}
            item["editor_content"] = clean
            item["editor_original"] = original
            item["editor_version"] = version
            item["editor_history"] = history
            item["editor_updated_at"] = edited_at
            item["editor_updated_by"] = operador or "Não informado"
            write_study_row_to_sheet(row_number, item)
            return item
        return None
    item = _studies.get(estudo_id)
    if not item:
        return None
    item["editor_original"] = normalize_editor_content(item.get("editor_original"), True)
    item["editor_content"] = clean
    item["editor_version"] = int(item.get("editor_version") or 1) + 1
    item["editor_updated_at"] = datetime.now().isoformat(timespec="seconds")
    item["editor_updated_by"] = operador or "Não informado"
    item.setdefault("editor_history", []).append({"version": item["editor_version"], "content": clean, "original": item["editor_original"], "edited_at": item["editor_updated_at"], "edited_by": item["editor_updated_by"]})
    save_studies_to_disk()
    return item


def restore_estudo_editor(estudo_id: str, version: int | None = None) -> dict | None:
    item = get_estudo(estudo_id)
    if not item:
        return None
    target = normalize_editor_content(item.get("editor_original"), True)
    if version is not None:
        for entry in item.get("editor_history") or []:
            if int(entry.get("version") or 0) == int(version):
                target = entry.get("content") or target
                break
    return update_estudo_editor(estudo_id, target, item.get("operador") or "Não informado")


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


def export_estudo_pdf_payload(estudo: dict, output_dir: Path, filename: str | None = None) -> str:
    output_dir.mkdir(parents=True, exist_ok=True)
    target_filename = filename or f"{estudo.get('estudo_id', 'estudo')}.pdf"
    path = output_dir / target_filename
    path.write_bytes(build_pdf_bytes(study_pdf_lines(estudo)))
    return target_filename


def export_estudo_pdf(estudo_id: str, output_dir: Path) -> str | None:
    estudo = get_estudo(estudo_id)
    if not estudo:
        return None
    return export_estudo_pdf_payload(estudo, output_dir, filename=f"{estudo_id}.pdf")
