from datetime import datetime

from .models import EstudoRequest

_counter = 0
_studies: dict[str, dict] = {}


def create_estudo(payload: EstudoRequest) -> dict:
    global _counter
    _counter += 1
    estudo_id = f"EST-{datetime.now().year}-{_counter:05d}"
    _studies[estudo_id] = {
        "estudo_id": estudo_id,
        "cliente": payload.cliente.model_dump(),
        "grupo_id": payload.grupo_id,
        "criado_em": datetime.now().isoformat(timespec="seconds"),
    }
    return {"estudo_id": estudo_id, "success": True}
