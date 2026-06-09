from __future__ import annotations

from datetime import date
import re
import unicodedata
from typing import Any

from .lance_reference import (
    calculate_lance_references,
    classify_profile as classify_lance_profile,
    reference_in_profile_range,
)
from .models import ViabilidadeRequest


def normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.lower().strip()


def classify_profile(prazo_desejado: int) -> tuple[str, str]:
    label, field, _ = classify_lance_profile(prazo_desejado)
    return label, field


def compatible_tipo_bem(objetivo: str, tipo_bem: str, requested_tipo_bem: str) -> bool:
    wanted = normalize_text(requested_tipo_bem)
    group_type = normalize_text(tipo_bem)
    objective = normalize_text(objetivo)

    if not wanted:
        wanted = "imovel" if any(term in objective for term in ("imovel", "financiamento", "construcao")) else objective
    if "imovel" in wanted:
        return "imovel" in group_type
    if "auto" in wanted or "veiculo" in wanted:
        return "auto" in group_type or "veiculo" in group_type
    if "servico" in wanted:
        return "servico" in group_type
    if "pesado" in wanted:
        return "pesado" in group_type
    if "outro" in wanted:
        return "outro" in group_type
    return wanted == group_type


def history_last_12_months(historico: dict[str, Any]) -> dict[str, float | int | None]:
    valid_items = [
        (month, item)
        for month, item in historico.items()
        if re.fullmatch(r"\d{4}-\d{2}", str(month))
    ]
    recent_items = sorted(valid_items, key=lambda entry: entry[0], reverse=True)[:12]
    maiores: list[float] = []
    menores: list[float] = []
    quantidades: list[int] = []
    for _, item in recent_items:
        get_value = item.get if isinstance(item, dict) else lambda key: getattr(item, key, None)
        maior = get_value("maior_lance")
        menor = get_value("menor_lance")
        qtd = get_value("qtd_contemplacoes")
        if maior is not None:
            maiores.append(float(maior))
        if menor is not None:
            menores.append(float(menor))
        if qtd is not None:
            quantidades.append(int(qtd))

    return {
        "media_maior_lance": round(sum(maiores) / len(maiores), 6) if maiores else None,
        "media_menor_lance": round(sum(menores) / len(menores), 6) if menores else None,
        "media_qtd_contemplacoes": round(sum(quantidades) / len(quantidades), 2) if quantidades else None,
        "total_contemplacoes": sum(quantidades),
    }


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
    if score >= 60:
        return "Regular"
    return "Baixa Compatibilidade"


def calculate_age(date_text: str) -> int | None:
    if not date_text:
        return None
    try:
        born = date.fromisoformat(date_text)
    except ValueError:
        return None
    today = date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


def calculate_age_at(date_text: str, reference_date_text: str) -> int | None:
    if not date_text or not reference_date_text:
        return None
    try:
        born = date.fromisoformat(date_text)
        reference_date = date.fromisoformat(reference_date_text)
    except ValueError:
        return None
    return reference_date.year - born.year - ((reference_date.month, reference_date.day) < (born.month, born.day))


def group_age_validation(group: dict[str, Any], payload: ViabilidadeRequest, titular_age: int | None, spouse_age: int | None) -> tuple[bool, str]:
    maximum_age = group.get("idade_maxima")
    informed_ages = [age for age in (titular_age, spouse_age) if age is not None]
    if not informed_ages:
        return False, "idade_nao_validada"
    if any(age < 18 for age in informed_ages):
        return False, "idade_minima_incompativel"
    if maximum_age is None:
        return True, "idade_nao_validada"
    data_termino = str(group.get("data_termino") or "")
    ages_at_end = [
        age
        for age in (
            calculate_age_at(payload.data_nascimento, data_termino),
            calculate_age_at(payload.data_nascimento_conjuge, data_termino),
        )
        if age is not None
    ]
    if not ages_at_end:
        return True, "idade_termino_nao_validada"
    if any(age > int(maximum_age) for age in ages_at_end):
        return False, "idade_termino_incompativel"
    return True, ""


def analyze_viabilidade(payload: ViabilidadeRequest, groups: list[dict[str, Any]], modo_preliminar: bool = False) -> dict[str, Any]:
    profile_label, profile_field, operational_range = classify_lance_profile(payload.prazo_desejado)
    fgts_total = payload.fgts
    titular_age = calculate_age(payload.data_nascimento)
    spouse_age = calculate_age(payload.data_nascimento_conjuge)
    age_informed = titular_age is not None or spouse_age is not None
    results: list[dict[str, Any]] = []

    for group in groups:
        credito_minimo = group.get("credito_minimo") or 0
        credito_maximo = group.get("credito_maximo") or 0
        prazo_restante = group.get("prazo_restante")
        if prazo_restante is None:
            prazo_restante = group.get("prazo_total") or 0
        status = normalize_text(str(group.get("status") or ""))

        if status != "ativo":
            continue
        if prazo_restante <= 0:
            continue
        if not compatible_tipo_bem(payload.objetivo, str(group.get("tipo_bem") or ""), payload.tipo_bem):
            continue

        fgts_permitido = bool(group.get("fgts"))
        fgts_utilizado = fgts_total if fgts_permitido else 0
        lance_embutido_permitido = bool(group.get("lance_embutido"))
        percentual_lance_embutido = (group.get("percentual_lance_embutido") or 0) if lance_embutido_permitido else 0
        if percentual_lance_embutido < 0 or percentual_lance_embutido >= 1:
            percentual_lance_embutido = 0

        credito_contratado = payload.credito_desejado / (1 - percentual_lance_embutido)
        lance_embutido = credito_contratado * percentual_lance_embutido
        lance_total_formula = lance_embutido + payload.lance_proprio
        lance_total = lance_total_formula
        percentual_lance = lance_total_formula / credito_contratado if credito_contratado else 0
        credito_disponivel = credito_contratado - lance_embutido

        taxa_adm = group.get("taxa_adm") or 0
        fundo_reserva = group.get("fundo_reserva") or 0
        prazo_total = group.get("prazo_total") or prazo_restante
        taxa_administrativa_valor = credito_contratado * taxa_adm
        fundo_reserva_valor = credito_contratado * fundo_reserva
        parcela_estimada = (
            credito_contratado
            + taxa_administrativa_valor
            + fundo_reserva_valor
        ) / prazo_total
        prazo_minimo = (
            credito_contratado
            + taxa_administrativa_valor
            + fundo_reserva_valor
            - lance_total_formula
        ) / payload.parcela_desejada

        historico = group.get("historico") or {}
        historico_12m = history_last_12_months(historico)
        lance_references = calculate_lance_references(
            historico,
            group.get("percentual_lance_fixo"),
        )
        lance_referencia = lance_references[profile_field]
        historico_disponivel = lance_referencia is not None
        lance_na_faixa_perfil = reference_in_profile_range(profile_field, lance_referencia)

        credito_score = 0 if credito_contratado < credito_minimo or credito_contratado > credito_maximo else 100
        parcela_score = 100 if parcela_estimada <= payload.parcela_desejada else score_ratio(payload.parcela_desejada, parcela_estimada)
        lance_score = 0 if not historico_disponivel or not lance_na_faixa_perfil else (100 if percentual_lance >= float(lance_referencia) else score_ratio(percentual_lance, float(lance_referencia)))
        prazo_score = 100 if prazo_restante >= prazo_minimo else score_ratio(prazo_restante, prazo_minimo)
        historico_score = 0
        if lance_referencia is not None and lance_na_faixa_perfil:
            historico_score = 70 if percentual_lance >= float(lance_referencia) else score_ratio(percentual_lance, float(lance_referencia)) * 0.7
            historico_score += min(30, int(historico_12m["total_contemplacoes"]) * 2)

        afinidade_score = (
            credito_score * 25
            + parcela_score * 25
            + lance_score * 25
            + prazo_score * 15
            + bounded_score(historico_score) * 10
        ) / 100

        idade_compativel, idade_alerta = group_age_validation(group, payload, titular_age, spouse_age)
        renda_compativel = parcela_estimada * 3 <= payload.renda_total
        parcela_compativel = parcela_estimada <= payload.parcela_desejada
        lance_compativel = historico_disponivel and lance_na_faixa_perfil and percentual_lance >= float(lance_referencia)
        prazo_compativel = prazo_restante >= prazo_minimo
        credito_compativel = credito_minimo <= credito_contratado <= credito_maximo
        permissoes_compativeis = (fgts_total <= 0 or fgts_permitido) and (
            percentual_lance_embutido <= 0 or lance_embutido_permitido
        )

        alertas = []
        if modo_preliminar:
            alertas.append("regras_administradoras_pendentes_analise_humana")
        if not historico_disponivel:
            alertas.append("historico_lance_insuficiente")
        elif not lance_na_faixa_perfil:
            alertas.append("lance_historico_fora_do_perfil")
        if idade_alerta:
            alertas.append(idade_alerta)
        if fgts_total > 0 and not fgts_permitido:
            alertas.append("fgts_nao_permitido")
        if group.get("percentual_lance_embutido") and not lance_embutido_permitido:
            alertas.append("lance_embutido_nao_permitido")

        if modo_preliminar:
            aprovado = credito_compativel
        else:
            aprovado = all((
                credito_compativel,
                renda_compativel,
                parcela_compativel,
                lance_compativel,
                prazo_compativel,
                permissoes_compativeis,
                idade_compativel if age_informed else True,
            ))

        motivos = []
        motivos.append("Credito contratado compativel" if credito_compativel else "Credito contratado fora da faixa do grupo")
        motivos.append("Parcela dentro do limite" if parcela_estimada <= payload.parcela_desejada else "Parcela acima do limite")
        motivos.append("Lance compativel com o perfil" if lance_compativel else "Lance abaixo do perfil, fora da faixa ou sem historico")
        motivos.append("Prazo compativel" if prazo_restante >= prazo_minimo else "Prazo restante abaixo do prazo minimo calculado")
        if modo_preliminar:
            motivos.append("Analise preliminar: regras da administradora pendentes de revisao humana")

        results.append({
            "ranking": 0,
            "grupo_aprovado": aprovado,
            "grupo_id": group["grupo_id"],
            "administradora": group.get("administradora") or "",
            "grupo": group.get("grupo") or "",
            "tipo_bem": group.get("tipo_bem") or "",
            "credito_minimo": round(credito_minimo, 2),
            "credito_maximo": round(credito_maximo, 2),
            "credito": round(credito_disponivel, 2),
            "credito_desejado": round(payload.credito_desejado, 2),
            "credito_contratado": round(credito_contratado, 2),
            "credito_disponivel": round(credito_disponivel, 2),
            "lance_embutido_utilizado": round(lance_embutido, 2),
            "fgts_utilizado": round(fgts_utilizado, 2),
            "lance_proprio_utilizado": round(payload.lance_proprio, 2),
            "lance_total": round(lance_total, 2),
            "percentual_lance": round(percentual_lance, 4),
            "taxa_administrativa_valor": round(taxa_administrativa_valor, 2),
            "fundo_reserva_valor": round(fundo_reserva_valor, 2),
            "parcela_estimada": round(parcela_estimada, 2),
            "lance_sugerido_percentual": (
                round(float(lance_referencia), 6)
                if lance_referencia is not None
                else None
            ),
            "lance_sugerido_valor": (
                round(credito_contratado * float(lance_referencia), 2)
                if lance_referencia is not None
                else None
            ),
            "lance_referencia_percentual": (
                round(float(lance_referencia), 6)
                if lance_referencia is not None
                else None
            ),
            "perfil_prazo_operacional": operational_range,
            "prazo_minimo": round(max(0, prazo_minimo), 2),
            "taxa_adm": round(taxa_adm, 6),
            "fundo_reserva": round(fundo_reserva, 6),
            "prazo": int(prazo_restante),
            "afinidade": round(afinidade_score / 100, 4),
            "selo": group_selo(afinidade_score),
            "historico_12m": historico_12m,
            "alertas": alertas,
            "motivos": motivos,
            "_aprovado": aprovado,
            "_checks": {
                "idade_compativel": idade_compativel,
                "renda_compativel": renda_compativel,
                "parcela_compativel": parcela_compativel,
                "lance_compativel": lance_compativel,
                "fgts_permitido": fgts_total <= 0 or fgts_permitido,
                "lance_embutido_permitido": percentual_lance_embutido <= 0 or lance_embutido_permitido,
                "prazo_compativel": prazo_compativel,
                "tipo_bem_compativel": True,
            },
        })

    results.sort(key=lambda item: item["afinidade"], reverse=True)
    approved_groups = [item for item in results if item["_aprovado"]]
    melhores = approved_groups[:10]
    for index, item in enumerate(melhores, start=1):
        item["ranking"] = index

    cenario_viavel = bool(approved_groups)
    checklist_keys = (
        "idade_compativel",
        "renda_compativel",
        "parcela_compativel",
        "lance_compativel",
        "fgts_permitido",
        "lance_embutido_permitido",
        "prazo_compativel",
        "tipo_bem_compativel",
    )
    representative_group = approved_groups[0] if approved_groups else (results[0] if results else None)
    checklist = {
        key: representative_group["_checks"][key] if representative_group else False
        for key in checklist_keys
    }
    if not age_informed:
        checklist["idade_compativel"] = False
    checklist["cenario_viavel"] = cenario_viavel
    motivos_reprovacao = [
        key
        for key in checklist_keys
        if not checklist[key] and not (key == "idade_compativel" and not age_informed)
    ]
    if not results:
        motivos_reprovacao.append("nenhum_grupo_compativel_com_filtros_iniciais")
    public_results = []
    for item in melhores:
        public_results.append({key: value for key, value in item.items() if not key.startswith("_")})

    return {
        "cenario_viavel": cenario_viavel,
        "total_grupos_encontrados": len(results),
        "total_grupos_analisados": len(groups),
        "total_grupos_compativeis": len(approved_groups),
        "perfil": profile_label,
        "perfil_prazo_operacional": operational_range,
        "fgts_total": round(fgts_total, 2),
        "lance_total_disponivel": round(payload.lance_proprio + fgts_total, 2),
        "renda_total": round(payload.renda_total, 2),
        "estado_bem": payload.estado_bem,
        "idade_titular": titular_age,
        "idade_conjuge": spouse_age,
        "idade_validada": age_informed,
        "idade_alerta": "" if age_informed else "idade_nao_validada",
        "cenario": "Viavel" if cenario_viavel else "Inviavel",
        "motivos_reprovacao": motivos_reprovacao,
        "checklist": checklist,
        "melhores_grupos": public_results,
    }
