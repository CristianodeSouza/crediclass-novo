from pathlib import Path
import unittest

from backend.main import app


ROOT = Path(__file__).resolve().parents[1]


class RetiredFinancialStudyTest(unittest.TestCase):
    def test_old_study_apis_and_public_routes_are_not_registered(self):
        paths = {route.path for route in app.routes}
        self.assertFalse(any(path.startswith("/api/estudos") for path in paths))
        self.assertFalse(any(path.startswith("/api/public-estudos") for path in paths))
        self.assertFalse(any(path.startswith("/api/templates-estudos") for path in paths))
        self.assertNotIn("/estudo/{estudo_id}", paths)

    def test_operator_tab_is_empty_and_does_not_render_legacy_content(self):
        html = (ROOT / "backend/static/index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "backend/static/js/app.js").read_text(encoding="utf-8")
        start = html.index('<section id="screen-estudo"')
        end = html.index("</section>", start)
        section = html[start:end]
        self.assertNotIn("financial-study", section)
        self.assertNotIn("studyTemplates", section)
        self.assertIn("renderEmptyFinancialStudyScreen", app_js)
        self.assertNotIn("renderFinancialStudyScreen", app_js)
        self.assertNotIn("saveCurrentStudy", app_js)
        self.assertNotIn("openSharedStudyFromUrl", app_js)

    def test_legacy_study_backend_modules_are_absent(self):
        backend = ROOT / "backend"
        for module in ("estudos.py", "templates_estudos.py", "financial_study_engine.py", "pdf_bridge.py"):
            self.assertFalse((backend / module).exists(), module)

    def test_legacy_study_styles_are_absent(self):
        css = (ROOT / "backend/static/css/style.css").read_text(encoding="utf-8")
        for legacy_selector in (".financial-study-", ".study-v4-", ".study-template-preview-"):
            self.assertNotIn(legacy_selector, css)

    def test_production_smoke_test_accepts_retired_financial_study(self):
        smoke = (ROOT / "scripts/production-smoke-test.mjs").read_text(encoding="utf-8")
        self.assertIn("renderEmptyFinancialStudyScreen", smoke)
        self.assertIn('!app.body.includes("renderFinancialStudyScreen")', smoke)


if __name__ == "__main__":
    unittest.main()
