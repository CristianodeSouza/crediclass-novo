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
        self.assertEqual(result["etapa4"]["fluxo"], "contemplacao")
        self.assertEqual(result["etapa4"]["conceito"], "Contemplacao Urgente")

    def test_valida_parcela_total_e_renda_do_cenario(self):
        result = analyze_scenarios(payload(renda_total=20000, lance_proprio=50000), [
            group("500", 500000, prazo_total=250),
            group("400", 400000, prazo_total=267),
        ])
        scenario = next(item for item in result["cenarios"] if item["quantidade_cartas"] == 2)

        self.assertLessEqual(scenario["parcela_total"], 3500)
        self.assertEqual(scenario["renda_minima"], round(scenario["parcela_total"] * 3, 2))
        self.assertNotEqual(scenario["status"], "inviavel")

    def test_etapa4_contemplacao_filtra_primeiros_20_por_urgencia(self):
        groups = [group(f"g{i:02d}", 500000 + i, percentual_lance_embutido=0.0) for i in range(25)]
        result = analyze_scenarios(payload(), groups)

        self.assertEqual(result["etapa4"]["fluxo"], "contemplacao")
        self.assertEqual(result["etapa4"]["filtro_1"], "Classificacao pela urgencia de contemplacao")
        self.assertEqual(result["etapa4"]["limite"], 20)
        self.assertEqual(result["total_grupos_pos_filtro_1"], 20)

    def test_etapa4_investimento_filtra_primeiros_10_por_beneficios(self):
        groups = [
            group(
                f"inv{i:02d}",
                500000 + i,
                percentual_lance_embutido=0.0,
                prazo_restante=120 + i,
                taxa_adm=0.30 - (i * 0.005),
                fundo_reserva=0.05,
                percentual_lance_fixo=max(0.01, 0.20 - (i * 0.002)),
            )
            for i in range(15)
        ]
        result = analyze_scenarios(payload(objetivo="Investidor - Vender carta contemplada (ganhar agil)", prazo_desejado=36), groups)

        self.assertEqual(result["etapa4"]["fluxo"], "investimento")
        self.assertEqual(result["etapa4"]["filtro_1"], "Classificacao pelo objetivo de investimento")
        self.assertEqual(result["etapa4"]["limite"], 10)
        self.assertEqual(result["total_grupos_pos_filtro_1"], 10)
        self.assertIn("Maior prazo remanescente", result["etapa4"]["criterios"])


if __name__ == "__main__":
    unittest.main()
