"""E2E smoke of the real app shell against a deterministic local API fixture."""

from __future__ import annotations

import json
import html
import re
import os
import copy
import shutil
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from tests.test_motor360_browser import _chrome_binary


ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "backend" / "static"
FIXTURE_PATH = ROOT / "tests" / "fixtures" / "motor360_api_fixture.json"


class Motor360ApplicationBrowserTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.chrome = _chrome_binary()
        if not cls.chrome:
            if os.environ.get("REQUIRE_MOTOR360_BROWSER") == "1":
                raise RuntimeError("Chromium/Chrome is required for the Motor 360 application E2E test")
            raise unittest.SkipTest("Chromium/Chrome not installed")
        cls.fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    def setUp(self):
        self.analysis_calls = 0
        self.composition_candidate_e2e = False
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass

            def _json(self, payload, status=200, headers=None):
                raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(raw)))
                for key, value in (headers or {}).items():
                    self.send_header(key, value)
                self.end_headers()
                self.wfile.write(raw)

            def do_GET(self):
                path = urlsplit(self.path).path
                if path == "/":
                    html = (STATIC / "index.html").read_text(encoding="utf-8")
                    e2e_script = (
                        outer._composition_candidate_automation_script()
                        if getattr(outer, "composition_candidate_e2e", False)
                        else outer._automation_script()
                    )
                    html = html.replace("</body>", f"{e2e_script}</body>")
                    raw = html.encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(raw)))
                    self.end_headers()
                    self.wfile.write(raw)
                    return
                if path == "/api/auth/me":
                    self._json({"user": {"usuario": "e2e-fixture", "nome": "Motor 360 E2E", "perfil": "teste"}})
                    return
                if path == "/api/health":
                    self._json({"status": "ok", "version": "e2e-fixture", "environment": "test"})
                    return
                if path == "/api/grupos":
                    self._json({"items": [], "total": 0, "total_administradoras": 0, "administradoras": [], "tipos_bem": []})
                    return
                if path.startswith("/static/"):
                    file_path = (STATIC / path.removeprefix("/static/")).resolve()
                    if not file_path.is_relative_to(STATIC.resolve()) or not file_path.is_file():
                        self.send_error(404)
                        return
                    content_type = "text/javascript" if file_path.suffix == ".js" else "text/css" if file_path.suffix == ".css" else "application/octet-stream"
                    body = file_path.read_bytes()
                    self.send_response(200)
                    self.send_header("Content-Type", content_type)
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return
                self._json({"success": True, "items": []})

            def do_POST(self):
                path = urlsplit(self.path).path
                length = int(self.headers.get("Content-Length", "0"))
                if length:
                    self.rfile.read(length)
                if path == "/api/viabilidade-360/analisar":
                    outer.analysis_calls += 1
                    self._json(outer.fixture["payload"], headers={"Server-Timing": "sheet_load;dur=1.25, engine;dur=4.5, audit_save;dur=0.2, total;dur=6.0"})
                    return
                self._json({"success": True})

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    @staticmethod
    def _automation_script() -> str:
        return r'''<script>
window.__motor360E2E = { errors: [], analysisCalls: 0, outcome: null };
window.addEventListener("error", event => window.__motor360E2E.errors.push(event.message));
window.addEventListener("unhandledrejection", event => window.__motor360E2E.errors.push(String(event.reason)));
const originalFetch = window.fetch.bind(window);
window.fetch = (input, init) => {
  if (String(input).includes("/api/viabilidade-360/analisar")) window.__motor360E2E.analysisCalls++;
  return originalFetch(input, init).then(response => {
    if (!response.ok) window.__motor360E2E.errors.push(`HTTP ${response.status} ${input}`);
    return response;
  });
};
const sleep = milliseconds => new Promise(resolve => setTimeout(resolve, milliseconds));
const until = async (predicate, timeout = 15000) => {
  const start = Date.now();
  while (!predicate()) {
    if (Date.now() - start > timeout) throw new Error("Timeout aguardando estado da interface");
    await sleep(50);
  }
};
(async () => {
  await until(() => document.body.classList.contains("authenticated"));
  document.getElementById("clientProfileCredito").value = "600000";
  document.getElementById("clientProfileParcelaIdeal").value = "12000";
  document.getElementById("clientProfileParcelaLimite").value = "12000";
  updateClientProfileTotals();
  document.querySelector('[data-screen="motor360"]').click();
  await until(() => document.querySelectorAll("#investorAnalysisResults .motor360-group-card").length === 4);
  const initialGroups = [...document.querySelectorAll(".motor360-group-card h3")].map(node => node.textContent.trim());

  const sort = document.querySelector('[data-motor360-filter="sort"]');
  sort.value = "bid";
  sort.dispatchEvent(new Event("change", { bubbles: true }));
  await until(() => document.querySelectorAll(".motor360-bid-sort-value").length === 4, 5000);
  await sleep(800);
  const sortedCards = [...document.querySelectorAll(".motor360-group-card")].map(card => ({
    group: card.querySelector("h3").textContent.trim(),
    label: card.querySelector(".motor360-bid-sort-value")?.textContent.trim() || "",
  }));

  const withScenario = document.getElementById("investorFilterWithEmbedded");
  const withoutScenario = document.getElementById("investorFilterWithoutEmbedded");
  withScenario.checked = true;
  withScenario.dispatchEvent(new Event("change", { bubbles: true }));
  const withCount = document.querySelectorAll(".motor360-group-card").length;
  withoutScenario.checked = true;
  withoutScenario.dispatchEvent(new Event("change", { bubbles: true }));
  const bothCount = document.querySelectorAll(".motor360-group-card").length;
  withScenario.checked = false;
  withScenario.dispatchEvent(new Event("change", { bubbles: true }));
  const withoutCount = document.querySelectorAll(".motor360-group-card").length;

  const term = document.querySelector('[data-motor360-advanced="maxTerm"]');
  term.value = "100";
  term.dispatchEvent(new Event("input", { bubbles: true }));
  await sleep(900);
  const termFilteredGroups = [...document.querySelectorAll(".motor360-group-card h3")].map(node => node.textContent.trim());
  document.querySelector("[data-motor360-clear-filters]").click();
  await sleep(900);
  const cleared = term.value === "" && document.querySelectorAll(".motor360-group-card").length === 4;

  const layout = { viewport: innerWidth, document: document.documentElement.scrollWidth, results: document.getElementById("investorAnalysisResults").scrollWidth };
  window.__motor360E2E.outcome = {
    initialGroups, sortedCards, withCount, bothCount, withoutCount, termFilteredGroups, cleared,
    analysisCalls: window.__motor360E2E.analysisCalls, errors: window.__motor360E2E.errors, layout,
  };
  document.getElementById("motor360-e2e-result").textContent = JSON.stringify(window.__motor360E2E.outcome);
})().catch(error => {
  window.__motor360E2E.errors.push(error.stack || String(error));
  document.getElementById("motor360-e2e-result").textContent = JSON.stringify({ errors: window.__motor360E2E.errors });
});
</script><pre id="motor360-e2e-result">pending</pre>'''

    @staticmethod
    def _composition_candidate_automation_script() -> str:
        return r'''<script>
window.__motor360E2E = { errors: [], analysisCalls: 0, outcome: null };
window.addEventListener("error", event => window.__motor360E2E.errors.push(event.message));
window.addEventListener("unhandledrejection", event => window.__motor360E2E.errors.push(String(event.reason)));
const originalFetch = window.fetch.bind(window);
window.fetch = (input, init) => {
  if (String(input).includes("/api/viabilidade-360/analisar")) window.__motor360E2E.analysisCalls++;
  return originalFetch(input, init).then(response => {
    if (!response.ok) window.__motor360E2E.errors.push(`HTTP ${response.status} ${input}`);
    return response;
  });
};
const sleep = milliseconds => new Promise(resolve => setTimeout(resolve, milliseconds));
const until = async (predicate, timeout = 15000) => {
  const start = Date.now();
  while (!predicate()) {
    if (Date.now() - start > timeout) throw new Error("Timeout aguardando lista do Motor 360");
    await sleep(50);
  }
};
(async () => {
  await until(() => document.body.classList.contains("authenticated"));
  document.getElementById("clientProfileCredito").value = "600000";
  document.getElementById("clientProfileParcelaIdeal").value = "12000";
  document.getElementById("clientProfileParcelaLimite").value = "12000";
  updateClientProfileTotals();
  document.querySelector('[data-screen="motor360"]').click();
  await until(() => document.querySelector("#investorAnalysisResults .motor360-group-list"));
  await sleep(250);
  const result = investorState.result;
  const apiItems = result.final_items || result.items || [];
  const cards = [...document.querySelectorAll("#investorAnalysisResults .motor360-group-card")];
  const compositionCard = cards.find(card => card.querySelector("h3")?.textContent.includes("1045"));
  window.__motor360E2E.outcome = {
    apiCount: apiItems.length,
    renderedCount: cards.length,
    renderedGroups: cards.map(card => card.querySelector("h3")?.textContent.trim()),
    compositionCandidateVisible: Boolean(compositionCard),
    compositionStatus: compositionCard?.querySelector(".motor360-group-status")?.textContent.trim() || "",
    displayedStatus: document.getElementById("investorAnalysisStatus")?.textContent.trim() || "",
    summaryDisplayedCount: [...document.querySelectorAll(".smart-engine-summary-item")]
      .find(node => node.querySelector("span")?.textContent.includes("Grupos exibidos nesta administradora"))
      ?.querySelector("strong")?.textContent.trim() || "",
    analysisCalls: window.__motor360E2E.analysisCalls,
    errors: window.__motor360E2E.errors,
  };
  document.getElementById("motor360-e2e-result").textContent = JSON.stringify(window.__motor360E2E.outcome);
})().catch(error => {
  window.__motor360E2E.errors.push(error.stack || String(error));
  document.getElementById("motor360-e2e-result").textContent = JSON.stringify({ errors: window.__motor360E2E.errors });
});
</script><pre id="motor360-e2e-result">pending</pre>'''

    def test_real_application_flow_with_mocked_api(self):
        expected = self.fixture["fixture_metadata"]
        with tempfile.TemporaryDirectory(prefix="motor360-app-e2e-") as directory:
            profile = Path(directory) / "chrome-profile"
            completed = subprocess.run(
                [self.chrome, "--headless=new", "--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage",
                 "--window-size=390,844", "--virtual-time-budget=8000", f"--user-data-dir={profile}",
                 "--dump-dom", f"http://127.0.0.1:{self.server.server_port}/"],
                capture_output=True, text=True, timeout=45, check=True,
                encoding="utf-8", errors="replace",
            )
        marker = '<pre id="motor360-e2e-result">'
        self.assertIn(marker, completed.stdout, completed.stderr[-2000:])
        serialized = completed.stdout.split(marker, 1)[1].split("</pre>", 1)[0]
        outcome = json.loads(serialized)
        self.assertFalse(outcome.get("errors"), outcome.get("errors"))
        self.assertEqual(outcome["initialGroups"], [f"Grupo {group}" for group in expected["expected_visible_groups_per_scenario"]["per_group"]])
        self.assertEqual([row["group"].removeprefix("Grupo ") for row in outcome["sortedCards"]], expected["expected_bid_order"])
        parsed_bids = []
        for row in outcome["sortedCards"][:3]:
            amount_text = html.unescape(row["label"].split("R$", 1)[1]).replace("\xa0", " ").strip()
            amount_match = re.search(r"-?[\d.,]+", amount_text)
            self.assertIsNotNone(amount_match, f"rótulo sem valor monetário: {row['label']!r}")
            normalized = amount_match.group(0)
            if "," in normalized:
                normalized = normalized.replace(".", "").replace(",", ".")
            parsed_bids.append(round(float(normalized)))
        self.assertEqual(parsed_bids, expected["expected_numeric_bid_order"])
        self.assertIn("referência calculável", outcome["sortedCards"][-1]["label"].lower())
        self.assertEqual(outcome["withCount"], 2)
        self.assertEqual(outcome["bothCount"], 4)
        self.assertEqual(outcome["withoutCount"], 4)
        self.assertEqual(outcome["termFilteredGroups"], ["Grupo 20399", "Grupo 1011", "Grupo NO-BID"])
        self.assertTrue(outcome["cleared"])
        self.assertEqual(outcome["analysisCalls"], 1, "filtros/ordenação locais não podem repetir o POST de análise")
        self.assertLessEqual(outcome["layout"]["results"], outcome["layout"]["viewport"] + 2)

    def test_profile_filter_keeps_composition_candidates_and_matches_payload_count(self):
        self.composition_candidate_e2e = True
        self.fixture = copy.deepcopy(type(self).fixture)
        payload = self.fixture["payload"]
        payload["perfil_contemplacao"] = "moderate"
        existing_items = payload["items"]
        for item in existing_items:
            for scenario in item.get("cenarios", []):
                for profile in scenario.get("perfis_contemplacao", []):
                    if profile.get("id") == "moderate":
                        profile["atinge_perfil"] = True
        candidate = copy.deepcopy(next(item for item in existing_items if item["grupo"] == "I227"))
        candidate.update({
            "grupo": "1045",
            "administradora": "CNP",
            "matrix_approved": False,
            "result": "composition",
            "composition_candidate": True,
            "requires_composition": True,
            "selection_stage": "composition",
        })
        payload["items"] = [*existing_items, candidate]
        payload["final_items"] = payload["items"]
        payload["matrix_items"] = existing_items
        payload["total_grupos_preselecionados"] = len(payload["final_items"])
        payload["total_grupos_viaveis"] = len(payload["final_items"])
        payload["total_grupos_composicao"] = 2

        with tempfile.TemporaryDirectory(prefix="motor360-composition-e2e-") as directory:
            profile = Path(directory) / "chrome-profile"
            completed = subprocess.run(
                [self.chrome, "--headless=new", "--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage",
                 "--window-size=390,844", "--virtual-time-budget=8000", f"--user-data-dir={profile}",
                 "--dump-dom", f"http://127.0.0.1:{self.server.server_port}/"],
                capture_output=True, text=True, timeout=45, check=True,
                encoding="utf-8", errors="replace",
            )
        marker = '<pre id="motor360-e2e-result">'
        self.assertIn(marker, completed.stdout, completed.stderr[-2000:])
        outcome = json.loads(completed.stdout.split(marker, 1)[1].split("</pre>", 1)[0])
        self.assertFalse(outcome.get("errors"), outcome.get("errors"))
        self.assertEqual(outcome["apiCount"], 5)
        self.assertEqual(outcome["renderedCount"], outcome["apiCount"], outcome["renderedGroups"])
        self.assertTrue(outcome["compositionCandidateVisible"], outcome["renderedGroups"])
        self.assertIn("Possível em composição", outcome["compositionStatus"])
        self.assertIn("5 grupos disponíveis exibidos", outcome["displayedStatus"])
        self.assertEqual(outcome["summaryDisplayedCount"], "5")
        self.assertEqual(outcome["analysisCalls"], 1)


if __name__ == "__main__":
    unittest.main()
