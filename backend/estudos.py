from datetime import datetime

from .models import EstudoRequest

_counter = 0
_studies: dict[str, dict] = {}


def create_estudo(payload: EstudoRequest, grupo: dict | None = None) -> dict:
    global _counter
    _counter += 1
    estudo_id = f"EST-{datetime.now().year}-{_counter:05d}"
    _studies[estudo_id] = {
        "estudo_id": estudo_id,
        "cliente": payload.cliente.model_dump(),
        "grupo_id": payload.grupo_id,
        "grupo": grupo or {},
        "financeiro": {},
        "estrategia": "Lance Total",
        "status": "Em andamento",
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
