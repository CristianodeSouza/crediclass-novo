import unittest
from unittest.mock import patch

from backend.main import estudos_criar
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


if __name__ == "__main__":
    unittest.main()
