import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.main import estudos_criar, estudos_excluir, estudos_listar, estudos_obter
from backend.models import EstudoCliente, EstudoRequest
from backend import estudos as estudos_module
from backend.estudos import export_estudo_pdf


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

        with patch("backend.main.get_grupo", return_value=fake_group):
            result = estudos_criar(payload)

        self.assertTrue(result["success"])
        self.assertTrue(result["estudo_id"].startswith("EST-"))
        detail = estudos_obter(result["estudo_id"])
        self.assertGreater(detail["financeiro"]["credito_original"], 500000)
        self.assertEqual(len(detail["financeiro"]["estrategias"]), 5)
        self.assertEqual(detail["financeiro"]["historico_12_meses"]["total_contemplacoes"], 12)
        self.assertEqual(detail["cliente"]["data_nascimento_conjuge"], "1988-02-03")
        self.assertEqual(detail["status"], "Concluido")

    def test_criar_estudo_persiste_campos_do_template(self):
        payload = EstudoRequest(
            cliente=EstudoCliente(nome="Cliente Template", credito_desejado=400000),
            grupo_id="128",
            template_campos={
                "observacoes_comerciais": "Cliente prefere comunicacao por WhatsApp.",
                "comentario_cliente": "Estudo gerado com base no grupo selecionado.",
            },
        )

        with patch("backend.main.get_grupo", return_value={"grupo_id": "128", "grupo": "128"}):
            created = estudos_criar(payload)

        detail = estudos_obter(created["estudo_id"])
        self.assertEqual(
            detail["template_campos"]["observacoes_comerciais"],
            "Cliente prefere comunicacao por WhatsApp.",
        )

    def test_listar_obter_e_excluir_estudo(self):
        payload = EstudoRequest(
            cliente=EstudoCliente(nome="Cliente Historico", credito_desejado=300000),
            grupo_id="017",
        )

        with patch("backend.main.get_grupo", return_value={"grupo_id": "017", "grupo": "017"}):
            created = estudos_criar(payload)

        listed = estudos_listar(cliente="Historico")
        self.assertGreaterEqual(listed["total"], 1)

        detail = estudos_obter(created["estudo_id"])
        self.assertEqual(detail["cliente"]["nome"], "Cliente Historico")

        deleted = estudos_excluir(created["estudo_id"])
        self.assertTrue(deleted["success"])
        canceled = estudos_obter(created["estudo_id"])
        self.assertEqual(canceled["status"], "Cancelado")

    def test_listar_estudos_filtra_por_periodo(self):
        items = [
            {"estudo_id": "EST-1", "criado_em": "2026-06-01T10:00:00", "cliente": {}, "grupo": {}, "financeiro": {}},
            {"estudo_id": "EST-2", "criado_em": "2026-06-04T10:00:00", "cliente": {}, "grupo": {}, "financeiro": {}},
        ]

        with patch("backend.main.list_estudos", return_value=items):
            result = estudos_listar(data_inicio="2026-06-02", data_fim="2026-06-04")

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["estudo_id"], "EST-2")

    def test_listar_estudos_filtra_por_grupo_e_credito(self):
        items = [
            {
                "estudo_id": "EST-1",
                "cliente": {"credito_desejado": 250000},
                "grupo_id": "128",
                "grupo": {"administradora": "Itau", "tipo_bem": "Imovel"},
                "financeiro": {},
            },
            {
                "estudo_id": "EST-2",
                "cliente": {"credito_desejado": 900000},
                "grupo_id": "999",
                "grupo": {"administradora": "CNP", "tipo_bem": "Auto"},
                "financeiro": {},
            },
        ]

        with patch("backend.main.list_estudos", return_value=items):
            result = estudos_listar(administradora="itau", tipo_bem="imovel", credito_minimo=200000, credito_maximo=300000)

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["estudo_id"], "EST-1")

    def test_export_estudo_pdf_gera_arquivo(self):
        payload = EstudoRequest(
            cliente=EstudoCliente(nome="Cliente PDF", credito_desejado=250000, lance_proprio=50000),
            grupo_id="128",
        )

        with patch("backend.main.get_grupo", return_value={"grupo_id": "128", "grupo": "128", "administradora": "Itau"}):
            created = estudos_criar(payload)

        with tempfile.TemporaryDirectory() as temp_dir:
            filename = export_estudo_pdf(created["estudo_id"], Path(temp_dir))
            content = (Path(temp_dir) / filename).read_bytes()

        self.assertEqual(filename, f"{created['estudo_id']}.pdf")
        self.assertTrue(content.startswith(b"%PDF"))

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
