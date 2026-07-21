from __future__ import annotations

import math
from typing import Any


def normalize_embedded_bid_percent(value: Any) -> float | None:
    """Returns a valid embedded-bid percentage as a decimal, or None."""
    if value is None or value == "" or isinstance(value, bool):
        return None
    try:
        raw_text = str(value).strip()
        has_percent = "%" in raw_text
        text = raw_text.replace("%", "").replace(" ", "")
        if "," in text:
            text = text.replace(".", "").replace(",", ".")
        percent = float(text)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(percent):
        return None
    if has_percent or percent > 1:
        percent /= 100
    if percent <= 0 or percent >= 1:
        return None
    return round(percent, 8)


def normalize_cost_percent(value: Any) -> float:
    """Normalizes group administration and reserve rates, allowing zero."""
    if value is None or value == "" or isinstance(value, bool):
        return 0.0
    try:
        raw_text = str(value).strip()
        has_percent = "%" in raw_text
        text = raw_text.replace("%", "").replace(" ", "")
        if "," in text:
            text = text.replace(".", "").replace(",", ".")
        percent = float(text)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(percent) or percent < 0:
        return 0.0
    if has_percent or percent > 1:
        percent /= 100
    return round(percent, 8) if percent < 1 else 0.0


def build_credit_liquidity_scenarios(
    desired_net_credit: float,
    own_resources: float,
    fgts: float,
    embedded_bid_percent: Any,
    administration_fee_percent: Any = 0,
    reserve_fund_percent: Any = 0,
) -> dict[str, float | None]:
    desired = float(desired_net_credit)
    own = max(0.0, float(own_resources))
    fgts_value = max(0.0, float(fgts))
    required_without = desired + own + fgts_value
    percent = normalize_embedded_bid_percent(embedded_bid_percent)
    administration_fee_percent = normalize_cost_percent(administration_fee_percent)
    reserve_fund_percent = normalize_cost_percent(reserve_fund_percent)
    required_with = required_without / (1 - percent) if percent is not None else None
    embedded_amount = required_with * percent if required_with is not None and percent is not None else None
    administration_fee_without = required_without * administration_fee_percent
    reserve_fund_without = required_without * reserve_fund_percent
    debtor_balance_without = required_without + administration_fee_without + reserve_fund_without
    administration_fee_with = required_with * administration_fee_percent if required_with is not None else None
    reserve_fund_with = required_with * reserve_fund_percent if required_with is not None else None
    debtor_balance_with = (
        required_with + administration_fee_with + reserve_fund_with
        if required_with is not None and administration_fee_with is not None and reserve_fund_with is not None
        else None
    )
    projected_with = (
        required_with - embedded_amount - own - fgts_value
        if required_with is not None and embedded_amount is not None
        else None
    )
    return {
        "credito_liquido_desejado": round(desired, 2),
        "recurso_proprio": round(own, 2),
        "fgts": round(fgts_value, 2),
        "percentual_lance_embutido": percent,
        "taxa_administracao_total": administration_fee_percent,
        "fundo_reserva_total": reserve_fund_percent,
        "credito_necessario_sem_embutido": round(required_without, 2),
        "credito_necessario_com_embutido": round(required_with, 2) if required_with is not None else None,
        "valor_lance_embutido": round(embedded_amount, 2) if embedded_amount is not None else None,
        "taxa_administracao_sem_embutido": round(administration_fee_without, 2),
        "fundo_reserva_sem_embutido": round(reserve_fund_without, 2),
        "saldo_devedor_sem_embutido": round(debtor_balance_without, 2),
        "taxa_administracao_com_embutido": round(administration_fee_with, 2) if administration_fee_with is not None else None,
        "fundo_reserva_com_embutido": round(reserve_fund_with, 2) if reserve_fund_with is not None else None,
        "saldo_devedor_com_embutido": round(debtor_balance_with, 2) if debtor_balance_with is not None else None,
        "credito_liquido_projetado_sem_embutido": round(required_without - own - fgts_value, 2),
        "credito_liquido_projetado_com_embutido": round(projected_with, 2) if projected_with is not None else None,
    }


def evaluate_group_credit_liquidity(
    credit_maximum: float,
    scenarios: dict[str, float | None],
) -> dict[str, float | bool | None | str]:
    credit_max = float(credit_maximum)
    required_without = float(scenarios["credito_necessario_sem_embutido"] or 0)
    required_with = scenarios["credito_necessario_com_embutido"]
    compatible_without = credit_max >= required_without
    compatible_with = required_with is not None and credit_max >= float(required_with)
    if compatible_without and compatible_with:
        classification = "Compativel nos dois cenarios"
    elif compatible_without:
        classification = "Compativel sem embutido"
    elif compatible_with:
        classification = "Compativel com embutido"
    else:
        classification = "Incompativel nos dois cenarios"
    compatible_margins = [credit_max - required_without] if compatible_without else []
    if compatible_with and required_with is not None:
        compatible_margins.append(credit_max - float(required_with))
    return {
        **scenarios,
        "credito_maximo": round(credit_max, 2),
        "compativel_sem_embutido": compatible_without,
        "compativel_com_embutido": compatible_with,
        "classificacao_credito": classification,
        "margem_credito": round(min(compatible_margins), 2) if compatible_margins else None,
    }
