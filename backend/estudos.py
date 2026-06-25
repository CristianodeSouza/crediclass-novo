from datetime import datetime
import json
from pathlib import Path
import unicodedata

from .financial_study_engine import build_financeiro
from .models import EstudoRequest

RUNTIME_DIR = Path(__file__).resolve().parent / "runtime_data"
STUDIES_FILE = RUNTIME_DIR / "studies.json"


def load_studies_from_disk() -> dict[str, dict]:
    if not STUDIES_FILE.exists():
        return {}
    try:
        data = json.loads(STUDIES_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def initial_counter(studies: dict[str, dict]) -> int:
    counters = []
    for estudo_id in studies:
        try:
            counters.append(int(str(estudo_id).rsplit("-", 1)[-1]))
        except ValueError:
            continue
    return max(counters, default=0)


def save_studies_to_disk() -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    STUDIES_FILE.write_text(json.dumps(_studies, ensure_ascii=False, indent=2), encoding="utf-8")


_studies: dict[str, dict] = load_studies_from_disk()
_counter = initial_counter(_studies)


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
        "cenario": payload.cenario,
        "financeiro": financeiro,
        "template_campos": payload.template_campos,
        "estrategia": financeiro["estrategia_recomendada"],
        "status": "Concluido",
        "operador": "Joyce",
        "criado_em": datetime.now().isoformat(timespec="seconds"),
    }
    save_studies_to_disk()
    return {"estudo_id": estudo_id, "success": True}


def list_estudos() -> list[dict]:
    return sorted(_studies.values(), key=lambda item: item["criado_em"], reverse=True)


def get_estudo(estudo_id: str) -> dict | None:
    return _studies.get(estudo_id)


def delete_estudo(estudo_id: str) -> bool:
    estudo = _studies.get(estudo_id)
    if not estudo:
        return False
    estudo["status"] = "Cancelado"
    estudo["cancelado_em"] = datetime.now().isoformat(timespec="seconds")
    save_studies_to_disk()
    return True


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
        "Campos do Operador",
    ]
    template_campos = estudo.get("template_campos") or {}
    for label, value in template_campos.items():
        lines.append(f"{label}: {value or '-'}")
    lines.extend([
        "",
        "Estrategias",
    ])
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
