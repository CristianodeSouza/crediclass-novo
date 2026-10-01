import unittest
from backend.estudos import normalize_study_item, study_item_to_row, study_item_from_row

from backend.financial_study_engine import build_financeiro
from backend.models import EstudoCliente, EstudoRequest


class FinancialStudyEngineTest(unittest.TestCase):
    def test_snapshot_preserva_quantidade_e_identidade_dos_grupos(self):
        groups = [
            {"grupo": str(40000 + index), "taxa_adm": 0.16 + index / 100, "prazo_restante": 240 - index,
             "historico": {f"2026-{index + 1:02d}": {"menor_lance": index / 100}},
             "cenarios": [{"id": "without_embedded", "credito_contratado": 100000 + index}]}
            for index in range(12)
        ]
        item = normalize_study_item({"estudo_id": "EST-2026-00069", "grupo": groups[0], "grupos_selecionados": groups})
        restored = study_item_from_row(study_item_to_row(item))
        self.assertEqual([group["grupo"] for group in restored["grupos_selecionados"]], [str(40000 + i) for i in range(12)])
        self.assertEqual(restored["grupos_selecionados"][1]["taxa_adm"], 0.17)
        self.assertEqual(restored["grupos_selecionados"][11]["historico"]["2026-12"]["menor_lance"], 0.11)

    def test_snapshot_preserva_casos_de_quantidade_dinamica(self):
        for count in (1, 2, 4, 5, 8, 10, 12):
            groups = [{"grupo": f"G-{index}", "taxa_adm": 0.10 + index / 100} for index in range(count)]
            item = normalize_study_item({"grupo": groups[0], "grupos_selecionados": groups})
            restored = study_item_from_row(study_item_to_row(item))
            self.assertEqual(len(restored["grupos_selecionados"]), count)
            self.assertEqual(restored["grupos_selecionados"][-1]["grupo"], f"G-{count - 1}")

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
        self.assertAlmostEqual(financeiro["parcela_inicial"], 4845.238095238095)

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
