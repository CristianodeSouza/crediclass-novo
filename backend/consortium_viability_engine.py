from __future__ import annotations

import math
from typing import Any

from .credit_composition import as_float
from .credit_liquidity import build_credit_liquidity_scenarios, normalize_cost_percent
from .viabilidade import compatible_tipo_bem, normalize_text


STRATEGY_TARGETS = (
    ("urgent", "Contemplacao urgente - 3 meses", "lance_super_agressivo_3m"),
    ("fast", "Contemplacao rapida - 6 meses", "lance_agressivo_6m"),
    ("moderate", "Contemplacao moderada - 12 meses", "lance_moderado_12m"),
    ("conservative", "Contemplacao conservadora - 24 meses", "lance_conservador_24m"),
    ("long_term", "Contemplacao investidor - 36 meses", "lance_investidor"),
)


def is_investor_objective(objective: str) -> bool:
    return normalize_text(objective).startswith("investidor")


def is_contemplar_objective(objective: str) -> bool:
    return normalize_text(objective).startswith("contemplar")


def _money(value: Any) -> float:
    return max(0.0, as_float(value))


def _scenario(base: dict[str, Any], identifier: str, credit_min: float, credit_max: float) -> dict[str, Any] | None:
    suffix = "sem_embutido" if identifier == "without_embedded" else "com_embutido"
    credit = base.get(f"credito_necessario_{suffix}")
    if credit is None:
        return None
    credit = float(credit)
    compatible = credit_min <= credit <= credit_max
    bid = base["recurso_proprio"] + base["fgts"] + (float(base.get("valor_lance_embutido") or 0) if identifier == "with_embedded" else 0)
    balance = base.get(f"saldo_devedor_{suffix}")
    desired_installment, income_limit = base["parcela_desejada"], base["parcela_maxima"]
    after_bid = max(0.0, float(balance or 0) - bid)
    return {
        "id": identifier,
        "label": "Sem lance embutido" if identifier == "without_embedded" else "Com lance embutido",
        "credito_contratado": round(credit, 2),
        "credito_liquido_projetado": base.get(f"credito_liquido_projetado_{suffix}"),
        "lance_total": round(bid, 2),
        "percentual_lance": round(bid / credit, 8) if credit else 0,
        "taxa_administracao": base.get(f"taxa_administracao_{suffix}"),
        "fundo_reserva": base.get(f"fundo_reserva_{suffix}"),
        "saldo_devedor": balance,
        "saldo_apos_lance": round(after_bid, 2),
        "prazo_minimo_parcela_desejada": round(float(balance or 0) / desired_installment, 2) if desired_installment else None,
        "prazo_apos_lance_parcela_desejada": round(after_bid / desired_installment, 2) if desired_installment else None,
        "prazo_minimo_limite_renda": round(float(balance or 0) / income_limit, 2) if income_limit else None,
        "prazo_apos_lance_limite_renda": round(after_bid / income_limit, 2) if income_limit else None,
        "compativel_credito": compatible,
        "margem_credito": round(min(credit - credit_min, credit_max - credit), 2) if compatible else None,
    }


def _strategies(group: dict[str, Any], scenarios: list[dict[str, Any]], installment: float | None, income_limit: float) -> list[str]:
    strategies = ["investment"] if installment is not None and installment <= income_limit else []
    for key, _label, field in STRATEGY_TARGETS:
        target = normalize_cost_percent(group.get(field))
        if target and any(item["percentual_lance"] >= target for item in scenarios):
            strategies.append(key)
    return strategies


def analyze_client_consortium_viability(payload: Any, groups: list[dict[str, Any]], commitment_percent: float = 0.30) -> dict[str, Any]:
    """Single 360-degree engine. The declared objective only sets presentation priority."""
    desired_credit = _money(getattr(payload, "credito_desejado", 0))
    if not desired_credit:
        raise ValueError("credito_desejado invalido")
    own, fgts = _money(getattr(payload, "lance_proprio", 0)), _money(getattr(payload, "fgts", 0))
    desired_installment = _money(getattr(payload, "parcela_desejada", 0) or getattr(payload, "parcela_ideal", 0))
    income = _money(getattr(payload, "renda_total", 0))
    income_limit = _money(getattr(payload, "parcela_limite", 0)) or income * commitment_percent
    objective = str(getattr(payload, "objetivo", "") or "")
    preferred_strategy = "investment" if is_investor_objective(objective) else "contemplation"
    viable, counters = [], {"inativo": 0, "tipo": 0, "incompleto": 0, "credito": 0, "parcela": 0}

    for group in groups:
        if normalize_text(str(group.get("status") or "")) not in ("", "ativo"):
            counters["inativo"] += 1
            continue
        if not compatible_tipo_bem(objective, str(group.get("tipo_bem") or ""), getattr(payload, "tipo_bem", "")):
            counters["tipo"] += 1
            continue
        credit_min, credit_max = _money(group.get("credito_minimo")), _money(group.get("credito_maximo"))
        if not credit_max:
            counters["incompleto"] += 1
            continue
        base = build_credit_liquidity_scenarios(desired_credit, own, fgts, group.get("percentual_lance_embutido"), group.get("taxa_adm"), group.get("fundo_reserva"))
        base.update(parcela_desejada=desired_installment, parcela_maxima=income_limit)
        scenarios = [item for item in (_scenario(base, "without_embedded", credit_min, credit_max), _scenario(base, "with_embedded", credit_min, credit_max)) if item]
        valid = [item for item in scenarios if item["compativel_credito"]]
        if not valid:
            counters["credito"] += 1
            continue
        raw_installment = group.get("parcela_inicial_grupo")
        installment = _money(raw_installment) if raw_installment not in (None, "") else None
        if installment is not None and installment > income_limit:
            counters["parcela"] += 1
        strategies = _strategies(group, valid, installment, income_limit)
        deviation = abs(installment - desired_installment) / desired_installment if installment is not None and desired_installment else None
        viable.append({
            "grupo_id": str(group.get("grupo_id") or ""), "grupo": str(group.get("grupo") or ""), "administradora": str(group.get("administradora") or ""), "tipo_bem": str(group.get("tipo_bem") or ""),
            "credito_minimo": round(credit_min, 2), "credito_maximo": round(credit_max, 2), "prazo_remanescente": group.get("prazo_remanescente"), "parcela_inicial": installment,
            "parcela_desejada": round(desired_installment, 2), "parcela_maxima": round(income_limit, 2), "desvio_percentual": round(deviation, 8) if deviation is not None else None,
            "cenarios": scenarios, "estrategias_possiveis": strategies, "dentro_limite_renda": installment is not None and installment <= income_limit,
            "destaque_preferencia": preferred_strategy == "investment" and "investment" in strategies or preferred_strategy == "contemplation" and any(key != "investment" for key in strategies),
        })
    viable.sort(key=lambda item: (not item["destaque_preferencia"], not item["dentro_limite_renda"], item["desvio_percentual"] is None, item["desvio_percentual"] or math.inf, str(item["grupo"])))
    for rank, item in enumerate(viable, 1): item["ranking"] = rank
    return {
        "motor": "360", "objetivo_declarado": objective, "estrategia_preferida": preferred_strategy,
        "cliente": {"credito_liquido_desejado": round(desired_credit, 2), "recurso_proprio": round(own, 2), "fgts": round(fgts, 2), "parcela_desejada": round(desired_installment, 2), "renda_total": round(income, 2), "parcela_maxima": round(income_limit, 2), "comprometimento_percentual": commitment_percent},
        "total_grupos_analisados": len(groups), "total_grupos_viaveis": len(viable), "totais_exclusao": counters,
        "passos": ["O objetivo declarado define apenas a preferencia de apresentacao, sem excluir outras estrategias.", "Cada grupo recebe cenarios sem e com lance embutido.", "A faixa e validada em cada cenario: coluna O <= credito contratado <= coluna U.", "Taxa administrativa (AC) e fundo de reserva (AA) formam o saldo devedor, sem alterar a faixa de credito.", "Capacidade de lance, prazo e parcela alimentam as estrategias de investimento e contemplacao."],
        "items": viable,
    }
