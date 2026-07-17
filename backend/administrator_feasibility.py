from __future__ import annotations

import math
from typing import Any

from .administrator_rules import AdministratorRule, get_rule_for_administradora
from .models import ViabilidadeRequest
from .viabilidade import calculate_age


def client_fgts_total(payload: ViabilidadeRequest) -> float:
    if payload.fgts_titular is not None or payload.fgts_conjuge is not None:
        return float(payload.fgts_titular or 0) + float(payload.fgts_conjuge or 0)
    return float(payload.fgts or 0)


def client_renda_total(payload: ViabilidadeRequest) -> float:
    if payload.renda_titular is not None or payload.renda_conjuge is not None:
        return float(payload.renda_titular or 0) + float(payload.renda_conjuge or 0)
    return float(payload.renda_total or 0)


def client_contracting_type(payload: ViabilidadeRequest) -> str:
    return str(payload.tipo_contratacao or "").strip().lower()


def client_parcela_limite(payload: ViabilidadeRequest) -> float:
    return float(payload.parcela_limite or payload.parcela_desejada)


def client_parcela_ideal(payload: ViabilidadeRequest) -> float:
    return float(payload.parcela_ideal or payload.parcela_desejada)


def client_lance_maximo_disponivel(payload: ViabilidadeRequest, fgts_permitido: bool = True) -> float:
    fgts_total = client_fgts_total(payload) if fgts_permitido else 0.0
    return float(payload.lance_proprio or 0) + fgts_total


def calculate_administrator_feasibility(payload: ViabilidadeRequest, rule: AdministratorRule) -> dict[str, Any]:
    status_operacional = str(rule.status_operacional or "Ativo").strip()
    produto_ativo = status_operacional.upper() != "INATIVO"
    percentual_lance_embutido = max(0.0, min(float(rule.percentual_lance_embutido or 0), 0.95))
    if not payload.considerar_lance_embutido:
        percentual_lance_embutido = 0.0
    credito_a_contratar = payload.credito_desejado / (1 - percentual_lance_embutido)
    lance_embutido_valor = credito_a_contratar * percentual_lance_embutido
    fgts_total = client_fgts_total(payload)
    fgts_utilizado = fgts_total if rule.aceita_fgts else 0.0
    lance_proprio = client_lance_maximo_disponivel(payload, rule.aceita_fgts)
    lance_total = lance_embutido_valor + lance_proprio
    lance_maximo_percentual = lance_total / credito_a_contratar if credito_a_contratar else 0.0
    taxa_adm_valor = credito_a_contratar * float(rule.taxa_adm or 0)
    # Com embutido, o fundo de reserva usa o credito liquido desejado.
    fundo_reserva_base = payload.credito_desejado if percentual_lance_embutido > 0 else credito_a_contratar
    fundo_reserva_valor = fundo_reserva_base * float(rule.fundo_reserva or 0)
    parcela_limite = client_parcela_limite(payload)
    parcela_ideal = client_parcela_ideal(payload)
    prazo_minimo = (
        (credito_a_contratar + taxa_adm_valor + fundo_reserva_valor - lance_total) / parcela_limite
        if parcela_limite > 0
        else math.inf
    )
    prazo_minimo = max(0.0, prazo_minimo)

    titular_age = calculate_age(payload.data_nascimento)
    spouse_age = calculate_age(payload.data_nascimento_conjuge)
    informed_ages = [age for age in (titular_age, spouse_age) if age is not None]
    idade_compativel = bool(informed_ages)
    if informed_ages and rule.idade_maxima is not None:
        idade_compativel = all(age <= rule.idade_maxima for age in informed_ages)

    renda_total = client_renda_total(payload)
    parcela_compativel = math.isfinite(prazo_minimo) and parcela_limite > 0
    renda_compativel = parcela_ideal * 3 <= renda_total
    limite_compativel = (
        True
        if rule.limite_sem_comprovacao_renda is None
        else credito_a_contratar <= float(rule.limite_sem_comprovacao_renda)
    )
    tipo_contratacao = client_contracting_type(payload)
    is_pj = tipo_contratacao == "pj"
    cenarios_pj_disponiveis: list[str] = []
    if is_pj:
        if rule.aceita_pj:
            cenarios_pj_disponiveis.append("PJ_PURA")
        if rule.permite_composicao_pj_socios:
            cenarios_pj_disponiveis.append("PJ_SOCIOS")
        if rule.permite_cpf_socio:
            cenarios_pj_disponiveis.append("CPF_SOCIOS")

    tipo_contratacao_compativel = not is_pj or bool(cenarios_pj_disponiveis)
    fgts_permitido = fgts_total <= 0 or rule.aceita_fgts
    lance_embutido_permitido = percentual_lance_embutido > 0

    alertas: list[str] = []
    motivos_reprovacao: list[str] = []
    restricoes: list[str] = []
    if not produto_ativo:
        alertas.append("produto_inativo")
        motivos_reprovacao.append("Produto da administradora marcado como inativo.")
    if not tipo_contratacao_compativel:
        motivos_reprovacao.append("Administradora nao aceita PJ, composicao com socios ou analise por CPF dos socios.")
    if not informed_ages:
        alertas.append("idade_nao_validada")
    elif not idade_compativel:
        alertas.append("idade_incompativel")
        motivos_reprovacao.append("Idade do participante maior que o limite permitido pela administradora.")
    if not renda_compativel:
        alertas.append("renda_insuficiente")
        motivos_reprovacao.append("Renda insuficiente para a parcela desejada.")
    if not parcela_compativel:
        alertas.append("parcela_limite_invalida")
        motivos_reprovacao.append("Parcela limite invalida para calcular a elegibilidade.")
    if not limite_compativel:
        alertas.append("credito_acima_limite_sem_comprovacao")
        motivos_reprovacao.append("Credito desejado acima do limite sem comprovacao da administradora.")
    if fgts_total > 0 and not rule.aceita_fgts:
        alertas.append("fgts_nao_permitido")
        restricoes.append("FGTS nao sera considerado no calculo do lance.")
    if not lance_embutido_permitido:
        alertas.append("lance_embutido_nao_permitido")
        restricoes.append("Calculadora devera considerar apenas cenario sem embutido.")
    if rule.seguro_obrigatorio:
        alertas.append("seguro_obrigatorio")

    elegivel = all((
        produto_ativo,
        tipo_contratacao_compativel,
        idade_compativel,
        renda_compativel,
        parcela_compativel,
        limite_compativel,
    ))
    status = "REPROVADA" if not elegivel else ("APROVADA_COM_RESTRICOES" if restricoes or alertas else "APROVADA")

    return {
        "administradora": rule.administradora,
        "status": status,
        "status_operacional": status_operacional,
        "produto_ativo": produto_ativo,
        "data_cadastro_produto": rule.data_cadastro_produto,
        "responsavel_produto": rule.responsavel_produto,
        "aceita_adesao_clientes_texto": rule.aceita_adesao_clientes_texto,
        "limite_sem_comprovacao_renda_texto": rule.limite_sem_comprovacao_renda_texto,
        "seguro_obrigatorio": rule.seguro_obrigatorio,
        "idade_maxima": rule.idade_maxima,
        "limite_sem_comprovacao_renda": rule.limite_sem_comprovacao_renda,
        "percentual_lance_embutido": round(percentual_lance_embutido, 6),
        "tipo_lance_embutido": rule.tipo_lance_embutido,
        "credito_a_contratar": round(credito_a_contratar, 2),
        "lance_embutido_valor": round(lance_embutido_valor, 2),
        "lance_proprio": round(lance_proprio, 2),
        "fgts_utilizado": round(fgts_utilizado, 2),
        "lance_total": round(lance_total, 2),
        "lance_maximo_percentual": round(lance_maximo_percentual, 6),
        "taxa_adm": round(float(rule.taxa_adm or 0), 6),
        "fundo_reserva": round(float(rule.fundo_reserva or 0), 6),
        "prazo_minimo": round(prazo_minimo, 2),
        "renda_compativel": renda_compativel,
        "idade_compativel": idade_compativel,
        "parcela_compativel": parcela_compativel,
        "limite_sem_comprovacao_compativel": limite_compativel,
        "fgts_permitido": fgts_permitido,
        "lance_embutido_permitido": lance_embutido_permitido,
        "elegivel": elegivel,
        "alertas": alertas,
        "motivos_reprovacao": motivos_reprovacao,
        "restricoes": restricoes,
        "cenarios_pj_disponiveis": cenarios_pj_disponiveis if is_pj else [],
        "regras_aplicaveis": {
            "status_operacional": status_operacional,
            "produto_ativo": produto_ativo,
            "data_cadastro_produto": rule.data_cadastro_produto,
            "responsavel_produto": rule.responsavel_produto,
            "aceita_adesao_clientes_texto": rule.aceita_adesao_clientes_texto,
            "aceita_fgts": rule.aceita_fgts,
            "permite_lance_embutido": lance_embutido_permitido,
            "percentual_lance_embutido": round(percentual_lance_embutido if lance_embutido_permitido else 0.0, 6),
            "base_calculo_embutido": rule.tipo_lance_embutido,
            "seguro_obrigatorio": rule.seguro_obrigatorio,
            "idade_maxima": rule.idade_maxima,
            "limite_sem_comprovacao_renda": rule.limite_sem_comprovacao_renda,
            "aceita_pj": rule.aceita_pj,
            "permite_pj_socios": rule.permite_composicao_pj_socios,
            "permite_cpf_socios": rule.permite_cpf_socio,
        },
    }


def administrator_rule_has_operational_data(rule: AdministratorRule) -> bool:
    """Retorna true somente quando a regra tem dados reais para bloquear administradora."""
    return any((
        bool(str(rule.status_operacional or "").strip() and str(rule.status_operacional).strip().upper() != "ATIVO"),
        bool(str(rule.data_cadastro_produto or "").strip()),
        bool(str(rule.responsavel_produto or "").strip()),
        bool(str(rule.aceita_adesao_clientes_texto or "").strip()),
        bool(str(rule.limite_sem_comprovacao_renda_texto or "").strip()),
        float(rule.percentual_lance_embutido or 0) > 0,
        float(rule.taxa_adm or 0) > 0,
        float(rule.fundo_reserva or 0) > 0,
        rule.idade_maxima is not None,
        rule.aceita_fgts,
        rule.aceita_saida_fiscal,
        bool(str(rule.possui_negociacao_taxa or "").strip() not in {"", "Nao", "Não"}),
    ))


def analyze_administradoras(payload: ViabilidadeRequest, administradoras: list[str], config_rules: list[dict] | None = None) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    seen: set[str] = set()
    for administradora in administradoras:
        rule = get_rule_for_administradora(administradora, config_rules)
        if not rule:
            continue
        if not administrator_rule_has_operational_data(rule):
            continue
        key = rule.administradora.upper()
        if key in seen:
            continue
        seen.add(key)
        results.append(calculate_administrator_feasibility(payload, rule))

    results.sort(key=lambda item: (
        not item["elegivel"],
        item["credito_a_contratar"],
        item["prazo_minimo"],
        -item["lance_maximo_percentual"],
    ))
    return results
