from __future__ import annotations

import os
import re
from html import unescape

import httpx


PIPERUN_BASE_URL = "https://api.pipe.run/v1"

FIELD_MAP = {
    "Nome Completo": "nome",
    "Qual é o valor do imóvel?": "credito_desejado",
    "Qual valor do imóvel desejado?": "credito_desejado",
    "Qual é o valor de carta de crédito desejada?": "credito_desejado",
    "Informe o valor máximo para Entrada / Lance?": "lance_proprio",
    "Recurso próprio máximo disponível": "lance_proprio",
    "Qual é o valor de lance máximo disponível?": "lance_proprio",
    "Qual é o valor máximo para entrada ou lance?": "lance_proprio",
    "Informe o valor máximo para Mensalidade?": "parcela_desejada",
    "Parcela máxima disponível": "parcela_desejada",
    "Qual é a parcela limite que deseja investir?": "parcela_desejada",
    "Qual é o valor máximo para mensalidade?": "parcela_desejada",
    "Perfil informado": "perfil_informado",
    "Qual é o prazo desejado de contemplação?": "prazo_contemplacao",
    "Renda Mensal": "renda_total",
    "Data de Nascimento": "data_nascimento",
    "Qual é o tipo do imóvel desejado?": "tipo_bem",
    "Qual é o tipo de imóvel desejado?": "tipo_bem",
    "Qual o tipo de imóvel?": "tipo_bem",
}


def _strip_html(value: str) -> str:
    value = re.sub(r"<br\s*/?>", "\n", value or "", flags=re.I)
    value = re.sub(r"</(?:p|div)>", "\n", value, flags=re.I)
    return unescape(re.sub(r"<[^>]+>", "", value))


def _number(value: str) -> float | None:
    raw = re.sub(r"[^\d,.]", "", str(value or ""))
    if not raw:
        return None
    if "," in raw and "." in raw:
        raw = raw.replace(".", "").replace(",", ".")
    elif "," in raw:
        raw = raw.replace(",", ".")
    elif "." in raw and len(raw.rsplit(".", 1)[-1]) == 3:
        raw = raw.replace(".", "")
    try:
        return float(raw)
    except ValueError:
        return None


def _date_input(value: str) -> str:
    parts = str(value or "").strip().split("/")
    return f"{parts[2]}-{parts[1]}-{parts[0]}" if len(parts) == 3 and len(parts[2]) == 4 else str(value or "")


def _parse_form(text: str) -> dict:
    lines = [line.strip().replace("::", ":") for line in _strip_html(text).splitlines() if line.strip()]
    result: dict = {}
    raw_fields: dict[str, list[str]] = {}
    for line in lines:
        if ":" in line:
            label, value = line.split(":", 1)
            label, value = label.strip(), value.strip()
            if label and value:
                raw_fields.setdefault(label, []).append(value)
    people: list[dict] = []
    person: dict | None = None
    for line in lines:
        if line.startswith("Nome Completo:"):
            person = {"nome": line.split(":", 1)[1].strip(), "renda": 0, "lance_fgts": 0, "lance_recursos_proprios": 0}
            people.append(person)
            continue
        if person is not None:
            if line.startswith("Data de Nascimento:"):
                person["nascimento"] = _date_input(line.split(":", 1)[1].strip())
            elif line.startswith("Renda Mensal"):
                person["renda"] += _number(line.split(":", 1)[1]) or 0
            elif line.startswith("Valor do FGTS"):
                person["lance_fgts"] = _number(line.split(":", 1)[1]) or 0
            continue
        for label, key in FIELD_MAP.items():
            if line.startswith(label):
                value = line[len(label):].lstrip(":? ")
                if value:
                    result[key] = value
                break
    for key in ("credito_desejado", "lance_proprio", "parcela_desejada", "renda_total"):
        if key in result:
            result[key] = _number(result[key])
    if people:
        result["titulares"] = people
        result["tipo_contratacao"] = "pf_conjuge" if len(people) > 1 else "pf_individual"
        result["nome"] = people[0].get("nome", "")
        result["data_nascimento"] = people[0].get("nascimento", "")
        result["renda_total"] = sum(float(item.get("renda") or 0) for item in people)
        result["lance_proprio"] = result.get("lance_proprio") or 0
        result["fgts"] = sum(float(item.get("lance_fgts") or 0) for item in people)
        result["renda_titular"] = people[0].get("renda", 0)
        result["fgts_titular"] = people[0].get("lance_fgts", 0)
        if len(people) > 1:
            result["nome_conjuge"] = people[1].get("nome", "")
            result["data_nascimento_conjuge"] = people[1].get("nascimento", "")
            result["renda_conjuge"] = people[1].get("renda", 0)
            result["fgts_conjuge"] = people[1].get("lance_fgts", 0)
        prazo = str(result.get("prazo_contemplacao", "")).lower()
        perfil = str(result.get("perfil_informado", "")).lower()
        if "13 a 24" in prazo or "conserv" in perfil:
            result["objetivo"] = "Contemplar - conservador - 24 meses"
        elif "7 a 12" in prazo or "moder" in perfil:
            result["objetivo"] = "Contemplar - moderado - 12 meses"
        elif "até 6" in prazo or "rápido" in perfil:
            result["objetivo"] = "Contemplar - rapido - 6 meses"
    result["campos_formulario"] = raw_fields
    return result


async def fetch_opportunity_notes(opportunity_id: str) -> dict:
    opportunity_id = str(opportunity_id).strip()
    if not opportunity_id.isdigit():
        raise ValueError("O ID da oportunidade deve ser numérico.")
    token = os.getenv("PIPERUN_API_KEY", "").strip()
    if not token:
        raise RuntimeError("Integração PipeRun não configurada no ambiente.")
    async with httpx.AsyncClient(timeout=20) as client:
        notes_response = await client.get(
            f"{PIPERUN_BASE_URL}/notes",
            params={"cursor": "", "deal_id": int(opportunity_id)},
            headers={"token": token, "accept": "application/json"},
        )
        if notes_response.status_code in (401, 403):
            raise RuntimeError("Token PipeRun inválido ou sem permissão para consultar notas.")
        if notes_response.status_code >= 400 and notes_response.status_code != 404:
            raise RuntimeError(f"PipeRun recusou as notas (HTTP {notes_response.status_code}).")
    response_data = notes_response.json()
    notes = response_data.get("data", []) if notes_response.status_code != 404 else []
    if isinstance(notes, dict):
        notes = notes.get("data", [])
    form_note = next((note for note in notes if "DADOS DO FORMULÁRIO" in (note.get("text") or "")), None)
    dados = _parse_form(form_note.get("text", "")) if form_note else {}
    return {
        "crm_oportunidade_id": str(opportunity_id),
        "dados": {key: value for key, value in dados.items() if value not in (None, "")},
        "nota_id": form_note.get("id") if form_note else None,
        "nota_texto": form_note.get("text") if form_note else None,
        "encontrado": bool(form_note),
    }


async def fetch_opportunities_preview(limit: int = 25) -> list[dict]:
    """Carrega uma amostra temporária de oportunidades e suas notas de formulário."""
    token = os.getenv("PIPERUN_API_KEY", "").strip()
    if not token:
        raise RuntimeError("Integração PipeRun não configurada no ambiente.")
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(
            f"{PIPERUN_BASE_URL}/deals",
            headers={"token": token, "accept": "application/json"},
        )
        if response.status_code in (401, 403):
            raise RuntimeError("Token PipeRun inválido ou sem permissão para consultar oportunidades.")
        if response.status_code >= 400:
            raise RuntimeError(f"PipeRun recusou as oportunidades (HTTP {response.status_code}).")
        payload = response.json()
        deals = payload.get("data", [])
        if isinstance(deals, dict):
            deals = deals.get("data", [])
        deals = deals[: max(1, min(int(limit), 50))]

    result = []
    for deal in deals:
        deal_id = str(deal.get("id") or "").strip()
        if deal_id.isdigit():
            result.append({"oportunidade": deal, **await fetch_opportunity_notes(deal_id)})
    return result
