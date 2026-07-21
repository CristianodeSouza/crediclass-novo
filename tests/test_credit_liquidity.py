import unittest

from backend.credit_liquidity import (
    build_credit_liquidity_scenarios,
    evaluate_group_credit_liquidity,
    normalize_embedded_bid_percent,
)


class CreditLiquidityTest(unittest.TestCase):
    def test_normalizes_supported_embedded_bid_formats(self):
        for value in ("30%", "30", "0,30", "0.30", 0.30):
            self.assertEqual(normalize_embedded_bid_percent(value), 0.30)
        self.assertEqual(normalize_embedded_bid_percent("1%"), 0.01)
        self.assertIsNone(normalize_embedded_bid_percent(""))
        self.assertIsNone(normalize_embedded_bid_percent(0))
        self.assertIsNone(normalize_embedded_bid_percent(-0.1))
        self.assertIsNone(normalize_embedded_bid_percent(1))

    def test_preserves_desired_liquidity_in_both_scenarios(self):
        scenarios = build_credit_liquidity_scenarios(950000, 100000, 100000, "30%", "16%", "3%")

        self.assertEqual(scenarios["credito_necessario_sem_embutido"], 1150000)
        self.assertEqual(scenarios["credito_necessario_com_embutido"], 1642857.14)
        self.assertEqual(scenarios["valor_lance_embutido"], 492857.14)
        self.assertEqual(scenarios["taxa_administracao_sem_embutido"], 184000)
        self.assertEqual(scenarios["fundo_reserva_sem_embutido"], 34500)
        self.assertEqual(scenarios["saldo_devedor_sem_embutido"], 1368500)
        self.assertEqual(scenarios["taxa_administracao_com_embutido"], 262857.14)
        self.assertEqual(scenarios["fundo_reserva_com_embutido"], 49285.71)
        self.assertEqual(scenarios["saldo_devedor_com_embutido"], 1955000)
        self.assertEqual(scenarios["credito_liquido_projetado_sem_embutido"], 950000)
        self.assertEqual(scenarios["credito_liquido_projetado_com_embutido"], 950000)

    def test_classifies_the_two_credit_compatibility_scenarios(self):
        scenarios = build_credit_liquidity_scenarios(950000, 100000, 100000, 0.30)

        sem = evaluate_group_credit_liquidity(1150000, scenarios)
        ambos = evaluate_group_credit_liquidity(1642857.14, scenarios)
        nenhum = evaluate_group_credit_liquidity(1000000, scenarios)

        self.assertEqual(sem["classificacao_credito"], "Compativel sem embutido")
        self.assertEqual(ambos["classificacao_credito"], "Compativel nos dois cenarios")
        self.assertEqual(nenhum["classificacao_credito"], "Incompativel nos dois cenarios")


if __name__ == "__main__":
    unittest.main()
