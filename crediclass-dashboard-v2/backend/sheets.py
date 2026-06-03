"""
Módulo para interação com Google Sheets API
Implementação Etapa 2 do plano
"""

import json
import os
from typing import List, Dict, Optional, Tuple
from google.oauth2.service_account import Credentials
from google.api_python_client import discovery
from config import settings

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# Cache de dados em memória
_cached_data = None
_cached_headers = None

def get_service():
    """Retorna cliente autenticado da Google Sheets API"""
    try:
        # Parsear JSON das credenciais da variável de ambiente
        service_account_json = settings.GOOGLE_SERVICE_ACCOUNT_JSON

        if not service_account_json:
            print("❌ GOOGLE_SERVICE_ACCOUNT_JSON não está configurado")
            return None

        # Se for string JSON, parsear
        if isinstance(service_account_json, str):
            credentials_info = json.loads(service_account_json)
        else:
            credentials_info = service_account_json

        # Autenticar
        credentials = Credentials.from_service_account_info(
            credentials_info,
            scopes=SCOPES
        )

        # Criar cliente
        service = discovery.build('sheets', 'v4', credentials=credentials)
        print("✅ Autenticação Google Sheets bem-sucedida")
        return service

    except json.JSONDecodeError as e:
        print(f"❌ Erro ao parsear JSON das credenciais: {e}")
        return None
    except Exception as e:
        print(f"❌ Erro ao autenticar Google Sheets: {e}")
        return None

def get_headers() -> List[str]:
    """Retorna lista de headers da planilha"""
    global _cached_headers

    if _cached_headers:
        return _cached_headers

    try:
        service = get_service()
        if not service:
            print("❌ Serviço Google Sheets indisponível")
            return []

        sheet_name = settings.GOOGLE_SHEET_NAME
        if not sheet_name:
            print("❌ GOOGLE_SHEET_NAME não configurado")
            return []

        # Ler primeira linha (headers)
        range_name = f"'{sheet_name}'!A1:Z1"
        result = service.spreadsheets().values().get(
            spreadsheetId=settings.GOOGLE_SHEETS_ID,
            range=range_name
        ).execute()

        values = result.get('values', [])
        if values:
            _cached_headers = values[0]
            print(f"✅ Headers carregados: {len(_cached_headers)} colunas")
            return _cached_headers

        print("❌ Nenhum header encontrado")
        return []

    except Exception as e:
        print(f"❌ Erro ao ler headers: {e}")
        return []

def read_all_rows() -> List[Dict[str, any]]:
    """Lê todas as linhas da planilha e retorna como dicts"""
    global _cached_data

    if _cached_data:
        return _cached_data

    try:
        service = get_service()
        if not service:
            print("❌ Serviço Google Sheets indisponível")
            return []

        sheet_name = settings.GOOGLE_SHEET_NAME
        if not sheet_name:
            print("❌ GOOGLE_SHEET_NAME não configurado")
            return []

        # Ler todos os dados
        range_name = f"'{sheet_name}'!A:Z"
        result = service.spreadsheets().values().get(
            spreadsheetId=settings.GOOGLE_SHEETS_ID,
            range=range_name
        ).execute()

        values = result.get('values', [])
        if not values or len(values) < 2:
            print("⚠️  Nenhuma linha de dados encontrada")
            return []

        headers = values[0]
        rows = []

        for idx, row in enumerate(values[1:], start=2):
            # Preencher células vazias
            while len(row) < len(headers):
                row.append('')

            row_dict = {}
            for i, header in enumerate(headers):
                row_dict[header.strip()] = row[i] if i < len(row) else ''

            rows.append(row_dict)

        _cached_data = rows
        print(f"✅ {len(rows)} linhas carregadas da Google Sheets")
        return rows

    except Exception as e:
        print(f"❌ Erro ao ler linhas: {e}")
        return []

def find_group_row(grupo_id: str) -> Optional[Tuple[int, Dict[str, any]]]:
    """Localiza linha do grupo na planilha
    Retorna (row_index, row_dict) ou None se não encontrado
    """
    try:
        rows = read_all_rows()

        # Procurar por grupo_id em várias colunas possíveis
        for idx, row in enumerate(rows):
            # Tentar encontrar por ID composto (ADMIN-GRUPO)
            admin = row.get('Administradora', '')
            grupo = row.get('Grupo', '')

            composed_id = f"{admin.strip()}-{grupo.strip()}" if admin and grupo else None

            if composed_id == grupo_id or row.get('Grupo', '').strip() == grupo_id:
                print(f"✅ Grupo {grupo_id} encontrado na linha {idx + 2}")
                return (idx + 2, row)  # +2 porque Google Sheets começa em 1 e há header

        print(f"⚠️  Grupo {grupo_id} não encontrado")
        return None

    except Exception as e:
        print(f"❌ Erro ao localizar grupo: {e}")
        return None

def append_group(data: dict) -> bool:
    """Insere nova linha na planilha"""
    try:
        service = get_service()
        if not service:
            return False

        headers = get_headers()
        if not headers:
            print("❌ Headers não disponíveis")
            return False

        sheet_name = settings.GOOGLE_SHEET_NAME

        # Preparar nova linha
        new_row = []
        for header in headers:
            new_row.append(data.get(header.strip(), ''))

        # Inserir linha
        range_name = f"'{sheet_name}'!A:Z"
        body = {'values': [new_row]}

        result = service.spreadsheets().values().append(
            spreadsheetId=settings.GOOGLE_SHEETS_ID,
            range=range_name,
            valueInputOption='RAW',
            body=body
        ).execute()

        print(f"✅ Nova linha inserida: {result.get('updates', {}).get('updatedRows')} linhas adicionadas")
        _cached_data = None  # Invalidar cache
        return True

    except Exception as e:
        print(f"❌ Erro ao inserir grupo: {e}")
        return False

def update_group(grupo_id: str, data: dict) -> bool:
    """Atualiza linha do grupo na planilha"""
    try:
        service = get_service()
        if not service:
            return False

        headers = get_headers()
        if not headers:
            return False

        row_info = find_group_row(grupo_id)
        if not row_info:
            print(f"❌ Grupo {grupo_id} não encontrado para atualização")
            return False

        row_index, existing_row = row_info
        sheet_name = settings.GOOGLE_SHEET_NAME

        # Preparar linha atualizada
        updated_row = []
        for header in headers:
            header_clean = header.strip()
            if header_clean in data:
                updated_row.append(data[header_clean])
            else:
                updated_row.append(existing_row.get(header_clean, ''))

        # Atualizar na planilha
        range_name = f"'{sheet_name}'!A{row_index}:Z{row_index}"
        body = {'values': [updated_row]}

        result = service.spreadsheets().values().update(
            spreadsheetId=settings.GOOGLE_SHEETS_ID,
            range=range_name,
            valueInputOption='RAW',
            body=body
        ).execute()

        print(f"✅ Grupo {grupo_id} atualizado na linha {row_index}")
        _cached_data = None  # Invalidar cache
        return True

    except Exception as e:
        print(f"❌ Erro ao atualizar grupo: {e}")
        return False

def delete_group(grupo_id: str) -> bool:
    """Deleta ou inativa linha do grupo"""
    try:
        service = get_service()
        if not service:
            return False

        row_info = find_group_row(grupo_id)
        if not row_info:
            print(f"❌ Grupo {grupo_id} não encontrado para exclusão")
            return False

        row_index, _ = row_info
        sheet_id = 0  # ID da primeira aba

        # Usar exclusão física (remover linha)
        requests = [
            {
                'deleteDimension': {
                    'range': {
                        'sheetId': sheet_id,
                        'dimension': 'ROWS',
                        'startIndex': row_index - 1,
                        'endIndex': row_index
                    }
                }
            }
        ]

        body = {'requests': requests}

        result = service.spreadsheets().batchUpdate(
            spreadsheetId=settings.GOOGLE_SHEETS_ID,
            body=body
        ).execute()

        print(f"✅ Grupo {grupo_id} removido da linha {row_index}")
        _cached_data = None  # Invalidar cache
        return True

    except Exception as e:
        print(f"❌ Erro ao excluir grupo: {e}")
        return False

def reload_data() -> bool:
    """Recarrega dados da planilha (limpa cache)"""
    global _cached_data, _cached_headers
    try:
        _cached_data = None
        _cached_headers = None

        # Forçar reload
        read_all_rows()
        print("✅ Dados recarregados com sucesso")
        return True
    except Exception as e:
        print(f"❌ Erro ao recarregar dados: {e}")
        return False

# Teste de inicialização
if __name__ == "__main__":
    print("Testando módulo sheets.py...")
    print(f"GOOGLE_SHEETS_ID: {'✅ Configurado' if settings.GOOGLE_SHEETS_ID else '❌ Não configurado'}")
    print(f"GOOGLE_SHEET_NAME: {'✅ Configurado' if settings.GOOGLE_SHEET_NAME else '❌ Não configurado'}")
    print(f"GOOGLE_SERVICE_ACCOUNT_JSON: {'✅ Configurado' if settings.GOOGLE_SERVICE_ACCOUNT_JSON else '❌ Não configurado'}")
