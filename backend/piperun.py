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
    token = os.getenv("PIPERUN_API_KEY", "").strip()
    if not token:
        raise RuntimeError("Integração PipeRun não configurada no ambiente.")
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(
            f"{PIPERUN_BASE_URL}/notes",
            params={"cursor": '""', "deal_id": opportunity_id},
            headers={"token": token, "accept": "application/json"},
        )
        response.raise_for_status()
    notes = response.json().get("data", [])
    form_note = next((note for note in notes if "DADOS DO FORMULÁRIO" in (note.get("text") or "")), None)
    return {
        "crm_oportunidade_id": str(opportunity_id),
        "dados": _parse_form(form_note.get("text", "")) if form_note else {},
        "nota_id": form_note.get("id") if form_note else None,
        "encontrado": bool(form_note),
    }
