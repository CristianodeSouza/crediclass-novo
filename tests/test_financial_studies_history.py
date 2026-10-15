import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import AUTH_COOKIE, app
from backend import financial_studies
from backend.financial_studies import _compress_archive, _decompress_archive


class _FakeRequest:
    def __init__(self, action):
        self.action = action

    def execute(self):
        return self.action()


class _FakeSheetValues:
    def __init__(self, parent):
        self.parent = parent

    def get(self, spreadsheetId, range):
        tab_range = range.split("!", 1)[1]
        if tab_range == "A1:ZZ1":
            return _FakeRequest(lambda: {"values": [self.parent.headers]})
        import re
        column = re.match(r"([A-Z]+)(\d*)", tab_range).group(1)
        index = self.parent.column_index(column)
        row_match = re.search(r"!(?:[A-Z]+)(\d+):[A-Z]+(\d+)$", range)
        if row_match:
            row_number = int(row_match.group(1))
            return _FakeRequest(lambda: {"values": [self.parent.rows[row_number - 2]] if row_number - 2 < len(self.parent.rows) else []})
        if re.fullmatch(r"[A-Z]+2:[A-Z]+", tab_range):
            return _FakeRequest(lambda: {"values": [[row[index]] if index < len(row) else [] for row in self.parent.rows]})
        return _FakeRequest(lambda: {"values": []})

    def update(self, spreadsheetId, range, valueInputOption, body):
        import re
        columns = re.findall(r"[A-Z]+", range.split("!", 1)[1])
        start = self.parent.column_index(columns[0])
        values = body["values"][0]
        def apply():
            for offset, value in enumerate(values):
                while len(self.parent.headers) <= start + offset:
                    self.parent.headers.append("")
                self.parent.headers[start + offset] = value
            return {"updated": True}
        return _FakeRequest(apply)

    def append(self, spreadsheetId, range, valueInputOption, insertDataOption, body):
        return _FakeRequest(lambda: self.parent.rows.append(body["values"][0]) or {"updated": True})

    def batchGet(self, spreadsheetId, ranges):
        values = []
        for range in ranges:
            import re
            column = re.search(r"!([A-Z]+)2:", range).group(1)
            index = self.parent.column_index(column)
            values.append({"values": [[row[index]] if index < len(row) and row[index] != "" else [] for row in self.parent.rows]})
        return _FakeRequest(lambda: {"valueRanges": values})


class _FakeSheetService:
    def __init__(self):
        self.headers = ["estudo_id", "proposta_id", "criado_em", "status", "operador", "grupo_id", "cliente_nome", "administradora", "tipo_bem", "estrategia", "cliente_json", "grupo_json"]
        self.rows = []

    @staticmethod
    def column_index(column):
        index = 0
        for character in column:
            index = index * 26 + ord(character) - 64
        return index - 1

    def spreadsheets(self):
        return self

    def values(self):
        return _FakeSheetValues(self)


class FinancialStudiesHistoryApiTest(unittest.TestCase):
    def test_api_requires_authenticated_session(self):
        client = TestClient(app)
        self.assertEqual(client.get("/api/financial-studies").status_code, 401)
        self.assertEqual(client.post("/api/financial-studies", json={}).status_code, 401)

    def test_approval_is_saved_and_returns_sheet_record_identity(self):
        created = {"id": "EF-20261015-ABC123", "client_name": "Cliente Exemplo", "approved_at": "2026-10-15T12:00:00+00:00", "approved_by": "Administrador", "app_version": "4.0.200"}
        with patch("backend.main.financial_studies.create_study", return_value=created) as save:
            client = TestClient(app)
            client.post("/api/auth/login", json={"usuario": "adm", "senha": "cristiano"})
            self.assertIn(AUTH_COOKIE, client.cookies)
            response = client.post("/api/financial-studies", json={
                "client_name": "Cliente Exemplo",
                "approval_key": "00000000-0000-4000-8000-000000000001",
                "snapshot": {"groups": [{"group": "40086"}]},
                "document_html": '<article class="financial-study-document">Snapshot</article>',
            })
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()["study"]["id"], created["id"])
            self.assertEqual(save.call_args.kwargs["approved_by"], "Administrador")
            self.assertEqual(save.call_args.kwargs["app_version"], "4.0.200")

    def test_history_can_search_and_open_archived_record(self):
        item = {"id": "EF-1", "client_name": "Cliente", "approved_at": "2026-10-15T12:00:00+00:00", "approved_by": "Operador 1", "group_count": 2, "has_snapshot": True}
        study = {**item, "snapshot": {"groups": [{"group": "A"}, {"group": "B"}]}, "document_html": "<article>Snapshot</article>", "app_version": "4.0.200"}
        with patch("backend.main.financial_studies.list_studies", return_value=[item]), patch("backend.main.financial_studies.get_study", return_value=study):
            client = TestClient(app)
            client.post("/api/auth/login", json={"usuario": "operador1", "senha": "teste123"})
            self.assertEqual(client.get("/api/financial-studies", params={"query": "Cliente"}).json()["items"], [item])
            self.assertEqual(client.get("/api/financial-studies/EF-1").json()["study"], study)

    def test_archive_compression_round_trips_exact_snapshot_and_document(self):
        snapshot = {"groups": [{"group": "40086", "quota": 2}], "client": {"name": "Cliente á"}}
        document = '<article><p>Conteúdo imutável — R$ 600.000,00</p></article>'
        stored = _compress_archive(snapshot, document, "4.0.200")
        decoded = _decompress_archive(stored)
        self.assertEqual(decoded["snapshot"], snapshot)
        self.assertEqual(decoded["document_html"], document)
        self.assertEqual(decoded["app_version"], "4.0.200")

    def test_sheet_persistence_appends_without_overwriting_legacy_columns_and_is_idempotent(self):
        fake_service = _FakeSheetService()
        approval_key = "00000000-0000-4000-8000-000000000002"
        with patch("backend.financial_studies.get_service", return_value=fake_service), patch("backend.financial_studies.get_settings", return_value=type("Settings", (), {"google_sheets_id": "sheet-1"})()):
            study = financial_studies.create_study(
                client_name="Cliente Exemplo", approved_by="Administrador", app_version="4.0.200",
                snapshot={"groups": [{"group": "40086", "administrator": "ITAÚ", "selected_scenarios": [{"id": "without_embedded"}]}]},
                document_html="<article>Estudo</article>", approval_key=approval_key,
            )
            self.assertEqual(fake_service.headers[:12], ["estudo_id", "proposta_id", "criado_em", "status", "operador", "grupo_id", "cliente_nome", "administradora", "tipo_bem", "estrategia", "cliente_json", "grupo_json"])
            self.assertEqual(len(fake_service.rows), 1)
            self.assertEqual(fake_service.rows[0][0], study["id"])
            self.assertEqual(fake_service.rows[0][3], "Aprovado")
            self.assertEqual(fake_service.rows[0][5], "40086")
            self.assertEqual(fake_service.rows[0][6], "Cliente Exemplo")
            self.assertEqual(financial_studies.create_study(
                client_name="Cliente Exemplo", approved_by="Administrador", app_version="4.0.200",
                snapshot={"groups": [{"group": "40086"}]}, document_html="Outro", approval_key=approval_key,
            )["id"], study["id"])
            self.assertEqual(len(fake_service.rows), 1)
            self.assertEqual(financial_studies.list_studies(query="Exemplo")[0]["id"], study["id"])
            loaded = financial_studies.get_study(study["id"])
            self.assertEqual(loaded["document_html"], "<article>Estudo</article>")
            self.assertEqual(loaded["snapshot"]["groups"][0]["group"], "40086")

    def test_empty_history_read_does_not_mutate_sheet_headers(self):
        fake_service = _FakeSheetService()
        original_headers = list(fake_service.headers)
        with patch("backend.financial_studies.get_service", return_value=fake_service), patch("backend.financial_studies.get_settings", return_value=type("Settings", (), {"google_sheets_id": "sheet-1"})()):
            self.assertEqual(financial_studies.list_studies(), [])
        self.assertEqual(fake_service.headers, original_headers)

    def test_invalid_approval_payload_is_rejected(self):
        client = TestClient(app)
        client.post("/api/auth/login", json={"usuario": "adm", "senha": "cristiano"})
        response = client.post("/api/financial-studies", json={"client_name": "Cliente", "approval_key": "bad", "snapshot": {"groups": []}, "document_html": "<article></article>"})
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
