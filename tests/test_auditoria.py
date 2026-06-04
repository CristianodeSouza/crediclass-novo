import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend import auditoria as auditoria_module
from backend.main import grupo_atualizar, grupo_criar, grupo_detalhe, grupo_excluir, grupo_historico_atualizar
from backend.models import GrupoCreateRequest, GrupoUpdateRequest, HistoricoUpdateRequest


class AuditoriaTest(unittest.TestCase):
    def test_record_auditoria_persiste_por_grupo(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            audit_file = Path(temp_dir) / "auditoria_grupos.json"
            with patch.object(auditoria_module, "RUNTIME_DIR", Path(temp_dir)), patch.object(auditoria_module, "AUDIT_FILE", audit_file):
                entry = auditoria_module.record_auditoria("128", "Atualizacao", "Grupo atualizado", {"campo": "valor"})
                items = auditoria_module.list_auditoria("128")

        self.assertEqual(entry["acao"], "Atualizacao")
        self.assertEqual(items[0]["detalhe"], "Grupo atualizado")
        self.assertEqual(items[0]["payload"]["campo"], "valor")

    def test_grupo_detalhe_inclui_auditoria_local(self):
        fake_item = {
            "grupo_id": "128",
            "administradora": "Itau",
            "grupo": "128",
            "tipo_bem": "Imovel",
            "credito_minimo": 100000,
            "credito_maximo": 1000000,
            "taxa_adm": 0.2,
            "prazo_total": 222,
            "primeira_assembleia": "2023-03-15",
            "ultima_assembleia": "2041-03-15",
            "status": "Ativo",
            "fundo_reserva": 0.03,
            "prazo_restante": 180,
            "data_termino": "2041-03-15",
            "seguro_garantia": True,
            "meia_parcela": False,
            "lance_embutido": True,
            "fgts": True,
            "categoria": "Premium",
            "percentual_lance_embutido": 0.3,
            "percentual_lance_fixo": 0.25,
            "parcela_reduzida": "30%",
            "indice_correcao": "INCC",
            "vencimento_parcela": "10",
            "vencimento_lance": "8",
            "regras_especiais": "",
            "cadastrado_por": "Larissa",
            "ultima_atualizacao": "2026-06-04",
            "historico": {},
            "auditoria": [],
        }

        with patch("backend.main.get_grupo", return_value=fake_item), patch("backend.main.list_auditoria", return_value=[{"acao": "Criacao"}]):
            result = grupo_detalhe("128")

        self.assertEqual(result["auditoria"][0]["acao"], "Criacao")

    def test_endpoints_registram_auditoria_apos_sucesso(self):
        create_payload = GrupoCreateRequest(administradora="Itau", grupo="128", tipo_bem="Imovel", credito_minimo=100000, credito_maximo=1000000, taxa_adm=0.2, prazo_total=222)
        update_payload = GrupoUpdateRequest(taxa_adm=0.21)
        history_payload = HistoricoUpdateRequest(mes="2026-01", maior_lance=0.72, menor_lance=0.24, qtd_contemplacoes=12)

        with (
            patch("backend.main.create_grupo", return_value={"success": True, "grupo_id": "128"}),
            patch("backend.main.update_grupo", return_value={"success": True}),
            patch("backend.main.delete_grupo", return_value={"success": True, "status": "Excluido"}),
            patch("backend.main.update_historico_mensal", return_value={"success": True}),
            patch("backend.main.record_auditoria") as record,
        ):
            grupo_criar(create_payload)
            grupo_atualizar("128", update_payload)
            grupo_excluir("128")
            grupo_historico_atualizar("128", history_payload)

        self.assertEqual(record.call_count, 4)
        self.assertEqual(record.call_args_list[0].args[1], "Criacao de grupo")
        self.assertEqual(record.call_args_list[3].args[1], "Atualizacao de historico")


if __name__ == "__main__":
    unittest.main()
