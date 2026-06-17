from __future__ import annotations

import math
from typing import Any


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def embedded_bid_percent(group: dict[str, Any], considerar_lance_embutido: bool = True) -> float:
    if not considerar_lance_embutido or not group.get("lance_embutido"):
        return 0.0
    percent = as_float(group.get("percentual_lance_embutido"))
    if percent < 0 or percent >= 1:
        return 0.0
    return percent


def contracted_credit_for_liquid(credito_liquido: float, percentual_lance_embutido: float) -> dict[str, float]:
    percent = max(0.0, min(float(percentual_lance_embutido or 0), 0.95))
    credito_contratado = float(credito_liquido) / (1 - percent)
    lance_embutido = credito_contratado * percent
    return {
        "credito_contratado": round(credito_contratado, 2),
        "lance_embutido": round(lance_embutido, 2),
        "credito_liquido": round(credito_contratado - lance_embutido, 2),
    }


def build_card_from_liquid(
    group: dict[str, Any],
    credito_liquido: float,
    recurso_proprio_total: float,
    fgts_total: float,
    parcela_limite: float,
    considerar_lance_embutido: bool = True,
) -> dict[str, Any]:
    percent_embutido = embedded_bid_percent(group, considerar_lance_embutido)
    credit = contracted_credit_for_liquid(credito_liquido, percent_embutido)
    credito_contratado = credit["credito_contratado"]
    lance_embutido = credit["lance_embutido"]
    fgts_utilizado = fgts_total if group.get("fgts") else 0.0
    recurso_proprio_utilizado = max(0.0, recurso_proprio_total)
    lance_total = lance_embutido + recurso_proprio_utilizado + fgts_utilizado
    taxa_adm = as_float(group.get("taxa_adm"))
    fundo_reserva = as_float(group.get("fundo_reserva"))
    taxa_adm_valor = credito_contratado * taxa_adm
    fundo_reserva_valor = credito_contratado * fundo_reserva
    custo_total = credito_contratado + taxa_adm_valor + fundo_reserva_valor
    prazo_restante = int(as_float(group.get("prazo_restante"), as_float(group.get("prazo_total"))))
    prazo_base = prazo_restante or int(as_float(group.get("prazo_total")))
    parcela_estimada = custo_total / prazo_base if prazo_base > 0 else math.inf
    prazo_minimo = (custo_total - lance_total) / parcela_limite if parcela_limite > 0 else math.inf
    return {
        "grupo_id": str(group.get("grupo_id") or ""),
        "administradora": str(group.get("administradora") or ""),
        "grupo": str(group.get("grupo") or ""),
        "tipo_bem": str(group.get("tipo_bem") or ""),
        "credito_contratado": round(credito_contratado, 2),
        "percentual_lance_embutido": round(percent_embutido, 6),
        "lance_embutido": round(lance_embutido, 2),
        "credito_liquido": credit["credito_liquido"],
        "recurso_proprio_utilizado": round(recurso_proprio_utilizado, 2),
        "fgts_utilizado": round(fgts_utilizado, 2),
        "lance_total": round(lance_total, 2),
        "percentual_lance_total": round(lance_total / credito_contratado, 6) if credito_contratado else 0,
        "taxa_adm_valor": round(taxa_adm_valor, 2),
        "fundo_reserva_valor": round(fundo_reserva_valor, 2),
        "parcela_estimada": round(parcela_estimada, 2) if math.isfinite(parcela_estimada) else parcela_estimada,
        "prazo_restante": prazo_restante,
        "prazo_minimo": round(max(0.0, prazo_minimo), 2) if math.isfinite(prazo_minimo) else prazo_minimo,
    }


def summarize_cards(cards: list[dict[str, Any]]) -> dict[str, float]:
    return {
        "credito_contratado_total": round(sum(as_float(card.get("credito_contratado")) for card in cards), 2),
        "credito_liquido_total": round(sum(as_float(card.get("credito_liquido")) for card in cards), 2),
        "lance_embutido_total": round(sum(as_float(card.get("lance_embutido")) for card in cards), 2),
        "recurso_proprio_total": round(sum(as_float(card.get("recurso_proprio_utilizado")) for card in cards), 2),
        "fgts_utilizado_total": round(sum(as_float(card.get("fgts_utilizado")) for card in cards), 2),
        "lance_total": round(sum(as_float(card.get("lance_total")) for card in cards), 2),
        "parcela_total": round(sum(as_float(card.get("parcela_estimada")) for card in cards), 2),
    }
