from pathlib import Path
import re
import unittest

from backend.main import app


ROOT = Path(__file__).resolve().parents[1]


class FinancialStudyPartsTest(unittest.TestCase):
    def test_new_history_screen_uses_separate_actions_and_sandboxed_snapshot(self):
        html = (ROOT / "backend/static/index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "backend/static/js/app.js").read_text(encoding="utf-8")
        study_start = html.index('<section id="screen-estudo"')
        history_start = html.index('<section id="screen-historico-estudos"')
        crm_start = html.index('<section id="screen-crm-piperun"')
        study_screen = html[study_start:history_start]
        history_screen = html[history_start:crm_start]

        self.assertIn('data-screen="historico-estudos"', html)
        self.assertIn('id="approveFinancialStudyBtn"', study_screen)
        self.assertIn('id="rejectFinancialStudyBtn"', study_screen)
        self.assertLess(study_screen.index('id="approveFinancialStudyBtn"'), study_screen.index('<article class="financial-study-document"'))
        self.assertIn('id="financialStudyHistoryRows"', history_screen)
        self.assertIn('id="financialStudyHistoryFrame"', history_screen)
        self.assertIn('sandbox="allow-same-origin allow-modals"', history_screen)
        self.assertIn('function printFinancialStudyHistoryItem()', app_js)
        self.assertIn('id="generateFinancialStudyShareBtn"', history_screen)
        self.assertIn('id="copyFinancialStudyShareBtn"', history_screen)
        self.assertIn('id="revokeFinancialStudyShareBtn"', history_screen)
        self.assertIn("O link expirará em 30 dias", app_js)
        self.assertIn("financialStudyApprovalSnapshot(items, investmentSimulation)", app_js)
        self.assertIn('apiPost("/financial-studies"', app_js)
        self.assertIn('apiGet(`/financial-studies/${encodeURIComponent(studyId)}`)', app_js)
        self.assertIn("A seleção atual será mantida", app_js)

    def test_old_study_apis_and_public_routes_remain_unregistered(self):
        paths = {route.path for route in app.routes}
        self.assertFalse(any(path.startswith("/api/estudos") for path in paths))
        self.assertFalse(any(path.startswith("/api/public-estudos") for path in paths))
        self.assertFalse(any(path.startswith("/api/templates-estudos") for path in paths))
        self.assertNotIn("/estudo/{estudo_id}", paths)

    def test_part_one_is_static_fixed_copy_and_has_the_brand_image(self):
        html = (ROOT / "backend/static/index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "backend/static/js/app.js").read_text(encoding="utf-8")
        start = html.index('<section id="screen-estudo"')
        end = html.index("</section>", start)
        screen = html[start:end]

        self.assertIn('data-study-part="1"', screen)
        self.assertIn('data-study-part-name="Titulo Estudo Financeiro"', screen)
        self.assertIn("financial-study-part--introduction", screen)
        self.assertIn('src="/static/images/crediclass-logo.png"', screen)
        self.assertIn('alt="Crediclass — Aquisições Inteligentes"', screen)
        self.assertIn("Estudo Financeiro | Aquisição de Imóvel", screen)
        self.assertIn("Prezado,", screen)
        self.assertIn(
            "O presente Estudo Financeiro foi elaborado com base nas informações fornecidas e nas condições de mercado disponíveis na data de sua emissão e parâmetros abaixo.",
            screen,
        )
        self.assertIn(
            "O seu objetivo é apresentar cenários comparativos, auxiliando o cliente em seu processo de tomada de decisão.",
            screen,
        )
        self.assertIn(
            "As informações apresentadas possuem caráter informativo e ilustrativo, não constituindo garantia de resultado ou promessa de contemplação.",
            screen,
        )
        self.assertNotRegex(screen, re.compile(r"\{\{|\}\}|\$\{[^}]+\}|\b(?:cliente|grupo|cota)_\w+\b", re.I))
        self.assertIn("function clearRetiredFinancialStudyState()", app_js)
        self.assertNotIn("renderEmptyFinancialStudyScreen", app_js)
        self.assertNotIn("saveCurrentStudy", app_js)
        self.assertNotIn("openSharedStudyFromUrl", app_js)

    def test_part_two_uses_client_credit_editable_rate_and_motor_average_terms(self):
        html = (ROOT / "backend/static/index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "backend/static/js/app.js").read_text(encoding="utf-8")
        start = html.index('data-study-part="2"')
        end = html.index("</section>", start)
        part = html[start:end]

        self.assertIn('data-study-part-name="Simulação de Investimento"', part)
        self.assertIn("SIMULAÇÃO DE INVESTIMENTO", part)
        self.assertIn("A taxa anual é uma premissa editável pelo consultor", part)
        self.assertIn('id="financialStudyPart2AnnualRate"', part)
        for fixed_label in (
            "Uso de Recurso Próprio",
            "Valor Resgate Investimentos",
            "Rendimento Ano",
            "Prazo em Meses",
            "Custo de Perda de Rendimento no Período",
        ):
            self.assertIn(fixed_label, part)
        self.assertIn("À Vista", part)
        self.assertIn('id="financialStudyPart2Redemption"', part)
        self.assertIn('id="financialStudyPart2Cost1"', part)
        self.assertIn('id="financialStudyPart2Cost2"', part)
        self.assertIn('id="financialStudyPart2Cost3"', part)
        renderer_start = app_js.index("function renderFinancialStudyInvestment()")
        renderer_end = app_js.index("\nasync function approveCurrentFinancialStudy()", renderer_start)
        renderer = app_js[renderer_start:renderer_end]
        self.assertIn("selectedMotor360Items()", renderer)
        self.assertIn("terms.reduce((sum, term) => sum + term, 0) / terms.length", renderer)
        self.assertIn("(rate / 12) * principal", renderer)
        self.assertIn("principal * ((1 + rate) ** (term / 12)) - principal", renderer)
        self.assertIn('financialStudyApprovalSnapshot(items, investmentSimulation)', app_js)
        self.assertIn('rateInput.replaceWith(staticRate)', app_js)
        self.assertNotIn("<img", part)
        self.assertNotRegex(part, re.compile(r"\{\{|\}\}|\$\{[^}]+\}"))

    def test_part_three_has_fixed_copy_and_motor_selected_administrator(self):
        html = (ROOT / "backend/static/index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "backend/static/js/app.js").read_text(encoding="utf-8")
        start = html.index('data-study-part="3"')
        end = html.index("</section>", start)
        part = html[start:end]

        self.assertIn('data-study-part-name="Simulação dos melhores consórcios"', part)
        self.assertIn("SIMULAÇÃO DOS MELHORES CONSÓRCIOS", part)
        self.assertIn('id="financialStudyPart3Administrator"', part)
        self.assertIn("Nenhuma administradora selecionada", part)
        self.assertNotIn("<img", part)
        for fixed_copy in (
            "Critérios de seleção:",
            "Grupos antigos:",
            "Histórico de lance:",
            "Estabilidade nos lances:",
            "Saúde financeira:",
            "Lance embutido:",
            "Como funciona:",
            "Contemplações Mensais:",
            "Uso da Carta de Crédito:",
            "Participam do sorteio todos consorciados",
            "Comprar imóveis residenciais, comerciais",
        ):
            self.assertIn(fixed_copy, part)
        self.assertIn("function renderFinancialStudySelectedAdministrator()", app_js)
        self.assertIn("selectedMotor360Items()", app_js[app_js.index("function renderFinancialStudySelectedAdministrator()"):])
        self.assertIn('target.textContent = administrators.length', app_js)
        self.assertIn('renderFinancialStudySelectedAdministrator();', app_js)

    def test_part_four_quadro_resumo_consolidates_motor_groups_and_preserves_reference_content(self):
        html = (ROOT / "backend/static/index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "backend/static/js/app.js").read_text(encoding="utf-8")
        css = (ROOT / "backend/static/css/style.css").read_text(encoding="utf-8")
        start = html.index('data-study-part="4"')
        end = html.index("</section>", start)
        part = html[start:end]

        self.assertIn('data-study-part-name="Quadro Resumo"', part)
        self.assertIn("QUADRO RESUMO", part)
        self.assertIn("SIMULAÇÃO INVESTIMENTOS", part)
        self.assertIn("Valores hipotéticos do HTML de referência", part)
        for value in ("R$ 3.713.088,00", "R$ 1.927.733,55", "R$ 1.223.300,97", "R$ 6.726.706,47", "R$ 3.491.636,87", "R$ 2.216.157,17"):
            self.assertIn(value, part)
        self.assertIn('id="financialStudyPart4Content"', part)
        self.assertNotIn("<img", part)
        function_start = app_js.index("function renderFinancialStudySummary()")
        function_end = app_js.index("\nfunction clearRetiredFinancialStudyState()", function_start)
        summary_renderer = app_js[function_start:function_end]
        self.assertIn("selectedMotor360Items()", summary_renderer)
        self.assertIn("selectedCompositionScenarioMetrics(items, id)", summary_renderer)
        self.assertIn("financial-study-part4-top-grid", summary_renderer)
        self.assertIn("Somatória dos grupos selecionados", summary_renderer)
        self.assertIn("Parcelas<br>sem seguro", summary_renderer)
        self.assertIn("totalContractedCredit", summary_renderer)
        self.assertIn("chargeTotal", summary_renderer)
        self.assertIn("weightedRate", summary_renderer)
        self.assertIn("Lance Livre", summary_renderer)
        self.assertIn("Math.max(0, term - 1)", summary_renderer)
        for profile_id in ("conservative", "moderate", "aggressive", "super_aggressive"):
            self.assertIn(f'"{profile_id}"', summary_renderer)
        self.assertIn("lance_ideal_total", app_js)
        self.assertNotIn("Referência Motor 360", summary_renderer)
        self.assertNotIn("Recursos disponíveis atingem o perfil", summary_renderer)
        self.assertNotIn("recursos próprios`", summary_renderer)
        self.assertIn("Com lance embutido", summary_renderer)
        self.assertIn("Sem lance embutido", summary_renderer)
        self.assertIn("não é previsão", summary_renderer)
        self.assertIn('class="financial-study-part4-scenario-summary"', summary_renderer)
        self.assertIn("somatória dos grupos selecionados", summary_renderer)
        self.assertIn("return `<tr class=\"financial-study-part4-profile-row\"", summary_renderer)
        self.assertNotIn("detailRows", summary_renderer)
        self.assertNotIn("Ver taxas detalhadas por grupo", summary_renderer)
        self.assertNotIn("selectedScenarioIdsForGroup", summary_renderer)
        self.assertIn("renderFinancialStudySummary();", app_js)
        self.assertIn(".financial-study-part4-overview-table", css)
        self.assertIn(".financial-study-part4-embedded-total", css)
        self.assertIn(".financial-study-part4-category-row", css)
        self.assertIn(".financial-study-part4-table", css)

    def test_part_five_specialists_is_fixed_copy_without_images_or_motor_values(self):
        html = (ROOT / "backend/static/index.html").read_text(encoding="utf-8")
        css = (ROOT / "backend/static/css/style.css").read_text(encoding="utf-8")
        start = html.index('data-study-part="5"')
        end = html.index("</section>", start)
        part = html[start:end]

        self.assertIn('data-study-part-name="Especialistas da Jornada"', part)
        self.assertIn("ESPECIALISTAS EM TODA JORNADA", part)
        self.assertIn("Gestão da Contemplação:", part)
        self.assertIn("Consultoria de lances para estratégias assertivas, apoio operacional em oferta e acompanhamento resultado assembleia.", part)
        self.assertIn("Gestão da Utilização do Crédito:", part)
        self.assertIn("Trâmites com a administradora, vendedores, prefeitura, cartório de imóveis, certidões, contrato de compromisso de venda e compra, entre outros.", part)
        self.assertNotIn("<img", part)
        self.assertIn(".financial-study-part5-grid", css)

    def test_part_six_benefits_are_bound_to_itau_without_logo_or_cross_admin_leak(self):
        html = (ROOT / "backend/static/index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "backend/static/js/app.js").read_text(encoding="utf-8")
        css = (ROOT / "backend/static/css/style.css").read_text(encoding="utf-8")
        start = html.index('data-study-part="6"')
        end = html.index("</section>", start)
        part = html[start:end]

        self.assertIn('data-study-part-name="Principais Benefícios Itaú"', part)
        self.assertIn('id="financialStudyPart6AdministratorName"', part)
        self.assertIn('id="financialStudyPart6Content"', part)
        self.assertNotIn("<img", part)
        self.assertIn("renderFinancialStudyBenefits();", app_js)
        self.assertIn("FINANCIAL_STUDY_ADMINISTRATOR_BENEFITS", app_js)
        self.assertIn('keys.length === 1 && keys[0].includes("itau")', app_js)
        self.assertIn("Os benefícios de ${escapeHtml(administrators[0])} ainda não estão cadastrados.", app_js)
        for phrase in (
            "As contemplações ocorrem todos os meses: Sorteio e Lances Livres;",
            "É possível utilizar até 30% do crédito para pagar o lance ofertado;",
            "Seguro prestamista 0,06% sob o saldo devedor - opcional;",
            "Débito automático das prestações em contas Itaú.",
        ):
            self.assertIn(phrase, app_js)
        self.assertIn(".financial-study-part6-content", css)

    def test_part_seven_contracting_uses_selected_motor_scenarios_and_group_rates(self):
        html = (ROOT / "backend/static/index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "backend/static/js/app.js").read_text(encoding="utf-8")
        css = (ROOT / "backend/static/css/style.css").read_text(encoding="utf-8")
        start = html.index('data-study-part="7"')
        end = html.index("</section>", start)
        part = html[start:end]
        function_start = app_js.index("function renderFinancialStudyContracting()")
        function_end = app_js.index("\nfunction renderFinancialStudySummary()", function_start)
        renderer = app_js[function_start:function_end]

        self.assertIn('data-study-part-name="Contratação"', part)
        self.assertIn('id="financialStudyPart7Content"', part)
        self.assertIn("renderFinancialStudyContracting();", app_js)
        self.assertIn("selectedMotor360Items()", renderer)
        self.assertIn("selectedScenarioIdsForGroup(groupKey)", renderer)
        self.assertIn("selectedCompositionScenarioMetrics(items, id)", renderer)
        self.assertIn("entry.credit", renderer)
        self.assertIn("entry.installment", renderer)
        self.assertIn("entry.item.prazo_restante", renderer)
        self.assertIn("entry.item.taxa_adm ?? entry.item.taxa_total", renderer)
        self.assertIn("entry.item.taxa_ano", renderer)
        self.assertIn("Prazo e taxas no fechamento são médias aritméticas dos grupos daquele cenário", renderer)
        self.assertIn('average("term")', renderer)
        self.assertIn('average("adminRate")', renderer)
        self.assertIn('average("annualRate")', renderer)
        self.assertIn("return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null", renderer)
        self.assertIn('rows.filter((row) => row.scenarioId === scenarioId)', renderer)
        self.assertIn("sem seguro", renderer)
        self.assertIn(".financial-study-part7-table", css)

    def test_part_eight_contemplation_strategies_are_fixed_copy(self):
        html = (ROOT / "backend/static/index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "backend/static/js/app.js").read_text(encoding="utf-8")
        css = (ROOT / "backend/static/css/style.css").read_text(encoding="utf-8")
        start = html.index('data-study-part="8"')
        end = html.index("</section>", start)
        part = html[start:end]

        self.assertIn('data-study-part-name="Estratégias de contemplação"', part)
        self.assertIn("ESTRATÉGIAS DE CONTEMPLAÇÃO", part)
        self.assertIn("Estratégia 1) Investidor", part)
        self.assertIn("Sorteio + Lance Fixo 40%", part)
        self.assertIn("Estratégia 2) Conservadora", part)
        self.assertIn("Lance Livre Conservador", part)
        self.assertIn("1 das últimas 11 assembleias", part)
        self.assertIn("Estratégia 3) Moderada", part)
        self.assertIn("Lance Livre Moderado", part)
        self.assertIn("2 das últimas 11 assembleias", part)
        self.assertIn("não havendo garantia de contemplação", part)
        self.assertNotIn("<img", part)
        self.assertNotIn("${", part)
        self.assertNotIn("financialStudyPart8", app_js)
        self.assertIn(".financial-study-part8-content", css)

    def test_part_nine_contemplation_history_uses_selected_motor_monthly_data(self):
        html = (ROOT / "backend/static/index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "backend/static/js/app.js").read_text(encoding="utf-8")
        css = (ROOT / "backend/static/css/style.css").read_text(encoding="utf-8")
        start = html.index('data-study-part="9"')
        end = html.index("</section>", start)
        part = html[start:end]
        function_start = app_js.index("function renderFinancialStudyContemplationHistory()")
        function_end = app_js.index("\nfunction renderFinancialStudySummary()", function_start)
        renderer = app_js[function_start:function_end]

        self.assertIn('data-study-part-name="Histórico de Contemplações"', part)
        self.assertIn('id="financialStudyPart9Content"', part)
        self.assertIn("renderFinancialStudyContemplationHistory();", app_js)
        self.assertIn("selectedMotor360Items()", renderer)
        self.assertIn("item.historico_12_meses", renderer)
        self.assertIn("entry.menor_lance", renderer)
        self.assertIn("entry.qtd_contemplacoes", renderer)
        self.assertIn('.slice(0, 12)', renderer)
        self.assertIn('formatHistoryPercent(entry?.menor_lance)', renderer)
        self.assertIn("O total soma apenas quantidades numéricas disponíveis.", renderer)
        self.assertNotIn("<img", part)
        self.assertIn(".financial-study-part9-table", css)

    def test_part_ten_projection_uses_motor_profiles_and_lottery_full_credit(self):
        html = (ROOT / "backend/static/index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "backend/static/js/app.js").read_text(encoding="utf-8")
        css = (ROOT / "backend/static/css/style.css").read_text(encoding="utf-8")
        start = html.index('data-study-part="10"')
        end = html.index("</section>", start)
        part = html[start:end]
        function_start = app_js.index("function renderFinancialStudyProjection()")
        function_end = app_js.index("\nfunction renderFinancialStudySummary()", function_start)
        renderer = app_js[function_start:function_end]

        self.assertIn('data-study-part-name="Projeção de Contemplação"', part)
        self.assertIn('id="financialStudyPart10Content"', part)
        self.assertIn("renderFinancialStudyProjection();", app_js)
        self.assertIn("selectedCompositionScenarioMetrics(items, id)", renderer)
        for profile_id in ("conservative", "moderate", "aggressive", "super_aggressive"):
            self.assertIn(f'id: "{profile_id}"', app_js)
        self.assertIn('entryFor(item, "without_embedded")', renderer)
        self.assertIn("credit: entry.contractedCredit", renderer)
        self.assertIn("percentage: 0", renderer)
        self.assertIn("clientResources: 0", renderer)
        self.assertIn("profile?.lance_ideal_total", renderer)
        self.assertIn("Number(profile.ideal || 0)", renderer)
        self.assertIn("entry.embedded", renderer)
        self.assertIn("entry.installment", renderer)
        self.assertIn("Cenários sem e com embutido são alternativas", renderer)
        self.assertIn("não uma projeção de parcela após contemplação por perfil", renderer)
        self.assertNotIn("<img", part)
        self.assertIn(".financial-study-part10-table", css)

    def test_part_eleven_selects_first_future_adhesion_before_installment_due(self):
        html = (ROOT / "backend/static/index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "backend/static/js/app.js").read_text(encoding="utf-8")
        css = (ROOT / "backend/static/css/style.css").read_text(encoding="utf-8")
        start = html.index('data-study-part="11"')
        end = html.index("</section>", start)
        part = html[start:end]
        function_start = app_js.index("function financialStudyAssemblyEvent(")
        function_end = app_js.index("\nfunction renderFinancialStudySummary()", function_start)
        renderer = app_js[function_start:function_end]

        self.assertIn('data-study-part-name="Data limite de adesão"', part)
        self.assertIn('id="financialStudyPart11Content"', part)
        self.assertIn("renderFinancialStudyAdhesionDates();", app_js)
        self.assertIn('apiGet("/mapa-assembleia"', app_js)
        self.assertIn("data.group_due_dates", renderer)
        self.assertIn('"adesao"', renderer)
        self.assertIn('"vencimento_boleto_adesao"', renderer)
        self.assertIn('"vencimento_parcela"', renderer)
        self.assertIn('"assembleia"', renderer)
        self.assertIn('"pagamento_lance"', renderer)
        self.assertIn("cycle.adhesion >= reference", renderer)
        self.assertIn("cycle.adhesion < cycle.firstInstallment", renderer)
        self.assertIn("assemblyFormatDate(date)", renderer)
        self.assertIn("new Date()", renderer)
        self.assertIn(".financial-study-part11-table", css)

    def test_part_twelve_important_considerations_is_fixed_text_without_images_or_variables(self):
        html = (ROOT / "backend/static/index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "backend/static/js/app.js").read_text(encoding="utf-8")
        css = (ROOT / "backend/static/css/style.css").read_text(encoding="utf-8")
        start = html.index('data-study-part="12"')
        end = html.index("</section>", start)
        part = html[start:end]

        self.assertIn('data-study-part-name="Considerações importantes"', part)
        self.assertIn("CONSIDERAÇÕES IMPORTANTES", part)
        self.assertIn("informações fornecidas pelo cliente", part)
        self.assertIn("caráter exclusivamente informativo e ilustrativo", part)
        self.assertIn("A CrediClass não garante rentabilidade", part)
        self.assertIn("responsabilidade exclusiva do cliente", part)
        self.assertNotIn("<img", part)
        self.assertNotIn("${", part)
        self.assertNotIn("financialStudyPart12", app_js)
        self.assertIn(".financial-study-part12-content", css)

    def test_shared_study_has_mobile_cards_and_unclipped_print_tables(self):
        app_js = (ROOT / "backend/static/js/app.js").read_text(encoding="utf-8")
        css = (ROOT / "backend/static/css/style.css").read_text(encoding="utf-8")

        self.assertIn('class="financial-study-part9-mobile"', app_js)
        self.assertIn('class="financial-study-part10-card"', app_js)
        self.assertIn('data-label="Crédito"', app_js)
        self.assertIn(".financial-study-part4-table tbody tr {", css)
        self.assertIn(".financial-study-part9-group-card", css)
        self.assertIn(".financial-study-part10-card dl", css)
        self.assertIn("@page { size: A4 landscape; margin: 10mm; }", css)
        self.assertIn("overflow: visible !important;", css)
        self.assertIn(".financial-study-part9-mobile,\n  .financial-study-part10-mobile { display: none !important; }", css)

    def test_shared_study_mobile_enhancement_preserves_all_content(self):
        html = (ROOT / "backend/static/index.html").read_text(encoding="utf-8")
        helper = (ROOT / "backend/static/js/shared-study.js").read_text(encoding="utf-8")
        css = (ROOT / "backend/static/css/style.css").read_text(encoding="utf-8")

        self.assertIn("financial-study-part2-mobile", html)
        self.assertIn("rows.map((row, index)", helper)
        self.assertIn('headings[4]', helper)
        self.assertIn("sharedStudyNavigation", helper)
        self.assertIn("financial-study-part9-mobile-total > div { display: grid", css)
        self.assertIn("financial-study-part2-table-wrap.has-mobile-cards", css)

    def test_public_study_navigation_uses_section_buttons_without_repeated_summary(self):
        helper = (ROOT / "backend/static/js/shared-study.js").read_text(encoding="utf-8")
        css = (ROOT / "backend/static/css/style.css").read_text(encoding="utf-8")

        self.assertIn('class="shared-study-navigation-button" href=', helper)
        self.assertIn('setAttribute("aria-current", "location")', helper)
        self.assertIn('new IntersectionObserver(', helper)
        self.assertIn(".shared-study-navigation-links { display: flex; min-width: 0; flex: 1 1 auto; flex-wrap: wrap;", css)
        self.assertIn(".shared-study-navigation-button { min-height: 44px;", css)
        main = (ROOT / "backend/main.py").read_text(encoding="utf-8")
        self.assertNotIn("sharedStudyQuickSummary", helper)
        self.assertNotIn("shared-study-summary", main)
        self.assertIn("@media screen and (max-width: 420px)", css)

    def test_study_history_layout_print_and_close_controls(self):
        app_js = (ROOT / "backend/static/js/app.js").read_text(encoding="utf-8")
        html = (ROOT / "backend/static/index.html").read_text(encoding="utf-8")
        css = (ROOT / "backend/static/css/style.css").read_text(encoding="utf-8")

        self.assertIn('"Estudo Completo"', app_js)
        self.assertIn('state.hidden = items.length > 0', app_js)
        self.assertIn('const printWindow = frame?.contentWindow', app_js)
        self.assertIn('printWindow.print();', app_js)
        self.assertIn('document.addEventListener("click", (event) => {', app_js)
        self.assertIn('id="closeFinancialStudyHistoryBtn"', html)
        self.assertIn('sandbox="allow-same-origin allow-modals"', html)
        self.assertIn('id="printFinancialStudyHistoryBtn" class="btn btn-outline-secondary" type="button">Imprimir</button>', html)
        self.assertIn(".financial-study-history-table .study-col-id", css)
        self.assertIn(".financial-study-history-table tbody tr", css)
        self.assertIn("grid-template-columns: minmax(0, 1fr) auto", css)
        self.assertIn(".financial-study-share-link-row .btn { min-width: 88px; flex: 0 0 auto; white-space: nowrap; }", css)

    def test_legacy_study_backend_modules_are_absent(self):
        backend = ROOT / "backend"
        for module in ("estudos.py", "templates_estudos.py", "financial_study_engine.py", "pdf_bridge.py"):
            self.assertFalse((backend / module).exists(), module)

    def test_only_retired_template_styles_are_absent(self):
        css = (ROOT / "backend/static/css/style.css").read_text(encoding="utf-8")
        self.assertIn(".financial-study-part--introduction", css)
        self.assertIn(".financial-study-part--best-consortia", css)
        for legacy_selector in (".study-v4-", ".study-template-preview-"):
            self.assertNotIn(legacy_selector, css)

    def test_production_smoke_checks_fixed_part_one(self):
        smoke = (ROOT / "scripts/production-smoke-test.mjs").read_text(encoding="utf-8")
        self.assertIn("financial study fixed introduction is served", smoke)
        self.assertIn("financial-study-part--introduction", smoke)
        self.assertIn("clearRetiredFinancialStudyState", smoke)

    def test_production_smoke_checks_calculated_part_two(self):
        smoke = (ROOT / "scripts/production-smoke-test.mjs").read_text(encoding="utf-8")
        self.assertIn("SIMULAÇÃO DE INVESTIMENTO", smoke)
        self.assertIn("financialStudyPart2AnnualRate", smoke)
        self.assertIn("renderFinancialStudyInvestment", smoke)

    def test_production_smoke_checks_part_three_and_administrator_binding(self):
        smoke = (ROOT / "scripts/production-smoke-test.mjs").read_text(encoding="utf-8")
        self.assertIn("SIMULAÇÃO DOS MELHORES CONSÓRCIOS", smoke)
        self.assertIn("renderFinancialStudySelectedAdministrator", smoke)

    def test_production_smoke_checks_part_six_administrator_benefits(self):
        smoke = (ROOT / "scripts/production-smoke-test.mjs").read_text(encoding="utf-8")
        self.assertIn("financial study administrator-specific benefits part is served", smoke)
        self.assertIn("PRINCIPAIS BENEFÍCIOS", smoke)
        self.assertIn("renderFinancialStudyBenefits", smoke)


if __name__ == "__main__":
    unittest.main()
