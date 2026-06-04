from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


RUNTIME_DIR = Path(__file__).resolve().parent / "runtime_data"
AUDIT_FILE = RUNTIME_DIR / "auditoria_grupos.json"
MAX_ITEMS_PER_GROUP = 80


def _load_all() -> dict[str, list[dict[str, Any]]]:
    if not AUDIT_FILE.exists():
        return {}
    try:
        data = json.loads(AUDIT_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _save_all(data: dict[str, list[dict[str, Any]]]) -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    AUDIT_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def list_auditoria(grupo_id: str) -> list[dict[str, Any]]:
    data = _load_all()
    items = data.get(str(grupo_id), [])
    return deepcopy(items if isinstance(items, list) else [])


def record_auditoria(grupo_id: str, acao: str, detalhe: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    data = _load_all()
    key = str(grupo_id)
    items = data.get(key, [])
    if not isinstance(items, list):
        items = []

    entry = {
        "data_hora": datetime.now(timezone.utc).isoformat(),
        "acao": acao,
        "detalhe": detalhe,
        "operador": "Sistema",
        "payload": payload or {},
    }
    items.insert(0, entry)
    data[key] = items[:MAX_ITEMS_PER_GROUP]
    _save_all(data)
    return deepcopy(entry)
