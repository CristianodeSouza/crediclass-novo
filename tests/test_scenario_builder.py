import unittest

from backend.models import ViabilidadeRequest
from backend.scenario_builder import analyze_scenarios


def payload(**overrides):
    data = {
        "objetivo": "Aquisicao",
        "credito_desejado": 450000,
        "prazo_desejado": 3,
        "lance_proprio": 20000,
        "fgts": 0,
        "renda_total": 20000,
        "parcela_desejada": 3500,
        "parcela_ideal": 2500,
        "parcela_limite": 3500,
        "tipo_bem": "Imovel",
    }
    data.update(overrides)
    return ViabilidadeRequest(**data)


def group(grupo_id, credito_maximo, **overrides):
    data = {
        "grupo_id": grupo_id,
        "administradora": "CNP",
        "grupo": grupo_id,
        "tipo_bem": "Imovel",
        "credito_minimo": 0,
        "credito_maximo": credito_maximo,
        "taxa_adm": 0,
        "fundo_reserva": 0,
        "prazo_total": 300,
        "prazo_restante": 300,
        "lance_embutido": True,
        "percentual_lance_embutido": 0.50,
        "fgts": True,
        "status": "Ativo",
        "historico": {
            "2026-04": {"menor_lance": 0.50, "qtd_contemplacoes": 1},
            "2026-05": {"menor_lance": 0.52, "qtd_contemplacoes": 1},
            "2026-06": {"menor_lance": 0.49, "qtd_contemplacoes": 1},
        },
    }
    data.update(overrides)
    return data


class ScenarioBuilderTest(unittest.TestCase):
    def test_monta_composicao_com_duas_cartas_na_mesma_administradora(self):
        result = analyze_scenarios(payload(), [group("500", 500000), group("400", 400000)])
        scenario = next(item for item in result["cenarios"] if item["quantidade_cartas"] == 2)

        self.assertEqual(scenario["administradora"], "CNP")
        self.assertEqual(scenario["credito_liquido_total"], 450000)
        self.assertEqual(scenario["credito_contratado_total"], 900000)
        self.assertEqual(scenario["lance_embutido_total"], 450000)
        self.assertEqual(len(scenario["cartas"]), 2)

    def test_valida_parcela_total_e_renda_do_cenario(self):
        result = analyze_scenarios(payload(renda_total=20000), [
            group("500", 500000, prazo_total=250),
            group("400", 400000, prazo_total=267),
        ])
        scenario = next(item for item in result["cenarios"] if item["quantidade_cartas"] == 2)

        self.assertLessEqual(scenario["parcela_total"], 3500)
        self.assertEqual(scenario["renda_minima"], round(scenario["parcela_total"] * 3, 2))
        self.assertNotEqual(scenario["status"], "inviavel")


if __name__ == "__main__":
    unittest.main()
