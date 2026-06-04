from datetime import datetime
from pathlib import Path
import unicodedata

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


def ascii_text(value) -> str:
    text = str(value or "")
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in normalized if ord(ch) < 128)


def money(value) -> str:
    try:
        return f"R$ {float(value):,.2f}"
    except (TypeError, ValueError):
        return "-"


def percent(value) -> str:
    try:
        return f"{float(value) * 100:.2f}%"
    except (TypeError, ValueError):
        return "-"


def pdf_escape(text: str) -> str:
    return ascii_text(text).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def build_pdf_bytes(lines: list[str]) -> bytes:
    content_lines = ["BT", "/F1 11 Tf", "50 780 Td", "14 TL"]
    for line in lines[:48]:
        content_lines.append(f"({pdf_escape(line)}) Tj")
        content_lines.append("T*")
    content_lines.append("ET")
    stream = "\n".join(content_lines).encode("latin1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("ascii"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")
    xref_position = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_position}\n%%EOF\n".encode("ascii"))
    return bytes(pdf)


def study_pdf_lines(estudo: dict) -> list[str]:
    cliente = estudo.get("cliente") or {}
    grupo = estudo.get("grupo") or {}
    financeiro = estudo.get("financeiro") or {}
    historico = financeiro.get("historico_12_meses") or {}
    lines = [
        "Crediclass Dashboard V3 - Estudo Financeiro",
        f"Estudo: {estudo.get('estudo_id', '-')}",
        f"Status: {estudo.get('status', '-')}",
        f"Operador: {estudo.get('operador', '-')}",
        f"Criado em: {estudo.get('criado_em', '-')}",
        "",
        "Cliente",
        f"Nome: {cliente.get('nome', '-')}",
        f"Objetivo: {cliente.get('objetivo', '-')}",
        f"Credito desejado: {money(cliente.get('credito_desejado'))}",
        f"Prazo desejado: {cliente.get('prazo_desejado') or '-'} meses",
        f"Lance proprio: {money(cliente.get('lance_proprio'))}",
        f"FGTS: {money(cliente.get('fgts'))}",
        "",
        "Grupo",
        f"Administradora: {grupo.get('administradora', '-')}",
        f"Grupo: {grupo.get('grupo') or estudo.get('grupo_id', '-')}",
        f"Tipo de bem: {grupo.get('tipo_bem', '-')}",
        f"Status: {grupo.get('status', '-')}",
        "",
        "Resumo Financeiro",
        f"Carta de credito: {money(financeiro.get('credito_original') or financeiro.get('credito'))}",
        f"Lance embutido: {money(financeiro.get('lance_embutido'))}",
        f"Recurso proprio: {money(financeiro.get('recurso_proprio'))}",
        f"Valor total do lance: {money(financeiro.get('valor_total_lance'))}",
        f"Percentual lance total: {percent(financeiro.get('percentual_lance_total'))}",
        f"Parcela inicial: {money(financeiro.get('parcela_inicial'))}",
        f"Parcela apos contemplacao: {money(financeiro.get('parcela_apos_contemplacao'))}",
        f"Chance: {financeiro.get('chance_contemplacao', '-')}",
        f"Total contemplacoes 12m: {historico.get('total_contemplacoes', '-')}",
        "",
        "Estrategias",
    ]
    for strategy in financeiro.get("estrategias", [])[:8]:
        lines.append(
            f"{strategy.get('estrategia', '-')}: {percent(strategy.get('percentual_lance'))} | "
            f"Lance proprio {money(strategy.get('lance_proprio'))} | Chance {strategy.get('chance_contemplacao', '-')}"
        )
    return lines


def export_estudo_pdf(estudo_id: str, output_dir: Path) -> str | None:
    estudo = get_estudo(estudo_id)
    if not estudo:
        return None
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{estudo_id}.pdf"
    path = output_dir / filename
    path.write_bytes(build_pdf_bytes(study_pdf_lines(estudo)))
    return filename
