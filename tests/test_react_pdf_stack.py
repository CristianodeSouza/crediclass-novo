import json
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import AUTH_COOKIE, app
from backend.pdf_bridge import build_react_pdf_payload, ensure_react_pdf_runtime, react_pdf_service_status, render_react_study_pdf

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_JSON = ROOT / "backend" / "pdf_service" / "package.json"
RENDERER = ROOT / "backend" / "pdf_service" / "render-study-pdf.mjs"
BRIDGE = ROOT / "backend" / "pdf_bridge.py"
MAIN = ROOT / "backend" / "main.py"
DOCKERFILE = ROOT / "Dockerfile"


class ReactPdfStackTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sample_study = {
            "estudo_id": "EST-TESTE",
            "proposal_id": "PROP-1",
            "criado_em": "2026-08-28T08:30:00",
            "status": "Concluido",
            "operador": "Codex",
            "grupo_id": "40004",
            "cliente": {
                "nome": "Cliente Teste",
                "objetivo": "Aquisicao de Imovel",
                "credito_desejado": 300000,
                "prazo_desejado": 192,
                "parcela_desejada": 2800,
                "renda_total": 12000,
            },
            "grupo": {
                "administradora": "Itau",
                "grupo": "40004",
                "tipo_bem": "Imovel",
                "prazo_restante": 192,
                "taxa_ano": 0.12,
                "taxa_adm": 0.36,
                "limite_adesao": "2026-09-11",
                "proxima_assembleia": "2026-09-25",
                "vencimento_primeira_parcela": "2026-09-20",
                "vencimento_lance": "2026-09-15",
                "historico": {
                    "2026-06": {"menor_lance": 0.45, "qtd_contemplacoes": 4},
                    "2026-07": {"menor_lance": 0.47, "qtd_contemplacoes": 5},
                    "2026-08": {"menor_lance": 0.50, "qtd_contemplacoes": 6},
                },
            },
            "financeiro": {
                "credito": 300000,
                "credito_original": 337409,
                "recurso_proprio": 300000,
                "fgts_utilizado": 0,
                "lance_embutido": 0,
                "valor_total_lance": 300000,
                "percentual_lance_total": 0.5,
                "parcela_inicial": 2864.46,
                "custo_efetivo_total": 549976.67,
                "chance_contemplacao": "Referencia operacional",
                "estrategia_recomendada": "Rapido - 6 meses",
                "estrategias": [
                    {
                        "estrategia": "Investidor",
                        "percentual_lance": 0.42,
                        "lance_embutido": 0,
                        "lance_proprio": 143162.64,
                        "credito_disponivel": 337409,
                        "prazo_operacional": "Sem urgencia",
                    },
                    {
                        "estrategia": "Conservador",
                        "percentual_lance": 0.51,
                        "lance_embutido": 0,
                        "lance_proprio": 151613.48,
                        "credito_disponivel": 337409,
                        "prazo_operacional": "Ate 24 meses",
                    },
                ],
            },
            "template_campos": {"observacoes": "Observacao de teste"},
        }

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
        self.assertIn("SIMULACAO MELHORES CONSORCIOS", source)
        self.assertIn("DATAS LIMITES PARA ADESAO", source)
        self.assertIn("HISTORICO DE LANCES CONTEMPLADOS", source)

    def test_fastapi_bridge_and_endpoint_exist(self):
        bridge = BRIDGE.read_text(encoding="utf-8")
        main = MAIN.read_text(encoding="utf-8")
        self.assertIn("def react_pdf_service_status()", bridge)
        self.assertIn("def render_react_study_pdf(", bridge)
        self.assertIn('/api/estudos/{estudo_id}/exportar-pdf-react', main)
        self.assertIn('/api/estudos/preview-pdf', main)
        self.assertIn('/api/estudos/pdf-engine-status', main)
        self.assertIn('/api/health/pdf-engine', main)
        self.assertIn('raise RuntimeError("React-pdf indisponivel neste ambiente. O motor PDF canonico nao esta operacional.")', main)
        self.assertIn('"engine": "react-pdf"', main)
        self.assertNotIn("PDF gerado com motor legado", main)

    def test_bridge_builds_enriched_payload(self):
        payload = build_react_pdf_payload(self.sample_study, "4.0.99")
        self.assertEqual(payload["group"]["administrator"], "Itau")
        self.assertEqual(payload["sections"]["historyMatrix"]["months"], ["jun/26", "jul/26", "ago/26"])
        self.assertEqual(payload["sections"]["contractRows"][0]["group"], "Grupo 40004")
        self.assertEqual(payload["sections"]["deadlineRows"][0]["nextAssembly"], "25/09/2026")
        self.assertGreaterEqual(len(payload["sections"]["selectionCriteria"]), 5)

    def test_bridge_tolera_percentuais_e_valores_localizados(self):
        study = json.loads(json.dumps(self.sample_study))
        study["financeiro"]["credito_original"] = "337.409,00"
        study["financeiro"]["estrategias"][0]["percentual_lance"] = "42,43%"
        payload = build_react_pdf_payload(study, "4.0.106")
        self.assertEqual(payload["sections"]["projectionRows"][0]["percent"], "42,43%")
        self.assertEqual(payload["sections"]["projectionRows"][0]["totalBid"], "R$ 143.162,64")

    def test_bridge_procura_node_local_empacotado(self):
        bridge = BRIDGE.read_text(encoding="utf-8")
        self.assertIn('PDF_SERVICE_NODEENV_DIR = PDF_SERVICE_DIR / ".nodeenv"', bridge)
        self.assertIn('PDF_SERVICE_NODEENV_DIR / "bin" / "node"', bridge)
        self.assertIn('PDF_SERVICE_NODEENV_DIR / "Scripts" / "node.exe"', bridge)
        self.assertIn('def _npm_binary() -> str | None:', bridge)
        self.assertIn('[npm_path, "ci", "--prefix", str(PDF_SERVICE_DIR), "--omit=dev"]', bridge)

    def test_render_blueprint_bootstraps_pdf_runtime_before_start(self):
        render_yaml = (ROOT / "render.yaml").read_text(encoding="utf-8")
        self.assertIn("runtime: docker", render_yaml)
        self.assertIn("dockerfilePath: ./Dockerfile", render_yaml)
        self.assertIn("dockerContext: .", render_yaml)

    def test_dockerfile_bakes_python_node_and_react_pdf_runtime(self):
        dockerfile = DOCKERFILE.read_text(encoding="utf-8")
        self.assertIn("FROM python:3.12.4-slim", dockerfile)
        self.assertIn("https://deb.nodesource.com/node_24.x", dockerfile)
        self.assertIn("RUN pip install --no-cache-dir -r requirements.txt", dockerfile)
        self.assertIn("RUN npm ci --prefix backend/pdf_service --omit=dev", dockerfile)
        self.assertIn("RUN python scripts/ensure_pdf_service.py", dockerfile)
        self.assertIn("python scripts/ensure_pdf_service.py && python -m uvicorn backend.main:app", dockerfile)

    def test_ensure_runtime_installs_when_dependencies_are_missing(self):
        with patch("backend.pdf_bridge.react_pdf_service_status", side_effect=[
            {"available": False, "node": "node", "npm": "npm", "entrypoint": "render-study-pdf.mjs", "package_json": True, "dependencies_installed": False},
            {"available": True, "node": "node", "npm": "npm", "entrypoint": "render-study-pdf.mjs", "package_json": True, "dependencies_installed": True},
        ]), patch("backend.pdf_bridge._npm_binary", return_value="npm"), patch("backend.pdf_bridge._node_binary", return_value="node"), patch(
            "backend.pdf_bridge.PDF_SERVICE_PACKAGE", new=type("Pkg", (), {"exists": staticmethod(lambda: True), "__str__": staticmethod(lambda: "package.json")})()
        ), patch("backend.pdf_bridge.subprocess.run") as run_mock:
            run_mock.return_value.returncode = 0
            run_mock.return_value.stdout = b""
            run_mock.return_value.stderr = b""
            status = ensure_react_pdf_runtime()

        self.assertTrue(status["available"])
        run_mock.assert_called_once()

    def test_renderer_outputs_pdf_bytes(self):
        if not react_pdf_service_status()["available"]:
            self.skipTest("React-pdf indisponivel no ambiente de teste.")
        content = render_react_study_pdf(self.sample_study, "4.0.99")
        self.assertTrue(content.startswith(b"%PDF"))
        self.assertGreater(len(content), 1000)

    def test_preview_endpoint_returns_real_react_pdf(self):
        client = TestClient(app)
        login = client.post("/api/auth/login", json={"usuario": "adm", "senha": "cristiano"})
        self.assertEqual(login.status_code, 200)
        self.assertIn(AUTH_COOKIE, login.cookies)
        with patch("backend.main.get_grupo", return_value={"grupo": "40004", "administradora": "Itau"}), patch(
            "backend.main.react_pdf_service_status",
            return_value={"available": True, "node": "node", "entrypoint": "render-study-pdf.mjs", "dependencies_installed": True},
        ), patch("backend.main.render_react_study_pdf", return_value=b"%PDF-1.4\nmock"):
            response = client.post(
                "/api/estudos/preview-pdf",
                json={
                    "cliente": {"nome": "Cliente Teste", "credito_desejado": 300000},
                    "grupo_id": "40004",
                    "grupo": {"grupo": "40004", "administradora": "Itau"},
                    "cenario": {"credito_liquido_total": 300000},
                    "template_campos": {},
                },
            )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["engine"], "react-pdf")
        pdf_response = client.get(payload["download_url"])
        self.assertEqual(pdf_response.status_code, 200)
        self.assertTrue(pdf_response.content.startswith(b"%PDF"))

    def test_preview_endpoint_fails_clearly_when_react_pdf_is_unavailable(self):
        client = TestClient(app)
        client.post("/api/auth/login", json={"usuario": "adm", "senha": "cristiano"})
        with patch("backend.main.get_grupo", return_value={"grupo": "40004", "administradora": "Itau"}), patch(
            "backend.main.react_pdf_service_status",
            return_value={"available": False, "node": None, "entrypoint": "render-study-pdf.mjs", "dependencies_installed": False},
        ):
            response = client.post(
                "/api/estudos/preview-pdf",
                json={
                    "cliente": {"nome": "Cliente Teste", "credito_desejado": 300000},
                    "grupo_id": "40004",
                },
            )
        self.assertEqual(response.status_code, 503)
        payload = response.json()
        self.assertFalse(payload["success"])
        self.assertEqual(payload["engine"], "react-pdf")
        self.assertIn("motor PDF canonico", payload["error"])

    def test_pdf_engine_healthcheck_reports_failure_with_503(self):
        client = TestClient(app)
        with patch(
            "backend.main.react_pdf_service_status",
            return_value={"available": False, "node": None, "entrypoint": "render-study-pdf.mjs", "dependencies_installed": False},
        ):
            response = client.get("/api/health/pdf-engine")
        self.assertEqual(response.status_code, 503)
        payload = response.json()
        self.assertFalse(payload["success"])
        self.assertEqual(payload["engine"], "react-pdf")


if __name__ == "__main__":
    unittest.main()
