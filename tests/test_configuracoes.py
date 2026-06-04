import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend import configuracoes as configuracoes_module
from backend.main import configuracoes_obter, configuracoes_salvar


class ConfiguracoesTest(unittest.TestCase):
    def setUp(self):
        self.original_config = configuracoes_module.get_configuracoes()
        configuracoes_module._settings.clear()
        configuracoes_module._settings.update(configuracoes_module.DEFAULT_CONFIG)

    def tearDown(self):
        configuracoes_module._settings.clear()
        configuracoes_module._settings.update(self.original_config)

    def test_obter_configuracoes_retorna_empresa_integracoes_e_usuarios(self):
        result = configuracoes_obter()

        self.assertEqual(result["empresa"]["nome"], "Crediclass")
        self.assertIn("google_sheets", result["integracoes"])
        self.assertEqual(len(result["usuarios"]), 2)
        self.assertTrue(result["acesso"]["paineis_liberados"])

    def test_salvar_configuracoes_atualiza_empresa(self):
        result = configuracoes_salvar({"empresa": {"nome": "Crediclass Teste"}})
        config = configuracoes_obter()

        self.assertTrue(result["success"])
        self.assertEqual(config["empresa"]["nome"], "Crediclass Teste")

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
