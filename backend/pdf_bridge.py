from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
PDF_SERVICE_DIR = BASE_DIR / "pdf_service"
PDF_SERVICE_ENTRYPOINT = PDF_SERVICE_DIR / "render-study-pdf.mjs"
PDF_SERVICE_PACKAGE = PDF_SERVICE_DIR / "package.json"
PDF_SERVICE_NODE_MODULE = PDF_SERVICE_DIR / "node_modules" / "@react-pdf" / "renderer"


def _node_binary() -> str | None:
    return shutil.which("node")


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
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return "-"
    negative = amount < 0
    amount = abs(amount)
    inteiro, decimal = f"{amount:,.2f}".split(".")
    inteiro = inteiro.replace(",", "X").replace(".", ",").replace("X", ".")
    prefix = "-R$ " if negative else "R$ "
    return f"{prefix}{inteiro},{decimal}"


def _format_percent(value: Any) -> str:
    try:
        number = float(value) * 100
    except (TypeError, ValueError):
        return "-"
    inteiro = f"{number:.2f}".rstrip("0").rstrip(".").replace(".", ",")
    return f"{inteiro}%"


def _history_rows(financeiro: dict[str, Any], grupo: dict[str, Any]) -> list[dict[str, Any]]:
    historico = grupo.get("historico") or {}
    rows = []
    for month, item in sorted(historico.items())[-11:]:
        rows.append(
            {
                "month": str(month),
                "lowestBid": _format_percent(item.get("menor_lance")),
                "highestBid": _format_percent(item.get("maior_lance")),
                "contemplations": item.get("qtd_contemplacoes", "-"),
            }
        )
    if rows:
        return rows
    summary = financeiro.get("historico_12_meses") or {}
    if not summary:
        return []
    return [
        {
            "month": "Resumo 12 meses",
            "lowestBid": _format_percent(summary.get("media_menor_lance")),
            "highestBid": _format_percent(summary.get("media_maior_lance")),
            "contemplations": summary.get("total_contemplacoes", "-"),
        }
    ]


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
    notes = [str(value) for value in template_campos.values() if str(value or "").strip()]
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
            "objective": str(cliente.get("objetivo") or "Objetivo não informado"),
            "desiredCredit": _format_money(cliente.get("credito_desejado")),
            "desiredTerm": str(cliente.get("prazo_desejado") or "-"),
            "desiredInstallment": _format_money(cliente.get("parcela_desejada")),
            "income": _format_money(cliente.get("renda_total")),
        },
        "group": {
            "administrator": str(grupo.get("administradora") or "-"),
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
            "operatorNotes": notes,
            "strategyRows": strategy_rows,
            "historyRows": _history_rows(financeiro, grupo),
        },
    }


def render_react_study_pdf(estudo: dict[str, Any], version: str) -> bytes:
    status = react_pdf_service_status()
    if not status["available"]:
        reason = "React-pdf service unavailable"
        raise RuntimeError(reason)
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
