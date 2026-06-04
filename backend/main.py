from pathlib import Path
import logging
from typing import Annotated

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .models import GrupoDetalhe, GruposResponse
from .sheets_client import get_grupo, list_grupos

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
logger = logging.getLogger("crediclass.api")

app = FastAPI(title="Crediclass Dashboard V3")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health():
    settings = get_settings()
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.version,
        "environment": settings.environment,
    }


@app.get("/api/grupos", response_model=GruposResponse)
def grupos(
    administradora: str | None = None,
    tipo_bem: str | None = None,
    status: str | None = None,
    busca: str | None = None,
    credito_minimo: float | None = None,
    credito_maximo: float | None = None,
    prazo_minimo: int | None = None,
    prazo_maximo: int | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
):
    logger.info("GET /api/grupos page=%s page_size=%s busca=%s", page, page_size, busca)
    try:
        items = list_grupos()
    except Exception as error:
        logger.exception("Erro ao listar grupos")
        return JSONResponse(status_code=503, content={"success": False, "error": str(error)})

    if administradora:
        items = [item for item in items if item["administradora"].lower() == administradora.lower()]
    if tipo_bem:
        items = [item for item in items if item["tipo_bem"].lower() == tipo_bem.lower()]
    if status:
        items = [item for item in items if item["status"].lower() == status.lower()]
    if busca:
        needle = busca.lower()
        items = [
            item for item in items
            if needle in item["grupo_id"].lower()
            or needle in item["grupo"].lower()
            or needle in item["administradora"].lower()
        ]
    if credito_minimo is not None:
        items = [item for item in items if item["credito_maximo"] is not None and item["credito_maximo"] >= credito_minimo]
    if credito_maximo is not None:
        items = [item for item in items if item["credito_minimo"] is not None and item["credito_minimo"] <= credito_maximo]
    if prazo_minimo is not None:
        items = [item for item in items if item["prazo_total"] is not None and item["prazo_total"] >= prazo_minimo]
    if prazo_maximo is not None:
        items = [item for item in items if item["prazo_total"] is not None and item["prazo_total"] <= prazo_maximo]

    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    logger.info("GET /api/grupos retornou total=%s page=%s", total, page)
    return {"total": total, "page": page, "page_size": page_size, "items": items[start:end]}


@app.get("/api/grupos/{grupo_id}", response_model=GrupoDetalhe)
def grupo_detalhe(grupo_id: str):
    logger.info("GET /api/grupos/%s", grupo_id)
    try:
        item = get_grupo(grupo_id)
    except Exception as error:
        logger.exception("Erro ao obter grupo")
        return JSONResponse(status_code=503, content={"success": False, "error": str(error)})

    if not item:
        return JSONResponse(status_code=404, content={"success": False, "error": "Grupo nao encontrado"})
    return item
