"""Motor 360 orchestration: consolidation, eligibility, ranking and audit.

The financial formulas live exclusively in :mod:`motor360_math`.  This module
only composes the profile and the official group-base fields defined by RFC 001.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import math
import re
import time
from typing import Any

from .config import get_settings
from .motor360_auditoria import new_audit_id
from .motor360_math import ScenarioInput, calculate_scenario, money, normalize_percent, parse_decimal
from .viabilidade import compatible_tipo_bem, normalize_text


MOTOR_VERSION = "4.0.0"
RULES_VERSION = "RFC-001-architecture-v4.0"
STRATEGY_TARGETS = (
    ("urgent", "lance_super_agressivo_3m", "BP", "Urgente - 3 meses"),
    ("fast", "lance_agressivo_6m", "BO", "Rapido - 6 meses"),
    ("moderate", "lance_moderado_12m", "BN", "Moderado - 12 meses"),
    ("conservative", "lance_conservador_24m", "BM", "Conservador - 24 meses"),
    ("long_term", "lance_investidor", "BL", "Investidor - 36 meses"),
)


def map_declared_objective_to_preference(objective: str) -> str | None:
    """Map the declared objective only for presentation and ranking priority."""
    text = normalize_text(objective)
    if text.startswith("investidor"):
        return "investment"
    if not text.startswith("contemplar"):
        return None
    if "investidor" in text or "36 mes" in text:
        return "long_term"
    if "conservador" in text or "24 mes" in text:
        return "conservative"
    if "moderado" in text or "12 mes" in text:
        return "moderate"
    if "rapido" in text or "6 mes" in text:
        return "fast"
    if "urgente" in text or "3 mes" in text:
        return "urgent"
    return None


def _active_status(value: Any) -> tuple[bool, str]:
    status = normalize_text(str(value or ""))
    if status == "ativo":
        return True, "active"
    return False, "missing" if not status else "inactive"


def _positive_integer(value: Any) -> int | None:
    parsed = parse_decimal(value)
    if parsed is None or parsed <= 0 or parsed != parsed.to_integral_value():
        return None
    return int(parsed)


def _ranges(group: dict[str, Any]) -> tuple[dict[str, Any], dict[str, float | None]]:
    raw = {key: group.get(field) for key, field, _, _ in STRATEGY_TARGETS}
    return raw, {key: (float(normalize_percent(raw[key])) if normalize_percent(raw[key]) is not None else None) for key in raw}


def _strategy_matches(percentual_lance: float | None, ranges: dict[str, float | None]) -> list[str]:
    if percentual_lance is None:
        return []
    return [key for key, _, _, _ in STRATEGY_TARGETS if ranges.get(key) is not None and percentual_lance >= ranges[key]]


def _scenario_reasons(scenario: dict[str, Any], matches: list[str], has_ranges: bool) -> list[str]:
    reasons: list[str] = []
    if scenario["creation_status"] != "created":
        reasons.append(str(scenario["creation_reason"] or "cenario_nao_criado"))
        return reasons
    if scenario["credito_minimo"] is None:
        reasons.append("credito_minimo_nao_informado")
    if scenario["credito_maximo"] is None:
        reasons.append("credito_maximo_nao_informado")
    if scenario["taxa_administracao"] is None:
        reasons.append("taxa_administracao_nao_informada")
    if scenario["fundo_reserva"] is None:
        reasons.append("fundo_reserva_nao_informado")
    if scenario["prazo_apos_lance_limite_renda_meses"] is None:
        reasons.append("prazo_restante_nao_informado")
    if scenario["credit_compatible"] is False:
        reasons.append("credito_fora_da_faixa")
    if scenario["term_compatible"] is False:
        reasons.append("prazo_remanescente_insuficiente")
    if not has_ranges:
        reasons.append("faixas_contemplacao_nao_informadas")
    elif not matches:
        reasons.append("lance_abaixo_das_faixas")
    if scenario["liquidez_preservada"] is False:
        reasons.append("credito_liquido_nao_preservado")
    return reasons


def _reference_name(strategy: str | None) -> str | None:
    return next((label for key, _, _, label in STRATEGY_TARGETS if key == strategy), None)


def _audit_field(name: str, technical: str, value: Any, source: str, transformation: str) -> dict[str, Any]:
    return {
        "field_name": name,
        "technical_name": technical,
        "raw_value": value,
        "normalized_value": value,
        "source": source,
        "source_reference": "Perfil do Cliente" if source == "client_profile" else "Configuracao do sistema",
        "transformation": transformation,
        "validation_status": "warning" if value in (None, "") else "valid",
        "warnings": ["Valor nao informado."] if value in (None, "") else [],
    }


def analyze_client_consortium_viability(
    payload: Any,
    groups: list[dict[str, Any]],
    commitment_percent: float = 0.30,
    mode: str = "current",
) -> dict[str, Any]:
    """Execute the single Motor 360 flow from RFC 001 and Architecture v4.0."""
    started_at, started_clock = datetime.now(timezone.utc), time.perf_counter()
    desired = parse_decimal(getattr(payload, "credito_desejado", None))
    participants = parse_decimal(getattr(payload, "lance_proprio_participantes", None))
    manual = parse_decimal(getattr(payload, "lance_proprio_manual", None))
    declared_own = parse_decimal(getattr(payload, "lance_proprio", None))
    own_source = str(getattr(payload, "own_resources_source", "") or "").strip().lower()
    if own_source == "participants":
        own = participants if participants is not None else (declared_own or parse_decimal(0))
    elif own_source == "manual":
        own = manual if manual is not None else (declared_own or parse_decimal(0))
    else:
        own = declared_own or participants or manual or parse_decimal(0)
    fgts = parse_decimal(getattr(payload, "fgts", None)) or parse_decimal(0)
    income = parse_decimal(getattr(payload, "renda_total", None))
    desired_installment = parse_decimal(getattr(payload, "parcela_desejada", None)) or parse_decimal(getattr(payload, "parcela_ideal", None))
    configured_limit = parse_decimal(getattr(payload, "parcela_limite", None))
    if desired is None or desired <= 0:
        raise ValueError("credito_desejado_invalido")
    if income is None or income <= 0:
        raise ValueError("renda_total_invalida")
    if desired_installment is None or desired_installment <= 0:
        raise ValueError("parcela_desejada_invalida")
    commitment = parse_decimal(commitment_percent) or parse_decimal("0.30")
    income_limit = configured_limit or income * commitment
    if income_limit <= 0:
        raise ValueError("parcela_maxima_invalida")

    if (
        own_source not in {"participants", "manual"}
        and manual is not None
        and participants is not None
        and manual != participants
    ):
        raise ValueError("conflito_recurso_proprio")

    objective = str(getattr(payload, "objetivo", "") or "")
    preference = map_declared_objective_to_preference(objective)
    explicit_type = bool(getattr(payload, "tipo_bem_explicit", False))
    requested_type = str(getattr(payload, "tipo_bem", "") or "") if explicit_type else ""
    counters = Counter()
    durations = Counter()
    eligible_items: list[dict[str, Any]] = []
    credit_eligible_items: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    incomplete_groups: list[dict[str, Any]] = []
    group_results: list[dict[str, Any]] = []

    for group in groups:
        group_ref = {
            "grupo": str(group.get("grupo") or group.get("grupo_id") or "-"),
            "administradora": str(group.get("administradora") or "-"),
        }
        step_started = time.perf_counter()
        active, status_reason = _active_status(group.get("status"))
        durations["status"] += time.perf_counter() - step_started
        if not active:
            counters["status_rejected"] += 1
            excluded.append({**group_ref, "reason": "status_nao_informado" if status_reason == "missing" else "status_inativo", "detail": f"Status recebido: {group.get('status') or '-'}"})
            group_results.append({**group_ref, "result": "rejected", "justification": [excluded[-1]["reason"]], "scenarios": []})
            continue
        counters["active"] += 1

        step_started = time.perf_counter()
        compatible_type = not explicit_type or compatible_tipo_bem("", str(group.get("tipo_bem") or ""), requested_type)
        durations["type"] += time.perf_counter() - step_started
        if not compatible_type:
            counters["type_rejected"] += 1
            excluded.append({**group_ref, "reason": "tipo_bem_incompativel", "detail": f"Solicitado: {requested_type}; grupo: {group.get('tipo_bem') or '-'}"})
            group_results.append({**group_ref, "result": "rejected", "justification": [excluded[-1]["reason"]], "scenarios": []})
            continue

        step_started = time.perf_counter()
        minimum = parse_decimal(group.get("credito_minimo"))
        maximum = parse_decimal(group.get("credito_maximo"))
        fee = normalize_percent(group.get("taxa_adm"))
        fund = normalize_percent(group.get("fundo_reserva"))
        embedded = normalize_percent(group.get("percentual_lance_embutido"), allow_one=False)
        remaining_term = _positive_integer(group.get("prazo_restante", group.get("prazo_remanescente")))
        raw_ranges, ranges = _ranges(group)
        has_ranges = any(value is not None for value in ranges.values())
        scenario_input = ScenarioInput(
            credito_liquido_desejado=desired,
            recurso_proprio=own,
            fgts=fgts,
            parcela_desejada=desired_installment,
            parcela_maxima_renda=income_limit,
            credito_minimo=minimum,
            credito_maximo=maximum,
            taxa_administracao_total=fee,
            fundo_reserva_total=fund,
            prazo_remanescente=remaining_term,
            percentual_embutido=embedded,
        )
        scenarios = []
        for with_embedded in (False, True):
            scenario = calculate_scenario(scenario_input, with_embedded=with_embedded).to_dict()
            scenario["credito_minimo"] = money(minimum)
            scenario["credito_maximo"] = money(maximum)
            matches = _strategy_matches(scenario["percentual_lance"], ranges)
            scenario["compatible_contemplation_strategies"] = matches
            scenario["contemplation_compatible"] = bool(matches) if has_ranges else None
            scenario["eligibility_reasons"] = _scenario_reasons(scenario, matches, has_ranges)
            scenario["eligible"] = (
                scenario["creation_status"] == "created"
                and scenario["data_complete"]
                and scenario["credit_compatible"] is True
                and scenario["term_compatible"] is True
                and scenario["contemplation_compatible"] is True
                and scenario["liquidez_preservada"] is True
            )
            scenario["recommendable"] = scenario["eligible"]
            scenarios.append(scenario)
        durations["scenario"] += time.perf_counter() - step_started
        credit_scenarios = [
            scenario for scenario in scenarios
            if (
                scenario["creation_status"] == "created"
                and scenario["credit_compatible"] is True
                and scenario["liquidez_preservada"] is True
            )
        ]
        term_scenarios = [
            scenario for scenario in credit_scenarios
            if scenario["data_complete"] and scenario["term_compatible"] is True
        ]
        # The official architecture has a dedicated administrator stage.  Its
        # detailed rules are not yet specified, therefore it records a pass
        # without inventing a restriction.
        administrator_scenarios = list(term_scenarios)
        contemplation_scenarios = [
            scenario for scenario in administrator_scenarios
            if scenario["contemplation_compatible"] is True
        ]
        approved_scenarios = contemplation_scenarios
        source_values = {
            "prazo_restante": remaining_term,
            "credito_minimo": money(minimum),
            "credito_maximo": money(maximum),
            "taxa_adm": money(fee),
            "fundo_reserva": money(fund),
            "percentual_lance_embutido": money(embedded),
            "faixas_lance": ranges,
        }
        missing_fields = [
            {"field": "Crédito mínimo", "column": "O"} if minimum is None else None,
            {"field": "Crédito máximo", "column": "U"} if maximum is None else None,
            {"field": "Taxa ADM total", "column": "AC"} if fee is None else None,
            {"field": "Fundo de reserva total", "column": "AA"} if fund is None else None,
            {"field": "Prazo remanescente", "column": "F"} if remaining_term is None else None,
            {"field": "Faixas de contemplação", "column": "BL:BP"} if not has_ranges else None,
        ]
        missing_fields = [field for field in missing_fields if field]
        if missing_fields:
            incomplete_groups.append({**group_ref, "missing_fields": missing_fields})
        stage_results = {
            "credito": {"approved": bool(credit_scenarios), "scenario_ids": [scenario["id"] for scenario in credit_scenarios], "rule": "O <= crédito contratado <= U"},
            "prazo": {"approved": bool(term_scenarios), "scenario_ids": [scenario["id"] for scenario in term_scenarios], "rule": "F >= ceil(saldo após lance / parcela máxima)"},
            "administradora": {"approved": bool(administrator_scenarios), "scenario_ids": [scenario["id"] for scenario in administrator_scenarios], "rule": "Sem regra adicional definida"},
            "contemplacao": {"approved": bool(contemplation_scenarios), "scenario_ids": [scenario["id"] for scenario in contemplation_scenarios], "rule": "Lance do cliente >= uma faixa BL:BP"},
        }
        counters["credit_approved"] += int(bool(credit_scenarios))
        counters["credit_rejected"] += int(not credit_scenarios)
        counters["term_approved"] += int(bool(term_scenarios))
        counters["term_rejected"] += int(bool(credit_scenarios) and not term_scenarios)
        counters["administrator_approved"] += int(bool(administrator_scenarios))
        counters["contemplation_approved"] += int(bool(contemplation_scenarios))
        counters["contemplation_rejected"] += int(bool(administrator_scenarios) and not contemplation_scenarios)
        if credit_scenarios:
            credit_matches = [strategy for scenario in credit_scenarios for strategy in scenario["compatible_contemplation_strategies"]]
            credit_distinct_matches = [key for key, _, _, _ in STRATEGY_TARGETS if key in credit_matches]
            credit_selected = credit_scenarios[0]
            credit_eligible_items.append({
                **group_ref,
                "grupo_id": str(group.get("grupo_id") or group_ref["grupo"]),
                "tipo_bem": str(group.get("tipo_bem") or ""),
                "credito_minimo": money(minimum),
                "credito_maximo": money(maximum),
                "prazo_restante": remaining_term,
                "prazo_remanescente": remaining_term,
                "taxa_total": money(fee),
                "taxa_ano": money(normalize_percent(group.get("taxa_adm_ano"))),
                "lance_embutido": money(embedded),
                "parcela_reduzida": money(parse_decimal(group.get("parcela_reduzida"))),
                "reference_installment": money(parse_decimal(group.get("parcela_inicial_grupo"))),
                "installment_source": "planilha coluna AJ (referencia)",
                "cenarios": scenarios,
                "eligible_scenarios": [scenario["id"] for scenario in approved_scenarios],
                "credit_compatible": True,
                "term_compatible": any(scenario["term_compatible"] is True for scenario in credit_scenarios),
                "income_compatible": any(scenario["income_compatible"] is True for scenario in credit_scenarios),
                "data_completeness": "complete" if any(scenario["data_complete"] for scenario in credit_scenarios) else "incomplete",
                "financial_data_complete": any(scenario["financial_data_complete"] for scenario in credit_scenarios),
                "recommendable": bool(approved_scenarios),
                "compatible_contemplation_strategies": credit_distinct_matches,
                "best_contemplation_strategy": _reference_name(preference if preference in credit_distinct_matches else (credit_distinct_matches[0] if credit_distinct_matches else None)),
                "destaque_preferencia": preference in credit_distinct_matches,
                "source_values": source_values,
                "alerts": sorted({reason for scenario in credit_scenarios for reason in scenario["eligibility_reasons"] if reason != "credito_fora_da_faixa"}),
                "selected_scenario": credit_selected["id"],
                "selection_stage": "credit",
                "stage_results": stage_results,
            })
        if not approved_scenarios:
            reasons = sorted({reason for scenario in scenarios for reason in scenario["eligibility_reasons"]})
            for reason in reasons:
                counters[reason] += 1
            excluded.append({**group_ref, "reason": reasons[0] if reasons else "nao_elegivel", "detail": ", ".join(reasons) or "Nenhum cenario aprovado."})
            group_results.append({**group_ref, "result": "rejected", "justification": reasons, "scenarios": scenarios, "source_values": source_values, "stage_results": stage_results, "missing_fields": missing_fields})
            continue

        all_matches = [strategy for scenario in approved_scenarios for strategy in scenario["compatible_contemplation_strategies"]]
        distinct_matches = [key for key, _, _, _ in STRATEGY_TARGETS if key in all_matches]
        best_strategy = preference if preference in distinct_matches else (distinct_matches[0] if distinct_matches else None)
        selected = approved_scenarios[0]
        item = {
            **group_ref,
            "grupo_id": str(group.get("grupo_id") or group_ref["grupo"]),
            "tipo_bem": str(group.get("tipo_bem") or ""),
            "credito_minimo": money(minimum),
            "credito_maximo": money(maximum),
            "prazo_restante": remaining_term,
            "prazo_remanescente": remaining_term,
            "taxa_total": money(fee),
            "taxa_ano": money(normalize_percent(group.get("taxa_adm_ano"))),
            "lance_embutido": money(embedded),
            "parcela_reduzida": money(parse_decimal(group.get("parcela_reduzida"))),
            "reference_installment": money(parse_decimal(group.get("parcela_inicial_grupo"))),
            "installment_source": "planilha coluna AJ (referencia)",
            "cenarios": scenarios,
            "eligible_scenarios": [scenario["id"] for scenario in approved_scenarios],
            "credit_compatible": True,
            "term_compatible": True,
            "income_compatible": True,
            "data_completeness": "complete",
            "financial_data_complete": True,
            "recommendable": True,
            "compatible_contemplation_strategies": distinct_matches,
            "best_contemplation_strategy": _reference_name(best_strategy),
            "destaque_preferencia": preference in distinct_matches,
            "source_values": source_values,
            "alerts": [],
            "selected_scenario": selected["id"],
            "selection_stage": "final",
            "stage_results": stage_results,
        }
        eligible_items.append(item)
        group_results.append({**group_ref, "result": "eligible", "justification": [], "scenarios": scenarios, "source_values": source_values, "stage_results": stage_results, "missing_fields": missing_fields})

    def ordering_key(item: dict[str, Any]) -> tuple[Any, ...]:
        number = re.search(r"\d+", item["grupo"])
        return (
            not item["destaque_preferencia"],
            -(item["prazo_restante"] or 0),
            item["taxa_total"] if item["taxa_total"] is not None else math.inf,
            int(number.group()) if number else math.inf,
        )

    eligible_items.sort(key=ordering_key)
    credit_eligible_items.sort(key=ordering_key)
    for rank, item in enumerate(eligible_items, 1):
        item["ranking"] = rank
    for rank, item in enumerate(credit_eligible_items, 1):
        item["ranking"] = rank
    for entry in group_results:
        match = next((item for item in eligible_items if item["grupo"] == entry["grupo"] and item["administradora"] == entry["administradora"]), None)
        entry["ranking"] = match["ranking"] if match else None

    completed_at = datetime.now(timezone.utc)
    settings = get_settings()
    client = {
        "objetivo_declarado": objective,
        "presentation_preference": preference,
        "tipo_bem": requested_type or None,
        "credito_liquido_desejado": money(desired),
        "own_resources_total": money(own),
        "fgts": money(fgts),
        "renda_total": money(income),
        "parcela_desejada": money(desired_installment),
        "parcela_maxima": money(income_limit),
        "percentual_comprometimento": float(commitment),
    }
    columns = [
        ("A", "Administradora", "administradora", "Identificacao"), ("B", "Grupo", "grupo", "Identificacao"),
        ("C", "Tipo de bem", "tipo_bem", "Filtro explicito"), ("F", "Prazo remanescente", "prazo_remanescente", "Elegibilidade de prazo"),
        ("O", "Menor Credito", "credito_minimo", "Limite inferior de credito"), ("U", "Maior Credito", "credito_maximo", "Limite superior de credito"),
        ("V", "Indexador", "indexador", "Parametro do grupo"), ("W", "Modalidades de assembleia", "modalidades_assembleia", "Parametro operacional"),
        ("X", "Lance embutido", "percentual_lance_embutido", "Cenario com embutido"), ("Y", "Calculo do embutido", "base_calculo_embutido", "Parametro operacional"),
        ("Z", "Modalidades do embutido", "modalidades_embutido", "Parametro operacional"), ("AA", "Fundo reserva total", "fundo_reserva", "Saldo devedor"),
        ("AC", "Taxa ADM total", "taxa_adm", "Saldo devedor"), ("AJ", "Parcela inicial", "parcela_inicial_grupo", "Referencia apos selecao da carta"),
        ("AK", "Parcela apos lance", "parcela_apos_lance_grupo", "Referencia apos selecao da carta"), ("AL", "Parcela reduzida", "parcela_reduzida", "Ranking configuravel"),
        *[(column, label, field, "Faixa de contemplacao") for _, field, column, label in STRATEGY_TARGETS],
    ]
    audit = {
        "metadata": {"audit_id": new_audit_id(completed_at), "started_at": started_at.isoformat(), "completed_at": completed_at.isoformat(), "duration_ms": round((time.perf_counter() - started_clock) * 1000, 2), "engine_version": MOTOR_VERSION, "rules_version": RULES_VERSION, "application_version": settings.version, "environment": settings.environment},
        "client_snapshot": {"raw_fields": [
            _audit_field("Objetivo declarado", "objetivo", objective, "client_profile", "Preferencia de apresentacao"),
            _audit_field("Credito liquido desejado", "credito_desejado", money(desired), "client_profile", "Decimal ROUND_HALF_UP"),
            _audit_field("Recurso proprio", "lance_proprio", money(own), "client_profile", "Consolidado"),
            _audit_field("FGTS", "fgts", money(fgts), "client_profile", "Consolidado"),
            _audit_field("Renda total", "renda_total", money(income), "client_profile", "Consolidado"),
            _audit_field("Parcela desejada", "parcela_desejada", money(desired_installment), "client_profile", "Decimal"),
            _audit_field("Parcela maxima", "parcela_maxima", money(income_limit), "system_configuration", "Renda x comprometimento"),
        ], "consolidated_values": client, "participants": getattr(payload, "titulares", []) or []},
        "data_source": {"source_name": "Tabela de Grupos 3.0", "current_or_historical": "historical" if mode == "historical_audit" else "current", "loaded_at": completed_at.isoformat(), "total_rows": len(groups)},
        "columns_used": [{"column": column, "header": header, "technical_field": field, "purpose": purpose, "used": True} for column, header, field, purpose in columns],
        "execution_steps": [
            {"order": 1, "id": "status", "name": "Status", "formula_or_rule": "Somente status Ativo", "input_count": len(groups), "approved_count": counters["active"], "rejected_count": counters["status_rejected"], "incomplete_count": 0, "duration_ms": round(durations["status"] * 1000, 3)},
            {"order": 2, "id": "type", "name": "Tipo de bem", "formula_or_rule": "Aplicado somente quando explicitamente informado", "input_count": counters["active"], "approved_count": counters["active"] - counters["type_rejected"], "rejected_count": counters["type_rejected"], "incomplete_count": 0, "duration_ms": round(durations["type"] * 1000, 3)},
            {"order": 3, "id": "credit", "name": "Faixa de credito", "formula_or_rule": "Cenarios independentes sem e com X; O <= credito contratado <= U", "input_count": counters["active"] - counters["type_rejected"], "approved_count": counters["credit_approved"], "rejected_count": counters["credit_rejected"], "incomplete_count": sum(1 for item in incomplete_groups if any(field["column"] in {"O", "U"} for field in item["missing_fields"])), "duration_ms": round(durations["scenario"] * 1000, 3)},
            {"order": 4, "id": "term", "name": "Prazo e renda", "formula_or_rule": "F >= ceil(saldo apos lance / parcela maxima); parcela desejada tambem permanece auditada", "input_count": counters["credit_approved"], "approved_count": counters["term_approved"], "rejected_count": counters["term_rejected"], "incomplete_count": sum(1 for item in incomplete_groups if any(field["column"] in {"F", "AA", "AC"} for field in item["missing_fields"])), "duration_ms": 0},
            {"order": 5, "id": "administrator_rules", "name": "Regras da administradora", "formula_or_rule": "Nenhuma regra adicional foi definida nos documentos oficiais; nenhuma exclusao aplicada.", "input_count": counters["term_approved"], "approved_count": counters["administrator_approved"], "rejected_count": 0, "incomplete_count": 0, "duration_ms": 0},
            {"order": 6, "id": "contemplation", "name": "Contemplacao", "formula_or_rule": "Lance do cliente >= pelo menos uma faixa BL:BP; objetivo declarado somente prioriza o ranking", "input_count": counters["administrator_approved"], "approved_count": counters["contemplation_approved"], "rejected_count": counters["contemplation_rejected"], "incomplete_count": sum(1 for item in incomplete_groups if any(field["column"] == "BL:BP" for field in item["missing_fields"])), "duration_ms": 0},
            {"order": 7, "id": "ranking", "name": "Ranking", "formula_or_rule": "Preferências configuráveis apenas reordenam os grupos finais", "input_count": counters["contemplation_approved"], "approved_count": len(eligible_items), "rejected_count": 0, "incomplete_count": 0, "duration_ms": 0},
        ],
        "formulas": [
            {"id": "base_liquida", "name": "Base liquida", "expression": "credito liquido desejado + recurso proprio + FGTS", "result": money(desired + own + fgts)},
            {"id": "credito_sem_embutido", "name": "Credito sem embutido", "expression": "base liquida", "result": money(desired + own + fgts)},
            {"id": "credito_com_embutido", "name": "Credito com embutido", "expression": "base liquida / (1 - X)", "result": "calculado por grupo"},
            {"id": "taxa", "name": "Taxa", "expression": "credito contratado x AC", "result": "calculado por cenario"},
            {"id": "fundo", "name": "Fundo", "expression": "credito contratado x AA", "result": "calculado por cenario"},
            {"id": "saldo", "name": "Saldo devedor", "expression": "credito + taxa + fundo", "result": "calculado por cenario"},
            {"id": "lance", "name": "Lance", "expression": "RP + FGTS (+ embutido)", "result": "calculado por cenario"},
            {"id": "prazo", "name": "Prazo", "expression": "ceil(saldo ou saldo apos lance / parcela)", "result": "calculado por cenario"},
        ],
        "group_results": group_results,
        "incomplete_groups": incomplete_groups,
        "excluded_groups": excluded,
        "final_ordering": {"rules": ["Preferencia declarada apenas prioriza", "Maior prazo remanescente", "Menor taxa administrativa total", "Numero do grupo"], "selected_preferences": [], "execution_summary": "O ranking e aplicado somente depois da elegibilidade; ele nao elimina grupos."},
        "summary": {"total_loaded": len(groups), "total_analyzed": len(groups), "total_recommended": len(eligible_items), "total_credit_compatible": len(credit_eligible_items), "total_incomplete": sum(1 for item in excluded if "nao_informado" in item["detail"]), "total_rejected": len(excluded)},
        "warnings": [
            {"level": "info", "message": "O/U participa exclusivamente da elegibilidade de crédito. AJ, AK e AL são referências e não aprovam nem eliminam grupos nesta fase."},
            {"level": "info", "message": "As fórmulas de crédito contratado, saldo devedor e prazo são registradas por cenário e por grupo na auditoria."},
        ],
    }
    return {"motor": "360", "base_mode": mode, "objetivo_declarado": objective, "preferencia_declarada": preference, "cliente": client, "total_grupos_analisados": len(groups), "total_grupos_credito_compativeis": len(credit_eligible_items), "total_grupos_viaveis": len(eligible_items), "contadores": dict(counters), "passos": ["Perfil consolidado.", "Cenarios sem e com embutido calculados de forma independente.", "Faixa de credito aplicada por O/U.", "Prazo F, renda e lance BL:BP aplicados aos compatíveis por crédito.", "Ranking aplicado apenas aos grupos elegiveis finais."], "items": eligible_items, "credit_items": credit_eligible_items, "audit": audit}
