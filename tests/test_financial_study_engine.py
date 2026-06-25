import unittest

from backend.financial_study_engine import build_financeiro
from backend.models import EstudoCliente, EstudoRequest


class FinancialStudyEngineTest(unittest.TestCase):
    def test_build_financeiro_calcula_credito_e_lance_embutido(self):
        payload = EstudoRequest(
            cliente=EstudoCliente(
                nome="Cliente Teste",
                credito_desejado=500000,
                prazo_desejado=180,
                lance_proprio=80000,
                fgts=20000,
            ),
            grupo_id="128",
        )
        grupo = {
            "grupo_id": "128",
            "percentual_lance_embutido": 0.3,
            "taxa_adm": 0.2,
            "fundo_reserva": 0.03,
            "prazo_restante": 180,
        }

        financeiro = build_financeiro(payload, grupo)

        self.assertAlmostEqual(financeiro["credito_original"], 714285.7142857143)
        self.assertAlmostEqual(financeiro["lance_embutido"], 214285.7142857143)
        self.assertAlmostEqual(financeiro["credito_disponivel"], 500000)
        self.assertAlmostEqual(financeiro["recurso_proprio"], 100000)
        self.assertAlmostEqual(financeiro["percentual_lance_total"], 0.44)
        self.assertAlmostEqual(financeiro["parcela_inicial"], 4880.952380952381)

    def test_build_financeiro_herda_cenario_aprovado(self):
        cenario = {
            "credito_liquido_total": 450000,
            "credito_contratado_total": 900000,
            "lance_embutido_total": 450000,
            "recurso_proprio_total": 20000,
            "fgts_utilizado_total": 0,
            "percentual_lance_total": 0.522222,
            "lance_total": 470000,
            "parcela_total": 3400,
            "renda_minima": 10200,
            "score_cenario": 91,
            "status": "viavel",
            "estrategia": "Super Agressivo",
            "cartas": [{"grupo_id": "500"}],
        }
        payload = EstudoRequest(
            cliente=EstudoCliente(nome="Cliente Cenario", credito_desejado=450000),
            grupo_id="500",
            cenario=cenario,
        )

        financeiro = build_financeiro(payload, {})

        self.assertEqual(financeiro["credito"], 450000)
        self.assertEqual(financeiro["credito_original"], 900000)
        self.assertEqual(financeiro["percentual_lance_embutido"], 0.5)
        self.assertEqual(financeiro["estrategia_recomendada"], "Super Agressivo")
        self.assertEqual(financeiro["cartas"], [{"grupo_id": "500"}])

    def test_build_financeiro_resume_historico_e_estrategias(self):
        payload = EstudoRequest(
            cliente=EstudoCliente(nome="Cliente Historico", credito_desejado=300000),
            grupo_id="017",
        )
        grupo = {
            "grupo_id": "017",
            "prazo_total": 100,
            "percentual_lance_fixo": 0.18,
            "historico": {
                "2026-01": {"maior_lance": 0.7, "menor_lance": 0.31, "qtd_contemplacoes": 2},
                "2026-02": {"maior_lance": 0.75, "menor_lance": 0.29, "qtd_contemplacoes": 3},
            },
        }

        financeiro = build_financeiro(payload, grupo)

        self.assertEqual(financeiro["historico_12_meses"]["total_contemplacoes"], 5)
        self.assertEqual(len(financeiro["estrategias"]), 5)
        self.assertEqual(financeiro["estrategias"][0]["estrategia"], "Investidor")


if __name__ == "__main__":
    unittest.main()
