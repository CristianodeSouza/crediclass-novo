"""Browser-level regression checks for the real Motor 360 card and sort code.

These tests execute the production JavaScript functions inside Chromium and
assert on parsed DOM, not on source substrings or a fake DOM implementation.
The application data is a deterministic fixture; no production API is called.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[1]
APP_JS = ROOT / "backend" / "static" / "js" / "app.js"


def _chrome_binary() -> str | None:
    candidates = [
        shutil.which("chrome"),
        shutil.which("google-chrome"),
        shutil.which("chromium"),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        "/usr/bin/google-chrome",
        "/usr/bin/chromium",
    ]
    return next((path for path in candidates if path and Path(path).is_file()), None)


def _between(source: str, start: str, end: str) -> str:
    try:
        return start + source.split(start, 1)[1].split(end, 1)[0]
    except IndexError as exc:
        raise AssertionError(f"Production function boundary not found: {start}") from exc


class Motor360BrowserTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.chrome = _chrome_binary()
        if not cls.chrome:
            if os.environ.get("REQUIRE_MOTOR360_BROWSER") == "1":
                raise RuntimeError("Chromium/Chrome is required for the Motor 360 browser suite")
            raise unittest.SkipTest("Chromium/Chrome not installed; browser suite is required in CI")
        source = APP_JS.read_text(encoding="utf-8")
        cls.production_functions = "\n".join((
            _between(source, "function formatMotor360Reason", "function formatMotor360Duration"),
            _between(source, "function motor360CompositionIdealBid", "function motor360ScenarioIdsForSort"),
            _between(source, "function motor360ScenarioIdsForSort", "function motor360BidSortValue"),
            _between(source, "function motor360BidSortValue", "function motor360BidSortDescription"),
            _between(source, "function motor360BidSortLabel", "function sortMotor360ItemsByBid"),
            _between(source, "function sortMotor360ItemsByBid", "function selectedGroupAnalytics"),
            _between(source, "function renderMotor360GroupCardUncached", "function renderMotor360GroupCard"),
            _between(source, "function renderMotor360GroupCard(item)", "function selectedMotor360Items"),
        ))

    def _run_browser(self, actions: str, extra_functions: str = "") -> dict:
        fixture = r'''<!doctype html><meta charset="utf-8"><main id="cards"></main><pre id="result">pending</pre>
<script>window.addEventListener("error", event => { document.querySelector("#result").textContent = "ERROR: " + event.message; });</script>
<script>
const investorState = {
  selectedGroupIds: new Set(), selectedGroupScenario: "per_group", selectedGroupSort: "original",
  selectedGroupProfile: "all", quotaCounts: new Map(), selectedGroupData: new Map(),
  result: { cliente: { credito_liquido_desejado: 600000 } },
};
const motor360GroupCardCache = new Map();
const groupScenarios = new Map();
const motor360GroupKey = item => String(item.grupo || item.grupo_id);
const motor360GroupAnchorId = id => `motor360-group-${id}`;
const selectedScenarioIdsForGroup = id => groupScenarios.get(id) || new Set();
const selectedMotor360Items = () => [];
const selectedCompositionScenarioMetrics = () => null;
const minimumQuotasFor = (item, id) => item.minQuotas?.[id] ?? 1;
const quotaCountFor = item => item.quotas || 1;
const motor360ClientProfile = () => ({ credito_liquido_desejado: 600000 });
const motor360ClientProfileId = () => "moderate";
const motor360FocusedProfileId = () => "moderate";
const allocationProfileId = () => "moderate";
const motor360QuotaCapacity = () => null;
const profileMeetsBid = () => true;
const allocatedClientBidFor = (item, scenario, profileId) => Number(scenario.perfis_contemplacao?.find(p => p.id === profileId)?.lance_ideal ?? 0);
const formatGroupDueDate = value => value || "Não informado";
const formatMoney = value => value == null || !Number.isFinite(Number(value)) ? "-" : `R$ ${Number(value).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const formatPercent = value => `${(Number(value || 0) * 100).toLocaleString("pt-BR", { maximumFractionDigits: 3 })}%`;
const escapeHtml = value => String(value ?? "").replace(/[&<>"']/g, c => ({ "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;" }[c]));
const motor360HistoricalAverages = () => "";
const motor360HistoryTrigger = () => "";
'''+ self.production_functions + "\n" + extra_functions + r'''
const scenario = (id, ideal, compatible = true) => ({
  id, eligible: compatible, credit_compatible: compatible, term_compatible: compatible,
  income_compatible: true, credito_contratado: 600000, parcela_inicial: 4500,
  parcela_pos_contemplacao: 4200, lance_cliente_total: 460000, lance_embutido: 0,
  lance_total_cenario: 460000, saldo_devedor: 500000, percentual_lance_cliente: .76667,
  percentual_lance_efetivo: .76667,
  perfis_contemplacao: [{ id: "moderate", label: "Moderado", percentual_referencia: .45, lance_ideal: ideal, lance_embutido: 0 }],
});
const groups = [
  { grupo: "I227", administradora: "PORTO", matrix_approved: false, requires_composition: true,
    minQuotas: { without_embedded: 6 }, credito_maximo: 110000, prazo_restante: 147,
    cenarios: [scenario("without_embedded", 410760)] },
  { grupo: "20399", administradora: "AUTO-ITAÚ", credito_maximo: null, prazo_restante: 13,
    cenarios: [scenario("without_embedded", 0)] },
  { grupo: "1011", administradora: "CNP", matrix_approved: true, credito_maximo: 1255658.79, prazo_restante: 61,
    cenarios: [scenario("without_embedded", 56820)] },
  { grupo: "NO-BID", administradora: "TESTE", credito_maximo: 500000, prazo_restante: 12,
    cenarios: [scenario("without_embedded", null)] },
];
'''+ actions + r'''
</script>'''
        with tempfile.TemporaryDirectory(prefix="motor360-browser-") as directory:
            html = Path(directory) / "fixture.html"
            profile = Path(directory) / "chrome-profile"
            html.write_text(fixture, encoding="utf-8")
            completed = subprocess.run(
                [self.chrome, "--headless=new", "--disable-gpu", "--no-sandbox",
                 f"--user-data-dir={profile}", "--dump-dom", html.as_uri()],
                capture_output=True, text=True, timeout=30, check=True,
            )
        marker = '<pre id="result">'
        self.assertIn(marker, completed.stdout, completed.stderr[-2000:])
        payload = completed.stdout.split(marker, 1)[1].split("</pre>", 1)[0]
        try:
            return json.loads(payload)
        except json.JSONDecodeError as exc:
            raise AssertionError(f"Browser fixture did not produce JSON. DOM: {payload[:1000]}\nChrome: {completed.stderr[-3000:]}") from exc

    def test_real_sort_and_rendered_cards_agree_after_sort_change_and_cache(self):
        result = self._run_browser(r'''
const sorted = sortMotor360ItemsByBid(groups);
document.querySelector("#cards").innerHTML = sorted.map((item, index) => {
  item.ranking = index + 1;
  return renderMotor360GroupCard(item);
}).join("");
const before = document.querySelector("#motor360-group-I227 .motor360-bid-sort-value");
investorState.selectedGroupSort = "bid";
document.querySelector("#cards").innerHTML = sorted.map((item, index) => {
  item.ranking = index + 1;
  return renderMotor360GroupCard(item);
}).join("");
const cards = [...document.querySelectorAll(".motor360-group-card")].map(card => ({
  group: card.querySelector("h3")?.textContent,
  label: card.querySelector(".motor360-bid-sort-value")?.textContent.trim() || null,
  aria: card.querySelector(".motor360-bid-sort-value")?.getAttribute("aria-label") || null,
}));
const positions = cards.map(row => row.group);
const numeric = cards.slice(0, 3).map(row => {
  const match = row.label?.match(/R\$\s*([\d.,]+)/);
  return match ? Number(match[1].replaceAll(".", "").replace(",", ".")) : null;
});
document.querySelector("#result").textContent = JSON.stringify({ beforeHadNoSortLabel: before === null, cards, positions, numeric });
''')
        self.assertTrue(result["beforeHadNoSortLabel"])
        self.assertEqual(result["positions"], ["Grupo 20399", "Grupo 1011", "Grupo I227", "Grupo NO-BID"])
        self.assertEqual(result["numeric"], [0, 56820, 410760])
        self.assertTrue(all(row["label"] for row in result["cards"]))
        self.assertIn("calcul", result["cards"][-1]["label"].lower())
        self.assertIn("Menor lance ideal", result["cards"][2]["label"])
        self.assertIn("Sem embutido", result["cards"][2]["label"])
        self.assertIn("R$ 410.760,00", result["cards"][2]["label"])
        self.assertEqual(result["cards"][2]["label"], result["cards"][2]["aria"])

    def test_real_card_dom_preserves_missing_values_and_status_not_false_approval(self):
        result = self._run_browser(r'''
const incomplete = { grupo: "20370", administradora: "AUTO-ITAÚ", matrix_approved: false,
  credito_maximo: null, prazo_restante: null, alerts: [], cenarios: [scenario("without_embedded", 181500, false)] };
document.querySelector("#cards").innerHTML = renderMotor360GroupCard(incomplete);
const card = document.querySelector(".motor360-group-card");
document.querySelector("#result").textContent = JSON.stringify({
  credit: card.querySelector(".motor360-group-summary")?.textContent,
  status: card.querySelector(".motor360-group-status")?.textContent,
  scenario: card.querySelector(".motor360-scenario-card")?.textContent,
});
''')
        self.assertIn("R$ 181.500,00", result["scenario"])
        self.assertIn("- meses", result["credit"])
        self.assertNotIn("Aprovado no perfil de contemplação", result["status"])

    def test_omitted_group_diagnostics_are_complete_and_searchable_in_real_dom(self):
        source = APP_JS.read_text(encoding="utf-8")
        diagnostic_functions = "\n".join((
            _between(source, "function motor360BlockingReasonAdvice", "function renderMotor360BlockingDiagnostics"),
            _between(source, "function renderMotor360BlockingDiagnostics", "async function loadMotor360Audit"),
        ))
        result = self._run_browser(r'''
const audit = {
  metadata: { audit_id: "BROWSER-FIXTURE" },
  summary: { total_analyzed: 5, total_post_matrix_groups: 2, matrix_excluded_groups: [
    { grupo: "A1", administradora: "Banco A", source_row: 10, result: "excluded_contemplation", justification: ["lance_insuficiente_para_perfil"] },
    { grupo: "A2", administradora: "Banco A", source_row: 11, result: "excluded_data", justification: ["credito_maximo_nao_informado", "credito_maximo_nao_informado"], missing_fields: [{ reason: "credito_maximo_nao_informado" }] },
    { grupo: "", administradora: "Banco B", source_row: 12, result: "excluded_data", justification: [] },
  ] },
};
renderMotor360BlockingDiagnostics(audit);
const dialog = document.querySelector("dialog");
const before = [...dialog.querySelectorAll("tbody tr")].map(row => row.textContent);
const input = dialog.querySelector("[data-motor360-omitted-search]");
input.value = "linha 12";
input.dispatchEvent(new Event("input", { bubbles: true }));
const after = [...dialog.querySelectorAll("tbody tr")].map(row => ({ text: row.textContent, hidden: row.classList.contains("d-none") }));
document.querySelector("#result").textContent = JSON.stringify({
  summary: [...dialog.querySelectorAll(".motor360-blocking-summary b")].map(node => node.textContent),
  rows: before.length, hasA2: before.some(row => row.includes("A2")), hasSourceRow: before.some(row => row.includes("12")),
  duplicateReasonCount: (before.find(row => row.includes("A2"))?.match(/Crédito máximo/g) || []).length,
  searchResult: after.filter(row => !row.hidden).length, searchedRow: after.find(row => !row.hidden)?.text,
});
''', diagnostic_functions)
        self.assertEqual(result["summary"], ["5", "2", "3", "1"])
        self.assertEqual(result["rows"], 3)
        self.assertTrue(result["hasA2"])
        self.assertTrue(result["hasSourceRow"])
        self.assertEqual(result["duplicateReasonCount"], 1)
        self.assertEqual(result["searchResult"], 1)
        self.assertIn("12", result["searchedRow"])


if __name__ == "__main__":
    unittest.main()
