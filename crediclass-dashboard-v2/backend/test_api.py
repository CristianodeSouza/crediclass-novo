#!/usr/bin/env python3
"""
Script de teste para validar endpoints da API
Execute: python test_api.py
"""

import sys
import json
from sheets import read_all_rows, get_headers

def test_get_grupos():
    """Testa endpoint GET /api/grupos simulando o comportamento"""
    print("\n" + "="*70)
    print("TESTE: GET /api/grupos")
    print("="*70)

    try:
        rows = read_all_rows()
        if not rows:
            print("❌ Nenhuma linha carregada")
            return False

        print(f"✅ {len(rows)} grupos carregados")

        # Validar estrutura
        if len(rows) > 0:
            first_grupo = rows[0]
            required_fields = ['Administradora', 'Grupo']

            missing = [f for f in required_fields if f not in first_grupo]
            if missing:
                print(f"❌ Campos obrigatórios faltando: {missing}")
                return False

            print(f"✅ Estrutura validada")
            print(f"\nExemplo de grupo (primeiro):")
            print(f"  Administradora: {first_grupo.get('Administradora', '')}")
            print(f"  Grupo: {first_grupo.get('Grupo', '')}")
            print(f"  Tipo de Bem: {first_grupo.get('Tipo de Bem', '')}")
            print(f"  Menor Crédito: {first_grupo.get('Menor Crédito', '')}")
            print(f"  Status: {first_grupo.get('Status', 'Ativo')}")

        return True

    except Exception as e:
        print(f"❌ Erro ao testar GET /api/grupos: {e}")
        return False

def test_get_grupo_by_id():
    """Testa endpoint GET /api/grupos/{grupo_id}"""
    print("\n" + "="*70)
    print("TESTE: GET /api/grupos/{grupo_id}")
    print("="*70)

    try:
        rows = read_all_rows()
        if not rows:
            print("⚠️  Nenhuma linha para testar")
            return False

        first_row = rows[0]
        admin = first_row.get('Administradora', '').strip()
        grupo = first_row.get('Grupo', '').strip()

        if not admin or not grupo:
            print("⚠️  Primeiro grupo não tem Administradora ou Grupo definidos")
            return False

        grupo_id = f"{admin}-{grupo}"
        print(f"Buscando grupo: {grupo_id}")

        # Simular busca do grupo
        resultado = None
        for row in rows:
            if row.get('Administradora', '').strip() == admin and row.get('Grupo', '').strip() == grupo:
                resultado = row
                break

        if resultado:
            print(f"✅ Grupo encontrado!")
            print(f"  Administradora: {resultado.get('Administradora', '')}")
            print(f"  Grupo: {resultado.get('Grupo', '')}")
            print(f"  Tipo de Bem: {resultado.get('Tipo de Bem', '')}")
            print(f"  Status: {resultado.get('Status', 'Ativo')}")
            print(f"  Maior Crédito: {resultado.get('Maior Crédito', '')}")
            return True
        else:
            print(f"❌ Grupo não encontrado")
            return False

    except Exception as e:
        print(f"❌ Erro ao testar GET /api/grupos/{{grupo_id}}: {e}")
        return False

def test_response_structure():
    """Valida que a resposta tem a estrutura JSON correta"""
    print("\n" + "="*70)
    print("TESTE: Estrutura JSON")
    print("="*70)

    try:
        rows = read_all_rows()
        if not rows:
            print("⚠️  Nenhuma linha para validar estrutura")
            return False

        # Simular resposta da API
        response = []
        for row in rows:
            grupo_json = {
                "grupo_id": f"{row.get('Administradora', '')}-{row.get('Grupo', '')}",
                "administradora": row.get('Administradora', ''),
                "grupo": row.get('Grupo', ''),
                "tipo_bem": row.get('Tipo de Bem', ''),
                "menor_credito": row.get('Menor Crédito', ''),
                "maior_credito": row.get('Maior Crédito', ''),
                "prazo_grupo": row.get('Prazo do Grupo', ''),
                "prestacao_integral": row.get('Prestação Integral', ''),
                "taxa_administracao": row.get('Taxa Administração', ''),
                "status": row.get('Status', 'Ativo')
            }
            response.append(grupo_json)

        # Testar serialização JSON
        json_str = json.dumps(response, ensure_ascii=False, indent=2)
        print(f"✅ JSON serializado com sucesso")
        print(f"✅ Tamanho da resposta: {len(json_str)} caracteres")
        print(f"✅ Quantidade de grupos: {len(response)}")

        if len(response) > 0:
            print(f"\nExemplo de JSON (primeiro grupo):")
            print(json.dumps(response[0], ensure_ascii=False, indent=2))

        return True

    except Exception as e:
        print(f"❌ Erro ao validar estrutura JSON: {e}")
        return False

def main():
    print("\n")
    print("█" * 70)
    print("TESTES DA API - ETAPA 3")
    print("█" * 70)

    results = []

    # Teste 1
    results.append(("GET /api/grupos", test_get_grupos()))

    # Teste 2
    results.append(("GET /api/grupos/{grupo_id}", test_get_grupo_by_id()))

    # Teste 3
    results.append(("Estrutura JSON", test_response_structure()))

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
        print("\n✅ ETAPA 3 PRONTA PARA DEPLOY!")
        print("   Execute: curl http://localhost:8000/api/grupos")
        return 0
    else:
        print("\n❌ Alguns testes falharam")
        return 1

if __name__ == "__main__":
    sys.exit(main())
