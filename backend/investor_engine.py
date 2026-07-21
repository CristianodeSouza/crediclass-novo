from __future__ import annotations

from typing import Any

from .credit_composition import as_float
from .viabilidade import compatible_tipo_bem, normalize_text


INVESTOR_OBJECTIVE_PREFIX = "investidor"


def is_investor_objective(objective: str) -> bool:
    return normalize_text(objective).startswith(INVESTOR_OBJECTIVE_PREFIX)


def classify_installment_distance(deviation: float) -> str:
    if deviation <= 0.05:
        return "Parcela ideal"
    if deviation <= 0.10:
        return "Muito próxima"
    if deviation <= 0.20:
        return "Próxima"
    return "Distante"


def analyze_investor_groups(payload: Any, groups: list[dict[str, Any]], commitment_percent: float = 0.30) -> dict[str, Any]:
    desired_credit = float(payload.credito_desejado)
    desired_installment = float(payload.parcela_desejada or payload.parcela_ideal or 0)
    income_limit = float(payload.parcela_limite or (float(payload.renda_total) * commitment_percent))
    considered = 0
    excluded_credit = 0
    excluded_installment = 0
    excluded_incomplete = 0
    excluded_type = 0
    compatible: list[dict[str, Any]] = []

    for group in groups:
        if normalize_text(str(group.get("status") or "")) != "ativo":
            continue
        considered += 1
        if not compatible_tipo_bem(payload.objetivo, str(group.get("tipo_bem") or ""), payload.tipo_bem):
            excluded_type += 1
            continue

        missing = set(group.get("dados_incompletos") or [])
        if group.get("credito_maximo") is None:
            missing.add("credito_maximo")
        if group.get("parcela_inicial_grupo") is None:
            missing.add("parcela_inicial_grupo")
        if missing:
            excluded_incomplete += 1
            continue

        credit_max = float(group["credito_maximo"])
        initial_installment = float(group["parcela_inicial_grupo"])
        if credit_max < desired_credit:
            excluded_credit += 1
            continue
        if initial_installment > income_limit:
            excluded_installment += 1
            continue

        difference = abs(initial_installment - desired_installment)
        deviation = difference / desired_installment if desired_installment > 0 else None
        compatible.append({
            "grupo_id": str(group.get("grupo_id") or ""),
            "grupo": str(group.get("grupo") or ""),
            "administradora": str(group.get("administradora") or ""),
            "tipo_bem": str(group.get("tipo_bem") or ""),
            "credito_maximo": round(credit_max, 2),
            "parcela_inicial": round(initial_installment, 2),
            "parcela_desejada": round(desired_installment, 2),
            "parcela_maxima": round(income_limit, 2),
            "diferenca_parcela": round(difference, 2),
            "desvio_percentual": round(deviation, 6) if deviation is not None else None,
            "classificacao_parcela": classify_installment_distance(deviation) if deviation is not None else "Sem referência",
            "prazo_remanescente": group.get("prazo_remanescente"),
            "origens": {
                "credito_desejado": "front-end",
                "parcela_desejada": "front-end",
                "parcela_maxima": "front-end/configuração",
                "credito_maximo": "planilha coluna U",
                "parcela_inicial": "planilha coluna AJ",
            },
        })

    compatible.sort(key=lambda item: (item["desvio_percentual"] is None, item["desvio_percentual"] or 0, -item["credito_maximo"]))
    selected = []
    for rank, item in enumerate(compatible, start=1):
        item["ranking"] = rank
        selected.append(item)

    return {
        "perfil_investidor": True,
        "objetivo": payload.objetivo,
        "cliente": {
            "credito_desejado_liquido": round(desired_credit, 2),
            "parcela_desejada": round(desired_installment, 2),
            "parcela_maxima": round(income_limit, 2),
            "renda_total": round(float(payload.renda_total), 2),
        },
        "filtros": {
            "credito_minimo_grupo": round(desired_credit, 2),
            "parcela_inicial_maxima": round(income_limit, 2),
            "ordem": "desvio_percentual ASC",
            "classificacao": {
                "ate_5_porcento": "Parcela ideal",
                "ate_10_porcento": "Muito próxima",
                "ate_20_porcento": "Próxima",
                "acima_de_20_porcento": "Distante",
            },
        },
        "total_grupos_considerados": considered,
        "total_grupos_compativeis": len(compatible),
        "total_grupos_exibidos": len(selected),
        "totais_exclusao": {
            "credito_insuficiente": excluded_credit,
            "parcela_acima_da_renda": excluded_installment,
            "dados_incompletos": excluded_incomplete,
            "tipo_incompativel": excluded_type,
        },
        "passos": [
            "Identificado o perfil Investidor pelo objetivo selecionado.",
            f"Filtrados grupos com Maior Crédito (coluna U) maior ou igual a R$ {desired_credit:,.2f}.",
            f"Filtrados grupos com Parcela Inicial (coluna AJ) menor ou igual a R$ {income_limit:,.2f}.",
            "Calculado o desvio percentual da parcela inicial em relação à parcela desejada.",
            "Ordenados os grupos compatíveis do menor para o maior desvio.",
        ],
        "items": selected,
    }
