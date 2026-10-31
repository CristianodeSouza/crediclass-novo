import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "backend" / "static" / "index.html"
APP = ROOT / "backend" / "static" / "js" / "app.js"


class ProfileContemplationFrontendContractTests(unittest.TestCase):
    def test_profile_is_the_only_visible_strategy_selector(self):
        html = INDEX.read_text(encoding="utf-8")
        self.assertEqual(html.count('id="clientProfileObjetivo"'), 1)
        self.assertIn('id="clientProfileObjetivo" type="hidden"', html)
        self.assertEqual(html.count('id="clientProfileContemplacaoPerfil"'), 1)
        self.assertIn("<span>Perfil de contemplação</span>", html)

    def test_canonical_profile_keeps_legacy_objective_contract(self):
        app = APP.read_text(encoding="utf-8")
        expected = {
            "urgent": "Contemplar - urgente - 3 meses",
            "fast": "Contemplar - rapido - 6 meses",
            "moderate": "Contemplar - moderado - 12 meses",
            "conservative": "Contemplar - conservador - 24 meses",
            "long_term": "Contemplar - investidor - 36 meses",
        }
        for profile, objective in expected.items():
            self.assertIn(f'{profile}: "{objective}"', app)
        self.assertIn("syncCanonicalContemplationProfile", app)
        self.assertIn("contemplacao_perfil: document.getElementById", app)
        self.assertIn("objetivo: objective", app)

    def test_legacy_objective_is_not_used_as_an_independent_ui_input(self):
        html = INDEX.read_text(encoding="utf-8")
        objective_select = '<select id="clientProfileObjetivo"'
        self.assertNotIn(objective_select, html)


if __name__ == "__main__":
    unittest.main()
