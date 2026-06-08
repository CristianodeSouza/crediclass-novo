import unittest

from backend.lance_reference import (
    LANCE_INCREMENT,
    aggressive_reference,
    calculate_lance_references,
    classify_profile,
    investor_reference,
    second_lowest_reference,
    valid_lower_bids,
)


def history(values):
    return {
        f"2026-{index:02d}": {"menor_lance": value, "qtd_contemplacoes": 1}
        for index, value in enumerate(values, start=1)
    }


class LanceReferenceEngineTest(unittest.TestCase):
    def test_global_increment_is_quarter_percentage_point(self):
        self.assertEqual(LANCE_INCREMENT, 0.0025)

    def test_profiles_follow_official_operational_ranges(self):
        expected = {
            3: ("Agressivo", "lance_agressivo", "1 a 3 meses"),
            6: ("Moderado", "lance_moderado", "4 a 6 meses"),
            12: ("Conservador", "lance_conservador", "7 a 12 meses"),
            24: ("Super Conservador", "lance_super_conservador", "13 a 24 meses"),
            25: ("Investidor", "lance_investidor", "Sem urgencia"),
        }
        for months, profile in expected.items():
            with self.subTest(months=months):
                self.assertEqual(classify_profile(months), profile)

    def test_second_lowest_uses_latest_valid_months_and_adds_increment(self):
        historico = history([0.35, 0.31, 0.29, 0.40, 0.33, 0.28])
        historico["2025-12"] = {"menor_lance": 0.01, "qtd_contemplacoes": 1}
        historico["invalido"] = {"menor_lance": 0.02, "qtd_contemplacoes": 1}

        self.assertEqual(valid_lower_bids(historico, 6), [0.28, 0.33, 0.40, 0.29, 0.31, 0.35])
        self.assertEqual(second_lowest_reference(historico, 6), 0.2925)

    def test_aggressive_uses_threshold_that_passed_all_last_three_months(self):
        self.assertEqual(aggressive_reference(history([0.31, 0.29, 0.35])), 0.3525)

    def test_history_shortage_returns_none(self):
        self.assertIsNone(second_lowest_reference(history([0.30]), 12))
        self.assertIsNone(aggressive_reference(history([0.30])))

    def test_reference_requires_contemplated_months(self):
        historico = {
            "2026-01": {"menor_lance": 0.30, "qtd_contemplacoes": 0},
            "2026-02": {"menor_lance": 0.31, "qtd_contemplacoes": 1},
            "2026-03": {"menor_lance": 0.32, "qtd_contemplacoes": None},
        }

        self.assertIsNone(second_lowest_reference(historico, 3))

    def test_investor_uses_fixed_bid_without_history_and_caps_twenty_percent(self):
        self.assertEqual(investor_reference(None), 0)
        self.assertEqual(investor_reference(0.15), 0.15)
        self.assertEqual(investor_reference(0.35), 0.20)

    def test_generates_all_official_fields(self):
        result = calculate_lance_references(history([0.31, 0.29, 0.35, 0.30, 0.33, 0.34]), 0.10)
        self.assertEqual(set(result), {
            "lance_investidor",
            "lance_super_conservador",
            "lance_conservador",
            "lance_moderado",
            "lance_agressivo",
        })
