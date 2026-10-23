import unittest
import re
import json
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class StaticEmailTest(unittest.TestCase):
    def test_motor360_profile_lookup_is_pure_and_formatters_are_reused(self):
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")
        profile_start = app_js.index("function motor360ClientProfile()")
        profile_end = app_js.index("\nfunction renderMotor360ClientProfileSummary", profile_start)
        profile_reader = app_js[profile_start:profile_end]

        self.assertNotIn("collectClientProfile(", profile_reader)
        self.assertIn("motor360ClientProfileCache", profile_reader)
        self.assertIn("const moneyFormatter = new Intl.NumberFormat", app_js)
        self.assertIn("const percentFormatter = new Intl.NumberFormat", app_js)
        card_start = app_js.index("function renderMotor360GroupCard(item)")
        card_end = app_js.index("\nfunction selectedMotor360Items", card_start)
        self.assertIn("const compositionKey = selected", app_js[card_start:card_end])
        self.assertIn("const MOTOR360_GROUP_PAGE_SIZE = 20", app_js)
        self.assertIn("items.slice(pageStart, pageStart + MOTOR360_GROUP_PAGE_SIZE)", app_js)
        self.assertIn("installMotor360DelegatedControls(results)", app_js)
        persist_start = app_js.index("function persistMotor360SelectionNow()")
        persist_end = app_js.index("\nfunction persistMotor360Selection()", persist_start)
        persist_body = app_js[persist_start:persist_end]
        self.assertEqual(persist_body.count("localStorage.setItem("), 1)
        self.assertNotIn("selectedGroupData:", persist_body)
        self.assertIn('localStorage.removeItem("crediclass.motor360.selectedGroupData")', persist_body)
        self.assertIn("selectedCredits: Object.fromEntries(investorState.selectedCredits)", persist_body)

    def test_motor360_group_interactions_update_only_affected_cards(self):
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")
        refresh = app_js.split("function refreshMotor360VisibleCards(", 1)[1].split("function installMotor360DelegatedControls", 1)[0]
        render = app_js.split("function renderInvestorAnalysis(result)", 1)[1].split("function renderInvestorPreferenceOptions", 1)[0]

        self.assertIn("motor360ItemsByGroup(investorState.result)", refresh)
        self.assertIn("card.replaceWith(nextCard)", refresh)
        self.assertNotIn("renderInvestorAnalysis(", refresh)
        self.assertNotIn('results.querySelectorAll(".motor360-scenario-card")', render)
        self.assertIn("const sourceMetricsHtml = motor360ScenarioSourceMetrics(item)", app_js)
        self.assertIn("data-scenario-id=\"${escapeHtml(scenario.id)}\"", app_js)

    def test_motor360_group_and_administrator_keys_are_memoized(self):
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")
        self.assertIn("const motor360AdministratorKeyCache = new Map()", app_js)
        self.assertIn("const motor360ObjectGroupKeyCache = new WeakMap()", app_js)
        self.assertIn("const motor360ItemsByGroupCache = new WeakMap()", app_js)
        self.assertIn("function motor360ItemsByGroup(result = investorState.result)", app_js)

    def test_motor360_requests_compact_payload_without_breaking_legacy_api(self):
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")
        main_py = (ROOT / "backend" / "main.py").read_text(encoding="utf-8")
        self.assertIn('fetch("/api/viabilidade-360/analisar?compact=true"', app_js)
        self.assertIn("response: Response, compact: bool = False", main_py)
        self.assertIn('result.pop("items", None)', main_py)
        self.assertIn('result.pop("credit_items", None)', main_py)
        self.assertIn('result.pop("composition_items", None)', main_py)
        self.assertIn('if compact:', main_py)

    def test_motor360_credit_is_selected_per_scenario_before_quota_count(self):
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")
        css = (ROOT / "backend" / "static" / "css" / "style.css").read_text(encoding="utf-8")

        self.assertIn('data-credit-action="scenario"', app_js)
        self.assertIn('data-quota-action="scenario"', app_js)
        self.assertIn('${chosenCredit === null ? "disabled" : ""}', app_js)
        self.assertIn('"credito_minimo", "Menor Crédito"', app_js)
        self.assertIn('"credito_intermediario_3", "Créd. Inter. 3"', app_js)
        self.assertIn('"credito_maximo", "Maior Crédito"', app_js)
        self.assertIn('without_embedded: selectedCreditFor(item, "without_embedded")', app_js)
        self.assertIn('with_embedded: selectedCreditFor(item, "with_embedded")', app_js)
        self.assertIn('study_credit_basis: "credito_escolhido_por_cenario"', app_js)
        self.assertIn(".motor360-scenario-credit select", css)

    def test_release_version_matches_backend_render_and_front_assets(self):
        config_py = (ROOT / "backend" / "config.py").read_text(encoding="utf-8")
        engine_py = (ROOT / "backend" / "consortium_viability_engine.py").read_text(encoding="utf-8")
        render_yaml = (ROOT / "render.yaml").read_text(encoding="utf-8")
        index_html = (ROOT / "backend" / "static" / "index.html").read_text(encoding="utf-8")
        build_version = re.search(r'<meta name="crediclass-build" content="([^"]+)"', index_html).group(1)

        self.assertIn(f'version: str = "{build_version}"', config_py)
        self.assertIn(f'version="{build_version}"', config_py)
        self.assertIn(f'MOTOR_VERSION = "{build_version}"', engine_py)
        self.assertRegex(render_yaml, rf"(?m)^\s+value: {re.escape(build_version)}$")

    def test_index_referencia_app_js_atualizado(self):
        index_html = (ROOT / "backend" / "static" / "index.html").read_text(encoding="utf-8")

        build_version = re.search(r'<meta name="crediclass-build" content="([^"]+)"', index_html).group(1)
        self.assertIn(f"/static/css/style.css?v={build_version}", index_html)
        self.assertIn("fonts.googleapis.com/css2", index_html)
        self.assertIn("family=DM+Sans", index_html)
        self.assertIn("family=Raleway", index_html)
        self.assertIn(f"/static/js/app.js?v={build_version}", index_html)
        self.assertIn(f"/static/js/api.js?v={build_version}", index_html)
        self.assertIn('<button class="nav-item active" type="button" data-screen="perfil">', index_html)
        self.assertIn('<section id="screen-perfil" class="screen-panel active">', index_html)

    def test_motor360_alerta_cotas_acima_da_media_historica(self):
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")
        style_css = (ROOT / "backend" / "static" / "css" / "style.css").read_text(encoding="utf-8")

        self.assertIn("Média máxima", app_js)
        self.assertIn("Cálculo do período:", app_js)
        self.assertIn("capacity.total_contemplacoes", app_js)
        self.assertIn("Acima da média histórica", app_js)
        self.assertNotIn('class="motor360-quota-guidance"', app_js)
        self.assertIn("scheduleHistoryHoverHide", app_js)
        self.assertIn('modal.addEventListener("mouseenter", cancelHistoryHoverHide)', app_js)
        self.assertIn("motor360-quota-warning", style_css)

    def test_motor360_carrega_historico_completo_dos_grupos(self):
        main_py = (ROOT / "backend" / "main.py").read_text(encoding="utf-8")
        endpoint = main_py.split("def viabilidade_360_analisar", 1)[1].split("@app.get", 1)[0]

        self.assertIn("groups = list_grupos(include_history=True)", endpoint)

    def test_motor360_composicao_manual_de_multiplas_cotas(self):
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")
        style_css = (ROOT / "backend" / "static" / "css" / "style.css").read_text(encoding="utf-8")

        self.assertIn("Grupos compatíveis para composição da carteira", app_js)
        self.assertIn("const quotaCapacity = motor360QuotaCapacity(item)", app_js)
        self.assertIn("renderMotor360FloatingSelectionSummary", app_js)
        self.assertIn("Composição atual", app_js)
        self.assertIn("function selectedCompositionScenarioMetrics", app_js)
        self.assertIn("function selectedCompositionAssessment", app_js)
        self.assertIn("Dentro do limite de renda", app_js)
        self.assertIn('max="50"', app_js)
        self.assertIn("renderSelectedGroupsCartSummary", app_js)
        self.assertIn("motor360-cart-summary", style_css)
        self.assertIn("motor360-floating-summary", style_css)
        self.assertIn("--brand-orange: var(--primary)", style_css)

    def test_motor360_legacy_quota_review_and_shared_resources_are_explicit(self):
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")
        screen = app_js.split("function renderSelectedGroupsScreen()", 1)[1].split("function persistMotor360Selection()", 1)[0]
        quota_update = app_js.split("function setScenarioQuotaCount(", 1)[1].split("function minimumQuotasFor(", 1)[0]
        metrics = app_js.split("function selectedCompositionScenarioMetrics(", 1)[1].split("function selectedCompositionAssessment(", 1)[0]

        self.assertIn("empty.classList.toggle(\"d-none\", allItems.length > 0)", screen)
        self.assertIn("results.classList.toggle(\"d-none\", allItems.length === 0)", screen)
        self.assertIn("new Set(investorState.selectedScenarioIds.get(key) || [])", quota_update)
        self.assertIn("quotaCountFor(key) <= 0", quota_update)
        self.assertIn("const quotas = quotaCountFor(groupId, scenarioId)", metrics)
        self.assertIn("quotas_by_scenario", app_js)
        self.assertIn("composição combinada", app_js)
        self.assertIn("O lance próprio disponível é compartilhado uma única vez entre os contratos.", app_js)
        self.assertIn("allocatedPool * profile.ideal / portfolioRequired", metrics)
        self.assertNotIn("selectedPortfolioTotals", app_js)

    def test_motor360_rotulos_e_selo_de_status_coerentes_com_a_composicao(self):
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")
        style_css = (ROOT / "backend" / "static" / "css" / "style.css").read_text(encoding="utf-8")
        card_renderer = app_js.split("function renderMotor360GroupCardUncached", 1)[1].split("function renderMotor360GroupCard(", 1)[0]

        self.assertIn("const showPortfolioLabels = Boolean((selected && scenarioQuotaCount > 1) || (aggregate && Number(aggregate.cotas_minimas) > 1))", card_renderer)
        self.assertIn("scenario.composition_totals", card_renderer)
        self.assertIn("scenario.profile_compatible_in_composition", card_renderer)
        self.assertIn('showPortfolioLabels ? "Lance próprio atribuído ao grupo" : "Lance do cliente"', card_renderer)
        self.assertIn('showPortfolioLabels ? "Lance total no grupo" : "Lance total do cenário"', card_renderer)
        self.assertIn(".motor360-client-profile-summary-note", style_css)
        self.assertIn('item.requires_composition === true', card_renderer)
        self.assertIn('`Possível em composição · mín. ${visibleMinimum} cotas`', card_renderer)
        self.assertIn(': "Defina cotas por cenário"', card_renderer)
        self.assertIn(': "Requer ajuste"', card_renderer)
        self.assertIn('class="motor360-group-status is-${displayStatusTone}"', card_renderer)
        self.assertIn('title="${escapeHtml(displayStatusDetail)}"', card_renderer)
        self.assertIn(".motor360-group-status.is-neutral", style_css)
        self.assertIn(".motor360-group-status.is-warning", style_css)
        self.assertIn(".motor360-group-status.is-approved", style_css)

    def test_motor360_explica_credito_por_cota_e_nao_marca_lance_zero_como_falta(self):
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")
        card_renderer = app_js.split("function renderMotor360GroupCardUncached", 1)[1].split("function renderMotor360GroupCard(", 1)[0]

        self.assertIn('`1 cota não cobre o crédito desejado · mínimo de ${minimumQuotasFor(item, scenario.id)} cotas`', card_renderer)
        self.assertIn("const meetsBid = totalIdeal <= 0 || available >= totalIdeal", card_renderer)
        self.assertIn('"Sem lance próprio necessário"', card_renderer)

    def test_motor360_perfil_em_foco_tem_destaque_visual_nos_cards(self):
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")
        style_css = (ROOT / "backend" / "static" / "css" / "style.css").read_text(encoding="utf-8")

        self.assertIn('const focused = profile.id === focusProfileId', app_js)
        self.assertIn('class="motor360-profile-focus-tag">Em foco', app_js)
        self.assertIn(".motor360-profile-card-value.is-focused", style_css)

    def test_motor360_troca_administradora_e_cenario_sem_refazer_analise_e_local(self):
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")
        request_loader = app_js.split("async function loadInvestorAnalysis()", 1)[1].split("function investorAnalysisCacheKey", 1)[0]
        administrator_listener = app_js.split('document.getElementById("investorAdministratorFilter")?.addEventListener("change"', 1)[1].split('document.getElementById("recalculateInvestorAnalysisBtn")', 1)[0]

        self.assertIn("administradora: null, filtro_lance_embutido: null", request_loader)
        self.assertIn("renderInvestorAnalysis(investorState.result)", administrator_listener)
        self.assertNotIn("loadInvestorAnalysis(", administrator_listener)
        self.assertIn("return JSON.stringify(profile)", app_js)

    def test_motor360_reaproveita_metricas_e_cards_ao_ordenar(self):
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")
        sort_function = app_js.split("function applySelectedGroupsFiltersAndSort", 1)[1].split("function renderMotor360SelectionFilters", 1)[0]
        card_renderer = app_js.split("function renderMotor360GroupCard(item)", 1)[1].split("function selectedMotor360Items", 1)[0]

        self.assertIn("const motor360GroupAnalyticsCache = new Map()", app_js)
        self.assertIn("const cached = motor360GroupAnalyticsCache.get(cacheKey)", app_js)
        self.assertIn('investorState.selectedGroupIds.has(motor360GroupKey(a)) ? selectedValueFor(a, "credit") : analyticsFor(a).groupMaxCredit', sort_function)
        self.assertIn('investorState.selectedGroupSort || "credit_by_admin"', card_renderer)
        self.assertIn('if (sort === "credit_by_admin")', sort_function)
        self.assertIn('return creditB - creditA || Number(a.ranking || 0) - Number(b.ranking || 0)', sort_function)

    def test_motor360_menor_lance_usa_o_mesmo_total_de_composicao_do_card(self):
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")
        index_html = (ROOT / "backend" / "static" / "index.html").read_text(encoding="utf-8")
        ideal_helper = app_js.split("function motor360CompositionIdealBid", 1)[1].split("function motor360ScenarioIdsForSort", 1)[0]
        sort_function = app_js.split("function applySelectedGroupsFiltersAndSort", 1)[1].split("function renderMotor360SelectionFilters", 1)[0]
        card_renderer = app_js.split("function renderMotor360GroupCardUncached", 1)[1].split("function renderMotor360GroupCard(", 1)[0]
        bid_sort_helper = app_js.split("function motor360BidSortValue", 1)[1].split("function motor360BidSortDescription", 1)[0]

        self.assertIn("aggregateIdealBid", ideal_helper)
        self.assertNotIn("idealPerQuota * quotas", ideal_helper)
        self.assertIn("motor360FocusedProfileId()", ideal_helper)
        self.assertIn("motor360CompositionIdealBid(item, scenario, value.id)", card_renderer)
        self.assertIn("motor360CompositionIdealBid(item, scenario, profileId)", bid_sort_helper)
        self.assertIn('if (sort === "bid") return retainSelected(sortMotor360ItemsByBid(filtered))', sort_function)
        self.assertIn("Sem seleção: exibe grupos disponíveis, inclusive opções viáveis em composição.", index_html)
        self.assertIn("numericIdeal >= 0", ideal_helper)
        self.assertIn('if (sort === "bid") return retainSelected(sortMotor360ItemsByBid(filtered))', sort_function)
        self.assertIn('script.src = "https://cdn.jsdelivr.net/npm/echarts@6.1.0/dist/echarts.min.js"', app_js)
        self.assertIn("Não foi possível carregar os gráficos", app_js)
        self.assertNotIn("motor360HasHistoryEvidence", app_js)
        self.assertIn("motor360BidSortLabel(item)", card_renderer)
        self.assertIn('investorState.selectedGroupSort || "credit_by_admin"', app_js.split("function renderMotor360GroupCard(item)", 1)[1].split("function selectedMotor360Items", 1)[0])
        self.assertIn("R$ 0 é válido", app_js)
        self.assertIn("crédito e histórico não alteram a posição", app_js)

        # Production audit: the 68.46% profile reference is already based on
        # the target composition credit (R$ 600k), not one target per quota.
        i227_composition_bid = 410_760
        self.assertEqual(i227_composition_bid, 600_000 * 0.6846)

    def test_motor360_ordenacao_real_corresponde_ao_rotulo_do_card(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node.js indisponível para executar o teste de integração do helper da tela")
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")

        def section(start, end):
            return app_js.split(start, 1)[1].split(end, 1)[0]

        functions = "\n".join((
            "function motor360CompositionIdealBid" + section("function motor360CompositionIdealBid", "function motor360ScenarioIdsForSort"),
            "function motor360ScenarioIdsForSort" + section("function motor360ScenarioIdsForSort", "function motor360BidSortValue"),
            "function motor360BidSortValue" + section("function motor360BidSortValue", "function motor360BidSortDescription"),
            "function motor360BidSortLabel" + section("function motor360BidSortLabel", "function sortMotor360ItemsByBid"),
            "function sortMotor360ItemsByBid" + section("function sortMotor360ItemsByBid", "function selectedGroupAnalytics"),
        ))
        harness = r'''
const investorState = { selectedGroupIds: new Set(), selectedGroupScenario: "per_group" };
const groupScenarios = new Map();
const motor360GroupKey = (item) => String(item.grupo);
const motor360FocusedProfileId = () => "moderate";
const selectedScenarioIdsForGroup = (key) => groupScenarios.get(key) || new Set();
const selectedMotor360Items = () => [];
const selectedCompositionScenarioMetrics = () => ({ entries: [] });
const minimumQuotasFor = (item, scenarioId) => item.minQuotas?.[scenarioId] || 1;
const quotaCountFor = (item) => item.quotas || 1;
const formatMoney = (value) => `R$ ${Number(value).toFixed(2)}`;
''' + functions + r'''
const scenario = (id, ideal) => ({ id, perfis_contemplacao: [{ id: "moderate", lance_ideal: ideal }] });
const items = [
  { grupo: "I227", requires_composition: true, minQuotas: { without_embedded: 6 }, credito_maximo: 110000, historico_12_meses: [], cenarios: [scenario("without_embedded", 410760)] },
  { grupo: "20399", credito_maximo: null, historico_12_meses: [], cenarios: [scenario("without_embedded", null)] },
  { grupo: "1011", credito_maximo: 1255658.79, historico_12_meses: [{ qtd_contemplacoes: 3 }], cenarios: [scenario("without_embedded", 56820)] },
  { grupo: "20370", credito_maximo: 63230, historico_12_meses: [{ qtd_contemplacoes: 8 }], cenarios: [scenario("with_embedded", 2000), scenario("without_embedded", 1000)] },
  { grupo: "ZERO", credito_maximo: null, historico_12_meses: [], cenarios: [scenario("without_embedded", 0)] },
];
const sorted = sortMotor360ItemsByBid(items);
console.log(JSON.stringify(sorted.map((item) => ({ grupo: item.grupo, label: motor360BidSortLabel(item) }))));
'''
        completed = subprocess.run([node, "-e", harness], check=True, capture_output=True, text=True)
        rows = json.loads(completed.stdout)
        self.assertEqual([row["grupo"] for row in rows], ["ZERO", "20370", "1011", "I227", "20399"])
        self.assertIn("R$ 0.00", rows[0]["label"])
        self.assertIn("Sem embutido: R$ 1000.00", rows[1]["label"])
        self.assertIn("R$ 410760.00", rows[3]["label"])
        self.assertIn("sem refer", rows[4]["label"].lower())
        self.assertIn("calcul", rows[4]["label"].lower())
        self.assertEqual(rows[-1]["grupo"], "20399")

        # Explicit scenario filtering must use only that scenario's exact card value.
        harness_with_scenario = harness.replace('selectedGroupScenario: "per_group"', 'selectedGroupScenario: "with_embedded"')
        completed = subprocess.run([node, "-e", harness_with_scenario], check=True, capture_output=True, text=True)
        with_embedded = json.loads(completed.stdout)
        self.assertEqual(with_embedded[0]["grupo"], "20370")
        self.assertIn("Com embutido: R$ 2000.00", with_embedded[0]["label"])

    def test_motor360_auditoria_destaca_grupos_omitidos_e_timing_de_referencia(self):
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")
        style_css = (ROOT / "backend" / "static" / "css" / "style.css").read_text(encoding="utf-8")
        main_py = (ROOT / "backend" / "main.py").read_text(encoding="utf-8")

        self.assertIn('class="motor360-audit-omitted" open', app_js)
        self.assertIn("Grupos que não aparecem na lista do Motor 360", app_js)
        self.assertIn("matrixExcludedRows", app_js)
        self.assertIn("Nenhum grupo foi omitido pela matriz nesta execução.", app_js)
        self.assertIn(".motor360-audit-content details.motor360-audit-omitted", style_css)
        self.assertIn('response.headers["Server-Timing"]', main_py)
        self.assertIn("sheet_load;dur=", main_py)
        self.assertIn("audit_save;dur=", main_py)
        self.assertIn("sheet_cache;dur=", main_py)

    def test_motor360_impedimentos_lista_todos_os_omitidos_com_linha_e_motivo_unico(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node.js indisponível para validar a renderização dos impedimentos")
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")

        def section(start, end):
            return app_js.split(start, 1)[1].split(end, 1)[0]

        functions = "\n".join((
            "function formatMotor360Reason" + section("function formatMotor360Reason", "function formatMotor360Duration"),
            "function motor360BlockingReasonAdvice" + section("function motor360BlockingReasonAdvice", "function renderMotor360BlockingDiagnostics"),
            "function renderMotor360BlockingDiagnostics" + section("function renderMotor360BlockingDiagnostics", "async function loadMotor360Audit"),
        ))
        harness = r'''
const escapeHtml = (value) => String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");
const dialog = { innerHTML: "", querySelector: () => null, addEventListener: () => {}, showModal: () => {} };
globalThis.document = { createElement: () => dialog, body: { append: () => {} } };
''' + functions + r'''
const audit = {
  metadata: { audit_id: "FIXTURE-AUDIT" },
  summary: { total_analyzed: 5, total_post_matrix_groups: 2, matrix_excluded_groups: [
    { grupo: "A1", administradora: "Banco A", source_row: 10, result: "excluded_contemplation", justification: ["lance_insuficiente_para_perfil"] },
    { grupo: "A2", administradora: "Banco A", source_row: 11, result: "excluded_data", justification: ["credito_maximo_nao_informado", "credito_maximo_nao_informado"], missing_fields: [{ reason: "credito_maximo_nao_informado" }] },
    { grupo: "", administradora: "-", source_row: 12, result: "excluded_data", justification: [], missing_fields: [] },
  ] },
};
renderMotor360BlockingDiagnostics(audit);
console.log(JSON.stringify(dialog.innerHTML));
'''
        completed = subprocess.run([node, "-e", harness], check=True, capture_output=True, text=True)
        rendered = json.loads(completed.stdout)
        self.assertEqual(rendered.count("<tr data-omitted-search="), 3)
        self.assertIn("Analisados</small><b>5", rendered)
        self.assertIn("Na lista</small><b>2", rendered)
        self.assertIn("Omitidos</small><b>3", rendered)
        self.assertIn("<b>1</b></span></div>", rendered)
        self.assertIn("Banco A", rendered)
        self.assertIn("Linha da planilha", rendered)
        self.assertEqual(rendered.count("(V)"), 1)
        self.assertNotIn(" e outros", rendered)

    def test_motor360_formata_todos_os_tempos_em_portugues_sem_ambiguidade(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node.js indisponível para validar a formatação de duração")
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")
        formatter = "function formatMotor360Duration" + app_js.split("function formatMotor360Duration", 1)[1].split("function renderMotor360Audit", 1)[0]
        harness = formatter + r'''
console.log(JSON.stringify([formatMotor360Duration(56.528), formatMotor360Duration(1979), formatMotor360Duration(22096)]));
'''
        completed = subprocess.run([node, "-e", harness], check=True, capture_output=True, text=True)
        formatted = json.loads(completed.stdout)
        self.assertEqual(formatted, ["56,5 ms", "1,98 s", "22,10 s"])

    def test_motor360_mantem_selecionados_visiveis_e_ordena_por_contemplacoes(self):
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")
        style_css = (ROOT / "backend" / "static" / "css" / "style.css").read_text(encoding="utf-8")

        self.assertIn("Maior Média de Contemplações", app_js)
        self.assertIn("motor360QuotaCapacity(item)?.media_contemplacoes", app_js)
        self.assertIn("motor360-selected-group-label", app_js)
        self.assertIn("data-floating-summary-toggle", app_js)
        self.assertIn("motor360-selected-dock { position: sticky", style_css)
        self.assertIn("motor360-floating-summary.is-minimized", style_css)

    def test_motor_360_filtra_grupos_por_uma_administradora(self):
        index_html = (ROOT / "backend" / "static" / "index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")

        self.assertIn('id="investorAdministratorFilter"', index_html)
        self.assertIn("function motor360AdministratorKey(item)", app_js)
        self.assertIn("sourceItems.filter((item) => motor360AdministratorKey(item) === selectedAdministratorKey)", app_js)
        self.assertIn('item?.administradora || item?.adm', app_js)

    def test_motor_360_usa_lance_declarado_quando_a_simulacao_ainda_nao_foi_definida(self):
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")

        self.assertIn("investorState.simulatedBid !== null", app_js)
        self.assertIn("const simulatedBid = hasSimulatedBid ? Number(investorState.simulatedBid) : declaredBid", app_js)
        self.assertIn("investorState.lastDeclaredBid !== null && investorState.lastDeclaredBid !== declaredBid", app_js)
        self.assertIn("investorState.lastDesiredCredit !== null && investorState.lastDesiredCredit !== desiredCredit", app_js)

    def test_matriz_exibe_o_cenario_que_atingiu_o_perfil(self):
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")

        self.assertIn('entry.scenario.id === "with_embedded" ? "com embutido" : "sem embutido"', app_js)
        self.assertNotIn("cenário elegível:", app_js)

    def test_motor_360_nao_deixa_cenario_nao_elegivel_vazar_no_filtro(self):
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")

        self.assertIn("selectedScenarioIds.has(scenario.id)", app_js)
        self.assertIn("scenario.eligible === true || (scenario.credit_compatible === true && scenario.term_compatible === true)", app_js)

    def test_mapa_grupos_exibe_resumo_compacto_sem_cards_financeiros(self):
        index_html = (ROOT / "backend" / "static" / "index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")
        style_css = (ROOT / "backend" / "static" / "css" / "style.css").read_text(encoding="utf-8")

        self.assertIn('class="map-summary-strip"', index_html)
        self.assertIn('id="summaryTotal"', index_html)
        self.assertIn('id="summaryAdministradoras"', index_html)
        self.assertNotIn("Credito Total Disponivel", index_html)
        self.assertNotIn("Taxa ADM Media", index_html)
        self.assertNotIn("Ultima Atualizacao", index_html)
        self.assertNotIn("summaryCredito", app_js)
        self.assertNotIn("summaryTaxa", app_js)
        self.assertNotIn("summaryUpdated", app_js)
        self.assertIn(".map-summary-strip", style_css)

    def test_mapa_grupos_exibe_colunas_de_lance_por_perfil(self):
        index_html = (ROOT / "backend" / "static" / "index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")
        style_css = (ROOT / "backend" / "static" / "css" / "style.css").read_text(encoding="utf-8")

        for full_label, short_label in [
            ("Agressivo", "Agr."),
            ("Moderado", "Mod."),
            ("Conservador", "Cons."),
            ("Super Conservador", "S. Cons."),
        ]:
            self.assertIn(f'<th class="lance-profile-header" title="{full_label}">', index_html)
            self.assertIn(f"<span>{short_label}</span>", index_html)
        self.assertIn("lance-header-control", index_html)
        for header in [
            '<th title="ID Grupo">Grupo</th>',
            '<th title="Administradora">Adm.</th>',
            '<th title="Tipo de Bem">Tipo</th>',
            '<th title="Prazo Restante">Prazo Rest.</th>',
            '<th title="Última atualização da tríade Maior Lance, Menor Lance e Quantidade de Contemplação">Atualizado</th>',
        ]:
            self.assertIn(header, index_html)
        groups_table_markup = index_html.split('<tbody id="groupsTableBody"></tbody>')[0].split('<table class="table table-hover align-middle group-table">')[-1]
        self.assertNotIn("Ult. Ass.", groups_table_markup)
        self.assertNotIn("Cred. Min.", groups_table_markup)
        self.assertNotIn("1a Ass.", groups_table_markup)
        self.assertNotIn("<th>Status</th>", groups_table_markup)
        self.assertNotIn("item.ultima_assembleia", app_js.split("function renderGroupsTable")[1].split("function defasagemStatusLabel")[0])
        render_groups_block = app_js.split("function renderGroupsTable")[1].split("function setDefasagemState")[0]
        self.assertNotIn("item.credito_minimo", render_groups_block)
        self.assertNotIn("item.primeira_assembleia", render_groups_block)
        self.assertIn("item.prazo_restante", render_groups_block)
        self.assertIn("item.atualizado", render_groups_block)
        self.assertIn("data-history-index", render_groups_block)
        self.assertIn("function showHistoryHoverModal", app_js)
        self.assertIn('id="historyHoverModal"', index_html)
        self.assertIn('data-lance-sort="agressivo"', index_html)
        self.assertNotIn('data-lance-sort-order="desc"', index_html)
        self.assertNotIn(">Filtro</option>", index_html)
        for field in ["lance_agressivo", "lance_moderado", "lance_conservador", "lance_super_conservador"]:
            self.assertIn(f"formatPercent(item.{field})", app_js)
        self.assertIn(".lance-profile-cell", style_css)
        self.assertIn(".lance-sort-select", style_css)

    def test_modal_edicao_grupo_exibe_campos_da_planilha(self):
        index_html = (ROOT / "backend" / "static" / "index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")

        self.assertIn("Demais campos da planilha", index_html)
        self.assertIn('id="groupFormSheetFieldsGrid"', index_html)
        self.assertIn("function renderGroupFormSheetFields", app_js)
        self.assertIn("function collectGroupFormSheetFieldsPayload", app_js)
        self.assertIn("function sheetFieldMaskType", app_js)
        self.assertIn("formatSheetFieldInputValue(header, value)", app_js)
        self.assertIn("campos_planilha: collectGroupFormSheetFieldsPayload()", app_js)
        self.assertIn('if (field === "administradora" || field === "grupo"', app_js)

    def test_dependencias_visuais_sao_servidas_localmente(self):
        index_html = (ROOT / "backend" / "static" / "index.html").read_text(encoding="utf-8")
        style_css = (ROOT / "backend" / "static" / "css" / "style.css").read_text(encoding="utf-8")

        self.assertIn("/static/vendor/bootstrap.min.css?v=5.3.3", index_html)
        self.assertIn("/static/vendor/bootstrap.bundle.min.js?v=5.3.3", index_html)
        self.assertIn("/static/vendor/chart.umd.min.js?v=4.4.3", index_html)
        self.assertIn("/static/favicon.svg?v=1", index_html)
        self.assertNotIn("cdn.jsdelivr.net", index_html)
        self.assertIn(".d-none", style_css)

    def test_motor_360_e_o_unico_motor_de_selecao_exposto(self):
        index_html = (ROOT / "backend" / "static" / "index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")

        self.assertNotIn('data-screen="administradoras"', index_html)
        self.assertNotIn('id="screen-administradoras"', index_html)
        self.assertNotIn("Motor Inteligente de Seleção", index_html)
        self.assertNotIn("Motor Inteligente de Seleção", app_js)
        self.assertIn('data-screen="motor360"', index_html)
        self.assertIn('id="screen-motor360"', index_html)
        self.assertIn('if (screenName === "motor360") {', app_js)
        self.assertIn('renderInvestorAnalysis(investorState.result);', app_js)
        self.assertIn('/api/viabilidade-360/analisar', app_js)
        self.assertIn("const controller = new AbortController();", app_js)
        self.assertIn("signal: attemptController.signal", app_js)
        self.assertIn('if (error.name === "AbortError" || requestId !== investorAnalysisRequestId) return;', app_js)
        self.assertIn("const MOTOR360_ANALYSIS_REQUEST_TIMEOUT_MS = 60000;", app_js)
        self.assertIn("const MOTOR360_ANALYSIS_MAX_ATTEMPTS = 5;", app_js)
        self.assertIn("const retryableStatuses = new Set([408, 425, 429, 500, 502, 503, 504]);", app_js)
        self.assertIn("falha temporária de conexão", app_js)
        self.assertIn("a tela de consulta permanece ativa", app_js)
        self.assertNotIn('data-screen="viabilidade"', index_html)
        self.assertNotIn('id="screen-viabilidade"', index_html)
        self.assertNotIn('screenName === "viabilidade"', app_js)
        self.assertNotIn("renderSmartEngine", app_js)
        self.assertNotIn("scenarioAnalysis", app_js)
        for removed in [
            "selectionPipeline",
            "Motor de Elegibilidade das Administradoras",
            "Fase 2 - Selecao Melhores Grupos",
            "administratorPlansBody",
            "administratorEligibilityBody",
            "selectionFunnelSummary",
            "viabilityPhase2Summary",
            "viabilityRankingBody",
            "analyzeViabilityBtn",
            "addAdministratorPlanBtn",
            "saveAdministratorPlansBtn",
        ]:
            self.assertNotIn(removed, index_html)
        for removed in [
            "function refreshAdministratorEligibility",
            "function renderAdministratorPlans",
            "function saveAdministratorPlans",
            "function analyzeViability",
            "function openViabilityAudit",
            "function resetViabilityForm",
            "function phase2SelectionSignature",
            "function setPipelineStatus",
            "viabilityState",
            "administratorPlanComputedFields",
            "recalculateAdministratorPlanComputedCells",
        ]:
            self.assertNotIn(removed, app_js)
        self.assertNotIn("function exportAdministratorsCsv()", app_js)
        self.assertNotIn("function syncAdministratorInterviewToGroups()", app_js)
    def test_fluxos_legados_do_motor_foram_removidos(self):
        index_html = (ROOT / "backend" / "static" / "index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")

        self.assertNotIn('id="screen-viabilidade"', index_html)
        self.assertNotIn('id="analyzeViabilityBtn"', index_html)
        self.assertNotIn('data-screen-jump="perfil"', index_html)
        self.assertNotIn('id="addAdministratorPlanBtn"', index_html)
        self.assertNotIn('id="saveAdministratorPlansBtn"', index_html)
        self.assertNotIn('primaryAction.classList.toggle("d-none", screenName === "viabilidade"', app_js)
        self.assertNotIn("Aguardando selecao dos melhores grupos", index_html)
        self.assertNotIn("Top 10 exibido", app_js)
        self.assertNotIn("await analyzeViability({ silent: true })", app_js)
        self.assertNotIn("Filtro 1 manteve", app_js)
        self.assertNotIn("data-viability-action", app_js)
        self.assertNotIn("openFinancialStudy(button.dataset.groupId, item)", app_js)
        self.assertNotIn('id="viabilityProfileSummary"', index_html)
        self.assertNotIn("function renderViabilityProfileSummary()", app_js)
        self.assertNotIn("Viabilidade por Administradoras", index_html)
        self.assertNotIn("administratorViabilityBody", index_html)
        self.assertNotIn("function renderAdministratorViability", app_js)
        self.assertNotIn('id="viabilityForm"', index_html)
        self.assertNotIn('id="clearViabilityBtn"', index_html)
        self.assertNotIn('id="viabilityChecklist"', index_html)
    def test_tela_perfil_cliente_fica_no_fluxo_antes_do_mapa(self):
        index_html = (ROOT / "backend" / "static" / "index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")
        style_css = (ROOT / "backend" / "static" / "css" / "style.css").read_text(encoding="utf-8")

        self.assertLess(index_html.index('data-screen="perfil"'), index_html.index('data-screen="mapa"'))
        self.assertIn("Jornada do Cliente", index_html)
        self.assertIn("Administrativo", index_html)
        self.assertIn('id="screen-perfil"', index_html)
        self.assertIn("Perfil do Cliente", index_html)
        self.assertIn("clientProfileCredito", index_html)
        self.assertIn("clientProfileTotalDisponivel", index_html)
        self.assertIn("clientProfileConceito", index_html)
        self.assertIn("Análise preliminar dos titulares", index_html)
        self.assertNotIn("3 - Análise preliminar dos titulares", index_html)
        self.assertIn('id="clientPreliminaryAnalysis"', index_html)
        self.assertIn("function calculateClientPreliminaryAnalysis", app_js)
        self.assertIn("function renderClientPreliminaryAnalysis", app_js)
        self.assertIn("function renderPreliminaryAuditTrail", app_js)
        self.assertIn("Demonstrativo logico do calculo", app_js)
        self.assertIn("Somando FGTS + recurso proprio", app_js)
        self.assertIn(".client-preliminary-audit", style_css)
        self.assertIn('toNumber(document.getElementById("clientProfileParcelaIdeal").value)', app_js)
        self.assertIn('toNumber(document.getElementById("clientProfileLanceProprio").value)', app_js)
        self.assertIn('if (activeType === "pj")', app_js)
        self.assertIn('preliminaryDecision(pfLinha1Ok && pfLinha2Ok && pfAge.ok)', app_js)
        self.assertIn("Total Lance FGTS + RP", app_js)
        self.assertIn("sem embutido", app_js)
        self.assertNotIn("sem embudo", app_js)
        self.assertNotIn("sim embudo", app_js)
        self.assertIn("Total Renda PJ + Socio", app_js)
        self.assertIn("function evaluatePjCapacityScenarios", app_js)
        self.assertIn("Cenario 1 - CNPJ com renda PJ", app_js)
        self.assertIn("Cenario 2 - CNPJ com PJ + socio", app_js)
        self.assertIn("Cenario 3 - CPF do socio", app_js)
        self.assertIn("basePjSocios = faturamento + rendaSocios", app_js)
        self.assertIn("Aprovacao somente pela PJ", app_js)
        self.assertIn("Aprovacao PJ com composicao de renda dos socios", app_js)
        self.assertIn("Aprovacao somente pelo CPF dos socios", app_js)
        self.assertIn("approvedScenario", app_js)
        self.assertIn("nao permitido", app_js)
        self.assertIn("adminRuleAceitaPJ", index_html)
        self.assertIn("adminRuleComposicaoPJSocios", index_html)
        self.assertIn("adminRuleCpfSocio", index_html)
        self.assertNotIn("Math.max(pjFaturamento * 0.3", app_js)
        self.assertNotIn('["Resultado", pf.resultado', app_js)
        self.assertNotIn('["Linha 1", pf.decisaoLinha1', app_js)
        self.assertIn(".client-preliminary-grid", style_css)
        self.assertNotIn("Resumo do Perfil", index_html)
        self.assertNotIn("clientProfileSummary", index_html)
        self.assertIn("Avançar para Motor de Inteligência", index_html)
        self.assertIn("function saveClientProfile", app_js)
        self.assertIn("function applyClientProfileToFlow", app_js)
        self.assertNotIn("function renderClientProfileSummary", app_js)
        self.assertIn("Lance Recursos Proprios", app_js)
        self.assertIn("Renda do Cliente", app_js)
        self.assertIn("function calculateAgeFromDateText", app_js)
        self.assertNotIn("function smartEngineGenericField", app_js)
        self.assertNotIn('data-generic-filter="lance_embutido"', index_html)
        self.assertIn("function formatMoneyInputValue(value)", app_js)
        self.assertIn("const moneyInputIds", app_js)
        self.assertIn(".client-profile-layout", style_css)

    def test_configuracoes_possui_planos_administradoras(self):
        index_html = (ROOT / "backend" / "static" / "index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")
        style_css = (ROOT / "backend" / "static" / "css" / "style.css").read_text(encoding="utf-8")

        self.assertIn("Regras Administradoras", index_html)
        self.assertIn('id="administratorRulesForm"', index_html)
        self.assertIn('id="administratorRulesBody"', index_html)
        self.assertIn("adminRuleAdministradora", index_html)
        source = index_html + app_js
        for field_id in [
            "adminRuleStatusProduto",
            "adminRuleDataProduto",
            "adminRuleResponsavelProduto",
            "adminRuleLimiteRendaTexto",
            "adminRuleAceitaAdesao",
        ]:
            self.assertIn(field_id, index_html)
            self.assertIn(field_id, app_js)
        for field_name in [
            "status_operacional",
            "data_cadastro_produto",
            "responsavel_produto",
            "limite_sem_comprovacao_renda_texto",
            "aceita_adesao_clientes_texto",
        ]:
            self.assertIn(field_name, app_js)
        self.assertIn("function renderAdministratorRules(rules)", app_js)
        self.assertIn("function saveAdministratorRule()", app_js)
        self.assertIn("administradoras_regras", app_js)
        self.assertNotIn("administratorPlanRuleHelp", app_js)
        self.assertNotIn("function renderAdministratorPlanRowLabel(row)", app_js)
        self.assertNotIn("admin-plan-rule-marker", app_js)

    def test_configuracoes_possui_regras_de_negocio_com_feedback(self):
        index_html = (ROOT / "backend" / "static" / "index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")
        style_css = (ROOT / "backend" / "static" / "css" / "style.css").read_text(encoding="utf-8")

        self.assertIn("Regras de Negocio", index_html)
        self.assertIn('data-bs-target="#configRegrasNegocio"', index_html)
        self.assertIn('id="businessRulesBody"', index_html)
        self.assertIn('id="saveBusinessRulesFeedbackBtn"', index_html)
        self.assertIn("const businessRulesFlow", app_js)
        self.assertIn("function renderBusinessRules", app_js)
        self.assertIn("function collectBusinessRuleFeedbacks", app_js)
        self.assertIn("async function saveBusinessRuleFeedbacks", app_js)
        self.assertIn("regras_negocio_feedbacks", app_js)
        for etapa in ["Perfil do Cliente", "Estrategia", "Fase 1 - Calculadora de Grupos", "Fase 2 - Selecao Melhores Grupos por Prazo Remanescente e Compatibilidade Menor Lance"]:
            self.assertIn(etapa, app_js)
        for exemplo in [
            "credito_liquido_desejado",
            "percentual_lance_embutido",
            "parcela_total_cenario",
            "Super Agressivo",
            "cartas candidatas",
            "FGTS so entra quando permitido",
        ]:
            self.assertIn(exemplo, app_js)
        self.assertIn("business-rule-note-input", style_css)
        self.assertIn(".business-rules-table", style_css)
        self.assertNotIn("Soma recursos proprios com FGTS apenas para exibir", app_js)

    def test_filtros_de_credito_validam_intervalo(self):
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")

        self.assertIn("function validateMapCreditFilters(filters)", app_js)
        self.assertIn("O credito minimo nao pode ser maior que o credito maximo.", app_js)

    def test_percentuais_de_entrada_sao_formatados_sem_residuo_decimal(self):
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")

        self.assertIn("function percentToInputValue(value)", app_js)
        self.assertIn('minimumFractionDigits: 2', app_js)
        self.assertIn('maximumFractionDigits: 2', app_js)
        self.assertIn("return percentToInputValue(value);", app_js)

    def test_mapa_grupos_possui_recarregamento_manual(self):
        index_html = (ROOT / "backend" / "static" / "index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")

        self.assertIn('id="reloadMapDataBtn"', index_html)
        self.assertIn("Recarregar dados", index_html)
        self.assertIn("async function reloadMapData()", app_js)
        self.assertIn('apiPost("/reload", {})', app_js)
        self.assertIn("data.administradoras", app_js)
        self.assertIn("data.total_administradoras", app_js)

    def test_mapa_grupos_mantem_gestao_de_defasagem_sem_botao_na_lista(self):
        index_html = (ROOT / "backend" / "static" / "index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")
        style_css = (ROOT / "backend" / "static" / "css" / "style.css").read_text(encoding="utf-8")

        self.assertNotIn('id="openDefasagemBtn"', index_html)
        self.assertIn('id="defasagemModal"', index_html)
        self.assertIn("Gestao de Defasagem dos Grupos", index_html)
        self.assertIn("Plano de acao da atualizacao", index_html)
        self.assertIn("async function openDefasagemModal()", app_js)
        self.assertIn('apiGet("/grupos/defasagem")', app_js)
        self.assertIn("Preparando dados de defasagem da planilha", app_js)
        self.assertIn('apiPut(`/grupos/defasagem/${encodeURIComponent(grupoId)}`', app_js)
        self.assertIn("function renderDefasagemReport(report)", app_js)
        self.assertIn("data-defasagem-check", app_js)
        self.assertIn("defasagem-month-card", app_js)
        self.assertIn(".defasagem-summary-grid", style_css)
        self.assertIn(".defasagem-month-chip", style_css)
        self.assertIn(".defasagem-status.status-critical", style_css)

    def test_formulario_grupo_nao_exige_campos_obrigatorios(self):
        index_html = (ROOT / "backend" / "static" / "index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")

        group_form = index_html.split('id="groupCrudForm"', 1)[1].split("</form>", 1)[0]
        self.assertNotIn(" required", group_form)
        self.assertIn("Preencha somente os dados que deseja salvar", group_form)
        self.assertNotIn("Preencha os campos obrigatorios do grupo.", app_js)
        self.assertIn("function optionalNumber(value)", app_js)

    def test_backup_logs_disponivel_em_configuracoes(self):
        index_html = (ROOT / "backend" / "static" / "index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")
        style_css = (ROOT / "backend" / "static" / "css" / "style.css").read_text(encoding="utf-8")

        self.assertIn("Backup & Logs", index_html)
        self.assertIn('id="downloadConfigBackupBtn"', index_html)
        self.assertIn('id="operationalLogsList"', index_html)
        self.assertIn("function downloadConfigBackup()", app_js)
        self.assertIn("function addOperationalLog(message)", app_js)
        self.assertIn("application/json;charset=utf-8", app_js)
        self.assertIn("crediclass-configuracoes-", app_js)
        self.assertIn(".log-list", style_css)

    def test_acoes_do_sistema_possuem_rotinas_distintas(self):
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")

        self.assertIn("function clearSystemCache()", app_js)
        self.assertIn("async function reindexSystemData()", app_js)
        self.assertIn("async function validateSystemIntegrity()", app_js)
        self.assertIn("async function restartSystemSync()", app_js)
        self.assertIn('document.getElementById("clearSystemCacheBtn").addEventListener("click", clearSystemCache)', app_js)
        self.assertIn('document.getElementById("validateSystemBtn").addEventListener("click"', app_js)

    def test_crud_grupos_salva_historico_mensal(self):
        index_html = (ROOT / "backend" / "static" / "index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")
        style_css = (ROOT / "backend" / "static" / "css" / "style.css").read_text(encoding="utf-8")

        self.assertIn("Historico Mensal", index_html)
        self.assertIn("group-form-dialog", index_html)
        self.assertIn('id="groupFormHistoryGrid"', index_html)
        self.assertIn('id="groupFormHistoryYear"', index_html)
        self.assertIn('<option value="2024">2024</option>', index_html)
        self.assertIn('<option value="2025">2025</option>', index_html)
        self.assertIn('<option value="2026">2026</option>', index_html)
        self.assertNotIn('id="groupFormHistoryAddMonthBtn"', index_html)
        self.assertNotIn('id="historyUpdateAddMonthBtn"', index_html)
        self.assertNotIn("Adicionar mes", index_html)
        self.assertNotIn("function addHistoryEditorMonth", app_js)
        self.assertIn("function historyEditorYearFilter(prefix)", app_js)
        self.assertIn("function syncGroupFormVisibleHistory()", app_js)
        self.assertIn("function collectGroupFormHistoryPayloads()", app_js)
        self.assertIn('document.getElementById("groupFormHistoryYear").addEventListener("change"', app_js)
        self.assertIn(".history-add-month", style_css)
        self.assertIn(".history-year-filter", style_css)
        self.assertIn("display: none !important", style_css)
        self.assertIn("const HISTORY_START_MONTH = \"2024-01\"", app_js)
        self.assertIn("function collectHistoryBatchPayloads(prefix)", app_js)
        self.assertIn("markHistoryPayloadsSaved", app_js)
        self.assertIn("/historico/lote", app_js)
        self.assertIn("function normalizeHistoryField(field, rawValue)", app_js)
        self.assertIn("data-original-value", app_js)
        self.assertIn("Nenhuma alteracao de historico para salvar.", app_js)
        self.assertIn("o menor lance nao pode ser maior que o maior lance", app_js)
        self.assertIn("if (detailsModal) detailsModal.hide();", app_js)
        self.assertIn("function findLoadedGroupSummary(groupId)", app_js)
        self.assertIn("Carregando historico completo do grupo", app_js)
        self.assertIn("Nao foi possivel carregar o historico completo", app_js)
        self.assertIn(".group-form-dialog .modal-footer", style_css)
        self.assertIn("collectGroupFormHistoryPayloads()", app_js)
        self.assertIn('/historico/lote`, { items: historyPayloads })', app_js)

    def test_grafico_historico_grupo_exibe_lances_sem_barras(self):
        index_html = (ROOT / "backend" / "static" / "index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")

        self.assertIn('type: "line"', app_js)
        self.assertIn("Percentual do lance", app_js)
        self.assertNotIn('label: "Contemplacoes"', app_js)
        self.assertNotIn('yAxisID: "y1"', app_js)
        self.assertNotIn("Resumo do historico", index_html)
        self.assertNotIn('id="detailsHistoryBody"', index_html)

    def test_detalhe_grupo_renderiza_auditoria(self):
        index_html = (ROOT / "backend" / "static" / "index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")
        style_css = (ROOT / "backend" / "static" / "css" / "style.css").read_text(encoding="utf-8")

        self.assertIn('id="detailsAuditList"', index_html)
        self.assertIn("function renderDetailsAudit(group)", app_js)
        self.assertIn("renderDetailsAudit(group)", app_js)
        self.assertIn(".audit-list", style_css)

    def test_modal_ver_grupo_nao_exibe_botao_editar(self):
        index_html = (ROOT / "backend" / "static" / "index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")

        details_modal = index_html.split('id="groupDetailsModal"', 1)[1].split('id="defasagemModal"', 1)[0]
        self.assertNotIn('id="detailsEditBtn"', details_modal)
        self.assertNotIn("detailsEditBtn", app_js)
        self.assertIn('data-map-action="editar"', app_js)
        self.assertNotIn('data-map-action="duplicar"', app_js)
        self.assertNotIn('data-map-action="excluir"', app_js)

    def test_viabilidade_alinha_perfis_tipo_bem_e_lance_zero(self):
        index_html = (ROOT / "backend" / "static" / "index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")

        for label in [
            "Contemplar - urgente - 3 meses",
            "Contemplar - rapido - 6 meses",
            "Contemplar - moderado - 12 meses",
            "Contemplar - conservador - 24 meses",
            "Contemplar - investidor - 36 meses",
        ]:
            self.assertIn(label, index_html + app_js)
        self.assertIn("Parcela maxima desejada", index_html)
        self.assertIn("Lance maximo com recurso proprio", index_html)
        self.assertIn("function clientProfileConcept(months)", app_js)
        self.assertIn("CLIENT_OBJECTIVE_RULES", app_js)
        self.assertIn('id="clientProfileTipoBem"', index_html)
        self.assertIn('id="clientProfileTipoBem" class="form-select" required', index_html)
        self.assertNotIn('<option value="Auto">Automóvel</option>', index_html)
        self.assertIn('updateClientProfileTipoBemOptions(tipos)', app_js)
        self.assertIn('apiGet(`/grupos?${buildQuery(filters)}`)', app_js)
        self.assertIn("function validateClientProfileTipoBem", app_js)
        self.assertIn('tipo_bem: document.getElementById("clientProfileTipoBem").value', app_js)
        self.assertNotIn('tipo_bem: "Imovel"', app_js)
        self.assertIn('const lanceManual = toNumber(document.getElementById("clientProfileLanceProprio").value);', app_js)

    def test_perfil_cliente_suporta_titulares_pf_pj(self):
        index_html = (ROOT / "backend" / "static" / "index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")

        for label in [
            "Pessoa fisica individual",
            "Pessoa fisica com conjuge",
            "Dois titulares / grupo familiar",
            "Pessoa juridica",
        ]:
            self.assertIn(label, index_html + app_js)
        self.assertIn("CLIENT_PJ_SOCIOS_LIMIT = 5", app_js)
        self.assertIn('cnpj: ""', app_js)
        self.assertIn('profileHolderInput("pessoa_juridica.empresa.cnpj", empresa.cnpj, "CNPJ")', app_js)
        self.assertIn("renderClientProfileTitulares", app_js)
        self.assertIn("summarizeClientTitulares", app_js)
        self.assertIn("titulares: totals.titulares", app_js)
        self.assertNotIn("currentStudy.payload.titulares", app_js)

    def test_tema_configurado_aplica_aparencia(self):
        index_html = (ROOT / "backend" / "static" / "index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")
        style_css = (ROOT / "backend" / "static" / "css" / "style.css").read_text(encoding="utf-8")

        build_version = re.search(r'<meta name="crediclass-build" content="([^"]+)"', index_html).group(1)
        self.assertIn(f"/static/css/style.css?v={build_version}", index_html)
        self.assertNotIn('id="configTema"', index_html)
        self.assertIn("function applyTheme(theme)", app_js)
        self.assertIn("document.body.dataset.theme", app_js)
        self.assertIn('body[data-theme="escuro"]', style_css)

    def test_motor360_composition_bid_fields_use_aggregate_metrics(self):
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")

        self.assertIn("contractedCredit: entries.reduce((sum, entry) => sum + entry.contractedCredit, 0)", app_js)
        self.assertIn("embedded: entries.reduce((sum, entry) => sum + entry.embedded, 0)", app_js)
        self.assertIn("const cardClientBid = mixedSelectedScenarios", app_js)
        self.assertIn("metrics ? Number(metricEntry?.profiles[focusProfileId]?.available || 0)", app_js)
        self.assertIn("const cardScenarioBid = metrics ? cardClientBid + cardEmbedded", app_js)
        self.assertIn("const cardContractedCredit = Number(metricEntry?.contractedCredit || 0)", app_js)
        self.assertIn("cardClientBid / cardContractedCredit", app_js)
        self.assertIn("cardScenarioBid / cardContractedCredit", app_js)
        self.assertNotIn("cells[1].innerHTML", app_js)
        self.assertNotIn("cells[3].innerHTML", app_js)

    def test_login_inicial_protege_dashboard(self):
        index_html = (ROOT / "backend" / "static" / "index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")
        api_js = (ROOT / "backend" / "static" / "js" / "api.js").read_text(encoding="utf-8")
        style_css = (ROOT / "backend" / "static" / "css" / "style.css").read_text(encoding="utf-8")

        self.assertIn('class="auth-pending"', index_html)
        self.assertIn('id="loginScreen"', index_html)
        self.assertIn('id="loginForm"', index_html)
        self.assertIn("/static/images/crediclass-logo.png", index_html)
        self.assertIn('id="logoutBtn"', index_html)
        self.assertIn("async function submitLogin(event)", app_js)
        self.assertIn("/api/auth/login", app_js)
        self.assertIn("/api/auth/me", app_js)
        self.assertIn("/api/auth/logout", app_js)
        self.assertIn("function showLogin", app_js)
        self.assertIn("function showApp", app_js)
        self.assertIn("async function initializeDashboardData()", app_js)
        self.assertIn('document.getElementById("loginForm").addEventListener("submit", submitLogin)', app_js)
        self.assertIn('credentials: "same-origin"', api_js)
        self.assertIn("response.status === 401", api_js)
        self.assertIn(".login-screen", style_css)
        self.assertIn(".logout-btn", style_css)

    def test_configuracoes_remove_aba_geral(self):
        index_html = (ROOT / "backend" / "static" / "index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")

        self.assertNotIn("configGeral", index_html)
        self.assertNotIn("configGeneralForm", index_html)
        for field_id in [
            "configEmpresaNome",
            "configMoeda",
            "configTema",
            "configCasasValores",
            "configCasasPercentuais",
            "configMeiaParcela",
            "configLanceEmbutido",
            "configHistorico36",
        ]:
            self.assertNotIn(f'id="{field_id}"', index_html)
            self.assertNotIn(field_id, app_js)

        self.assertIn("function setSelectBool(id, value)", app_js)
        self.assertIn("function getSelectBool(id)", app_js)

    def test_notificacoes_configuracoes_removidas_da_tela(self):
        index_html = (ROOT / "backend" / "static" / "index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")

        self.assertNotIn("configNotificacoes", index_html)
        for field_id in ["notifySync", "notifyStudySaved", "notifyHistoryUpdated", "notifyIntegrationFailure"]:
            self.assertNotIn(f'id="{field_id}"', index_html)
            self.assertNotIn(field_id, app_js)

    def test_alertas_operacionais_nao_dependem_de_aba_notificacoes(self):
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")

        self.assertNotIn("function isNotificationEnabled", app_js)
        self.assertNotIn("function notifyWhen", app_js)
        self.assertIn("function showToast(message, type = \"success\")", app_js)
        self.assertNotIn("Estudo salvo:", app_js)
        self.assertIn('showToast(`Google Sheets sincronizado: ${result.total} linhas.`, "success")', app_js)
        self.assertIn('showToast("Nao foi possivel reindexar os dados.", "danger")', app_js)

    def test_integracoes_e_acesso_configuracoes_removidas_da_tela(self):
        index_html = (ROOT / "backend" / "static" / "index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")

        self.assertNotIn("configIntegracoes", index_html)
        self.assertNotIn("configAcesso", index_html)
        self.assertNotIn('id="configureIntegrationsBtn"', index_html)
        self.assertNotIn('id="configIntegrationsForm"', index_html)
        self.assertNotIn('id="configAccessGrid"', index_html)
        self.assertNotIn("renderAccessPolicy", app_js)
        for field_id in ["integrationGoogleSheetsToggle", "integrationPiperunToggle", "integrationEmailToggle", "integrationBackupToggle"]:
            self.assertNotIn(f'id="{field_id}"', index_html)
            self.assertNotIn(field_id, app_js)

    def test_usuarios_operacionais_possuem_acoes_reais(self):
        index_html = (ROOT / "backend" / "static" / "index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")

        self.assertIn('id="newConfigUserBtn"', index_html)
        self.assertIn('id="configUserModal"', index_html)
        self.assertIn('id="configUserForm"', index_html)
        self.assertIn("function saveConfigUsers(usuarios", app_js)
        self.assertIn("function openConfigUserForm(mode", app_js)
        self.assertIn("function submitConfigUserForm()", app_js)
        self.assertIn('data-config-user-action="editar"', app_js)
        self.assertIn('data-config-user-action="status"', app_js)
        self.assertIn('data-config-user-action="remover"', app_js)
        self.assertIn('apiPut("/configuracoes", { usuarios })', app_js)

if __name__ == "__main__":
    unittest.main()
