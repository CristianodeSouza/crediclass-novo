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
        values = body["values"][0]
        address = range.split("!", 1)[1]
        cell = re.fullmatch(r"([A-Z]+)(\d+)(?::([A-Z]+)(\d+))?", address)
        def apply():
            if cell and int(cell.group(2)) > 1:
                column = self.parent.column_index(cell.group(1))
                row_index = int(cell.group(2)) - 2
                while len(self.parent.rows[row_index]) <= column:
                    self.parent.rows[row_index].append("")
                self.parent.rows[row_index][column] = values[0]
            else:
                columns = re.findall(r"[A-Z]+", address)
                start = self.parent.column_index(columns[0])
                for offset, value in enumerate(values):
                    while len(self.parent.headers) <= start + offset:
                        self.parent.headers.append("")
                    self.parent.headers[start + offset] = value
            return {"updated": True}
        return _FakeRequest(apply)

    def append(self, spreadsheetId, range, valueInputOption, insertDataOption, body):
        return _FakeRequest(lambda: self.parent.rows.append(body["values"][0]) or {"updated": True})

    def batchUpdate(self, spreadsheetId, body):
        def apply():
            import re
            for item in body["data"]:
                address = item["range"].split("!", 1)[1]
                match = re.fullmatch(r"([A-Z]+)(\d+)", address)
                column = self.parent.column_index(match.group(1))
                row_index = int(match.group(2)) - 2
                while len(self.parent.rows[row_index]) <= column:
                    self.parent.rows[row_index].append("")
                self.parent.rows[row_index][column] = item["values"][0][0]
            return {"updated": True}
        return _FakeRequest(apply)

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
        self.headers.extend(f"coluna_legada_{index}" for index in range(13, 26))
        self.rows = []
        self.grid_column_count = 28
        self.grid_expansions = []

    @staticmethod
    def column_index(column):
        index = 0
        for character in column:
            index = index * 26 + ord(character) - 64
        return index - 1

    def spreadsheets(self):
        return self

    def get(self, spreadsheetId, fields):
        return _FakeRequest(lambda: {"sheets": [{"properties": {
            "sheetId": 123,
            "title": financial_studies.SHEET_NAME,
            "gridProperties": {"columnCount": self.grid_column_count},
        }}]})

    def batchUpdate(self, spreadsheetId, body):
        def apply():
            request = body["requests"][0]["updateSheetProperties"]
            self.grid_column_count = request["properties"]["gridProperties"]["columnCount"]
            self.grid_expansions.append(self.grid_column_count)
            return {"replies": [{}]}
        return _FakeRequest(apply)

    def values(self):
        return _FakeSheetValues(self)


class FinancialStudiesHistoryApiTest(unittest.TestCase):
    def test_persistence_targets_the_existing_sheet_tab_title_exactly(self):
        self.assertEqual(financial_studies.SHEET_NAME, "Historico de Estudos")
        self.assertEqual(financial_studies._quoted_sheet(), "'Historico de Estudos'")

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
            self.assertEqual(save.call_args.kwargs["app_version"], "4.0.214")

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

    def test_study_id_uses_sequential_number_and_brazil_month_year(self):
        approval_key = "c5b649db06114abd8be30cb8a9f4c6f0"
        now = financial_studies.datetime(2026, 10, 15, 14, 0, tzinfo=financial_studies.timezone.utc)
        self.assertEqual(financial_studies._next_study_id(now, approval_key, []), "EF-1000102026-C5B649DB06")
        ids = [["EF-20261015-OLDIDENTIFIER"], ["EF-1000102026-C5B649DB06"]]
        self.assertEqual(financial_studies._next_study_id(now, approval_key, ids), "EF-1001102026-C5B649DB06")

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

    def test_public_link_is_hashed_expires_and_replacement_invalidates_previous_token(self):
        fake_service = _FakeSheetService()
        with patch("backend.financial_studies.get_service", return_value=fake_service), patch("backend.financial_studies.get_settings", return_value=type("Settings", (), {"google_sheets_id": "sheet-1"})()):
            study = financial_studies.create_study(
                client_name="Cliente Exemplo", approved_by="Administrador", app_version="4.0.200",
                snapshot={"groups": [{"group": "40086"}]}, document_html="<article>Estudo protegido</article>",
                approval_key="00000000-0000-4000-8000-000000000101",
            )
            first_link = financial_studies.create_public_link(study["id"])
            self.assertEqual(fake_service.grid_column_count, 31)
            self.assertEqual(fake_service.grid_expansions, [31])
            self.assertEqual(first_link["validity_days"], 30)
            self.assertIsNotNone(financial_studies.get_public_study(first_link["token"]))
            self.assertNotIn(first_link["token"], " ".join(str(value) for value in fake_service.rows[0]))
            first_hash = financial_studies.hashlib.sha256(first_link["token"].encode("utf-8")).hexdigest()
            token_hash_column = fake_service.headers.index("financial_study_public_token_sha256")
            stored_token = fake_service.rows[0][token_hash_column]
            self.assertTrue(stored_token.startswith(first_hash + "."))
            self.assertNotIn(first_link["token"], stored_token)
            self.assertNotIn("financial_study_public_token_encrypted", fake_service.headers)
            self.assertEqual(financial_studies._share_state(fake_service.rows[0], {financial_studies.normalize_header(name): index for index, name in enumerate(fake_service.headers)})["token"], first_link["token"])
            fake_service.rows[0][token_hash_column] = first_hash
            self.assertIsNotNone(financial_studies.get_public_study(first_link["token"]))
            fake_service.rows[0][token_hash_column] = stored_token

            expires_column = fake_service.headers.index("financial_study_public_expires_at")
            fake_service.rows[0][expires_column] = "2020-01-01T00:00:00+00:00"
            self.assertIsNone(financial_studies.get_public_study(first_link["token"]))

            second_link = financial_studies.create_public_link(study["id"])
            self.assertIsNone(financial_studies.get_public_study(first_link["token"]))
            self.assertEqual(financial_studies.get_public_study(second_link["token"])["document_html"], "<article>Estudo protegido</article>")
            financial_studies.revoke_public_link(study["id"])
            self.assertIsNone(financial_studies.get_public_study(second_link["token"]))

    def test_public_route_is_anonymous_and_invalid_tokens_are_not_found(self):
        with patch("backend.main.financial_studies.get_public_study", return_value=None):
            response = TestClient(app).get("/estudo-compartilhado/token-inexistente")
        self.assertEqual(response.status_code, 404)
        self.assertIn("noindex", response.headers.get("X-Robots-Tag", ""))

    def test_public_route_renders_archived_study_without_login(self):
        public_study = {"id": "EF-1", "client_name": "Cliente Exemplo", "document_html": '<article class="financial-study-document"><h1>Snapshot aprovado</h1></article>'}
        with patch("backend.main.financial_studies.get_public_study", return_value=public_study) as load:
            response = TestClient(app).get("/estudo-compartilhado/opaque-token")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Snapshot aprovado", response.text)
        self.assertNotIn("<iframe", response.text)
        self.assertIn("sharedStudyNavigation", response.text)
        self.assertNotIn("sharedStudyQuickSummary", response.text)
        self.assertNotIn("Resumo do estudo", response.text)
        self.assertIn("<main class='shared-study-content'>", response.text)
        self.assertIn("/static/js/shared-study.js?v=4.0.214", response.text)
        self.assertIn("Content-Security-Policy", response.headers)
        self.assertIn("noindex, nofollow, noarchive", response.headers["X-Robots-Tag"])
        load.assert_called_once_with("opaque-token")

    def test_share_management_returns_link_only_after_authenticated_operator_action(self):
        link = {"token": "opaque-generated-token", "expires_at": "2026-11-14T12:00:00+00:00", "validity_days": 30}
        with patch("backend.main.financial_studies.create_public_link", return_value=link) as create_link:
            client = TestClient(app)
            client.post("/api/auth/login", json={"usuario": "operador1", "senha": "teste123"})
            response = client.post("/api/financial-studies/EF-1/share", json={})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["url"], "http://testserver/estudo-compartilhado/opaque-generated-token")
        create_link.assert_called_once_with("EF-1")

    def test_study_detail_returns_active_share_url_to_authenticated_operator(self):
        study = {
            "id": "EF-1", "client_name": "Cliente", "approved_at": "2026-10-15T12:00:00+00:00",
            "approved_by": "Administrador", "app_version": "4.0.210", "document_html": "<article></article>",
            "public_link": {"active": True, "expires_at": "2026-11-14T12:00:00+00:00", "revoked": False, "token": "recoverable-token"},
        }
        with patch("backend.main.financial_studies.get_study", return_value=study):
            client = TestClient(app)
            client.post("/api/auth/login", json={"usuario": "operador1", "senha": "teste123"})
            response = client.get("/api/financial-studies/EF-1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["study"]["public_link"]["url"], "http://testserver/estudo-compartilhado/recoverable-token")
        self.assertNotIn("token", response.json()["study"]["public_link"])

    def test_share_management_endpoints_require_login(self):
        client = TestClient(app)
        self.assertEqual(client.post("/api/financial-studies/EF-1/share").status_code, 401)
        self.assertEqual(client.delete("/api/financial-studies/EF-1/share").status_code, 401)


if __name__ == "__main__":
    unittest.main()
