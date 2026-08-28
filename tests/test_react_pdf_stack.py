import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_JSON = ROOT / "backend" / "pdf_service" / "package.json"
RENDERER = ROOT / "backend" / "pdf_service" / "render-study-pdf.mjs"
BRIDGE = ROOT / "backend" / "pdf_bridge.py"
MAIN = ROOT / "backend" / "main.py"


class ReactPdfStackTest(unittest.TestCase):
    def test_package_declares_react_pdf_renderer(self):
        payload = json.loads(PACKAGE_JSON.read_text(encoding="utf-8"))
        self.assertEqual(payload["name"], "crediclass-react-pdf-service")
        self.assertIn("@react-pdf/renderer", payload["dependencies"])
        self.assertIn("react", payload["dependencies"])

    def test_renderer_has_document_entrypoint(self):
        source = RENDERER.read_text(encoding="utf-8")
        self.assertIn("renderToBuffer", source)
        self.assertIn("function StudyDocument", source)
        self.assertIn('size: "A4"', source)

    def test_fastapi_bridge_and_endpoint_exist(self):
        bridge = BRIDGE.read_text(encoding="utf-8")
        main = MAIN.read_text(encoding="utf-8")
        self.assertIn("def react_pdf_service_status()", bridge)
        self.assertIn("def render_react_study_pdf(", bridge)
        self.assertIn('/api/estudos/{estudo_id}/exportar-pdf-react', main)
        self.assertIn('/api/estudos/pdf-engine-status', main)
        self.assertIn('engine = "react-pdf"', main)
        self.assertIn('warning = "React-pdf indisponivel neste ambiente. PDF gerado com motor legado."', main)
        self.assertIn('warning = "React-pdf indisponivel para este estudo. PDF gerado com motor legado."', main)


if __name__ == "__main__":
    unittest.main()
