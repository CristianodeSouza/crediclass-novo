from __future__ import annotations

import math
import re
from typing import Any


LANCE_INCREMENT = 0.0025

PROFILE_LANCE_RANGES = {
    "lance_super_agressivo_3m": (0.50, None),
    "lance_agressivo_6m": (0.40, 0.50),
    "lance_moderado_12m": (0.30, 0.40),
    "lance_conservador_24m": (0.20, 0.30),
    "lance_investidor": (0.0, 0.20),
    "lance_agressivo": (0.40, 0.50),
    "lance_moderado": (0.30, 0.40),
    "lance_conservador": (0.20, 0.30),
    "lance_super_conservador": (0.20, 0.30),
}

PROFILE_BY_MONTHS = [
    (3, "Super Agressivo", "lance_super_agressivo_3m", "Ate 3 meses"),
    (6, "Agressivo", "lance_agressivo_6m", "Ate 6 meses"),
    (12, "Moderado", "lance_moderado_12m", "Ate 12 meses"),
    (24, "Conservador", "lance_conservador_24m", "Ate 24 meses"),
    (math.inf, "Investidor", "lance_investidor", "Sem urgencia"),
]


def classify_profile(prazo_desejado: int) -> tuple[str, str, str]:
    for max_months, label, field, operational_range in PROFILE_BY_MONTHS:
        if prazo_desejado <= max_months:
            return label, field, operational_range
    return "Investidor", "lance_investidor", "Sem urgencia"


def _history_value(item: Any, field: str) -> Any:
    if isinstance(item, dict):
        return item.get(field)
    return getattr(item, field, None)


def valid_lower_bids(historico: dict[str, Any], limit: int, only_contemplated: bool = False) -> list[float]:
    valid_items = []
    for month, item in (historico or {}).items():
        if not re.fullmatch(r"\d{4}-\d{2}", str(month)):
            continue
        if only_contemplated:
            try:
                contemplated = int(_history_value(item, "qtd_contemplacoes") or 0)
            except (TypeError, ValueError):
                contemplated = 0
            if contemplated <= 0:
                continue
        value = _history_value(item, "menor_lance")
        if value is None:
            continue
        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            continue
        if numeric_value <= 0:
            continue
        valid_items.append((str(month), numeric_value))
    valid_items.sort(key=lambda entry: entry[0], reverse=True)
    return [value for _, value in valid_items[:limit]]


def second_lowest_reference(historico: dict[str, Any], months: int) -> float | None:
    values = valid_lower_bids(historico, months, only_contemplated=True)
    if len(values) < 2:
        return None
    return round(sorted(values)[1] + LANCE_INCREMENT, 6)


def super_aggressive_reference(historico: dict[str, Any]) -> float | None:
    values = valid_lower_bids(historico, 3, only_contemplated=True)
    if len(values) < 2:
        return None
    return round(max(values) + LANCE_INCREMENT, 6)


def aggressive_reference(historico: dict[str, Any]) -> float | None:
    return second_lowest_reference(historico, 6)


def investor_reference(percentual_lance_fixo: Any) -> float:
    try:
        value = float(percentual_lance_fixo)
    except (TypeError, ValueError):
        value = 0.0
    return round(max(0.0, min(0.20, value)), 6)


def calculate_lance_references(
    historico: dict[str, Any],
    percentual_lance_fixo: Any = None,
) -> dict[str, float | None]:
    super_agressivo = super_aggressive_reference(historico)
    agressivo = aggressive_reference(historico)
    moderado = second_lowest_reference(historico, 12)
    conservador = second_lowest_reference(historico, 12)
    investidor = investor_reference(percentual_lance_fixo)
    return {
        "lance_investidor": investor_reference(percentual_lance_fixo),
        "lance_super_agressivo_3m": super_agressivo,
        "lance_agressivo_6m": agressivo,
        "lance_moderado_12m": moderado,
        "lance_conservador_24m": conservador,
        "lance_super_conservador": conservador,
        "lance_conservador": moderado,
        "lance_moderado": agressivo,
        "lance_agressivo": super_agressivo,
    }


def reference_in_profile_range(field: str, value: float | None) -> bool:
    if value is None:
        return False
    minimum, maximum = PROFILE_LANCE_RANGES.get(field, (None, None))
    if minimum is not None and value < minimum:
        return False
    if maximum is not None and value > maximum:
        return False
    return True
