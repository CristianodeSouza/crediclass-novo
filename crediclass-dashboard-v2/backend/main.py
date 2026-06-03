from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from dotenv import load_dotenv
from config import settings
from sheets import get_service, read_all_rows, get_headers
from models import GrupoResumido, GrupoComHistorico, GrupoUpdate, ResponseMessage
from typing import List
from fastapi import HTTPException
from sheets import update_group, append_group

# Carregar variáveis de ambiente
load_dotenv()

# Criar instância FastAPI
app = FastAPI(title="Crediclass Dashboard Grupos V2")

# Montar arquivos estáticos
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Servir index.html na raiz
@app.get("/")
async def root():
    return FileResponse(os.path.join(static_dir, "index.html"))

# Health check com diagnóstico
@app.get("/health")
async def health():
    diagnostico = {
        "status": "ok",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "google_sheets": {
            "sheets_id_configured": bool(settings.GOOGLE_SHEETS_ID),
            "credentials_configured": bool(settings.GOOGLE_SERVICE_ACCOUNT_JSON),
            "sheet_name_configured": bool(settings.GOOGLE_SHEET_NAME),
            "service_available": False,
            "headers_count": 0,
            "rows_count": 0
        }
    }

    # Testar conexão Google Sheets
    try:
        service = get_service()
        if service:
            diagnostico["google_sheets"]["service_available"] = True

            headers = get_headers()
            if headers:
                diagnostico["google_sheets"]["headers_count"] = len(headers)

            rows = read_all_rows()
            if rows:
                diagnostico["google_sheets"]["rows_count"] = len(rows)
    except Exception as e:
        print(f"Erro ao testar Google Sheets: {e}")

    return diagnostico

# Endpoint de diagnóstico detalhado
@app.get("/diagnostic")
async def diagnostic():
    print("\n" + "="*60)
    print("DIAGNÓSTICO ETAPA 2 - CONEXÃO GOOGLE SHEETS")
    print("="*60)

    print(f"\n📋 CONFIGURAÇÃO:")
    print(f"  GOOGLE_SHEETS_ID: {'✅ Configurado' if settings.GOOGLE_SHEETS_ID else '❌ NÃO CONFIGURADO'}")
    print(f"  GOOGLE_SHEET_NAME: {'✅ Configurado' if settings.GOOGLE_SHEET_NAME else '❌ NÃO CONFIGURADO'}")
    print(f"  GOOGLE_SERVICE_ACCOUNT_JSON: {'✅ Configurado' if settings.GOOGLE_SERVICE_ACCOUNT_JSON else '❌ NÃO CONFIGURADO'}")

    response = {
        "timestamp": __import__("datetime").datetime.now().isoformat(),
        "configuration": {
            "sheets_id": bool(settings.GOOGLE_SHEETS_ID),
            "credentials": bool(settings.GOOGLE_SERVICE_ACCOUNT_JSON),
            "sheet_name": bool(settings.GOOGLE_SHEET_NAME),
        },
        "connection_test": {},
        "data_summary": {}
    }

    # Testar conexão
    print(f"\n🔌 TESTE DE CONEXÃO:")
    try:
        service = get_service()
        if service:
            print(f"  ✅ Serviço Google Sheets autenticado com sucesso")
            response["connection_test"]["authenticated"] = True

            # Ler headers
            headers = get_headers()
            if headers:
                print(f"  ✅ Headers carregados: {len(headers)} colunas")
                response["connection_test"]["headers_loaded"] = True
                response["connection_test"]["header_count"] = len(headers)
                response["data_summary"]["headers"] = headers[:5]  # Mostrar primeiros 5

            # Ler linhas
            rows = read_all_rows()
            if rows:
                print(f"  ✅ Dados carregados: {len(rows)} linhas")
                response["connection_test"]["data_loaded"] = True
                response["data_summary"]["total_rows"] = len(rows)

                # Mostrar primeira linha como exemplo
                if rows:
                    first_row = rows[0]
                    print(f"  📊 Exemplo de primeira linha:")
                    for k, v in list(first_row.items())[:3]:
                        print(f"     {k}: {v}")

            response["status"] = "✅ ETAPA 2 - CONEXÃO BEM-SUCEDIDA"
        else:
            print(f"  ❌ Falha ao autenticar")
            response["status"] = "❌ ETAPA 2 - FALHA NA AUTENTICAÇÃO"
            response["connection_test"]["authenticated"] = False

    except Exception as e:
        print(f"  ❌ Erro: {e}")
        response["status"] = f"❌ ETAPA 2 - ERRO: {str(e)}"
        response["error"] = str(e)

    print("\n" + "="*60 + "\n")
    return response

# Etapa 3: Listar todos os grupos
@app.get("/api/grupos", response_model=List[GrupoResumido])
async def listar_grupos():
    """Lista todos os grupos da planilha"""
    try:
        rows = read_all_rows()
        if not rows:
            return []

        grupos = []
        for row in rows:
            grupo = GrupoResumido(
                grupo_id=f"{row.get('Administradora', '')}-{row.get('Grupo', '')}",
                administradora=row.get('Administradora', ''),
                grupo=row.get('Grupo', ''),
                tipo_bem=row.get('Tipo de Bem', ''),
                menor_credito=_safe_float(row.get('Menor Crédito', '')),
                maior_credito=_safe_float(row.get('Maior Crédito', '')),
                prazo_grupo=_safe_int(row.get('Prazo do Grupo', '')),
                prestacao_integral=_safe_float(row.get('Prestação Integral', '')),
                taxa_administracao=_safe_float(row.get('Taxa Administração', '')),
                status=row.get('Status', 'Ativo')
            )
            grupos.append(grupo)

        return grupos
    except Exception as e:
        print(f"❌ Erro ao listar grupos: {e}")
        return []

# Etapa 4: Buscar grupo específico
@app.get("/api/grupos/{grupo_id}", response_model=GrupoComHistorico)
async def obter_grupo(grupo_id: str):
    """Retorna dados completos de um grupo incluindo histórico"""
    try:
        rows = read_all_rows()
        if not rows:
            raise HTTPException(status_code=404, detail="Nenhum grupo encontrado")

        # Buscar grupo por ID (formato: ADMINISTRADORA-GRUPO)
        partes_id = grupo_id.split('-', 1)
        if len(partes_id) != 2:
            raise HTTPException(status_code=400, detail="Formato de ID inválido. Use: ADMINISTRADORA-GRUPO")

        admin_search = partes_id[0].strip()
        grupo_search = partes_id[1].strip()

        for row in rows:
            admin = row.get('Administradora', '').strip()
            grupo = row.get('Grupo', '').strip()

            if admin == admin_search and grupo == grupo_search:
                # Encontrou o grupo, montar resposta com histórico
                grupo_com_historico = GrupoComHistorico(
                    grupo_id=grupo_id,
                    administradora=row.get('Administradora', ''),
                    grupo=row.get('Grupo', ''),
                    tipo_bem=row.get('Tipo de Bem', ''),
                    primeira_assembleia=row.get('Primeira Assembleia', ''),
                    data_termino=row.get('Data Término', ''),
                    prazo_grupo=_safe_int(row.get('Prazo do Grupo', '')),
                    prazo_restante=_safe_int(row.get('Prazo Restante', '')),
                    menor_credito=_safe_float(row.get('Menor Crédito', '')),
                    maior_credito=_safe_float(row.get('Maior Crédito', '')),
                    taxa_administracao=_safe_float(row.get('Taxa Administração', '')),
                    fundo_reserva=_safe_float(row.get('Fundo Reserva', '')),
                    prestacao_integral=_safe_float(row.get('Prestação Integral', '')),
                    categoria=row.get('Categoria', ''),
                    status=row.get('Status', 'Ativo'),
                    historico={
                        "2024": [],
                        "2025": [],
                        "2026": []
                    }
                )
                return grupo_com_historico

        raise HTTPException(status_code=404, detail=f"Grupo {grupo_id} não encontrado")

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Erro ao buscar grupo: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Etapa 5: Atualizar grupo
@app.put("/api/grupos/{grupo_id}", response_model=ResponseMessage)
async def atualizar_grupo(grupo_id: str, grupo_data: GrupoUpdate):
    """Atualiza dados de um grupo existente"""
    try:
        # Verificar se grupo existe
        rows = read_all_rows()
        partes_id = grupo_id.split('-', 1)
        if len(partes_id) != 2:
            raise HTTPException(status_code=400, detail="Formato de ID inválido. Use: ADMINISTRADORA-GRUPO")

        admin_search = partes_id[0].strip()
        grupo_search = partes_id[1].strip()

        grupo_existe = False
        for row in rows:
            if row.get('Administradora', '').strip() == admin_search and row.get('Grupo', '').strip() == grupo_search:
                grupo_existe = True
                break

        if not grupo_existe:
            raise HTTPException(status_code=404, detail=f"Grupo {grupo_id} não encontrado")

        # Preparar dados para atualizar
        dados_para_atualizar = {}

        if grupo_data.dados_gerais:
            # Mapear dados gerais para nomes de colunas do Google Sheets
            mapeamento = {
                'administradora': 'Administradora',
                'grupo': 'Grupo',
                'tipo_bem': 'Tipo de Bem',
                'primeira_assembleia': 'Primeira Assembleia',
                'data_termino': 'Data Término',
                'prazo_grupo': 'Prazo do Grupo',
                'prazo_restante': 'Prazo Restante',
                'menor_credito': 'Menor Crédito',
                'maior_credito': 'Maior Crédito',
                'taxa_administracao': 'Taxa Administração',
                'fundo_reserva': 'Fundo Reserva',
                'prestacao_integral': 'Prestação Integral',
                'categoria': 'Categoria',
                'status': 'Status'
            }

            for campo_json, valor in grupo_data.dados_gerais.items():
                if valor is not None and campo_json in mapeamento:
                    coluna = mapeamento[campo_json]
                    dados_para_atualizar[coluna] = str(valor)

        # Se tem histórico, adicionar aos dados (será tratado em Etapas posteriores)
        if grupo_data.historico:
            # Por enquanto, apenas registrar que há histórico
            print(f"⚠️  Histórico recebido para {grupo_id}: será processado em etapas posteriores")

        # Executar atualização
        sucesso = update_group(grupo_id, dados_para_atualizar)

        if sucesso:
            return ResponseMessage(
                status="success",
                message=f"Grupo {grupo_id} atualizado com sucesso",
                data={"grupo_id": grupo_id}
            )
        else:
            raise HTTPException(status_code=500, detail=f"Erro ao atualizar grupo {grupo_id}")

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Erro ao atualizar grupo: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Etapa 6: Criar novo grupo
@app.post("/api/grupos", response_model=ResponseMessage)
async def criar_grupo(grupo_data: GrupoUpdate):
    """Cria um novo grupo na planilha"""
    try:
        if not grupo_data.dados_gerais:
            raise HTTPException(
                status_code=400,
                detail="dados_gerais é obrigatório para criar novo grupo"
            )

        # Validar campos obrigatórios
        campos_obrigatorios = ['administradora', 'grupo']
        for campo in campos_obrigatorios:
            if campo not in grupo_data.dados_gerais or not grupo_data.dados_gerais[campo]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Campo obrigatório ausente: {campo}"
                )

        # Verificar se grupo já existe
        rows = read_all_rows()
        admin_novo = str(grupo_data.dados_gerais.get('administradora', '')).strip()
        grupo_novo = str(grupo_data.dados_gerais.get('grupo', '')).strip()

        for row in rows:
            if (row.get('Administradora', '').strip() == admin_novo and
                row.get('Grupo', '').strip() == grupo_novo):
                raise HTTPException(
                    status_code=409,
                    detail=f"Grupo {admin_novo}-{grupo_novo} já existe"
                )

        # Preparar dados para inserir
        dados_para_inserir = {}

        # Mapeamento de campos JSON para colunas do Google Sheets
        mapeamento = {
            'administradora': 'Administradora',
            'grupo': 'Grupo',
            'tipo_bem': 'Tipo de Bem',
            'primeira_assembleia': 'Primeira Assembleia',
            'data_termino': 'Data Término',
            'prazo_grupo': 'Prazo do Grupo',
            'prazo_restante': 'Prazo Restante',
            'menor_credito': 'Menor Crédito',
            'maior_credito': 'Maior Crédito',
            'taxa_administracao': 'Taxa Administração',
            'fundo_reserva': 'Fundo Reserva',
            'prestacao_integral': 'Prestação Integral',
            'categoria': 'Categoria',
            'status': 'Status'
        }

        for campo_json, valor in grupo_data.dados_gerais.items():
            if valor is not None and campo_json in mapeamento:
                coluna = mapeamento[campo_json]
                dados_para_inserir[coluna] = str(valor)

        # Adicionar valor padrão para Status se não fornecido
        if 'Status' not in dados_para_inserir:
            dados_para_inserir['Status'] = 'Ativo'

        # Executar inserção
        sucesso = append_group(dados_para_inserir)

        if sucesso:
            grupo_id = f"{admin_novo}-{grupo_novo}"
            return ResponseMessage(
                status="success",
                message=f"Grupo {grupo_id} criado com sucesso",
                data={"grupo_id": grupo_id}
            )
        else:
            raise HTTPException(
                status_code=500,
                detail="Erro ao criar novo grupo"
            )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Erro ao criar grupo: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def _safe_float(value: str) -> float:
    """Converte string para float com segurança"""
    if not value or value.strip() == '':
        return None
    try:
        return float(str(value).replace(',', '.'))
    except (ValueError, TypeError):
        return None

def _safe_int(value: str) -> int:
    """Converte string para int com segurança"""
    if not value or value.strip() == '':
        return None
    try:
        return int(str(value).split('.')[0])
    except (ValueError, TypeError):
        return None

if __name__ == "__main__":
    import uvicorn
    debug = os.getenv("DEBUG", "false").lower() == "true"
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=debug
    )
