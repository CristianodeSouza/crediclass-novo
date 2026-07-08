import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from backend.main import grupo_detalhe, grupo_historico_atualizar, grupo_historico_lote_atualizar, grupos, grupos_exportar_planilha, reload_data
from backend.models import GrupoCreateRequest, GrupoUpdateRequest, HistoricoBatchUpdateRequest, HistoricoUpdateRequest
from backend import sheets_client
from backend.defasagem import build_defasagem_report, update_defasagem_task
from backend.sheets_client import get_grupo as sheets_get_grupo
from backend.sheets_client import build_historico, clean_text, create_grupo, delete_grupo, format_history_value, parse_credit, payload_to_row_values, row_to_grupo, row_to_grupo_detalhe, update_grupo, update_historico_mensal


class MapaGruposTest(unittest.TestCase):
    def test_defasagem_calcula_meses_pendentes_e_ordena_prioridade(self):
        groups = [
            {
                "grupo_id": "128",
                "administradora": "Itau",
                "grupo": "128",
                "tipo_bem": "Imovel",
                "status": "Ativo",
                "historico": {
                    "2025-12": {"maior_lance": 0.62, "menor_lance": 0.58, "qtd_contemplacoes": 4},
                    "2026-01": {"maior_lance": None, "menor_lance": None, "qtd_contemplacoes": None},
                },
            },
            {
                "grupo_id": "1025",
                "administradora": "Caixa",
                "grupo": "1025",
                "tipo_bem": "Imovel",
                "status": "Ativo",
                "historico": {
                    "2026-06": {"maior_lance": 0.52, "menor_lance": 0.5, "qtd_contemplacoes": 2},
                },
            },
        ]

        with TemporaryDirectory() as temp_dir:
            with patch("backend.defasagem.DEFASAGEM_FILE", Path(temp_dir) / "defasagem.json"):
                report = build_defasagem_report(groups, today=date(2026, 6, 9))

        self.assertEqual(report["competencia_atual"], "2026-06")
        self.assertEqual(report["total_grupos"], 2)
        self.assertEqual(report["total_atrasados"], 1)
        self.assertEqual(report["total_criticos"], 1)
        self.assertEqual(report["items"][0]["grupo_id"], "128")
        self.assertEqual(report["items"][0]["total_meses_defasados"], 6)
        self.assertEqual(report["items"][0]["meses_pendentes"], ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"])
        self.assertEqual(report["items"][0]["campos_ultima_competencia"], ["maior lance", "menor lance", "contemplacoes"])

    def test_defasagem_salva_checklist_operacional(self):
        with TemporaryDirectory() as temp_dir:
            with patch("backend.defasagem.DEFASAGEM_FILE", Path(temp_dir) / "defasagem.json"):
                task = update_defasagem_task("128", {"concluido": True, "observacao": "Atualizar jan a jun"}, operador="larissa")
                report = build_defasagem_report([
                    {
                        "grupo_id": "128",
                        "administradora": "Itau",
                        "grupo": "128",
                        "tipo_bem": "Imovel",
                        "status": "Ativo",
                        "historico": {"2025-12": {"maior_lance": 0.62}},
                    }
                ], today=date(2026, 6, 9))

        self.assertTrue(task["concluido"])
        self.assertEqual(report["items"][0]["status_defasagem"], "marcado_para_conferencia")
        self.assertEqual(report["items"][0]["observacao"], "Atualizar jan a jun")
        self.assertEqual(report["items"][0]["operador"], "larissa")

    def test_defasagem_considera_mes_atualizado_somente_com_tres_campos(self):
        groups = [
            {
                "grupo_id": "1038",
                "administradora": "Caixa",
                "grupo": "1038",
                "tipo_bem": "Imovel",
                "status": "Ativo",
                "historico": {
                    "2026-03": {"maior_lance": 0.71, "menor_lance": 0.70, "qtd_contemplacoes": 4},
                    "2026-04": {"maior_lance": 0.70, "menor_lance": None, "qtd_contemplacoes": 2},
                },
            }
        ]

        with TemporaryDirectory() as temp_dir:
            with patch("backend.defasagem.DEFASAGEM_FILE", Path(temp_dir) / "defasagem.json"):
                report = build_defasagem_report(groups, today=date(2026, 6, 9))

        item = report["items"][0]
        self.assertEqual(item["ultima_competencia"], "2026-03")
        self.assertEqual(item["meses_pendentes"], ["2026-04", "2026-05", "2026-06"])
        self.assertEqual(item["total_meses_defasados"], 3)

    def test_grupos_detalhados_usam_cache_e_preservam_copia(self):
        sheets_client.clear_rows_cache()
        row = {
            "Administradora": "Itau",
            "Grupo": "128",
            "Tipo de Bem": "Imovel",
            "Credito Minimo": "100.000,00",
            "Credito Maximo": "500.000,00",
            "Prazo Total": "180",
            "Status": "Ativo",
        }

        with patch("backend.sheets_client.read_sheet_rows", return_value=[row]) as read_rows:
            first = sheets_client.list_grupos_detalhe()
            first[0]["administradora"] = "Alterado"
            second = sheets_client.list_grupos_detalhe()

        self.assertEqual(read_rows.call_count, 1)
        self.assertEqual(second[0]["administradora"], "Itau")

    def test_limpeza_de_cache_invalida_grupos_detalhados(self):
        sheets_client.clear_rows_cache()
        first_row = {
            "Administradora": "Itau",
            "Grupo": "128",
            "Tipo de Bem": "Imovel",
            "Credito Maximo": "500.000,00",
            "Prazo Total": "180",
            "Status": "Ativo",
        }
        second_row = {
            "Administradora": "Caixa",
            "Grupo": "1025",
            "Tipo de Bem": "Imovel",
            "Credito Maximo": "600.000,00",
            "Prazo Total": "200",
            "Status": "Ativo",
        }

        with patch("backend.sheets_client.read_sheet_rows", side_effect=[[first_row], [second_row]]) as read_rows:
            self.assertEqual(sheets_client.list_grupos_detalhe()[0]["administradora"], "Itau")
            sheets_client.clear_rows_cache()
            self.assertEqual(sheets_client.list_grupos_detalhe()[0]["administradora"], "Caixa")

        self.assertEqual(read_rows.call_count, 2)

    def test_row_blocks_agrupa_linhas_proximas(self):
        self.assertEqual(sheets_client.row_blocks([3, 4, 6, 10, 14], max_gap=1), [(3, 6), (10, 10), (14, 14)])

    def test_read_summary_rows_com_historico_usa_intervalo_continuo(self):
        sheets_client.clear_rows_cache()
        headers = [""] * 65
        headers[0] = "ADM"
        headers[1] = "Grupo"
        headers[2] = "Tipo de Bem"
        headers[17] = "Credito Maximo"
        headers[62] = "Agressivo"
        headers[63] = "JAN-26 Menor Lance"
        headers[64] = "JAN-26 Qtd"
        row = [""] * 65
        row[0] = "Itau"
        row[1] = "128"
        row[2] = "Imovel"
        row[17] = "500000"
        row[62] = "18"
        row[63] = "24"
        row[64] = "12"

        class ExecuteMock:
            def execute(self):
                return {"values": [row]}

        class ValuesMock:
            def get(self, **kwargs):
                self.get_kwargs = kwargs
                return ExecuteMock()

        class ServiceMock:
            def __init__(self):
                self.values_api = ValuesMock()

            def spreadsheets(self):
                return self

            def values(self):
                return self.values_api

        service = ServiceMock()
        settings = SimpleNamespace(google_sheets_id="sheet-id", google_sheet_name="Grupos")
        with (
            patch("backend.sheets_client.read_sheet_headers", return_value=headers),
            patch("backend.sheets_client.get_service", return_value=service),
            patch("backend.sheets_client.get_settings", return_value=settings),
        ):
            rows = sheets_client.read_summary_rows(include_history=True)

        self.assertEqual(rows[0]["JAN-26 Menor Lance"], "24")
        self.assertEqual(service.values_api.get_kwargs["range"], "'Grupos'!A2:BM")

    def test_read_summary_rows_usa_colunas_fixas_do_mapa_de_grupos(self):
        sheets_client.clear_rows_cache()
        headers = [f"Coluna {index}" for index in range(63)]
        headers[0] = "ADM"
        headers[1] = "Grupo"
        headers[2] = "Tipo de Bem"
        row = [""] * 63
        row[0] = "PORTO"
        row[1] = "1136"
        row[2] = "Imovel"
        row[5] = "14"
        row[17] = "600.000,00"
        row[18] = "18%"
        row[59] = "10%"
        row[60] = "20%"
        row[61] = "30%"
        row[62] = "40%"

        class ExecuteMock:
            def execute(self):
                return {"values": [row]}

        class ValuesMock:
            def get(self, **kwargs):
                self.get_kwargs = kwargs
                return ExecuteMock()

        class ServiceMock:
            def __init__(self):
                self.values_api = ValuesMock()

            def spreadsheets(self):
                return self

            def values(self):
                return self.values_api

        service = ServiceMock()
        settings = SimpleNamespace(google_sheets_id="sheet-id", google_sheet_name="Grupos")
        with (
            patch("backend.sheets_client.read_sheet_headers", return_value=headers),
            patch("backend.sheets_client.get_service", return_value=service),
            patch("backend.sheets_client.get_settings", return_value=settings),
        ):
            grupo = row_to_grupo(sheets_client.read_summary_rows(include_history=True)[0])

        self.assertEqual(grupo["administradora"], "PORTO")
        self.assertEqual(grupo["grupo"], "1136")
        self.assertEqual(grupo["tipo_bem"], "Imovel")
        self.assertEqual(grupo["prazo_restante"], 14)
        self.assertEqual(grupo["credito_maximo"], 600000)
        self.assertEqual(grupo["taxa_adm"], 0.18)
        self.assertEqual(grupo["lance_super_conservador"], 0.1)
        self.assertEqual(grupo["lance_conservador"], 0.2)
        self.assertEqual(grupo["lance_moderado"], 0.3)
        self.assertEqual(grupo["lance_agressivo"], 0.4)

    def test_percentuais_de_historico_nao_gravam_residuos_decimais(self):
        self.assertEqual(format_history_value("maior_lance", 0.56), "56,0")
        self.assertEqual(format_history_value("menor_lance", 0.5256000000000001), "52,56")
        self.assertEqual(format_history_value("maior_lance", 0.5550000000000001), "55,5")

    def test_grupo_aceita_campos_vazios_e_valores_zero(self):
        create_payload = GrupoCreateRequest(credito_minimo=0, credito_maximo=0, taxa_adm=0, prazo_total=0)
        update_payload = GrupoUpdateRequest(credito_minimo=0, credito_maximo=0, taxa_adm=0, prazo_total=0)

        self.assertEqual(create_payload.administradora, "")
        self.assertEqual(create_payload.grupo, "")
        self.assertEqual(create_payload.credito_maximo, 0)
        self.assertEqual(update_payload.credito_maximo, 0)

    def test_row_to_grupo_uses_header_names(self):
        row = {
            "ADM": "Itau Consorcios",
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

        self.assertEqual(result["grupo_id"], "128")
        self.assertEqual(result["administradora"], "Itau Consorcios")
        self.assertEqual(result["credito_minimo"], 100000)
        self.assertEqual(result["credito_maximo"], 1000000)
        self.assertEqual(result["taxa_adm"], 0.2)
        self.assertEqual(result["prazo_total"], 222)

    def test_row_to_grupo_expoe_lances_de_referencia_do_historico(self):
        row = {
            "ADM": "Itau Consorcios",
            "Grupo": "128",
            "Tipo de Bem": "Imovel",
            "JAN-26 Menor Lance": "48%",
            "JAN-26 Qtd Contemplacoes": "3",
            "FEV-26 Menor Lance": "41%",
            "FEV-26 Qtd Contemplacoes": "2",
            "MAR-26 Menor Lance": "43%",
            "MAR-26 Qtd Contemplacoes": "1",
            "ABR-26 Menor Lance": "50%",
            "ABR-26 Qtd Contemplacoes": "2",
            "MAI-26 Menor Lance": "52%",
            "MAI-26 Qtd Contemplacoes": "1",
            "JUN-26 Menor Lance": "",
            "JUN-26 Qtd Contemplacoes": "",
        }

        result = row_to_grupo(row)

        self.assertEqual(result["lance_agressivo"], 0.5225)
        self.assertEqual(result["lance_moderado"], 0.4325)
        self.assertEqual(result["lance_conservador"], 0.4325)
        self.assertEqual(result["lance_super_conservador"], 0.4325)

    def test_row_to_grupo_prioriza_lances_diretos_da_planilha(self):
        row = {
            "__lance_super_conservador": "11%",
            "__lance_conservador": "22%",
            "__lance_moderado": "33%",
            "__lance_agressivo": "44%",
            "JAN-26 Menor Lance": "70%",
            "JAN-26 Qtd Contemplacoes": "3",
        }

        result = row_to_grupo(row)

        self.assertEqual(result["lance_super_conservador"], 0.11)
        self.assertEqual(result["lance_conservador"], 0.22)
        self.assertEqual(result["lance_moderado"], 0.33)
        self.assertEqual(result["lance_agressivo"], 0.44)

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

        self.assertEqual(result["grupo_id"], "901")
        self.assertEqual(result["administradora"], "Porto Seguro")
        self.assertEqual(result["grupo"], "901")
        self.assertEqual(result["tipo_bem"], "Imovel")
        self.assertEqual(result["credito_minimo"], 200000)
        self.assertEqual(result["credito_maximo"], 800000)
        self.assertEqual(result["taxa_adm"], 0.18)

    def test_row_to_grupo_accepts_id_grupo_header(self):
        row = {
            "ADM": "Embracon",
            "ID Grupo": "1025",
            "Tipo de Bem": "Imovel",
            "Credito Minimo": "150.000,00",
            "Credito Maximo": "900.000,00",
        }

        result = row_to_grupo(row)

        self.assertEqual(result["grupo_id"], "1025")
        self.assertEqual(result["grupo"], "1025")
        self.assertEqual(result["administradora"], "Embracon")

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
                "grupo_id": "128",
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
                "grupo_id": "017",
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
        self.assertEqual(result["total_administradoras"], 1)
        self.assertEqual(result["administradoras"], ["CNP", "Itau"])
        self.assertEqual(result["tipos_bem"], ["Imovel"])
        self.assertEqual(result["items"][0]["grupo_id"], "128")

    def test_grupos_endpoint_filtra_colunas_de_credito_literalmente(self):
        fake_items = [
            {
                "grupo_id": "fora",
                "administradora": "CAIXA",
                "grupo": "1019",
                "tipo_bem": "Imovel",
                "credito_minimo": 489851.41,
                "credito_maximo": 857239.98,
                "taxa_adm": 0.16,
                "prazo_total": 200,
                "primeira_assembleia": "",
                "ultima_assembleia": "",
                "status": "Ativo",
            },
            {
                "grupo_id": "dentro",
                "administradora": "CAIXA",
                "grupo": "teste",
                "tipo_bem": "Imovel",
                "credito_minimo": 320000,
                "credito_maximo": 480000,
                "taxa_adm": 0.2,
                "prazo_total": 200,
                "primeira_assembleia": "",
                "ultima_assembleia": "",
                "status": "Ativo",
            },
        ]

        with patch("backend.main.list_grupos", return_value=fake_items):
            result = grupos(credito_minimo=300000, credito_maximo=500000, page=1, page_size=25)

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["grupo_id"], "dentro")

    def test_grupos_endpoint_filtra_por_prazo_restante(self):
        fake_items = [
            {
                "grupo_id": "curto",
                "administradora": "PORTO",
                "grupo": "101",
                "tipo_bem": "Imovel",
                "credito_minimo": 100000,
                "credito_maximo": 500000,
                "taxa_adm": 0.2,
                "prazo_total": 200,
                "prazo_restante": 18,
                "primeira_assembleia": "",
                "ultima_assembleia": "",
                "status": "Ativo",
            },
            {
                "grupo_id": "longo",
                "administradora": "PORTO",
                "grupo": "102",
                "tipo_bem": "Imovel",
                "credito_minimo": 100000,
                "credito_maximo": 500000,
                "taxa_adm": 0.2,
                "prazo_total": 200,
                "prazo_restante": 55,
                "primeira_assembleia": "",
                "ultima_assembleia": "",
                "status": "Ativo",
            },
        ]

        with patch("backend.main.list_grupos", return_value=fake_items):
            result = grupos(prazo_minimo=50, page=1, page_size=25)

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["grupo_id"], "longo")

    def test_grupos_endpoint_ordena_lance_antes_da_paginacao(self):
        fake_items = [
            {
                "grupo_id": "baixo",
                "administradora": "CNP",
                "grupo": "101",
                "tipo_bem": "Imovel",
                "credito_minimo": 100000,
                "credito_maximo": 500000,
                "taxa_adm": 0.2,
                "prazo_total": 200,
                "prazo_restante": 80,
                "primeira_assembleia": "",
                "ultima_assembleia": "",
                "status": "Ativo",
                "lance_agressivo": 0.2,
            },
            {
                "grupo_id": "alto",
                "administradora": "CNP",
                "grupo": "102",
                "tipo_bem": "Imovel",
                "credito_minimo": 100000,
                "credito_maximo": 500000,
                "taxa_adm": 0.2,
                "prazo_total": 200,
                "prazo_restante": 80,
                "primeira_assembleia": "",
                "ultima_assembleia": "",
                "status": "Ativo",
                "lance_agressivo": 0.6,
            },
        ]

        with patch("backend.main.list_grupos", return_value=fake_items):
            result = grupos(sort_lance="agressivo", sort_order="desc", page=1, page_size=1)

        self.assertEqual(result["total"], 2)
        self.assertEqual(result["items"][0]["grupo_id"], "alto")

    def test_grupo_detalhe_endpoint_returns_item(self):
        fake_item = {
            "grupo_id": "128",
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
            result = grupo_detalhe("128")

        self.assertEqual(result["grupo_id"], "128")
        self.assertEqual(result["historico"]["2026-01"]["menor_lance"], 0.24)

    def test_reload_endpoint_clears_cache_and_returns_total(self):
        fake_rows = [
            {"Administradora": "Itau", "Grupo": "128"},
            {"Administradora": "CNP", "Grupo": "017"},
        ]

        with patch("backend.main.clear_rows_cache") as clear_cache, patch("backend.main.list_grupos", return_value=fake_rows):
            result = reload_data()

        clear_cache.assert_called_once()
        self.assertEqual(result["success"], True)
        self.assertEqual(result["total"], 2)

    def test_export_sheet_csv_preserva_matriz_da_planilha(self):
        with patch("backend.sheets_client.read_sheet_values", return_value=[["ADM", "Grupo", "Status"], ["ITAU", "128"]]):
            csv_content = sheets_client.export_sheet_csv()

        self.assertEqual(csv_content, "ADM;Grupo;Status\nITAU;128;\n")

    def test_exportar_planilha_devolve_csv_oficial(self):
        with patch("backend.main.export_sheet_csv", return_value="ADM;Grupo;Status\nITAU;128;Ativo\n") as export_sheet:
            response = grupos_exportar_planilha()

        export_sheet.assert_called_once()
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response.media_type)
        self.assertIn("crediclass-planilha-oficial-", response.headers["content-disposition"])
        self.assertTrue(response.body.startswith("\ufeffADM;Grupo;Status".encode("utf-8")))

    def test_sheets_get_grupo_builds_only_matching_row_detail(self):
        headers = ["ADM", "Grupo", "Tipo de Bem", "JAN-26 Maior Lance", "JAN-26 Menor Lance", "JAN-26 Qtd"]

        class ExecuteMock:
            def execute(self):
                return {"values": [["Itau", "128", "Imovel", "72", "24", "12"]]}

        class ValuesMock:
            def get(self, **kwargs):
                self.get_kwargs = kwargs
                return ExecuteMock()

        class ServiceMock:
            def __init__(self):
                self.values_api = ValuesMock()

            def spreadsheets(self):
                return self

            def values(self):
                return self.values_api

        service = ServiceMock()
        settings = SimpleNamespace(google_sheets_id="sheet-id", google_sheet_name="Grupos")
        with (
            patch("backend.sheets_client.read_sheet_headers", return_value=headers),
            patch("backend.sheets_client.get_service", return_value=service),
            patch("backend.sheets_client.get_settings", return_value=settings),
            patch.dict("backend.sheets_client._group_row_index", {"128": 3}, clear=True),
            patch.dict("backend.sheets_client._grupo_detail_cache", {}, clear=True),
        ):
            result = sheets_get_grupo("128")

        self.assertEqual(result["grupo_id"], "128")
        self.assertEqual(result["historico"]["2026-01"]["qtd_contemplacoes"], 12)
        self.assertEqual(service.values_api.get_kwargs["range"], "'Grupos'!A3:F3")

    def test_sheets_lista_detalhes_por_ids_em_lote(self):
        headers = ["ADM", "Grupo", "Tipo de Bem", "Credito Maximo", "Prazo Total", "JAN-26 Maior Lance", "JAN-26 Menor Lance", "JAN-26 Qtd"]

        class ExecuteMock:
            def execute(self):
                return {
                    "valueRanges": [
                        {"values": [["Itau", "128", "Imovel", "500000", "180", "72", "24", "12"]]},
                        {"values": [["Caixa", "1025", "Imovel", "600000", "200", "55", "40", "4"]]},
                    ]
                }

        class ValuesMock:
            def batchGet(self, **kwargs):
                self.batch_get_kwargs = kwargs
                return ExecuteMock()

        class ServiceMock:
            def __init__(self):
                self.values_api = ValuesMock()

            def spreadsheets(self):
                return self

            def values(self):
                return self.values_api

        service = ServiceMock()
        settings = SimpleNamespace(google_sheets_id="sheet-id", google_sheet_name="Grupos")
        with (
            patch("backend.sheets_client.list_grupos", return_value=[]),
            patch("backend.sheets_client.read_sheet_headers", return_value=headers),
            patch("backend.sheets_client.get_service", return_value=service),
            patch("backend.sheets_client.get_settings", return_value=settings),
            patch.dict("backend.sheets_client._group_row_index", {"128": 3, "1025": 8}, clear=True),
            patch.dict("backend.sheets_client._grupo_detail_cache", {}, clear=True),
        ):
            result = sheets_client.list_grupos_detalhe_by_ids(["128", "1025"])

        self.assertEqual([item["grupo_id"] for item in result], ["128", "1025"])
        self.assertEqual(service.values_api.batch_get_kwargs["ranges"], ["'Grupos'!A3:H3", "'Grupos'!A8:H8"])

    def test_payload_to_row_values_uses_headers_not_positions(self):
        headers = ["ADM", "Tipo de Bem", "Grup0", "Menor\nCredito", "Maior\nCredito", "Taxa\nAdm Original", "Prazo\nGrupo"]

        values = payload_to_row_values(headers, {
            "administradora": "Crediclass",
            "grupo": "777",
            "tipo_bem": "Imovel",
            "credito_minimo": 100000,
            "credito_maximo": 500000,
            "taxa_adm": 0.2,
            "prazo_total": 180,
        })

        self.assertEqual(values[0], "Crediclass")
        self.assertEqual(values[1], "Imovel")
        self.assertEqual(values[2], "777")
        self.assertEqual(values[5], "20,0")

    def test_create_update_delete_grupo_call_google_sheets(self):
        headers = ["ADM", "Grup0", "Tipo de Bem", "Menor\nCredito", "Maior\nCredito", "Taxa\nAdm Original", "Prazo\nGrupo", "Status"]
        values = [headers, ["Crediclass", "128", "Imovel", "100000", "500000", "20", "180", "Ativo"]]

        class ExecuteMock:
            def execute(self):
                return {}

        class ValuesMock:
            def append(self, **kwargs):
                self.append_kwargs = kwargs
                return ExecuteMock()

            def update(self, **kwargs):
                self.update_kwargs = kwargs
                return ExecuteMock()

        class SpreadsheetsMock:
            def __init__(self):
                self.values_mock = ValuesMock()

            def values(self):
                return self.values_mock

        class ServiceMock:
            def __init__(self):
                self.spreadsheets_mock = SpreadsheetsMock()

            def spreadsheets(self):
                return self.spreadsheets_mock

        service = ServiceMock()
        with patch("backend.sheets_client.read_sheet_values", return_value=values), patch("backend.sheets_client.get_service", return_value=service):
            created = create_grupo({
                "administradora": "Crediclass",
                "grupo": "999",
                "tipo_bem": "Imovel",
                "credito_minimo": 200000,
                "credito_maximo": 600000,
                "taxa_adm": 0.18,
                "prazo_total": 180,
                "status": "Excluido",
            })
            updated = update_grupo("128", {"taxa_adm": 0.19})
            deleted = delete_grupo("128")

        appended_row = service.spreadsheets_mock.values_mock.append_kwargs["body"]["values"][0]
        self.assertTrue(created["success"])
        self.assertEqual(appended_row[7], "Excluido")
        self.assertTrue(updated["success"])
        self.assertEqual(deleted["status"], "Excluido")

    def test_update_grupo_accepts_sheet_fields_and_locks_identifiers(self):
        headers = ["ADM", "Grupo", "Tipo de Bem", "Data Termino", "Observacoes", "Credito Maximo"]
        values = [headers, ["ITAU", "128", "Imovel", "5/20/2030", "Antiga", "247868,04"]]

        class ExecuteMock:
            def execute(self):
                return {}

        class ValuesMock:
            def __init__(self):
                self.update_kwargs = None

            def update(self, **kwargs):
                self.update_kwargs = kwargs
                return ExecuteMock()

        class SpreadsheetsMock:
            def __init__(self):
                self.values_mock = ValuesMock()

            def values(self):
                return self.values_mock

        class ServiceMock:
            def __init__(self):
                self.spreadsheets_mock = SpreadsheetsMock()

            def spreadsheets(self):
                return self.spreadsheets_mock

        service = ServiceMock()
        payload = {
            "campos_planilha": {
                "ADM": "CAIXA",
                "Grupo": "999",
                "Data Termino": "6/20/2031",
                "Observacoes": "",
                "Credito Maximo": "",
            }
        }
        with patch("backend.sheets_client.read_sheet_values", return_value=values), patch("backend.sheets_client.get_service", return_value=service):
            result = update_grupo("128", payload)

        updated_row = service.spreadsheets_mock.values_mock.update_kwargs["body"]["values"][0]
        self.assertTrue(result["success"])
        self.assertEqual(updated_row[0], "ITAU")
        self.assertEqual(updated_row[1], "128")
        self.assertEqual(updated_row[3], "6/20/2031")
        self.assertEqual(updated_row[4], "")
        self.assertEqual(updated_row[5], "")

    def test_update_historico_mensal_uses_existing_month_headers(self):
        headers = ["ADM", "Grupo", "Tipo de Bem", "JAN-26 Maior Lance", "JAN-26 Menor Lance", "JAN-26 Qtd"]
        values = [headers, ["Itau", "128", "Imovel", "70", "20", "5"]]

        class ExecuteMock:
            def execute(self):
                return {}

        class ValuesMock:
            def __init__(self):
                self.batch_update_kwargs = None

            def batchUpdate(self, **kwargs):
                self.batch_update_kwargs = kwargs
                return ExecuteMock()

        class SpreadsheetsMock:
            def __init__(self):
                self.values_mock = ValuesMock()

            def values(self):
                return self.values_mock

        class ServiceMock:
            def __init__(self):
                self.spreadsheets_mock = SpreadsheetsMock()

            def spreadsheets(self):
                return self.spreadsheets_mock

        service = ServiceMock()
        with patch("backend.sheets_client.read_sheet_values", return_value=values), patch("backend.sheets_client.get_service", return_value=service):
            result = update_historico_mensal("128", {
                "mes": "2026-01",
                "maior_lance": 0.72,
                "menor_lance": 0.24,
                "qtd_contemplacoes": 12,
            })

        updates = service.spreadsheets_mock.values_mock.batch_update_kwargs["body"]["data"]
        self.assertTrue(result["success"])
        self.assertEqual(updates[0], {"range": "'Tabela de Grupos 3.0'!D2", "values": [["72,0"]]})
        self.assertEqual(updates[1], {"range": "'Tabela de Grupos 3.0'!E2", "values": [["24,0"]]})
        self.assertEqual(updates[2], {"range": "'Tabela de Grupos 3.0'!F2", "values": [["12"]]})

    def test_update_historico_mensal_creates_missing_month_headers(self):
        headers = ["ADM", "Grupo", "Tipo de Bem", "JAN-26 Maior Lance"]
        values = [headers, ["Itau", "128", "Imovel", "70"]]

        class ExecuteMock:
            def execute(self):
                return {}

        class ValuesMock:
            def __init__(self):
                self.batch_update_kwargs = None

            def batchUpdate(self, **kwargs):
                self.batch_update_kwargs = kwargs
                return ExecuteMock()

        class SpreadsheetsMock:
            def __init__(self):
                self.values_mock = ValuesMock()

            def values(self):
                return self.values_mock

        class ServiceMock:
            def __init__(self):
                self.spreadsheets_mock = SpreadsheetsMock()

            def spreadsheets(self):
                return self.spreadsheets_mock

        service = ServiceMock()
        with patch("backend.sheets_client.read_sheet_values", return_value=values), patch("backend.sheets_client.get_service", return_value=service):
            result = update_historico_mensal("128", {
                "mes": "2026-04",
                "maior_lance": 0.71,
                "menor_lance": 0.22,
                "qtd_contemplacoes": 8,
            })

        updates = service.spreadsheets_mock.values_mock.batch_update_kwargs["body"]["data"]
        self.assertTrue(result["success"])
        self.assertEqual(updates[0], {"range": "'Tabela de Grupos 3.0'!E1", "values": [["ABR-26 Maior Lance"]]})
        self.assertEqual(updates[1], {"range": "'Tabela de Grupos 3.0'!F1", "values": [["ABR-26 Menor Lance"]]})
        self.assertEqual(updates[2], {"range": "'Tabela de Grupos 3.0'!G1", "values": [["ABR-26 Qtd Contemplacoes"]]})
        self.assertEqual(updates[3], {"range": "'Tabela de Grupos 3.0'!E2", "values": [["71,0"]]})
        self.assertEqual(updates[4], {"range": "'Tabela de Grupos 3.0'!F2", "values": [["22,0"]]})
        self.assertEqual(updates[5], {"range": "'Tabela de Grupos 3.0'!G2", "values": [["8"]]})

    def test_update_historico_mensal_clears_explicit_null_metric(self):
        headers = ["ADM", "Grupo", "Tipo de Bem", "ABR-26 Maior Lance", "ABR-26 Menor Lance", "ABR-26 Qtd Contemplacoes"]
        values = [headers, ["Itau", "128", "Imovel", "71", "22", "8"]]

        class ExecuteMock:
            def execute(self):
                return {}

        class ValuesMock:
            def __init__(self):
                self.batch_update_kwargs = None

            def batchUpdate(self, **kwargs):
                self.batch_update_kwargs = kwargs
                return ExecuteMock()

        class SpreadsheetsMock:
            def __init__(self):
                self.values_mock = ValuesMock()

            def values(self):
                return self.values_mock

        class ServiceMock:
            def __init__(self):
                self.spreadsheets_mock = SpreadsheetsMock()

            def spreadsheets(self):
                return self.spreadsheets_mock

        service = ServiceMock()
        with patch("backend.sheets_client.read_sheet_values", return_value=values), patch("backend.sheets_client.get_service", return_value=service):
            result = update_historico_mensal("128", {
                "mes": "2026-04",
                "menor_lance": None,
            })

        updates = service.spreadsheets_mock.values_mock.batch_update_kwargs["body"]["data"]
        self.assertTrue(result["success"])
        self.assertEqual(updates, [{"range": "'Tabela de Grupos 3.0'!E2", "values": [[""]]}])

    def test_historico_endpoint_returns_success(self):
        payload = HistoricoUpdateRequest(mes="2026-01", maior_lance=0.72, menor_lance=0.24, qtd_contemplacoes=12)

        with patch("backend.main.update_historico_mensal", return_value={"success": True}):
            result = grupo_historico_atualizar("128", payload)

        self.assertTrue(result["success"])

    def test_historico_lote_endpoint_returns_success(self):
        payload = HistoricoBatchUpdateRequest(items=[
            HistoricoUpdateRequest(mes="2026-11", maior_lance=0.5, menor_lance=0.5, qtd_contemplacoes=2),
            HistoricoUpdateRequest(mes="2026-12", maior_lance=0.51, menor_lance=0.49, qtd_contemplacoes=3),
        ])

        with patch("backend.main.update_historico_mensal_lote", return_value={"success": True}) as update_lote:
            result = grupo_historico_lote_atualizar("128", payload)

        update_lote.assert_called_once()
        self.assertTrue(result["success"])


if __name__ == "__main__":
    unittest.main()
