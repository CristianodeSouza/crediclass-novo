from __future__ import annotations

from typing import Any


def clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, value))


def proximity_score(actual: float, target: float) -> float:
    if target <= 0:
        return 0.0
    return clamp(100 - abs(actual - target) / target * 100)


def installment_score(parcela_total: float, parcela_ideal: float, parcela_limite: float) -> float:
    if parcela_total <= parcela_ideal:
        return 100.0
    if parcela_limite > 0 and parcela_total <= parcela_limite:
        return clamp(80 - (parcela_total - parcela_ideal) / parcela_limite * 40)
    return 30.0


def scenario_score(scenario: dict[str, Any], credito_liquido_desejado: float, parcela_ideal: float, parcela_limite: float) -> float:
    credito = proximity_score(float(scenario["credito_liquido_total"]), credito_liquido_desejado)
    parcela = installment_score(float(scenario["parcela_total"]), parcela_ideal, parcela_limite)
    lance = 100.0 if "recurso_proprio_excedido" not in scenario["alertas"] else 30.0
    prazo = 100.0 if "prazo_incompativel" not in scenario["alertas"] else 35.0
    historico = 100.0 if "historico_lance_insuficiente" not in scenario["alertas"] else 55.0
    risco = 100.0 - min(60.0, len(scenario["alertas"]) * 12.0 + (scenario["quantidade_cartas"] - 1) * 8.0)
    score = (
        credito * 0.25
        + parcela * 0.20
        + lance * 0.20
        + prazo * 0.15
        + historico * 0.15
        + risco * 0.05
    )
    return round(clamp(score), 2)
