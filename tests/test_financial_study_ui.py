import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_JS = ROOT / "backend" / "static" / "js" / "app.js"
STYLE_CSS = ROOT / "backend" / "static" / "css" / "style.css"
INDEX_HTML = ROOT / "backend" / "static" / "index.html"


class FinancialStudyUiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.javascript = APP_JS.read_text(encoding="utf-8")
        cls.styles = STYLE_CSS.read_text(encoding="utf-8")
        cls.index_html = INDEX_HTML.read_text(encoding="utf-8")

    def test_estudo_carrega_agenda_de_assembleias(self):
        self.assertIn('apiGet("/mapa-assembleia")', self.javascript)
        self.assertIn("financialStudyAssemblyAgenda", self.javascript)
        self.assertIn("Limite Adesão - Reserva Vagas Grupos", self.javascript)
        self.assertIn("Limite Adesão - Assembleia", self.javascript)
        self.assertIn("Vencimento Pagamento Lance", self.javascript)
        self.assertIn("byId.pagamento_lance", self.javascript)
        self.assertNotIn("financial-study-pdf-table-deadlines-agenda", self.javascript)

    def test_agenda_filtra_datas_anteriores_a_emissao(self):
        self.assertIn("start.setHours(0, 0, 0, 0)", self.javascript)
        self.assertIn("date >= start", self.javascript)
        self.assertIn("Estudo gerado em", self.javascript)

    def test_agenda_possui_layout_responsivo_e_impressao(self):
        self.assertIn(".financial-study-deadlines", self.styles)
        self.assertIn(".financial-study-agenda-cycles", self.styles)
        self.assertIn("@media (max-width: 900px)", self.styles)
        self.assertIn("@media print", self.styles)

    def test_previa_do_pdf_e_renderizada_em_modal_dedicado(self):
        self.assertIn('id="financialStudyPreviewModal"', self.index_html)
        self.assertIn('id="financialStudyPreviewContent"', self.index_html)
        self.assertIn('id="financialStudyPreviewSubtitle"', self.index_html)
        self.assertIn('/static/js/app.js?v=4.0.105', self.index_html)
        self.assertIn('data-study-open-preview', self.javascript)
        self.assertIn('bootstrap.Modal.getOrCreateInstance(previewModal).show()', self.javascript)
        self.assertIn("generateStudyPdfArtifact()", self.javascript)
        self.assertIn('|| previewModal?.querySelector(".modal-subtitle")', self.javascript)
        self.assertIn("if (previewSubtitle) {", self.javascript)
        self.assertIn('previewContent.innerHTML = `<iframe class="financial-study-preview-frame"', self.javascript)
        self.assertIn('previewPrintButton.onclick = () => exportStudyPdf().catch(() => showToast("Nao foi possivel gerar o PDF.", "danger"))', self.javascript)
        self.assertNotIn("previewPrintButton.onclick = () => window.print()", self.javascript)
        self.assertIn(".financial-study-preview-dialog", self.styles)
        self.assertIn(".financial-study-preview-frame", self.styles)
        self.assertIn("--financial-study-a4-width: 210mm;", self.styles)
        self.assertIn("--financial-study-a4-height: 297mm;", self.styles)
        self.assertIn("width: var(--financial-study-a4-width);", self.styles)
        self.assertIn("min-height: var(--financial-study-a4-height);", self.styles)
        self.assertIn("overflow: hidden;", self.styles)
        self.assertIn("word-break: break-word;", self.styles)

    def test_estudo_reaproveita_cenario_sem_embutido_quando_x_ausente(self):
        self.assertIn("function fallbackScenarioForDisplay(item, scenarioId)", self.javascript)
        self.assertIn('scenario.creation_reason !== "percentual_x_ausente"', self.javascript)
        self.assertIn('const withEmbedded = fallbackScenarioForDisplay(item, "with_embedded")', self.javascript)

    def test_previa_html_usa_intro_editorial_sem_coluna_espremida(self):
        self.assertIn("function financialStudyPdfIntroSection(", self.javascript)
        self.assertIn('class="financial-study-pdf-intro-copy"', self.javascript)
        self.assertIn(".financial-study-pdf-intro-copy", self.styles)
        self.assertIn("width: min(calc(var(--financial-study-a4-width) + 24mm), 100%);", self.styles)
        self.assertNotIn("financial-study-pdf-client-meta", self.javascript)
        self.assertIn("const totalPages = pages.length;", self.javascript)
        self.assertNotIn("financialStudyPdfPage(1, 4", self.javascript)
        self.assertIn("Prévia em PDF", self.javascript)

    def test_bloco_melhores_consorcios_tem_texto_padrao_e_administradora_dinamica(self):
        self.assertIn('Administradora selecionada: <strong>${escapeHtml(administrator)}</strong>', self.javascript)
        self.assertIn("Os grupos apresentados foram selecionados", self.javascript)
        self.assertIn("Contemplações Mensais:", self.javascript)
        self.assertIn("Uso da Carta de Crédito:", self.javascript)
        self.assertIn("<strong>1 - Grupos antigos:</strong> mais participantes já contemplados", self.javascript)
        self.assertIn("<strong>1) Sorteio:</strong> Participam do sorteio", self.javascript)
        self.assertIn(".financial-study-pdf-table-editorial td p {", self.styles)

    def test_simulacao_de_investimento_usa_apenas_tabela_expandida(self):
        self.assertIn("Simulação dinâmica usando o estudo atual e o grupo em destaque.", self.javascript)
        self.assertIn("financial-study-pdf-table-investment-wide", self.javascript)
        self.assertIn(".financial-study-pdf-table-investment-wide", self.styles)
        self.assertNotIn('eyebrow: "Simulação dinâmica"', self.javascript)

    def test_exportacao_pdf_exibe_motor_utilizado(self):
        self.assertIn('result.engine === "react-pdf" ? "PDF gerado com React-pdf." : "PDF gerado com motor legado."', self.javascript)
        self.assertIn("if (result.warning) {", self.javascript)


if __name__ == "__main__":
    unittest.main()
