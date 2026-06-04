from __future__ import annotations

from datetime import date
import math
import unicodedata
from typing import Any

from .models import ViabilidadeRequest


PROFILE_BY_MONTHS = [
    (3, "Super Agressivo", "super_agressivo"),
    (6, "Agressivo", "agressivo"),
    (12, "Moderado", "moderado"),
    (24, "Conservador", "conservador"),
    (math.inf, "Investidor", "investidor"),
]


def normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.lower().strip()


def classify_profile(prazo_desejado: int) -> tuple[str, str]:
    for max_months, label, field in PROFILE_BY_MONTHS:
        if prazo_desejado <= max_months:
            return label, field
    return "Investidor", "investidor"


def compatible_tipo_bem(objetivo: str, tipo_bem: str, requested_tipo_bem: str) -> bool:
    wanted = normalize_text(requested_tipo_bem or "Imovel")
    group_type = normalize_text(tipo_bem)
    objective = normalize_text(objetivo)

    if "imovel" in wanted or "imovel" in objective or "financiamento" in objective or "construcao" in objective:
        return "imovel" in group_type
    if "auto" in wanted or "veiculo" in wanted:
        return "auto" in group_type or "veiculo" in group_type
    return True


def latest_history_values(historico: dict[str, Any]) -> tuple[float | None, int]:
    menores: list[float] = []
    contemplacoes = 0
    for item in historico.values():
        menor = item.get("menor_lance") if isinstance(item, dict) else getattr(item, "menor_lance", None)
        qtd = item.get("qtd_contemplacoes") if isinstance(item, dict) else getattr(item, "qtd_contemplacoes", None)
        if menor is not None:
            menores.append(float(menor))
        if qtd is not None:
            contemplacoes += int(qtd)
    if not menores:
        return None, contemplacoes
    return sum(menores) / len(menores), contemplacoes


def bounded_score(value: float) -> float:
    return max(0.0, min(100.0, value))


def score_ratio(actual: float, target: float) -> float:
    if target <= 0:
        return 0.0
    return bounded_score(100 - abs(actual - target) / target * 100)


def group_selo(score: float) -> str:
    if score >= 90:
        return "Excelente"
    if score >= 80:
        return "Muito Bom"
    if score >= 70:
        return "Bom"
    return "Analise"


def analyze_viabilidade(payload: ViabilidadeRequest, groups: list[dict[str, Any]]) -> dict[str, Any]:
    profile_label, profile_field = classify_profile(payload.prazo_desejado)
    fgts_total = payload.fgts
    lance_total_disponivel = payload.lance_proprio + fgts_total
    results: list[dict[str, Any]] = []

    for group in groups:
        credito_maximo = group.get("credito_maximo") or 0
        prazo_restante = group.get("prazo_restante")
        if prazo_restante is None:
            prazo_restante = group.get("prazo_total") or 0
        status = normalize_text(str(group.get("status") or ""))

        if credito_maximo < payload.credito_desejado:
            continue
        if status != "ativo":
            continue
        if prazo_restante <= 0:
            continue
        if not compatible_tipo_bem(payload.objetivo, str(group.get("tipo_bem") or ""), payload.tipo_bem):
            continue

        percentual_lance_embutido = group.get("percentual_lance_embutido") or 0
        if percentual_lance_embutido >= 1:
            percentual_lance_embutido = 0

        credito_contratado = payload.credito_desejado / (1 - percentual_lance_embutido)
        lance_embutido = credito_contratado * percentual_lance_embutido
        lance_total = lance_embutido + payload.lance_proprio + fgts_total
        percentual_lance = lance_total / credito_contratado if credito_contratado else 0
        credito_disponivel = credito_contratado - lance_embutido

        taxa_adm = group.get("taxa_adm") or 0
        fundo_reserva = group.get("fundo_reserva") or 0
        prazo_total = group.get("prazo_total") or prazo_restante
        parcela_estimada = (credito_contratado + credito_contratado * taxa_adm + credito_contratado * fundo_reserva) / prazo_total

        lance_referencia = group.get(profile_field) or group.get("percentual_lance_fixo") or 0
        menor_lance_historico, qtd_contemplacoes = latest_history_values(group.get("historico") or {})

        credito_score = 100 if credito_disponivel >= payload.credito_desejado else score_ratio(credito_disponivel, payload.credito_desejado)
        parcela_score = 100 if parcela_estimada <= payload.parcela_desejada else score_ratio(payload.parcela_desejada, parcela_estimada)
        lance_score = 100 if not lance_referencia or percentual_lance >= lance_referencia else score_ratio(percentual_lance, lance_referencia)
        prazo_score = 100 if prazo_restante >= payload.prazo_desejado else score_ratio(prazo_restante, payload.prazo_desejado)
        historico_score = 50
        if menor_lance_historico is not None:
            historico_score = (70 if percentual_lance >= menor_lance_historico else score_ratio(percentual_lance, menor_lance_historico) * 0.7)
            historico_score += min(30, qtd_contemplacoes * 2)

        afinidade_score = (
            credito_score * 25
            + parcela_score * 25
            + lance_score * 25
            + prazo_score * 15
            + bounded_score(historico_score) * 10
        ) / 100

        motivos = []
        motivos.append("Credito compativel" if credito_disponivel >= payload.credito_desejado else "Credito abaixo do desejado")
        motivos.append("Parcela dentro do limite" if parcela_estimada <= payload.parcela_desejada else "Parcela acima do limite")
        motivos.append("Lance compativel com o perfil" if not lance_referencia or percentual_lance >= lance_referencia else "Lance abaixo do perfil")
        motivos.append("Prazo compativel" if prazo_restante >= payload.prazo_desejado else "Prazo abaixo do desejado")

        results.append({
            "ranking": 0,
            "grupo_id": group["grupo_id"],
            "administradora": group.get("administradora") or "",
            "grupo": group.get("grupo") or "",
            "tipo_bem": group.get("tipo_bem") or "",
            "credito": round(credito_disponivel, 2),
            "parcela_estimada": round(parcela_estimada, 2),
            "lance_sugerido_percentual": round(percentual_lance, 4),
            "lance_sugerido_valor": round(lance_total, 2),
            "prazo": int(prazo_restante),
            "afinidade": round(afinidade_score / 100, 4),
            "selo": group_selo(afinidade_score),
            "motivos": motivos,
        })

    results.sort(key=lambda item: item["afinidade"], reverse=True)
    melhores = results[:10]
    for index, item in enumerate(melhores, start=1):
        item["ranking"] = index

    renda_comporta = any(item["parcela_estimada"] * 3 <= payload.renda_total for item in melhores) if melhores else False
    parcela_comporta = any(item["parcela_estimada"] <= payload.parcela_desejada for item in melhores)
    prazo_compativel = any(item["prazo"] >= payload.prazo_desejado for item in melhores)
    lance_suficiente = any(item["lance_sugerido_valor"] <= lance_total_disponivel + (payload.credito_desejado * 0.5) for item in melhores)
    cenario_viavel = bool(melhores) and renda_comporta and parcela_comporta and prazo_compativel

    return {
        "total_grupos_encontrados": len(results),
        "perfil": profile_label,
        "fgts_total": round(fgts_total, 2),
        "lance_total_disponivel": round(lance_total_disponivel, 2),
        "renda_total": round(payload.renda_total, 2),
        "cenario": "Viavel" if cenario_viavel else "Inviavel",
        "checklist": {
            "idade_compativel": is_age_compatible(payload.data_nascimento),
            "renda_comporta_parcela": renda_comporta,
            "lance_proprio_suficiente": lance_suficiente,
            "fgts_disponivel": fgts_total > 0,
            "prazo_compativel": prazo_compativel,
            "cenario_viavel": cenario_viavel,
        },
        "melhores_grupos": melhores,
    }


def is_age_compatible(date_text: str) -> bool:
    if not date_text:
        return True
    try:
        born = date.fromisoformat(date_text)
    except ValueError:
        return False
    today = date.today()
    age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    return 18 <= age <= 80
