from pathlib import Path
import logging
from typing import Annotated

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .auditoria import list_auditoria, record_auditoria
from .administrator_feasibility import analyze_administradoras
from .administrator_rules import normalize_admin_name
from .config import get_settings
from .configuracoes import get_configuracoes, update_configuracoes
from .estudos import create_estudo, delete_estudo, export_estudo_pdf, get_estudo, list_estudos
from .models import EstudoCreateResponse, EstudoRequest, EstudosResponse, GrupoCreateRequest, GrupoCreateResponse, GrupoDetalhe, GrupoUpdateRequest, GruposResponse, HistoricoBatchUpdateRequest, HistoricoUpdateRequest, SuccessResponse, ViabilidadeRequest, ViabilidadeResponse
from .sheets_client import clear_rows_cache, create_grupo, delete_grupo, get_grupo, list_grupos, list_grupos_detalhe, list_grupos_detalhe_by_ids, update_grupo, update_historico_mensal, update_historico_mensal_lote
from .viabilidade import analyze_viabilidade, compatible_tipo_bem, normalize_text

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
        total = len(list_grupos())
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

    administradoras = sorted({item["administradora"] for item in items if item["administradora"]})
    tipos_bem = sorted({item["tipo_bem"] for item in items if item["tipo_bem"]})

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
        items = [item for item in items if item["credito_minimo"] is not None and item["credito_minimo"] >= credito_minimo]
    if credito_maximo is not None:
        items = [item for item in items if item["credito_maximo"] is not None and item["credito_maximo"] <= credito_maximo]
    if prazo_minimo is not None:
        items = [item for item in items if item["prazo_total"] is not None and item["prazo_total"] >= prazo_minimo]
    if prazo_maximo is not None:
        items = [item for item in items if item["prazo_total"] is not None and item["prazo_total"] <= prazo_maximo]

    total = len(items)
    total_administradoras = len({item["administradora"] for item in items if item["administradora"]})
    start = (page - 1) * page_size
    end = start + page_size
    logger.info("GET /api/grupos retornou total=%s page=%s", total, page)
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_administradoras": total_administradoras,
        "administradoras": administradoras,
        "tipos_bem": tipos_bem,
        "items": items[start:end],
    }


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
    item["auditoria"] = list_auditoria(item["grupo_id"])
    return item


@app.post("/api/grupos", response_model=GrupoCreateResponse)
def grupo_criar(payload: GrupoCreateRequest):
    logger.info("POST /api/grupos grupo=%s tipo=%s", payload.grupo, payload.tipo_bem)
    try:
        result = create_grupo(payload.model_dump())
        record_auditoria(result["grupo_id"], "Criacao de grupo", "Grupo criado na Google Sheets", payload.model_dump())
    except Exception as error:
        logger.exception("Erro ao criar grupo")
        return JSONResponse(status_code=503, content={"success": False, "error": str(error)})
    return result


@app.put("/api/grupos/{grupo_id}", response_model=SuccessResponse)
def grupo_atualizar(grupo_id: str, payload: GrupoUpdateRequest):
    logger.info("PUT /api/grupos/%s", grupo_id)
    data = payload.model_dump(exclude_unset=True)
    if not data:
        return JSONResponse(status_code=400, content={"success": False, "error": "Nenhum campo enviado"})
    try:
        result = update_grupo(grupo_id, data)
        record_auditoria(data.get("grupo") or grupo_id, "Atualizacao de grupo", "Grupo atualizado na Google Sheets", data)
        return result
    except KeyError:
        return JSONResponse(status_code=404, content={"success": False, "error": "Grupo nao encontrado"})
    except Exception as error:
        logger.exception("Erro ao atualizar grupo")
        return JSONResponse(status_code=503, content={"success": False, "error": str(error)})


@app.delete("/api/grupos/{grupo_id}")
def grupo_excluir(grupo_id: str):
    logger.info("DELETE /api/grupos/%s", grupo_id)
    try:
        result = delete_grupo(grupo_id)
        record_auditoria(grupo_id, "Exclusao logica", "Status alterado para Excluido", {"status": "Excluido"})
        return result
    except KeyError:
        return JSONResponse(status_code=404, content={"success": False, "error": "Grupo nao encontrado"})
    except Exception as error:
        logger.exception("Erro ao excluir grupo")
        return JSONResponse(status_code=503, content={"success": False, "error": str(error)})


@app.put("/api/grupos/{grupo_id}/historico", response_model=SuccessResponse)
def grupo_historico_atualizar(grupo_id: str, payload: HistoricoUpdateRequest):
    logger.info("PUT /api/grupos/%s/historico mes=%s", grupo_id, payload.mes)
    data = payload.model_dump(exclude_unset=True)
    try:
        result = update_historico_mensal(grupo_id, data)
        record_auditoria(grupo_id, "Atualizacao de historico", f"Historico mensal atualizado: {payload.mes}", data)
        return result
    except KeyError:
        return JSONResponse(status_code=404, content={"success": False, "error": "Grupo nao encontrado"})
    except Exception as error:
        logger.exception("Erro ao atualizar historico mensal")
        return JSONResponse(status_code=503, content={"success": False, "error": str(error)})


@app.put("/api/grupos/{grupo_id}/historico/lote", response_model=SuccessResponse)
def grupo_historico_lote_atualizar(grupo_id: str, payload: HistoricoBatchUpdateRequest):
    logger.info("PUT /api/grupos/%s/historico/lote total=%s", grupo_id, len(payload.items))
    try:
        items = [item.model_dump(exclude_unset=True) for item in payload.items]
        update_historico_mensal_lote(grupo_id, items)
        meses = [item.mes for item in payload.items]
        record_auditoria(grupo_id, "Atualizacao de historico", f"Historico mensal atualizado em lote: {', '.join(meses)}", {"items": [item.model_dump(exclude_unset=True) for item in payload.items]})
        return {"success": True}
    except KeyError:
        return JSONResponse(status_code=404, content={"success": False, "error": "Grupo nao encontrado"})
    except Exception as error:
        logger.exception("Erro ao atualizar historico mensal em lote")
        return JSONResponse(status_code=503, content={"success": False, "error": str(error)})


@app.post("/api/viabilidade/analisar", response_model=ViabilidadeResponse)
def viabilidade_analisar(payload: ViabilidadeRequest):
    logger.info(
        "POST /api/viabilidade/analisar credito=%s prazo=%s",
        payload.credito_desejado,
        payload.prazo_desejado,
    )
    try:
        summary_groups = list_grupos()
        config = get_configuracoes()
        administrator_rules = config.get("administradoras_regras") or []
        administradoras = sorted({item["administradora"] for item in summary_groups if item.get("administradora")})
        administradoras_viabilidade = analyze_administradoras(payload, administradoras, administrator_rules)
        administradoras_elegiveis = {
            normalize_admin_name(item["administradora"])
            for item in administradoras_viabilidade
            if item["elegivel"]
        }
        candidate_ids = [
            item["grupo_id"]
            for item in summary_groups
            if normalize_admin_name(item.get("administradora", "")) in administradoras_elegiveis
            and (item.get("credito_maximo") or 0) >= payload.credito_desejado
            and normalize_text(str(item.get("status") or "")) == "ativo"
            and compatible_tipo_bem(payload.objetivo, str(item.get("tipo_bem") or ""), payload.tipo_bem)
        ]
        groups = list_grupos_detalhe_by_ids(candidate_ids) if candidate_ids else []
        result = analyze_viabilidade(payload, groups)
        result["total_grupos_analisados"] = len(summary_groups)
        result["total_administradoras_analisadas"] = len(administradoras_viabilidade)
        result["total_administradoras_elegiveis"] = len(administradoras_elegiveis)
        result["administradoras_viabilidade"] = administradoras_viabilidade
    except Exception as error:
        logger.exception("Erro ao analisar viabilidade")
        return JSONResponse(status_code=503, content={"success": False, "error": str(error)})

    logger.info(
        "POST /api/viabilidade/analisar retornou total=%s perfil=%s",
        result["total_grupos_encontrados"],
        result["perfil"],
    )
    return result


@app.post("/api/viabilidade/administradoras")
def viabilidade_administradoras(payload: ViabilidadeRequest):
    logger.info(
        "POST /api/viabilidade/administradoras credito=%s prazo=%s",
        payload.credito_desejado,
        payload.prazo_desejado,
    )
    try:
        summary_groups = list_grupos()
        config = get_configuracoes()
        administrator_rules = config.get("administradoras_regras") or []
        administradoras = sorted({item["administradora"] for item in summary_groups if item.get("administradora")})
        items = analyze_administradoras(payload, administradoras, administrator_rules)
    except Exception as error:
        logger.exception("Erro ao analisar administradoras")
        return JSONResponse(status_code=503, content={"success": False, "error": str(error)})

    return {
        "total": len(items),
        "total_elegiveis": len([item for item in items if item["elegivel"]]),
        "items": items,
    }


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
    administradora: str | None = None,
    tipo_bem: str | None = None,
    status: str | None = None,
    operador: str | None = None,
    estrategia: str | None = None,
    data_inicio: str | None = None,
    data_fim: str | None = None,
    credito_minimo: float | None = None,
    credito_maximo: float | None = None,
):
    logger.info("GET /api/estudos cliente=%s grupo=%s status=%s", cliente, grupo, status)
    items = list_estudos()

    if cliente:
        needle = cliente.lower()
        items = [item for item in items if needle in str(item.get("cliente", {}).get("nome", "")).lower()]
    if grupo:
        needle = grupo.lower()
        items = [item for item in items if needle in str(item.get("grupo_id", "")).lower()]
    if administradora:
        needle = administradora.lower()
        items = [item for item in items if needle in str(item.get("grupo", {}).get("administradora", "")).lower()]
    if tipo_bem:
        needle = tipo_bem.lower()
        items = [item for item in items if needle in str(item.get("grupo", {}).get("tipo_bem", "")).lower()]
    if status:
        items = [item for item in items if str(item.get("status", "")).lower() == status.lower()]
    if operador:
        items = [item for item in items if str(item.get("operador", "")).lower() == operador.lower()]
    if estrategia:
        items = [item for item in items if str(item.get("estrategia", "")).lower() == estrategia.lower()]
    if data_inicio:
        items = [item for item in items if str(item.get("criado_em", ""))[:10] >= data_inicio]
    if data_fim:
        items = [item for item in items if str(item.get("criado_em", ""))[:10] <= data_fim]
    if credito_minimo is not None:
        items = [
            item for item in items
            if float(item.get("cliente", {}).get("credito_desejado") or item.get("financeiro", {}).get("credito") or 0) >= credito_minimo
        ]
    if credito_maximo is not None:
        items = [
            item for item in items
            if float(item.get("cliente", {}).get("credito_desejado") or item.get("financeiro", {}).get("credito") or 0) <= credito_maximo
        ]

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
