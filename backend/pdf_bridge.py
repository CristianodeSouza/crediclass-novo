from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
PDF_SERVICE_DIR = BASE_DIR / "pdf_service"
PDF_SERVICE_ENTRYPOINT = PDF_SERVICE_DIR / "render-study-pdf.mjs"
PDF_SERVICE_PACKAGE = PDF_SERVICE_DIR / "package.json"
PDF_SERVICE_NODE_MODULE = PDF_SERVICE_DIR / "node_modules" / "@react-pdf" / "renderer"
PDF_SERVICE_NODEENV_DIR = PDF_SERVICE_DIR / ".nodeenv"

MONTH_LABELS = {
    "01": "jan",
    "02": "fev",
    "03": "mar",
    "04": "abr",
    "05": "mai",
    "06": "jun",
    "07": "jul",
    "08": "ago",
    "09": "set",
    "10": "out",
    "11": "nov",
    "12": "dez",
}


def _local_node_candidates() -> list[Path]:
    return [
        PDF_SERVICE_NODEENV_DIR / "bin" / "node",
        PDF_SERVICE_NODEENV_DIR / "Scripts" / "node.exe",
    ]


def _node_binary() -> str | None:
    explicit = str(Path(shutil.which("node") or "")).strip()
    env_path = str(Path(__import__("os").getenv("REACT_PDF_NODE_PATH", "")).expanduser()).strip() if __import__("os").getenv("REACT_PDF_NODE_PATH") else ""
    if env_path and Path(env_path).exists():
        return env_path
    for candidate in _local_node_candidates():
        if candidate.exists():
            return str(candidate)
    if explicit:
        return explicit
    return None


def react_pdf_service_status() -> dict[str, Any]:
    node_path = _node_binary()
    return {
        "available": bool(node_path and PDF_SERVICE_ENTRYPOINT.exists() and PDF_SERVICE_NODE_MODULE.exists()),
        "node": node_path,
        "entrypoint": str(PDF_SERVICE_ENTRYPOINT),
        "package_json": PDF_SERVICE_PACKAGE.exists(),
        "dependencies_installed": PDF_SERVICE_NODE_MODULE.exists(),
    }


def _format_money(value: Any) -> str:
    amount = _to_float(value)
    if amount is None:
        return "-"
    negative = amount < 0
    amount = abs(amount)
    inteiro, decimal = f"{amount:,.2f}".split(".")
    inteiro = inteiro.replace(",", "X").replace(".", ",").replace("X", ".")
    prefix = "-R$ " if negative else "R$ "
    return f"{prefix}{inteiro},{decimal}"


def _format_percent(value: Any) -> str:
    parsed = _to_float(value)
    if parsed is None:
        return "-"
    number = parsed * 100
    inteiro = f"{number:.2f}".rstrip("0").rstrip(".").replace(".", ",")
    return f"{inteiro}%"


def _to_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    raw = str(value).strip()
    if not raw:
        return None
    had_percent = "%" in raw
    raw = raw.replace("R$", "").replace("%", "").replace(" ", "")
    if "," in raw and "." in raw:
        raw = raw.replace(".", "").replace(",", ".")
    elif "," in raw:
        raw = raw.replace(",", ".")
    try:
        parsed = float(raw)
    except (TypeError, ValueError):
        return None
    if had_percent:
        return parsed / 100
    return parsed


def _format_date(value: Any) -> str:
    if value in (None, ""):
        return "-"
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y")
    raw = str(value).strip()
    if not raw:
        return "-"
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%d/%m/%Y"):
        try:
            return datetime.strptime(raw[:19], fmt).strftime("%d/%m/%Y")
        except ValueError:
            continue
    return raw


def _month_title(value: Any) -> str:
    raw = str(value or "").strip()
    if len(raw) == 7 and raw[4] == "-":
        year, month = raw.split("-", 1)
        return f"{MONTH_LABELS.get(month, month)}/{year[-2:]}"
    return raw or "-"



def _snapshot_groups(estudo: dict[str, Any]) -> list[dict[str, Any]]:
    snapshot = estudo.get("study_snapshot") or {}
    groups = snapshot.get("groups") if isinstance(snapshot, dict) else None
    return list(groups or estudo.get("grupos_selecionados") or [])


def _scenario(group: dict[str, Any], scenario_id: str) -> dict[str, Any]:
    return next((item for item in group.get("cenarios", []) if item.get("id") == scenario_id), {})


def _quota_count(group: dict[str, Any]) -> int:
    return max(1, int(_to_float(group.get("quota_count")) or 1))

def _history_matrix(financeiro: dict[str, Any], grupo: dict[str, Any], estudo: dict[str, Any]) -> dict[str, Any]:
    selected_groups = _snapshot_groups(estudo)
    if selected_groups:
        histories = [list(group.get("historico_12_meses") or [])[-10:] for group in selected_groups]
        labels = [str(entry.get("label") or entry.get("mes") or "-") for entry in (histories[0] if histories else [])]
        if labels:
            return {"months": labels, "rows": [{"group": f"Grupo {group.get('grupo') or group.get('grupo_id') or '-'}", "administrator": str(group.get("administradora") or "-"), "cells": [{"value": _format_percent(entry.get("menor_lance")), "detail": f"Qtd {entry.get('qtd_contemplacoes', '-')}"} for entry in history]} for group, history in zip(selected_groups, histories)]}
        return {"months": ["Resumo"], "rows": [{"group": f"Grupo {group.get('grupo') or group.get('grupo_id') or '-'}", "administrator": str(group.get("administradora") or "-"), "cells": [{"value": "-", "detail": "Sem histórico"}]} for group in selected_groups]}
    historico = grupo.get("historico") or {}
    entries = sorted(historico.items())[-11:]
    if entries:
        return {"months": [_month_title(month) for month, _ in entries], "rows": [{"group": f"Grupo {grupo.get('grupo') or estudo.get('grupo_id') or '-'}", "administrator": str(grupo.get("administradora") or "-"), "cells": [{"value": _format_percent(item.get("menor_lance")), "detail": f"Qtd {item.get('qtd_contemplacoes', '-')}"} for _, item in entries]}]}
    summary = financeiro.get("historico_12_meses") or {}
    return {"months": ["Resumo"], "rows": [{"group": f"Grupo {grupo.get('grupo') or estudo.get('grupo_id') or '-'}", "administrator": str(grupo.get("administradora") or "-"), "cells": [{"value": _format_percent(summary.get("media_menor_lance")), "detail": f"Qtd {summary.get('total_contemplacoes', '-')}"}]}]}



def _selected_scenario_pairs(group: dict[str, Any]) -> list[tuple[str, str]]:
    selected = str(group.get("selected_scenario_id") or "")
    labels = {"without_embedded": "Sem embutido", "with_embedded": "Com embutido"}
    if selected in labels:
        return [(selected, labels[selected])]
    return [("without_embedded", "Sem embutido"), ("with_embedded", "Com embutido")]


def _contract_rows(estudo: dict[str, Any], grupo: dict[str, Any], financeiro: dict[str, Any]) -> list[dict[str, Any]]:
    selected_groups = _snapshot_groups(estudo)
    if selected_groups:
        rows = []
        for group in selected_groups:
            quota_count = _quota_count(group)
            for scenario_id, label in _selected_scenario_pairs(group):
                scenario = _scenario(group, scenario_id)
                rows.append({"group": f"Grupo {group.get('grupo') or group.get('grupo_id') or '-'} - {label}", "credit": _format_money((_to_float(scenario.get("credito_liquido_projetado")) or 0) * quota_count), "installment": _format_money((_to_float(scenario.get("parcela_inicial")) or 0) * quota_count), "term": str(group.get("prazo_restante") or group.get("prazo_total") or "-"), "rateTotal": _format_percent(group.get("taxa_total") or group.get("taxa_adm")), "rateYear": _format_percent(group.get("taxa_ano")), "administrator": str(group.get("administradora") or "-")})
        return rows
    cartas = financeiro.get("cartas") or []
    rows: list[dict[str, Any]] = []
    taxa_total = grupo.get("taxa_adm")
    taxa_ano = grupo.get("taxa_ano")
    prazo = grupo.get("prazo_restante") or grupo.get("prazo_total") or "-"
    administrator = str(grupo.get("administradora") or "-")
    if cartas:
        for card in cartas:
            rows.append({"group": f"Grupo {card.get('grupo') or card.get('grupo_id') or grupo.get('grupo') or estudo.get('grupo_id') or '-'}", "credit": _format_money(card.get("credito_contratado") or card.get("credito_contratado_total")), "installment": _format_money(card.get("parcela_estimada") or financeiro.get("parcela_inicial")), "term": str(card.get("prazo_restante") or card.get("prazo_total") or prazo), "rateTotal": _format_percent(taxa_total), "rateYear": _format_percent(taxa_ano), "administrator": administrator})
    return rows or [{"group": f"Grupo {grupo.get('grupo') or estudo.get('grupo_id') or '-'}", "credit": _format_money(financeiro.get("credito_original") or financeiro.get("credito")), "installment": _format_money(financeiro.get("parcela_inicial")), "term": str(prazo), "rateTotal": _format_percent(taxa_total), "rateYear": _format_percent(taxa_ano), "administrator": administrator}]



def _projection_rows(financeiro: dict[str, Any], estudo: dict[str, Any]) -> list[dict[str, Any]]:
    selected_groups = _snapshot_groups(estudo)
    if selected_groups:
        rows = []
        for group in selected_groups:
            quota_count = _quota_count(group)
            for scenario_id, label in _selected_scenario_pairs(group):
                scenario = _scenario(group, scenario_id)
                embedded = (_to_float(scenario.get("lance_embutido")) or 0) * quota_count
                rows.append({"title": f"Grupo {group.get('grupo') or group.get('grupo_id') or '-'} - {label}", "percent": "-", "totalBid": _format_money(embedded), "cardPayment": _format_money(embedded), "ownPayment": "Não consolidado", "credit": _format_money((_to_float(scenario.get("credito_liquido_projetado")) or 0) * quota_count), "installment": _format_money((_to_float(scenario.get("parcela_inicial")) or 0) * quota_count), "term": str(group.get("prazo_restante") or "-")})
        return rows
    rows = []
    credito_base = _to_float(financeiro.get("credito_original") or financeiro.get("credito")) or 0.0
    parcela_base = financeiro.get("parcela_inicial")
    prazo_base = financeiro.get("prazo_apos_contemplacao") or financeiro.get("prazo_operacional") or "-"
    labels = {"Investidor": "1. Sorteio Geral", "Conservador": "2. Lance Conservador", "Moderado": "3. Lance Moderado", "Agressivo": "4. Lance Rapido", "Super Agressivo": "5. Lance Acelerado"}
    for strategy in financeiro.get("estrategias", [])[:5]:
        percentual = strategy.get("percentual_lance")
        percentual_base = _to_float(percentual)
        total_bid = credito_base * percentual_base if percentual_base is not None else None
        rows.append({"title": labels.get(strategy.get("estrategia"), strategy.get("estrategia") or "-"), "percent": _format_percent(percentual), "totalBid": _format_money(total_bid), "cardPayment": _format_money(strategy.get("lance_embutido")), "ownPayment": _format_money(strategy.get("lance_proprio")), "credit": _format_money(strategy.get("credito_disponivel") or financeiro.get("credito")), "installment": _format_money(strategy.get("parcela_apos_contemplacao") or parcela_base), "term": str(strategy.get("prazo_apos_lance") or prazo_base or "-")})
    return rows



def _deadline_rows(estudo: dict[str, Any], grupo: dict[str, Any]) -> list[dict[str, Any]]:
    selected_groups = _snapshot_groups(estudo)
    if selected_groups:
        return [{"group": f"Grupo {item.get('grupo') or item.get('grupo_id') or '-'}", "reservationLimit": _format_date(item.get("limite_adesao")), "assemblyLimit": _format_date(item.get("limite_adesao")), "firstInstallment": _format_date(item.get("vencimento_primeira_parcela") or item.get("vencimento_parcela")), "nextAssembly": _format_date(item.get("proxima_assembleia") or item.get("primeira_assembleia")), "bidPayment": _format_date(item.get("vencimento_lance") or item.get("vencimento_parcela"))} for item in selected_groups]
    return [{"group": f"Grupo {grupo.get('grupo') or estudo.get('grupo_id') or '-'}", "reservationLimit": _format_date(grupo.get("limite_adesao")), "assemblyLimit": _format_date(grupo.get("limite_adesao")), "firstInstallment": _format_date(grupo.get("vencimento_primeira_parcela") or grupo.get("vencimento_parcela")), "nextAssembly": _format_date(grupo.get("proxima_assembleia") or grupo.get("primeira_assembleia")), "bidPayment": _format_date(grupo.get("vencimento_lance") or grupo.get("vencimento_parcela"))}]



def _operator_notes(template_campos: dict[str, Any]) -> list[str]:
    return [str(value).strip() for value in template_campos.values() if str(value or "").strip()]



def _composition_groups(estudo: dict[str, Any]) -> list[dict[str, str]]:
    groups = list(estudo.get("grupos_selecionados") or [])
    result = []
    for group in groups:
        quota_count = max(1, int(_to_float(group.get("quota_count")) or 1))
        scenarios = {str(item.get("id")): item for item in group.get("cenarios") or []}
        def scenario_row(scenario_id: str) -> dict[str, str]:
            scenario = scenarios.get(scenario_id) or {}
            scale = lambda key: (_to_float(scenario.get(key)) or 0) * quota_count
            return {"label": "Com embutido" if scenario_id == "with_embedded" else "Sem embutido", "liquidCredit": _format_money(scale("credito_liquido_projetado")), "contractedCredit": _format_money(scale("credito_contratado")), "embeddedBid": _format_money(scale("lance_embutido")), "installment": _format_money(scale("parcela_inicial")), "balance": _format_money(scale("saldo_devedor"))}
        result.append({"groupId": str(group.get("grupo") or group.get("grupo_id") or "-"), "administrator": str(group.get("administradora") or "-"), "quotas": str(quota_count), "strategy": str(group.get("best_contemplation_strategy") or "-"), "withoutEmbedded": scenario_row("without_embedded"), "withEmbedded": scenario_row("with_embedded")})
    return result


def _composition_groups(estudo: dict[str, Any]) -> list[dict[str, str]]:
    groups = list(estudo.get("grupos_selecionados") or [])
    result = []
    for group in groups:
        quota_count = max(1, int(_to_float(group.get("quota_count")) or 1))
        scenarios = {str(item.get("id")): item for item in group.get("cenarios") or []}
        def scenario_row(scenario_id: str) -> dict[str, str]:
            scenario = scenarios.get(scenario_id) or {}
            scale = lambda key: (_to_float(scenario.get(key)) or 0) * quota_count
            return {"label": "Com embutido" if scenario_id == "with_embedded" else "Sem embutido", "liquidCredit": _format_money(scale("credito_liquido_projetado")), "contractedCredit": _format_money(scale("credito_contratado")), "embeddedBid": _format_money(scale("lance_embutido")), "installment": _format_money(scale("parcela_inicial")), "balance": _format_money(scale("saldo_devedor"))}
        result.append({"groupId": str(group.get("grupo") or group.get("grupo_id") or "-"), "administrator": str(group.get("administradora") or "-"), "quotas": str(quota_count), "strategy": str(group.get("best_contemplation_strategy") or "-"), "withoutEmbedded": scenario_row("without_embedded"), "withEmbedded": scenario_row("with_embedded")})
    return result

def build_react_pdf_payload(estudo: dict[str, Any], version: str) -> dict[str, Any]:
    cliente = estudo.get("cliente") or {}
    grupo = estudo.get("grupo") or {}
    financeiro = estudo.get("financeiro") or {}
    cenario = estudo.get("cenario") or {}
    template_campos = estudo.get("template_campos") or {}
    strategy_rows = []
    for strategy in financeiro.get("estrategias", [])[:5]:
        strategy_rows.append(
            {
                "label": strategy.get("estrategia", "-"),
                "bidPercent": _format_percent(strategy.get("percentual_lance")),
                "ownBid": _format_money(strategy.get("lance_proprio")),
                "embeddedBid": _format_money(strategy.get("lance_embutido")),
                "creditAvailable": _format_money(strategy.get("credito_disponivel")),
                "operationalWindow": str(strategy.get("prazo_operacional") or "-"),
            }
        )
    alerts = [str(item) for item in financeiro.get("alertas", []) if str(item).strip()]
    recommended_admin = str(grupo.get("administradora") or "-")
    return {
        "meta": {
            "studyId": str(estudo.get("estudo_id") or "-"),
            "proposalId": str(estudo.get("proposal_id") or estudo.get("estudo_id") or "-"),
            "generatedAt": str(estudo.get("criado_em") or ""),
            "validityDays": 10,
            "version": version,
            "status": str(estudo.get("status") or "-"),
            "operator": str(estudo.get("operador") or "-"),
        },
        "client": {
            "name": str(cliente.get("nome") or "Cliente em estudo"),
            "objective": str(cliente.get("objetivo") or "Objetivo nao informado"),
            "desiredCredit": _format_money(cliente.get("credito_desejado")),
            "desiredTerm": str(cliente.get("prazo_desejado") or "-"),
            "desiredInstallment": _format_money(cliente.get("parcela_desejada")),
            "income": _format_money(cliente.get("renda_total")),
        },
        "group": {
            "administrator": recommended_admin,
            "groupId": str(grupo.get("grupo") or estudo.get("grupo_id") or "-"),
            "assetType": str(grupo.get("tipo_bem") or "-"),
            "remainingTerm": str(grupo.get("prazo_restante") or grupo.get("prazo_total") or "-"),
            "rateYear": _format_percent(grupo.get("taxa_ano")),
        },
        "financial": {
            "recommendedStrategy": str(financeiro.get("estrategia_recomendada") or cenario.get("estrategia") or "-"),
            "credit": _format_money(financeiro.get("credito")),
            "contractedCredit": _format_money(financeiro.get("credito_original")),
            "ownResources": _format_money(financeiro.get("recurso_proprio")),
            "fgts": _format_money(financeiro.get("fgts_utilizado")),
            "embeddedBid": _format_money(financeiro.get("lance_embutido")),
            "totalBid": _format_money(financeiro.get("valor_total_lance")),
            "bidPercent": _format_percent(financeiro.get("percentual_lance_total")),
            "initialInstallment": _format_money(financeiro.get("parcela_inicial")),
            "effectiveTotalCost": _format_money(financeiro.get("custo_efetivo_total")),
            "chance": str(financeiro.get("chance_contemplacao") or "-"),
            "alerts": alerts,
        },
        "sections": {
            "introNotes": [
                "O presente Estudo Financeiro foi elaborado com base nas informacoes fornecidas e nas condicoes de mercado disponiveis na data de sua emissao.",
                "O objetivo deste material e apresentar cenarios comparativos para apoiar uma decisao clara e auditavel.",
                "As informacoes apresentadas possuem carater informativo e ilustrativo e nao constituem garantia de resultado ou promessa de contemplacao.",
            ],
            "operatorNotes": _operator_notes(template_campos),
            "strategyRows": strategy_rows,
            "compositionGroups": _composition_groups(estudo),
            "historyMatrix": _history_matrix(financeiro, grupo, estudo),
            "contractRows": _contract_rows(estudo, grupo, financeiro),
            "projectionRows": _projection_rows(financeiro, estudo),
            "deadlineRows": _deadline_rows(estudo, grupo),
            "benefits": [
                "Grupos em andamento com leitura historica dos ultimos 12 meses disponivel no sistema.",
                "Comparacao entre cenarios sem embutido e com embutido, de forma separada.",
                "Possibilidade de utilizar o lance embutido quando informado na base do grupo.",
                "Leitura do perfil de contemplacao por estrategia para apoiar a decisao.",
                "Agenda de contratacao e assembleias vinculada a administradora quando disponivel.",
            ],
            "specialists": [
                {
                    "label": "Gestao da Contemplacao",
                    "text": "Consultoria de lances para estrategias assertivas, apoio operacional em oferta e acompanhamento do resultado da assembleia.",
                },
                {
                    "label": "Gestao da Utilizacao do Credito",
                    "text": "Tramites com administradora, vendedores, prefeitura, cartorio de imoveis, certidoes e contratos da operacao.",
                },
            ],
            "selectionCriteria": [
                "1 - Grupos antigos: mais participantes ja contemplados, menor concorrencia nos lances.",
                "2 - Historico de lance: concorrencia de lances abaixo da media de mercado para grupos com prazo similar.",
                "3 - Estabilidade nos lances: menor volatilidade nos ultimos 11 meses, trazendo maior previsibilidade.",
                "4 - Saude financeira: grupos saudaveis, com contemplacoes recorrentes nos ultimos ciclos.",
                "5 - Lance embutido: permite utilizar parte da carta de credito para pagamento do lance ofertado quando aplicavel.",
            ],
            "howItWorks": [
                "O consorcio e uma modalidade de credito planejado que permite a aquisicao de imoveis e outros bens por meio da formacao de um fundo comum entre participantes.",
                "Mensalmente, sao realizadas contemplacoes por sorteio e lance, possibilitando o acesso a carta de credito com flexibilidade para diferentes objetivos patrimoniais.",
            ],
            "monthlyContemplations": [
                "1) Sorteio: participam do sorteio todos os consorciados que estao com suas mensalidades em dia.",
                "2) Lance livre: modalidade que permite ofertar qualquer valor de lance, contemplando as cartas com as maiores ofertas mensais.",
            ],
            "creditUses": [
                "Comprar imoveis residenciais, comerciais, novos, usados, na planta, terrenos, casa de praia ou de campo.",
                "Usar para construcao e reforma.",
                "Quitacao de financiamento imobiliario.",
                "Deixar aplicada obtendo rendimentos e retirar corrigida ao fim do grupo.",
            ],
            "considerations": [
                "Os cenarios, projecoes e simulacoes apresentados foram elaborados com base nas informacoes fornecidas pelo cliente e nas condicoes observadas na data de emissao.",
                "Os resultados demonstrados possuem carater exclusivamente informativo e ilustrativo, podendo sofrer alteracoes por fatores economicos, financeiros, regulatórios, operacionais ou de mercado.",
                "A Crediclass nao garante rentabilidade de investimentos, indices de correcao futuros, percentuais de contemplacao, prazos de contemplacao ou quaisquer resultados futuros.",
                "A decisao pela contratacao de qualquer produto financeiro ou estrategia patrimonial e de responsabilidade exclusiva do cliente.",
            ],
        },
    }


def render_react_study_pdf(estudo: dict[str, Any], version: str) -> bytes:
    status = react_pdf_service_status()
    if not status["available"]:
        raise RuntimeError("React-pdf service unavailable")
    payload = build_react_pdf_payload(estudo, version)
    result = subprocess.run(
        [status["node"], str(PDF_SERVICE_ENTRYPOINT)],
        input=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip() or "Unknown React-pdf renderer error"
        raise RuntimeError(detail)
    return result.stdout
