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

        self.assertIn("/static/js/app.js?v=20260604-19", index_html)

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


if __name__ == "__main__":
    unittest.main()
