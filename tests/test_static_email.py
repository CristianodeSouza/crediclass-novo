import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class StaticEmailTest(unittest.TestCase):
    def test_estudos_email_usa_cliente_de_email(self):
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")

        self.assertIn("function emailCurrentStudy()", app_js)
        self.assertIn("function emailHistoryStudy(studyId)", app_js)
        self.assertIn("mailto:?subject=", app_js)
        self.assertNotIn("Envio por e-mail depende de SMTP configurado.", app_js)

    def test_index_referencia_app_js_atualizado(self):
        index_html = (ROOT / "backend" / "static" / "index.html").read_text(encoding="utf-8")

        self.assertIn("/static/js/app.js?v=20260604-25", index_html)

    def test_exportacao_csv_disponivel_para_grupos_e_estudos(self):
        index_html = (ROOT / "backend" / "static" / "index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")

        self.assertIn('id="exportGroupsCsvBtn"', index_html)
        self.assertIn('id="exportStudiesCsvBtn"', index_html)
        self.assertIn("function downloadCsv(filename, rows)", app_js)
        self.assertIn("function exportGroupsCsv()", app_js)
        self.assertIn("function exportStudiesCsv()", app_js)
        self.assertIn("text/csv;charset=utf-8", app_js)
        self.assertIn("crediclass-grupos-", app_js)
        self.assertIn("crediclass-estudos-", app_js)

    def test_backup_logs_disponivel_em_configuracoes(self):
        index_html = (ROOT / "backend" / "static" / "index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")
        style_css = (ROOT / "backend" / "static" / "css" / "style.css").read_text(encoding="utf-8")

        self.assertIn("Backup & Logs", index_html)
        self.assertIn('id="downloadConfigBackupBtn"', index_html)
        self.assertIn('id="operationalLogsList"', index_html)
        self.assertIn("function downloadConfigBackup()", app_js)
        self.assertIn("function addOperationalLog(message)", app_js)
        self.assertIn("application/json;charset=utf-8", app_js)
        self.assertIn("crediclass-configuracoes-", app_js)
        self.assertIn(".log-list", style_css)

    def test_crud_grupos_salva_historico_mensal(self):
        index_html = (ROOT / "backend" / "static" / "index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")

        self.assertIn("Atualizacao Mensal", index_html)
        self.assertIn('id="groupFormHistoryMes"', index_html)
        self.assertIn('id="groupFormHistoryMaior"', index_html)
        self.assertIn('id="groupFormHistoryMenor"', index_html)
        self.assertIn('id="groupFormHistoryQtd"', index_html)
        self.assertIn("function collectMonthlyHistoryPayload(prefix)", app_js)
        self.assertIn('collectMonthlyHistoryPayload("groupFormHistory")', app_js)
        self.assertIn('/historico`, historyPayload)', app_js)

    def test_detalhe_grupo_renderiza_auditoria(self):
        index_html = (ROOT / "backend" / "static" / "index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")
        style_css = (ROOT / "backend" / "static" / "css" / "style.css").read_text(encoding="utf-8")

        self.assertIn('id="detailsAuditList"', index_html)
        self.assertIn("function renderDetailsAudit(group)", app_js)
        self.assertIn("renderDetailsAudit(group)", app_js)
        self.assertIn(".audit-list", style_css)

    def test_acao_principal_salva_estudo_financeiro(self):
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")

        self.assertIn('document.getElementById("screen-estudo").classList.contains("active")', app_js)
        self.assertIn("saveCurrentStudy().catch(() => setStudyState(\"error\"))", app_js)
        self.assertNotIn("Funcionalidade sera implementada na etapa correspondente.", app_js)

    def test_tema_configurado_aplica_aparencia(self):
        index_html = (ROOT / "backend" / "static" / "index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")
        style_css = (ROOT / "backend" / "static" / "css" / "style.css").read_text(encoding="utf-8")

        self.assertIn("/static/css/style.css?v=20260604-20", index_html)
        self.assertIn('id="configTema"', index_html)
        self.assertIn("function applyTheme(theme)", app_js)
        self.assertIn("document.body.dataset.theme", app_js)
        self.assertIn('document.getElementById("configTema").addEventListener("change"', app_js)
        self.assertIn('body[data-theme="escuro"]', style_css)

    def test_preferencias_configuracoes_expoem_campos_obrigatorios(self):
        index_html = (ROOT / "backend" / "static" / "index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")

        for field_id in [
            "configCasasValores",
            "configCasasPercentuais",
            "configMeiaParcela",
            "configLanceEmbutido",
            "configHistorico36",
        ]:
            self.assertIn(f'id="{field_id}"', index_html)
            self.assertIn(field_id, app_js)

        self.assertIn("function setSelectBool(id, value)", app_js)
        self.assertIn("function getSelectBool(id)", app_js)
        self.assertIn("casas_decimais_valores", app_js)
        self.assertIn("ativar_lance_embutido", app_js)

    def test_notificacoes_configuracoes_disponiveis(self):
        index_html = (ROOT / "backend" / "static" / "index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")

        self.assertIn("configNotificacoes", index_html)
        for field_id in ["notifySync", "notifyStudySaved", "notifyHistoryUpdated", "notifyIntegrationFailure"]:
            self.assertIn(f'id="{field_id}"', index_html)
            self.assertIn(field_id, app_js)

        self.assertIn("notificacoes", app_js)
        self.assertIn("alertar_sincronizacao", app_js)
        self.assertIn("alertar_falha_integracao", app_js)

    def test_notificacoes_controlam_alertas_operacionais(self):
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")

        self.assertIn("function isNotificationEnabled(key)", app_js)
        self.assertIn("function notifyWhen(key, message, type = \"success\")", app_js)
        self.assertIn('notifyWhen("alertar_sincronizacao"', app_js)
        self.assertIn('notifyWhen("alertar_estudo_salvo"', app_js)
        self.assertIn('notifyWhen("alertar_historico_atualizado"', app_js)
        self.assertIn('notifyWhen("alertar_falha_integracao"', app_js)


if __name__ == "__main__":
    unittest.main()
