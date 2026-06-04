import unittest
from unittest.mock import patch

from backend.main import estudos_criar, estudos_excluir, estudos_listar, estudos_obter
from backend.models import EstudoCliente, EstudoRequest


class EstudosTest(unittest.TestCase):
    def test_criar_estudo_valida_grupo_e_retorna_id(self):
        payload = EstudoRequest(
            cliente=EstudoCliente(nome="Cliente Teste", credito_desejado=500000),
            grupo_id="ITAU-128-IMOVEL",
        )

        with patch("backend.main.get_grupo", return_value={"grupo_id": "ITAU-128-IMOVEL"}):
            result = estudos_criar(payload)

        self.assertTrue(result["success"])
        self.assertTrue(result["estudo_id"].startswith("EST-"))

    def test_listar_obter_e_excluir_estudo(self):
        payload = EstudoRequest(
            cliente=EstudoCliente(nome="Cliente Historico", credito_desejado=300000),
            grupo_id="CNP-017-IMOVEL",
        )

        with patch("backend.main.get_grupo", return_value={"grupo_id": "CNP-017-IMOVEL", "grupo": "017"}):
            created = estudos_criar(payload)

        listed = estudos_listar(cliente="Historico")
        self.assertGreaterEqual(listed["total"], 1)

        detail = estudos_obter(created["estudo_id"])
        self.assertEqual(detail["cliente"]["nome"], "Cliente Historico")

        deleted = estudos_excluir(created["estudo_id"])
        self.assertTrue(deleted["success"])


if __name__ == "__main__":
    unittest.main()
