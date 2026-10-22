"""Canonical Motor 360 credit-option mapping from source group columns."""

from __future__ import annotations

from .motor360_math import money, parse_decimal


CREDIT_OPTION_FIELDS = (
    ("credito_minimo", "Menor Crédito"),
    ("credito_intermediario_1", "Créd. Inter. 1"),
    ("credito_intermediario_2", "Créd. Inter. 2"),
    ("credito_intermediario_3", "Créd. Inter. 3"),
    ("credito_maximo", "Maior Crédito"),
)


def available_credit_options(group: dict) -> list[dict]:
    """Return valid, positive and deduplicated values while preserving source fields."""
    source_values = group.get("source_values") if isinstance(group.get("source_values"), dict) else {}
    source_mapping = group.get("mapeamento_origem") or group.get("source_mapping") or source_values.get("mapeamento_origem") or {}
    indexed: dict[int, dict] = {}
    for field, label in CREDIT_OPTION_FIELDS:
        raw_value = group.get(field)
        if raw_value is None:
            raw_value = source_values.get(field)
        value = parse_decimal(raw_value)
        if value is None or value <= 0:
            continue
        amount = money(value)
        cents = round(amount * 100)
        mapping = source_mapping.get(field) if isinstance(source_mapping, dict) else None
        entry = indexed.setdefault(cents, {
            "value": amount,
            "labels": [],
            "source_fields": [],
            "sources": [],
        })
        entry["labels"].append(label)
        entry["source_fields"].append(field)
        entry["sources"].append({
            "field": field,
            "column": (mapping or {}).get("column") if isinstance(mapping, dict) else None,
            "header": (mapping or {}).get("header") if isinstance(mapping, dict) else None,
            "source": (mapping or {}).get("source") if isinstance(mapping, dict) else None,
        })
    return list(indexed.values())
