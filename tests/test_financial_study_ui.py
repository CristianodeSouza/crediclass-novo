import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_JS = ROOT / "backend" / "static" / "js" / "app.js"
STYLE_CSS = ROOT / "backend" / "static" / "css" / "style.css"


class FinancialStudyUiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.javascript = APP_JS.read_text(encoding="utf-8")
        cls.styles = STYLE_CSS.read_text(encoding="utf-8")

    def test_estudo_carrega_agenda_de_assembleias(self):
        self.assertIn('apiGet("/mapa-assembleia")', self.javascript)
        self.assertIn("financialStudyAssemblyAgenda", self.javascript)
        self.assertIn("Agenda de contratação e assembleias", self.javascript)

    def test_agenda_filtra_datas_anteriores_a_emissao(self):
        self.assertIn("start.setHours(0, 0, 0, 0)", self.javascript)
        self.assertIn("date >= start", self.javascript)
        self.assertIn("Estudo gerado em", self.javascript)

    def test_agenda_possui_layout_responsivo_e_impressao(self):
        self.assertIn(".financial-study-deadlines", self.styles)
        self.assertIn(".financial-study-agenda-cycles", self.styles)
        self.assertIn("@media (max-width: 900px)", self.styles)
        self.assertIn("@media print", self.styles)


if __name__ == "__main__":
    unittest.main()
