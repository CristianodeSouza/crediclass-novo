from __future__ import annotations

from typing import Any

from .lance_reference import calculate_lance_references
from .models import EstudoRequest


def as_number(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def latest_history_items(historico: dict) -> list[tuple[str, dict]]:
    return sorted((historico or {}).items())[-12:]


def average(values: list[float]) -> float | None:
    clean = [value for value in values if value is not None]
    return sum(clean) / len(clean) if clean else None


def summarize_history(historico: dict) -> dict:
    entries = latest_history_items(historico)
    maiores = [as_number(item.get("maior_lance"), None) for _, item in entries if item.get("maior_lance") is not None]
    menores = [as_number(item.get("menor_lance"), None) for _, item in entries if item.get("menor_lance") is not None]
    contemplacoes = [int(as_number(item.get("qtd_contemplacoes"), 0)) for _, item in entries]
    return {
        "meses_analisados": len(entries),
        "media_maior_lance": average(maiores),
        "media_menor_lance": average(menores),
        "media_contemplacoes": average(contemplacoes),
        "total_contemplacoes": sum(contemplacoes),
    }


def build_strategy(label: str, percentual: float | None, base: dict, operational_range: str) -> dict:
    if percentual is None:
        return {
            "estrategia": label,
            "percentual_lance": None,
            "lance_embutido": 0,
            "lance_proprio": 0,
            "credito_disponivel": base["credito_disponivel"],
            "parcela_apos_contemplacao": None,
            "prazo_apos_lance": None,
            "prazo_operacional": operational_range,
            "chance_contemplacao": "Historico insuficiente",
        }
    percentual = max(0.0, percentual)
    valor_total_lance = base["credito_original"] * percentual
    lance_embutido = min(base["lance_embutido"], valor_total_lance)
    lance_proprio = max(0.0, valor_total_lance - lance_embutido)
    return {
        "estrategia": label,
        "percentual_lance": percentual,
        "lance_embutido": lance_embutido,
        "lance_proprio": lance_proprio,
        "credito_disponivel": base["credito_disponivel"],
        "parcela_apos_contemplacao": None,
        "prazo_apos_lance": None,
        "prazo_operacional": operational_range,
        "chance_contemplacao": "Referencia operacional",
    }


def build_financeiro(payload: EstudoRequest, grupo: dict) -> dict:
    if payload.cenario:
        cenario = payload.cenario
        return {
            "credito": cenario.get("credito_liquido_total"),
            "credito_original": cenario.get("credito_contratado_total"),
            "percentual_lance_embutido": (
                cenario.get("lance_embutido_total", 0) / cenario.get("credito_contratado_total", 1)
                if cenario.get("credito_contratado_total")
                else 0
            ),
            "lance_embutido": cenario.get("lance_embutido_total", 0),
            "credito_disponivel": cenario.get("credito_liquido_total", 0),
            "recurso_proprio": cenario.get("recurso_proprio_total", 0),
            "fgts_utilizado": cenario.get("fgts_utilizado_total", 0),
            "percentual_lance_total": cenario.get("percentual_lance_total", 0),
            "valor_total_lance": cenario.get("lance_total", 0),
            "parcela_inicial": cenario.get("parcela_total", 0),
            "renda_minima": cenario.get("renda_minima", 0),
            "score_cenario": cenario.get("score_cenario", 0),
            "status_cenario": cenario.get("status", ""),
            "alertas": cenario.get("alertas", []),
            "cartas": cenario.get("cartas", []),
            "parcela_apos_contemplacao": None,
            "prazo_apos_contemplacao": None,
            "prazo_operacional": cenario.get("estrategia", ""),
            "custo_efetivo_total": cenario.get("credito_contratado_total", 0),
            "seguro_garantia": None,
            "chance_contemplacao": "Cenario aprovado herdado da viabilidade",
            "estrategia_recomendada": cenario.get("estrategia", "Cenario financeiro"),
            "estrategias": [],
            "historico_12_meses": {},
        }
    cliente = payload.cliente
    credito_desejado = as_number(cliente.credito_desejado)
    percentual_embutido = as_number(grupo.get("percentual_lance_embutido"))
    credito_original = credito_desejado / (1 - percentual_embutido) if 0 < percentual_embutido < 1 else credito_desejado
    lance_embutido = credito_original * percentual_embutido
    recurso_proprio = as_number(cliente.lance_proprio) + as_number(cliente.fgts)
    valor_total_lance = lance_embutido + recurso_proprio
    percentual_lance_total = valor_total_lance / credito_original if credito_original else 0
    credito_disponivel = credito_original - lance_embutido
    prazo = int(as_number(grupo.get("prazo_restante")) or as_number(grupo.get("prazo_total")) or as_number(cliente.prazo_desejado) or 1)
    taxa_adm = as_number(grupo.get("taxa_adm"))
    fundo_reserva = as_number(grupo.get("fundo_reserva"))
    custo_total = credito_original * (1 + taxa_adm + fundo_reserva)
    parcela_inicial = custo_total / prazo
    historico = summarize_history(grupo.get("historico") or {})
    references = calculate_lance_references(
        grupo.get("historico") or {},
        grupo.get("percentual_lance_fixo"),
    )
    base = {
        "credito_original": credito_original,
        "lance_embutido": lance_embutido,
        "credito_disponivel": credito_disponivel,
        "prazo": prazo,
        "custo_total": custo_total,
    }
    estrategias = [
        build_strategy("Investidor", references["lance_investidor"], base, "Sem urgencia"),
        build_strategy("Conservador", references["lance_conservador_24m"], base, "Ate 24 meses"),
        build_strategy("Moderado", references["lance_moderado_12m"], base, "Ate 12 meses"),
        build_strategy("Agressivo", references["lance_agressivo_6m"], base, "Ate 6 meses"),
        build_strategy("Super Agressivo", references["lance_super_agressivo_3m"], base, "Ate 3 meses"),
    ]
    return {
        "credito": credito_desejado,
        "credito_original": credito_original,
        "percentual_lance_embutido": percentual_embutido,
        "lance_embutido": lance_embutido,
        "credito_disponivel": credito_disponivel,
        "recurso_proprio": recurso_proprio,
        "percentual_lance_total": percentual_lance_total,
        "valor_total_lance": valor_total_lance,
        "parcela_inicial": parcela_inicial,
        "parcela_apos_contemplacao": None,
        "prazo_apos_contemplacao": None,
        "prazo_operacional": "Definido pelo perfil de lance",
        "custo_efetivo_total": custo_total,
        "seguro_garantia": grupo.get("seguro_garantia"),
        "chance_contemplacao": "Referencia operacional; nao garante contemplacao",
        "estrategia_recomendada": "Perfil definido na Viabilidade",
        "estrategias": estrategias,
        "historico_12_meses": historico,
    }
