from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime
import json
from pathlib import Path
import re
from typing import Any

from .configuracoes import RUNTIME_DIR


DEFASAGEM_FILE = RUNTIME_DIR / "defasagem_tarefas.json"


def current_month_key(today: date | None = None) -> str:
    reference = today or date.today()
    return f"{reference.year:04d}-{reference.month:02d}"


def month_label(month_key: str) -> str:
    names = {
        1: "jan", 2: "fev", 3: "mar", 4: "abr", 5: "mai", 6: "jun",
        7: "jul", 8: "ago", 9: "set", 10: "out", 11: "nov", 12: "dez",
    }
    try:
        year, month = month_key.split("-")
        return f"{names[int(month)]}/{year}"
    except (ValueError, KeyError):
        return month_key


def month_index(month_key: str) -> int:
    year, month = month_key.split("-")
    return int(year) * 12 + int(month)


def valid_month_key(month_key: str | None) -> bool:
    return bool(month_key and re.fullmatch(r"\d{4}-\d{2}", str(month_key)))


def add_months(month_key: str, amount: int) -> str:
    absolute = month_index(month_key) + amount
    year = (absolute - 1) // 12
    month = (absolute - 1) % 12 + 1
    return f"{year:04d}-{month:02d}"


def months_between(start_month: str, end_month: str) -> list[str]:
    if month_index(start_month) > month_index(end_month):
        return []
    total = month_index(end_month) - month_index(start_month) + 1
    return [add_months(start_month, offset) for offset in range(total)]


def history_month_has_data(item: dict[str, Any]) -> bool:
    return any(item.get(field) is not None for field in ("maior_lance", "menor_lance", "qtd_contemplacoes"))


def history_month_updated_fields(item: dict[str, Any]) -> list[str]:
    labels = {
        "maior_lance": "maior lance",
        "menor_lance": "menor lance",
        "qtd_contemplacoes": "contemplacoes",
    }
    return [label for field, label in labels.items() if item.get(field) is not None]


def last_history_month(historico: dict[str, dict[str, Any]]) -> str | None:
    valid_months = [month for month, item in (historico or {}).items() if valid_month_key(month) and history_month_has_data(item)]
    if not valid_months:
        return None
    return max(valid_months, key=month_index)


def load_defasagem_tasks() -> dict[str, dict[str, Any]]:
    if not DEFASAGEM_FILE.exists():
        return {}
    try:
        data = json.loads(DEFASAGEM_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def save_defasagem_tasks(tasks: dict[str, dict[str, Any]]) -> None:
    RUNTIME_DIR.mkdir(exist_ok=True)
    DEFASAGEM_FILE.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")


def update_defasagem_task(grupo_id: str, payload: dict[str, Any], operador: str = "") -> dict[str, Any]:
    tasks = load_defasagem_tasks()
    key = str(grupo_id or "").strip().upper()
    current = deepcopy(tasks.get(key, {}))
    current.update({
        "grupo_id": key,
        "concluido": bool(payload.get("concluido")),
        "observacao": str(payload.get("observacao") or "").strip(),
        "operador": operador,
        "atualizado_em": datetime.now().isoformat(timespec="seconds"),
    })
    tasks[key] = current
    save_defasagem_tasks(tasks)
    return current


def build_defasagem_report(groups: list[dict[str, Any]], today: date | None = None) -> dict[str, Any]:
    current = current_month_key(today)
    tasks = load_defasagem_tasks()
    items: list[dict[str, Any]] = []

    for group in groups:
        group_id = str(group.get("grupo_id") or group.get("grupo") or "").strip().upper()
        historico = group.get("historico") or {}
        last_month = last_history_month(historico)
        pending_months = months_between(add_months(last_month, 1), current) if last_month else months_between("2024-01", current)
        last_fields = history_month_updated_fields(historico.get(last_month, {})) if last_month else []
        task = tasks.get(group_id, {})
        atraso = len(pending_months)
        status = "em_dia" if atraso == 0 else "critico" if atraso >= 6 else "atrasado" if atraso >= 3 else "atencao"
        if task.get("concluido") and atraso > 0:
            status = "marcado_para_conferencia"

        items.append({
            "grupo_id": group_id,
            "administradora": group.get("administradora") or "",
            "grupo": group.get("grupo") or "",
            "tipo_bem": group.get("tipo_bem") or "",
            "status_grupo": group.get("status") or "",
            "ultima_competencia": last_month,
            "ultima_competencia_label": month_label(last_month) if last_month else "-",
            "campos_ultima_competencia": last_fields,
            "meses_pendentes": pending_months,
            "meses_pendentes_label": [month_label(month) for month in pending_months],
            "total_meses_defasados": atraso,
            "status_defasagem": status,
            "concluido": bool(task.get("concluido")),
            "observacao": task.get("observacao") or "",
            "operador": task.get("operador") or "",
            "check_atualizado_em": task.get("atualizado_em") or "",
        })

    items.sort(key=lambda item: (
        item["concluido"],
        -item["total_meses_defasados"],
        item["administradora"],
        str(item["grupo"]),
    ))
    total = len(items)
    atrasados = [item for item in items if item["total_meses_defasados"] > 0]
    criticos = [item for item in atrasados if item["total_meses_defasados"] >= 6]
    em_dia = total - len(atrasados)

    return {
        "competencia_atual": current,
        "competencia_atual_label": month_label(current),
        "total_grupos": total,
        "total_em_dia": em_dia,
        "total_atrasados": len(atrasados),
        "total_criticos": len(criticos),
        "maior_defasagem_meses": max((item["total_meses_defasados"] for item in items), default=0),
        "items": items,
    }
