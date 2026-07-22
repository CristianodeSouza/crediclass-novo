import unittest
from types import SimpleNamespace

from backend.consortium_viability_engine import analyze_client_consortium_viability, map_declared_objective_to_preference


def payload(**overrides):
    values = {"objetivo": "Investidor - Adquirir imovel e alugar (pagar parcelas com aluguel)", "credito_desejado": 950000, "lance_proprio": 100000, "fgts": 50000, "parcela_desejada": 6500, "parcela_limite": 15000, "renda_total": 50000, "tipo_bem": "Imovel"}
    values.update(overrides)
    return SimpleNamespace(**values)


def group(identifier, minimum, maximum, **overrides):
    values = {"grupo_id": identifier, "grupo": identifier, "administradora": "ITAU", "tipo_bem": "Imovel", "status": "Ativo", "credito_minimo": minimum, "credito_maximo": maximum, "parcela_inicial_grupo": 6000, "percentual_lance_embutido": "30%", "taxa_adm": "16%", "fundo_reserva": "3%", "lance_moderado_12m": "10%"}
    values.update(overrides)
    return values


class ConsortiumViabilityEngineTest(unittest.TestCase):
    def test_declared_investor_still_returns_contemplation_strategy(self):
        result = analyze_client_consortium_viability(payload(), [group("both", 100000, 1700000, lance_super_agressivo_3m="40%", lance_agressivo_6m="30%", lance_moderado_12m="10%", lance_conservador_24m="5%", lance_investidor="2%")])
        item = result["items"][0]
        self.assertEqual(result["motor"], "360")
        self.assertEqual(item["investment"], "not_classified")
        self.assertIn("moderate", item["compatible_contemplation_strategies"])

    def test_validates_credit_range_not_only_group_maximum(self):
        result = analyze_client_consortium_viability(payload(lance_proprio=0, fgts=0), [group("below-minimum", 1600000, 2000000), group("inside-range", 900000, 1000000)])
        self.assertEqual([item["grupo"] for item in result["items"]], ["inside-range"])
        self.assertEqual(result["contadores"]["credito_incompativel"], 1)

    def test_calculates_bid_and_debt_for_each_scenario(self):
        result = analyze_client_consortium_viability(payload(), [group("both", 100000, 1700000)])
        scenarios = result["items"][0]["cenarios"]
        without = next(item for item in scenarios if item["id"] == "without_embedded")
        embedded = next(item for item in scenarios if item["id"] == "with_embedded")
        self.assertEqual(without["credito_contratado"], 1100000)
        self.assertEqual(without["lance_total"], 150000)
        self.assertEqual(without["saldo_devedor"], 1309000)
        self.assertEqual(embedded["credito_contratado"], 1571428.57)
        self.assertEqual(embedded["lance_total"], 621428.57)

    def test_declared_objective_mapping_is_specific_or_none(self):
        self.assertEqual(map_declared_objective_to_preference("Contemplar - urgente - 3 meses"), "urgent")
        self.assertEqual(map_declared_objective_to_preference("Contemplar - rapido - 6 meses"), "fast")
        self.assertEqual(map_declared_objective_to_preference("Contemplar - moderado - 12 meses"), "moderate")
        self.assertEqual(map_declared_objective_to_preference("Contemplar - conservador - 24 meses"), "conservative")
        self.assertEqual(map_declared_objective_to_preference("Contemplar - investidor - 36 meses"), "long_term")
        self.assertEqual(map_declared_objective_to_preference("Investidor - carta"), "investment")
        self.assertIsNone(map_declared_objective_to_preference("Sem objetivo"))

    def test_accepts_only_explicit_active_status(self):
        groups = [group("ativo", 100000, 1700000, status="ATIVO"), group("vazio", 100000, 1700000, status=""), group("inativo", 100000, 1700000, status="Inativo")]
        result = analyze_client_consortium_viability(payload(), groups)
        self.assertEqual([item["grupo"] for item in result["items"]], ["ativo"])
        self.assertEqual(result["contadores"]["status_incompleto"], 1)
        self.assertEqual(result["contadores"]["inativos"], 1)

    def test_missing_cost_data_never_recommends_group(self):
        result = analyze_client_consortium_viability(payload(), [group("missing-cost", 100000, 1700000, taxa_adm=None, fundo_reserva=None)])
        item = result["items"][0]
        self.assertFalse(item["financial_data_complete"])
        self.assertIn("taxa_administracao", item["incomplete_fields"])
        self.assertFalse(item["recommendable"])

    def test_missing_minimum_credit_uses_only_maximum_and_alerts(self):
        result = analyze_client_consortium_viability(payload(), [group("no-min", None, 1700000)])
        scenario = result["items"][0]["cenarios"][0]
        self.assertTrue(scenario["credit_compatible"])
        self.assertIn("credito_minimo_nao_informado", scenario["alerts"])

    def test_reference_installment_does_not_approve_financial_capacity(self):
        result = analyze_client_consortium_viability(payload(), [group("reference", 100000, 1700000, parcela_inicial_grupo=1)])
        item = result["items"][0]
        self.assertTrue(item["installment_affordable_reference"])
        self.assertIsNone(item["income_compatible"])
        self.assertFalse(item["recommendable"])

    def test_term_compatibility_uses_ceil_against_remaining_term(self):
        base = group("equal", 100000, 1700000, prazo_remanescente=202)
        result = analyze_client_consortium_viability(payload(), [base])
        scenario = result["items"][0]["cenarios"][0]
        self.assertTrue(scenario["term_compatible_desired_before_bid"])
        lower = analyze_client_consortium_viability(payload(), [group("below", 100000, 1700000, prazo_remanescente=201)])
        self.assertFalse(lower["items"][0]["cenarios"][0]["term_compatible_desired_before_bid"])

    def test_inconsistent_contemplation_ranges_do_not_classify_strategy(self):
        result = analyze_client_consortium_viability(payload(), [group("bad-ranges", 100000, 1700000, lance_super_agressivo_3m="10%", lance_agressivo_6m="30%", lance_conservador_24m="5%", lance_investidor="2%")])
        item = result["items"][0]
        self.assertEqual(item["compatible_contemplation_strategies"], [])
        self.assertIn("faixas_contemplacao_inconsistentes", item["alerts"])

    def test_conflicting_own_resource_sources_block_analysis(self):
        with self.assertRaisesRegex(ValueError, "conflito_recurso_proprio"):
            analyze_client_consortium_viability(payload(lance_proprio=100000, lance_proprio_participantes=100000, lance_proprio_manual=50000), [])


if __name__ == "__main__":
    unittest.main()
