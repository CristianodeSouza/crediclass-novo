from __future__ import annotations

import os
import re
from datetime import datetime, timedelta
from html import unescape

import httpx


PIPERUN_BASE_URL = "https://api.pipe.run/v1"
PIPERUN_CUSTOM_FORM_ID = "44495"

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


async def create_opportunity_note(opportunity_id: str, text: str) -> dict:
    """Create a plain-text note linked to a PipeRun opportunity."""
    opportunity_id = str(opportunity_id).strip()
    if not opportunity_id.isdigit():
        raise ValueError("O ID da oportunidade deve ser numérico.")
    text = str(text or "").strip()
    if not text:
        raise ValueError("O texto da nota não pode ficar vazio.")
    token = os.getenv("PIPERUN_API_KEY", "").strip()
    if not token:
        raise RuntimeError("Integração PipeRun não configurada no ambiente.")
    payload = {"text": text, "deal_id": int(opportunity_id)}
    user_id = os.getenv("PIPERUN_USER_ID", "").strip()
    if user_id.isdigit():
        payload["user_id"] = int(user_id)
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            f"{PIPERUN_BASE_URL}/notes",
            json=payload,
            headers={"token": token, "accept": "application/json", "content-type": "application/json"},
        )
    if response.status_code in (401, 403):
        raise RuntimeError("Token PipeRun inválido ou sem permissão para criar notas.")
    if response.status_code >= 400:
        raise RuntimeError(f"PipeRun recusou a nota (HTTP {response.status_code}).")
    result = response.json()
    data = result.get("data") if isinstance(result, dict) else None
    if isinstance(data, list):
        data = data[0] if data else {}
    return {"note_id": data.get("id") if isinstance(data, dict) else None, "response": result}


async def activate_custom_form_public_link(opportunity_id: str, form_id: str = PIPERUN_CUSTOM_FORM_ID) -> dict:
    """Activate a PipeRun custom-form public link and return its stable URL.

    PipeRun exposes a toggle endpoint. If the first response reports an inactive
    hash, call it once more to reach the active state requested by the caller.
    """
    opportunity_id = str(opportunity_id).strip()
    if not opportunity_id.isdigit():
        raise ValueError("O ID da oportunidade deve ser numérico.")
    form_id = str(form_id).strip()
    if not form_id.isdigit():
        raise ValueError("O ID do formulário PipeRun é inválido.")
    token = os.getenv("PIPERUN_API_KEY", "").strip()
    if not token:
        raise RuntimeError("Integração PipeRun não configurada no ambiente.")

    endpoint = f"{PIPERUN_BASE_URL}/customForms/{form_id}/deals/{opportunity_id}/public_hash"
    headers = {"token": token, "accept": "application/json", "content-type": "application/json"}
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.put(endpoint, json={}, headers=headers)
        if response.status_code in (401, 403):
            raise RuntimeError("Token PipeRun inválido ou sem permissão para ativar o formulário público.")
        if response.status_code >= 400:
            raise RuntimeError(f"PipeRun recusou a ativação do formulário (HTTP {response.status_code}).")
        payload = response.json()
        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, dict):
            raise RuntimeError("PipeRun não retornou os dados do formulário público.")
        if data.get("is_hash_active") is not True:
            response = await client.put(endpoint, json={}, headers=headers)
            if response.status_code in (401, 403):
                raise RuntimeError("Token PipeRun inválido ou sem permissão para ativar o formulário público.")
            if response.status_code >= 400:
                raise RuntimeError(f"PipeRun recusou a ativação do formulário (HTTP {response.status_code}).")
            payload = response.json()
            data = payload.get("data") if isinstance(payload, dict) else None

    public_hash = str(data.get("public_hash") or "").strip() if isinstance(data, dict) else ""
    if not isinstance(data, dict) or data.get("is_hash_active") is not True or not public_hash:
        raise RuntimeError("PipeRun não confirmou um link público ativo para o formulário.")
    return {
        "form_id": form_id,
        "opportunity_id": opportunity_id,
        "public_hash": public_hash,
        "url": f"https://app.pipe.run/v2/custom-form-public/{public_hash}",
    }


async def fetch_opportunities_preview(limit: int = 25) -> list[dict]:
    """Carrega oportunidades criadas nos últimos três dias e suas notas de formulário."""
    token = os.getenv("PIPERUN_API_KEY", "").strip()
    if not token:
        raise RuntimeError("Integração PipeRun não configurada no ambiente.")
    async with httpx.AsyncClient(timeout=20) as client:
        created_at_start = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")
        cursor = ""
        deals = []
        seen_cursors = set()
        while True:
            response = await client.get(
                f"{PIPERUN_BASE_URL}/deals",
                headers={"token": token, "accept": "application/json"},
                params={"created_at_start": created_at_start, "deleted": "false", "show": 200, "cursor": cursor},
            )
            if response.status_code in (401, 403):
                raise RuntimeError("Token PipeRun inválido ou sem permissão para consultar oportunidades.")
            if response.status_code >= 400:
                raise RuntimeError(f"PipeRun recusou as oportunidades (HTTP {response.status_code}).")
            payload = response.json()
            page = payload.get("data", [])
            if isinstance(page, dict):
                page = page.get("data", [])
            deals.extend(page if isinstance(page, list) else [])
            next_cursor = payload.get("next_cursor") or payload.get("cursor")
            if isinstance(payload.get("meta"), dict):
                next_cursor = next_cursor or payload["meta"].get("next_cursor") or payload["meta"].get("cursor")
            if isinstance(next_cursor, dict):
                next_cursor = next_cursor.get("next_cursor") or next_cursor.get("cursor") or next_cursor.get("value")
            if next_cursor is not None:
                next_cursor = str(next_cursor)
            if not next_cursor or next_cursor in seen_cursors or next_cursor == cursor:
                break
            seen_cursors.add(next_cursor)
            cursor = next_cursor
        if limit:
            deals = deals[: max(1, int(limit))]

    result = []
    for deal in deals:
        deal_id = str(deal.get("id") or "").strip()
        if deal_id.isdigit():
            result.append({"oportunidade": deal, **await fetch_opportunity_notes(deal_id)})
    return result
