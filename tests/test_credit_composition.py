import unittest

from backend.credit_composition import build_card_from_liquid, contracted_credit_for_liquid, summarize_cards


class CreditCompositionTest(unittest.TestCase):
    def test_credito_contratado_com_lance_embutido(self):
        result = contracted_credit_for_liquid(450000, 0.50)

        self.assertEqual(result["credito_contratado"], 900000)
        self.assertEqual(result["lance_embutido"], 450000)
        self.assertEqual(result["credito_liquido"], 450000)

    def test_fgts_nao_permitido_nao_e_utilizado(self):
        card = build_card_from_liquid(
            {"grupo_id": "1", "lance_embutido": False, "fgts": False, "prazo_total": 100},
            300000,
            recurso_proprio_total=10000,
            fgts_total=100000,
            parcela_limite=3500,
        )

        self.assertEqual(card["fgts_utilizado"], 0)

    def test_lance_embutido_nao_permitido_nao_e_aplicado(self):
        card = build_card_from_liquid(
            {
                "grupo_id": "1",
                "lance_embutido": False,
                "percentual_lance_embutido": 0.50,
                "fgts": True,
                "prazo_total": 100,
            },
            300000,
            recurso_proprio_total=0,
            fgts_total=0,
            parcela_limite=3500,
        )

        self.assertEqual(card["lance_embutido"], 0)
        self.assertEqual(card["credito_contratado"], 300000)

    def test_parcela_total_de_composicao(self):
        cards = [{"parcela_estimada": 1900}, {"parcela_estimada": 1500}]
        summary = summarize_cards(cards)

        self.assertEqual(summary["parcela_total"], 3400)
        self.assertTrue(summary["parcela_total"] <= 3500)

    def test_renda_minima(self):
        parcela_total = 3400
        renda_minima = parcela_total * 3

        self.assertEqual(renda_minima, 10200)
        self.assertTrue(20000 >= renda_minima)


if __name__ == "__main__":
    unittest.main()
