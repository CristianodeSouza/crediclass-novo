from __future__ import annotations

import os
import re
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from html import unescape

import httpx


PIPERUN_BASE_URL = "https://api.pipe.run/v1"
PIPERUN_CUSTOM_FORM_ID = "44495"
PIPERUN_CACHE_DB = Path(os.getenv("PIPERUN_CACHE_DB", str(Path(__file__).resolve().parent / "data" / "piperun.sqlite3")))


async def fetch_piperun_owner(owner_id: str) -> dict:
    owner_id = str(owner_id).strip()
    if not owner_id.isdigit():
        raise ValueError("O ID do owner deve ser numérico.")
    token = os.getenv("PIPERUN_API_KEY", "").strip()
    if not token:
        raise RuntimeError("Integração PipeRun não configurada no ambiente.")
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(f"{PIPERUN_BASE_URL}/users/{owner_id}", headers={"token": token, "accept": "application/json"})
    if response.status_code == 404:
        raise LookupError("Owner não encontrado no PipeRun.")
    if response.status_code in (401, 403):
        raise RuntimeError("Token PipeRun inválido ou sem permissão para consultar usuários.")
    if response.status_code >= 400:
        raise RuntimeError(f"PipeRun recusou a consulta do owner (HTTP {response.status_code}).")
    payload = response.json()
    data = payload.get("data") if isinstance(payload, dict) else None
    if isinstance(data, list):
        data = data[0] if data else None
    if not isinstance(data, dict):
        raise LookupError("PipeRun não retornou um usuário para esse ID.")
    name = data.get("name") or data.get("full_name") or data.get("username") or data.get("email")
    if not name:
        raise LookupError("O usuário retornado pelo PipeRun não possui nome.")
    return {"owner_id": int(owner_id), "nome": str(name).strip(), "response": data}


async def fetch_piperun_users() -> list[dict]:
    token = os.getenv("PIPERUN_API_KEY", "").strip()
    if not token:
        raise RuntimeError("Integração PipeRun não configurada no ambiente.")
    users: list[dict] = []
    cursor = ""
    async with httpx.AsyncClient(timeout=20) as client:
        while True:
            response = await client.get(f"{PIPERUN_BASE_URL}/users", headers={"token": token, "accept": "application/json"}, params={"show": 200, "cursor": cursor, "active": "active"})
            if response.status_code in (401, 403):
                raise RuntimeError("Token PipeRun inválido ou sem permissão para listar usuários.")
            if response.status_code >= 400:
                raise RuntimeError(f"PipeRun recusou a lista de usuários (HTTP {response.status_code}).")
            payload = response.json()
            data = payload.get("data") if isinstance(payload, dict) else []
            if isinstance(data, list):
                for user in data:
                    if isinstance(user, dict) and user.get("id") and (user.get("name") or user.get("full_name")):
                        users.append({"owner_id": int(user["id"]), "nome": str(user.get("name") or user.get("full_name")).strip()})
            meta = payload.get("meta") if isinstance(payload, dict) else {}
            next_cursor = str((meta or {}).get("cursor", {}).get("next") or "")
            if not next_cursor or next_cursor == cursor:
                break
            cursor = next_cursor
    return users


def _init_opportunity_cache() -> None:
    PIPERUN_CACHE_DB.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(PIPERUN_CACHE_DB) as db:
        db.execute("CREATE TABLE IF NOT EXISTS piperun_opportunities (deal_id TEXT PRIMARY KEY, payload TEXT NOT NULL, updated_at TEXT NOT NULL)")
        db.commit()


def _cached_opportunities() -> list[dict]:
    _init_opportunity_cache()
    with sqlite3.connect(PIPERUN_CACHE_DB) as db:
        rows = db.execute("SELECT payload FROM piperun_opportunities ORDER BY updated_at DESC").fetchall()
    return [json.loads(row[0]) for row in rows]


def _save_cached_opportunity(item: dict) -> None:
    deal = item.get("oportunidade") or {}
    deal_id = str(deal.get("id") or "").strip()
    if not deal_id:
        return
    _init_opportunity_cache()
    with sqlite3.connect(PIPERUN_CACHE_DB) as db:
        db.execute("INSERT INTO piperun_opportunities (deal_id, payload, updated_at) VALUES (?, ?, datetime('now')) ON CONFLICT(deal_id) DO UPDATE SET payload=excluded.payload, updated_at=excluded.updated_at", (deal_id, json.dumps(item, ensure_ascii=False, default=str)))
        db.commit()

FIELD_MAP = {
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
    titular_section = False
    for line in lines:
        if line.startswith("Em qual titularidade você deseja prosseguir"):
            titular_section = True
            person = None
            continue
        if titular_section and line.startswith("Nome Completo:"):
            person = {"nome": line.split(":", 1)[1].strip(), "renda": 0, "lance_fgts": 0, "lance_recursos_proprios": 0}
            people.append(person)
            continue
        if titular_section and person is not None:
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
    result["empresa_parceira"] = {
        "cnpj": re.sub(r"\D", "", str((raw_fields.get("CNPJ do parceiro cadastrado") or [""])[-1])),
        "nome": (raw_fields.get("Nome da Empresa Parceira") or [""])[-1],
    }
    result["parceiros"] = {
        "indicador": {"nome": (raw_fields.get("Nome Completo") or [""])[0], "telefone": (raw_fields.get("Telefone") or [""])[0], "email": (raw_fields.get("E-mail") or [""])[0]},
        "assessor": {"nome": (raw_fields.get("Nome do assessor do cliente") or [""])[-1], "telefone": (raw_fields.get("Telefone") or ["", ""])[1], "email": (raw_fields.get("E-mail") or ["", ""])[1]},
        "acompanhante_1": {"nome": (raw_fields.get("Nome completo (pessoa 1)") or [""])[-1], "telefone": (raw_fields.get("Telefone") or ["", "", ""])[2], "email": (raw_fields.get("E-mail") or ["", "", ""])[2]},
        "acompanhante_2": {"nome": (raw_fields.get("Nome completo (pessoa 2)") or [""])[-1], "telefone": (raw_fields.get("Telefone") or ["", "", "", ""])[3], "email": (raw_fields.get("E-mail") or ["", "", "", ""])[3]},
    }
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


async def update_opportunity_person(opportunity_id: str, person_id: str, dados: dict) -> dict:
    opportunity_id = str(opportunity_id).strip()
    person_id = str(person_id).strip()
    token = os.getenv("PIPERUN_API_KEY", "").strip()
    if not opportunity_id.isdigit() or not person_id.isdigit():
        raise ValueError("O ID da oportunidade e o person_id devem ser numéricos.")
    if not token:
        raise RuntimeError("Integração PipeRun não configurada no ambiente.")
    cpf = re.sub(r"\D", "", str(dados.get("cpf") or ""))
    async with httpx.AsyncClient(timeout=20) as client:
        headers = {"token": token, "accept": "application/json"}
        current_response = await client.get(
            f"{PIPERUN_BASE_URL}/persons/{person_id}",
            params={"with": "contactEmails,contactPhones"},
            headers=headers,
        )
        if current_response.status_code == 404:
            raise RuntimeError("Titular não encontrado no PipeRun.")
        if current_response.status_code >= 400:
            raise RuntimeError(f"PipeRun recusou a consulta do titular (HTTP {current_response.status_code}).")
        current = current_response.json().get("data", current_response.json())
        current_emails = {str(value).strip().lower() for value in (current.get("contactEmails") or current.get("contact_emails") or []) if value}
        current_phones = {re.sub(r"\D", "", str(value)) for value in (current.get("contactPhones") or current.get("contact_phones") or []) if value}
        body = {}
        incoming = str(dados.get("nome") or "").strip()
        if incoming and not str(current.get("name") or "").strip(): body["name"] = incoming
        email = str(dados.get("email") or "").strip()
        if email and email.lower() not in current_emails: body["contactEmails"] = [*(current.get("contactEmails") or []), email]
        phone = str(dados.get("celular") or "").strip()
        if phone and re.sub(r"\D", "", phone) not in current_phones: body["contactPhones"] = [*(current.get("contactPhones") or []), phone]
        if cpf and not re.sub(r"\D", "", str(current.get("cpf") or "")): body["cpf"] = cpf
        if dados.get("data_nascimento") and not current.get("birth_day"): body["birth_day"] = str(dados["data_nascimento"]).strip()
        if dados.get("profissao") and not current.get("job_title"): body["job_title"] = str(dados["profissao"]).strip()
        if dados.get("observacoes") and not current.get("observation"): body["observation"] = str(dados["observacoes"]).strip()
        custom_response = await client.get(f"{PIPERUN_BASE_URL}/customFields", params={"belongs": 2, "show": 200, "cursor": ""}, headers={"token": token, "accept": "application/json"})
        custom_fields = custom_response.json().get("data", []) if custom_response.status_code < 400 else []
        if isinstance(custom_fields, dict):
            custom_fields = custom_fields.get("data", [])
        normalized_form = {re.sub(r"[^a-z0-9]", "", str(key).lower()): value for key, value in (dados.get("campos_formulario") or {}).items() if value not in (None, "", "Adicionar valor")}
        custom_values = []
        for field in custom_fields if isinstance(custom_fields, list) else []:
            field_name = field.get("name") or field.get("label") or field.get("title") or ""
            field_key = re.sub(r"[^a-z0-9]", "", str(field_name).lower())
            value = normalized_form.get(field_key)
            if value is not None and field.get("id"):
                custom_values.append({"id": field["id"], "value": value if isinstance(value, (str, int, float, bool)) else json.dumps(value, ensure_ascii=False)})
        if custom_values:
            body["custom_fields"] = custom_values
        if not body:
            return {"opportunity_id": opportunity_id, "person_id": person_id, "updated_fields": [], "custom_fields_count": 0, "titular_atualizado": True, "already_complete": True, "response": current}
        response = await client.put(f"{PIPERUN_BASE_URL}/persons/{person_id}", json=body, headers={**headers, "content-type": "application/json"})
    if response.status_code in (401, 403):
        raise RuntimeError("Token PipeRun inválido ou sem permissão para atualizar a pessoa.")
    if response.status_code >= 400:
        raise RuntimeError(f"PipeRun recusou a atualização do titular (HTTP {response.status_code}).")
    return {"opportunity_id": opportunity_id, "person_id": person_id, "updated_fields": [key for key, value in body.items() if value], "custom_fields_count": len(body.get("custom_fields", [])), "titular_atualizado": True, "already_complete": False, "response": response.json()}


def _spouse_data(dados: dict) -> dict:
    """Extract only the explicit spouse block; never treat a second titular as a spouse."""
    fields = dados.get("campos_formulario") or {}
    values = {}
    for label, raw in fields.items():
        normalized = re.sub(r"[^a-z0-9]", "", str(label).lower())
        if not any(marker in normalized for marker in ("conjuge", "convivente")):
            continue
        value = raw[-1] if isinstance(raw, list) and raw else raw
        if value not in (None, "", "Adicionar valor"):
            values[normalized] = value
    def find(*names):
        for name in names:
            for key, value in values.items():
                if name in key:
                    return value
        return ""
    return {
        "nome": find("nomecompleto", "nome"),
        "email": find("email", "emaildoconjuge"),
        "celular": find("celular", "telefone"),
        "cpf": re.sub(r"\D", "", str(find("cpf") or "")),
        "data_nascimento": _date_input(str(find("datadenascimento", "nascimento") or "")),
    }


async def sync_spouse(opportunity_id: str, dados: dict) -> dict:
    spouse = _spouse_data(dados)
    if not spouse["nome"] and not spouse["cpf"] and not spouse["email"]:
        return {"conjuge_atualizado": False, "conjuge_status": "nao_informado"}
    token = os.getenv("PIPERUN_API_KEY", "").strip()
    headers = {"token": token, "accept": "application/json"}
    async with httpx.AsyncClient(timeout=20) as client:
        person = None
        if spouse["cpf"]:
            lookup = await client.get(f"{PIPERUN_BASE_URL}/persons", params={"cpf": spouse["cpf"], "with": "contactEmails,contactPhones", "show": 10}, headers=headers)
            if lookup.status_code < 400:
                rows = lookup.json().get("data", [])
                person = rows[0] if isinstance(rows, list) and rows else None
        if person and person.get("id"):
            spouse_id = str(person["id"])
            current = await client.get(f"{PIPERUN_BASE_URL}/persons/{spouse_id}", params={"with": "contactEmails,contactPhones"}, headers=headers)
            current_data = current.json().get("data", current.json()) if current.status_code < 400 else person
            update = {}
            if spouse["nome"] and not current_data.get("name"): update["name"] = spouse["nome"]
            if spouse["email"] and not (current_data.get("contactEmails") or []): update["contactEmails"] = [spouse["email"]]
            if spouse["celular"] and not (current_data.get("contactPhones") or []): update["contactPhones"] = [spouse["celular"]]
            if spouse["cpf"] and not current_data.get("cpf"): update["cpf"] = spouse["cpf"]
            if spouse["data_nascimento"] and not current_data.get("birth_day"): update["birth_day"] = spouse["data_nascimento"]
            if update: await client.put(f"{PIPERUN_BASE_URL}/persons/{spouse_id}", json=update, headers={**headers, "content-type": "application/json"})
        else:
            payload = {"name": spouse["nome"], "cpf": spouse["cpf"]}
            if spouse["email"]: payload["contactEmails"] = [spouse["email"]]
            if spouse["celular"]: payload["contactPhones"] = [spouse["celular"]]
            if spouse["data_nascimento"]: payload["birth_day"] = spouse["data_nascimento"]
            created = await client.post(f"{PIPERUN_BASE_URL}/persons", json=payload, headers={**headers, "content-type": "application/json"})
            if created.status_code >= 400: raise RuntimeError(f"PipeRun recusou o cadastro do cônjuge (HTTP {created.status_code}).")
            spouse_id = str((created.json().get("data") or {}).get("id") or "")
        if not spouse_id.isdigit(): raise RuntimeError("PipeRun não retornou o ID do cônjuge.")
        link = await client.put(f"{PIPERUN_BASE_URL}/deals/{opportunity_id}/persons/{spouse_id}", headers=headers)
        if link.status_code >= 400 and link.status_code != 409: raise RuntimeError(f"PipeRun recusou o vínculo do cônjuge (HTTP {link.status_code}).")
    return {"conjuge_atualizado": True, "conjuge_id": spouse_id, "nome_conjuge": spouse["nome"], "conjuge_status": "ok"}


async def sync_partner_company(opportunity_id: str, dados: dict) -> dict:
    company = dados.get("empresa_parceira") or {}
    cnpj = re.sub(r"\D", "", str(company.get("cnpj") or ""))
    company_name = str(company.get("nome") or "").strip()
    if not cnpj:
        return {"empresa_parceira_status": "nao_informada", "parceiros_status": "nao_informados", "parceiros_atualizados": []}
    token = os.getenv("PIPERUN_API_KEY", "").strip()
    headers = {"token": token, "accept": "application/json"}
    async with httpx.AsyncClient(timeout=20) as client:
        lookup = await client.get(f"{PIPERUN_BASE_URL}/companies", params={"cnpj": cnpj, "show": 10, "cursor": ""}, headers=headers)
        if lookup.status_code >= 400 and lookup.status_code != 404:
            raise RuntimeError(f"PipeRun recusou a consulta da empresa (HTTP {lookup.status_code}).")
        rows = lookup.json().get("data", []) if lookup.status_code < 400 else []
        if isinstance(rows, dict): rows = rows.get("data", [])
        existing = rows[0] if isinstance(rows, list) and rows else None
        if existing and existing.get("id"):
            company_id = str(existing["id"])
        else:
            created = await client.post(f"{PIPERUN_BASE_URL}/companies", json={"name": company_name or cnpj, "cnpj": cnpj}, headers={**headers, "content-type": "application/json"})
            if created.status_code >= 400: raise RuntimeError(f"PipeRun recusou o cadastro da empresa (HTTP {created.status_code}).")
            company_id = str((created.json().get("data") or {}).get("id") or "")
        if not company_id.isdigit(): raise RuntimeError("PipeRun não retornou o ID da empresa parceira.")
        deal_update = await client.put(
            f"{PIPERUN_BASE_URL}/deals/{opportunity_id}",
            json={"company_id": int(company_id)},
            headers={**headers, "content-type": "application/json"},
        )
        if deal_update.status_code >= 400:
            raise RuntimeError(f"PipeRun recusou o vínculo da empresa à oportunidade (HTTP {deal_update.status_code}).")
        linked = []
        for role, contact in (dados.get("parceiros") or {}).items():
            name = str(contact.get("nome") or "").strip()
            email = str(contact.get("email") or "").strip()
            phone = str(contact.get("telefone") or "").strip()
            if not name or name.lower() in {"não informado", "nao informado"}: continue
            person = None
            people_response = await client.get(f"{PIPERUN_BASE_URL}/persons", params={"company_id": int(company_id), "show": 200, "cursor": "", "with": "contactEmails,contactPhones"}, headers=headers)
            if people_response.status_code < 400:
                people = people_response.json().get("data", [])
                if isinstance(people, list):
                    person = next((row for row in people if (email and email.lower() in {str(v).lower() for v in (row.get("contactEmails") or [])}) or (not email and str(row.get("name") or "").strip().lower() == name.lower())), None)
            if not person:
                created_person = await client.post(f"{PIPERUN_BASE_URL}/persons", json={"name": name, "company_id": int(company_id), "contactEmails": [email] if email else [], "contactPhones": [phone] if phone else []}, headers={**headers, "content-type": "application/json"})
                if created_person.status_code >= 400: raise RuntimeError(f"PipeRun recusou o cadastro do parceiro {role} (HTTP {created_person.status_code}).")
                person = created_person.json().get("data") or {}
            person_id = str(person.get("id") or "")
            if person_id.isdigit():
                link_deal = await client.put(f"{PIPERUN_BASE_URL}/deals/{opportunity_id}/persons/{person_id}", headers=headers)
                if link_deal.status_code >= 400 and link_deal.status_code != 409:
                    raise RuntimeError(f"PipeRun recusou o vínculo do parceiro {role} à oportunidade (HTTP {link_deal.status_code}).")
                linked.append({"papel": role, "person_id": person_id, "nome": name})
    return {"empresa_parceira_id": company_id, "empresa_parceira_status": "ok", "parceiros_status": "ok" if linked else "nao_informados", "parceiros_atualizados": linked}


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


async def fetch_opportunities_preview(limit: int = 25, created_at_start: str | None = None, created_at_end: str | None = None) -> list[dict]:
    """Carrega oportunidades criadas nos últimos três dias e suas notas de formulário."""
    token = os.getenv("PIPERUN_API_KEY", "").strip()
    if not token:
        raise RuntimeError("Integração PipeRun não configurada no ambiente.")
    async with httpx.AsyncClient(timeout=20) as client:
        created_at_start = created_at_start or (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")
        cursor = ""
        deals = []
        seen_cursors = set()
        while True:
            response = await client.get(
                f"{PIPERUN_BASE_URL}/deals",
                headers={"token": token, "accept": "application/json"},
                params={"created_at_start": created_at_start, "created_at_end": created_at_end or "", "deleted": "false", "show": 200, "cursor": cursor, "with": "persons,companies,users"},
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
                next_cursor = (
                    next_cursor.get("next")
                    or next_cursor.get("next_cursor")
                    or next_cursor.get("cursor")
                    or next_cursor.get("value")
                )
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
            item = {"oportunidade": deal, **await fetch_opportunity_notes(deal_id)}
            _save_cached_opportunity(item)
            result.append(item)
    # A resposta atual do PipeRun é a fonte principal. O cache local permanece
    # apenas para recuperação interna e nunca substitui uma resposta nova.
    return result[: max(1, int(limit))] if limit else result
