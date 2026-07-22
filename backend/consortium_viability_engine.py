from __future__ import annotations

import math
import re
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from .credit_liquidity import build_credit_liquidity_scenarios, normalize_cost_percent
from .viabilidade import compatible_tipo_bem, normalize_text


ALLOW_EMPTY_GROUP_STATUS = False
MONEY = Decimal("0.01")
STRATEGY_TARGETS = (
    ("urgent", "lance_super_agressivo_3m"), ("fast", "lance_agressivo_6m"),
    ("moderate", "lance_moderado_12m"), ("conservative", "lance_conservador_24m"),
    ("long_term", "lance_investidor"),
)


def _decimal(value: Any) -> Decimal | None:
    if value is None or value == "" or isinstance(value, bool): return None
    try:
        if isinstance(value, (int, float, Decimal)):
            value = Decimal(str(value))
        else:
            text = str(value).strip().replace("R$", "").replace(" ", "")
            if "," in text: text = text.replace(".", "").replace(",", ".")
            value = Decimal(text)
    except Exception: return None
    return value if value.is_finite() and value >= 0 else None


def _money(value: Decimal | None) -> float | None:
    return float(value.quantize(MONEY, rounding=ROUND_HALF_UP)) if value is not None else None


def map_declared_objective_to_preference(objective: str) -> str | None:
    text = normalize_text(objective)
    if text.startswith("investidor"): return "investment"
    if not text.startswith("contemplar"): return None
    if "investidor" in text or "36 mes" in text: return "long_term"
    if "conservador" in text or "24 mes" in text: return "conservative"
    if "moderado" in text or "12 mes" in text: return "moderate"
    if "rapido" in text or "6 mes" in text: return "fast"
    if "urgente" in text or "3 mes" in text: return "urgent"
    return None


def _active_status(value: Any) -> tuple[bool, str]:
    text = normalize_text(str(value or ""))
    if text == "ativo": return True, "active"
    if not text: return ALLOW_EMPTY_GROUP_STATUS, "incomplete"
    return False, "inactive"


def _term_flags(balance: Decimal | None, after_bid: Decimal | None, desired: Decimal, income_limit: Decimal, term: int | None) -> dict[str, bool | None]:
    keys = ("term_compatible_desired_before_bid", "term_compatible_income_before_bid", "term_compatible_desired_after_bid", "term_compatible_income_after_bid")
    if balance is None or after_bid is None or not term or term <= 0: return {key: None for key in keys}
    def enough(amount: Decimal, installment: Decimal) -> bool | None:
        return math.ceil(float(amount / installment)) <= term if installment > 0 else None
    return {keys[0]: enough(balance, desired), keys[1]: enough(balance, income_limit), keys[2]: enough(after_bid, desired), keys[3]: enough(after_bid, income_limit)}


def _ranges(group: dict[str, Any]) -> tuple[dict[str, float], bool]:
    values = {key: normalize_cost_percent(group.get(field)) for key, field in STRATEGY_TARGETS}
    ordered = [values[key] for key, _ in STRATEGY_TARGETS]
    complete = all(value > 0 for value in ordered)
    return values, complete and ordered == sorted(ordered, reverse=True)


def _scenario(base: dict[str, Any], identifier: str, credit_min: Decimal | None, credit_max: Decimal, fee: Decimal | None, fund: Decimal | None, desired: Decimal, income_limit: Decimal, term: int | None) -> dict[str, Any] | None:
    suffix = "sem_embutido" if identifier == "without_embedded" else "com_embutido"
    credit = _decimal(base.get(f"credito_necessario_{suffix}"))
    if credit is None: return None
    alerts: list[str] = []
    if credit_min is None: alerts.append("credito_minimo_nao_informado")
    credit_compatible = credit <= credit_max and (credit_min is None or credit >= credit_min)
    financial_data_complete = fee is not None and fund is not None
    bid = _decimal(base["recurso_proprio"]) + _decimal(base["fgts"])
    if identifier == "with_embedded": bid += _decimal(base.get("valor_lance_embutido") or 0)
    balance = None
    if financial_data_complete:
        balance = (credit + credit * fee + credit * fund).quantize(MONEY, rounding=ROUND_HALF_UP)
    else:
        if fee is None: alerts.append("taxa_administracao_nao_informada")
        if fund is None: alerts.append("fundo_reserva_nao_informado")
    after_bid = max(Decimal(0), balance - bid) if balance is not None else None
    term_flags = _term_flags(balance, after_bid, desired, income_limit, term)
    # AJ is intentionally reference-only until a matching card is selected.
    return {"id": identifier, "label": "Sem lance embutido" if identifier == "without_embedded" else "Com lance embutido", "credito_contratado": _money(credit), "credito_liquido_projetado": base.get(f"credito_liquido_projetado_{suffix}"), "lance_total": _money(bid), "percentual_lance": float((bid / credit).quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)) if credit else 0.0, "taxa_administracao": _money(credit * fee) if fee is not None else None, "fundo_reserva": _money(credit * fund) if fund is not None else None, "saldo_devedor": _money(balance), "saldo_apos_lance": _money(after_bid), "credit_compatible": credit_compatible, "financial_data_complete": financial_data_complete, "income_compatible": None, "term_compatible": all(value is True for value in term_flags.values()) if all(value is not None for value in term_flags.values()) else None, "recommendable": False, "margem_credito": _money(min(credit - credit_min, credit_max - credit)) if credit_compatible and credit_min is not None else _money(credit_max - credit) if credit_compatible else None, "alerts": alerts, **term_flags}


def analyze_client_consortium_viability(payload: Any, groups: list[dict[str, Any]], commitment_percent: float = 0.30, mode: str = "current") -> dict[str, Any]:
    desired = _decimal(getattr(payload, "credito_desejado", 0))
    own, fgts = _decimal(getattr(payload, "lance_proprio", 0)) or Decimal(0), _decimal(getattr(payload, "fgts", 0)) or Decimal(0)
    income, desired_installment = _decimal(getattr(payload, "renda_total", 0)) or Decimal(0), _decimal(getattr(payload, "parcela_desejada", 0) or getattr(payload, "parcela_ideal", 0)) or Decimal(0)
    if desired is None or desired <= 0: raise ValueError("credito_desejado invalido")
    manual = _decimal(getattr(payload, "lance_proprio_manual", None))
    participants = _decimal(getattr(payload, "lance_proprio_participantes", None))
    conflict = manual is not None and participants is not None and manual != participants
    own_source = getattr(payload, "own_resources_source", "participants") or "participants"
    if conflict: raise ValueError("conflito_recurso_proprio")
    income_limit = _decimal(getattr(payload, "parcela_limite", None)) or (income * Decimal(str(commitment_percent)))
    objective, preference = str(getattr(payload, "objetivo", "") or ""), map_declared_objective_to_preference(str(getattr(payload, "objetivo", "") or ""))
    explicit_type = bool(getattr(payload, "tipo_bem_explicit", False))
    requested_type = str(getattr(payload, "tipo_bem", "") or "") if explicit_type else ""
    items, counters = [], {"ativos": 0, "inativos": 0, "status_incompleto": 0, "tipo_incompativel": 0, "credito_incompativel": 0, "dados_incompletos": 0}
    for group in groups:
        allowed, status_kind = _active_status(group.get("status"))
        if not allowed:
            counters["status_incompleto" if status_kind == "incomplete" else "inativos"] += 1; continue
        counters["ativos"] += 1
        if explicit_type and not compatible_tipo_bem("", str(group.get("tipo_bem") or ""), requested_type):
            counters["tipo_incompativel"] += 1; continue
        minimum, maximum = _decimal(group.get("credito_minimo")), _decimal(group.get("credito_maximo"))
        if maximum is None or maximum <= 0:
            counters["credito_incompativel"] += 1; continue
        raw_fee, raw_fund = group.get("taxa_adm"), group.get("fundo_reserva")
        fee = Decimal(str(normalize_cost_percent(raw_fee))) if raw_fee not in (None, "") else None
        fund = Decimal(str(normalize_cost_percent(raw_fund))) if raw_fund not in (None, "") else None
        base = build_credit_liquidity_scenarios(float(desired), float(own), float(fgts), group.get("percentual_lance_embutido"), 0, 0)
        term = int(_decimal(group.get("prazo_remanescente")) or 0) or None
        scenarios = [item for item in (_scenario(base, "without_embedded", minimum, maximum, fee, fund, desired_installment, income_limit, term), _scenario(base, "with_embedded", minimum, maximum, fee, fund, desired_installment, income_limit, term)) if item]
        credit_scenarios = [item for item in scenarios if item["credit_compatible"]]
        if not credit_scenarios: counters["credito_incompativel"] += 1; continue
        incomplete_fields = [field for field, value in (("taxa_administracao", fee), ("fundo_reserva", fund), ("prazo_remanescente", term)) if value is None]
        financial_complete = not incomplete_fields
        if not financial_complete: counters["dados_incompletos"] += 1
        ranges, ranges_consistent = _ranges(group)
        possible = [] if not ranges_consistent else [key for key, _ in STRATEGY_TARGETS if any(item["percentual_lance"] >= ranges[key] for item in credit_scenarios)]
        best = next((key for key, _ in STRATEGY_TARGETS if key in possible), None)
        installment = _decimal(group.get("parcela_inicial_grupo"))
        reference_affordable = installment is not None and installment <= income_limit
        for scenario in scenarios:
            scenario["recommendable"] = bool(scenario["credit_compatible"] and scenario["financial_data_complete"] and scenario["income_compatible"] is True and scenario["term_compatible"] is True)
        alerts = (["faixas_contemplacao_inconsistentes"] if not ranges_consistent else []) + (["seguro_nao_analisado"] if group.get("seguro_obrigatorio") else [])
        items.append({"grupo_id": str(group.get("grupo_id") or ""), "grupo": str(group.get("grupo") or ""), "administradora": str(group.get("administradora") or ""), "tipo_bem": str(group.get("tipo_bem") or ""), "tipo_bem_source": "explicit" if explicit_type else "not_provided", "credito_minimo": _money(minimum), "credito_maximo": _money(maximum), "prazo_remanescente": term, "reference_installment": _money(installment), "installment_source": "planilha coluna AJ", "installment_is_reference": True, "installment_affordable_reference": reference_affordable, "cenarios": scenarios, "credit_compatible": True, "financial_data_complete": financial_complete, "income_compatible": None, "term_compatible": any(item["term_compatible"] is True for item in credit_scenarios), "recommendable": False, "compatible_contemplation_strategies": possible, "best_contemplation_strategy": best, "investment": "not_classified", "destaque_preferencia": preference == best or preference == "investment" and False, "incomplete_fields": incomplete_fields, "data_completeness": "complete" if financial_complete else "incomplete", "insurance_eligibility": "not_analyzed", "alerts": alerts})
    def key(item: dict[str, Any]):
        both = sum(1 for scenario in item["cenarios"] if scenario["credit_compatible"]) == 2
        margin = min((scenario["margem_credito"] for scenario in item["cenarios"] if scenario["margem_credito"] is not None), default=float("inf"))
        number = int(re.search(r"\d+", item["grupo"] or "") .group()) if re.search(r"\d+", item["grupo"] or "") else math.inf
        return (not item["financial_data_complete"], not item["recommendable"], not both, not item["installment_affordable_reference"], not item["term_compatible"], not item["destaque_preferencia"], margin, number)
    items.sort(key=key)
    for rank, item in enumerate(items, 1): item["ranking"] = rank
    return {"motor": "360", "base_mode": mode, "objetivo_declarado": objective, "preferencia_declarada": preference, "cliente": {"credito_liquido_desejado": _money(desired), "own_resources_total": _money(own), "own_resources_source": own_source, "own_resources_conflict": conflict, "fgts": _money(fgts), "renda_total": _money(income), "parcela_desejada": _money(desired_installment), "parcela_maxima": _money(income_limit), "percentual_comprometimento": commitment_percent, "tipo_bem_source": "explicit" if explicit_type else "not_provided"}, "total_grupos_analisados": len(groups), "total_grupos_viaveis": len(items), "contadores": counters, "passos": ["Base atual carregada em modo current.", "Objetivo declarado é preferência e não elimina estratégias.", "Cenários são avaliados sem e com embutido, com crédito na faixa O/U.", "AJ é parcela de referência e não aprova financeiramente o cenário.", "Seguro e idade permanecem não analisados."], "items": items}
