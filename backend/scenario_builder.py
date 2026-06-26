from __future__ import annotations

from itertools import combinations
import math
from typing import Any

from .credit_composition import as_float, build_card_from_liquid, embedded_bid_percent, summarize_cards
from .lance_reference import calculate_lance_references, reference_in_profile_range
from .models import ViabilidadeRequest
from .scenario_scoring import scenario_score
from .strategy_profile import strategic_profile_for_months
from .viabilidade import client_fgts_total, compatible_tipo_bem, history_last_12_months, normalize_text


STAGE4_CONTEMPLATION_RULES = {
    "3 meses": {
        "label": "Contemplacao Urgente",
        "field": "lance_super_agressivo_3m",
        "limit": 20,
    },
    "6 meses": {
        "label": "Contemplacao Rapida",
        "field": "lance_agressivo_6m",
        "limit": 20,
    },
    "12 meses": {
        "label": "Contemplacao Moderada",
        "field": "lance_moderado_12m",
        "limit": 20,
    },
    "24 meses": {
        "label": "Contemplacao Conservadora",
        "field": "lance_conservador_24m",
        "limit": 20,
    },
    "36 meses": {
        "label": "Contemplacao Investidor",
        "field": "lance_investidor",
        "limit": 20,
    },
}

STAGE4_INVESTMENT_OBJECTIVES = {
    "adquirir imovel e alugar": "Investidor - Comprar imovel para alugar",
    "adquirir terreno construir e alugar": "Investidor - Comprar terreno, construir e alugar",
    "adquirir terreno construir e vender": "Investidor - Comprar terreno, construir e vender",
    "vender carta contemplada": "Investidor - Venda de carta contemplada",
    "carta de credito aposentadoria": "Investidor - Carta de credito para aposentadoria",
}


def _max_liquid(group: dict[str, Any], considerar_lance_embutido: bool) -> float:
    return as_float(group.get("credito_maximo")) * (1 - embedded_bid_percent(group, considerar_lance_embutido))


def _min_liquid(group: dict[str, Any], considerar_lance_embutido: bool) -> float:
    return as_float(group.get("credito_minimo")) * (1 - embedded_bid_percent(group, considerar_lance_embutido))


def _allocate_liquid(target: float, groups: tuple[dict[str, Any], ...], considerar_lance_embutido: bool) -> list[float] | None:
    minimums = [_min_liquid(group, considerar_lance_embutido) for group in groups]
    maximums = [_max_liquid(group, considerar_lance_embutido) for group in groups]
    if target < sum(minimums) or target > sum(maximums):
        return None
    values = minimums[:]
    remaining = target - sum(values)
    for index, maximum in sorted(enumerate(maximums), key=lambda item: item[1], reverse=True):
        room = maximum - values[index]
        addition = min(room, remaining)
        values[index] += addition
        remaining -= addition
        if remaining <= 0.01:
            break
    if remaining > 0.01:
        return None
    return [round(value, 2) for value in values]


def _scenario_status(alertas: list[str], parcela_compativel: bool, renda_compativel: bool) -> str:
    if not parcela_compativel or not renda_compativel:
        return "inviavel"
    return "viavel_com_alertas" if alertas else "viavel"


def _reference_from_group(group: dict[str, Any], profile_field: str) -> float | None:
    historico = group.get("historico") or {}
    if historico:
        references = calculate_lance_references(historico, group.get("percentual_lance_fixo"))
        return references.get(profile_field)
    aliases = {
        "lance_super_agressivo_3m": ["lance_super_agressivo_3m", "lance_agressivo"],
        "lance_agressivo_6m": ["lance_agressivo_6m", "lance_moderado"],
        "lance_moderado_12m": ["lance_moderado_12m", "lance_conservador"],
        "lance_conservador_24m": ["lance_conservador_24m", "lance_super_conservador"],
        "lance_investidor": ["lance_investidor"],
    }
    for field in aliases.get(profile_field, [profile_field]):
        value = group.get(field)
        if value is not None:
            return as_float(value)
    return None


def history_last_12_months_for_group(group: dict[str, Any]) -> dict[str, Any]:
    return history_last_12_months(group.get("historico") or {})


def _stage4_objective_kind(objetivo: str) -> str:
    normalized = normalize_text(objetivo)
    return "investimento" if normalized.startswith("investidor") else "contemplacao"


def _contemplation_rule_for_payload(payload: ViabilidadeRequest) -> dict[str, Any]:
    objective = normalize_text(payload.objetivo)
    if "6 meses" in objective or "rapido" in objective:
        return STAGE4_CONTEMPLATION_RULES["6 meses"]
    if "12 meses" in objective or "moderado" in objective:
        return STAGE4_CONTEMPLATION_RULES["12 meses"]
    if "24 meses" in objective or "conservador" in objective:
        return STAGE4_CONTEMPLATION_RULES["24 meses"]
    if "36 meses" in objective or "investidor" in objective:
        return STAGE4_CONTEMPLATION_RULES["36 meses"]
    return STAGE4_CONTEMPLATION_RULES["3 meses"]


def _investment_objective_label(objetivo: str) -> str:
    normalized = normalize_text(objetivo).replace("(", " ").replace(")", " ")
    normalized = " ".join(normalized.split())
    for fragment, label in STAGE4_INVESTMENT_OBJECTIVES.items():
        if fragment in normalized:
            return label
    return "Investidor - Estrategia de investimento"


def _benefit_flag(value: Any) -> bool:
    normalized = normalize_text(str(value or ""))
    return normalized.startswith("sim") or normalized in {"true", "1", "possui", "permite"}


def _investment_benefit_score(group: dict[str, Any]) -> float:
    prazo = as_float(group.get("prazo_restante"), as_float(group.get("prazo_total")))
    taxa_total = as_float(group.get("taxa_adm")) + as_float(group.get("fundo_reserva"))
    taxa_ano = as_float(group.get("taxa_adm_ano")) + as_float(group.get("fundo_reserva_ano"))
    lance_embutido = embedded_bid_percent(group, True)
    lance_fixo = as_float(group.get("percentual_lance_fixo"))
    parcela_reduzida = as_float(group.get("percentual_parcela_reduzida"), as_float(group.get("parcela_reduzida")))
    moderado = _reference_from_group(group, "lance_moderado_12m")
    conservador = _reference_from_group(group, "lance_conservador_24m")
    investidor = _reference_from_group(group, "lance_investidor")
    historico = history_last_12_months_for_group(group)
    total_contemplacoes = as_float(historico.get("total_contemplacoes"))
    fixed_and_free = _benefit_flag(group.get("permite_lance_fixo_livre_texto")) or _benefit_flag(group.get("permite_lance_fixo_livre"))
    return (
        max(0.0, 35 - taxa_total * 100) * 1.3
        + max(0.0, 10 - taxa_ano * 100) * 0.8
        + parcela_reduzida * 20
        + min(30.0, prazo / 12)
        + lance_embutido * 40
        + max(0.0, 25 - lance_fixo * 100) * 0.7
        + (12 if fixed_and_free else 0)
        + max(0.0, 30 - as_float(moderado) * 100) * 0.4
        + max(0.0, 25 - as_float(conservador) * 100) * 0.4
        + max(0.0, 20 - as_float(investidor) * 100) * 0.5
        + min(25.0, total_contemplacoes * 2)
    )


def _stage4_contemplation_filter(payload: ViabilidadeRequest, groups: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rule = _contemplation_rule_for_payload(payload)
    field = str(rule["field"])
    scored = []
    fallback = []
    for group in groups:
        reference = _reference_from_group(group, field)
        if reference is None:
            continue
        history = history_last_12_months_for_group(group)
        score = (
            (100 if reference_in_profile_range(field, reference) else 45)
            + min(30, int(history["total_contemplacoes"]) * 2)
            + max(0, 25 - reference * 100)
            + min(15, as_float(group.get("prazo_restante"), as_float(group.get("prazo_total"))) / 24)
        )
        item = (score, group)
        if reference_in_profile_range(field, reference):
            scored.append(item)
        else:
            fallback.append(item)
    ordered = [group for _, group in sorted(scored or fallback, key=lambda item: item[0], reverse=True)]
    selected = ordered[: int(rule["limit"])]
    return selected, {
        "fluxo": "contemplacao",
        "filtro_1": "Classificacao pela urgencia de contemplacao",
        "conceito": rule["label"],
        "campo_lance": field,
        "limite": int(rule["limit"]),
        "total_entrada": len(groups),
        "total_pos_filtro_1": len(selected),
        "fallback_usado": not scored and bool(fallback),
    }


def _stage4_investment_filter(payload: ViabilidadeRequest, groups: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    objective_label = _investment_objective_label(payload.objetivo)
    scored = sorted(
        ((_investment_benefit_score(group), group) for group in groups),
        key=lambda item: item[0],
        reverse=True,
    )
    selected = [group for _, group in scored[:10]]
    return selected, {
        "fluxo": "investimento",
        "filtro_1": "Classificacao pelo objetivo de investimento",
        "estrategia": objective_label,
        "criterios": [
            "Menor taxa total",
            "Menor taxa ano",
            "Maior parcela reduzida",
            "Maior prazo remanescente",
            "Maior lance embutido",
            "Menor lance fixo",
            "Participa do fixo e livre",
            "Menores lances moderado/conservador/investidor",
            "Maior historico de contemplacoes",
        ],
        "limite": 10,
        "total_entrada": len(groups),
        "total_pos_filtro_1": len(selected),
    }


def stage4_filter_candidates(payload: ViabilidadeRequest, groups: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if _stage4_objective_kind(payload.objetivo) == "investimento":
        return _stage4_investment_filter(payload, groups)
    return _stage4_contemplation_filter(payload, groups)


def _candidate_pool_for_admin(
    groups: list[dict[str, Any]],
    target: float,
    considerar_lance_embutido: bool,
    limit: int,
) -> list[dict[str, Any]]:
    selected: dict[str, dict[str, Any]] = {}
    liquid_max = [(group, _max_liquid(group, considerar_lance_embutido)) for group in groups]
    for divisor in (1, 2, 3):
        chunk = target / divisor
        for group, _ in sorted(liquid_max, key=lambda item: abs(item[1] - chunk))[:limit]:
            selected[str(group.get("grupo_id") or id(group))] = group
    for group, _ in sorted(liquid_max, key=lambda item: item[1], reverse=True)[:limit]:
        selected[str(group.get("grupo_id") or id(group))] = group
    return list(selected.values())[:limit]


def analyze_scenarios(payload: ViabilidadeRequest, groups: list[dict[str, Any]], max_cards: int = 3, max_groups_per_admin: int = 10) -> dict[str, Any]:
    profile = strategic_profile_for_months(payload.prazo_desejado)
    fgts_total = client_fgts_total(payload)
    parcela_ideal = float(payload.parcela_ideal or payload.parcela_desejada)
    parcela_limite = float(payload.parcela_limite or payload.parcela_desejada)
    recurso_total = float(payload.lance_proprio or 0)
    eligible: list[dict[str, Any]] = []
    for group in groups:
        if normalize_text(str(group.get("status") or "")) != "ativo":
            continue
        if not compatible_tipo_bem(payload.objetivo, str(group.get("tipo_bem") or ""), payload.tipo_bem):
            continue
        prazo_restante = as_float(group.get("prazo_restante"), as_float(group.get("prazo_total")))
        if prazo_restante <= 0:
            continue
        eligible.append(group)

    filtered_groups, stage4_summary = stage4_filter_candidates(payload, eligible)
    by_admin: dict[str, list[dict[str, Any]]] = {}
    for group in filtered_groups:
        by_admin.setdefault(str(group.get("administradora") or ""), []).append(group)

    scenarios: list[dict[str, Any]] = []
    counter = 1
    for administradora, raw_admin_groups in by_admin.items():
        admin_groups = _candidate_pool_for_admin(
            raw_admin_groups,
            payload.credito_desejado,
            payload.considerar_lance_embutido,
            max_groups_per_admin,
        )
        for quantity in range(1, min(max_cards, len(admin_groups)) + 1):
            for combo in combinations(admin_groups, quantity):
                if sum(_max_liquid(group, payload.considerar_lance_embutido) for group in combo) < payload.credito_desejado:
                    continue
                allocations = _allocate_liquid(payload.credito_desejado, combo, payload.considerar_lance_embutido)
                if allocations is None:
                    continue
                cards = []
                alertas: list[str] = []
                recurso_por_carta = recurso_total / quantity if quantity else 0
                fgts_por_carta = fgts_total / quantity if quantity else 0
                for group, credito_liquido in zip(combo, allocations):
                    card = build_card_from_liquid(
                        group,
                        credito_liquido,
                        recurso_por_carta,
                        fgts_por_carta,
                        parcela_limite,
                        payload.considerar_lance_embutido,
                    )
                    lance_ref = _reference_from_group(group, profile["campo_lance"])
                    card["referencia_lance"] = lance_ref
                    card["perfil"] = profile["perfil"]
                    card["historico_lance_insuficiente"] = lance_ref is None
                    if lance_ref is None:
                        alertas.append("historico_lance_insuficiente")
                    elif not reference_in_profile_range(profile["campo_lance"], lance_ref):
                        alertas.append("lance_historico_fora_do_perfil")
                    elif card["percentual_lance_total"] < float(lance_ref):
                        alertas.append("lance_total_abaixo_da_referencia")
                    if fgts_total > 0 and not group.get("fgts"):
                        alertas.append("fgts_nao_permitido")
                    if as_float(group.get("percentual_lance_embutido")) > 0 and not group.get("lance_embutido"):
                        alertas.append("lance_embutido_nao_permitido")
                    if math.isfinite(card["prazo_minimo"]) and card["prazo_restante"] < card["prazo_minimo"]:
                        alertas.append("prazo_incompativel")
                    cards.append(card)

                totals = summarize_cards(cards)
                renda_minima = totals["parcela_total"] * 3
                parcela_compativel = totals["parcela_total"] <= parcela_limite
                renda_compativel = float(payload.renda_total or 0) >= renda_minima
                if not parcela_compativel:
                    alertas.append("parcela_total_acima_do_limite")
                if not renda_compativel:
                    alertas.append("renda_insuficiente")
                if totals["recurso_proprio_total"] > recurso_total + 0.01:
                    alertas.append("recurso_proprio_excedido")
                scenario = {
                    "id": f"cenario_{counter:03d}",
                    "administradora": administradora,
                    "estrategia": profile["perfil"],
                    "quantidade_cartas": quantity,
                    **totals,
                    "percentual_lance_total": round(totals["lance_total"] / totals["credito_contratado_total"], 6)
                    if totals["credito_contratado_total"]
                    else 0,
                    "renda_minima": round(renda_minima, 2),
                    "excedente_credito_liquido": round(max(0.0, totals["credito_liquido_total"] - payload.credito_desejado), 2),
                    "status": _scenario_status(sorted(set(alertas)), parcela_compativel, renda_compativel),
                    "alertas": sorted(set(alertas)),
                    "cartas": cards,
                }
                scenario["score_cenario"] = scenario_score(scenario, payload.credito_desejado, parcela_ideal, parcela_limite)
                scenarios.append(scenario)
                counter += 1

    scenarios.sort(key=lambda item: (item["status"] == "inviavel", -item["score_cenario"], item["quantidade_cartas"]))
    return {
        "cliente": {
            "credito_liquido_desejado": round(payload.credito_desejado, 2),
            "perfil_estrategico": profile["perfil"],
            "prazo_desejado": payload.prazo_desejado,
            "parcela_ideal": round(parcela_ideal, 2),
            "parcela_limite": round(parcela_limite, 2),
            "renda_total": round(float(payload.renda_total or 0), 2),
            "fgts_total": round(fgts_total, 2),
            "recursos_proprios_para_lance": round(recurso_total, 2),
        },
        "etapa4": stage4_summary,
        "total_grupos_analisados": len(groups),
        "total_grupos_elegiveis": len(eligible),
        "total_grupos_pos_filtro_1": len(filtered_groups),
        "total_cenarios": len(scenarios),
        "total_cenarios_viaveis": len([item for item in scenarios if item["status"] != "inviavel"]),
        "cenarios": scenarios[:30],
    }
