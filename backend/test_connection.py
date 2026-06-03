#!/usr/bin/env python3
"""
Script de teste para validar conexão com Google Sheets
Execute: python test_connection.py
"""

import sys
from config import settings
from sheets import get_service, get_headers, read_all_rows, find_group_row

def test_configuration():
    """Verifica se as variáveis de ambiente estão configuradas"""
    print("\n" + "="*70)
    print("TESTE 1: CONFIGURAÇÃO")
    print("="*70)

    checks = {
        "GOOGLE_SHEETS_ID": settings.GOOGLE_SHEETS_ID,
        "GOOGLE_SHEET_NAME": settings.GOOGLE_SHEET_NAME,
        "GOOGLE_SERVICE_ACCOUNT_JSON": settings.GOOGLE_SERVICE_ACCOUNT_JSON[:50] + "..." if settings.GOOGLE_SERVICE_ACCOUNT_JSON else None,
    }

    all_ok = True
    for var, value in checks.items():
        status = "✅" if value else "❌"
        print(f"{status} {var}: {value if value else 'NÃO CONFIGURADO'}")
        if not value:
            all_ok = False

    return all_ok

def test_authentication():
    """Testa autenticação na Google Sheets API"""
    print("\n" + "="*70)
    print("TESTE 2: AUTENTICAÇÃO")
    print("="*70)

    service = get_service()
    if service:
        print("✅ Autenticação bem-sucedida!")
        return True
    else:
        print("❌ Falha na autenticação")
        return False

def test_headers():
    """Testa leitura de headers"""
    print("\n" + "="*70)
    print("TESTE 3: LEITURA DE HEADERS")
    print("="*70)

    headers = get_headers()
    if headers:
        print(f"✅ {len(headers)} colunas carregadas:")
        for i, header in enumerate(headers[:10], 1):
            print(f"   {i}. {header}")
        if len(headers) > 10:
            print(f"   ... e mais {len(headers) - 10} colunas")
        return True
    else:
        print("❌ Nenhum header carregado")
        return False

def test_data():
    """Testa leitura de dados"""
    print("\n" + "="*70)
    print("TESTE 4: LEITURA DE DADOS")
    print("="*70)

    rows = read_all_rows()
    if rows:
        print(f"✅ {len(rows)} linhas carregadas")
        print("\nPrimeira linha de exemplo:")
        first_row = rows[0]
        for i, (key, value) in enumerate(list(first_row.items())[:5], 1):
            print(f"   {key}: {value}")
        return True
    else:
        print("❌ Nenhuma linha carregada")
        return False

def test_find_group():
    """Testa busca de grupo"""
    print("\n" + "="*70)
    print("TESTE 5: BUSCA DE GRUPO")
    print("="*70)

    rows = read_all_rows()
    if not rows:
        print("⚠️  Nenhuma linha para testar")
        return False

    # Tentar encontrar primeiro grupo
    first_row = rows[0]
    admin = first_row.get('Administradora', '').strip()
    grupo = first_row.get('Grupo', '').strip()

    if not admin or not grupo:
        print("⚠️  Primeiro grupo não tem Administradora ou Grupo")
        return False

    grupo_id = f"{admin}-{grupo}"
    print(f"Buscando: {grupo_id}")

    result = find_group_row(grupo_id)
    if result:
        print(f"✅ Grupo encontrado!")
        return True
    else:
        print(f"❌ Grupo não encontrado")
        return False

def main():
    """Executa todos os testes"""
    print("\n")
    print("█" * 70)
    print("TESTES DE CONEXÃO - ETAPA 2")
    print("█" * 70)

    results = []

    # Teste 1
    results.append(("Configuração", test_configuration()))

    # Teste 2
    if results[0][1]:  # Se config OK
        results.append(("Autenticação", test_authentication()))
    else:
        print("\n⚠️  Pulando autenticação (configure variáveis de ambiente)")
        results.append(("Autenticação", False))

    # Testes 3-5
    if results[1][1]:  # Se autenticação OK
        results.append(("Headers", test_headers()))
        results.append(("Dados", test_data()))
        results.append(("Busca", test_find_group()))

    # Resumo
    print("\n" + "="*70)
    print("RESUMO DOS TESTES")
    print("="*70)

    for name, passed in results:
        status = "✅ PASSOU" if passed else "❌ FALHOU"
        print(f"{name}: {status}")

    passed_count = sum(1 for _, p in results if p)
    total_count = len(results)

    print(f"\nTotal: {passed_count}/{total_count} testes passaram")

    if passed_count == total_count:
        print("\n✅ ETAPA 2 CONCLUÍDA COM SUCESSO!")
        print("   Backend consegue ler a Google Sheets")
        return 0
    else:
        print("\n❌ Alguns testes falharam")
        print("   Verifique as configurações no arquivo .env")
        return 1

if __name__ == "__main__":
    sys.exit(main())
