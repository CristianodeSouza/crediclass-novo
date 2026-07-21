import unittest
from types import SimpleNamespace

from backend.investor_engine import analyze_investor_groups, is_investor_objective


def payload(**overrides):
    values = {
        "objetivo": "Investidor - Adquirir imovel e alugar (pagar parcelas com aluguel)",
        "credito_desejado": 950000,
        "parcela_desejada": 6500,
        "parcela_ideal": 6500,
        "parcela_limite": 15000,
        "renda_total": 50000,
        "tipo_bem": "Imovel",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def group(group_id, credit_max, installment, **overrides):
    return {
        "grupo_id": group_id,
        "grupo": group_id,
        "administradora": "ITAU",
        "tipo_bem": "Imovel",
        "status": "Ativo",
        "credito_maximo": credit_max,
        "parcela_inicial_grupo": installment,
        **overrides,
    }


class InvestorEngineTest(unittest.TestCase):
    def test_identifies_only_investor_objectives(self):
        self.assertTrue(is_investor_objective("Investidor - Vender carta contemplada"))
        self.assertFalse(is_investor_objective("Contemplar - urgente - 3 meses"))

    def test_applies_credit_and_installment_filters_then_ranks_distance(self):
        result = analyze_investor_groups(payload(), [
            group("ideal", 1000000, 6450),
            group("credit-too-low", 900000, 6450),
            group("income-too-high", 1000000, 16000),
            group("close", 1000000, 6800),
        ])

        self.assertEqual(result["total_grupos_compativeis"], 2)
        self.assertEqual([item["grupo"] for item in result["items"]], ["ideal", "close"])
        self.assertEqual(result["items"][0]["classificacao_parcela"], "Parcela ideal")
        self.assertEqual(result["totais_exclusao"]["credito_insuficiente"], 1)
        self.assertEqual(result["totais_exclusao"]["parcela_acima_da_renda"], 1)

    def test_does_not_assume_missing_group_parameters(self):
        result = analyze_investor_groups(payload(), [group("missing", None, None)])
        self.assertEqual(result["total_grupos_compativeis"], 0)
        self.assertEqual(result["totais_exclusao"]["dados_incompletos"], 1)

    def test_returns_all_compatible_groups_instead_of_top_ten(self):
        groups = [group(f"compatible-{index}", 1000000 + index, 6000 + index) for index in range(12)]
        result = analyze_investor_groups(payload(), groups)

        self.assertEqual(result["total_grupos_compativeis"], 12)
        self.assertEqual(result["total_grupos_exibidos"], 12)
        self.assertEqual(len(result["items"]), 12)
        self.assertEqual([item["ranking"] for item in result["items"]], list(range(1, 13)))


if __name__ == "__main__":
    unittest.main()
