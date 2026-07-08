import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class StaticEmailTest(unittest.TestCase):
    def test_estudos_email_usa_cliente_de_email(self):
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")

        self.assertIn("function emailCurrentStudy()", app_js)
        self.assertIn("function emailHistoryStudy(studyId)", app_js)
        self.assertIn("mailto:?subject=", app_js)
        self.assertNotIn("Envio por e-mail depende de SMTP configurado.", app_js)

    def test_index_referencia_app_js_atualizado(self):
        index_html = (ROOT / "backend" / "static" / "index.html").read_text(encoding="utf-8")

        self.assertIn("/static/css/style.css?v=20260708-07", index_html)
        self.assertIn("fonts.googleapis.com/css2", index_html)
        self.assertIn("family=DM+Sans", index_html)
        self.assertIn("family=Raleway", index_html)
        self.assertIn("/static/js/app.js?v=20260708-04", index_html)

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
            '<th title="Ultima atualizacao da triade Maior Lance, Menor Lance e Quantidade de Contemplacao">Atualizado</th>',
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

    def test_calculadora_administradoras_fica_na_selecao_de_grupos(self):
        index_html = (ROOT / "backend" / "static" / "index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")
        style_css = (ROOT / "backend" / "static" / "css" / "style.css").read_text(encoding="utf-8")

        self.assertNotIn('data-screen="administradoras"', index_html)
        self.assertNotIn('id="screen-administradoras"', index_html)
        self.assertIn("Motor Inteligente de Selecao", index_html)
        self.assertIn("selectionPipeline", index_html)
        self.assertIn("Motor de Elegibilidade das Administradoras", index_html)
        self.assertIn("Calculo dos Grupos", index_html)
        self.assertIn("Fase 2 - Selecao Melhores Grupos por Prazo Remanescente e Compatibilidade Menor Lance", index_html)
        self.assertIn("Adicionar cartas de credito", index_html)
        self.assertIn("Calculo: credito contratado com embutido", index_html)
        self.assertIn("Compatibilidade", index_html)
        self.assertIn("Ranking Inteligente", index_html)
        self.assertIn("Top 10 Grupos", index_html)
        self.assertNotIn('class="selection-flow-grid"', index_html)
        self.assertNotIn('class="phase-two-help"', index_html)
        self.assertIn('id="viabilityPhase2Idle"', index_html)
        self.assertIn('id="viabilityPhase2Summary"', index_html)
        self.assertIn('class="content-card phase-two-card"', index_html)
        self.assertIn('data-admin-plan-kind="Imovel"', index_html)
        self.assertIn('data-admin-plan-kind="Automovel"', index_html)
        self.assertIn('id="administratorPlansCols"', index_html)
        self.assertIn('id="administratorPlansBody"', index_html)
        self.assertIn('id="administratorPlanAudit"', index_html)
        self.assertIn('id="administratorEligibilityBody"', index_html)
        self.assertIn('id="administratorEliminatedDetails"', index_html)
        self.assertIn('id="eligibleAdministratorsList"', index_html)
        self.assertIn('id="selectionFunnelSummary"', index_html)
        self.assertIn("function refreshAdministratorEligibility", app_js)
        self.assertIn('apiGet("/configuracoes")', app_js)
        self.assertIn('apiPost("/viabilidade/administradoras", payload)', app_js)
        self.assertIn("function administratorPlanDisplayRulesForKind", app_js)
        self.assertIn("function setPipelineStatus", app_js)
        self.assertIn("function renderSelectionFunnelSummary", app_js)
        self.assertIn("function runPhase2SelectionAutomatically", app_js)
        self.assertIn("function renderPhase2Summary", app_js)
        self.assertIn("function phase2SelectionSignature", app_js)
        self.assertIn("function renderAdministratorPlans()", app_js)
        self.assertIn("function saveAdministratorPlans()", app_js)
        self.assertIn("function renderAdministratorPlanColgroup(rules)", app_js)
        self.assertIn("function renderAdministratorPlanAudit(rules)", app_js)
        self.assertIn("Demonstrativo logico do calculo", app_js)
        self.assertNotIn("admin-plan-col-group", app_js)
        self.assertNotIn("admin-plan-group-cell", app_js)
        self.assertIn('const labelColumnWidth = "176px"', app_js)
        self.assertIn('const scenarioColumnWidth = "124px"', app_js)
        self.assertIn("overflow-x: auto", style_css)
        self.assertIn("width: max-content", style_css)
        self.assertIn("table-layout: auto", style_css)
        self.assertIn("font-size: 0.8rem", style_css)
        self.assertIn(".phase-two-summary", style_css)
        self.assertIn("white-space: normal", style_css)
        self.assertIn("overflow-wrap: normal", style_css)
        self.assertIn('admin-plan-cell[data-admin-plan-field="percentual_lance_embutido"]', style_css)
        self.assertIn('admin-plan-cell[data-admin-plan-field="lance_embutido_valor"]', style_css)
        self.assertIn("mapState.administradoras", app_js)
        for campo in [
            "ETAPA 4 - FASE 1 - CALCULADORA DE GRUPOS",
            "CENARIOS CALCULO",
            "Sem Emb.",
            "Com Emb.",
            "Tipo de bem",
            "Prazo remanescente",
            "Lance Embutido",
            "Calculo do Lance Embutido",
            "Calculo do Percentual de Lance",
            "Permite amortizar o lance na parcela?",
            "Permite participar do lance fixo e livre?",
            "Possui Parcela Reduzida?",
            "Possui Lance Fixo?",
            "Taxa Administracao (total)",
            "Taxa Administracao (ao ano)",
            "Possui Taxa de Adesao?",
            "Fundo de reserva (total)",
            "Fundo de reserva (ao ano)",
            "Seg. obrigatorio?",
            "Idade maxima seguro",
            "Aliquota seguro mensal sobre saldo devedor",
            "Calculo A - Credito a ser contratado:",
            "Saldo devedor / categoria",
            "Calculo B - Lance Maximo Cliente:",
            "Lance Total:",
            "Recurso Proprio:",
            "FGTS:",
            "Embutido:",
            "Parcela Inicial - Desejada",
            "Parcela Inicial - Limite Renda",
            "Parcela Apos Lance - Desejada",
            "Parcela Apos Lance - Limite Renda",
        ]:
            self.assertIn(campo, app_js)
        self.assertIn("const administratorPlanComputedFields", app_js)
        self.assertIn('"idade_maxima_ok"', app_js)
        self.assertIn("const administratorPlanScenarioRows", app_js)
        self.assertIn("function administratorPlanAgeValidation(rule)", app_js)
        self.assertIn("function calculateAgeFromDateText(dateText)", app_js)
        self.assertIn('if (age < 18) return "Nao - menor de 18";', app_js)
        self.assertIn('return "Sim - validar termino no grupo";', app_js)
        self.assertIn('["idade_maxima", "percentual_lance_embutido", "taxa_adm", "fundo_reserva"].includes', app_js)
        self.assertIn('.replace("R$", "").replace("%", "")', app_js)
        self.assertIn("function administratorPlanCreditoContratado(rule, useEmbedded = true)", app_js)
        self.assertIn('administratorPlanPercent(rule, "percentual_lance_embutido")', app_js)
        self.assertIn("return creditoDesejado / (1 - percentualLanceEmbutido);", app_js)
        self.assertIn("function administratorPlanLanceEmbutidoValor(rule, useEmbedded = true)", app_js)
        self.assertIn("function currentClientProfileFgtsTotal()", app_js)
        self.assertIn("function currentClientProfileLanceMaximoDisponivel(rule = {})", app_js)
        self.assertIn("function administratorPlanLanceTotalConsiderado(rule, useEmbedded = true)", app_js)
        self.assertIn("function administratorPlanLanceMaximo(rule, useEmbedded = true)", app_js)
        self.assertIn("return lanceTotal === null ? null : lanceTotal / creditoContratado", app_js)
        self.assertIn("function administratorPlanTaxaAdmValor(rule, useEmbedded = true)", app_js)
        self.assertIn("function administratorPlanFundoReservaValor(rule, useEmbedded = true)", app_js)
        self.assertIn("function administratorPlanSaldoDevedor(rule, useEmbedded = true)", app_js)
        self.assertIn("function administratorPlanPrazoMinimo(rule, useEmbedded = true, options = {})", app_js)
        self.assertIn("function administratorPlanScenarioCellValue(rule, row, useEmbedded)", app_js)
        self.assertIn("function currentClientObjectiveFlow()", app_js)
        self.assertIn("function visibleAdministratorPlanScenarioRows()", app_js)
        self.assertIn('row.key.includes("_investidor_")', app_js)
        self.assertIn('row.key.includes("_contemplacao_")', app_js)
        self.assertIn('if (id === "clientProfileObjetivo") renderAdministratorPlans();', app_js)
        self.assertIn("- lanceTotal", app_js)
        self.assertIn("administratorPlanComputedFields.includes", app_js)
        for administradora in ["AUTO-CAIXA", "AUTO-CAOA", "AUTO-ITAU", "CAIXA", "CANOPUS", "CAOA", "ITAU", "PORTO", "RODOBENS"]:
            self.assertIn(administradora, app_js)
        self.assertNotIn("administratorTotalDisponivel", index_html)
        self.assertNotIn("administratorUsarFgts", index_html)
        self.assertNotIn('id="exportAdministratorsCsvBtn"', index_html)
        self.assertNotIn('id="advanceToGroupsBtn"', index_html)
        self.assertIn('if (screenName === "viabilidade") loadConfiguracoes();', app_js)
        self.assertIn('apiPost("/viabilidade/administradoras", payload)', app_js)
        self.assertNotIn("function exportAdministratorsCsv()", app_js)
        self.assertNotIn("function syncAdministratorInterviewToGroups()", app_js)

    def test_viabilidade_cenarios_nao_repete_formulario_do_cliente(self):
        index_html = (ROOT / "backend" / "static" / "index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")

        self.assertIn("Fase 2 - Selecao Melhores Grupos por Prazo Remanescente e Compatibilidade Menor Lance", index_html)
        self.assertIn("Calculo dos Grupos", index_html)
        self.assertIn("Adicionar cartas de credito", index_html)
        self.assertNotIn('id="analyzeViabilityBtn"', index_html)
        self.assertNotIn('data-screen-jump="perfil"', index_html)
        self.assertNotIn('id="addAdministratorPlanBtn"', index_html)
        self.assertNotIn('id="saveAdministratorPlansBtn"', index_html)
        self.assertIn('primaryAction.classList.toggle("d-none", screenName === "viabilidade")', app_js)
        self.assertIn("Aguardando selecao dos melhores grupos", index_html)
        self.assertIn("Top 10 exibido", app_js)
        self.assertIn("ordenado por score de compatibilidade", app_js)
        self.assertIn("await analyzeViability({ silent: true })", app_js)
        self.assertIn('state !== "idle"', app_js)
        self.assertIn('state !== "ready"', app_js)
        self.assertIn("fluxo ${fluxo}", app_js)
        self.assertIn("Filtro 1 manteve", app_js)
        self.assertIn("const profile = collectClientProfile();", app_js)
        self.assertIn("const parcelaLimite = profile.parcela_limite || profile.parcela_ideal;", app_js)
        self.assertIn("parcela_desejada: parcelaLimite", app_js)
        self.assertIn("Credito contratado", index_html)
        self.assertNotIn("Lance referencia perfil", index_html)
        self.assertNotIn("Lance maximo cliente", index_html)
        self.assertNotIn("Motivo / Alerta", index_html)
        self.assertNotIn("<th>Compativel</th>", index_html)
        self.assertIn("function renderViabilityEmpty(result)", app_js)
        self.assertIn("function openViabilityAudit(groupId, scenarioId", app_js)
        self.assertIn("data-viability-action=\"auditar\"", app_js)
        self.assertIn('button.dataset.viabilityAction === "estrategias"', app_js)
        self.assertIn("openFinancialStudy(button.dataset.groupId, item)", app_js)
        self.assertIn("<th>Status</th>", index_html)
        self.assertIn("regras_administradoras_pendentes_analise_humana", app_js)
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
        self.assertIn("Fluxo do Estudo", index_html)
        self.assertIn("Administrativo", index_html)
        self.assertIn('id="screen-perfil"', index_html)
        self.assertIn("Perfil do Cliente", index_html)
        self.assertIn("clientProfileCredito", index_html)
        self.assertIn("clientProfileTotalDisponivel", index_html)
        self.assertIn("clientProfileConceito", index_html)
        self.assertIn("Analise Preliminar - Titular(es)", index_html)
        self.assertNotIn("3 - Analise Preliminar - Titular(es)", index_html)
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
        self.assertIn("function saveClientProfile", app_js)
        self.assertIn("function applyClientProfileToFlow", app_js)
        self.assertNotIn("function renderClientProfileSummary", app_js)
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
        self.assertIn("administratorPlanRuleHelp", app_js)
        self.assertIn("function renderAdministratorPlanRowLabel(row)", app_js)
        self.assertIn("admin-plan-rule-marker", app_js)
        self.assertIn("administradoras_regras", app_js)
        self.assertIn(".admin-plan-rule-marker", style_css)
        self.assertIn("#dc2626", style_css)

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
        for etapa in ["Perfil do Cliente", "Estrategia", "Fase 1 - Calculadora de Grupos", "Fase 2 - Selecao Melhores Grupos por Prazo Remanescente e Compatibilidade Menor Lance", "Estudo Financeiro"]:
            self.assertIn(etapa, app_js)
        for exemplo in [
            "credito_liquido_desejado",
            "percentual_lance_embutido",
            "parcela_total_cenario",
            "Super Agressivo",
            "cartas candidatas",
            "FGTS so entra quando permitido",
            "formulas financeiras ficam centralizadas no backend",
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

    def test_exportacao_csv_disponivel_para_grupos_e_estudos(self):
        index_html = (ROOT / "backend" / "static" / "index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")

        self.assertNotIn('id="exportGroupsCsvBtn"', index_html)
        self.assertIn('id="exportStudiesCsvBtn"', index_html)
        self.assertIn("function downloadCsv(filename, rows)", app_js)
        self.assertIn("function downloadBlob(filename, blob)", app_js)
        self.assertIn("function exportGroupsCsv()", app_js)
        self.assertIn("function exportStudiesCsv()", app_js)
        self.assertIn("text/csv;charset=utf-8", app_js)
        self.assertIn("/api/grupos/exportar-planilha", app_js)
        self.assertIn("crediclass-planilha-oficial-", app_js)
        self.assertIn("crediclass-estudos-", app_js)

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

    def test_acao_principal_salva_estudo_financeiro(self):
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")

        self.assertIn('document.getElementById("screen-estudo").classList.contains("active")', app_js)
        self.assertIn("saveCurrentStudy().catch(() => setStudyState(\"error\"))", app_js)
        self.assertNotIn("Funcionalidade sera implementada na etapa correspondente.", app_js)

    def test_estudo_financeiro_preserva_data_nascimento_conjuge(self):
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")

        self.assertIn("data_nascimento_conjuge: profile.data_nascimento_conjuge", app_js)
        self.assertIn('data_nascimento_conjuge: currentStudy.payload.data_nascimento_conjuge', app_js)
        self.assertIn('["Data nascimento conjuge", payload.data_nascimento_conjuge || "-"]', app_js)
        self.assertIn('["Data nascimento conjuge", cliente.data_nascimento_conjuge || "-"]', app_js)

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
            self.assertIn(label, index_html)
        self.assertIn("Parcela maxima desejada", index_html)
        self.assertIn("Lance maximo com recurso proprio", index_html)
        self.assertIn("function clientProfileConcept(months)", app_js)
        self.assertIn("CLIENT_OBJECTIVE_RULES", app_js)
        self.assertIn('id="clientProfileTipoBem"', index_html)
        self.assertIn("tipo_bem: profile.tipo_bem", app_js)
        self.assertNotIn('tipo_bem: "Imovel"', app_js)
        self.assertIn("payload.lance_proprio < 0", app_js)

    def test_perfil_cliente_suporta_titulares_pf_pj(self):
        index_html = (ROOT / "backend" / "static" / "index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")

        for label in [
            "Pessoa fisica individual",
            "Pessoa fisica com conjuge",
            "Dois titulares / grupo familiar",
            "Pessoa juridica",
        ]:
            self.assertIn(label, index_html)
        self.assertIn("CLIENT_PJ_SOCIOS_LIMIT = 5", app_js)
        self.assertIn('cnpj: ""', app_js)
        self.assertIn('profileHolderInput("pessoa_juridica.empresa.cnpj", empresa.cnpj, "CNPJ")', app_js)
        self.assertIn("renderClientProfileTitulares", app_js)
        self.assertIn("summarizeClientTitulares", app_js)
        self.assertIn("titulares: profile.titulares", app_js)
        self.assertIn("titulares: currentStudy.payload.titulares", app_js)

    def test_estudo_financeiro_exibe_metricas_historico_12_meses(self):
        index_html = (ROOT / "backend" / "static" / "index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")

        for field_id in [
            "studyAvgMaiorLance",
            "studyAvgMenorLance",
            "studyAvgContemplacoes",
            "studyTotalContemplacoes",
        ]:
            self.assertIn(f'id="{field_id}"', index_html)
            self.assertIn(field_id, app_js)

        self.assertIn("function averageNumber(values)", app_js)
        self.assertIn("const entries = Object.entries(group.historico || {}).slice(-12)", app_js)

    def test_estudo_financeiro_exibe_resumo_financeiro_completo(self):
        index_html = (ROOT / "backend" / "static" / "index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")

        for field_id in [
            "studyRecursoProprio",
            "studyPercentualLanceTotal",
            "studyParcelaApos",
            "studyPrazoApos",
            "studyCustoTotal",
            "studySeguroGarantia",
            "studyProximaAssembleia",
            "studyChanceContemplacao",
            "studyRankingPosition",
        ]:
            self.assertIn(f'id="{field_id}"', index_html)
            self.assertIn(field_id, app_js)

        self.assertIn("function renderStudySummary(financial, group, viabilityItem)", app_js)
        self.assertIn("percentualLanceTotal", app_js)
        self.assertIn("renderStudySummary(financial, group, viabilityItem)", app_js)

    def test_estudo_financeiro_usa_layout_v4_da_referencia(self):
        index_html = (ROOT / "backend" / "static" / "index.html").read_text(encoding="utf-8")
        style_css = (ROOT / "backend" / "static" / "css" / "style.css").read_text(encoding="utf-8")
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")

        for label in [
            "1. Dados do Cliente",
            "2. Cenario Financeiro",
            "3. Grupo Selecionado",
            "4. Estrategia Recomendada",
            "5. Simulacao Financeira da Estrategia Recomendada",
            "6. Historico do Grupo",
            "7. Datas Operacionais",
            "8. Motivos da Recomendacao",
            "9. Campos Pendentes",
            "Status do Preenchimento",
            "Versoes do Estudo",
        ]:
            self.assertIn(label, index_html)
        self.assertIn(".study-v4-shell", style_css)
        self.assertIn('id="studyScenarioGrid"', index_html)
        self.assertIn('id="studyOperationalDates"', index_html)
        self.assertIn('document.getElementById("studyDisplayId").textContent', app_js)

    def test_estudo_financeiro_campos_do_template_sao_editaveis(self):
        index_html = (ROOT / "backend" / "static" / "index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")
        style_css = (ROOT / "backend" / "static" / "css" / "style.css").read_text(encoding="utf-8")

        for field_id in [
            "studyFieldObservacoes",
            "studyFieldComentario",
            "studyFieldBeneficios",
            "studyFieldCondicoes",
            "studyPendingFields",
            "studyCompletionPercent",
            "studyTemplateTechnicalGrid",
        ]:
            self.assertIn(f'id="{field_id}"', index_html)
        self.assertIn("const studyOperatorFields", app_js)
        self.assertIn("function collectStudyOperatorFields()", app_js)
        self.assertIn("template_campos: collectStudyOperatorFields()", app_js)
        self.assertIn("function activateStudyTemplateTab(tabName)", app_js)
        self.assertIn(".study-template-panel.active", style_css)

    def test_estudo_financeiro_exibe_abas_de_estrategias(self):
        index_html = (ROOT / "backend" / "static" / "index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")

        self.assertIn('id="studyStrategyTabs"', index_html)
        self.assertIn("let currentStudyStrategies", app_js)
        self.assertIn("let currentStudyStrategyTab", app_js)
        self.assertIn("function renderStudyStrategyTabs()", app_js)
        self.assertIn("function renderStudyStrategyTable()", app_js)
        for label in ["Investidor", "Super Conservador", "Conservador", "Moderado", "Agressivo"]:
            self.assertIn(label, app_js)
        self.assertIn('data-study-strategy', app_js)

    def test_estudo_financeiro_exibe_recomendacoes_automaticas_completas(self):
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")

        self.assertIn("function renderStudyRecommendations(viabilityItem, financial, group)", app_js)
        self.assertIn("totalContemplacoes", app_js)
        self.assertIn("Grupo com bom historico", app_js)
        self.assertIn("Estrategia recomendada", app_js)
        self.assertIn("Prazo operacional do perfil", app_js)
        self.assertIn("Necessidade de acompanhamento semanal", app_js)
        self.assertIn("A analise nao garante contemplacao", app_js)

    def test_tema_configurado_aplica_aparencia(self):
        index_html = (ROOT / "backend" / "static" / "index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")
        style_css = (ROOT / "backend" / "static" / "css" / "style.css").read_text(encoding="utf-8")

        self.assertIn("/static/css/style.css?v=20260708-07", index_html)
        self.assertIn('id="configTema"', index_html)
        self.assertIn("function applyTheme(theme)", app_js)
        self.assertIn("document.body.dataset.theme", app_js)
        self.assertIn('document.getElementById("configTema").addEventListener("change"', app_js)
        self.assertIn('body[data-theme="escuro"]', style_css)

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

    def test_estudo_financeiro_exibe_logo_da_administradora(self):
        index_html = (ROOT / "backend" / "static" / "index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")
        style_css = (ROOT / "backend" / "static" / "css" / "style.css").read_text(encoding="utf-8")

        self.assertIn('id="studyAdminLogo"', index_html)
        self.assertIn('id="studyAdminName"', index_html)
        self.assertIn("function initialsFromName(value)", app_js)
        self.assertIn('document.getElementById("studyAdminLogo").textContent', app_js)
        self.assertIn(".admin-logo", style_css)

    def test_preferencias_configuracoes_expoem_campos_obrigatorios(self):
        index_html = (ROOT / "backend" / "static" / "index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")

        for field_id in [
            "configCasasValores",
            "configCasasPercentuais",
            "configMeiaParcela",
            "configLanceEmbutido",
            "configHistorico36",
        ]:
            self.assertIn(f'id="{field_id}"', index_html)
            self.assertIn(field_id, app_js)

        self.assertIn("function setSelectBool(id, value)", app_js)
        self.assertIn("function getSelectBool(id)", app_js)
        self.assertIn("casas_decimais_valores", app_js)
        self.assertIn("ativar_lance_embutido", app_js)

    def test_notificacoes_configuracoes_disponiveis(self):
        index_html = (ROOT / "backend" / "static" / "index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")

        self.assertIn("configNotificacoes", index_html)
        for field_id in ["notifySync", "notifyStudySaved", "notifyHistoryUpdated", "notifyIntegrationFailure"]:
            self.assertIn(f'id="{field_id}"', index_html)
            self.assertIn(field_id, app_js)

        self.assertIn("notificacoes", app_js)
        self.assertIn("alertar_sincronizacao", app_js)
        self.assertIn("alertar_falha_integracao", app_js)

    def test_notificacoes_controlam_alertas_operacionais(self):
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")

        self.assertIn("function isNotificationEnabled(key)", app_js)
        self.assertIn("function notifyWhen(key, message, type = \"success\")", app_js)
        self.assertIn('notifyWhen("alertar_sincronizacao"', app_js)
        self.assertIn('notifyWhen("alertar_estudo_salvo"', app_js)
        self.assertIn('notifyWhen("alertar_historico_atualizado"', app_js)
        self.assertIn('notifyWhen("alertar_falha_integracao"', app_js)

    def test_integracoes_configuracoes_podem_ser_alteradas(self):
        index_html = (ROOT / "backend" / "static" / "index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")

        self.assertIn('id="configureIntegrationsBtn"', index_html)
        self.assertIn('id="configIntegrationsForm"', index_html)
        for field_id in ["integrationGoogleSheetsToggle", "integrationPiperunToggle", "integrationEmailToggle", "integrationBackupToggle"]:
            self.assertIn(f'id="{field_id}"', index_html)
            self.assertIn(field_id, app_js)

        self.assertIn("integracoes", app_js)
        self.assertIn("google_sheets: getSelectBool", app_js)
        self.assertIn("piperun_crm: getSelectBool", app_js)

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
