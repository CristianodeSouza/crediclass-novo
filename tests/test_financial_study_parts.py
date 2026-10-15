from pathlib import Path
import re
import unittest

from backend.main import app


ROOT = Path(__file__).resolve().parents[1]


class FinancialStudyPartsTest(unittest.TestCase):
    def test_old_study_apis_and_public_routes_remain_unregistered(self):
        paths = {route.path for route in app.routes}
        self.assertFalse(any(path.startswith("/api/estudos") for path in paths))
        self.assertFalse(any(path.startswith("/api/public-estudos") for path in paths))
        self.assertFalse(any(path.startswith("/api/templates-estudos") for path in paths))
        self.assertNotIn("/estudo/{estudo_id}", paths)

    def test_part_one_is_static_fixed_copy_and_has_the_brand_image(self):
        html = (ROOT / "backend/static/index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "backend/static/js/app.js").read_text(encoding="utf-8")
        start = html.index('<section id="screen-estudo"')
        end = html.index("</section>", start)
        screen = html[start:end]

        self.assertIn('data-study-part="1"', screen)
        self.assertIn("financial-study-part--introduction", screen)
        self.assertIn('src="/static/images/crediclass-logo.png"', screen)
        self.assertIn('alt="Crediclass — Aquisições Inteligentes"', screen)
        self.assertIn("Estudo Financeiro | Aquisição de Imóvel", screen)
        self.assertIn("Prezado,", screen)
        self.assertIn(
            "O presente Estudo Financeiro foi elaborado com base nas informações fornecidas e nas condições de mercado disponíveis na data de sua emissão e parâmetros abaixo.",
            screen,
        )
        self.assertIn(
            "O seu objetivo é apresentar cenários comparativos, auxiliando o cliente em seu processo de tomada de decisão.",
            screen,
        )
        self.assertIn(
            "As informações apresentadas possuem caráter informativo e ilustrativo, não constituindo garantia de resultado ou promessa de contemplação.",
            screen,
        )
        self.assertNotRegex(screen, re.compile(r"\{\{|\}\}|\$\{[^}]+\}|\b(?:cliente|grupo|cota)_\w+\b", re.I))
        self.assertIn("function clearRetiredFinancialStudyState()", app_js)
        self.assertNotIn("renderEmptyFinancialStudyScreen", app_js)
        self.assertNotIn("saveCurrentStudy", app_js)
        self.assertNotIn("openSharedStudyFromUrl", app_js)

    def test_legacy_study_backend_modules_are_absent(self):
        backend = ROOT / "backend"
        for module in ("estudos.py", "templates_estudos.py", "financial_study_engine.py", "pdf_bridge.py"):
            self.assertFalse((backend / module).exists(), module)

    def test_only_retired_template_styles_are_absent(self):
        css = (ROOT / "backend/static/css/style.css").read_text(encoding="utf-8")
        self.assertIn(".financial-study-part--introduction", css)
        for legacy_selector in (".study-v4-", ".study-template-preview-"):
            self.assertNotIn(legacy_selector, css)

    def test_production_smoke_checks_fixed_part_one(self):
        smoke = (ROOT / "scripts/production-smoke-test.mjs").read_text(encoding="utf-8")
        self.assertIn("financial study fixed introduction is served", smoke)
        self.assertIn("financial-study-part--introduction", smoke)
        self.assertIn("clearRetiredFinancialStudyState", smoke)


if __name__ == "__main__":
    unittest.main()
