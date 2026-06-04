import unittest
from unittest.mock import patch

from backend.main import viabilidade_analisar
from backend.models import ViabilidadeRequest
from backend.viabilidade import analyze_viabilidade, classify_profile


class ViabilidadeTest(unittest.TestCase):
    def test_classify_profile_by_prazo(self):
        self.assertEqual(classify_profile(3)[0], "Super Agressivo")
        self.assertEqual(classify_profile(6)[0], "Agressivo")
        self.assertEqual(classify_profile(12)[0], "Moderado")
        self.assertEqual(classify_profile(24)[0], "Conservador")
        self.assertEqual(classify_profile(36)[0], "Investidor")

    def test_analyze_filters_and_orders_groups(self):
        payload = ViabilidadeRequest(
            objetivo="Aquisicao de Imovel",
            credito_desejado=500000,
            prazo_desejado=12,
            lance_proprio=100000,
            fgts=50000,
            renda_total=25000,
            parcela_desejada=4500,
            data_nascimento="1985-01-01",
        )
        groups = [
            {
                "grupo_id": "ITAU-128-IMOVEL",
                "administradora": "Itau",
                "grupo": "128",
                "tipo_bem": "Imovel",
                "credito_maximo": 1000000,
                "taxa_adm": 0.2,
                "fundo_reserva": 0.03,
                "prazo_total": 222,
                "prazo_restante": 180,
                "percentual_lance_embutido": 0.3,
                "moderado": 0.25,
                "status": "Ativo",
                "historico": {"2026-01": {"menor_lance": 0.24, "qtd_contemplacoes": 5}},
            },
            {
                "grupo_id": "AUTO-001",
                "administradora": "Auto",
                "grupo": "001",
                "tipo_bem": "Auto",
                "credito_maximo": 900000,
                "prazo_total": 100,
                "prazo_restante": 100,
                "status": "Ativo",
                "historico": {},
            },
            {
                "grupo_id": "OLD-001-IMOVEL",
                "administradora": "Old",
                "grupo": "001",
                "tipo_bem": "Imovel",
                "credito_maximo": 900000,
                "prazo_total": 100,
                "prazo_restante": 0,
                "status": "Ativo",
                "historico": {},
            },
        ]

        result = analyze_viabilidade(payload, groups)

        self.assertEqual(result["total_grupos_encontrados"], 1)
        self.assertEqual(result["perfil"], "Moderado")
        self.assertEqual(result["melhores_grupos"][0]["grupo_id"], "ITAU-128-IMOVEL")
        self.assertEqual(result["melhores_grupos"][0]["ranking"], 1)
        self.assertTrue(result["checklist"]["cenario_viavel"])

    def test_endpoint_uses_sheets_and_returns_response(self):
        payload = ViabilidadeRequest(
            objetivo="Aquisicao de Imovel",
            credito_desejado=300000,
            prazo_desejado=24,
            lance_proprio=60000,
            fgts=20000,
            renda_total=20000,
            parcela_desejada=2500,
        )
        fake_groups = [
            {
                "grupo_id": "CNP-017-IMOVEL",
                "administradora": "CNP",
                "grupo": "017",
                "tipo_bem": "Imovel",
                "credito_maximo": 500000,
                "taxa_adm": 0.18,
                "fundo_reserva": 0.02,
                "prazo_total": 180,
                "prazo_restante": 150,
                "percentual_lance_embutido": 0.2,
                "conservador": 0.2,
                "status": "Ativo",
                "historico": {},
            }
        ]

        with patch("backend.main.list_grupos_detalhe", return_value=fake_groups):
            result = viabilidade_analisar(payload)

        self.assertEqual(result["total_grupos_encontrados"], 1)
        self.assertEqual(result["melhores_grupos"][0]["administradora"], "CNP")


if __name__ == "__main__":
    unittest.main()
