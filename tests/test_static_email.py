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

        self.assertIn("/static/js/app.js?v=20260608-27", index_html)

    def test_dependencias_visuais_sao_servidas_localmente(self):
        index_html = (ROOT / "backend" / "static" / "index.html").read_text(encoding="utf-8")
        style_css = (ROOT / "backend" / "static" / "css" / "style.css").read_text(encoding="utf-8")

        self.assertIn("/static/vendor/bootstrap.min.css?v=5.3.3", index_html)
        self.assertIn("/static/vendor/bootstrap.bundle.min.js?v=5.3.3", index_html)
        self.assertIn("/static/vendor/chart.umd.min.js?v=4.4.3", index_html)
        self.assertIn("/static/favicon.svg?v=1", index_html)
        self.assertNotIn("cdn.jsdelivr.net", index_html)
        self.assertIn(".d-none", style_css)

    def test_tela_administradoras_existe_no_menu(self):
        index_html = (ROOT / "backend" / "static" / "index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")

        self.assertIn('data-screen="administradoras"', index_html)
        self.assertIn('id="screen-administradoras"', index_html)
        self.assertIn("Administradoras", index_html)
        self.assertIn("2 - Planos Administradoras", index_html)
        self.assertIn('data-admin-plan-kind="Imovel"', index_html)
        self.assertIn('data-admin-plan-kind="Automovel"', index_html)
        self.assertIn('id="administratorPlansBody"', index_html)
        self.assertIn("function renderAdministratorPlans()", app_js)
        self.assertIn("function saveAdministratorPlans()", app_js)
        self.assertIn("mapState.administradoras", app_js)
        for campo in [
            "Data de cadastro do produto",
            "Responsável pelo cadastro do produto",
            "Tem Seguro obrigatório?",
            "Qual é a idade máxima (seguro obrigatório)",
            "Limite adesão sem comprovação de renda",
            "% de lance embutido",
            "Calculo do lance embutido",
            "Tem furo no grupo",
            "Aceita adesão de clientes com saída fiscal?",
            "Taxa Administração",
            "Tem negociação de Taxa?",
            "Fundo de reserva",
            "Idade máxima ok?",
            "Crédito a ser contratado:",
            "Lance máximo:",
            "Prazo mínimo:",
        ]:
            self.assertIn(campo, app_js)
        self.assertIn("function administratorPlanCreditoContratado(rule)", app_js)
        self.assertIn("return creditoDesejado / (1 - percentualLanceEmbutido);", app_js)
        self.assertIn("function administratorPlanLanceMaximo(rule)", app_js)
        self.assertIn("((creditoContratado * percentualLanceEmbutido) + lanceProprio) / creditoContratado", app_js)
        self.assertIn("function administratorPlanPrazoMinimo(rule)", app_js)
        self.assertIn("creditoContratado * taxaAdm", app_js)
        self.assertIn("creditoContratado * fundoReserva", app_js)
        self.assertIn("- ((creditoContratado * percentualLanceEmbutido) + lanceProprio)", app_js)
        self.assertIn("[\"credito_a_ser_contratado\", \"lance_maximo\", \"prazo_minimo\"].includes", app_js)
        for administradora in ["AUTO-CAIXA", "AUTO-CAOA", "AUTO-ITAU", "CAIXA", "CANOPUS", "CAOA", "ITAU", "PORTO", "RODOBENS"]:
            self.assertIn(administradora, app_js)
        self.assertNotIn("administratorTotalDisponivel", index_html)
        self.assertNotIn("administratorUsarFgts", index_html)
        self.assertNotIn('id="exportAdministratorsCsvBtn"', index_html)
        self.assertNotIn('id="advanceToGroupsBtn"', index_html)
        self.assertNotIn('apiPost("/viabilidade/administradoras"', app_js)
        self.assertNotIn("function exportAdministratorsCsv()", app_js)
        self.assertNotIn("function syncAdministratorInterviewToGroups()", app_js)

    def test_viabilidade_grupos_nao_repete_formulario_do_cliente(self):
        index_html = (ROOT / "backend" / "static" / "index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")

        self.assertIn("Grupos Compat", index_html)
        self.assertIn("const profile = collectClientProfile();", app_js)
        self.assertIn("Credito a contratar", index_html)
        self.assertNotIn("Lance referencia perfil", index_html)
        self.assertNotIn("Lance maximo cliente", index_html)
        self.assertNotIn("Motivo / Alerta", index_html)
        self.assertNotIn("<th>Compativel</th>", index_html)
        self.assertIn("function renderViabilityEmpty(result)", app_js)
        self.assertIn("regras_administradoras_pendentes_analise_humana", app_js)
        self.assertNotIn('id="viabilityProfileSummary"', index_html)
        self.assertNotIn("function renderViabilityProfileSummary()", app_js)
        self.assertNotIn("Viabilidade por Administradoras", index_html)
        self.assertNotIn("administratorViabilityBody", index_html)
        self.assertNotIn("function renderAdministratorViability", app_js)
        self.assertNotIn('id="viabilityForm"', index_html)
        self.assertNotIn('id="clearViabilityBtn"', index_html)
        self.assertNotIn('id="viabilityChecklist"', index_html)

    def test_tela_perfil_cliente_existe_apos_mapa(self):
        index_html = (ROOT / "backend" / "static" / "index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")
        style_css = (ROOT / "backend" / "static" / "css" / "style.css").read_text(encoding="utf-8")

        self.assertLess(index_html.index('data-screen="mapa"'), index_html.index('data-screen="perfil"'))
        self.assertIn('id="screen-perfil"', index_html)
        self.assertIn("Perfil do Cliente", index_html)
        self.assertIn("clientProfileCredito", index_html)
        self.assertIn("clientProfileTotalDisponivel", index_html)
        self.assertIn("clientProfileConceito", index_html)
        self.assertIn("function saveClientProfile", app_js)
        self.assertIn("function applyClientProfileToFlow", app_js)
        self.assertIn(".client-profile-layout", style_css)

    def test_configuracoes_possui_planos_administradoras(self):
        index_html = (ROOT / "backend" / "static" / "index.html").read_text(encoding="utf-8")
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")

        self.assertIn("Planos Administradoras", index_html)
        self.assertIn('id="administratorRulesForm"', index_html)
        self.assertIn('id="administratorRulesBody"', index_html)
        self.assertIn("adminRuleAdministradora", index_html)
        self.assertIn("function renderAdministratorRules(rules)", app_js)
        self.assertIn("function saveAdministratorRule()", app_js)
        self.assertIn("administradoras_regras", app_js)

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
        for etapa in ["Perfil do Cliente", "Administradoras", "Viabilidade de Grupos", "Estrategias", "Estudo Financeiro"]:
            self.assertIn(etapa, app_js)
        for exemplo in [
            "R$ 450.000",
            "R$ 900.000",
            "66,6667%",
            "80 meses",
            "R$ 100.000 de FGTS",
            "grupo com 62 meses restantes nao atende",
        ]:
            self.assertIn(exemplo, app_js)
        self.assertIn("business-rule-note-input", style_css)
        self.assertIn(".business-rules-table", style_css)

    def test_filtros_de_credito_validam_intervalo(self):
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")

        self.assertIn("function validateMapCreditFilters(filters)", app_js)
        self.assertIn("O credito minimo nao pode ser maior que o credito maximo.", app_js)

    def test_percentuais_de_entrada_sao_formatados_sem_residuo_decimal(self):
        app_js = (ROOT / "backend" / "static" / "js" / "app.js").read_text(encoding="utf-8")

        self.assertIn("function percentToInputValue(value)", app_js)
        self.assertIn('maximumFractionDigits: 3', app_js)
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

        self.assertIn('id="exportGroupsCsvBtn"', index_html)
        self.assertIn('id="exportStudiesCsvBtn"', index_html)
        self.assertIn("Exportar Planilha", index_html)
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
        self.assertNotIn('id="groupFormHistoryAddMonthBtn"', index_html)
        self.assertNotIn('id="historyUpdateAddMonthBtn"', index_html)
        self.assertNotIn("Adicionar mes", index_html)
        self.assertNotIn("function addHistoryEditorMonth", app_js)
        self.assertIn(".history-add-month", style_css)
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
        self.assertIn('collectHistoryBatchPayloads("groupFormHistory")', app_js)
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
            "1 a 3 meses",
            "4 a 6 meses",
            "7 a 12 meses",
            "13 a 24 meses",
        ]:
            self.assertIn(label, index_html)
        self.assertIn("function clientProfileConcept(months)", app_js)
        self.assertIn('id="clientProfileTipoBem"', index_html)
        self.assertIn("tipo_bem: profile.tipo_bem", app_js)
        self.assertNotIn('tipo_bem: "Imovel"', app_js)
        self.assertIn("payload.lance_proprio < 0", app_js)

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

        self.assertIn("/static/css/style.css?v=20260608-18", index_html)
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
