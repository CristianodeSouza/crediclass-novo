import unittest

from fastapi.testclient import TestClient

from backend.main import AUTH_COOKIE, app


class AuthTest(unittest.TestCase):
    def test_api_grupos_exige_login(self):
        client = TestClient(app)

        response = client.get("/api/grupos")

        self.assertEqual(response.status_code, 401)
        self.assertFalse(response.json()["success"])

    def test_login_valido_cria_sessao(self):
        client = TestClient(app)

        response = client.post("/api/auth/login", json={"usuario": "adm", "senha": "cristiano"})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.assertEqual(response.json()["user"]["usuario"], "adm")
        self.assertIn(AUTH_COOKIE, response.cookies)

        session = client.get("/api/auth/me")
        self.assertEqual(session.status_code, 200)
        self.assertEqual(session.json()["user"]["usuario"], "adm")

    def test_login_invalido_nao_cria_sessao(self):
        client = TestClient(app)

        response = client.post("/api/auth/login", json={"usuario": "adm", "senha": "errada"})

        self.assertEqual(response.status_code, 401)
        self.assertFalse(response.json()["success"])
        self.assertNotIn(AUTH_COOKIE, response.cookies)


if __name__ == "__main__":
    unittest.main()
