# Crediclass Dashboard Grupos V2

Sistema de gerenciamento de grupos de consórcio imobiliário desenvolvido com FastAPI e JavaScript Vanilla.

## Stack

- **Backend:** Python 3.12, FastAPI, Uvicorn
- **Frontend:** HTML5, Bootstrap 5, JavaScript Vanilla
- **Dados:** Google Sheets API
- **Hospedagem:** Render

## Instalação

### Pré-requisitos
- Python 3.12+
- pip

### Setup Local

```bash
# 1. Criar ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# 2. Instalar dependências
cd backend
pip install -r requirements.txt

# 3. Configurar variáveis de ambiente
cp .env.example .env
# Editar .env com suas credenciais Google Sheets

# 4. Executar servidor
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Acessar

Abra no navegador: `http://localhost:8000`

## Status do Desenvolvimento

- [x] Etapa 1: Projeto limpo com FastAPI
- [x] Etapa 2: Conexão Google Sheets
- [x] Etapa 3: GET /api/grupos
- [x] Etapa 4: GET /api/grupos/{grupo_id}
- [x] Etapa 5: PUT /api/grupos/{grupo_id}
- [x] Etapa 6: POST /api/grupos
- [x] Etapa 7: DELETE /api/grupos/{grupo_id}
- [ ] Etapa 8: Frontend mínimo
- [ ] Etapa 9: Modal com abas
- [ ] Etapa 10: Salvar da modal

## Documentação

Veja `PLANO_EXECUCAO_CREDICLASS_V2_CODEX.md` para detalhes completos.
