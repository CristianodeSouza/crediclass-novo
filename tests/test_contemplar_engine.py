import unittest
from types import SimpleNamespace

from backend.contemplar_engine import (
    analyze_contemplar_groups,
    calculate_required_gross_credit,
    is_contemplar_objective,
)


def payload(**overrides):
    values = {
        "objetivo": "Contemplar - urgente - 3 meses",
        "credito_desejado": 950000,
        "lance_proprio": 100000,
        "fgts": 50000,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def group(group_id, credit_max, **overrides):
    return {
        "grupo_id": group_id,
        "grupo": group_id,
        "administradora": "ITAU",
        "credito_minimo": 100000,
        "credito_maximo": credit_max,
        **overrides,
    }


class ContemplarEngineTest(unittest.TestCase):
    def test_identifies_only_contemplar_objectives(self):
        self.assertTrue(is_contemplar_objective("Contemplar - moderado - 12 meses"))
        self.assertFalse(is_contemplar_objective("Investidor - Vender carta contemplada"))

    def test_calculates_required_gross_credit_from_the_three_client_values(self):
        self.assertEqual(calculate_required_gross_credit(950000, 100000, 50000), 1100000)
        self.assertEqual(calculate_required_gross_credit("950.000,00", "100.000,00", "50.000,00"), 1100000)

    def test_filters_only_by_credit_maximum_and_uses_credit_minimum_as_information(self):
        result = analyze_contemplar_groups(payload(), [
            group("below", 1099999),
            group("equal", 1100000, credito_minimo=1099999),
            group("above", 1200000, credito_minimo=1200000),
            group("missing", None),
        ])

        self.assertEqual(result["total_grupos_analisados"], 4)
        self.assertEqual(result["total_grupos_compativeis"], 2)
        self.assertEqual(result["total_grupos_incompativeis_credito"], 1)
        self.assertEqual(result["total_grupos_incompletos"], 1)
        self.assertEqual([item["grupo"] for item in result["items"]], ["equal", "above"])
        self.assertEqual(result["items"][0]["credito_minimo"], 1099999)

    def test_returns_all_compatible_groups_ordered_by_smallest_margin_then_group(self):
        result = analyze_contemplar_groups(payload(lance_proprio=0, fgts=0), [
            group("20", 950500),
            group("10", 950500),
            group("30", 960000),
        ])

        self.assertEqual([item["grupo"] for item in result["items"]], ["10", "20", "30"])
        self.assertEqual([item["ranking"] for item in result["items"]], [1, 2, 3])
        self.assertTrue(result["filtros"]["sem_limite_de_resultados"])

    def test_keeps_each_group_credit_scenario_separate(self):
        result = analyze_contemplar_groups(payload(fgts=100000), [
            group("sem", 1150000, percentual_lance_embutido="30%"),
            group("ambos", 1642857.14, percentual_lance_embutido="0,30"),
            group("nenhum", 1149999, percentual_lance_embutido="30"),
        ])

        self.assertEqual(result["total_grupos_compativeis"], 2)
        by_group = {item["grupo"]: item for item in result["items"]}
        self.assertEqual(by_group["sem"]["compatibilidade"], "Compativel sem embutido")
        self.assertEqual(by_group["ambos"]["compatibilidade"], "Compativel nos dois cenarios")
        self.assertEqual(by_group["ambos"]["credito_liquido_projetado_com_embutido"], 950000)

    def test_rejects_invalid_credit_input(self):
        with self.assertRaises(ValueError):
            analyze_contemplar_groups(payload(credito_desejado=0), [])


if __name__ == "__main__":
    unittest.main()
