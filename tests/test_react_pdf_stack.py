import json
import unittest
from pathlib import Path

from backend.pdf_bridge import build_react_pdf_payload, react_pdf_service_status, render_react_study_pdf

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_JSON = ROOT / "backend" / "pdf_service" / "package.json"
RENDERER = ROOT / "backend" / "pdf_service" / "render-study-pdf.mjs"
BRIDGE = ROOT / "backend" / "pdf_bridge.py"
MAIN = ROOT / "backend" / "main.py"


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
        self.assertIn('/api/estudos/pdf-engine-status', main)
        self.assertIn('engine = "react-pdf"', main)
        self.assertIn('warning = "React-pdf indisponivel neste ambiente. PDF gerado com motor legado."', main)
        self.assertIn('warning = "React-pdf indisponivel para este estudo. PDF gerado com motor legado."', main)

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
        payload = build_react_pdf_payload(study, "4.0.104")
        self.assertEqual(payload["sections"]["projectionRows"][0]["percent"], "42,43%")
        self.assertEqual(payload["sections"]["projectionRows"][0]["totalBid"], "R$ 143.162,64")

    def test_bridge_procura_node_local_empacotado(self):
        bridge = BRIDGE.read_text(encoding="utf-8")
        self.assertIn('PDF_SERVICE_NODEENV_DIR = PDF_SERVICE_DIR / ".nodeenv"', bridge)
        self.assertIn('PDF_SERVICE_NODEENV_DIR / "bin" / "node"', bridge)
        self.assertIn('PDF_SERVICE_NODEENV_DIR / "Scripts" / "node.exe"', bridge)

    def test_renderer_outputs_pdf_bytes(self):
        if not react_pdf_service_status()["available"]:
            self.skipTest("React-pdf indisponivel no ambiente de teste.")
        content = render_react_study_pdf(self.sample_study, "4.0.99")
        self.assertTrue(content.startswith(b"%PDF"))
        self.assertGreater(len(content), 1000)


if __name__ == "__main__":
    unittest.main()
