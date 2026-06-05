from __future__ import annotations

import math
import re
from typing import Any


LANCE_INCREMENT = 0.0025

PROFILE_BY_MONTHS = [
    (3, "Agressivo", "lance_agressivo", "1 a 3 meses"),
    (6, "Moderado", "lance_moderado", "4 a 6 meses"),
    (12, "Conservador", "lance_conservador", "7 a 12 meses"),
    (24, "Super Conservador", "lance_super_conservador", "13 a 24 meses"),
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


def valid_lower_bids(historico: dict[str, Any], limit: int) -> list[float]:
    valid_items = []
    for month, item in (historico or {}).items():
        if not re.fullmatch(r"\d{4}-\d{2}", str(month)):
            continue
        value = _history_value(item, "menor_lance")
        if value is None:
            continue
        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            continue
        if numeric_value < 0:
            continue
        valid_items.append((str(month), numeric_value))
    valid_items.sort(key=lambda entry: entry[0], reverse=True)
    return [value for _, value in valid_items[:limit]]


def second_lowest_reference(historico: dict[str, Any], months: int) -> float | None:
    values = valid_lower_bids(historico, months)
    if len(values) < 2:
        return None
    return round(sorted(values)[1] + LANCE_INCREMENT, 6)


def aggressive_reference(historico: dict[str, Any]) -> float | None:
    values = valid_lower_bids(historico, 3)
    if len(values) < 3:
        return None
    return round(max(values) + LANCE_INCREMENT, 6)


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
    return {
        "lance_investidor": investor_reference(percentual_lance_fixo),
        "lance_super_conservador": second_lowest_reference(historico, 12),
        "lance_conservador": second_lowest_reference(historico, 12),
        "lance_moderado": second_lowest_reference(historico, 6),
        "lance_agressivo": aggressive_reference(historico),
    }
