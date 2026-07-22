from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
import math
import re
import time
from typing import Any

from .config import get_settings
from .credit_liquidity import build_credit_liquidity_scenarios, normalize_cost_percent, normalize_embedded_bid_percent
from .motor360_auditoria import new_audit_id
from .viabilidade import compatible_tipo_bem, normalize_text


ALLOW_EMPTY_GROUP_STATUS = False
MONEY = Decimal("0.01")
STRATEGY_TARGETS = (
    ("urgent", "lance_super_agressivo_3m"), ("fast", "lance_agressivo_6m"),
    ("moderate", "lance_moderado_12m"), ("conservative", "lance_conservador_24m"),
    ("long_term", "lance_investidor"),
)


def _decimal(value: Any) -> Decimal | None:
    if value is None or value == "" or isinstance(value, bool):
        return None
    try:
        if isinstance(value, (int, float, Decimal)):
            parsed = Decimal(str(value))
        else:
            text = str(value).strip().replace("R$", "").replace(" ", "")
            if "," in text:
                text = text.replace(".", "").replace(",", ".")
            parsed = Decimal(text)
    except Exception:
        return None
    return parsed if parsed.is_finite() and parsed >= 0 else None


def _money(value: Decimal | None) -> float | None:
    return float(value.quantize(MONEY, rounding=ROUND_HALF_UP)) if value is not None else None


def _active_status(value: Any) -> tuple[bool, str]:
    text = normalize_text(str(value or ""))
    if text == "ativo":
        return True, "active"
    if not text:
        return ALLOW_EMPTY_GROUP_STATUS, "incomplete"
    return False, "inactive"


def map_declared_objective_to_preference(objective: str) -> str | None:
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


def _term_flags(balance: Decimal | None, after_bid: Decimal | None, desired: Decimal, income_limit: Decimal, term: int | None) -> dict[str, bool | None]:
    keys = ("term_compatible_desired_before_bid", "term_compatible_income_before_bid", "term_compatible_desired_after_bid", "term_compatible_income_after_bid")
    if balance is None or after_bid is None or not term or term <= 0:
        return {key: None for key in keys}

    def enough(amount: Decimal, installment: Decimal) -> bool | None:
        return math.ceil(float(amount / installment)) <= term if installment > 0 else None

    return {
        keys[0]: enough(balance, desired), keys[1]: enough(balance, income_limit),
        keys[2]: enough(after_bid, desired), keys[3]: enough(after_bid, income_limit),
    }


def _ranges(group: dict[str, Any]) -> tuple[dict[str, float], bool, dict[str, Any]]:
    raw = {key: group.get(field) for key, field in STRATEGY_TARGETS}
    values = {key: normalize_cost_percent(raw[key]) for key, _ in STRATEGY_TARGETS}
    ordered = [values[key] for key, _ in STRATEGY_TARGETS]
    complete = all(value > 0 for value in ordered)
    return values, complete and ordered == sorted(ordered, reverse=True), raw


def _embedded_reason(raw: Any) -> str | None:
    if raw is None or raw == "":
        return "percentual_x_ausente"
    if isinstance(raw, bool):
        return "percentual_x_invalido"
    parsed = normalize_embedded_bid_percent(raw)
    if parsed is not None:
        return None
    numeric = _decimal(raw)
    return "percentual_x_zero" if numeric == 0 else "percentual_x_invalido"


def _not_created_embedded_scenario(reason: str) -> dict[str, Any]:
    return {
        "id": "with_embedded", "label": "Com lance embutido", "creation_status": "not_created",
        "creation_reason": reason, "credito_contratado": None, "credito_liquido_projetado": None,
        "lance_total": None, "percentual_lance": None, "taxa_administracao": None,
        "fundo_reserva": None, "saldo_devedor": None, "saldo_apos_lance": None,
        "credit_compatible": False, "financial_cost_data_complete": None,
        "term_data_complete": None, "analysis_data_complete": None, "financial_data_complete": None,
        "income_compatible": None, "term_compatible": None, "recommendable": False,
        "margem_credito": None, "alerts": [reason],
        "term_compatible_desired_before_bid": None, "term_compatible_income_before_bid": None,
        "term_compatible_desired_after_bid": None, "term_compatible_income_after_bid": None,
    }


def _scenario(base: dict[str, Any], identifier: str, credit_min: Decimal | None, credit_max: Decimal, fee: Decimal | None, fund: Decimal | None, desired: Decimal, income_limit: Decimal, term: int | None, embedded_reason: str | None = None) -> dict[str, Any] | None:
    suffix = "sem_embutido" if identifier == "without_embedded" else "com_embutido"
    credit = _decimal(base.get(f"credito_necessario_{suffix}"))
    if credit is None:
        return _not_created_embedded_scenario(embedded_reason or "cenario_com_embutido_indisponivel") if identifier == "with_embedded" else None
    alerts: list[str] = []
    if credit_min is None:
        alerts.append("credito_minimo_nao_informado")
    credit_compatible = credit <= credit_max and (credit_min is None or credit >= credit_min)
    cost_complete = fee is not None and fund is not None
    term_complete = term is not None
    analysis_complete = cost_complete and term_complete
    bid = (_decimal(base["recurso_proprio"]) or Decimal(0)) + (_decimal(base["fgts"]) or Decimal(0))
    if identifier == "with_embedded":
        bid += _decimal(base.get("valor_lance_embutido") or 0) or Decimal(0)
    balance = None
    if cost_complete:
        balance = (credit + credit * fee + credit * fund).quantize(MONEY, rounding=ROUND_HALF_UP)
    else:
        if fee is None:
            alerts.append("taxa_administracao_nao_informada")
        if fund is None:
            alerts.append("fundo_reserva_nao_informado")
    if not term_complete:
        alerts.append("prazo_restante_nao_informado")
    after_bid = max(Decimal(0), balance - bid) if balance is not None else None
    term_flags = _term_flags(balance, after_bid, desired, income_limit, term)
    return {
        "id": identifier, "label": "Sem lance embutido" if identifier == "without_embedded" else "Com lance embutido",
        "creation_status": "created", "creation_reason": None, "credito_contratado": _money(credit),
        "credito_liquido_projetado": base.get(f"credito_liquido_projetado_{suffix}"), "lance_total": _money(bid),
        "percentual_lance": float((bid / credit).quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)) if credit else 0.0,
        "taxa_administracao": _money(credit * fee) if fee is not None else None,
        "fundo_reserva": _money(credit * fund) if fund is not None else None,
        "saldo_devedor": _money(balance), "saldo_apos_lance": _money(after_bid),
        "credit_compatible": credit_compatible, "financial_cost_data_complete": cost_complete,
        "term_data_complete": term_complete, "analysis_data_complete": analysis_complete,
        "financial_data_complete": analysis_complete, "income_compatible": None,
        "term_compatible": all(value is True for value in term_flags.values()) if all(value is not None for value in term_flags.values()) else None,
        "recommendable": False,
        "margem_credito": _money(min(credit - credit_min, credit_max - credit)) if credit_compatible and credit_min is not None else _money(credit_max - credit) if credit_compatible else None,
        "alerts": alerts, **term_flags,
    }


def _snapshot_field(name: str, technical: str, raw: Any, normalized: Any, source: str, transformation: str | None) -> dict[str, Any]:
    status = "warning" if raw in (None, "") else "valid"
    return {"field_name": name, "technical_name": technical, "raw_value": raw, "normalized_value": normalized, "source": source, "source_reference": "Perfil do Cliente", "transformation": transformation, "validation_status": status, "warnings": ["Valor não informado."] if status == "warning" else []}


def analyze_client_consortium_viability(payload: Any, groups: list[dict[str, Any]], commitment_percent: float = 0.30, mode: str = "current") -> dict[str, Any]:
    started_at, started_clock = datetime.now(timezone.utc), time.perf_counter()
    desired = _decimal(getattr(payload, "credito_desejado", 0))
    own = _decimal(getattr(payload, "lance_proprio", 0)) or Decimal(0)
    fgts = _decimal(getattr(payload, "fgts", 0)) or Decimal(0)
    income = _decimal(getattr(payload, "renda_total", 0)) or Decimal(0)
    desired_installment = _decimal(getattr(payload, "parcela_desejada", 0) or getattr(payload, "parcela_ideal", 0)) or Decimal(0)
    if desired is None or desired <= 0:
        raise ValueError("credito_desejado invalido")
    manual = _decimal(getattr(payload, "lance_proprio_manual", None))
    participants = _decimal(getattr(payload, "lance_proprio_participantes", None))
    conflict = manual is not None and participants is not None and manual != participants
    own_source = getattr(payload, "own_resources_source", "participants") or "participants"
    if conflict:
        raise ValueError("conflito_recurso_proprio")
    raw_income_limit = getattr(payload, "parcela_limite", None)
    income_limit = _decimal(raw_income_limit) or (income * Decimal(str(commitment_percent)))
    objective = str(getattr(payload, "objetivo", "") or "")
    preference = map_declared_objective_to_preference(objective)
    explicit_type = bool(getattr(payload, "tipo_bem_explicit", False))
    requested_type = str(getattr(payload, "tipo_bem", "") or "") if explicit_type else ""

    items: list[dict[str, Any]] = []
    excluded_groups: list[dict[str, Any]] = []
    counters = {"ativos": 0, "inativos": 0, "status_incompleto": 0, "tipo_incompativel": 0, "credito_incompativel": 0, "dados_incompletos": 0}
    stage_durations = {"status": 0.0, "tipo_bem": 0.0, "credito": 0.0, "dados_financeiros": 0.0}

    for group in groups:
        group_ref = {"grupo": str(group.get("grupo") or group.get("grupo_id") or "-"), "administradora": str(group.get("administradora") or "-")}
        tick = time.perf_counter()
        allowed, status_kind = _active_status(group.get("status"))
        stage_durations["status"] += time.perf_counter() - tick
        if not allowed:
            counters["status_incompleto" if status_kind == "incomplete" else "inativos"] += 1
            excluded_groups.append({**group_ref, "reason": "status_nao_informado" if status_kind == "incomplete" else "status_inativo", "detail": f"Status recebido: {group.get('status') or '-'}"})
            continue
        counters["ativos"] += 1

        tick = time.perf_counter()
        type_compatible = not explicit_type or compatible_tipo_bem("", str(group.get("tipo_bem") or ""), requested_type)
        stage_durations["tipo_bem"] += time.perf_counter() - tick
        if not type_compatible:
            counters["tipo_incompativel"] += 1
            excluded_groups.append({**group_ref, "reason": "tipo_bem_incompativel", "detail": f"Tipo solicitado: {requested_type}; tipo do grupo: {group.get('tipo_bem') or '-'}"})
            continue

        tick = time.perf_counter()
        minimum, maximum = _decimal(group.get("credito_minimo")), _decimal(group.get("credito_maximo"))
        if maximum is None or maximum <= 0:
            counters["credito_incompativel"] += 1
            excluded_groups.append({**group_ref, "reason": "credito_maximo_invalido", "detail": "Coluna U sem crédito máximo positivo."})
            stage_durations["credito"] += time.perf_counter() - tick
            continue
        raw_embedded = group.get("percentual_lance_embutido")
        embedded_reason = _embedded_reason(raw_embedded)
        base = build_credit_liquidity_scenarios(float(desired), float(own), float(fgts), raw_embedded, 0, 0)
        raw_fee, raw_fund = group.get("taxa_adm"), group.get("fundo_reserva")
        fee = Decimal(str(normalize_cost_percent(raw_fee))) if raw_fee not in (None, "") else None
        fund = Decimal(str(normalize_cost_percent(raw_fund))) if raw_fund not in (None, "") else None
        raw_term = group.get("prazo_restante", group.get("prazo_remanescente"))
        term = int(_decimal(raw_term) or 0) or None
        scenarios = [item for item in (
            _scenario(base, "without_embedded", minimum, maximum, fee, fund, desired_installment, income_limit, term),
            _scenario(base, "with_embedded", minimum, maximum, fee, fund, desired_installment, income_limit, term, embedded_reason),
        ) if item]
        credit_scenarios = [item for item in scenarios if item["credit_compatible"]]
        stage_durations["credito"] += time.perf_counter() - tick
        if not credit_scenarios:
            counters["credito_incompativel"] += 1
            excluded_groups.append({**group_ref, "reason": "credito_fora_da_faixa", "detail": f"Faixa de crédito: {minimum or '-'} a {maximum}."})
            continue

        tick = time.perf_counter()
        incomplete_reasons = []
        if fee is None:
            incomplete_reasons.append("taxa_administracao_nao_informada")
        if fund is None:
            incomplete_reasons.append("fundo_reserva_nao_informado")
        if term is None:
            incomplete_reasons.append("prazo_restante_nao_informado")
        cost_complete, term_complete = fee is not None and fund is not None, term is not None
        analysis_complete = cost_complete and term_complete
        if not analysis_complete:
            counters["dados_incompletos"] += 1
        ranges, ranges_consistent, raw_ranges = _ranges(group)
        strategy_warnings = [] if ranges_consistent else ["faixas_contemplacao_inconsistentes"]
        possible = [] if not ranges_consistent else [key for key, _ in STRATEGY_TARGETS if any(item["percentual_lance"] is not None and item["percentual_lance"] >= ranges[key] for item in credit_scenarios)]
        best = next((key for key, _ in STRATEGY_TARGETS if key in possible), None)
        installment = _decimal(group.get("parcela_inicial_grupo"))
        reference_affordable = installment is not None and installment <= income_limit
        for scenario in scenarios:
            scenario["recommendable"] = bool(scenario["credit_compatible"] and scenario["analysis_data_complete"] and scenario["income_compatible"] is True and scenario["term_compatible"] is True)
        stage_durations["dados_financeiros"] += time.perf_counter() - tick

        alerts = strategy_warnings + (["seguro_nao_analisado"] if group.get("seguro_obrigatorio") else [])
        items.append({
            "grupo_id": str(group.get("grupo_id") or ""), "grupo": str(group.get("grupo") or ""), "administradora": str(group.get("administradora") or ""),
            "tipo_bem": str(group.get("tipo_bem") or ""), "tipo_bem_source": "explicit" if explicit_type else "not_provided",
            "credito_minimo": _money(minimum), "credito_maximo": _money(maximum), "prazo_restante": term, "prazo_remanescente": term,
            "reference_installment": _money(installment), "installment_source": "planilha coluna AJ", "installment_is_reference": True,
            "installment_affordable_reference": reference_affordable, "cenarios": scenarios, "credit_compatible": True,
            "financial_cost_data_complete": cost_complete, "term_data_complete": term_complete, "analysis_data_complete": analysis_complete,
            "financial_data_complete": analysis_complete, "income_compatible": None,
            "term_compatible": any(item["term_compatible"] is True for item in credit_scenarios), "recommendable": False,
            "compatible_contemplation_strategies": possible, "best_contemplation_strategy": best, "investment": "not_classified",
            "destaque_preferencia": preference == best, "incomplete_fields": [field for field, value in (("taxa_administracao", fee), ("fundo_reserva", fund), ("prazo_restante", term)) if value is None],
            "incomplete_reasons": incomplete_reasons, "strategy_warnings": strategy_warnings,
            "data_completeness": "complete" if analysis_complete else "incomplete", "insurance_eligibility": "not_analyzed",
            "embedded_scenario_status": "created" if embedded_reason is None else "not_created", "embedded_scenario_reason": embedded_reason,
            "alerts": alerts, "source_values": {"credito_minimo": _money(minimum), "credito_maximo": _money(maximum), "prazo_restante_raw": raw_term, "prazo_restante": term, "percentual_lance_embutido_raw": raw_embedded, "percentual_lance_embutido": base.get("percentual_lance_embutido"), "faixas_lance_raw": raw_ranges, "faixas_lance_normalizadas": ranges},
        })

    def ordering_key(item: dict[str, Any]):
        both = sum(1 for scenario in item["cenarios"] if scenario["credit_compatible"]) == 2
        margin = min((scenario["margem_credito"] for scenario in item["cenarios"] if scenario["margem_credito"] is not None), default=float("inf"))
        match = re.search(r"\d+", item["grupo"] or "")
        number = int(match.group()) if match else math.inf
        return (not item["analysis_data_complete"], not item["recommendable"], not both, not item["installment_affordable_reference"], not item["term_compatible"], not item["destaque_preferencia"], margin, number)

    items.sort(key=ordering_key)
    for rank, item in enumerate(items, 1):
        item["ranking"] = rank

    client = {
        "nome": getattr(payload, "nome", None), "objetivo_declarado": objective, "presentation_preference": preference,
        "preference_mapping_rule": "Objetivo contemplar é mapeado para a faixa correspondente; objetivo investidor permanece como preferência de apresentação.",
        "tipo_bem": requested_type or None, "credito_liquido_desejado": _money(desired), "own_resources_total": _money(own),
        "own_resources_source": own_source, "own_resources_conflict": conflict, "fgts": _money(fgts), "renda_total": _money(income),
        "parcela_desejada": _money(desired_installment), "parcela_maxima": _money(income_limit), "percentual_comprometimento": commitment_percent,
        "tipo_bem_source": "explicit" if explicit_type else "not_provided",
    }
    completed_at = datetime.now(timezone.utc)
    reason_counts = Counter(item["reason"] for item in excluded_groups)
    settings = get_settings()
    active_after_type = counters["ativos"] - counters["tipo_incompativel"]
    raw_fields = [
        _snapshot_field("Objetivo declarado", "objetivo", getattr(payload, "objetivo", None), objective, "client_profile", "Normalização de texto"),
        _snapshot_field("Tipo de bem", "tipo_bem", getattr(payload, "tipo_bem", None), requested_type or None, "client_profile", "Normalização de texto"),
        _snapshot_field("Crédito líquido desejado", "credito_desejado", getattr(payload, "credito_desejado", None), _money(desired), "client_profile", "Normalização monetária"),
        _snapshot_field("Recurso próprio", "lance_proprio", getattr(payload, "lance_proprio", None), _money(own), "client_profile", "Normalização monetária"),
        _snapshot_field("FGTS total", "fgts", getattr(payload, "fgts", None), _money(fgts), "participant", "Normalização monetária"),
        _snapshot_field("Renda total", "renda_total", getattr(payload, "renda_total", None), _money(income), "participant", "Normalização monetária"),
        _snapshot_field("Parcela desejada", "parcela_desejada", getattr(payload, "parcela_desejada", None), _money(desired_installment), "client_profile", "Normalização monetária"),
        _snapshot_field("Parcela máxima", "parcela_limite", raw_income_limit, _money(income_limit), "calculated" if raw_income_limit in (None, "") else "client_profile", "Renda total x percentual de comprometimento" if raw_income_limit in (None, "") else "Normalização monetária"),
        _snapshot_field("Percentual de comprometimento", "percentual_comprometimento", commitment_percent, commitment_percent, "system_configuration", "Normalização percentual"),
        _snapshot_field("Conflito de recurso próprio", "own_resources_conflict", conflict, conflict, "calculated", "Normalização booleana"),
    ]
    columns = [("A", "Administradora", "administradora", "Identificação"), ("B", "Grupo", "grupo", "Identificação e desempate"), ("C", "Tipo de bem", "tipo_bem", "Filtro opcional"), ("F", "Prazo restante", "prazo_restante", "Cálculo de prazo"), ("O", "Crédito mínimo", "credito_minimo", "Limite inferior"), ("U", "Crédito máximo", "credito_maximo", "Limite superior"), ("X", "Lance embutido", "percentual_lance_embutido", "Cenário com embutido"), ("AA", "Fundo de reserva", "fundo_reserva", "Saldo devedor"), ("AC", "Taxa ADM", "taxa_adm", "Saldo devedor"), ("AJ", "Parcela inicial", "parcela_inicial_grupo", "Referência de ordenação"), ("BL", "Lance investidor", "lance_investidor", "Estratégia longo prazo"), ("BM", "Lance conservador", "lance_conservador_24m", "Estratégia 24 meses"), ("BN", "Lance moderado", "lance_moderado_12m", "Estratégia 12 meses"), ("BO", "Lance rápido", "lance_agressivo_6m", "Estratégia 6 meses"), ("BP", "Lance urgente", "lance_super_agressivo_3m", "Estratégia 3 meses")]
    ordering_summary = "Como os critérios anteriores estão empatados ou indisponíveis, a ordem desta execução foi definida pela menor margem de crédito." if items and all(item["data_completeness"] == "incomplete" for item in items) else "A ordem usa os critérios configurados do Motor 360."
    audit = {
        "metadata": {"audit_id": new_audit_id(completed_at), "analysis_id": None, "study_id": None, "client_id": None, "started_at": started_at.isoformat(), "completed_at": completed_at.isoformat(), "duration_ms": round((time.perf_counter() - started_clock) * 1000, 2), "engine_version": "3.0.0", "rules_version": "motor-360-v2-audit", "application_version": settings.version, "environment": settings.environment, "executed_by_user_id": None, "executed_by_user_name": None, "data_source_version": None},
        "client_snapshot": {"raw_fields": raw_fields, "consolidated_values": client, "participants": getattr(payload, "titulares", []) or []},
        "data_source": {"source_name": "Mapa de Grupos", "current_or_historical": "historical" if mode == "historical_audit" else "current", "loaded_at": completed_at.isoformat(), "total_rows": len(groups), "source_version": None},
        "columns_used": [{"column": column, "header": header, "technical_field": field, "purpose": purpose, "used": True} for column, header, field, purpose in columns],
        "execution_steps": [
            {"order": 1, "id": "status", "name": "Status do grupo", "description": "Mantém somente grupos ativos.", "formula_or_rule": "status normalizado = Ativo", "fields_used": ["status"], "columns_used": [], "input_count": len(groups), "approved_count": counters["ativos"], "rejected_count": counters["inativos"] + counters["status_incompleto"], "incomplete_count": counters["status_incompleto"], "duration_ms": round(stage_durations["status"] * 1000, 3), "rejection_reasons": {"status_inativo": counters["inativos"], "status_nao_informado": counters["status_incompleto"]}},
            {"order": 2, "id": "tipo_bem", "name": "Tipo de bem", "description": "Filtro somente quando declarado explicitamente.", "formula_or_rule": "compatibilidade de tipo quando tipo_bem_explicit = true", "fields_used": ["tipo_bem"], "columns_used": ["C"], "input_count": counters["ativos"], "approved_count": active_after_type, "rejected_count": counters["tipo_incompativel"], "incomplete_count": 0, "duration_ms": round(stage_durations["tipo_bem"] * 1000, 3), "rejection_reasons": {"tipo_bem_incompativel": counters["tipo_incompativel"]}},
            {"order": 3, "id": "credito", "name": "Compatibilidade de crédito", "description": "Avalia cenários sem e com embutido na faixa O/U.", "formula_or_rule": "O <= crédito contratado <= U, quando O informado; crédito contratado <= U quando O ausente", "fields_used": ["credito_minimo", "credito_maximo", "percentual_lance_embutido"], "columns_used": ["O", "U", "X"], "input_count": active_after_type, "approved_count": len(items), "rejected_count": counters["credito_incompativel"], "incomplete_count": 0, "duration_ms": round(stage_durations["credito"] * 1000, 3), "rejection_reasons": {key: value for key, value in reason_counts.items() if key.startswith("credito_")}},
            {"order": 4, "id": "dados_financeiros", "name": "Completude da análise", "description": "Taxa ADM, fundo de reserva e prazo restante são exigidos para cálculo completo.", "formula_or_rule": "AC, AA e F devem estar preenchidas", "fields_used": ["taxa_adm", "fundo_reserva", "prazo_restante"], "columns_used": ["AC", "AA", "F"], "input_count": len(items), "approved_count": len(items) - counters["dados_incompletos"], "rejected_count": 0, "incomplete_count": counters["dados_incompletos"], "duration_ms": round(stage_durations["dados_financeiros"] * 1000, 3), "rejection_reasons": {}},
        ],
        "formulas": [{"id": "credito_sem_embutido", "name": "Crédito contratado sem embutido", "expression": "crédito desejado + recurso próprio + FGTS", "inputs": {"credito_desejado": _money(desired), "recurso_proprio": _money(own), "fgts": _money(fgts)}, "result": _money(desired + own + fgts), "rounding_rule": "Decimal para 2 casas, ROUND_HALF_UP"}, {"id": "credito_com_embutido", "name": "Crédito contratado com embutido", "expression": "crédito sem embutido / (1 - percentual de embutido)", "inputs": {"credito_sem_embutido": _money(desired + own + fgts)}, "result": "Calculado individualmente com a coluna X", "rounding_rule": "Decimal para 2 casas, ROUND_HALF_UP"}, {"id": "parcela_limite", "name": "Parcela máxima pela renda", "expression": "parcela limite informada ou renda total x 30%", "inputs": {"renda_total": _money(income), "percentual": commitment_percent}, "result": _money(income_limit), "rounding_rule": "Decimal para 2 casas, ROUND_HALF_UP"}, {"id": "saldo_devedor", "name": "Saldo devedor por cenário", "expression": "crédito contratado + (crédito x taxa ADM) + (crédito x fundo de reserva)", "inputs": {}, "result": "Calculado individualmente por grupo", "rounding_rule": "Decimal para 2 casas, ROUND_HALF_UP"}],
        "group_results": [{"grupo": item["grupo"], "administradora": item["administradora"], "result": "incompleto" if item["data_completeness"] == "incomplete" else "compativel_por_credito", "justification": item["incomplete_reasons"] + item["strategy_warnings"], "incomplete_reasons": item["incomplete_reasons"], "strategy_warnings": item["strategy_warnings"], "embedded_scenario_status": item["embedded_scenario_status"], "embedded_scenario_reason": item["embedded_scenario_reason"], "scenarios": item["cenarios"], "ranking": item["ranking"], "source_values": item["source_values"]} for item in items],
        "excluded_groups": excluded_groups,
        "final_ordering": {"rules": ["Dados da análise completos", "Cenário recomendável", "Compatibilidade nos dois cenários", "Parcela AJ dentro do limite de renda como referência", "Compatibilidade de prazo", "Preferência declarada", "Menor margem de crédito", "Número do grupo"], "selected_preferences": [], "execution_summary": ordering_summary},
        "summary": {"total_loaded": len(groups), "total_analyzed": len(groups), "total_recommended": sum(1 for item in items if item["recommendable"]), "total_credit_compatible": len(items), "total_incomplete": counters["dados_incompletos"], "total_rejected": len(excluded_groups)},
        "warnings": [{"level": "warning", "message": "Parcela da coluna AJ é somente referência até a seleção da carta."}, {"level": "info", "message": "Seguro e idade ainda não são critérios de aprovação nesta fase."}],
    }
    return {"motor": "360", "base_mode": mode, "objetivo_declarado": objective, "preferencia_declarada": preference, "cliente": client, "total_grupos_analisados": len(groups), "total_grupos_viaveis": len(items), "contadores": counters, "passos": ["Base atual carregada em modo current.", "Objetivo declarado é preferência e não elimina estratégias.", "Cenários são avaliados sem e com embutido, com crédito na faixa O/U.", "AJ é parcela de referência e não aprova financeiramente o cenário.", "Seguro e idade permanecem não analisados."], "items": items, "audit": audit}
