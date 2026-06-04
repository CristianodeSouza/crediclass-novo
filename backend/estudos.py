from datetime import datetime

from .models import EstudoRequest

_counter = 0
_studies: dict[str, dict] = {}


def as_number(value, default: float = 0.0) -> float:
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


def chance_from_percent(percentual: float, group: dict) -> str:
    agressivo = as_number(group.get("agressivo"), 0.5)
    moderado = as_number(group.get("moderado"), 0.3)
    conservador = as_number(group.get("conservador"), 0.2)
    if percentual >= agressivo:
        return "Alta"
    if percentual >= moderado:
        return "Media"
    if percentual >= conservador:
        return "Acompanhar"
    return "Baixa"


def build_strategy(label: str, percentual: float, base: dict, group: dict) -> dict:
    percentual = max(0.0, percentual)
    valor_total_lance = base["credito_original"] * percentual
    lance_embutido = min(base["lance_embutido"], valor_total_lance)
    lance_proprio = max(0.0, valor_total_lance - lance_embutido)
    prazo_apos = max(1, base["prazo"] - round(percentual * base["prazo"]))
    parcela_apos = base["custo_total"] / prazo_apos
    return {
        "estrategia": label,
        "percentual_lance": percentual,
        "lance_embutido": lance_embutido,
        "lance_proprio": lance_proprio,
        "credito_disponivel": base["credito_disponivel"],
        "parcela_apos_contemplacao": parcela_apos,
        "prazo_apos_lance": prazo_apos,
        "chance_contemplacao": chance_from_percent(percentual, group),
    }


def build_financeiro(payload: EstudoRequest, grupo: dict) -> dict:
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
    prazo_apos_total = max(1, prazo - round(percentual_lance_total * prazo))
    parcela_apos = custo_total / prazo_apos_total
    historico = summarize_history(grupo.get("historico") or {})
    base = {
        "credito_original": credito_original,
        "lance_embutido": lance_embutido,
        "credito_disponivel": credito_disponivel,
        "prazo": prazo,
        "custo_total": custo_total,
    }
    estrategias = [
        build_strategy("Lance Fixo", as_number(grupo.get("percentual_lance_fixo")), base, grupo),
        build_strategy("Conservadora", as_number(grupo.get("conservador")), base, grupo),
        build_strategy("Moderada", as_number(grupo.get("moderado")), base, grupo),
        build_strategy("Agressiva", as_number(grupo.get("agressivo")), base, grupo),
        build_strategy("Lance Total", percentual_lance_total, base, grupo),
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
        "parcela_apos_contemplacao": parcela_apos,
        "prazo_apos_contemplacao": prazo_apos_total,
        "custo_efetivo_total": custo_total,
        "seguro_garantia": grupo.get("seguro_garantia"),
        "chance_contemplacao": chance_from_percent(percentual_lance_total, grupo),
        "estrategia_recomendada": "Lance Total",
        "estrategias": estrategias,
        "historico_12_meses": historico,
    }


def create_estudo(payload: EstudoRequest, grupo: dict | None = None) -> dict:
    global _counter
    _counter += 1
    estudo_id = f"EST-{datetime.now().year}-{_counter:05d}"
    grupo_data = grupo or {}
    financeiro = build_financeiro(payload, grupo_data)
    _studies[estudo_id] = {
        "estudo_id": estudo_id,
        "cliente": payload.cliente.model_dump(),
        "grupo_id": payload.grupo_id,
        "grupo": grupo_data,
        "financeiro": financeiro,
        "estrategia": financeiro["estrategia_recomendada"],
        "status": "Concluido",
        "operador": "Joyce",
        "criado_em": datetime.now().isoformat(timespec="seconds"),
    }
    return {"estudo_id": estudo_id, "success": True}


def list_estudos() -> list[dict]:
    return sorted(_studies.values(), key=lambda item: item["criado_em"], reverse=True)


def get_estudo(estudo_id: str) -> dict | None:
    return _studies.get(estudo_id)


def delete_estudo(estudo_id: str) -> bool:
    return _studies.pop(estudo_id, None) is not None
