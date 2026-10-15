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
STYLE_CSS = ROOT / "backend" / "static" / "css" / "style.css"


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
            _between(source, "function motor360ExecutionStepMessage", "async function loadMotor360Audit"),
            _between(source, "function renderMotor360GroupCardUncached", "function renderMotor360GroupCard"),
            _between(source, "function renderMotor360GroupCard(item)", "function selectedMotor360Items"),
        ))

    def test_group_controls_are_grouped_separately_from_summary_metrics(self):
        result = self._run_browser(r'''
document.querySelector("#cards").innerHTML = renderMotor360GroupCard(groups[2]);
const card = document.querySelector(".motor360-group-card");
const summary = card.querySelector(".motor360-group-summary");
const actions = summary.querySelector(".motor360-group-actions");
document.querySelector("#result").textContent = JSON.stringify({
  metrics: [...summary.children].slice(0, 3).map(node => node.querySelector("small")?.textContent),
  actionsPresent: Boolean(actions),
  actionControls: [...(actions?.children || [])].map(node => node.textContent.trim().replace(/\\s+/g, " ")),
});
''')
        self.assertEqual(len(result["metrics"]), 3)
        self.assertEqual(result["metrics"][0], "Data de Venc.")
        self.assertTrue(result["metrics"][1].startswith("Cr"))
        self.assertEqual(result["metrics"][2], "Prazo restante")
        self.assertTrue(result["actionsPresent"])
        self.assertIn("Selecionar grupo", " ".join(result["actionControls"]))
        self.assertIn("Ver", result["actionControls"][-1])

    def test_group_and_scenario_controls_have_nonbreaking_responsive_layout_rules(self):
        css = STYLE_CSS.read_text(encoding="utf-8")
        self.assertIn(".motor360-group-summary .motor360-group-actions", css)
        self.assertIn(".motor360-group-actions .motor360-group-select,", css)
        self.assertIn(".motor360-scenario-title > label { display: inline-flex", css)
        self.assertIn(
            ".motor360-group-actions .motor360-group-select,\n.motor360-scenario-title > label { white-space: nowrap; }",
            css,
        )
        self.assertIn("@media (max-width: 560px)", css)
        self.assertIn("grid-template-columns: repeat(2, minmax(0, 1fr)); align-items: stretch", css)

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
window.formatMotor360Duration = value => `${Number(value || 0)} ms`;
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

    def test_real_card_dom_distinguishes_composition_candidate_from_single_quota_approval(self):
        result = self._run_browser(r'''
const candidate = {
  grupo: "1045", administradora: "CNP", result: "composition", matrix_approved: false,
  composition_candidate: true, requires_composition: true, selection_stage: "composition",
  cotas_minimas_sem_embutido: 2, cotas_minimas_com_embutido: 3,
  credito_minimo: 100000, credito_maximo: 300000, prazo_restante: 300,
  minQuotas: { without_embedded: 2, with_embedded: 3 }, alerts: [],
  cenarios: [
    { ...scenario("without_embedded", 300000, false), eligible: false, cotas_minimas: 2, credito_contratado: 300000 },
    { ...scenario("with_embedded", 300000, true), eligible: true, cotas_minimas: 3, credito_contratado: 300000 },
  ],
};
document.querySelector("#cards").innerHTML = renderMotor360GroupCard(candidate);
const card = document.querySelector(".motor360-group-card");
const normalize = value => String(value || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").replaceAll("\u00ad", "");
const scenarioCards = [...card.querySelectorAll(".motor360-scenario-card")];
document.querySelector("#result").textContent = JSON.stringify({
  status: normalize(card.querySelector(".motor360-group-status")?.textContent).replace(/[^a-zA-Z0-9]+/g, " ").trim(),
  aria: normalize(card.querySelector(".motor360-group-status")?.getAttribute("aria-label")),
  scenarioTitles: scenarioCards.map(node => normalize(node.querySelector(".motor360-scenario-title")?.textContent)),
  scenarioStatuses: scenarioCards.map(node => normalize(node.querySelector(".motor360-scenario-title span")?.textContent)),
  eligibleScenarioCompatibleClass: scenarioCards[1]?.classList.contains("is-compatible"),
});
''')
        self.assertEqual(result["status"], "Possivel em composicao min 2 cotas")
        self.assertIn("nao e aprovacao de uma cota isolada", result["aria"])
        self.assertIn("minimo de 3 cotas", result["scenarioTitles"][1])
        self.assertIn("Viavel em composicao", result["scenarioStatuses"][1])
        self.assertTrue(result["eligibleScenarioCompatibleClass"])

    def test_composition_candidate_card_uses_aggregate_totals_and_profile_gap(self):
        result = self._run_browser(r'''
const profileRows = [{ id: "moderate", label: "Moderado", percentual_referencia: .9,
  lance_ideal: 540000, lance_ideal_total: 540000, lance_embutido: 0,
  lance_cliente: 460000, percentual_lance_efetivo: .766667, atinge_perfil: false, falta_para_ideal: 80000 }];
const candidate = {
  grupo: "40145", administradora: "ITAÚ", result: "composition", matrix_approved: false,
  composition_candidate: true, requires_composition: true, selection_stage: "composition",
  credito_minimo: 70000, credito_maximo: 114778, prazo_restante: 133,
  cotas_minimas_sem_embutido: 6, cotas_minimas_com_embutido: 8,
  minQuotas: { without_embedded: 6, with_embedded: 8 }, alerts: [],
  cenarios: [
    {
      ...scenario("without_embedded", 114778, false), eligible: true,
      financially_eligible_in_composition: true, profile_compatible_in_composition: false,
      cotas_minimas: 6,
      composition_totals: { credito_contratado: 600000, credito_liquido_projetado: 600000,
        credito_por_cota: 100000, lance_cliente_total: 460000, lance_embutido: 0,
        lance_total_cenario: 460000, percentual_lance_cliente: .766667,
        percentual_lance_efetivo: .766667, saldo_devedor: 750000,
        parcela_inicial: 5639.10, parcela_pos_contemplacao: 2154.25,
        cotas_minimas: 6, perfis_contemplacao: profileRows },
    },
    {
      ...scenario("with_embedded", 114778, true), eligible: true,
      financially_eligible_in_composition: true, profile_compatible_in_composition: false,
      cotas_minimas: 8,
      composition_totals: { credito_contratado: 857142.86, credito_liquido_projetado: 600000,
        credito_por_cota: 107142.86, lance_cliente_total: 460000, lance_embutido: 257142.86,
        lance_total_cenario: 717142.86, percentual_lance_cliente: .536667,
        percentual_lance_efetivo: .836667, saldo_devedor: 1071428.58,
        parcela_inicial: 8055.10, parcela_pos_contemplacao: 2622.96,
        cotas_minimas: 8, perfis_contemplacao: [{ ...profileRows[0], lance_ideal: 514285.71,
          lance_ideal_total: 771428.57, lance_embutido: 257142.86, percentual_lance_efetivo: .836667,
          atinge_perfil: false, falta_para_ideal: 54285.71 }] },
    },
  ],
};
investorState.selectedGroupSort = "bid";
document.querySelector("#cards").innerHTML = renderMotor360GroupCard(candidate);
const card = document.querySelector(".motor360-group-card");
document.querySelector("#result").textContent = JSON.stringify({
  card: card.textContent.replaceAll("\u00ad", ""),
  order: motor360BidSortLabel(candidate),
  raw: [...card.querySelectorAll(".motor360-scenario-grid b")].map(node => node.textContent),
});
''')
        self.assertIn("R$ 600.000,00", result["card"])
        self.assertIn("R$ 460.000,00", result["card"])
        self.assertIn("R$ 5.639,10", result["card"])
        self.assertIn("R$ 857.142,86", result["card"])
        self.assertIn("R$ 257.142,86", result["card"])
        self.assertIn("R$ 717.142,86", result["card"])
        self.assertIn("perfil pendente", result["card"].lower())
        self.assertIn("perfil", result["card"].lower())
        self.assertIn("R$ 514.285,71", result["order"])
        self.assertIn("80.000,00", result["card"])

    def test_execution_log_shows_all_three_outcomes_without_losing_candidates(self):
        result = self._run_browser(r'''
const messages = [
  motor360ExecutionStepMessage({ order: 3, input_count: 502, approved_count: 317, composition_count: 4, rejected_count: 181, duration_ms: 0 }),
  motor360ExecutionStepMessage({ order: 4, input_count: 321, approved_count: 317, composition_count: 4, rejected_count: 0, duration_ms: 0 }),
  motor360ExecutionStepMessage({ order: 5, input_count: 321, approved_count: 317, composition_count: 4, rejected_count: 0, duration_ms: 0 }),
].map(message => message.normalize("NFD").replace(/[\u0300-\u036f]/g, "").replaceAll("·", "|"));
document.querySelector("#result").textContent = JSON.stringify(messages);
''')
        self.assertIn("Entrada 502 | aprovados individualmente 317 | opcoes em composicao 4 | eliminados 181", result[0])
        self.assertIn("Entrada 321 | aprovados 317 | opcoes em composicao 4 | eliminados 0", result[1])
        self.assertIn("Entrada 321 | aprovados 317 | opcoes em composicao 4 | eliminados 0", result[2])

    def test_omitted_group_diagnostics_are_complete_and_searchable_in_real_dom(self):
        source = APP_JS.read_text(encoding="utf-8")
        diagnostic_functions = "\n".join((
            _between(source, "function motor360BlockingReasonAdvice", "function renderMotor360BlockingDiagnostics"),
            _between(source, "function renderMotor360BlockingDiagnostics", "async function loadMotor360Audit"),
        ))
        result = self._run_browser(r'''
const audit = {
  metadata: { audit_id: "BROWSER-FIXTURE" },
  summary: { total_analyzed: 6, total_displayed_groups: 2, matrix_excluded_groups: [
    { grupo: "A1", administradora: "Banco A", source_row: 10, result: "excluded_credit", justification: ["credito_fora_da_faixa"] },
    { grupo: "A2", administradora: "Banco A", source_row: 11, result: "excluded_data", justification: ["credito_maximo_nao_informado", "credito_maximo_nao_informado"], missing_fields: [{ reason: "credito_maximo_nao_informado" }] },
    { grupo: "-", administradora: "Banco B", source_row: 12, result: "excluded_invalid_identity", justification: ["identificacao_grupo_invalida"] },
    { grupo: "", administradora: "Banco B", source_row: 13, result: "composition", justification: ["composicao_parcela_maxima_excedida"] },
  ] },
};
renderMotor360BlockingDiagnostics(audit);
const dialog = document.querySelector("dialog");
const normalize = value => String(value || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").replaceAll("\u00ad", "");
const before = [...dialog.querySelectorAll("tbody tr")].map(row => normalize(row.textContent));
const resultCells = [...dialog.querySelectorAll("tbody tr td:nth-child(4)")].map(cell => normalize(cell.textContent));
const input = dialog.querySelector("[data-motor360-omitted-search]");
input.value = "linha 13";
input.dispatchEvent(new Event("input", { bubbles: true }));
const after = [...dialog.querySelectorAll("tbody tr")].map(row => ({ text: normalize(row.textContent), hidden: row.classList.contains("d-none") }));
document.querySelector("#result").textContent = JSON.stringify({
  summary: [...dialog.querySelectorAll(".motor360-blocking-summary b")].map(node => node.textContent),
  rows: before.length, resultCells, hasA2: before.some(row => row.includes("A2")), hasSourceRow: before.some(row => row.includes("12")), hasUnnamed: before.some(row => row.includes("Sem identificador de grupo")),
  hasTechnicalCode: before.some(row => /excluded_[a-z_]+|\bcomposition\b/.test(row)),
  duplicateReasonCount: (before.find(row => row.includes("A2"))?.match(/Credito maximo/g) || []).length,
  searchResult: after.filter(row => !row.hidden).length, searchedRow: after.find(row => !row.hidden)?.text,
});
''', diagnostic_functions)
        self.assertEqual(result["summary"], ["6", "2", "4", "2"])
        self.assertEqual(result["rows"], 4)
        self.assertIn("Fora da faixa de credito", result["resultCells"])
        self.assertIn("Possivel em composicao; nao aprovado como cota isolada", result["resultCells"])
        self.assertFalse(result["hasTechnicalCode"])
        self.assertTrue(result["hasA2"])
        self.assertTrue(result["hasSourceRow"])
        self.assertTrue(result["hasUnnamed"])
        self.assertEqual(result["duplicateReasonCount"], 1)
        self.assertEqual(result["searchResult"], 1)
        self.assertIn("13", result["searchedRow"])

    def test_full_audit_tables_translate_composition_and_exclusion_codes(self):
        source = APP_JS.read_text(encoding="utf-8")
        audit_function = _between(source, "function renderMotor360Audit", "function renderMotor360GroupAudit")
        result = self._run_browser(r'''
const audit = {
  metadata: { audit_id: "AUDIT-LABELS" }, summary: {
    total_analyzed: 2, total_displayed_groups: 1, total_matrix_approved_groups: 0,
    matrix_excluded_groups: [{ grupo: "EX1", administradora: "CNP", source_row: 20,
      result: "excluded_credit", justification: ["credito_fora_da_faixa"] }],
  },
  client_snapshot: { raw_fields: [] }, execution_steps: [{ order: 3, name: "Matriz e opções de composição",
    formula_or_rule: "Contabilizadas separadamente", input_count: 2, approved_count: 0,
    composition_count: 1, rejected_count: 1, incomplete_count: 0 }], columns_used: [], formulas: [],
  excluded_groups: [], incomplete_groups: [], group_results: [{ grupo: "1045", administradora: "CNP",
    result: "composition", matrix_approved: false, stage_results: {}, scenarios: [], source_values: {} }],
  final_ordering: { execution_summary: "", rules: [] }, warnings: [], data_source: {},
};
const html = renderMotor360Audit(audit);
document.querySelector("#cards").innerHTML = html;
const rendered = document.querySelector("#cards").textContent;
const sequenceTable = [...document.querySelectorAll(".motor360-audit-panel table")]
  .find(table => table.querySelector("thead")?.textContent.includes("Opções viáveis em composição"));
document.querySelector("#result").textContent = JSON.stringify({
  hasHumanCreditLabel: rendered.includes("Fora da faixa de crédito"),
  hasHumanCompositionLabel: rendered.includes("Possível em composição; não aprovado como cota isolada"),
  separatesCompositionCount: Boolean(sequenceTable && sequenceTable.tBodies[0].rows[0].textContent.includes("0") && sequenceTable.tBodies[0].rows[0].textContent.includes("1")),
  technicalCodeLeak: /excluded_credit|\bcomposition\b/.test(rendered),
});
''', "function auditDateTime() { return '-'; }\nfunction formatMotor360Duration() { return '-'; }\n" + audit_function)
        self.assertTrue(result["hasHumanCreditLabel"])
        self.assertTrue(result["hasHumanCompositionLabel"])
        self.assertTrue(result["separatesCompositionCount"])
        self.assertFalse(result["technicalCodeLeak"])


if __name__ == "__main__":
    unittest.main()
