from __future__ import annotations

from .lance_reference import classify_profile


def strategic_profile_for_months(prazo_desejado: int) -> dict[str, str]:
    label, field, operational_range = classify_profile(prazo_desejado)
    return {
        "perfil": label,
        "campo_lance": field,
        "faixa_operacional": operational_range,
    }
