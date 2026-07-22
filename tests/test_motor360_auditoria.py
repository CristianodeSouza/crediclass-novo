import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from backend.consortium_viability_engine import analyze_client_consortium_viability
from backend import motor360_auditoria


class Motor360AuditoriaTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_file = motor360_auditoria.AUDIT_FILE
        motor360_auditoria.AUDIT_FILE = Path(self.temp_dir.name) / "auditorias.json"

    def tearDown(self):
        motor360_auditoria.AUDIT_FILE = self.previous_file
        self.temp_dir.cleanup()

    def test_generates_persistable_snapshot_with_filters_and_formulas(self):
        payload = SimpleNamespace(
            objetivo="Contemplar - moderado - 12 meses", credito_desejado=950000,
            lance_proprio=100000, fgts=50000, renda_total=50000,
            parcela_desejada=6500, parcela_limite=15000, tipo_bem="", tipo_bem_explicit=False,
        )
        groups = [
            {"grupo": "100", "administradora": "ITAU", "status": "Ativo", "tipo_bem": "Imovel", "credito_minimo": 100000, "credito_maximo": 1700000, "percentual_lance_embutido": "30%", "taxa_adm": "16%", "fundo_reserva": "3%", "prazo_remanescente": 240, "parcela_inicial_grupo": 6000, "lance_super_agressivo_3m": "40%", "lance_agressivo_6m": "30%", "lance_moderado_12m": "10%", "lance_conservador_24m": "5%", "lance_investidor": "2%"},
            {"grupo": "101", "administradora": "ITAU", "status": "Inativo", "credito_maximo": 1700000},
        ]
        result = analyze_client_consortium_viability(payload, groups)
        audit = result["audit"]

        self.assertTrue(audit["metadata"]["audit_id"].startswith("AUD-"))
        self.assertEqual(audit["summary"]["total_loaded"], 2)
        self.assertEqual(
            [step["id"] for step in audit["execution_steps"]],
            ["status", "type", "credit", "term", "preselection", "contemplation_information", "preliminary_order"],
        )
        self.assertEqual(audit["execution_steps"][2]["approved_count"], 1)
        self.assertEqual(audit["formulas"][0]["result"], 1100000.0)
        self.assertEqual(audit["excluded_groups"][0]["reason"], "status_inativo")

        motor360_auditoria.save_motor360_audit(audit)
        stored = motor360_auditoria.get_motor360_audit(audit["metadata"]["audit_id"])
        self.assertEqual(stored["client_snapshot"]["consolidated_values"]["fgts"], 50000.0)
        markdown = motor360_auditoria.audit_to_markdown(stored)
        self.assertIn("Auditoria da Análise", markdown)
        self.assertIn("Pré-selecionados", markdown)
        self.assertIn("Ocorrências de campos incompletos", markdown)
        self.assertNotIn("total_incomplete", stored["summary"])


if __name__ == "__main__":
    unittest.main()
