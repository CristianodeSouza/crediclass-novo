import unittest
from unittest.mock import patch

from backend.administrator_feasibility import analyze_administradoras, calculate_administrator_feasibility
from backend.administrator_rules import AdministratorRule, rule_from_config
from backend.main import viabilidade_analisar
from backend.models import ViabilidadeRequest
from backend.viabilidade import (
    analyze_viabilidade,
    calculate_age,
    classify_profile,
    group_selo,
    history_last_12_months,
)


def make_payload(**overrides):
    values = {
        "objetivo": "Aquisicao",
        "credito_desejado": 500000,
        "prazo_desejado": 12,
        "lance_proprio": 100000,
        "fgts": 50000,
        "renda_total": 25000,
        "parcela_desejada": 4500,
        "data_nascimento": "1985-01-01",
        "data_nascimento_conjuge": "1987-01-01",
        "tipo_bem": "Imovel",
        "estado_bem": "Pronto",
    }
    values.update(overrides)
    return ViabilidadeRequest(**values)


def make_group(**overrides):
    values = {
        "grupo_id": "128",
        "administradora": "Itau",
        "grupo": "128",
        "tipo_bem": "Imovel",
        "credito_minimo": 100000,
        "credito_maximo": 1000000,
        "taxa_adm": 0.2,
        "fundo_reserva": 0.03,
        "prazo_total": 222,
        "prazo_restante": 180,
        "lance_embutido": True,
        "percentual_lance_embutido": 0.3,
        "fgts": True,
        "status": "Ativo",
        "historico": {
            "2026-01": {
                "maior_lance": 0.32,
                "menor_lance": 0.24,
                "qtd_contemplacoes": 5,
            },
            "2026-02": {
                "maior_lance": 0.34,
                "menor_lance": 0.25,
                "qtd_contemplacoes": 4,
            },
        },
    }
    values.update(overrides)
    return values


def make_admin_rule(**overrides):
    values = {
        "administradora": "Itau",
        "seguro_obrigatorio": False,
        "idade_maxima": 80,
        "limite_sem_comprovacao_renda": None,
        "percentual_lance_embutido": 0.30,
        "tipo_lance_embutido": "Credito",
        "taxa_adm": 0.20,
        "possui_negociacao_taxa": "Sim",
        "fundo_reserva": 0.03,
        "aceita_saida_fiscal": True,
        "aceita_fgts": True,
    }
    values.update(overrides)
    return values


class ViabilidadeTest(unittest.TestCase):
    def test_administrator_feasibility_calcula_credito_lance_e_prazo(self):
        rule = AdministratorRule(
            administradora="Teste",
            seguro_obrigatorio=False,
            idade_maxima=80,
            limite_sem_comprovacao_renda=None,
            percentual_lance_embutido=0.30,
            tipo_lance_embutido="Credito",
            taxa_adm=0.15,
            possui_negociacao_taxa="Sim",
            fundo_reserva=0.01,
            aceita_saida_fiscal=True,
            aceita_fgts=True,
        )
        payload = make_payload(
            credito_desejado=400000,
            lance_proprio=100000,
            fgts=50000,
            renda_total=15000,
            parcela_desejada=4500,
            parcela_limite=6000,
            prazo_desejado=6,
            data_nascimento="1980-01-01",
            data_nascimento_conjuge="",
        )

        result = calculate_administrator_feasibility(payload, rule)

        self.assertAlmostEqual(result["credito_a_contratar"], 571428.57, places=2)
        self.assertAlmostEqual(result["lance_embutido_valor"], 171428.57, places=2)
        self.assertAlmostEqual(result["lance_total"], 321428.57, places=2)
        self.assertAlmostEqual(result["lance_maximo_percentual"], 0.5625, places=4)
        self.assertAlmostEqual(result["prazo_minimo"], 56.9, places=2)
        self.assertTrue(result["elegivel"])

    def test_administrator_feasibility_ordena_elegiveis_por_credito_prazo_e_lance(self):
        result = analyze_administradoras(
            make_payload(
                credito_desejado=400000,
                lance_proprio=100000,
                fgts=100000,
                renda_total=15000,
                parcela_desejada=4500,
                parcela_limite=6000,
                prazo_desejado=6,
                data_nascimento="1980-01-01",
            ),
            ["ITAÚ", "PORTO", "EMBRACON"],
            [
                make_admin_rule(administradora="ITAÚ", taxa_adm=0.20, fundo_reserva=0.03),
                make_admin_rule(administradora="PORTO", taxa_adm=0.16, fundo_reserva=0.005),
                make_admin_rule(administradora="EMBRACON", taxa_adm=0.20, fundo_reserva=0.02, percentual_lance_embutido=0.25),
            ],
        )

        self.assertGreaterEqual(len(result), 3)
        self.assertTrue(result[0]["elegivel"])
        self.assertLessEqual(result[0]["credito_a_contratar"], result[1]["credito_a_contratar"])

    def test_administrator_feasibility_nao_usa_regras_importadas_da_planilha(self):
        result = analyze_administradoras(make_payload(), ["ITAÚ", "CAIXA"], config_rules=[])

        self.assertEqual(result, [])

    def test_administrator_rule_normaliza_campos_vazios_e_percentuais_humanos(self):
        rule = rule_from_config(
            make_admin_rule(
                idade_maxima="",
                limite_sem_comprovacao_renda="R$ 3.000.000,00",
                percentual_lance_embutido="30%",
                taxa_adm="20",
                fundo_reserva="3%",
            )
        )

        self.assertIsNotNone(rule)
        self.assertIsNone(rule.idade_maxima)
        self.assertEqual(rule.limite_sem_comprovacao_renda, 3000000)
        self.assertEqual(rule.percentual_lance_embutido, 0.30)
        self.assertEqual(rule.taxa_adm, 0.20)
        self.assertEqual(rule.fundo_reserva, 0.03)

    def test_administrator_feasibility_pode_desconsiderar_lance_embutido(self):
        rule = AdministratorRule(
            administradora="Teste",
            seguro_obrigatorio=False,
            idade_maxima=80,
            limite_sem_comprovacao_renda=None,
            percentual_lance_embutido=0.30,
            tipo_lance_embutido="Credito",
            taxa_adm=0.15,
            possui_negociacao_taxa="Sim",
            fundo_reserva=0.01,
            aceita_saida_fiscal=True,
            aceita_fgts=True,
        )
        payload = make_payload(
            credito_desejado=400000,
            lance_proprio=100000,
            fgts=50000,
            renda_total=15000,
            parcela_desejada=4500,
            parcela_limite=6000,
            data_nascimento="1980-01-01",
            considerar_lance_embutido=False,
        )

        result = calculate_administrator_feasibility(payload, rule)

        self.assertEqual(result["percentual_lance_embutido"], 0)
        self.assertEqual(result["credito_a_contratar"], 400000)
        self.assertEqual(result["lance_embutido_valor"], 0)

    def test_classify_profile_all_intervals(self):
        expected = {
            1: "Agressivo",
            3: "Agressivo",
            4: "Moderado",
            6: "Moderado",
            7: "Conservador",
            12: "Conservador",
            13: "Super Conservador",
            24: "Super Conservador",
            25: "Investidor",
        }
        for months, profile in expected.items():
            with self.subTest(months=months):
                self.assertEqual(classify_profile(months)[0], profile)

    def test_history_uses_only_latest_12_valid_months(self):
        history = {
            f"2025-{month:02d}": {
                "maior_lance": month / 100,
                "menor_lance": month / 200,
                "qtd_contemplacoes": month,
            }
            for month in range(1, 13)
        }
        history["2024-12"] = {
            "maior_lance": 0.99,
            "menor_lance": 0.99,
            "qtd_contemplacoes": 999,
        }
        history["invalido"] = {"maior_lance": 1, "menor_lance": 1, "qtd_contemplacoes": 1}

        result = history_last_12_months(history)

        self.assertAlmostEqual(result["media_maior_lance"], 0.065)
        self.assertAlmostEqual(result["media_menor_lance"], 0.0325)
        self.assertEqual(result["media_qtd_contemplacoes"], 6.5)
        self.assertEqual(result["total_contemplacoes"], 78)

    def test_filters_inactive_credit_above_maximum_and_wrong_type(self):
        groups = [
            make_group(grupo_id="inactive", status="Inativo"),
            make_group(grupo_id="low-max", credito_maximo=400000),
            make_group(grupo_id="vehicle", tipo_bem="Veiculo"),
        ]

        result = analyze_viabilidade(make_payload(), groups)

        self.assertEqual(result["total_grupos_encontrados"], 0)
        self.assertFalse(result["cenario_viavel"])

    def test_credit_below_minimum_scores_zero_and_is_not_approved(self):
        result = analyze_viabilidade(
            make_payload(credito_desejado=500000),
            [make_group(credito_minimo=600000)],
        )

        self.assertEqual(result["total_grupos_encontrados"], 1)
        self.assertEqual(result["total_grupos_compativeis"], 0)
        self.assertEqual(result["melhores_grupos"], [])

    def test_credit_inside_range_is_approved_when_other_rules_pass(self):
        result = analyze_viabilidade(make_payload(), [make_group()])

        self.assertTrue(result["cenario_viavel"])
        self.assertEqual(result["total_grupos_compativeis"], 1)
        item = result["melhores_grupos"][0]
        self.assertEqual(item["lance_sugerido_percentual"], 0.2525)
        self.assertAlmostEqual(
            item["lance_sugerido_valor"],
            item["credito_contratado"] * 0.2525,
            places=2,
        )

    def test_fgts_is_used_only_when_group_allows_it(self):
        allowed = analyze_viabilidade(make_payload(), [make_group(fgts=True)])
        blocked = analyze_viabilidade(make_payload(), [make_group(fgts=False)])

        self.assertEqual(allowed["melhores_grupos"][0]["fgts_utilizado"], 50000)
        self.assertEqual(blocked["melhores_grupos"], [])
        self.assertFalse(blocked["checklist"]["fgts_permitido"])

    def test_embedded_bid_is_used_only_when_group_allows_it(self):
        allowed = analyze_viabilidade(make_payload(), [make_group(lance_embutido=True)])
        blocked = analyze_viabilidade(make_payload(), [make_group(lance_embutido=False)])

        self.assertAlmostEqual(allowed["melhores_grupos"][0]["credito_contratado"], 714285.71, places=2)
        self.assertAlmostEqual(allowed["melhores_grupos"][0]["lance_embutido_utilizado"], 214285.71, places=2)
        self.assertEqual(blocked["melhores_grupos"][0]["credito_contratado"], 500000)
        self.assertEqual(blocked["melhores_grupos"][0]["lance_embutido_utilizado"], 0)

    def test_lance_zero_is_accepted_but_can_make_scenario_unviable(self):
        result = analyze_viabilidade(
            make_payload(lance_proprio=0, fgts=0),
            [make_group(lance_embutido=False, percentual_lance_embutido=0)],
        )

        self.assertEqual(result["total_grupos_encontrados"], 1)
        self.assertEqual(result["melhores_grupos"], [])
        self.assertFalse(result["checklist"]["lance_compativel"])
        self.assertFalse(result["cenario_viavel"])

    def test_no_artificial_fifty_percent_is_added_to_available_bid(self):
        result = analyze_viabilidade(
            make_payload(lance_proprio=10000, fgts=0),
            [make_group(lance_embutido=False, percentual_lance_embutido=0)],
        )

        self.assertEqual(result["lance_total_disponivel"], 10000)
        self.assertFalse(result["checklist"]["lance_compativel"])

    def test_group_without_bid_history_or_reference_gets_zero_bid_score_alert(self):
        result = analyze_viabilidade(
            make_payload(),
            [
                make_group(
                    percentual_lance_fixo=None,
                    historico={},
                    lance_embutido=False,
                )
            ],
        )

        self.assertEqual(result["total_grupos_encontrados"], 1)
        self.assertEqual(result["melhores_grupos"], [])
        self.assertFalse(result["checklist"]["lance_compativel"])

    def test_seals_cover_every_score_range(self):
        cases = [
            (100, "Excelente"),
            (90, "Excelente"),
            (89.9, "Muito Bom"),
            (80, "Muito Bom"),
            (79.9, "Bom"),
            (70, "Bom"),
            (69.9, "Regular"),
            (60, "Regular"),
            (59.9, "Baixa Compatibilidade"),
            (0, "Baixa Compatibilidade"),
        ]
        for score, seal in cases:
            with self.subTest(score=score):
                self.assertEqual(group_selo(score), seal)

    def test_age_calculates_holder_and_spouse_and_preserves_state(self):
        result = analyze_viabilidade(make_payload(), [make_group()])

        self.assertEqual(result["idade_titular"], calculate_age("1985-01-01"))
        self.assertEqual(result["idade_conjuge"], calculate_age("1987-01-01"))
        self.assertTrue(result["idade_validada"])
        self.assertEqual(result["estado_bem"], "Pronto")

    def test_missing_age_is_not_marked_compatible_automatically(self):
        result = analyze_viabilidade(
            make_payload(data_nascimento="", data_nascimento_conjuge=""),
            [make_group()],
        )

        self.assertFalse(result["idade_validada"])
        self.assertFalse(result["checklist"]["idade_compativel"])
        self.assertEqual(result["idade_alerta"], "idade_nao_validada")
        self.assertIn("idade_nao_validada", result["melhores_grupos"][0]["alertas"])
        self.assertTrue(result["melhores_grupos"][0]["grupo_aprovado"])

    def test_group_age_limit_can_reject_scenario(self):
        result = analyze_viabilidade(
            make_payload(data_nascimento="1940-01-01", data_nascimento_conjuge=""),
            [make_group(idade_maxima=70)],
        )

        self.assertFalse(result["cenario_viavel"])
        self.assertFalse(result["checklist"]["idade_compativel"])
        self.assertEqual(result["melhores_grupos"], [])

    def test_calculates_installment_and_contract_credit(self):
        result = analyze_viabilidade(make_payload(), [make_group()])
        item = result["melhores_grupos"][0]
        expected_installment = (item["credito_contratado"] * 1.23) / 222

        self.assertAlmostEqual(item["taxa_administrativa_valor"], item["credito_contratado"] * 0.2, places=2)
        self.assertAlmostEqual(item["fundo_reserva_valor"], item["credito_contratado"] * 0.03, places=2)
        self.assertAlmostEqual(item["parcela_estimada"], expected_installment, places=2)
        self.assertAlmostEqual(item["credito_disponivel"], 500000, places=2)

    def test_vehicle_request_does_not_return_property_group(self):
        result = analyze_viabilidade(
            make_payload(tipo_bem="Veiculo", objetivo="Aquisicao"),
            [make_group(tipo_bem="Imovel")],
        )

        self.assertEqual(result["total_grupos_encontrados"], 0)

    def test_found_group_with_failed_checklist_is_inviable(self):
        result = analyze_viabilidade(
            make_payload(renda_total=1000, parcela_desejada=100),
            [make_group()],
        )

        self.assertEqual(result["total_grupos_encontrados"], 1)
        self.assertFalse(result["cenario_viavel"])
        self.assertEqual(result["melhores_grupos"], [])
        self.assertIn("renda_compativel", result["motivos_reprovacao"])
        self.assertIn("parcela_compativel", result["motivos_reprovacao"])

    def test_endpoint_uses_sheets_and_returns_response(self):
        with (
            patch("backend.main.list_grupos", return_value=[make_group()]),
            patch("backend.main.get_configuracoes", return_value={"administradoras_regras": [make_admin_rule(administradora="Itau")]}),
            patch("backend.main.list_grupos_detalhe_by_ids", return_value=[make_group()]) as list_details,
        ):
            result = viabilidade_analisar(make_payload())

        list_details.assert_called_once_with(["128"])
        self.assertEqual(result["total_administradoras_analisadas"], 1)
        self.assertEqual(result["total_administradoras_elegiveis"], 1)
        self.assertEqual(result["administradoras_viabilidade"][0]["administradora"], "Itau")
        self.assertEqual(result["total_grupos_analisados"], 1)
        self.assertEqual(result["melhores_grupos"][0]["administradora"], "Itau")

    def test_endpoint_busca_grupos_em_modo_preliminar_sem_regra_de_administradora(self):
        with (
            patch("backend.main.list_grupos", return_value=[make_group()]),
            patch("backend.main.get_configuracoes", return_value={"administradoras_regras": []}),
            patch("backend.main.list_grupos_detalhe_by_ids", return_value=[make_group()]) as list_details,
        ):
            result = viabilidade_analisar(make_payload())

        list_details.assert_called_once_with(["128"])
        self.assertEqual(result["total_administradoras_analisadas"], 0)
        self.assertEqual(result["total_grupos_analisados"], 1)
        self.assertEqual(result["melhores_grupos"][0]["administradora"], "Itau")
        self.assertIn("regras_administradoras_pendentes_analise_humana", result["melhores_grupos"][0]["alertas"])
        self.assertIn("regras_administradoras_pendentes_analise_humana", result["motivos_reprovacao"])


if __name__ == "__main__":
    unittest.main()
