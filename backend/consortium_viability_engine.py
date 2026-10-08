"""Motor 360 orchestration: consolidation, eligibility, ranking and audit.

The financial formulas live exclusively in :mod:`motor360_math`.  This module
only composes the profile and the official group-base fields defined by RFC 001.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
import re
import time
from decimal import Decimal
from typing import Any

from .config import get_settings
from .motor360_auditoria import new_audit_id
from .motor360_math import ScenarioInput, calculate_scenario, money, normalize_percent, parse_decimal
from .viabilidade import compatible_tipo_bem, normalize_text


MOTOR_VERSION = "4.0.118"
RULES_VERSION = "RFC-001-architecture-v4.0"
STRATEGY_TARGETS = (
    ("urgent", "lance_super_agressivo_3m", "BP", "Urgente - 3 meses"),
    ("fast", "lance_agressivo_6m", "BO", "Rapido - 6 meses"),
    ("moderate", "lance_moderado_12m", "BN", "Moderado - 12 meses"),
    ("conservative", "lance_conservador_24m", "BM", "Conservador - 24 meses"),
    ("long_term", "lance_investidor", "BL", "Investidor - 36 meses"),
)

CONTEMPLATION_PROFILE_TARGETS = (
    ("conservative", "Conservador", "conservative"),
    ("moderate", "Moderado", "moderate"),
    ("aggressive", "Agressivo", "fast"),
    ("super_aggressive", "Super Agressivo", "urgent"),
)

CONTEMPLATION_CAPACITY_WINDOWS = {
    "urgent": 3,
    "fast": 6,
    "moderate": 12,
    "conservative": 12,
    "long_term": 12,
}


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


def _group_feature_flags(group: dict[str, Any]) -> dict[str, bool]:
    embedded_percent = normalize_percent(group.get("percentual_lance_embutido"), allow_one=False) or Decimal("0")
    embedded_text = normalize_text(str(group.get("modalidades_embutido") or group.get("base_calculo_embutido") or ""))
    reduced_value = parse_decimal(group.get("parcela_reduzida"))
    reduced_text = normalize_text(str(group.get("parcela_reduzida") or ""))
    return {
        "lance_embutido": embedded_percent > 0 or bool(embedded_text and embedded_text not in {"nao", "não", "n", "nenhum"}),
        "parcela_reduzida": (reduced_value is not None and reduced_value > 0) or reduced_text not in {"", "nao", "não", "n", "0", "0,00", "0.00"},
    }


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
    # Contemplation ranges are informational during pre-selection. They do
    # not eliminate a group before the later classification/ranking phase.
    if scenario["liquidez_preservada"] is False:
        reasons.append("credito_liquido_nao_preservado")
    return reasons


def _reference_name(strategy: str | None) -> str | None:
    return next((label for key, _, _, label in STRATEGY_TARGETS if key == strategy), None)


def _contemplation_capacity(group: dict[str, Any]) -> dict[str, dict[str, Any]]:
    history = [
        item for item in (group.get("historico_12_meses") or [])
        if item.get("qtd_contemplacoes") is not None
    ]
    capacities: dict[str, dict[str, Any]] = {}
    for strategy, months in CONTEMPLATION_CAPACITY_WINDOWS.items():
        quantities = [int(item["qtd_contemplacoes"]) for item in history[-months:]]
        total = sum(quantities)
        average = round(total / len(quantities), 2) if quantities else None
        capacities[strategy] = {
            "perfil": _reference_name(strategy),
            "janela_meses": months,
            "meses_com_dados": len(quantities),
            "quantidades": quantities,
            "total_contemplacoes": total,
            "media_contemplacoes": average,
            "limite_cotas": math.floor(average) if average is not None else None,
            "fonte": "Quantidades mensais de contemplacoes da planilha oficial",
        }
    return capacities


def _parcela_inicial_por_cenario(scenario: dict[str, Any]) -> float | None:
    """Calculate the initial installment from the client's contracted credit.

    AJ is a later card reference. It must not replace this preliminary
    calculation, which uses the scenario debt balance and column F.
    """
    saldo = parse_decimal(scenario.get("saldo_devedor"))
    prazo = scenario.get("prazo_remanescente")
    if saldo is None or prazo is None or int(prazo) <= 0:
        return None
    return money(saldo / Decimal(str(int(prazo))))


def _parcela_pos_contemplacao_por_cenario(scenario: dict[str, Any]) -> float | None:
    """Calculate the installment after contemplation for one financial scenario."""
    saldo = parse_decimal(scenario.get("saldo_devedor"))
    parcela_inicial = parse_decimal(scenario.get("parcela_inicial"))
    lance_total = parse_decimal(scenario.get("lance_total_cenario"))
    prazo = scenario.get("prazo_remanescente")
    if (
        saldo is None
        or parcela_inicial is None
        or lance_total is None
        or prazo is None
        or int(prazo) <= 1
    ):
        return None
    return money(
        (saldo - parcela_inicial - lance_total)
        / Decimal(str(int(prazo) - 1))
    )


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
    request_id: str | None = None,
) -> dict[str, Any]:
    """Execute the single Motor 360 flow from RFC 001 and Architecture v4.0."""
    started_at, started_clock = datetime.now(timezone.utc), time.perf_counter()
    desired = parse_decimal(getattr(payload, "credito_desejado", None))
    participants = parse_decimal(getattr(payload, "lance_proprio_participantes", None))
    manual = parse_decimal(getattr(payload, "lance_proprio_manual", None))
    declared_own = parse_decimal(getattr(payload, "lance_proprio", None))
    declared_bid = parse_decimal(getattr(payload, "lance_proprio_declarado", None))
    simulated_bid = parse_decimal(getattr(payload, "lance_simulado", None))
    own_source = str(getattr(payload, "own_resources_source", "") or "").strip().lower()
    if own_source == "participants":
        own = participants if participants is not None else (declared_own or parse_decimal(0))
    elif own_source == "manual":
        own = manual if manual is not None else (declared_own or parse_decimal(0))
    else:
        own = declared_own or participants or manual or parse_decimal(0)
    if simulated_bid is not None and own == simulated_bid and simulated_bid != declared_bid:
        effective_bid_source = "simulado"
    elif own_source == "manual":
        effective_bid_source = "manual"
    else:
        effective_bid_source = "declarado"
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
    selected_profile = str(getattr(payload, "contemplacao_perfil", "") or "").strip().lower()
    if selected_profile not in {key for key, _, _, _ in STRATEGY_TARGETS}:
        selected_profile = None
    selected_profile_row = {"urgent": "super_aggressive", "fast": "aggressive", "moderate": "moderate", "conservative": "conservative", "long_term": "investor"}.get(selected_profile)
    explicit_type = bool(getattr(payload, "tipo_bem_explicit", False))
    requested_type = str(getattr(payload, "tipo_bem", "") or "") if explicit_type else ""
    counters = Counter()
    durations = Counter()
    eligible_items: list[dict[str, Any]] = []
    credit_eligible_items: list[dict[str, Any]] = []
    composition_items: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    incomplete_groups: list[dict[str, Any]] = []
    group_results: list[dict[str, Any]] = []

    for group in groups:
        group_ref = {
            "grupo": str(group.get("grupo") or group.get("grupo_id") or "-"),
            "grupo_raw": str(group.get("grupo_raw") or group.get("grupo") or group.get("grupo_id") or "-"),
            "administradora": str(group.get("administradora") or "-"),
            "vencimento_parcela": str(group.get("vencimento_parcela") or ""),
            "source_row": group.get("source_row"),
        }
        # Rows without the two parts of the business key are invalid source
        # records. Keep them in the audit, but never expose them as a matrix
        # candidate or a selectable group.
        if group_ref["grupo"] == "-" or group_ref["administradora"] == "-":
            counters["invalid_identity"] += 1
            excluded.append({**group_ref, "reason": "identificacao_grupo_invalida", "detail": "Administradora e número do grupo são obrigatórios para análise."})
            group_results.append({**group_ref, "result": "excluded_invalid_identity", "justification": ["identificacao_grupo_invalida"], "scenarios": [], "missing_fields": []})
            continue
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

        feature_flags = _group_feature_flags(group)
        requested_embedded = str(getattr(payload, "filtro_lance_embutido", "") or "").strip().lower()
        requested_reduced = str(getattr(payload, "filtro_parcela_reduzida", "") or "").strip().lower()
        scenario_filter = {"with_embedded"} if requested_embedded == "sim" else {"without_embedded"} if requested_embedded == "nao" else {"with_embedded", "without_embedded"}
        # The scenario filter is applied after both financial scenarios and
        # the selected profile are evaluated. A group may support both
        # scenarios, so filtering by the group's capability here would wrongly
        # remove it from the other valid scenario (e.g. group 1031).
        if requested_reduced in {"sim", "nao"} and feature_flags["parcela_reduzida"] != (requested_reduced == "sim"):
            counters["reduced_installment_filter_rejected"] += 1
            excluded.append({**group_ref, "reason": "filtro_parcela_reduzida", "detail": f"Grupo {'possui' if feature_flags['parcela_reduzida'] else 'não possui'} parcela reduzida; filtro: {requested_reduced}."})
            group_results.append({**group_ref, "result": "excluded_group_filter", "justification": ["filtro_parcela_reduzida"], "scenarios": []})
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
            scenario["parcela_inicial"] = _parcela_inicial_por_cenario(scenario)
            scenario["parcela_inicial_formula"] = "saldo devedor / prazo remanescente (coluna F)"
            client_bid = own + fgts
            contracted_credit = parse_decimal(scenario.get("credito_contratado"))
            embedded_amount = parse_decimal(scenario.get("valor_lance_embutido")) or Decimal("0")
            total_bid = client_bid + embedded_amount
            client_bid_percent = (
                client_bid / contracted_credit
                if contracted_credit is not None and contracted_credit > 0
                else None
            )
            total_bid_percent = (
                total_bid / contracted_credit
                if contracted_credit is not None and contracted_credit > 0
                else None
            )
            scenario["lance_cliente_total"] = money(client_bid)
            scenario["lance_embutido"] = money(embedded_amount)
            scenario["lance_total_cenario"] = money(total_bid)
            scenario["percentual_lance_cliente"] = float(client_bid_percent) if client_bid_percent is not None else None
            scenario["percentual_lance_efetivo"] = float(total_bid_percent) if total_bid_percent is not None else None
            scenario["parcela_pos_contemplacao"] = _parcela_pos_contemplacao_por_cenario(scenario)
            scenario["parcela_pos_contemplacao_formula"] = "(saldo devedor - parcela inicial - lance total ofertado) / (prazo remanescente - 1)"
            profile_rows = []
            for profile_id, label, strategy_key in CONTEMPLATION_PROFILE_TARGETS:
                threshold = ranges.get(strategy_key)
                threshold_decimal = Decimal(str(threshold)) if threshold is not None else None
                ideal_total_bid = contracted_credit * threshold_decimal if contracted_credit is not None and threshold_decimal is not None else None
                required_client_bid = (
                    max(Decimal("0"), ideal_total_bid - embedded_amount)
                    if ideal_total_bid is not None
                    else None
                )
                profile_rows.append({
                    "id": profile_id,
                    "label": label,
                    "percentual_referencia": threshold,
                    # The ideal client bid is the total profile bid less the
                    # embedded portion already financed by the credit.
                    "lance_ideal": money(required_client_bid),
                    "lance_ideal_total": money(ideal_total_bid),
                    "lance_embutido": money(embedded_amount),
                    "lance_cliente": money(client_bid),
                    "percentual_lance_efetivo": float(total_bid_percent) if total_bid_percent is not None else None,
                    "falta_para_ideal": money(max(Decimal("0"), required_client_bid - client_bid)) if required_client_bid is not None else None,
                    "atinge_perfil": total_bid_percent is not None and threshold is not None and total_bid_percent >= threshold,
                })
            scenario["perfis_contemplacao"] = profile_rows
            matches = _strategy_matches(total_bid_percent, ranges)
            scenario["compatible_contemplation_strategies"] = matches
            scenario["contemplation_compatible"] = bool(matches) if has_ranges else None
            scenario["eligibility_reasons"] = _scenario_reasons(scenario, matches, has_ranges)
            scenario["eligible"] = (
                scenario["creation_status"] == "created"
                and scenario["data_complete"]
                and scenario["credit_compatible"] is True
                and scenario["term_compatible"] is True
                and scenario["liquidez_preservada"] is True
            )
            scenario["recommendable"] = scenario["eligible"]
            scenarios.append(scenario)
        parcelas_iniciais = {
            scenario["id"]: _parcela_inicial_por_cenario(scenario)
            for scenario in scenarios
        }
        durations["scenario"] += time.perf_counter() - step_started
        step_started = time.perf_counter()
        credit_scenarios = [
            scenario for scenario in scenarios
            if (
                scenario["creation_status"] == "created"
                and scenario["credit_compatible"] is True
                and scenario["liquidez_preservada"] is True
            )
        ]
        durations["credit_decision"] += time.perf_counter() - step_started
        step_started = time.perf_counter()
        term_scenarios = [
            scenario for scenario in credit_scenarios
            if scenario["data_complete"] and scenario["term_compatible"] is True
        ]
        durations["term"] += time.perf_counter() - step_started
        # The official architecture has a dedicated administrator stage.  Its
        # detailed rules are not yet specified, therefore it records a pass
        # without inventing a restriction.
        step_started = time.perf_counter()
        administrator_scenarios = list(term_scenarios)
        durations["administrator_rules"] += time.perf_counter() - step_started
        step_started = time.perf_counter()
        contemplation_scenarios = [
            scenario for scenario in scenarios
            if scenario["id"] in scenario_filter and scenario["contemplation_compatible"] is True
        ]
        selected_profile_scenarios = [
            scenario for scenario in scenarios
            if scenario["id"] in scenario_filter and selected_profile_row is not None and any(
                profile.get("id") == selected_profile_row and profile.get("atinge_perfil") is True
                for profile in scenario.get("perfis_contemplacao", [])
            )
        ]
        durations["contemplation"] += time.perf_counter() - step_started
        # An explicit client profile makes contemplation the first eligibility gate.
        approved_scenarios = [
            scenario for scenario in term_scenarios
            if scenario["id"] in scenario_filter
            if selected_profile is None
            or any(profile.get("id") == selected_profile_row and profile.get("atinge_perfil") is True for profile in scenario.get("perfis_contemplacao", []))
        ]
        contemplation_capacities = _contemplation_capacity(group)
        source_values = {
            "filtros_grupo": feature_flags,
            "prazo_restante": remaining_term,
            "credito_minimo": money(minimum),
            "credito_maximo": money(maximum),
            "taxa_adm": money(fee),
            "fundo_reserva": money(fund),
            "vencimento_parcela": str(group.get("vencimento_parcela") or ""),
            "percentual_lance_embutido": money(embedded),
            "faixas_lance": ranges,
            "capacidade_contemplacoes": contemplation_capacities,
            "mapeamento_origem": group.get("mapeamento_origem") or {},
        }
        composition_item: dict[str, Any] | None = None
        composition_rejection_reason: str | None = None
        if (
            maximum is not None
            and maximum > 0
            and maximum < desired
            and maximum * Decimal("50") >= desired
            and fee is not None
            and fund is not None
            and remaining_term is not None
        ):
            composition_scenarios = []
            for with_embedded in (False, True):
                scenario_id = "with_embedded" if with_embedded else "without_embedded"
                if scenario_id not in scenario_filter:
                    continue
                if with_embedded and (embedded is None or embedded <= 0 or embedded >= 1):
                    continue
                embedded_amount = maximum * (embedded or Decimal("0")) if with_embedded else Decimal("0")
                liquid_credit = maximum - embedded_amount
                minimum_quotas = math.ceil(desired / liquid_credit) if liquid_credit > 0 else None
                fee_amount = maximum * fee
                fund_amount = maximum * fund
                balance = maximum + fee_amount + fund_amount
                initial_installment = balance / Decimal(remaining_term)
                profile_rows = []
                for profile_id, label, strategy_key in CONTEMPLATION_PROFILE_TARGETS:
                    threshold = ranges.get(strategy_key)
                    threshold_decimal = Decimal(str(threshold)) if threshold is not None else None
                    ideal_total = maximum * threshold_decimal if threshold_decimal is not None else None
                    ideal_client = max(Decimal("0"), ideal_total - embedded_amount) if ideal_total is not None else None
                    total_bid = own + fgts + embedded_amount
                    total_bid_percent = total_bid / maximum if maximum > 0 else None
                    profile_rows.append({
                        "id": profile_id,
                        "label": label,
                        "percentual_referencia": threshold,
                        "lance_ideal": money(ideal_client),
                        "lance_ideal_total": money(ideal_total),
                        "lance_embutido": money(embedded_amount),
                        "lance_cliente": money(own + fgts),
                        "percentual_lance_efetivo": float(total_bid_percent) if total_bid_percent is not None else None,
                        "atinge_perfil": total_bid_percent is not None and threshold_decimal is not None and total_bid_percent >= threshold_decimal,
                        "falta_para_ideal": money(max(Decimal("0"), ideal_client - (own + fgts))) if ideal_client is not None else None,
                    })
                composition_scenarios.append({
                    "id": scenario_id,
                    "credito_contratado": money(maximum),
                    "credito_liquido_projetado": money(liquid_credit),
                    "cotas_minimas": minimum_quotas,
                    "lance_embutido": money(embedded_amount),
                    "saldo_devedor": money(balance),
                    "parcela_inicial": money(initial_installment),
                    "credito_total_minimo": money(liquid_credit * Decimal(minimum_quotas)) if minimum_quotas else None,
                    "parcela_total_minima": money(initial_installment * Decimal(minimum_quotas)) if minimum_quotas else None,
                    "parcela_maxima_compatível": bool(minimum_quotas and initial_installment * Decimal(minimum_quotas) <= income_limit),
                    "perfis_contemplacao": profile_rows,
                    "credit_compatible": True,
                    "term_compatible": None,
                    "composition_candidate": True,
                })
            composition_financial_scenarios = [
                scenario for scenario in composition_scenarios
                if (
                    scenario.get("cotas_minimas") is not None
                    and 1 <= int(scenario["cotas_minimas"]) <= 50
                    and (parse_decimal(scenario.get("credito_total_minimo")) or Decimal("0")) >= desired
                    and scenario.get("parcela_maxima_compatível") is True
                    and (
                        not selected_profile
                        or any(
                            profile.get("id") == selected_profile_row and profile.get("atinge_perfil") is True
                            for profile in scenario.get("perfis_contemplacao", [])
                        )
                    )
                )
            ]
            eligible_composition_ids = {scenario["id"] for scenario in composition_financial_scenarios}
            for scenario in composition_scenarios:
                scenario["eligible"] = scenario["id"] in eligible_composition_ids
            selected_composition_scenario = composition_financial_scenarios[0] if composition_financial_scenarios else None
            if selected_composition_scenario:
                composition_capacity_key = preference if preference in contemplation_capacities else next(iter(contemplation_capacities), "")
                composition_item = {
                    **group_ref,
                    "grupo_id": str(group.get("grupo_id") or group_ref["grupo"]),
                    "tipo_bem": str(group.get("tipo_bem") or ""),
                    "credito_minimo": money(minimum),
                    "credito_maximo": money(maximum),
                    "prazo_restante": remaining_term,
                    "prazo_remanescente": remaining_term,
                    "taxa_adm": money(fee),
                    "fundo_reserva": money(fund),
                    "taxa_total": money(fee),
                    "taxa_ano": money(normalize_percent(group.get("taxa_adm_ano"))),
                    "lance_embutido": money(embedded),
                    "cenarios": composition_scenarios,
                    "capacidade_contemplacoes": contemplation_capacities,
                    "capacidade_contemplacoes_selecionada": contemplation_capacities.get(composition_capacity_key or ""),
                    "historico_12_meses": list(group.get("historico_12_meses") or []),
                    "best_contemplation_strategy": _reference_name(composition_capacity_key),
                    "selected_composition_scenario": selected_composition_scenario["id"],
                    "selection_stage": "composition",
                    "composition_candidate": True,
                    "cotas_minimas_sem_embutido": next((scenario["cotas_minimas"] for scenario in composition_scenarios if scenario["id"] == "without_embedded"), None),
                    "cotas_minimas_com_embutido": next((scenario["cotas_minimas"] for scenario in composition_scenarios if scenario["id"] == "with_embedded"), None),
                    "cotas_maximas": 50,
                }
                composition_items.append(composition_item)
            elif any(
                scenario.get("cotas_minimas") is not None
                and 1 <= int(scenario["cotas_minimas"]) <= 50
                and (parse_decimal(scenario.get("credito_total_minimo")) or Decimal("0")) >= desired
                for scenario in composition_scenarios
            ):
                composition_rejection_reason = "composicao_parcela_maxima_excedida"
            else:
                composition_rejection_reason = "composicao_credito_insuficiente_ou_limite_cotas"
        missing_fields = [
            {"field": "Credito minimo", "column": "O", "raw_value": group.get("credito_minimo"), "reason": "Necessario para validar a faixa de credito.", "impact": "group_excluded"} if minimum is None else None,
            {"field": "Credito maximo", "column": "U", "raw_value": group.get("credito_maximo"), "reason": "Necessario para validar a faixa de credito.", "impact": "group_excluded"} if maximum is None else None,
            {"field": "Taxa ADM total", "column": "AC", "raw_value": group.get("taxa_adm"), "reason": "Necessaria para calcular saldo e prazo.", "impact": "scenario_unavailable"} if fee is None else None,
            {"field": "Fundo de reserva total", "column": "AA", "raw_value": group.get("fundo_reserva"), "reason": "Necessario para calcular saldo e prazo.", "impact": "scenario_unavailable"} if fund is None else None,
            {"field": "Prazo remanescente", "column": "F", "raw_value": group.get("prazo_restante", group.get("prazo_remanescente")), "reason": "Necessario para validar prazo/renda.", "impact": "group_excluded"} if remaining_term is None else None,
            {"field": "Faixas de contemplacao", "column": "BL:BP", "raw_value": json.dumps(raw_ranges, ensure_ascii=False, sort_keys=True), "reason": "Usadas somente na classificacao informativa posterior.", "impact": "informational_only"} if not has_ranges else None,
        ]
        missing_fields = [field for field in missing_fields if field]
        if missing_fields:
            incomplete_groups.append({**group_ref, "missing_fields": missing_fields})
        matrix_data_incomplete = bool(administrator_scenarios) and (
            not has_ranges
            or any(field["column"] == "BL:BP" for field in missing_fields)
        )
        if administrator_scenarios:
            counters["matrix_incomplete"] += int(matrix_data_incomplete)
            counters["matrix_evaluated"] += int(not matrix_data_incomplete)
        if selected_profile and administrator_scenarios and not matrix_data_incomplete and not selected_profile_scenarios:
            counters["selected_profile_rejected"] += 1
        stage_results = {
            "credito": {"approved": bool(credit_scenarios), "scenario_ids": [scenario["id"] for scenario in credit_scenarios], "rule": "O <= crédito contratado <= U"},
            "prazo": {"approved": bool(term_scenarios), "scenario_ids": [scenario["id"] for scenario in term_scenarios], "rule": "F >= ceil(saldo após lance / parcela máxima)"},
            "administradora": {"approved": bool(administrator_scenarios), "scenario_ids": [scenario["id"] for scenario in administrator_scenarios], "rule": "Sem regra adicional definida"},
            "contemplacao": {"approved": bool(selected_profile_scenarios if selected_profile else contemplation_scenarios), "scenario_ids": [scenario["id"] for scenario in (selected_profile_scenarios if selected_profile else contemplation_scenarios)], "perfil_selecionado": selected_profile, "rule": "Lance do cliente >= faixa do perfil selecionado" if selected_profile else "Lance do cliente >= uma faixa BL:BP"},
            "composicao": {"approved": bool(composition_item), "scenario_ids": [composition_item["selected_composition_scenario"]] if composition_item else [], "rule": "Crédito e parcela total compatíveis em até 50 cotas"},
        }
        counters["credit_approved"] += int(bool(credit_scenarios))
        counters["credit_rejected"] += int(not credit_scenarios)
        counters["term_approved"] += int(bool(term_scenarios))
        counters["term_rejected"] += int(bool(credit_scenarios) and not term_scenarios)
        counters["administrator_approved"] += int(bool(administrator_scenarios))
        counters["contemplation_approved"] += int(bool(selected_profile_scenarios if selected_profile else contemplation_scenarios))
        counters["contemplation_rejected"] += int(bool(administrator_scenarios) and not (selected_profile_scenarios if selected_profile else contemplation_scenarios))
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
                "taxa_adm": money(fee),
                "fundo_reserva": money(fund),
                "taxa_total": money(fee),
                "taxa_ano": money(normalize_percent(group.get("taxa_adm_ano"))),
                "lance_embutido": money(embedded),
                "parcela_reduzida": money(parse_decimal(group.get("parcela_reduzida"))),
                "reference_installment": parcelas_iniciais.get("without_embedded"),
                "parcela_inicial_sem_embutido": parcelas_iniciais.get("without_embedded"),
                "parcela_inicial_com_embutido": parcelas_iniciais.get("with_embedded"),
                "installment_source": "saldo devedor da categoria / prazo remanescente (coluna F)",
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
                "capacidade_contemplacoes": contemplation_capacities,
                "capacidade_contemplacoes_selecionada": contemplation_capacities.get(preference if preference in credit_distinct_matches else (credit_distinct_matches[0] if credit_distinct_matches else "")),
                "historico_12_meses": list(group.get("historico_12_meses") or []),
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
            if composition_item:
                group_results.append({**group_ref, "result": "composition", "justification": [], "scenarios": scenarios, "source_values": source_values, "stage_results": stage_results, "missing_fields": missing_fields})
                continue
            if composition_rejection_reason:
                reason = composition_rejection_reason
                consolidated_reasons = [composition_rejection_reason]
            elif selected_profile and term_scenarios and not selected_profile_scenarios:
                reason = "lance_insuficiente_para_perfil"
                counters[reason] += 1
            else:
                reason = "prazo_remanescente_insuficiente" if credit_scenarios and not term_scenarios else (reasons[0] if reasons else "nao_elegivel")
            if composition_rejection_reason:
                consolidated_reasons = [composition_rejection_reason]
            elif selected_profile and term_scenarios and not selected_profile_scenarios:
                consolidated_reasons = ["lance_insuficiente_para_perfil"]
            elif credit_scenarios and not term_scenarios:
                incomplete_reasons = [reason for reason in reasons if reason.endswith("nao_informada") or reason.endswith("nao_informado")]
                consolidated_reasons = incomplete_reasons or ["prazo_remanescente_insuficiente"]
            else:
                consolidated_reasons = reasons
            excluded.append({**group_ref, "reason": reason, "detail": ", ".join(consolidated_reasons) or "Nenhum cenario aprovado."})
            exclusion_result = "excluded_composition" if composition_rejection_reason else ("excluded_contemplation" if selected_profile and term_scenarios and not selected_profile_scenarios else ("excluded_term_income" if credit_scenarios else "excluded_credit"))
            group_results.append({**group_ref, "result": exclusion_result, "justification": consolidated_reasons, "scenarios": scenarios, "source_values": source_values, "stage_results": stage_results, "missing_fields": missing_fields})
            continue

        all_matches = [strategy for scenario in approved_scenarios for strategy in scenario["compatible_contemplation_strategies"]]
        distinct_matches = [key for key, _, _, _ in STRATEGY_TARGETS if key in all_matches]
        best_strategy = preference if preference in distinct_matches else (distinct_matches[0] if distinct_matches else None)
        ignored_contemplation_scenarios = [
            {
                "scenario_id": scenario["id"],
                "reason": next((reason for reason in scenario["eligibility_reasons"] if reason in {"credito_fora_da_faixa", "prazo_remanescente_insuficiente", "credito_liquido_nao_preservado"}), "cenario_nao_preselecionado"),
            }
            for scenario in scenarios
            if scenario not in approved_scenarios
        ]
        contemplation_classification = {
            "eligible_scenarios_only": True,
            "strategies": distinct_matches,
            "ignored_scenarios": ignored_contemplation_scenarios,
        }
        selected = approved_scenarios[0]
        history_quality_alerts = [
            "historico_menor_maior_inconsistente"
            for entry in (group.get("historico_12_meses") or [])
            if entry.get("menor_lance") is not None and entry.get("maior_lance") is not None and parse_decimal(entry.get("menor_lance")) > parse_decimal(entry.get("maior_lance"))
        ]
        item = {
            **group_ref,
            "grupo_id": str(group.get("grupo_id") or group_ref["grupo"]),
            "tipo_bem": str(group.get("tipo_bem") or ""),
            "credito_minimo": money(minimum),
            "credito_maximo": money(maximum),
            "prazo_restante": remaining_term,
            "prazo_remanescente": remaining_term,
            "taxa_adm": money(fee),
            "fundo_reserva": money(fund),
            "taxa_total": money(fee),
            "taxa_ano": money(normalize_percent(group.get("taxa_adm_ano"))),
            "lance_embutido": money(embedded),
            "parcela_reduzida": money(parse_decimal(group.get("parcela_reduzida"))),
            "reference_installment": parcelas_iniciais.get("without_embedded"),
            "parcela_inicial_sem_embutido": parcelas_iniciais.get("without_embedded"),
            "parcela_inicial_com_embutido": parcelas_iniciais.get("with_embedded"),
            "installment_source": "saldo devedor da categoria / prazo remanescente (coluna F)",
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
            "capacidade_contemplacoes": contemplation_capacities,
            "capacidade_contemplacoes_selecionada": contemplation_capacities.get(best_strategy or ""),
            "historico_12_meses": list(group.get("historico_12_meses") or []),
            "contemplation_classification": contemplation_classification,
            "destaque_preferencia": preference in distinct_matches,
            "source_values": source_values,
            "alerts": sorted(set(history_quality_alerts)),
            "selected_scenario": selected["id"],
            "selection_stage": "preselection",
            "stage_results": stage_results,
        }
        eligible_items.append(item)
        group_results.append({**group_ref, "result": "preselected", "justification": [], "scenarios": scenarios, "source_values": source_values, "stage_results": stage_results, "missing_fields": missing_fields, "contemplation_classification": contemplation_classification})

    matrix_approved_keys = {
        (str(entry.get("administradora") or "").strip().lower(), str(entry.get("grupo") or "").strip())
        for entry in group_results
        if entry.get("stage_results", {}).get("contemplacao", {}).get("approved") is True
    }
    if selected_profile:
        eligible_items = [item for item in eligible_items if (str(item.get("administradora") or "").strip().lower(), str(item.get("grupo") or "").strip()) in matrix_approved_keys]
        credit_eligible_items = [item for item in credit_eligible_items if (str(item.get("administradora") or "").strip().lower(), str(item.get("grupo") or "").strip()) in matrix_approved_keys]
        composition_items = [item for item in composition_items if (str(item.get("administradora") or "").strip().lower(), str(item.get("grupo") or "").strip()) in matrix_approved_keys]

    def ordering_key(item: dict[str, Any]) -> tuple[Any, ...]:
        number = re.search(r"\d+", str(item.get("grupo") or ""))
        return (
            -(item.get("prazo_restante") or 0),
            item.get("taxa_total") if item.get("taxa_total") is not None else math.inf,
            normalize_text(item.get("administradora") or ""),
            int(number.group()) if number else math.inf,
        )

    step_started = time.perf_counter()
    eligible_items.sort(key=ordering_key)
    credit_eligible_items.sort(key=ordering_key)
    composition_items.sort(key=ordering_key)
    for rank, item in enumerate(eligible_items, 1):
        item["ranking"] = rank
    for rank, item in enumerate(credit_eligible_items, 1):
        item["ranking"] = rank
    for rank, item in enumerate(composition_items, 1):
        item["ranking"] = rank
    for entry in group_results:
        match = next((item for item in eligible_items if item["grupo"] == entry["grupo"] and item["administradora"] == entry["administradora"]), None)
        entry["ranking"] = match["ranking"] if match else None
    durations["ranking"] += time.perf_counter() - step_started

    incomplete_field_occurrences = sum(len(item["missing_fields"]) for item in incomplete_groups)
    contemplation_classified_count = sum(
        bool(item.get("contemplation_classification", {}).get("strategies"))
        for item in eligible_items
    )
    contemplation_unclassified_count = len(eligible_items) - contemplation_classified_count

    completed_at = datetime.now(timezone.utc)
    settings = get_settings()
    client = {
        "objetivo_declarado": objective,
        "presentation_preference": preference,
        "tipo_bem": requested_type or None,
        "credito_liquido_desejado": money(desired),
        "own_resources_total": money(own),
        "own_resources_declared": money(declared_bid if declared_bid is not None else own),
        "simulated_bid": money(simulated_bid if simulated_bid is not None else own),
        "effective_bid": money(own),
        "effective_bid_source": effective_bid_source,
        "fgts": money(fgts),
        "lance_cliente_total": money(own + fgts),
        "renda_total": money(income),
        "parcela_desejada": money(desired_installment),
        "parcela_maxima": money(income_limit),
        "percentual_comprometimento": float(commitment),
    }
    columns = [
        ("A", "Administradora", "administradora", "Identificacao"), ("B", "Grupo", "grupo", "Identificacao"),
        ("C", "Tipo de bem", "tipo_bem", "Filtro explicito"), ("F", "Prazo remanescente", "prazo_remanescente", "Elegibilidade de prazo"),
        ("O", "Menor Credito", "credito_minimo", "Limite inferior de credito"), ("U", "Maior Credito", "credito_maximo", "Limite superior de credito"),
        ("W", "Indexador", "indexador", "Parametro do grupo"), ("X", "Modalidades de assembleia", "modalidades_assembleia", "Parametro operacional"),
        ("Y", "Lance embutido", "percentual_lance_embutido", "Cenario com embutido"), ("Z", "Calculo do embutido", "base_calculo_embutido", "Parametro operacional"),
        ("AA", "Modalidades do embutido", "modalidades_embutido", "Parametro operacional"), ("AB", "Fundo reserva total", "fundo_reserva", "Saldo devedor"),
        ("AD", "Taxa ADM total", "taxa_adm", "Saldo devedor"), ("AJ", "Parcela inicial", "parcela_inicial_grupo", "Referencia apos selecao da carta"),
        ("AK", "Parcela apos lance", "parcela_apos_lance_grupo", "Referencia apos selecao da carta"), ("AL", "Parcela reduzida", "parcela_reduzida", "Ranking configuravel"),
        *[(column, label, field, "Faixa de contemplacao") for _, field, column, label in STRATEGY_TARGETS],
    ]
    decision_columns = {"A", "B", "F", "O", "U", "Y", "AB", "AD"}
    if explicit_type:
        decision_columns.add("C")
    source_snapshot = [
        {
            "source_row": group.get("source_row"),
            "administradora": group.get("administradora"),
            "grupo_raw": group.get("grupo_raw", group.get("grupo")),
            "credito_minimo": group.get("credito_minimo"),
            "credito_maximo": group.get("credito_maximo"),
            "prazo_restante": group.get("prazo_restante"),
        }
        for group in groups
    ]
    source_fingerprint = hashlib.sha256(
        json.dumps(source_snapshot, ensure_ascii=True, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    mapping_by_administrator: dict[str, dict[str, dict[str, Any]]] = {}
    for group in groups:
        administrator = str(group.get("administradora") or "Não informado")
        administrator_mapping = mapping_by_administrator.setdefault(administrator, {})
        for field, mapping in (group.get("mapeamento_origem") or {}).items():
            entry = administrator_mapping.setdefault(field, {"headers": set(), "sources": set(), "mapped_rows": 0, "missing_rows": 0})
            if mapping.get("source") == "ausente":
                entry["missing_rows"] += 1
            else:
                entry["mapped_rows"] += 1
                entry["headers"].add(str(mapping.get("header") or "-"))
                entry["sources"].add(str(mapping.get("source") or "-"))
    for administrator_mapping in mapping_by_administrator.values():
        for entry in administrator_mapping.values():
            entry["headers"] = sorted(entry["headers"])
            entry["sources"] = sorted(entry["sources"])

    # Keep the audit contract aligned with the actual request. The analysis
    # evaluates both financial scenarios internally, but an explicit scenario
    # filter must not leave the other scenario visible in audit/group output.
    for entry in group_results:
        entry["scenarios"] = [
            scenario for scenario in (entry.get("scenarios") or [])
            if scenario.get("id") in scenario_filter
        ]
        stage_results = entry.get("stage_results") or {}
        for stage in stage_results.values():
            if isinstance(stage, dict) and isinstance(stage.get("scenario_ids"), list):
                stage["scenario_ids"] = [scenario_id for scenario_id in stage["scenario_ids"] if scenario_id in scenario_filter]

    audit = {
        "metadata": {"audit_id": new_audit_id(completed_at), "request_id": request_id, "started_at": started_at.isoformat(), "completed_at": completed_at.isoformat(), "duration_ms": round((time.perf_counter() - started_clock) * 1000, 2), "engine_version": MOTOR_VERSION, "rules_version": RULES_VERSION, "application_version": settings.version, "environment": settings.environment},
        "client_snapshot": {"raw_fields": [
            _audit_field("Objetivo declarado", "objetivo", objective, "client_profile", "Preferencia de apresentacao"),
            _audit_field("Credito liquido desejado", "credito_desejado", money(desired), "client_profile", "Decimal ROUND_HALF_UP"),
            _audit_field("Recurso proprio", "lance_proprio", money(own), "client_profile", "Consolidado"),
            _audit_field("Recurso proprio declarado", "lance_proprio_declarado", client["own_resources_declared"], "client_profile", "Valor declarado antes da simulação"),
            _audit_field("Lance simulado", "lance_simulado", client["simulated_bid"], "motor360_simulation", "Valor efetivamente usado na execução"),
            _audit_field("Lance efetivo utilizado", "lance_efetivo", client["effective_bid"], "motor360_simulation" if effective_bid_source == "simulado" else "client_profile", "Valor que determinou os cenários financeiros"),
            _audit_field("Fonte do lance efetivo", "fonte_lance_efetivo", effective_bid_source, "motor360_simulation" if effective_bid_source == "simulado" else "client_profile", "Declarado, manual ou simulado"),
            _audit_field("FGTS", "fgts", money(fgts), "client_profile", "Consolidado"),
            _audit_field("Renda total", "renda_total", money(income), "client_profile", "Consolidado"),
            _audit_field("Parcela desejada", "parcela_desejada", money(desired_installment), "client_profile", "Decimal"),
            _audit_field("Parcela maxima", "parcela_maxima", money(income_limit), "system_configuration", "Renda x comprometimento"),
        ], "consolidated_values": client, "participants": getattr(payload, "titulares", []) or []},
        "data_source": {"source_name": "Tabela de Grupos 3.0", "current_or_historical": "historical" if mode == "historical_audit" else "current", "loaded_at": completed_at.isoformat(), "total_rows": len(groups), "base_snapshot": {"row_count": len(groups), "fingerprint_algorithm": "sha256", "fingerprint": source_fingerprint}, "mapping_by_administrator": mapping_by_administrator},
        "parameters": {"commitment_percent": float(commitment), "requested_type": requested_type or None, "explicit_type_filter": bool(explicit_type), "base_mode": mode, "embedded_column": "Y", "decision_columns": sorted(decision_columns), "filtro_lance_embutido": requested_embedded or None, "cenarios_considerados": sorted(scenario_filter)},
        "columns_used": [{"column": column, "header": header, "technical_field": field, "purpose": purpose, "loaded": True, "used_in_decision": column in decision_columns, "used": column in decision_columns} for column, header, field, purpose in columns],
        "execution_steps": [
            {"order": 1, "id": "status", "name": "Status e identificação", "formula_or_rule": "Somente status Ativo e grupo com administradora/número válidos", "input_count": len(groups), "approved_count": counters["active"], "rejected_count": counters["status_rejected"] + counters["invalid_identity"], "incomplete_count": 0, "duration_ms": round(durations["status"] * 1000, 3)},
            {"order": 2, "id": "type", "name": "Tipo de bem", "formula_or_rule": "Aplicado somente quando explicitamente informado", "input_count": counters["active"], "approved_count": counters["active"] - counters["type_rejected"], "rejected_count": counters["type_rejected"], "incomplete_count": 0, "duration_ms": round(durations["type"] * 1000, 3)},
            {"order": 3, "id": "credit", "name": "Faixa de credito", "formula_or_rule": "Cenarios independentes sem e com X; O <= credito contratado <= U", "input_count": counters["active"] - counters["type_rejected"], "approved_count": counters["credit_approved"], "rejected_count": counters["credit_rejected"], "incomplete_count": sum(1 for item in incomplete_groups if any(field["column"] in {"O", "U"} for field in item["missing_fields"])), "duration_ms": round((durations["scenario"] + durations["credit_decision"]) * 1000, 3)},
            {"order": 4, "id": "term", "name": "Prazo e renda", "formula_or_rule": "F >= ceil(saldo apos lance / parcela maxima); parcela desejada tambem permanece auditada", "input_count": counters["credit_approved"], "approved_count": counters["term_approved"], "rejected_count": counters["term_rejected"], "incomplete_count": sum(1 for item in incomplete_groups if any(field["column"] in {"F", "AA", "AC"} for field in item["missing_fields"])), "duration_ms": round(durations["term"] * 1000, 3)},
            {"order": 5, "id": "administrator_rules", "name": "Regras da administradora", "formula_or_rule": "Nenhuma regra adicional foi definida nos documentos oficiais; nenhuma exclusao aplicada.", "input_count": counters["term_approved"], "approved_count": counters["administrator_approved"], "rejected_count": 0, "incomplete_count": 0, "duration_ms": round(durations["administrator_rules"] * 1000, 3)},
            {"order": 6, "id": "contemplation", "name": "Filtro de contemplacao", "formula_or_rule": "Com perfil selecionado, o lance efetivo deve atingir a faixa BL:BP correspondente; sem perfil explicito a classificacao permanece informativa", "input_count": counters["administrator_approved"], "approved_count": len(eligible_items), "rejected_count": counters["selected_profile_rejected"] if selected_profile else counters["contemplation_rejected"], "incomplete_count": sum(1 for item in incomplete_groups if any(field["column"] == "BL:BP" for field in item["missing_fields"])), "duration_ms": round(durations["contemplation"] * 1000, 3)},
            {"order": 7, "id": "ranking", "name": "Ranking", "formula_or_rule": "Preferências configuráveis apenas reordenam os grupos finais", "input_count": counters["contemplation_approved"], "approved_count": len(eligible_items), "rejected_count": 0, "incomplete_count": 0, "duration_ms": 0},
        ],
        "formulas": [
            {"id": "base_liquida", "name": "Base liquida", "expression": "credito liquido desejado", "result": money(desired)},
            {"id": "credito_sem_embutido", "name": "Credito sem embutido", "expression": "base liquida", "result": money(desired)},
            {"id": "credito_com_embutido", "name": "Credito com embutido", "expression": "base liquida / (1 - X)", "result": "calculado por grupo"},
            {"id": "taxa", "name": "Taxa", "expression": "credito contratado x AC", "result": "calculado por cenario"},
            {"id": "fundo", "name": "Fundo", "expression": "credito contratado x AA", "result": "calculado por cenario"},
            {"id": "saldo", "name": "Saldo devedor", "expression": "credito + taxa + fundo", "result": "calculado por cenario"},
            {"id": "parcela_inicial_sem_embutido", "name": "Parcela inicial sem lance embutido", "expression": "saldo devedor sem lance embutido / prazo remanescente (coluna F)", "result": "calculado por grupo"},
            {"id": "parcela_inicial_com_embutido", "name": "Parcela inicial com lance embutido", "expression": "saldo devedor com lance embutido / prazo remanescente (coluna F)", "result": "calculado por grupo"},
            {"id": "parcela_pos_contemplacao", "name": "Parcela pós-contemplação por cenário", "expression": "(saldo devedor - parcela inicial - lance total ofertado) / (prazo remanescente - 1)", "result": "calculado por grupo e cenário"},
            {"id": "lance_cliente", "name": "Lance ofertado pelo cliente", "expression": "RP + FGTS", "result": money(own + fgts)},
            {"id": "lance_cenario", "name": "Lance financeiro do cenario", "expression": "RP + FGTS + lance embutido quando aplicavel", "result": "calculado por cenario"},
            {"id": "prazo", "name": "Prazo", "expression": "ceil(saldo ou saldo apos lance / parcela)", "result": "calculado por cenario"},
        ],
        "group_results": group_results,
        "incomplete_groups": incomplete_groups,
        "excluded_groups": excluded,
        "final_ordering": {"rules": ["Maior prazo remanescente", "Menor taxa administrativa total", "Administradora", "Numero do grupo"], "selected_preferences": [], "execution_summary": "Esta e uma ordem preliminar da pre-selecao; ranking definitivo sera aplicado em etapa posterior."},
        "summary": {"total_loaded": len(groups), "total_analyzed": len(groups), "total_matrix_candidates": len(matrix_approved_keys), "total_matrix_evaluated": counters["matrix_evaluated"], "total_matrix_incomplete": counters["matrix_incomplete"], "total_matrix_rejected": counters["selected_profile_rejected"] if selected_profile else counters["contemplation_rejected"], "total_preselected": len(eligible_items), "total_composition_candidates": len(composition_items), "total_credit_compatible": len(credit_eligible_items), "total_credit_rejected": counters["credit_rejected"], "total_term_income_rejected": counters["term_rejected"], "total_selected_profile_rejected": counters["selected_profile_rejected"] if selected_profile else 0, "groups_with_incomplete_data": len(incomplete_groups), "incomplete_field_occurrences": incomplete_field_occurrences, "total_rejected": len(excluded)},
        "schema_notes": {"columns_used": {"official_decision_field": "used_in_decision", "compatibility_field": "used", "compatibility_note": "The used field mirrors used_in_decision for compatibility with prior consumers."}},
        "warnings": [
            {"level": "info", "message": "O/U participa exclusivamente da elegibilidade de crédito. AJ, AK e AL são referências e não aprovam nem eliminam grupos nesta fase."},
            {"level": "info", "message": "As fórmulas de crédito contratado, saldo devedor e prazo são registradas por cenário e por grupo na auditoria."},
        ],
    }
    def audit_key(entry: dict[str, Any]) -> tuple[str, str]:
        return (str(entry.get("administradora") or "").strip().lower(), str(entry.get("grupo") or "").strip())

    matrix_entries = [entry for entry in group_results if entry.get("stage_results", {}).get("contemplacao")]
    matrix_incomplete_entries = [
        entry for entry in matrix_entries
        if any(field.get("column") == "BL:BP" for field in entry.get("missing_fields", []))
    ]
    matrix_credit_keys = {
        audit_key(entry) for entry in matrix_entries
        if audit_key(entry) in matrix_approved_keys and entry.get("stage_results", {}).get("credito", {}).get("approved")
    }
    matrix_term_keys = {
        audit_key(entry) for entry in matrix_entries
        if audit_key(entry) in matrix_credit_keys and entry.get("stage_results", {}).get("prazo", {}).get("approved")
    }
    matrix_input_count = len(matrix_entries)
    matrix_incomplete_count = len(matrix_incomplete_entries)
    matrix_rejected_count = max(0, matrix_input_count - len(matrix_approved_keys) - matrix_incomplete_count)
    composition_keys = {audit_key(item) for item in composition_items}
    lower_list_keys = matrix_term_keys | composition_keys
    lower_list_count = len(lower_list_keys)
    initial_steps = audit["execution_steps"]
    audit["execution_steps"] = [
        initial_steps[0],
        initial_steps[1],
        {"order": 3, "id": "matrix", "name": "Matriz de contemplação", "formula_or_rule": "Lance efetivo (declarado ou simulado) >= faixa do perfil; o cenário aprovado é exibido na matriz.", "input_count": matrix_input_count, "approved_count": len(matrix_approved_keys), "rejected_count": matrix_rejected_count, "incomplete_count": matrix_incomplete_count, "duration_ms": round(durations["contemplation"] * 1000, 3)},
        {"order": 4, "id": "credit", "name": "Refinamento: faixa de crédito", "formula_or_rule": "Somente candidatos aprovados na matriz; O <= crédito contratado <= U.", "input_count": len(matrix_approved_keys), "approved_count": len(matrix_credit_keys), "rejected_count": max(0, len(matrix_approved_keys) - len(matrix_credit_keys)), "incomplete_count": 0, "duration_ms": round(durations["credit_decision"] * 1000, 3)},
        {"order": 5, "id": "term", "name": "Refinamento: prazo e renda", "formula_or_rule": "Somente candidatos aprovados em matriz e crédito; parcela e prazo devem respeitar o limite de renda.", "input_count": len(matrix_credit_keys), "approved_count": len(matrix_term_keys), "rejected_count": max(0, len(matrix_credit_keys) - len(matrix_term_keys)), "incomplete_count": 0, "duration_ms": round(durations["term"] * 1000, 3)},
        {"order": 6, "id": "preselection", "name": "Refinamento: 1 cota ou composição", "formula_or_rule": "Candidatos aprovados na matriz são classificados em 1 cota ou composição; composição exige crédito e parcela total compatíveis em até 50 cotas.", "input_count": len(lower_list_keys), "approved_count": lower_list_count, "rejected_count": 0, "incomplete_count": 0, "duration_ms": round(durations["administrator_rules"] * 1000, 3)},
        {"order": 7, "id": "preliminary_order", "name": "Ordem preliminar", "formula_or_rule": "Maior prazo remanescente, menor taxa administrativa total, administradora e grupo. Não é ranking final.", "input_count": lower_list_count, "approved_count": lower_list_count, "rejected_count": 0, "incomplete_count": 0, "duration_ms": round(durations["ranking"] * 1000, 3)},
    ]
    def matrix_eligible_scenarios(entry: dict[str, Any]) -> list[dict[str, Any]]:
        eligible = []
        for scenario in entry.get("scenarios", []):
            if scenario.get("id") not in scenario_filter:
                continue
            if selected_profile and not any(
                profile.get("id") == selected_profile_row and profile.get("atinge_perfil") is True
                for profile in scenario.get("perfis_contemplacao", [])
            ):
                continue
            eligible.append(scenario)
        return eligible

    matrix_items = []
    for entry in group_results:
        if str(entry.get("grupo") or "").strip() in {"", "-"} or str(entry.get("administradora") or "").strip() in {"", "-"}:
            continue
        eligible_scenarios = matrix_eligible_scenarios(entry)
        if not eligible_scenarios:
            continue
        matrix_items.append({
            "grupo": entry.get("grupo"),
            "administradora": entry.get("administradora"),
            "cenarios": entry.get("scenarios", []),
            "eligible_scenarios": [scenario.get("id") for scenario in eligible_scenarios],
            "stage_results": entry.get("stage_results", {}),
            "result": entry.get("result"),
            "missing_fields": entry.get("missing_fields", []),
        })
    def filter_output_scenarios(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        filtered_items = []
        for item in items:
            item["cenarios"] = [scenario for scenario in (item.get("cenarios") or []) if scenario.get("id") in scenario_filter]
            if isinstance(item.get("eligible_scenarios"), list):
                item["eligible_scenarios"] = [scenario_id for scenario_id in item["eligible_scenarios"] if scenario_id in scenario_filter]
            if item.get("selected_scenario") not in scenario_filter:
                item["selected_scenario"] = next((scenario_id for scenario_id in item.get("eligible_scenarios", []) if scenario_id in scenario_filter), None)
            if item.get("selected_composition_scenario") not in scenario_filter:
                item["selected_composition_scenario"] = next((scenario.get("id") for scenario in item.get("cenarios", [])), None)
            filtered_items.append(item)
        return filtered_items

    eligible_items = filter_output_scenarios(eligible_items)
    credit_eligible_items = filter_output_scenarios(credit_eligible_items)
    composition_items = filter_output_scenarios(composition_items)
    if len(scenario_filter) == 1:
        eligible_items = [item for item in eligible_items if item.get("eligible_scenarios")]
        credit_eligible_items = [item for item in credit_eligible_items if item.get("eligible_scenarios")]
        composition_items = [item for item in composition_items if item.get("selected_composition_scenario") in scenario_filter]
    detail_items = {}
    for item in [*eligible_items, *credit_eligible_items, *composition_items]:
        detail_items[(str(item.get("administradora") or "").strip().lower(), str(item.get("grupo") or "").strip())] = item
    final_items = []
    for matrix_item in matrix_items:
        key = (str(matrix_item.get("administradora") or "").strip().lower(), str(matrix_item.get("grupo") or "").strip())
        item = dict(detail_items.get(key) or matrix_item)
        item["cenarios"] = matrix_item.get("cenarios", item.get("cenarios", []))
        item["eligible_scenarios"] = matrix_item.get("eligible_scenarios", item.get("eligible_scenarios", []))
        item["matrix_approved"] = True
        item["selection_stage"] = "matrix"
        item["requires_composition"] = any(
            scenario.get("cotas_minimas") is not None and int(scenario.get("cotas_minimas") or 1) > 1
            for scenario in item.get("cenarios", [])
        ) or (parse_decimal(item.get("credito_maximo")) or Decimal("0")) < desired
        final_items.append(item)
    final_items.sort(key=ordering_key)
    for rank, item in enumerate(final_items, 1):
        item["ranking"] = rank
    final_keys = {
        (str(item.get("administradora") or "").strip().lower(), str(item.get("grupo") or "").strip())
        for item in final_items
    }
    for entry in audit.get("group_results", []):
        key = (str(entry.get("administradora") or "").strip().lower(), str(entry.get("grupo") or "").strip())
        if key in final_keys:
            entry["result"] = "matrix_approved"
            entry["matrix_approved"] = True
            entry["justification"] = []
    audit["parameters"]["post_matrix_selection"] = "matrix_approved_groups_only"
    audit["summary"]["total_post_matrix_groups"] = len(final_items)
    audit["summary"]["total_requires_composition"] = sum(1 for item in final_items if item.get("requires_composition"))
    audit["execution_steps"] = [
        audit["execution_steps"][0],
        audit["execution_steps"][1],
        {"order": 3, "id": "matrix", "name": "Matriz de contemplação", "formula_or_rule": "Lance efetivo atende à faixa do perfil selecionado no cenário permitido.", "input_count": len(groups), "approved_count": len(final_items), "rejected_count": max(0, len(groups) - len(final_items)), "incomplete_count": counters["matrix_incomplete"], "duration_ms": round(durations["contemplation"] * 1000, 3)},
        {"order": 4, "id": "operator_analysis", "name": "Indicadores para análise do operador", "formula_or_rule": "Crédito, prazo, renda, parcela e composição são informativos e não eliminam grupos aprovados na matriz.", "input_count": len(final_items), "approved_count": len(final_items), "rejected_count": 0, "incomplete_count": 0, "duration_ms": 0},
        {"order": 5, "id": "ranking", "name": "Ordem preliminar", "formula_or_rule": "Preferências configuráveis apenas reordenam os grupos aprovados na matriz.", "input_count": len(final_items), "approved_count": len(final_items), "rejected_count": 0, "incomplete_count": 0, "duration_ms": 0},
    ]
    administrators_analyzed = sorted({str(group.get("administradora") or "").strip() for group in groups if str(group.get("administradora") or "").strip()}, key=normalize_text)
    return {"motor": "360", "base_mode": mode, "objetivo_declarado": objective, "preferencia_declarada": preference, "perfil_contemplacao": selected_profile, "administradoras_analisadas": administrators_analyzed, "cliente": client, "total_grupos_analisados": len(groups), "total_grupos_credito_compativeis": len(credit_eligible_items), "total_grupos_preselecionados": len(final_items), "total_grupos_viaveis": len(final_items), "total_grupos_composicao": sum(1 for item in final_items if item.get("requires_composition")), "contadores": dict(counters), "passos": ["Perfil consolidado.", "Cenarios sem e com embutido calculados de forma independente por grupo.", "Matriz de contemplacao aplicada primeiro pelo lance e perfil em todas as administradoras.", "Indicadores de credito, prazo, renda e composicao calculados sem eliminar grupos aprovados na matriz.", "Grupos aprovados na matriz apresentados em lista unica para avaliacao do operador.", "Ordem preliminar aplicada sem ranking definitivo."], "items": final_items, "final_items": final_items, "credit_items": credit_eligible_items, "matrix_items": matrix_items, "composition_items": composition_items, "audit": audit}
