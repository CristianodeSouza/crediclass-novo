import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend import configuracoes as configuracoes_module
from backend.main import configuracoes_obter, configuracoes_salvar


class ConfiguracoesTest(unittest.TestCase):
    def setUp(self):
        self.original_config = configuracoes_module.get_configuracoes()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.runtime_dir_patcher = patch.object(configuracoes_module, "RUNTIME_DIR", Path(self.temp_dir.name))
        self.config_file_patcher = patch.object(configuracoes_module, "CONFIG_FILE", Path(self.temp_dir.name) / "configuracoes.json")
        self.runtime_dir_patcher.start()
        self.config_file_patcher.start()
        configuracoes_module._settings.clear()
        configuracoes_module._settings.update(configuracoes_module.DEFAULT_CONFIG)

    def tearDown(self):
        configuracoes_module._settings.clear()
        configuracoes_module._settings.update(self.original_config)
        self.config_file_patcher.stop()
        self.runtime_dir_patcher.stop()
        self.temp_dir.cleanup()

    def test_obter_configuracoes_retorna_empresa_integracoes_e_usuarios(self):
        result = configuracoes_obter()

        self.assertEqual(result["empresa"]["nome"], "Crediclass")
        self.assertIn("google_sheets", result["integracoes"])
        self.assertIn("alertar_sincronizacao", result["notificacoes"])
        self.assertEqual(len(result["usuarios"]), 2)
        self.assertTrue(result["acesso"]["paineis_liberados"])

    def test_salvar_configuracoes_atualiza_empresa(self):
        result = configuracoes_salvar({"empresa": {"nome": "Crediclass Teste"}})
        config = configuracoes_obter()

        self.assertTrue(result["success"])
        self.assertEqual(config["empresa"]["nome"], "Crediclass Teste")

    def test_salvar_configuracoes_atualiza_preferencias(self):
        result = configuracoes_salvar({
            "preferencias": {
                "casas_decimais_valores": 3,
                "casas_decimais_percentuais": 4,
                "ativar_meia_parcela": False,
                "ativar_lance_embutido": False,
                "exibir_historico_36_meses": False,
            }
        })
        config = configuracoes_obter()

        self.assertTrue(result["success"])
        self.assertEqual(config["preferencias"]["casas_decimais_valores"], 3)
        self.assertEqual(config["preferencias"]["casas_decimais_percentuais"], 4)
        self.assertFalse(config["preferencias"]["ativar_meia_parcela"])
        self.assertFalse(config["preferencias"]["ativar_lance_embutido"])
        self.assertFalse(config["preferencias"]["exibir_historico_36_meses"])

    def test_salvar_configuracoes_atualiza_notificacoes(self):
        result = configuracoes_salvar({
            "notificacoes": {
                "alertar_sincronizacao": False,
                "alertar_estudo_salvo": False,
                "alertar_historico_atualizado": False,
                "alertar_falha_integracao": False,
            }
        })
        config = configuracoes_obter()

        self.assertTrue(result["success"])
        self.assertFalse(config["notificacoes"]["alertar_sincronizacao"])
        self.assertFalse(config["notificacoes"]["alertar_estudo_salvo"])
        self.assertFalse(config["notificacoes"]["alertar_historico_atualizado"])
        self.assertFalse(config["notificacoes"]["alertar_falha_integracao"])

    def test_salvar_configuracoes_atualiza_integracoes(self):
        result = configuracoes_salvar({
            "integracoes": {
                "google_sheets": False,
                "piperun_crm": True,
                "email_smtp": True,
                "backup_automatico": True,
            }
        })
        config = configuracoes_obter()

        self.assertTrue(result["success"])
        self.assertFalse(config["integracoes"]["google_sheets"])
        self.assertTrue(config["integracoes"]["piperun_crm"])
        self.assertTrue(config["integracoes"]["email_smtp"])
        self.assertTrue(config["integracoes"]["backup_automatico"])

    def test_salvar_configuracoes_atualiza_usuarios(self):
        usuarios = [{
            "nome": "Ana",
            "email": "ana@crediclass.local",
            "perfil": "Referencia Operacional",
            "status": "Inativo",
            "ultimo_acesso": "",
        }]

        result = configuracoes_salvar({"usuarios": usuarios})
        config = configuracoes_obter()

        self.assertTrue(result["success"])
        self.assertEqual(config["usuarios"], usuarios)

    def test_salvar_configuracoes_atualiza_feedbacks_regras_negocio(self):
        feedbacks = {
            "perfil-cliente": {
                "observacao": "Validar se parcela limite deve ser usada nesta etapa.",
                "status": "Em revisao",
            }
        }

        result = configuracoes_salvar({"regras_negocio_feedbacks": feedbacks})
        config = configuracoes_obter()

        self.assertTrue(result["success"])
        self.assertEqual(config["regras_negocio_feedbacks"], feedbacks)

    def test_salvar_configuracoes_persiste_json(self):
        original = configuracoes_module.get_configuracoes()
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                runtime_dir = Path(temp_dir)
                with patch.object(configuracoes_module, "RUNTIME_DIR", runtime_dir), patch.object(configuracoes_module, "CONFIG_FILE", runtime_dir / "configuracoes.json"):
                    configuracoes_module.update_configuracoes({"empresa": {"nome": "Persistida"}})
                    loaded = configuracoes_module.load_config()
        finally:
            configuracoes_module._settings.clear()
            configuracoes_module._settings.update(original)

        self.assertEqual(loaded["empresa"]["nome"], "Persistida")

    def test_carregar_configuracoes_ignora_permissoes_antigas(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir)
            config_file = runtime_dir / "configuracoes.json"
            runtime_dir.mkdir(parents=True, exist_ok=True)
            config_file.write_text('{"permissoes": {"Operadora": {"visualizar_grupos": true}}}', encoding="utf-8")
            with patch.object(configuracoes_module, "RUNTIME_DIR", runtime_dir), patch.object(configuracoes_module, "CONFIG_FILE", config_file):
                loaded = configuracoes_module.load_config()

        self.assertNotIn("permissoes", loaded)
        self.assertTrue(loaded["acesso"]["paineis_liberados"])


if __name__ == "__main__":
    unittest.main()
