import unittest

from backend.main import configuracoes_obter, configuracoes_salvar


class ConfiguracoesTest(unittest.TestCase):
    def test_obter_configuracoes_retorna_empresa_integracoes_e_usuarios(self):
        result = configuracoes_obter()

        self.assertEqual(result["empresa"]["nome"], "Crediclass")
        self.assertIn("google_sheets", result["integracoes"])
        self.assertEqual(len(result["usuarios"]), 2)
        self.assertIn("Operadora", result["permissoes"])

    def test_salvar_configuracoes_atualiza_empresa(self):
        result = configuracoes_salvar({"empresa": {"nome": "Crediclass Teste"}})
        config = configuracoes_obter()

        self.assertTrue(result["success"])
        self.assertEqual(config["empresa"]["nome"], "Crediclass Teste")


if __name__ == "__main__":
    unittest.main()
