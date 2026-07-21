import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import app


class ContemplarApiTest(unittest.TestCase):
    def test_returns_only_groups_with_credit_maximum_above_required_credit(self):
        groups = [
            {"grupo_id": "1", "grupo": "1", "administradora": "ITAU", "credito_minimo": 100000, "credito_maximo": 1000000},
            {"grupo_id": "2", "grupo": "2", "administradora": "ITAU", "credito_minimo": 100000, "credito_maximo": 1100000},
            {"grupo_id": "3", "grupo": "3", "administradora": "ITAU", "credito_minimo": 100000, "credito_maximo": 1200000},
        ]
        client = TestClient(app)
        login = client.post("/api/auth/login", json={"usuario": "adm", "senha": "cristiano"})
        self.assertEqual(login.status_code, 200)

        with patch("backend.main.list_grupos", return_value=groups):
            response = client.post("/api/contemplar/analisar", json={
                "objetivo": "Contemplar - urgente - 3 meses",
                "credito_desejado": 950000,
                "lance_proprio": 100000,
                "fgts": 50000,
                "renda_total": 10000,
                "parcela_desejada": 3000,
                "prazo_desejado": 3,
            })

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["cliente"]["credito_bruto_necessario"], 1100000)
        self.assertEqual(result["total_grupos_compativeis"], 2)
        self.assertEqual([item["grupo"] for item in result["items"]], ["2", "3"])


if __name__ == "__main__":
    unittest.main()
