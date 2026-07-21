from __future__ import annotations

import math
import re
from typing import Any

from .viabilidade import normalize_text


CONTEMPLAR_OBJECTIVE_PREFIX = "contemplar"


def is_contemplar_objective(objective: str) -> bool:
    return normalize_text(objective).startswith(CONTEMPLAR_OBJECTIVE_PREFIX)


def normalize_money(value: Any, field_name: str, *, positive: bool = False) -> float:
    """Normalizes Brazilian currency inputs before the domain calculation."""
    if isinstance(value, bool) or value is None:
        raise ValueError(f"{field_name} invalido")
    if isinstance(value, (int, float)):
        number = float(value)
    else:
        text = str(value).strip().replace("R$", "").replace(" ", "")
        if not text:
            raise ValueError(f"{field_name} invalido")
        text = re.sub(r"[^0-9,.-]", "", text)
        if "," in text:
            text = text.replace(".", "").replace(",", ".")
        try:
            number = float(text)
        except ValueError as error:
            raise ValueError(f"{field_name} invalido") from error
    if not math.isfinite(number) or number < 0 or (positive and number <= 0):
        raise ValueError(f"{field_name} invalido")
    return round(number, 2)


def calculate_required_gross_credit(
    desired_net_credit: Any,
    own_resources: Any = 0,
    fgts: Any = 0,
) -> float:
    desired = normalize_money(desired_net_credit, "credito_desejado", positive=True)
    own = normalize_money(own_resources, "lance_proprio")
    fgts_value = normalize_money(fgts, "fgts")
    return round(desired + own + fgts_value, 2)


def _group_sort_key(item: dict[str, Any]) -> tuple[float, int, str]:
    group = str(item.get("grupo") or item.get("grupo_id") or "")
    match = re.search(r"\d+", group)
    return (
        float(item["margem_credito"]),
        int(match.group()) if match else math.inf,
        group,
    )


def analyze_contemplar_groups(payload: Any, groups: list[dict[str, Any]]) -> dict[str, Any]:
    desired_credit = normalize_money(payload.credito_desejado, "credito_desejado", positive=True)
    own_resources = normalize_money(payload.lance_proprio, "lance_proprio")
    fgts = normalize_money(payload.fgts, "fgts")
    required_credit = calculate_required_gross_credit(desired_credit, own_resources, fgts)

    compatible: list[dict[str, Any]] = []
    incompatible_credit = 0
    incomplete = 0

    for group in groups:
        credit_max_raw = group.get("credito_maximo")
        try:
            credit_max = normalize_money(credit_max_raw, "credito_maximo", positive=True)
        except ValueError:
            incomplete += 1
            continue

        if credit_max < required_credit:
            incompatible_credit += 1
            continue

        credit_min_raw = group.get("credito_minimo")
        try:
            credit_min = normalize_money(credit_min_raw, "credito_minimo")
        except ValueError:
            credit_min = None

        compatible.append({
            "grupo_id": str(group.get("grupo_id") or ""),
            "grupo": str(group.get("grupo") or ""),
            "administradora": str(group.get("administradora") or ""),
            "credito_minimo": credit_min,
            "credito_maximo": credit_max,
            "credito_bruto_necessario": required_credit,
            "margem_credito": round(credit_max - required_credit, 2),
            "compatibilidade": "Compativel",
            "origens": {
                "credito_liquido_desejado": "front-end",
                "recurso_proprio": "front-end",
                "fgts": "front-end",
                "credito_maximo": "planilha coluna U",
                "credito_minimo": "planilha coluna O (informativo)",
            },
        })

    compatible.sort(key=_group_sort_key)
    for ranking, item in enumerate(compatible, start=1):
        item["ranking"] = ranking

    return {
        "perfil_contemplar": True,
        "objetivo": payload.objetivo,
        "cliente": {
            "credito_liquido_desejado": desired_credit,
            "recurso_proprio": own_resources,
            "fgts": fgts,
            "credito_bruto_necessario": required_credit,
        },
        "total_grupos_analisados": len(groups),
        "total_grupos_compativeis": len(compatible),
        "total_grupos_incompativeis_credito": incompatible_credit,
        "total_grupos_incompletos": incomplete,
        "filtros": {
            "regra": "credito_maximo >= credito_bruto_necessario",
            "ordem": "margem_credito ASC, grupo ASC",
            "sem_limite_de_resultados": True,
        },
        "passos": [
            "Identificado o perfil Contemplar pelo objetivo selecionado.",
            f"Credito bruto necessario = credito liquido desejado ({desired_credit:,.2f}) + recurso proprio ({own_resources:,.2f}) + FGTS ({fgts:,.2f}) = {required_credit:,.2f}.",
            "Foram mantidos somente grupos cujo Maior Credito (coluna U) e maior ou igual ao credito bruto necessario.",
            "Credito minimo (coluna O) e exibido apenas como informacao e nao elimina grupos.",
            "Os grupos compativeis foram ordenados da menor para a maior margem de credito, sem limite de quantidade.",
        ],
        "items": compatible,
    }
