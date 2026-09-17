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
    "Informe o valor máximo para Entrada / Lance?": "lance_proprio",
    "Recurso próprio máximo disponível": "lance_proprio",
    "Informe o valor máximo para Mensalidade?": "parcela_desejada",
    "Parcela máxima disponível": "parcela_desejada",
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


def _parse_form(text: str) -> dict:
    result: dict = {}
    for line in _strip_html(text).splitlines():
        line = line.strip()
        for label, key in FIELD_MAP.items():
            if line.startswith(label):
                value = line[len(label):].lstrip(":? ")
                if value:
                    result[key] = value
                break
    for key in ("credito_desejado", "lance_proprio", "parcela_desejada", "renda_total"):
        if key in result:
            result[key] = _number(result[key])
    return result


async def fetch_opportunity_notes(opportunity_id: str) -> dict:
    opportunity_id = str(opportunity_id).strip()
    if not opportunity_id.isdigit():
        raise ValueError("O ID da oportunidade deve ser numérico.")
    token = os.getenv("PIPERUN_API_KEY", "").strip()
    if not token:
        raise RuntimeError("Integração PipeRun não configurada no ambiente.")
    async with httpx.AsyncClient(timeout=20) as client:
        detail_response = await client.get(
            f"{PIPERUN_BASE_URL}/deals/{int(opportunity_id)}",
            params={"with": "persons,companies,customForms,users"},
            headers={"token": token, "accept": "application/json"},
        )
        if detail_response.status_code in (401, 403):
            raise RuntimeError("Token PipeRun inválido ou sem permissão para consultar oportunidades.")
        if detail_response.status_code == 404:
            raise LookupError("Oportunidade não encontrada na PipeRun.")
        if detail_response.status_code >= 400:
            raise RuntimeError(f"PipeRun recusou a oportunidade (HTTP {detail_response.status_code}).")
        notes_response = await client.get(
            f"{PIPERUN_BASE_URL}/notes",
            params={"cursor": "", "deal_id": int(opportunity_id)},
            headers={"token": token, "accept": "application/json"},
        )
        if notes_response.status_code in (401, 403):
            raise RuntimeError("Token PipeRun inválido ou sem permissão para consultar notas.")
        if notes_response.status_code >= 400 and notes_response.status_code != 404:
            raise RuntimeError(f"PipeRun recusou as notas (HTTP {notes_response.status_code}).")
    detail = detail_response.json().get("data", detail_response.json())
    notes = notes_response.json().get("data", []) if notes_response.status_code != 404 else []
    form_note = next((note for note in notes if "DADOS DO FORMULÁRIO" in (note.get("text") or "")), None)
    dados = _parse_form(form_note.get("text", "")) if form_note else {}
    person = detail.get("person") or detail.get("persons") or {}
    if isinstance(person, list):
        person = person[0] if person else {}
    dados.setdefault("nome", person.get("name", ""))
    dados.setdefault("email", person.get("email", ""))
    dados.setdefault("celular", person.get("phone", "") or person.get("mobile", ""))
    return {
        "crm_oportunidade_id": str(opportunity_id),
        "dados": {key: value for key, value in dados.items() if value not in (None, "")},
        "nota_id": form_note.get("id") if form_note else None,
        "encontrado": bool(form_note),
        "oportunidade": detail,
    }
