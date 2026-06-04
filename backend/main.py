from pathlib import Path
import logging
from typing import Annotated

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .configuracoes import get_configuracoes, update_configuracoes
from .estudos import create_estudo, delete_estudo, export_estudo_pdf, get_estudo, list_estudos
from .models import EstudoCreateResponse, EstudoRequest, EstudosResponse, GrupoCreateRequest, GrupoCreateResponse, GrupoDetalhe, GrupoUpdateRequest, GruposResponse, HistoricoUpdateRequest, SuccessResponse, ViabilidadeRequest, ViabilidadeResponse
from .sheets_client import clear_rows_cache, create_grupo, delete_grupo, get_grupo, list_grupos, list_grupos_detalhe, read_sheet_rows, update_grupo, update_historico_mensal
from .viabilidade import analyze_viabilidade

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
FILES_DIR = BASE_DIR / "generated_files"
FILES_DIR.mkdir(exist_ok=True)
logger = logging.getLogger("crediclass.api")

app = FastAPI(title="Crediclass Dashboard V3")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/files", StaticFiles(directory=FILES_DIR), name="files")


@app.get("/")
def index():
    return FileResponse(
        STATIC_DIR / "index.html",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
        },
    )


@app.get("/api/health")
def health():
    settings = get_settings()
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.version,
        "environment": settings.environment,
    }


@app.post("/api/reload")
def reload_data():
    logger.info("POST /api/reload")
    try:
        clear_rows_cache()
        total = len(read_sheet_rows(force_reload=True))
    except Exception as error:
        logger.exception("Erro ao recarregar dados da planilha")
        return JSONResponse(status_code=503, content={"success": False, "error": str(error)})

    logger.info("POST /api/reload recarregou total=%s", total)
    return {"success": True, "total": total}


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


@app.post("/api/grupos", response_model=GrupoCreateResponse)
def grupo_criar(payload: GrupoCreateRequest):
    logger.info("POST /api/grupos grupo=%s tipo=%s", payload.grupo, payload.tipo_bem)
    try:
        result = create_grupo(payload.model_dump())
    except Exception as error:
        logger.exception("Erro ao criar grupo")
        return JSONResponse(status_code=503, content={"success": False, "error": str(error)})
    return result


@app.put("/api/grupos/{grupo_id}", response_model=SuccessResponse)
def grupo_atualizar(grupo_id: str, payload: GrupoUpdateRequest):
    logger.info("PUT /api/grupos/%s", grupo_id)
    data = payload.model_dump(exclude_none=True)
    if not data:
        return JSONResponse(status_code=400, content={"success": False, "error": "Nenhum campo enviado"})
    try:
        return update_grupo(grupo_id, data)
    except KeyError:
        return JSONResponse(status_code=404, content={"success": False, "error": "Grupo nao encontrado"})
    except Exception as error:
        logger.exception("Erro ao atualizar grupo")
        return JSONResponse(status_code=503, content={"success": False, "error": str(error)})


@app.delete("/api/grupos/{grupo_id}")
def grupo_excluir(grupo_id: str):
    logger.info("DELETE /api/grupos/%s", grupo_id)
    try:
        return delete_grupo(grupo_id)
    except KeyError:
        return JSONResponse(status_code=404, content={"success": False, "error": "Grupo nao encontrado"})
    except Exception as error:
        logger.exception("Erro ao excluir grupo")
        return JSONResponse(status_code=503, content={"success": False, "error": str(error)})


@app.put("/api/grupos/{grupo_id}/historico", response_model=SuccessResponse)
def grupo_historico_atualizar(grupo_id: str, payload: HistoricoUpdateRequest):
    logger.info("PUT /api/grupos/%s/historico mes=%s", grupo_id, payload.mes)
    data = payload.model_dump(exclude_none=True)
    try:
        return update_historico_mensal(grupo_id, data)
    except KeyError:
        return JSONResponse(status_code=404, content={"success": False, "error": "Grupo nao encontrado"})
    except Exception as error:
        logger.exception("Erro ao atualizar historico mensal")
        return JSONResponse(status_code=503, content={"success": False, "error": str(error)})


@app.post("/api/viabilidade/analisar", response_model=ViabilidadeResponse)
def viabilidade_analisar(payload: ViabilidadeRequest):
    logger.info(
        "POST /api/viabilidade/analisar credito=%s prazo=%s",
        payload.credito_desejado,
        payload.prazo_desejado,
    )
    try:
        groups = list_grupos_detalhe()
        result = analyze_viabilidade(payload, groups)
    except Exception as error:
        logger.exception("Erro ao analisar viabilidade")
        return JSONResponse(status_code=503, content={"success": False, "error": str(error)})

    logger.info(
        "POST /api/viabilidade/analisar retornou total=%s perfil=%s",
        result["total_grupos_encontrados"],
        result["perfil"],
    )
    return result


@app.post("/api/estudos", response_model=EstudoCreateResponse)
def estudos_criar(payload: EstudoRequest):
    logger.info("POST /api/estudos grupo_id=%s", payload.grupo_id)
    try:
        item = get_grupo(payload.grupo_id)
        if not item:
            return JSONResponse(status_code=404, content={"success": False, "error": "Grupo nao encontrado"})
        result = create_estudo(payload, item)
    except Exception as error:
        logger.exception("Erro ao criar estudo")
        return JSONResponse(status_code=503, content={"success": False, "error": str(error)})

    logger.info("POST /api/estudos criou estudo_id=%s", result["estudo_id"])
    return result


@app.get("/api/estudos", response_model=EstudosResponse)
def estudos_listar(
    cliente: str | None = None,
    grupo: str | None = None,
    status: str | None = None,
    operador: str | None = None,
    estrategia: str | None = None,
):
    logger.info("GET /api/estudos cliente=%s grupo=%s status=%s", cliente, grupo, status)
    items = list_estudos()

    if cliente:
        needle = cliente.lower()
        items = [item for item in items if needle in str(item.get("cliente", {}).get("nome", "")).lower()]
    if grupo:
        needle = grupo.lower()
        items = [item for item in items if needle in str(item.get("grupo_id", "")).lower()]
    if status:
        items = [item for item in items if str(item.get("status", "")).lower() == status.lower()]
    if operador:
        items = [item for item in items if str(item.get("operador", "")).lower() == operador.lower()]
    if estrategia:
        items = [item for item in items if str(item.get("estrategia", "")).lower() == estrategia.lower()]

    return {"total": len(items), "items": items}


@app.get("/api/estudos/{estudo_id}")
def estudos_obter(estudo_id: str):
    logger.info("GET /api/estudos/%s", estudo_id)
    item = get_estudo(estudo_id)
    if not item:
        return JSONResponse(status_code=404, content={"success": False, "error": "Estudo nao encontrado"})
    return item


@app.delete("/api/estudos/{estudo_id}")
def estudos_excluir(estudo_id: str):
    logger.info("DELETE /api/estudos/%s", estudo_id)
    if not delete_estudo(estudo_id):
        return JSONResponse(status_code=404, content={"success": False, "error": "Estudo nao encontrado"})
    return {"success": True}


@app.post("/api/estudos/{estudo_id}/exportar-pdf")
def estudos_exportar_pdf(estudo_id: str):
    logger.info("POST /api/estudos/%s/exportar-pdf", estudo_id)
    filename = export_estudo_pdf(estudo_id, FILES_DIR)
    if not filename:
        return JSONResponse(status_code=404, content={"success": False, "error": "Estudo nao encontrado"})
    return {"success": True, "download_url": f"/files/{filename}"}


@app.get("/api/configuracoes")
def configuracoes_obter():
    logger.info("GET /api/configuracoes")
    settings = get_settings()
    data = get_configuracoes()
    data["sistema"] = {
        "app": settings.app_name,
        "version": settings.version,
        "environment": settings.environment,
        "debug": settings.debug,
        "google_sheet_name": settings.google_sheet_name,
        "google_sheets_configurado": bool(settings.google_sheets_id and settings.google_service_account_json),
    }
    return data


@app.put("/api/configuracoes")
def configuracoes_salvar(payload: dict):
    logger.info("PUT /api/configuracoes")
    try:
        return update_configuracoes(payload)
    except Exception as error:
        logger.exception("Erro ao salvar configuracoes")
        return JSONResponse(status_code=400, content={"success": False, "error": str(error)})
