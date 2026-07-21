import unittest
from types import SimpleNamespace

from backend.consortium_viability_engine import analyze_client_consortium_viability


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
        result = analyze_client_consortium_viability(payload(), [group("both", 100000, 1700000)])
        item = result["items"][0]
        self.assertEqual(result["motor"], "360")
        self.assertIn("investment", item["estrategias_possiveis"])
        self.assertIn("moderate", item["estrategias_possiveis"])

    def test_validates_credit_range_not_only_group_maximum(self):
        result = analyze_client_consortium_viability(payload(lance_proprio=0, fgts=0), [group("below-minimum", 1600000, 2000000), group("inside-range", 900000, 1000000)])
        self.assertEqual([item["grupo"] for item in result["items"]], ["inside-range"])
        self.assertEqual(result["totais_exclusao"]["credito"], 1)

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


if __name__ == "__main__":
    unittest.main()
