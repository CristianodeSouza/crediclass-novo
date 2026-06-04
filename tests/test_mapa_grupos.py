import unittest
from unittest.mock import patch

from backend.main import grupo_detalhe, grupos, reload_data
from backend.sheets_client import get_grupo as sheets_get_grupo
from backend.sheets_client import build_historico, clean_text, parse_credit, row_to_grupo, row_to_grupo_detalhe


class MapaGruposTest(unittest.TestCase):
    def test_row_to_grupo_uses_header_names(self):
        row = {
            "Administradora": "Itau Consorcios",
            "Grupo": "128",
            "Tipo de Bem": "Imovel",
            "Credito Minimo": "100.000,00",
            "Credito Maximo": "1.000.000,00",
            "Taxa Administracao": "20%",
            "Prazo Total": "222",
            "Primeira Assembleia": "2023-03-15",
            "Ultima Assembleia": "2041-03-15",
            "Status": "Ativo",
        }

        result = row_to_grupo(row)

        self.assertEqual(result["grupo_id"], "ITAU-CONSORCIOS-128-IMOVEL")
        self.assertEqual(result["credito_minimo"], 100000)
        self.assertEqual(result["credito_maximo"], 1000000)
        self.assertEqual(result["taxa_adm"], 0.2)
        self.assertEqual(result["prazo_total"], 222)

    def test_row_to_grupo_accepts_sheet_header_variations(self):
        row = {
            "Consorciadora": "Porto Seguro",
            "Grup0": "901",
            "Segmento": "Imovel",
            "Carta Minima": "200.000,00",
            "Carta Maxima": "800.000,00",
            "Taxa Adm Original": "18%",
            "Prazo do Grupo": "180",
            "Status": "Ativo",
        }

        result = row_to_grupo(row)

        self.assertEqual(result["grupo_id"], "PORTO-SEGURO-901-IMOVEL")
        self.assertEqual(result["administradora"], "Porto Seguro")
        self.assertEqual(result["grupo"], "901")
        self.assertEqual(result["tipo_bem"], "Imovel")
        self.assertEqual(result["credito_minimo"], 200000)
        self.assertEqual(result["credito_maximo"], 800000)
        self.assertEqual(result["taxa_adm"], 0.18)

    def test_text_and_credit_sanitization(self):
        self.assertEqual(clean_text("ImÃ³vel"), "Imóvel")
        self.assertIsNone(parse_credit("33.066.216.206.100.000,00"))
        self.assertEqual(parse_credit("247.868,04"), 247868.04)

    def test_row_to_grupo_detalhe_builds_history(self):
        row = {
            "Administradora": "Itau",
            "Grupo": "128",
            "Tipo de Bem": "Imovel",
            "Credito Maximo": "1.000.000,00",
            "Taxa Administracao": "20%",
            "Fundo Reserva": "3%",
            "Prazo Total": "222",
            "Prazo Restante": "180",
            "Seguro Garantia": "Sim",
            "Meia Parcela": "Nao",
            "JAN-26 Maior Lance": "72%",
            "JAN-26 Menor Lance": "24%",
            "JAN-26 Qtd": "12",
        }

        result = row_to_grupo_detalhe(row)

        self.assertEqual(result["fundo_reserva"], 0.03)
        self.assertEqual(result["prazo_restante"], 180)
        self.assertTrue(result["seguro_garantia"])
        self.assertFalse(result["meia_parcela"])
        self.assertEqual(result["historico"]["2026-01"]["maior_lance"], 0.72)
        self.assertEqual(result["historico"]["2026-01"]["qtd_contemplacoes"], 12)

    def test_grupos_endpoint_filters_and_paginates(self):
        fake_items = [
            {
                "grupo_id": "ITAU-128-IMOVEL",
                "administradora": "Itau",
                "grupo": "128",
                "tipo_bem": "Imovel",
                "credito_minimo": 100000,
                "credito_maximo": 1000000,
                "taxa_adm": 0.2,
                "prazo_total": 222,
                "primeira_assembleia": "2023-03-15",
                "ultima_assembleia": "2041-03-15",
                "status": "Ativo",
            },
            {
                "grupo_id": "CNP-017-IMOVEL",
                "administradora": "CNP",
                "grupo": "017",
                "tipo_bem": "Imovel",
                "credito_minimo": 50000,
                "credito_maximo": 300000,
                "taxa_adm": 0.18,
                "prazo_total": 180,
                "primeira_assembleia": "2024-01-20",
                "ultima_assembleia": "2039-01-20",
                "status": "Ativo",
            },
        ]

        with patch("backend.main.list_grupos", return_value=fake_items):
            result = grupos(administradora="Itau", page=1, page_size=10)

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["grupo_id"], "ITAU-128-IMOVEL")

    def test_grupo_detalhe_endpoint_returns_item(self):
        fake_item = {
            "grupo_id": "ITAU-128-IMOVEL",
            "administradora": "Itau",
            "grupo": "128",
            "tipo_bem": "Imovel",
            "credito_minimo": 100000,
            "credito_maximo": 1000000,
            "taxa_adm": 0.2,
            "prazo_total": 222,
            "primeira_assembleia": "2023-03-15",
            "ultima_assembleia": "2041-03-15",
            "status": "Ativo",
            "fundo_reserva": 0.03,
            "prazo_restante": 180,
            "data_termino": "2041-03-15",
            "seguro_garantia": True,
            "meia_parcela": False,
            "lance_embutido": True,
            "fgts": True,
            "categoria": "Premium",
            "percentual_lance_embutido": 0.3,
            "percentual_lance_fixo": 0.25,
            "parcela_reduzida": "30%",
            "indice_correcao": "INCC",
            "vencimento_parcela": "10",
            "vencimento_lance": "8",
            "regras_especiais": "",
            "cadastrado_por": "Larissa",
            "ultima_atualizacao": "2026-06-04",
            "historico": {"2026-01": {"maior_lance": 0.72, "menor_lance": 0.24, "qtd_contemplacoes": 12}},
            "auditoria": [],
        }

        with patch("backend.main.get_grupo", return_value=fake_item):
            result = grupo_detalhe("ITAU-128-IMOVEL")

        self.assertEqual(result["grupo_id"], "ITAU-128-IMOVEL")
        self.assertEqual(result["historico"]["2026-01"]["menor_lance"], 0.24)

    def test_reload_endpoint_clears_cache_and_returns_total(self):
        fake_rows = [
            {"Administradora": "Itau", "Grupo": "128"},
            {"Administradora": "CNP", "Grupo": "017"},
        ]

        with patch("backend.main.clear_rows_cache") as clear_cache, patch("backend.main.read_sheet_rows", return_value=fake_rows):
            result = reload_data()

        clear_cache.assert_called_once()
        self.assertEqual(result["success"], True)
        self.assertEqual(result["total"], 2)

    def test_sheets_get_grupo_uses_detail_listing(self):
        fake_detail = {
            "grupo_id": "ITAU-128-IMOVEL",
            "administradora": "Itau",
            "grupo": "128",
            "tipo_bem": "Imovel",
        }

        with patch("backend.sheets_client.list_grupos_detalhe", return_value=[fake_detail]) as list_details:
            result = sheets_get_grupo("ITAU-128-IMOVEL")

        list_details.assert_called_once()
        self.assertEqual(result["grupo_id"], "ITAU-128-IMOVEL")


if __name__ == "__main__":
    unittest.main()
