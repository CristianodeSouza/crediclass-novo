import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.estudos import build_estudo_audit_payload, build_estudo_preview, create_estudo, delete_estudo, export_estudo_pdf, export_estudo_pdf_payload, get_estudo, list_estudos
from backend.models import EstudoCliente, EstudoRequest
from backend import estudos as estudos_module


class EstudosTest(unittest.TestCase):
    def test_criar_estudo_valida_grupo_e_retorna_id(self):
        payload = EstudoRequest(
            cliente=EstudoCliente(
                nome="Cliente Teste",
                credito_desejado=500000,
                prazo_desejado=24,
                lance_proprio=80000,
                fgts=20000,
                parcela_desejada=3500,
                data_nascimento_conjuge="1988-02-03",
            ),
            grupo_id="128",
        )
        fake_group = {
            "grupo_id": "128",
            "credito_maximo": 800000,
            "taxa_adm": 0.2,
            "fundo_reserva": 0.03,
            "prazo_restante": 180,
            "percentual_lance_embutido": 0.3,
            "percentual_lance_fixo": 0.25,
            "conservador": 0.2,
            "moderado": 0.3,
            "agressivo": 0.45,
            "historico": {"2026-01": {"maior_lance": 0.72, "menor_lance": 0.24, "qtd_contemplacoes": 12}},
        }

        result = create_estudo(payload, grupo=fake_group, operador="Operador Teste")

        self.assertTrue(result["success"])
        self.assertTrue(result["estudo_id"].startswith("EST-"))
        detail = get_estudo(result["estudo_id"])
        self.assertGreater(detail["financeiro"]["credito_original"], 500000)
        self.assertEqual(len(detail["financeiro"]["estrategias"]), 5)
        self.assertEqual(detail["financeiro"]["historico_12_meses"]["total_contemplacoes"], 12)
        self.assertEqual(detail["cliente"]["data_nascimento_conjuge"], "1988-02-03")
        self.assertEqual(detail["status"], "Concluido")
        self.assertEqual(detail["operador"], "Operador Teste")

    def test_criar_estudo_persiste_campos_do_template(self):
        payload = EstudoRequest(
            cliente=EstudoCliente(nome="Cliente Template", credito_desejado=400000),
            grupo_id="128",
            template_campos={
                "observacoes_comerciais": "Cliente prefere comunicacao por WhatsApp.",
                "comentario_cliente": "Estudo gerado com base no grupo selecionado.",
            },
        )

        created = create_estudo(payload, grupo={"grupo_id": "128", "grupo": "128"})

        detail = get_estudo(created["estudo_id"])
        self.assertEqual(
            detail["template_campos"]["observacoes_comerciais"],
            "Cliente prefere comunicacao por WhatsApp.",
        )

    def test_listar_obter_e_excluir_estudo(self):
        payload = EstudoRequest(
            cliente=EstudoCliente(nome="Cliente Historico", credito_desejado=300000),
            grupo_id="017",
        )

        created = create_estudo(payload, grupo={"grupo_id": "017", "grupo": "017"})

        listed = list_estudos()
        self.assertTrue(any(item["estudo_id"] == created["estudo_id"] for item in listed))

        detail = get_estudo(created["estudo_id"])
        self.assertEqual(detail["cliente"]["nome"], "Cliente Historico")

        deleted = delete_estudo(created["estudo_id"])
        self.assertTrue(deleted)
        canceled = get_estudo(created["estudo_id"])
        self.assertEqual(canceled["status"], "Cancelado")

    def test_export_estudo_pdf_gera_arquivo(self):
        payload = EstudoRequest(
            cliente=EstudoCliente(nome="Cliente PDF", credito_desejado=250000, lance_proprio=50000),
            grupo_id="128",
        )

        created = create_estudo(payload, grupo={"grupo_id": "128", "grupo": "128", "administradora": "Itau"})

        with tempfile.TemporaryDirectory() as temp_dir:
            filename = export_estudo_pdf(created["estudo_id"], Path(temp_dir))
            content = (Path(temp_dir) / filename).read_bytes()

        self.assertEqual(filename, f"{created['estudo_id']}.pdf")
        self.assertTrue(content.startswith(b"%PDF"))

    def test_export_estudo_pdf_payload_gera_arquivo_sem_rebuscar_estudo(self):
        study = {
            "estudo_id": "EST-PAYLOAD",
            "cliente": {"nome": "Cliente Payload", "credito_desejado": 250000},
            "grupo": {"grupo": "40004", "administradora": "Itau"},
            "financeiro": {"credito": 250000, "estrategias": []},
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            filename = export_estudo_pdf_payload(study, Path(temp_dir))
            content = (Path(temp_dir) / filename).read_bytes()

        self.assertEqual(filename, "EST-PAYLOAD.pdf")
        self.assertTrue(content.startswith(b"%PDF"))

    def test_build_estudo_preview_usa_dados_em_memoria_sem_persistir(self):
        payload = estudos_module.EstudoPreviewRequest(
            cliente=EstudoCliente(nome="Cliente Prévia", credito_desejado=300000),
            grupo_id="40004",
            grupo={"grupo": "40004", "administradora": "Itau"},
            cenario={"credito_liquido_total": 300000, "credito_contratado_total": 337409, "estrategia": "Rapido - 6 meses"},
            template_campos={"observacao": "teste"},
            motor360_audit_id="AUD-TESTE",
        )
        preview = build_estudo_preview(payload, grupo=payload.grupo, operador="Operador Preview")

        self.assertEqual(preview["estudo_id"], "PREVIEW")
        self.assertEqual(preview["status"], "Previa")
        self.assertEqual(preview["grupo"]["administradora"], "Itau")
        self.assertEqual(preview["operador"], "Operador Preview")

    def test_build_estudo_audit_payload_consolida_rastreabilidade(self):
        payload = estudos_module.EstudoPreviewRequest(
            cliente=EstudoCliente(nome="Cliente Auditoria", credito_desejado=320000),
            grupo_id="40004",
            grupo={"grupo": "40004", "administradora": "Itau"},
            cenario={"credito_liquido_total": 300000},
            template_campos={"observacao": "teste"},
            motor360_audit_id="AUD-TESTE",
        )
        audit = build_estudo_audit_payload(
            payload,
            grupo=payload.grupo,
            operador="Operador Auditoria",
            motor360_audit={"metadata": {"audit_id": "AUD-TESTE"}},
            group_audit=[{"acao": "Leitura"}],
            pdf_engine_status={"available": True},
        )

        self.assertEqual(audit["audit_type"], "financial_study_runtime")
        self.assertEqual(audit["study"]["grupo_id"], "40004")
        self.assertEqual(audit["study"]["operador"], "Operador Auditoria")
        self.assertEqual(audit["motor360_audit_id"], "AUD-TESTE")
        self.assertEqual(audit["group_audit_trail"][0]["acao"], "Leitura")
        self.assertTrue(audit["pdf_engine_status"]["available"])

    def test_criterio_de_aceite_pipeline_pdf_canonico_usa_react_pdf(self):
        main_source = Path(estudos_module.__file__).resolve().parent.joinpath("main.py").read_text(encoding="utf-8")

        self.assertIn("def _render_study_pdf_file(estudo: dict, filename: str) -> dict:", main_source)
        self.assertIn('raise RuntimeError("React-pdf indisponivel neste ambiente. O motor PDF canonico nao esta operacional.")', main_source)
        self.assertIn('@app.post("/api/estudos/preview-pdf")', main_source)
        self.assertIn('@app.get("/api/health/pdf-engine")', main_source)
        self.assertIn('@app.post("/api/estudos/preview-audit")', main_source)
        self.assertNotIn("PDF gerado com motor legado", main_source)

    def test_persistencia_estudos_json(self):
        original_studies = dict(estudos_module._studies)
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                runtime_dir = Path(temp_dir)
                with patch.object(estudos_module, "RUNTIME_DIR", runtime_dir), patch.object(estudos_module, "STUDIES_FILE", runtime_dir / "studies.json"):
                    estudos_module._studies.clear()
                    estudos_module._studies["EST-2026-00009"] = {"estudo_id": "EST-2026-00009", "status": "Concluido"}
                    estudos_module.save_studies_to_disk()
                    loaded = estudos_module.load_studies_from_disk()
        finally:
            estudos_module._studies.clear()
            estudos_module._studies.update(original_studies)

        self.assertEqual(loaded["EST-2026-00009"]["status"], "Concluido")


if __name__ == "__main__":
    unittest.main()
