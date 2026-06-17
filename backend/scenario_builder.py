from __future__ import annotations

from itertools import combinations
import math
from typing import Any

from .credit_composition import as_float, build_card_from_liquid, embedded_bid_percent, summarize_cards
from .lance_reference import calculate_lance_references, reference_in_profile_range
from .models import ViabilidadeRequest
from .scenario_scoring import scenario_score
from .strategy_profile import strategic_profile_for_months
from .viabilidade import client_fgts_total, compatible_tipo_bem, normalize_text


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

    by_admin: dict[str, list[dict[str, Any]]] = {}
    for group in eligible:
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
        "total_grupos_analisados": len(groups),
        "total_cenarios": len(scenarios),
        "total_cenarios_viaveis": len([item for item in scenarios if item["status"] != "inviavel"]),
        "cenarios": scenarios[:30],
    }
