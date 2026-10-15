const screens = {
  mapa: {
    letter: "A) MAPA DE GRUPOS",
    title: "Mapa de Grupos",
    subtitle: "Lista e manutenção da base de grupos",
    action: "Novo Grupo",
  },
  "mapa-assembleia": {
    letter: "A) MAPA ASSEMBLEIA",
    title: "Mapa Assembleia",
    subtitle: "Calendário e regras operacionais das assembleias",
    action: "",
  },
  perfil: {
    letter: "B) PERFIL DO CLIENTE",
    title: "Perfil do Cliente",
    subtitle: "Entrevista, capacidade financeira e necessidade de crédito",
    action: "Salvar Perfil",
  },
  motor360: {
    letter: "C) MOTOR 360 DE VIABILIDADE",
    title: "Motor 360 de Viabilidade do Consórcio",
    subtitle: "Todas as estratégias viáveis, com destaque para a preferência declarada",
    action: "",
  },
  "grupos-selecionados": {
    letter: "D) GRUPOS SELECIONADOS",
    title: "Grupos Selecionados",
    subtitle: "Comparativo dos grupos escolhidos para a próxima etapa",
    action: "",
  },
  administradoras: {
    letter: "D) ADMINISTRADORAS",
    title: "Administradoras",
    subtitle: "Parâmetros por administradora integrados à seleção de grupos",
    action: "Salvar Parâmetros",
  },
  configuracoes: {
    letter: "G) CONFIGURAÇÕES",
    title: "Configurações",
    subtitle: "Configurações do sistema e preferências",
    action: "Salvar Configurações",
  },
  "crm-piperun": {
    letter: "",
    title: "",
    subtitle: "",
    action: "",
  },
  estudo: {
    letter: "E) ESTUDO FINANCEIRO",
    title: "Estudo Financeiro",
    subtitle: "Área reservada para a reconstrução do modelo de estudo financeiro",
    action: "",
  },
};

const mapState = {
  page: 1,
  pageSize: 25,
  total: 0,
  items: [],
  administradoras: [],
  lanceSortField: "",
  lanceSortOrder: "",
  lastLoadAt: null,
};

const assemblyState = { data: null, loaded: false, loadingPromise: null };

const defasagemState = {
  report: null,
  modal: null,
};

const configState = {
  data: null,
};

const operationalLogs = [];
const motor360ExecutionLogs = [];
const clientDiagnosticErrors = [];
window.addEventListener("error", (event) => clientDiagnosticErrors.push({ type: "error", message: event.message, source: event.filename, line: event.lineno, time: new Date().toISOString() }));
window.addEventListener("unhandledrejection", (event) => clientDiagnosticErrors.push({ type: "unhandledrejection", message: String(event.reason?.stack || event.reason || ""), time: new Date().toISOString() }));
const investorPreferenceFlags = [];
const savedMotor360SelectedGroups = (() => {
  try { return JSON.parse(localStorage.getItem("crediclass.motor360.selectedGroups") || "[]"); } catch { return []; }
})();
const savedMotor360QuotaCounts = (() => {
  try { return JSON.parse(localStorage.getItem("crediclass.motor360.quotaCounts") || "{}"); } catch { return {}; }
})();
const savedMotor360SelectedData = (() => {
  try { return JSON.parse(localStorage.getItem("crediclass.motor360.selectedGroupData") || "{}"); } catch { return {}; }
})();
const savedMotor360Administrator = localStorage.getItem("crediclass.motor360.administrator") || "";
const investorState = {
  result: null,
  analysisKey: null,
  simulatedBid: null,
  lastDeclaredBid: null,
  lastDesiredCredit: null,
  preferences: [],
  administrator: savedMotor360Administrator,
  audit: null,
  selectedGroupIds: new Set(savedMotor360SelectedGroups.map(String)),
  selectedScenarioIds: new Map(Object.entries(JSON.parse(localStorage.getItem("crediclass.motor360.selectedScenarios") || "{}"))),
  quotaCounts: new Map(Object.entries(savedMotor360QuotaCounts).map(([id, value]) => [String(id), Math.min(50, Math.max(1, Number(value) || 1))])),
  selectedGroupData: new Map(Object.entries(savedMotor360SelectedData)),
  floatingSummaryMinimized: true,
};
const motor360GroupAnalyticsCache = new Map();
let motor360AnalyticsCacheResult = null;
let motor360CardCacheResult = null;
let investorAnalysisController = null;
let investorAnalysisRequestId = 0;
const INVESTOR_ANALYSIS_CACHE_KEY = "crediclass.motor360.analysisCache.v1";
const HISTORY_START_MONTH = "2024-01";
const CLIENT_PROFILE_STORAGE_KEY = "crediclass.clientProfile.v1";
const CLIENT_OBJECTIVE_RULES = {
  "Contemplar - urgente - 3 meses": { prazo: 3, conceito: "Super Agressivo", tipoBem: "Imovel", estadoBem: "Pronto" },
  "Contemplar - rapido - 6 meses": { prazo: 6, conceito: "Agressivo", tipoBem: "Imovel", estadoBem: "Pronto" },
  "Contemplar - moderado - 12 meses": { prazo: 12, conceito: "Moderado", tipoBem: "Imovel", estadoBem: "Pronto" },
  "Contemplar - conservador - 24 meses": { prazo: 24, conceito: "Conservador", tipoBem: "Imovel", estadoBem: "Pronto" },
  "Contemplar - investidor - 36 meses": { prazo: 36, conceito: "Investidor", tipoBem: "Imovel", estadoBem: "Pronto" },
  "Investidor - Adquirir imovel e alugar (pagar parcelas com aluguel)": { prazo: 36, conceito: "Investidor", tipoBem: "Imovel", estadoBem: "Pronto" },
  "Investidor - Adquirir terreno, construir e alugar (pagar parcelas com aluguel)": { prazo: 36, conceito: "Investidor", tipoBem: "Imovel", estadoBem: "Construcao" },
  "Investidor - Adquirir terreno, construir e vender (ganhar lucro)": { prazo: 36, conceito: "Investidor", tipoBem: "Imovel", estadoBem: "Construcao" },
  "Investidor - Vender carta contemplada (ganhar agil)": { prazo: 36, conceito: "Investidor", tipoBem: "Imovel", estadoBem: "Indefinido" },
  "Investidor - Carta de credito aposentadoria (alavancagem, rendimento e flexibilidade)": { prazo: 36, conceito: "Investidor", tipoBem: "Imovel", estadoBem: "Indefinido" },
};
const CLIENT_CONTRACTING_MODES = {
  pf_individual: { label: "Pessoa fisica individual", pfCount: 1 },
  pf_conjuge: { label: "Pessoa fisica com conjuge", pfCount: 2 },
  pf_grupo: { label: "Dois titulares / grupo familiar", pfCount: 4 },
  pj: { label: "Pessoa juridica", pfCount: 0 },
};
const CLIENT_PF_ROLES = [
  { papel: "titular_1", label: "Titular 1" },
  { papel: "conjuge_1", label: "Conjuge 1" },
  { papel: "titular_2", label: "Titular 2" },
  { papel: "conjuge_2", label: "Conjuge 2" },
];
const CLIENT_PJ_SOCIOS_LIMIT = 5;
const DEFAULT_INCOME_COMMITMENT_PERCENT = 0.3;
const DEFAULT_PJ_COMMITMENT_PERCENT = DEFAULT_INCOME_COMMITMENT_PERCENT;
const DEFAULT_CPF_COMMITMENT_PERCENT = 0.3;
const authState = { user: null };
let appBootstrapped = false;
const businessRuleStatuses = ["Pendente", "Em revisao", "Revisado", "Corrigir regra"];
const businessRulesFlow = [
  {
    id: "perfil-cliente",
    etapa: "1. Perfil do Cliente",
    regras: [
      "O sistema recebe credito liquido desejado, prazo desejado, objetivo, tipo de bem, estado do bem, recursos proprios, FGTS, renda e limites de parcela.",
      "O credito informado e sempre liquido, ou seja, o valor que o cliente precisa receber efetivamente.",
      "Soma renda titular e renda conjuge para renda total; soma FGTS titular e conjuge para FGTS total.",
    ],
  },
  {
    id: "estrategia",
    etapa: "2. Estrategia",
    regras: [
      "O backend define o perfil estrategico: ate 3 meses = Super Agressivo; ate 6 meses = Agressivo; ate 12 meses = Moderado; ate 24 meses = Conservador; acima de 24 meses = Investidor.",
      "A referencia de lance usa somente meses com qtd_contemplacoes maior que zero e menor_lance preenchido acima de zero.",
      "Todas as referencias recebem acrescimo operacional de 0,25 ponto percentual.",
    ],
  },
  {
    id: "administradoras",
    etapa: "4. Fase 1 - Calculadora de Grupos",
    regras: [
      "Os parametros por administradora deixam de ser uma etapa isolada e passam a alimentar a selecao de grupos.",
      "FGTS e lance embutido sao condicionais: FGTS so entra quando permitido; lance embutido so entra quando permitido.",
      "Taxa administrativa, fundo de reserva, idade, renda, tipo de bem e historico entram na selecao dos melhores grupos.",
    ],
  },
  {
    id: "cenarios",
    etapa: "4. Fase 2 - Selecao Melhores Grupos por Prazo Remanescente e Compatibilidade Menor Lance",
    regras: [
      "O sistema seleciona grupos conforme o objetivo do consorcio, usando filtros de contemplacao ou beneficios de investimento.",
      "Quando houver lance embutido: credito_contratado = credito_liquido_desejado / (1 - percentual_lance_embutido).",
      "Credito liquido da carta = credito_contratado - lance_embutido. O ranking da selecao usa os creditos liquidos das cartas candidatas.",
      "Lance total = lance embutido + recurso proprio utilizado + FGTS utilizado.",
      "Parcela total do cenario = soma das parcelas de todas as cartas.",
      "Renda minima necessaria = parcela_total_cenario * 3.",
    ],
  },
];
let detailsModal = null;
let detailsChart = null;
let motor360ChanceChart = null;
let groupFormModal = null;
let groupFormMode = "create";
let groupFormId = null;
let groupFormHistoryData = {};
let groupFormOriginalHistoryData = {};
let groupFormSheetFields = {};
let currentDetailsGroupId = null;
let configUserModal = null;
let configUserMode = "create";
let configUserIndex = null;
let configAdministratorRuleIndex = null;

function setLoginError(message) {
  const errorBox = document.getElementById("loginError");
  if (!errorBox) return;
  errorBox.textContent = message || "Usuario ou senha invalidos.";
  errorBox.classList.toggle("d-none", !message);
}

function showLogin(message = "") {
  authState.user = null;
  document.body.classList.remove("auth-pending", "authenticated");
  document.body.classList.add("auth-login");
  setLoginError(message);
  window.setTimeout(() => document.getElementById("loginUsuario")?.focus(), 60);
}

function showApp(user) {
  authState.user = user;
  document.body.classList.remove("auth-pending", "auth-login");
  document.body.classList.add("authenticated");
  setLoginError("");

  const displayName = user?.nome || user?.usuario || "Usuario";
  document.getElementById("sessionUserName").textContent = displayName;
  document.getElementById("sessionUserRole").textContent = user?.perfil || "Equipe";
  document.getElementById("sessionAvatar").textContent = displayName.trim().charAt(0).toUpperCase() || "U";
}

async function checkSession() {
  const response = await fetch("/api/auth/me", {
    cache: "no-store",
    credentials: "same-origin",
  });
  if (!response.ok) return null;
  const data = await response.json().catch(() => ({}));
  return data.user || null;
}

async function submitLogin(event) {
  event.preventDefault();
  const button = document.getElementById("loginSubmitBtn");
  const usuario = document.getElementById("loginUsuario").value.trim();
  const senha = document.getElementById("loginSenha").value;

  setLoginError("");
  button.disabled = true;
  button.textContent = "Entrando...";

  try {
    const response = await fetch("/api/auth/login", {
      method: "POST",
      cache: "no-store",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ usuario, senha }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      setLoginError(data.error || "Usuario ou senha invalidos.");
      return;
    }
    showApp(data.user);
    await initializeDashboardData();
  } catch (error) {
    setLoginError("Nao foi possivel comunicar com o servidor.");
  } finally {
    button.disabled = false;
    button.textContent = "Entrar";
  }
}

async function logout() {
  await fetch("/api/auth/logout", {
    method: "POST",
    cache: "no-store",
    credentials: "same-origin",
  }).catch(() => null);
  appBootstrapped = false;
  window.location.reload();
}

async function initializeDashboardData() {
  if (appBootstrapped) return;
  appBootstrapped = true;
  // O conteúdo inicial é o Perfil do Cliente; o cabeçalho deve refletir a
  // mesma tela, em vez de manter os textos estáticos do Mapa de Grupos.
  activateScreen("perfil");
  loadHealth().catch(() => {
    document.getElementById("environmentLabel").textContent = "indisponivel";
    document.getElementById("systemVersionLabel").textContent = "indisponivel";
  });
  loadMapaGrupos();
  loadClientProfile();
  ensureClientProfileHoldersRendered();
  updateViabilityTotals();
}

async function bootApp() {
  const user = await checkSession();
  if (!user) {
    showLogin();
    return;
  }
  showApp(user);
  await initializeDashboardData();
}

function showToast(message, type = "success") {
  const region = document.getElementById("toastRegion");
  const toast = document.createElement("div");
  toast.className = `alert alert-${type} shadow-sm mb-2`;
  toast.textContent = message;
  region.appendChild(toast);
  setTimeout(() => toast.remove(), 3600);
}

function withTimeout(promise, timeoutMs, message) {
  let timeoutId;
  const timeout = new Promise((_, reject) => {
    timeoutId = window.setTimeout(() => reject(new Error(message)), timeoutMs);
  });
  return Promise.race([promise, timeout]).finally(() => window.clearTimeout(timeoutId));
}

function activateScreen(screenName) {
  const meta = screens[screenName];
  if (!meta) return;
  if (screenName === "grupos-selecionados") {
    const selectedGroups = [...investorState.selectedGroupIds];
    const groupsWithoutScenario = selectedGroups.filter((groupId) => !selectedScenarioIdsForGroup(groupId).size);
    if (selectedGroups.length && groupsWithoutScenario.length) {
      showToast("Para avançar, escolha pelo menos um cenário financeiro em cada grupo selecionado.", "warning");
      const firstMissing = groupsWithoutScenario[0];
      window.setTimeout(() => focusMotor360Group(motor360GroupAnchorId(firstMissing.split("|").pop() || firstMissing)), 0);
      return;
    }
    openSelectedGroupsWorkspace();
    return;
  }

  document.querySelectorAll(".nav-item").forEach((item) => {
    item.classList.toggle("active", item.dataset.screen === screenName);
  });

  document.querySelectorAll(".screen-panel").forEach((panel) => {
    panel.classList.toggle("active", panel.id === `screen-${screenName}`);
  });

  document.getElementById("screenLetter").textContent = meta.letter;
  document.getElementById("screenTitle").textContent = meta.title;
  document.getElementById("screenSubtitle").textContent = meta.subtitle;
  document.querySelector(".page-header")?.classList.toggle("d-none", ["perfil", "motor360", "grupos-selecionados", "crm-piperun", "estudo"].includes(screenName));
  const primaryAction = document.getElementById("primaryAction");
  primaryAction.textContent = meta.action;
  primaryAction.classList.toggle("d-none", ["motor360", "estudo", "mapa-assembleia"].includes(screenName));
  document.getElementById("reloadMapDataBtn").classList.toggle("d-none", screenName !== "mapa");

  if (screenName === "motor360") {
    if (investorState.result) {
      renderInvestorAnalysis(investorState.result);
    } else {
      loadInvestorAnalysis();
    }
  }
  if (screenName === "mapa-assembleia") loadAssemblyMap();
  if (screenName === "estudo") {
    clearRetiredFinancialStudyState();
    renderFinancialStudySelectedAdministrator();
  }
  if (screenName === "configuracoes") {
    loadConfiguracoes();
  }
  if (screenName === "crm-piperun") resetPipeRunPreview();
}

function renderFinancialStudySelectedAdministrator() {
  const target = document.getElementById("financialStudyPart3Administrator");
  if (!target) return;
  const administrators = [...new Set(selectedMotor360Items()
    .map((item) => String(item.administradora || "").trim())
    .filter(Boolean))];
  target.textContent = administrators.length
    ? administrators.join(" · ")
    : "Nenhuma administradora selecionada";
}

function clearRetiredFinancialStudyState() {
  sessionStorage.removeItem("crediclass.currentStudy");
  localStorage.removeItem("crediclass.financialStudy.sections");
}

function resetPipeRunPreview() {
  const state = document.getElementById("pipeRunPreviewState");
  if (state && !document.getElementById("pipeRunPreviewBody")?.children.length) state.textContent = "Clique em “Carregar oportunidades” para consultar o PipeRun.";
}

async function loadPipeRunPreview() {
  const state = document.getElementById("pipeRunPreviewState");
  const wrap = document.getElementById("pipeRunPreviewTableWrap");
  const body = document.getElementById("pipeRunPreviewBody");
  const details = document.getElementById("pipeRunPreviewDetails");
  state.className = "table-state";
  state.textContent = "Consultando oportunidades e notas...";
  wrap.classList.add("d-none");
  body.innerHTML = "";
  details.innerHTML = "";
  details.classList.add("d-none");
  try {
    const response = await fetch("/api/piperun/63416847", { credentials: "same-origin", cache: "no-store" });
    const payload = await response.json();
    if (!response.ok || payload.success === false) throw new Error(payload.error || "Não foi possível consultar o PipeRun.");
    const dados = payload.dados || {};
    const safe = (value) => String(value ?? "-").replace(/[&<>\"]/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[char]));
    const labels = { crm_oportunidade_id: "ID da oportunidade", nota_id: "ID da nota", nome: "Titular", email: "E-mail", celular: "Celular", cpf: "CPF", credito_desejado: "Crédito desejado", lance_proprio: "Lance máximo", parcela_desejada: "Parcela máxima", prazo_contemplacao: "Prazo de contemplação", renda_total: "Renda total", fgts: "FGTS", objetivo: "Objetivo" };
    const rawFields = dados.campos_formulario || {};
    const fields = { crm_oportunidade_id: payload.crm_oportunidade_id, nota_id: payload.nota_id, ...dados, ...Object.fromEntries(Object.entries(rawFields).map(([key, value]) => [`form_${key}`, Array.isArray(value) ? value.join(" | ") : value])) };
    body.innerHTML = Object.entries(fields).filter(([, value]) => value !== null && value !== undefined && value !== "" && !Array.isArray(value) && typeof value !== "object").map(([key, value]) => `<tr><td>${safe(labels[key] || key)}</td><td>${safe(value)}</td></tr>`).join("");
    const people = Array.isArray(dados.titulares) ? dados.titulares : [];
    details.innerHTML = `<div class="crm-preview-section"><h3>Status da extração</h3><p><span class="crm-preview-status ${payload.encontrado ? "is-ok" : "is-warning"}">${payload.encontrado ? "Nota encontrada e extraída" : "Nota não encontrada"}</span></p></div>${people.length ? `<div class="crm-preview-section"><h3>Pessoas identificadas</h3><div class="crm-people-grid">${people.map((person, index) => `<article><strong>${safe(index === 0 ? "Titular" : `Pessoa ${index + 1}`)}</strong><span>${safe(person.nome || "Não informado")}</span><small>Renda: ${safe(person.renda || "0")} · FGTS: ${safe(person.lance_fgts || "0")}</small></article>`).join("")}</div></div>` : ""}${payload.nota_texto ? `<details class="crm-original-note"><summary>Visualizar nota original</summary><pre>${safe(payload.nota_texto)}</pre></details>` : ""}`;
    state.textContent = "Oportunidade 63416847 carregada temporariamente para teste.";
    wrap.classList.remove("d-none");
    details.classList.remove("d-none");
  } catch (error) { state.className = "table-state table-state-error"; state.textContent = error.message; }
}

async function preparePipeRunPlan() {
  const plan = document.getElementById("pipeRunSyncPlan");
  plan.classList.remove("d-none");
  plan.innerHTML = "<p>Montando plano de sincronização em modo simulação...</p>";
  try {
    const response = await fetch("/api/piperun/63416847/sync-plan", { method: "POST", credentials: "same-origin" });
    const payload = await response.json();
    if (!response.ok || !payload.success) throw new Error(payload.error || "Não foi possível montar o plano.");
    const validation = payload.can_execute ? "Dados mínimos validados. Execução ainda não iniciada." : `Campos ausentes: ${(payload.missing_fields || []).join(", ")}`;
    plan.innerHTML = `<h3>Plano de sincronização — simulação</h3><p>${validation}</p><p>Nenhuma alteração foi enviada ao PipeRun.</p><ol>${(payload.steps || []).map((step) => `<li><strong>${step.name}</strong><code>${step.method} ${step.endpoint}</code><small>${JSON.stringify(step.payload || {})}</small><span>${step.status}</span></li>`).join("")}</ol>`;
    document.getElementById("executePipeRunBtn")?.classList.toggle("d-none", !payload.can_execute);
  } catch (error) { plan.innerHTML = `<p class="table-state-error">${error.message}</p>`; }
}

function formatMoney(value) {
  if (value === null || value === undefined || !Number.isFinite(Number(value)) || Number(value) > 100000000) return "-";
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(value);
}

function formatMoneyInputValue(value) {
  const number = Number(parseNumberInput(value));
  if (!Number.isFinite(number)) return "";
  return new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(number);
}

function formatDecimalInputValue(value, minimumFractionDigits = 2, maximumFractionDigits = 2) {
  const number = Number(parseNumberInput(value));
  if (!Number.isFinite(number)) return "";
  return new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits,
    maximumFractionDigits,
  }).format(number);
}

function formatMoneyInputById(id) {
  const input = document.getElementById(id);
  if (!input || !String(input.value || "").trim()) return;
  input.value = formatMoneyInputValue(input.value);
}

function formatMoneyInputElement(input) {
  if (!input) return;
  const value = String(input.value || "").trim();
  input.value = value ? formatMoneyInputValue(value) : "";
  if (document.activeElement === input && input.value) {
    const decimalSeparator = input.value.indexOf(",");
    const caretPosition = decimalSeparator >= 0 ? decimalSeparator : input.value.length;
    input.setSelectionRange(caretPosition, caretPosition);
  }
}

function setMoneyInputValue(id, value) {
  const input = document.getElementById(id);
  if (!input) return;
  input.value = value === null || value === undefined || value === "" ? "" : formatMoneyInputValue(value);
}

function formatPercent(value) {
  if (value === null || value === undefined) return "-";
  return `${new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 3 }).format(value * 100)}%`;
}

function percentToInputValue(value) {
  if (value === null || value === undefined) return "";
  return new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
    useGrouping: false,
  }).format(Number(value) * 100);
}

function formatBool(value) {
  if (value === true) return "Sim";
  if (value === false) return "Nao";
  return "-";
}

function averageNumber(values) {
  const valid = values.filter((value) => Number.isFinite(value));
  if (!valid.length) return null;
  return valid.reduce((sum, value) => sum + value, 0) / valid.length;
}

function initialsFromName(value) {
  const words = String(value || "").trim().split(/\s+/).filter(Boolean);
  if (!words.length) return "--";
  return words.slice(0, 2).map((word) => word[0]).join("").toUpperCase();
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "\"": "&quot;",
    "'": "&#039;",
  }[char]));
}

function csvValue(value) {
  const text = String(value ?? "").replace(/\r?\n/g, " ").trim();
  return `"${text.replace(/"/g, '""')}"`;
}

function downloadCsv(filename, rows) {
  const content = rows.map((row) => row.map(csvValue).join(";")).join("\n");
  const blob = new Blob([`\uFEFF${content}`], { type: "text/csv;charset=utf-8" });
  downloadBlob(filename, blob);
}

function downloadBlob(filename, blob) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function downloadJson(filename, data) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function renderOperationalLogs() {
  const list = document.getElementById("operationalLogsList");
  if (!list) return;
  const items = operationalLogs.length ? operationalLogs : [{ message: "Nenhum evento registrado nesta sessao.", time: "--" }];
  list.innerHTML = items.map((item) => `
    <li><strong>${escapeHtml(item.message)}</strong><span>${escapeHtml(item.time)}</span></li>
  `).join("");
}

function addOperationalLog(message) {
  operationalLogs.unshift({ message, time: new Date().toLocaleString("pt-BR") });
  operationalLogs.splice(8);
  renderOperationalLogs();
}

function downloadConfigBackup() {
  if (!configState.data) {
    showToast("Carregue as configuracoes antes de baixar backup.", "warning");
    return;
  }
  const backup = {
    gerado_em: new Date().toISOString(),
    configuracoes: configState.data,
  };
  downloadJson(`crediclass-configuracoes-${new Date().toISOString().slice(0, 10)}.json`, backup);
  addOperationalLog("Backup JSON das configuracoes gerado");
  showToast("Backup JSON gerado.", "success");
}

async function exportGroupsCsv() {
  const button = document.getElementById("exportGroupsCsvBtn");
  if (button) button.disabled = true;
  try {
    const response = await fetch("/api/grupos/exportar-planilha", {
      cache: "no-store",
      credentials: "same-origin",
    });
    if (response.status === 401) {
      showLogin("Sessao expirada. Entre novamente para exportar a planilha.");
      return;
    }
    if (!response.ok) throw new Error("Falha ao exportar planilha oficial");

    const disposition = response.headers.get("Content-Disposition") || "";
    const match = disposition.match(/filename="?([^";]+)"?/i);
    const filename = match?.[1] || `crediclass-planilha-oficial-${new Date().toISOString().slice(0, 10)}.csv`;
    const blob = await response.blob();
    downloadBlob(filename, blob);
    showToast("Planilha oficial exportada.", "success");
  } catch (error) {
    showToast("Nao foi possivel exportar a planilha oficial.", "danger");
  } finally {
    if (button) button.disabled = false;
  }
}

function renderMotor360ExecutionLogs() {
  const list = document.getElementById("motor360ExecutionLogsList");
  const counter = document.getElementById("motor360ExecutionLogsCount");
  if (!list) return;
  counter && (counter.textContent = `${motor360ExecutionLogs.length} evento(s)`);
  list.innerHTML = motor360ExecutionLogs.length
    ? motor360ExecutionLogs.map((item) => `
      <li class="motor360-execution-log motor360-execution-log-${escapeHtml(item.level)}">
        <span class="motor360-execution-log-time">${escapeHtml(item.time)}</span>
        <strong>${escapeHtml(item.message)}</strong>
        ${item.detail ? `<small>${escapeHtml(item.detail)}</small>` : ""}
      </li>
    `).join("")
    : '<li class="motor360-execution-log-empty">Nenhum evento registrado nesta sessão.</li>';
}

function addMotor360ExecutionLog(message, detail = "", level = "info") {
  motor360ExecutionLogs.unshift({
    message,
    detail,
    level,
    time: new Date().toLocaleString("pt-BR"),
  });
  motor360ExecutionLogs.splice(100);
  renderMotor360ExecutionLogs();
}

function parseNumberInput(value) {
  const text = String(value || "").replace("R$", "").replace("%", "").trim();
  if (!text) return "";
  return text.replace(/\./g, "").replace(",", ".");
}

function toNumber(value) {
  const parsed = Number(parseNumberInput(value));
  return Number.isFinite(parsed) ? parsed : 0;
}

function optionalNumber(value) {
  const normalized = parseNumberInput(value);
  if (normalized === "") return null;
  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : null;
}

function normalizeText(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .trim()
    .toLowerCase();
}

function monthKeyToDate(monthKey) {
  const [year, month] = String(monthKey || "").split("-").map(Number);
  if (!year || !month) return null;
  return new Date(year, month - 1, 1);
}

function addMonths(monthKey, amount) {
  const date = monthKeyToDate(monthKey);
  if (!date) return monthKey;
  date.setMonth(date.getMonth() + amount);
  return date.toISOString().slice(0, 7);
}

function currentMonthKey() {
  return new Date().toISOString().slice(0, 7);
}

function compareMonthKeys(a, b) {
  return String(a).localeCompare(String(b));
}

function historyMonthLabel(monthKey) {
  const date = monthKeyToDate(monthKey);
  if (!date) return monthKey;
  return new Intl.DateTimeFormat("pt-BR", { month: "short", year: "numeric" }).format(date).replace(".", "");
}

function buildHistoryRows(historico = {}, extraMonths = []) {
  const months = new Set(Object.keys(historico || {}).filter(Boolean));
  extraMonths.filter(Boolean).forEach((month) => months.add(month));
  let cursor = HISTORY_START_MONTH;
  const endMonth = [...months, currentMonthKey()].sort(compareMonthKeys).at(-1) || currentMonthKey();
  while (compareMonthKeys(cursor, endMonth) <= 0) {
    months.add(cursor);
    cursor = addMonths(cursor, 1);
  }
  return [...months].sort(compareMonthKeys).map((month) => [month, historico?.[month] || {}]);
}

function formatChartMonth(monthKey) {
  const date = monthKeyToDate(monthKey);
  if (!date) return monthKey;
  return new Intl.DateTimeFormat("pt-BR", { month: "short", year: "2-digit" }).format(date).replace(".", "");
}

function getMapFilters() {
  return {
    administradora: document.getElementById("filterAdministradora").value,
    tipo_bem: document.getElementById("filterTipoBem").value,
    status: document.getElementById("filterStatus").value,
    busca: document.getElementById("filterBusca").value.trim(),
    credito_minimo: parseNumberInput(document.getElementById("filterCreditoMinimo").value),
    credito_maximo: parseNumberInput(document.getElementById("filterCreditoMaximo").value),
    prazo_minimo: document.getElementById("filterPrazoMinimo").value.trim(),
    prazo_maximo: document.getElementById("filterPrazoMaximo").value.trim(),
  };
}

function validateMapCreditFilters(filters) {
  const minimum = filters.credito_minimo === "" ? null : Number(filters.credito_minimo);
  const maximum = filters.credito_maximo === "" ? null : Number(filters.credito_maximo);
  if (minimum !== null && maximum !== null && minimum > maximum) {
    showToast("O credito minimo nao pode ser maior que o credito maximo.", "warning");
    return false;
  }
  return true;
}

function buildQuery(params) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== "" && value !== null && value !== undefined) query.set(key, value);
  });
  if (mapState.lanceSortField && mapState.lanceSortOrder) {
    query.set("sort_lance", mapState.lanceSortField);
    query.set("sort_order", mapState.lanceSortOrder);
  }
  query.set("page", mapState.page);
  query.set("page_size", mapState.pageSize);
  return query.toString();
}

function setMapState(state) {
  document.getElementById("groupsLoading").classList.toggle("d-none", state !== "loading");
  document.getElementById("groupsError").classList.toggle("d-none", state !== "error");
  document.getElementById("groupsEmpty").classList.toggle("d-none", state !== "empty");
  document.getElementById("groupsTableWrap").classList.toggle("d-none", state !== "ready");
}

function updateSelectOptions(id, values, defaultLabel) {
  const select = document.getElementById(id);
  const selected = select.value;
  select.innerHTML = `<option value="">${defaultLabel}</option>${values.map((value) => `<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`).join("")}`;
  if (values.includes(selected)) select.value = selected;
}

function updateFilterOptions(administradoras = [], tipos = []) {
  updateSelectOptions("filterAdministradora", administradoras, "Todas");
  updateSelectOptions("filterTipoBem", tipos, "Todos");
}

function renderSummary(items, total, totalAdministradoras = null) {
  const administradoras = new Set(items.map((item) => item.administradora).filter(Boolean));
  const totalEl = document.getElementById("summaryTotal");
  const administradorasEl = document.getElementById("summaryAdministradoras");
  if (totalEl) totalEl.textContent = total;
  if (administradorasEl) administradorasEl.textContent = totalAdministradoras ?? administradoras.size;
}

function renderGroupsTable(items) {
  hideHistoryHoverModal();
  const tbody = document.getElementById("groupsTableBody");
  tbody.innerHTML = items.map((item, index) => {
    return `
      <tr>
        <td>${escapeHtml(item.grupo_id)}</td>
        <td>${escapeHtml(item.administradora)}</td>
        <td>${escapeHtml(item.tipo_bem)}</td>
        <td>${formatMoney(item.credito_maximo)}</td>
        <td>${formatPercent(item.taxa_adm)}</td>
        <td class="lance-profile-cell">${formatPercent(item.lance_agressivo)}</td>
        <td class="lance-profile-cell">${formatPercent(item.lance_moderado)}</td>
        <td class="lance-profile-cell">${formatPercent(item.lance_conservador)}</td>
        <td class="lance-profile-cell">${formatPercent(item.lance_super_conservador)}</td>
        <td>${item.prazo_restante ?? "-"}</td>
        <td><span class="history-hover-trigger" data-history-index="${index}" tabindex="0">${escapeHtml(item.atualizado || "-")}</span></td>
        <td>
          <div class="row-actions">
            <button class="btn btn-sm btn-outline-primary" type="button" data-map-action="visualizar" data-group-id="${escapeHtml(item.grupo_id)}">Ver</button>
            <button class="btn btn-sm btn-outline-secondary" type="button" data-map-action="editar" data-group-id="${escapeHtml(item.grupo_id)}">Editar</button>
          </div>
        </td>
      </tr>
    `;
  }).join("");
}

function formatHistoryPercent(value) {
  return value === null || value === undefined || value === "" ? "-" : formatPercent(value);
}

function formatHistoryQuantity(value) {
  return value === null || value === undefined || value === "" ? "-" : escapeHtml(value);
}

function renderHistoryHoverRows(history = []) {
  if (!history.length) {
    return '<tr><td colspan="4" class="history-hover-empty">Sem historico mensal carregado.</td></tr>';
  }
  return history.map((item) => `
    <tr class="${item.atualizado ? "history-month-updated" : ""}">
      <td>${escapeHtml(item.label || item.mes || "-")}</td>
      <td>${formatHistoryPercent(item.maior_lance)}</td>
      <td>${formatHistoryPercent(item.menor_lance)}</td>
      <td>${formatHistoryQuantity(item.qtd_contemplacoes)}</td>
    </tr>
  `).join("");
}

function positionHistoryHoverModal(modal, trigger) {
  const rect = trigger.getBoundingClientRect();
  modal.style.visibility = "hidden";
  modal.classList.remove("d-none");
  const modalRect = modal.getBoundingClientRect();
  const top = Math.min(window.innerHeight - modalRect.height - 12, rect.bottom + 8);
  const left = Math.min(window.innerWidth - modalRect.width - 12, Math.max(12, rect.left - modalRect.width / 2 + rect.width / 2));
  modal.style.top = `${Math.max(12, top)}px`;
  modal.style.left = `${left}px`;
  modal.style.visibility = "visible";
}

function showHistoryHoverModal(trigger) {
  const index = Number(trigger.dataset.historyIndex);
  const item = mapState.items[index];
  showGroupHistoryHoverModal(trigger, item);
}

function showGroupHistoryHoverModal(trigger, item, capacity = null) {
  cancelHistoryHoverHide();
  const modalId = trigger?.dataset?.motor360HistoryGroup ? "motor360HistoryHoverModal" : "historyHoverModal";
  const modal = document.getElementById(modalId);
  if (!item || !modal) return;
  const average = Number.isFinite(Number(capacity?.media_contemplacoes))
    ? `${new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 }).format(Number(capacity.media_contemplacoes))} contemplações`
    : "Sem histórico suficiente";
  const averageCalculation = capacity?.meses_com_dados
    ? `${new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 }).format(Number(capacity.total_contemplacoes || 0))} contemplações ÷ ${escapeHtml(String(capacity.meses_com_dados))} meses = ${escapeHtml(average)}`
    : "Quantidade mensal não disponível";
  const capacitySummary = capacity ? `
    <div class="history-hover-capacity">
      <span>Média máxima · ${escapeHtml(capacity.perfil || "Perfil não classificado")}</span>
      <strong>${escapeHtml(average)}</strong>
      <small>Cálculo do período: ${averageCalculation}</small>
    </div>
  ` : "";
  modal.innerHTML = `
    <div class="history-hover-title">
      <strong>Histórico dos últimos 12 meses</strong>
      <span>${escapeHtml(item.administradora || "-")} - Grupo ${escapeHtml(item.grupo || item.grupo_id || "-")}</span>
    </div>
    ${capacitySummary}
    <table>
      <thead>
        <tr><th>Mês</th><th>Maior lance</th><th>Menor lance</th><th>Qtd.</th></tr>
      </thead>
      <tbody>${renderHistoryHoverRows(item.historico_12_meses || [])}</tbody>
    </table>
  `;
  modal.setAttribute("aria-hidden", "false");
  positionHistoryHoverModal(modal, trigger);
}

let historyHoverHideTimer = null;

function cancelHistoryHoverHide() {
  if (!historyHoverHideTimer) return;
  clearTimeout(historyHoverHideTimer);
  historyHoverHideTimer = null;
}

function scheduleHistoryHoverHide(delay = 280) {
  cancelHistoryHoverHide();
  historyHoverHideTimer = window.setTimeout(() => {
    historyHoverHideTimer = null;
    hideHistoryHoverModal();
  }, delay);
}

function hideHistoryHoverModal() {
  cancelHistoryHoverHide();
  ["historyHoverModal", "motor360HistoryHoverModal"].forEach((modalId) => {
    const modal = document.getElementById(modalId);
    if (!modal) return;
    modal.classList.add("d-none");
    modal.setAttribute("aria-hidden", "true");
  });
}

function setDefasagemState(state) {
  document.getElementById("defasagemLoading").classList.toggle("d-none", state !== "loading");
  document.getElementById("defasagemError").classList.toggle("d-none", state !== "error");
  document.getElementById("defasagemContent").classList.toggle("d-none", state !== "ready");
}

function defasagemStatusLabel(status) {
  const labels = {
    em_dia: "Em dia",
    atencao: "Atencao",
    atrasado: "Atrasado",
    critico: "Critico",
    marcado_para_conferencia: "Marcado",
  };
  return labels[status] || status || "-";
}

function defasagemStatusClass(status) {
  if (status === "em_dia") return "status-ok";
  if (status === "marcado_para_conferencia") return "status-marked";
  if (status === "critico") return "status-critical";
  if (status === "atrasado") return "status-late";
  return "status-warning";
}

function formatPendingMonths(months = []) {
  if (!months.length) {
    return '<span class="defasagem-months-ok">Sem pendencia</span>';
  }
  const first = months[0];
  const last = months[months.length - 1];
  const visible = months.slice(0, 4);
  const hiddenCount = months.length - visible.length;
  const chips = visible.map((month) => `<span class="defasagem-month-chip">${escapeHtml(month)}</span>`).join("");
  const more = hiddenCount > 0
    ? `<span class="defasagem-month-more">+ ${hiddenCount} mes(es)</span>`
    : "";
  return `
    <div class="defasagem-month-card" title="${escapeHtml(months.join(", "))}">
      <strong>${months.length} mes(es) pendente(s)</strong>
      <small>${escapeHtml(first)} a ${escapeHtml(last)}</small>
      <div class="defasagem-month-chip-row">${chips}${more}</div>
    </div>
  `;
}

function getFilteredDefasagemItems() {
  const filter = document.getElementById("defasagemFilter").value;
  const items = defasagemState.report?.items || [];
  if (filter === "todos") return items;
  if (filter === "criticos") return items.filter((item) => item.total_meses_defasados >= 6);
  if (filter === "concluidos") return items.filter((item) => item.concluido);
  return items.filter((item) => item.total_meses_defasados > 0 && !item.concluido);
}

function renderDefasagemReport(report) {
  defasagemState.report = report;
  document.getElementById("defasagemSubtitle").textContent = `Competencia atual: ${report.competencia_atual_label}. Atualize primeiro os grupos com maior defasagem.`;
  document.getElementById("defasagemCompetencia").textContent = report.competencia_atual_label;
  document.getElementById("defasagemAtrasados").textContent = report.total_atrasados;
  document.getElementById("defasagemCriticos").textContent = report.total_criticos;
  document.getElementById("defasagemMaior").textContent = `${report.maior_defasagem_meses} mes(es)`;
  renderDefasagemRows();
}

async function loadDefasagemReport(attempt = 0) {
  const loading = document.getElementById("defasagemLoading");
  const report = await apiGet("/grupos/defasagem");
  if (report.preparando) {
    loading.textContent = attempt === 0
      ? "Preparando dados de defasagem da planilha..."
      : `Preparando dados de defasagem da planilha... tentativa ${attempt + 1}`;
    if (attempt >= 18) {
      throw new Error("Tempo limite ao preparar a defasagem.");
    }
    window.setTimeout(() => {
      loadDefasagemReport(attempt + 1).catch(() => setDefasagemState("error"));
    }, 4000);
    return;
  }
  renderDefasagemReport(report);
  setDefasagemState("ready");
}

function renderDefasagemRows() {
  const tbody = document.getElementById("defasagemTableBody");
  const items = getFilteredDefasagemItems();
  if (!items.length) {
    tbody.innerHTML = '<tr><td colspan="9" class="empty-cell">Nenhum grupo encontrado para este filtro.</td></tr>';
    return;
  }
  tbody.innerHTML = items.map((item, index) => {
    const pendingText = formatPendingMonths(item.meses_pendentes_label);
    const updatedFields = item.campos_ultima_competencia?.length ? item.campos_ultima_competencia.join(", ") : "-";
    return `
      <tr class="${item.concluido ? "defasagem-done" : ""}">
        <td><strong>${index + 1}</strong></td>
        <td>
          <strong>${escapeHtml(item.grupo || item.grupo_id)}</strong>
          <small>${escapeHtml(item.tipo_bem || "-")}</small>
        </td>
        <td>${escapeHtml(item.administradora || "-")}</td>
        <td>
          <strong>${escapeHtml(item.ultima_competencia_label || "-")}</strong>
          <small>${escapeHtml(updatedFields)}</small>
        </td>
        <td>
          <span class="defasagem-status ${defasagemStatusClass(item.status_defasagem)}">${escapeHtml(defasagemStatusLabel(item.status_defasagem))}</span>
          <small>${item.total_meses_defasados} mes(es)</small>
        </td>
        <td class="defasagem-months">${pendingText}</td>
        <td>
          <span>${escapeHtml(item.check_atualizado_em || "-")}</span>
          <small>${escapeHtml(item.operador || "")}</small>
        </td>
        <td>
          <textarea class="form-control defasagem-note" data-defasagem-note="${escapeHtml(item.grupo_id)}" rows="2" placeholder="Observacao da atualizacao">${escapeHtml(item.observacao || "")}</textarea>
        </td>
        <td>
          <label class="defasagem-check">
            <input type="checkbox" data-defasagem-check="${escapeHtml(item.grupo_id)}" ${item.concluido ? "checked" : ""}>
            <span>Atualizado</span>
          </label>
        </td>
      </tr>
    `;
  }).join("");
}

async function openDefasagemModal() {
  if (!defasagemState.modal) {
    defasagemState.modal = new bootstrap.Modal(document.getElementById("defasagemModal"));
  }
  setDefasagemState("loading");
  document.getElementById("defasagemLoading").textContent = "Calculando defasagem dos grupos...";
  defasagemState.modal.show();
  try {
    await loadDefasagemReport();
  } catch (error) {
    setDefasagemState("error");
  }
}

async function saveDefasagemTask(grupoId, concluido) {
  const note = document.querySelector(`[data-defasagem-note="${CSS.escape(grupoId)}"]`)?.value || "";
  await apiPut(`/grupos/defasagem/${encodeURIComponent(grupoId)}`, { concluido, observacao: note });
  showToast("Plano de atualizacao registrado.", "success");
  const report = await apiGet("/grupos/defasagem");
  renderDefasagemReport(report);
}

function setDetailsState(state) {
  document.getElementById("detailsLoading").classList.toggle("d-none", state !== "loading");
  document.getElementById("detailsError").classList.toggle("d-none", state !== "error");
  document.getElementById("detailsContent").classList.toggle("d-none", state !== "ready");
}

function detailField(label, value) {
  return `
    <div class="detail-field">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value ?? "-")}</strong>
    </div>
  `;
}

function renderDetailsGeneral(group) {
  const fields = [
    ["ID Grupo", group.grupo_id],
    ["Administradora", group.administradora],
    ["Grupo", group.grupo],
    ["Tipo de Bem", group.tipo_bem],
    ["Credito minimo", formatMoney(group.credito_minimo)],
    ["Credito maximo", formatMoney(group.credito_maximo)],
    ["Taxa de Administracao", formatPercent(group.taxa_adm)],
    ["Fundo Reserva", formatPercent(group.fundo_reserva)],
    ["Prazo total", group.prazo_total ? `${group.prazo_total} meses` : "-"],
    ["Prazo restante", group.prazo_restante ? `${group.prazo_restante} meses` : "-"],
    ["Primeira Assembleia", group.primeira_assembleia || "-"],
    ["Ultima Assembleia", group.ultima_assembleia || "-"],
    ["Data de termino", group.data_termino || "-"],
    ["Seguro garantia", formatBool(group.seguro_garantia)],
    ["Meia parcela", formatBool(group.meia_parcela)],
    ["Lance embutido", formatBool(group.lance_embutido)],
    ["FGTS permitido", formatBool(group.fgts)],
    ["Status", group.status || "-"],
    ["Cadastrado por", group.cadastrado_por || "-"],
    ["Ultima atualizacao", group.ultima_atualizacao || "-"],
  ];
  document.getElementById("detailsGeneralGrid").innerHTML = fields.map(([label, value]) => detailField(label, value)).join("");
}

function renderDetailsParams(group) {
  const fields = [
    ["Categoria do grupo", group.categoria || "-"],
    ["Percentual maximo de lance embutido", formatPercent(group.percentual_lance_embutido)],
    ["Percentual de lance fixo", formatPercent(group.percentual_lance_fixo)],
    ["Parcela reduzida", group.parcela_reduzida || "-"],
    ["Indice de correcao", group.indice_correcao || "-"],
    ["Vencimento da parcela", group.vencimento_parcela || "-"],
    ["Vencimento do lance", group.vencimento_lance || "-"],
    ["Regras especiais", group.regras_especiais || "-"],
  ];
  document.getElementById("detailsParamsGrid").innerHTML = fields.map(([label, value]) => detailField(label, value)).join("");
}

function renderDetailsHistory(group) {
  const entries = buildHistoryRows(group.historico || {});
  renderHistoryEditor("historyUpdate", group.historico || {});

  const filledEntries = entries
    .filter(([, item]) => item.maior_lance !== null || item.menor_lance !== null)
    .sort(([a], [b]) => compareMonthKeys(a, b));

  const chartEntries = filledEntries.slice(-24);
  const labels = chartEntries.map(([month]) => formatChartMonth(month));
  const maiores = chartEntries.map(([, item]) => item.maior_lance !== null && item.maior_lance !== undefined ? item.maior_lance * 100 : null);
  const menores = chartEntries.map(([, item]) => item.menor_lance !== null && item.menor_lance !== undefined ? item.menor_lance * 100 : null);

  if (detailsChart) detailsChart.destroy();
  const canvas = document.getElementById("detailsHistoryChart");
  detailsChart = new Chart(canvas, {
    type: "line",
    data: {
      labels,
      datasets: [
        { label: "Maior Lance", data: maiores, borderColor: "#0d6efd", backgroundColor: "rgba(13, 110, 253, 0.08)", borderWidth: 2, tension: 0.18, pointRadius: 2, pointHoverRadius: 4, spanGaps: false },
        { label: "Menor Lance", data: menores, borderColor: "#16a34a", backgroundColor: "rgba(22, 163, 74, 0.08)", borderWidth: 2, tension: 0.18, pointRadius: 2, pointHoverRadius: 4, spanGaps: false },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { position: "top", labels: { boxWidth: 12, usePointStyle: true } },
        tooltip: {
          callbacks: {
            label(context) {
              return `${context.dataset.label}: ${new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 }).format(context.parsed.y)}%`;
            },
          },
        },
      },
      scales: {
        x: { grid: { display: false }, ticks: { maxRotation: 0, autoSkip: true, maxTicksLimit: 12 } },
        y: { min: 0, max: 100, ticks: { stepSize: 10, callback: (value) => `${value}%` }, title: { display: true, text: "Percentual do lance" } },
      },
    },
  });
  setTimeout(() => detailsChart?.resize(), 50);
}

function renderDetailsAudit(group) {
  const items = group.auditoria || [];
  const state = document.getElementById("detailsAuditState");
  const list = document.getElementById("detailsAuditList");
  if (!items.length) {
    state.textContent = "Nenhum registro de auditoria encontrado para este grupo.";
    state.classList.remove("d-none");
    list.classList.add("d-none");
    list.innerHTML = "";
    return;
  }
  state.classList.add("d-none");
  list.classList.remove("d-none");
  list.innerHTML = items.map((item) => `
    <li>
      <strong>${escapeHtml(item.acao || "-")}</strong>
      <span>${escapeHtml(item.detalhe || "-")}</span>
      <small>${escapeHtml(item.data_hora || "-")} - ${escapeHtml(item.operador || "Sistema")}</small>
    </li>
  `).join("");
}

function inputPercent(value) {
  return percentToInputValue(value);
}

function normalizeHistoryField(field, rawValue) {
  const text = String(rawValue || "").trim();
  if (!text) return { value: null, comparable: "" };
  const number = Number(parseNumberInput(text));
  if (!Number.isFinite(number) || number < 0) {
    throw new Error("Informe apenas numeros positivos no historico mensal.");
  }
  if (field === "qtd_contemplacoes") {
    if (!Number.isInteger(number)) throw new Error("Quantidade de contemplacoes deve ser um numero inteiro.");
    return { value: number, comparable: String(number) };
  }
  const percent = number > 1 ? number / 100 : number;
  return { value: percent, comparable: String(Number(percent.toFixed(8))) };
}

function originalHistoryComparable(field, value) {
  if (value === null || value === undefined || value === "") return "";
  return normalizeHistoryField(field, field === "qtd_contemplacoes" ? value : value * 100).comparable;
}

function historyEditorRow(prefix, month, item = {}) {
  return `
    <div class="history-edit-row" data-history-month="${escapeHtml(month)}">
      <div class="history-edit-month"><strong>${escapeHtml(historyMonthLabel(month))}</strong><span>${escapeHtml(month)}</span></div>
      <label><span>Maior Lance (%)</span><input class="form-control" data-history-field="maior_lance" data-original-value="${escapeHtml(originalHistoryComparable("maior_lance", item.maior_lance))}" inputmode="decimal" value="${escapeHtml(inputPercent(item.maior_lance))}"></label>
      <label><span>Menor Lance (%)</span><input class="form-control" data-history-field="menor_lance" data-original-value="${escapeHtml(originalHistoryComparable("menor_lance", item.menor_lance))}" inputmode="decimal" value="${escapeHtml(inputPercent(item.menor_lance))}"></label>
      <label><span>Qtd</span><input class="form-control" data-history-field="qtd_contemplacoes" data-original-value="${escapeHtml(originalHistoryComparable("qtd_contemplacoes", item.qtd_contemplacoes))}" inputmode="numeric" value="${escapeHtml(item.qtd_contemplacoes ?? "")}"></label>
    </div>
  `;
}

function historyEditorYearFilter(prefix) {
  const select = document.getElementById(`${prefix}Year`);
  return select?.value || "";
}

function renderHistoryEditor(prefix, historico = {}, extraMonths = []) {
  const grid = document.getElementById(`${prefix}Grid`);
  if (!grid) return;
  const year = historyEditorYearFilter(prefix);
  const rows = buildHistoryRows(historico, extraMonths).filter(([month]) => !year || month.startsWith(`${year}-`));
  grid.innerHTML = `
    <div class="history-edit-head">
      <span>Mes</span>
      <span>Maior Lance</span>
      <span>Menor Lance</span>
      <span>Qtd Contemplacoes</span>
    </div>
    ${rows.map(([month, item]) => historyEditorRow(prefix, month, item)).join("")}
  `;
  setHistoryUpdateStateForPrefix(prefix, "");
}

function collectHistoryRowPayload(row) {
  const payload = {
    mes: row.dataset.historyMonth,
  };
  const normalized = {};
  row.querySelectorAll("[data-history-field]").forEach((input) => {
    const field = input.dataset.historyField;
    normalized[field] = normalizeHistoryField(field, input.value);
    if (normalized[field].comparable !== input.dataset.originalValue) {
      payload[field] = normalized[field].value;
    }
  });
  const maior = normalized.maior_lance?.value;
  const menor = normalized.menor_lance?.value;
  if (maior !== null && maior !== undefined && menor !== null && menor !== undefined && menor > maior) {
    throw new Error(`No mes ${historyMonthLabel(payload.mes)}, o menor lance nao pode ser maior que o maior lance.`);
  }
  return payload;
}

function collectHistoryBatchPayloads(prefix) {
  const grid = document.getElementById(`${prefix}Grid`);
  if (!grid) return [];
  return [...grid.querySelectorAll(".history-edit-row")]
    .map(collectHistoryRowPayload)
    .filter(hasMonthlyHistoryMetrics);
}

function syncGroupFormVisibleHistory() {
  const grid = document.getElementById("groupFormHistoryGrid");
  if (!grid) return;
  grid.querySelectorAll(".history-edit-row").forEach((row) => {
    const month = row.dataset.historyMonth;
    if (!month) return;
    groupFormHistoryData[month] = groupFormHistoryData[month] || {};
    row.querySelectorAll("[data-history-field]").forEach((input) => {
      groupFormHistoryData[month][input.dataset.historyField] = normalizeHistoryField(input.dataset.historyField, input.value).value;
    });
  });
}

function collectGroupFormHistoryPayloads() {
  syncGroupFormVisibleHistory();
  return Object.entries(groupFormHistoryData)
    .sort(([monthA], [monthB]) => compareMonthKeys(monthA, monthB))
    .map(([month, item]) => {
      const payload = { mes: month };
      const original = groupFormOriginalHistoryData[month] || {};
      ["maior_lance", "menor_lance", "qtd_contemplacoes"].forEach((field) => {
        if (originalHistoryComparable(field, item?.[field]) !== originalHistoryComparable(field, original?.[field])) {
          payload[field] = item?.[field] ?? null;
        }
      });
      if (
        item?.maior_lance !== null
        && item?.maior_lance !== undefined
        && item?.menor_lance !== null
        && item?.menor_lance !== undefined
        && item.menor_lance > item.maior_lance
      ) {
        throw new Error(`No mes ${historyMonthLabel(month)}, o menor lance nao pode ser maior que o maior lance.`);
      }
      return payload;
    })
    .filter(hasMonthlyHistoryMetrics);
}

function markHistoryPayloadsSaved(prefix, payloads) {
  const grid = document.getElementById(`${prefix}Grid`);
  if (!grid) return;
  payloads.forEach((payload) => {
    const row = grid.querySelector(`[data-history-month="${payload.mes}"]`);
    if (!row) return;
    ["maior_lance", "menor_lance", "qtd_contemplacoes"].forEach((field) => {
      if (!(field in payload)) return;
      const input = row.querySelector(`[data-history-field="${field}"]`);
      if (!input) return;
      input.dataset.originalValue = normalizeHistoryField(field, input.value).comparable;
    });
  });
}

function hasMonthlyHistoryMetrics(payload) {
  return payload.maior_lance !== undefined || payload.menor_lance !== undefined || payload.qtd_contemplacoes !== undefined;
}

function setHistoryUpdateStateForPrefix(prefix, state, message = "") {
  const status = document.getElementById(`${prefix}Status`);
  const button = document.getElementById(`${prefix}SaveBtn`);
  if (button) {
    button.disabled = state === "loading";
    button.textContent = state === "loading" ? "Salvando..." : "Salvar Historico";
  }
  if (!status) return;
  status.className = `history-update-status ${state === "success" ? "success" : state === "error" ? "error" : ""}`;
  status.classList.toggle("d-none", !message);
  status.textContent = message;
}

function setHistoryUpdateState(state, message = "") {
  setHistoryUpdateStateForPrefix("historyUpdate", state, message);
}

async function saveHistoryUpdate() {
  if (!currentDetailsGroupId) return;
  let payloads = [];
  try {
    payloads = collectHistoryBatchPayloads("historyUpdate");
  } catch (error) {
    setHistoryUpdateState("error", error.message || "Revise os valores do historico.");
    return;
  }
  if (!payloads.length) {
    setHistoryUpdateState("error", "Nenhuma alteracao de historico para salvar.");
    return;
  }
  setHistoryUpdateState("loading", `Salvando ${payloads.length} mes(es) na Google Sheets...`);
  await apiPut(`/grupos/${encodeURIComponent(currentDetailsGroupId)}/historico/lote`, { items: payloads });
  markHistoryPayloadsSaved("historyUpdate", payloads);
  setHistoryUpdateState("success", "Historico atualizado na Google Sheets.");
  showToast("Historico mensal atualizado na Google Sheets.", "success");
  await loadMapaGrupos();
}

async function openGroupDetails(groupId) {
  currentDetailsGroupId = groupId;
  if (!detailsModal) {
    detailsModal = new bootstrap.Modal(document.getElementById("groupDetailsModal"));
  }
  detailsModal.show();
  setDetailsState("loading");
  document.getElementById("detailsTitle").textContent = "Detalhes do Grupo";
  document.getElementById("detailsSubtitle").textContent = groupId;

  try {
    const group = await apiGet(`/grupos/${encodeURIComponent(groupId)}`);
    document.getElementById("detailsTitle").textContent = `Detalhes do Grupo ${group.grupo}`;
    document.getElementById("detailsSubtitle").textContent = `${group.administradora} - ${group.tipo_bem}`;
    renderDetailsGeneral(group);
    renderDetailsParams(group);
    renderDetailsHistory(group);
    renderDetailsAudit(group);
    setDetailsState("ready");
  } catch (error) {
    setDetailsState("error");
  }
}

function ensureGroupFormModal() {
  if (!groupFormModal) {
    groupFormModal = new bootstrap.Modal(document.getElementById("groupFormModal"));
  }
}

function setGroupFormValues(group = {}) {
  setGroupFormIdentifierLock(groupFormMode === "edit");
  document.getElementById("groupFormAdministradora").value = group.administradora || "";
  document.getElementById("groupFormGrupo").value = group.grupo || "";
  document.getElementById("groupFormTipoBem").value = group.tipo_bem || "";
  setMoneyInputValue("groupFormCreditoMinimo", group.credito_minimo);
  setMoneyInputValue("groupFormCreditoMaximo", group.credito_maximo);
  document.getElementById("groupFormTaxaAdm").value = percentToInputValue(group.taxa_adm);
  document.getElementById("groupFormPrazoTotal").value = group.prazo_total ?? "";
  document.getElementById("groupFormStatus").value = group.status || "Ativo";
  renderGroupFormSheetFields(group);
  setGroupFormHistoryValues(group.historico || {});
}

function setGroupFormHistoryValues(historico) {
  groupFormHistoryData = JSON.parse(JSON.stringify(historico || {}));
  groupFormOriginalHistoryData = JSON.parse(JSON.stringify(historico || {}));
  renderHistoryEditor("groupFormHistory", historico || {});
  setGroupFormHistoryState("");
}

function setGroupFormHistoryState(state, message = "") {
  const status = document.getElementById("groupFormHistoryStatus");
  status.className = `history-update-status ${state === "success" ? "success" : state === "error" ? "error" : ""}`;
  status.classList.toggle("d-none", !message);
  status.textContent = message;
}

function findLoadedGroupSummary(groupId) {
  return mapState.items.find((item) => String(item.grupo_id).toUpperCase() === String(groupId).toUpperCase()) || null;
}

const groupFormFieldAliases = {
  administradora: ["adm", "administradora", "administradoras", "admin", "consorciadora"],
  grupo: ["grupo", "numero grupo", "numero do grupo", "codigo grupo", "codigo do grupo"],
  tipo_bem: ["tipo de bem", "tipo bem", "bem", "segmento"],
  credito_minimo: ["credito minimo", "menor credito", "credito min", "carta minima", "valor minimo"],
  credito_maximo: ["credito maximo", "maior credito", "credito max", "carta maxima", "valor maximo"],
  taxa_adm: ["taxa administracao", "taxa adm", "taxa administrativa", "tx adm"],
  prazo_total: ["prazo total", "prazo do grupo", "prazo grupo"],
  status: ["status"],
};

const groupFormFixedInputs = {
  tipo_bem: "groupFormTipoBem",
  credito_minimo: "groupFormCreditoMinimo",
  credito_maximo: "groupFormCreditoMaximo",
  taxa_adm: "groupFormTaxaAdm",
  prazo_total: "groupFormPrazoTotal",
  status: "groupFormStatus",
};

function sheetFieldForHeader(header) {
  const normalized = normalizeText(header).replace(/[^a-z0-9]+/g, " ").replace(/\s+/g, " ").trim();
  for (const [field, aliases] of Object.entries(groupFormFieldAliases)) {
    if (aliases.some((alias) => normalizeText(alias).replace(/[^a-z0-9]+/g, " ").replace(/\s+/g, " ").trim() === normalized)) {
      return field;
    }
  }
  return null;
}

function isHistorySheetHeader(header) {
  const normalized = normalizeText(header);
  const hasMonth = /\b(jan|fev|feb|mar|abr|apr|mai|may|jun|jul|ago|aug|set|sep|out|oct|nov|dez|dec)[\s\-\/]*\d{2,4}\b/.test(normalized);
  const hasMetric = /(maior|menor|contempla|contemplados|qtd|quantidade)/.test(normalized);
  return hasMonth && hasMetric;
}

function sheetFieldMaskType(header) {
  const normalized = normalizeText(header);
  if (/(%|percent|taxa|media lance|media contemp|lance quitacao|super agressivo|agressivo|moderado|conservador|investidor)/.test(normalized)) {
    return "percent";
  }
  if (/(credito|parcela|valor|preco|saldo|r\$|\(rs\)|limite|venda|categoria)/.test(normalized)) {
    return "money";
  }
  return "";
}

function formatSheetFieldInputValue(header, value) {
  if (value === null || value === undefined || String(value).trim() === "") return "";
  const mask = sheetFieldMaskType(header);
  if (mask === "percent") return formatDecimalInputValue(value, 2, 2) || String(value);
  if (mask === "money") return formatMoneyInputValue(value) || String(value);
  return String(value);
}

function setGroupFormIdentifierLock(locked) {
  ["groupFormAdministradora", "groupFormGrupo"].forEach((id) => {
    const input = document.getElementById(id);
    if (!input) return;
    input.readOnly = locked;
    input.setAttribute("aria-readonly", locked ? "true" : "false");
  });
}

function renderGroupFormSheetFields(group = {}) {
  groupFormSheetFields = group.campos_planilha || {};
  const grid = document.getElementById("groupFormSheetFieldsGrid");
  if (!grid) return;

  const fields = Object.entries(groupFormSheetFields).filter(([header]) => {
    const mapped = sheetFieldForHeader(header);
    return !mapped && !isHistorySheetHeader(header);
  });

  if (!fields.length) {
    grid.innerHTML = '<div class="group-sheet-fields-empty">Nenhum campo adicional da planilha foi carregado para esta linha.</div>';
    return;
  }

  grid.innerHTML = fields.map(([header, value]) => `
    <label title="${escapeHtml(header)}">
      <span>${escapeHtml(header)}</span>
      <input class="form-control" data-sheet-field-header="${escapeHtml(header)}" data-sheet-field-mask="${escapeHtml(sheetFieldMaskType(header))}" value="${escapeHtml(formatSheetFieldInputValue(header, value))}">
    </label>
  `).join("");
}

function collectGroupFormSheetFieldsPayload() {
  const payload = {};
  Object.keys(groupFormSheetFields || {}).forEach((header) => {
    const field = sheetFieldForHeader(header);
    if (field === "administradora" || field === "grupo" || isHistorySheetHeader(header)) return;
    const fixedInputId = groupFormFixedInputs[field];
    if (fixedInputId) {
      const input = document.getElementById(fixedInputId);
      payload[header] = input ? input.value : "";
    }
  });
  document.querySelectorAll("[data-sheet-field-header]").forEach((input) => {
    payload[input.dataset.sheetFieldHeader] = input.value;
  });
  return payload;
}

function collectGroupFormPayload() {
  const taxa = optionalNumber(document.getElementById("groupFormTaxaAdm").value);
  return {
    administradora: document.getElementById("groupFormAdministradora").value.trim(),
    grupo: document.getElementById("groupFormGrupo").value.trim(),
    tipo_bem: document.getElementById("groupFormTipoBem").value.trim(),
    credito_minimo: optionalNumber(document.getElementById("groupFormCreditoMinimo").value),
    credito_maximo: optionalNumber(document.getElementById("groupFormCreditoMaximo").value),
    taxa_adm: taxa !== null && taxa > 1 ? taxa / 100 : taxa,
    prazo_total: optionalNumber(document.getElementById("groupFormPrazoTotal").value),
    status: document.getElementById("groupFormStatus").value,
    campos_planilha: collectGroupFormSheetFieldsPayload(),
  };
}

async function openGroupForm(mode, groupId = null) {
  ensureGroupFormModal();
  if (detailsModal) detailsModal.hide();
  groupFormMode = mode;
  groupFormId = groupId;
  document.getElementById("groupCrudForm").reset();
  document.getElementById("groupFormTitle").textContent = mode === "create" ? "Novo Grupo" : mode === "duplicate" ? "Duplicar Grupo" : "Editar Grupo";
  document.getElementById("groupFormSubtitle").textContent = mode === "create" ? "Criacao de nova linha na Google Sheets" : groupId;

  if (mode === "create") {
    setGroupFormValues();
    groupFormModal.show();
    return;
  }

  const summary = findLoadedGroupSummary(groupId);
  let openedWithSummary = false;
  if (summary) {
    setGroupFormValues(summary);
    if (mode === "duplicate") {
      document.getElementById("groupFormGrupo").value = `${summary.grupo}-COPIA`;
      groupFormId = null;
    }
    setGroupFormHistoryState("success", "Carregando historico completo do grupo...");
    groupFormModal.show();
    openedWithSummary = true;
  }

  try {
    const group = await apiGet(`/grupos/${encodeURIComponent(groupId)}`);
    setGroupFormValues(group);
    if (mode === "duplicate") {
      document.getElementById("groupFormGrupo").value = `${group.grupo}-COPIA`;
      groupFormId = null;
    }
    groupFormModal.show();
  } catch (error) {
    if (openedWithSummary) {
      setGroupFormHistoryState("error", "Nao foi possivel carregar o historico completo. Os dados principais podem ser editados; tente novamente para atualizar historico.");
      return;
    }
    showToast(error.message || "Nao foi possivel carregar o grupo para edicao.", "danger");
  }
}

async function saveGroupForm() {
  const payload = collectGroupFormPayload();
  let historyPayloads = [];
  try {
    historyPayloads = collectGroupFormHistoryPayloads();
  } catch (error) {
    setGroupFormHistoryState("error", error.message || "Revise os valores do historico.");
    return;
  }
  let targetGroupId = payload.grupo;
  if (groupFormMode === "edit" && groupFormId) {
    await apiPut(`/grupos/${encodeURIComponent(groupFormId)}`, payload);
    showToast("Grupo atualizado na Google Sheets.", "success");
  } else {
    const result = await apiPost("/grupos", payload);
    targetGroupId = result.grupo_id || payload.grupo;
    showToast(`Grupo criado: ${result.grupo_id}`, "success");
  }
  if (historyPayloads.length) {
    setGroupFormHistoryState("success", `Salvando ${historyPayloads.length} mes(es) de historico...`);
    await apiPut(`/grupos/${encodeURIComponent(targetGroupId)}/historico/lote`, { items: historyPayloads });
    markHistoryPayloadsSaved("groupFormHistory", historyPayloads);
    showToast("Historico mensal atualizado na Google Sheets.", "success");
  }
  groupFormModal.hide();
  await loadMapaGrupos();
  if (historyPayloads.length) {
    showToast(`${historyPayloads.length} mes(es) de historico salvos na Google Sheets.`, "success");
  }
}

async function deleteGroup(groupId) {
  await apiDelete(`/grupos/${encodeURIComponent(groupId)}`);
  showToast("Grupo marcado como Excluido na Google Sheets.", "success");
  loadMapaGrupos();
}

function renderPagination() {
  const totalPages = Math.max(1, Math.ceil(mapState.total / mapState.pageSize));
  document.getElementById("paginationInfo").textContent = `Pagina ${mapState.page} de ${totalPages} - ${mapState.total} grupo(s)`;
  document.getElementById("prevPageBtn").disabled = mapState.page <= 1;
  document.getElementById("nextPageBtn").disabled = mapState.page >= totalPages;
}

async function loadMapaGrupos() {
  const filters = getMapFilters();
  if (!validateMapCreditFilters(filters)) return;
  setMapState("loading");
  try {
    const data = await apiGet(`/grupos?${buildQuery(filters)}`);
    mapState.total = data.total;
    mapState.items = data.items;
    mapState.administradoras = data.administradoras || [];
    mapState.lastLoadAt = new Date().toLocaleString("pt-BR");
    updateFilterOptions(data.administradoras || [], data.tipos_bem || []);
    renderSummary(data.items, data.total, data.total_administradoras);
    renderGroupsTable(data.items);
    renderPagination();
    document.getElementById("tableSubtitle").textContent = `${data.total} grupo(s) encontrado(s)`;
    setMapState(data.items.length ? "ready" : "empty");
    addOperationalLog(`Mapa de Grupos carregado: ${data.total} grupo(s)`);
  } catch (error) {
    renderSummary([], 0);
    document.getElementById("tableSubtitle").textContent = "Erro ao carregar grupos";
    setMapState("error");
    addOperationalLog("Falha ao carregar Mapa de Grupos");
  }
}

async function reloadMapData() {
  const button = document.getElementById("reloadMapDataBtn");
  button.disabled = true;
  button.textContent = "Recarregando...";
  try {
    const result = await apiPost("/reload", {});
    mapState.page = 1;
    await loadMapaGrupos();
    showToast(`Dados recarregados da planilha: ${result.total} grupo(s).`, "success");
    addOperationalLog(`Recarregamento manual da planilha: ${result.total} grupo(s)`);
  } catch (error) {
    showToast(error.message || "Nao foi possivel recarregar os dados.", "danger");
  } finally {
    button.disabled = false;
    button.textContent = "Recarregar dados";
  }
}

function updateViabilityTotals() {
  if (!document.getElementById("viabilityFgtsTitular")) return { fgts: 0, renda: 0 };
  const fgts = toNumber(document.getElementById("viabilityFgtsTitular").value) + toNumber(document.getElementById("viabilityFgtsConjuge").value);
  const renda = toNumber(document.getElementById("viabilityRendaTitular").value) + toNumber(document.getElementById("viabilityRendaConjuge").value);
  document.getElementById("viabilityFgtsTotal").value = formatMoney(fgts);
  document.getElementById("viabilityRendaTotal").value = formatMoney(renda);
  return { fgts, renda };
}

function clientProfileConcept(months) {
  const prazo = Number(months || 0);
  if (prazo <= 3) return "Super Agressivo";
  if (prazo <= 6) return "Agressivo";
  if (prazo <= 12) return "Moderado";
  if (prazo <= 24) return "Conservador";
  return "Investidor";
}

function clientObjectiveRule(objective) {
  return CLIENT_OBJECTIVE_RULES[objective] || CLIENT_OBJECTIVE_RULES["Contemplar - urgente - 3 meses"];
}

function emptyPessoaFisica(index) {
  const role = CLIENT_PF_ROLES[index] || CLIENT_PF_ROLES[0];
  return {
    papel: role.papel,
    nome: "",
    nascimento: "",
    lance_fgts: 0,
    lance_recursos_proprios: 0,
    renda: 0,
  };
}

function emptyPessoaJuridica() {
  return {
    empresa: {
      nome: "",
      cnpj: "",
      data_constituicao: "",
      faturamento_mensal: 0,
      tipo: "",
    },
    socios: Array.from({ length: CLIENT_PJ_SOCIOS_LIMIT }, (_, index) => ({
      papel: index === 0 ? "socio_administrador" : `socio_${index + 1}`,
      nome: "",
      nascimento: "",
      lance_recursos_proprios: 0,
      renda: 0,
    })),
  };
}

function normalizeClientTitulares(profile = {}) {
  const tipo = profile.tipo_contratacao || profile.titulares?.tipo_contratacao || "pf_individual";
  const mode = CLIENT_CONTRACTING_MODES[tipo] ? tipo : "pf_individual";
  const pessoasFisicas = Array.from({ length: 4 }, (_, index) => ({
    ...emptyPessoaFisica(index),
    ...(profile.titulares?.pessoas_fisicas?.[index] || {}),
  }));
  if (!profile.titulares?.pessoas_fisicas?.length) {
    pessoasFisicas[0] = {
      ...pessoasFisicas[0],
      nome: profile.nome || "",
      nascimento: profile.data_nascimento || "",
      lance_fgts: Number(profile.fgts_titular || profile.fgts || 0),
      lance_recursos_proprios: Number(profile.lance_recursos_proprios || profile.lance_proprio || 0),
      renda: Number(profile.renda_titular || profile.renda_total || 0),
    };
    pessoasFisicas[1] = {
      ...pessoasFisicas[1],
      nome: profile.nome_conjuge || "",
      nascimento: profile.data_nascimento_conjuge || "",
      lance_fgts: Number(profile.fgts_conjuge || 0),
      renda: Number(profile.renda_conjuge || 0),
    };
  }
  const pessoaJuridica = {
    ...emptyPessoaJuridica(),
    ...(profile.titulares?.pessoa_juridica || {}),
  };
  pessoaJuridica.empresa = {
    ...emptyPessoaJuridica().empresa,
    ...(profile.titulares?.pessoa_juridica?.empresa || {}),
  };
  pessoaJuridica.socios = Array.from({ length: CLIENT_PJ_SOCIOS_LIMIT }, (_, index) => ({
    ...emptyPessoaJuridica().socios[index],
    ...(profile.titulares?.pessoa_juridica?.socios?.[index] || {}),
  }));
  return {
    tipo_contratacao: mode,
    pessoas_fisicas: pessoasFisicas,
    pessoa_juridica: pessoaJuridica,
  };
}

function profileHolderInput(field, value = "", label = "", options = {}) {
  const type = options.type || "text";
  const moneyAttr = options.money ? ' data-money="true" inputmode="decimal"' : "";
  return `
    <label>
      <span>${escapeHtml(label)}</span>
      <input class="form-control" data-holder-field="${escapeHtml(field)}" type="${type}" value="${escapeHtml(value ?? "")}"${moneyAttr}>
    </label>
  `;
}

function renderPessoaFisicaCard(person, index) {
  const role = CLIENT_PF_ROLES[index] || CLIENT_PF_ROLES[0];
  return `
    <article class="profile-holder-table">
      <header>${escapeHtml(role.label)}</header>
      <div class="profile-holder-fields">
        ${profileHolderInput(`pessoas_fisicas.${index}.nome`, person.nome, "Nome")}
        ${profileHolderInput(`pessoas_fisicas.${index}.nascimento`, person.nascimento, "Nascimento", { type: "date" })}
        ${profileHolderInput(`pessoas_fisicas.${index}.lance_fgts`, formatMoneyInputValue(person.lance_fgts || ""), "Lance FGTS", { money: true })}
        ${profileHolderInput(`pessoas_fisicas.${index}.lance_recursos_proprios`, formatMoneyInputValue(person.lance_recursos_proprios || ""), "Lance Recursos Proprios", { money: true })}
        ${profileHolderInput(`pessoas_fisicas.${index}.renda`, formatMoneyInputValue(person.renda || ""), "Renda do Cliente", { money: true })}
      </div>
    </article>
  `;
}

function renderPessoaJuridicaCards(data) {
  const empresa = data.pessoa_juridica.empresa;
  const socios = data.pessoa_juridica.socios;
  return `
    <article class="profile-holder-table">
      <header>Empresa titular</header>
      <div class="profile-holder-fields">
        ${profileHolderInput("pessoa_juridica.empresa.nome", empresa.nome, "Nome")}
        ${profileHolderInput("pessoa_juridica.empresa.cnpj", empresa.cnpj, "CNPJ")}
        ${profileHolderInput("pessoa_juridica.empresa.data_constituicao", empresa.data_constituicao, "Data constituicao", { type: "date" })}
        ${profileHolderInput("pessoa_juridica.empresa.faturamento_mensal", formatMoneyInputValue(empresa.faturamento_mensal || ""), "Faturamento mensal", { money: true })}
        ${profileHolderInput("pessoa_juridica.empresa.tipo", empresa.tipo, "Tipo")}
      </div>
    </article>
    ${socios.map((socio, index) => `
      <article class="profile-holder-table">
        <header>${index === 0 ? "Socio administrador" : `Socio ${index + 1}`}</header>
        <div class="profile-holder-fields">
          ${profileHolderInput(`pessoa_juridica.socios.${index}.nome`, socio.nome, "Nome")}
          ${profileHolderInput(`pessoa_juridica.socios.${index}.nascimento`, socio.nascimento, "Nascimento", { type: "date" })}
          ${profileHolderInput(`pessoa_juridica.socios.${index}.lance_recursos_proprios`, formatMoneyInputValue(socio.lance_recursos_proprios || ""), "Lance Recursos Proprios", { money: true })}
          ${profileHolderInput(`pessoa_juridica.socios.${index}.renda`, formatMoneyInputValue(socio.renda || ""), "Renda do Cliente", { money: true })}
        </div>
      </article>
    `).join("")}
  `;
}

function renderClientProfileTitulares(profile = {}) {
  const data = normalizeClientTitulares(profile);
  const grid = document.getElementById("clientProfileTitularesGrid");
  if (!grid) return;
  const selector = document.getElementById("clientProfileTipoContratacao");
  if (selector) selector.value = data.tipo_contratacao;
  if (data.tipo_contratacao === "pj") {
    grid.innerHTML = `
      <div class="profile-holder-title">Dados da empresa e socios</div>
      <div class="profile-holder-group">
        <div class="profile-holder-band">pessoa juridica</div>
        <div class="profile-holder-list">${renderPessoaJuridicaCards(data)}</div>
      </div>
    `;
    return;
  }
  const count = CLIENT_CONTRACTING_MODES[data.tipo_contratacao]?.pfCount || 1;
  grid.innerHTML = `
    <div class="profile-holder-title">Dados das pessoas</div>
    <div class="profile-holder-group">
      <div class="profile-holder-band">pessoa fisica</div>
      <div class="profile-holder-list">${data.pessoas_fisicas.slice(0, count).map(renderPessoaFisicaCard).join("")}</div>
    </div>
  `;
}

function ensureClientProfileHoldersRendered() {
  const grid = document.getElementById("clientProfileTitularesGrid");
  if (!grid || grid.children.length) return;
  renderClientProfileTitulares({
    tipo_contratacao: document.getElementById("clientProfileTipoContratacao")?.value || "pf_individual",
  });
}

function setNestedValue(target, path, value) {
  const parts = path.split(".");
  let cursor = target;
  for (let index = 0; index < parts.length - 1; index += 1) {
    const part = parts[index];
    const next = parts[index + 1];
    if (cursor[part] === undefined) cursor[part] = Number.isInteger(Number(next)) ? [] : {};
    cursor = cursor[part];
  }
  cursor[parts[parts.length - 1]] = value;
}

function collectClientTitularesFromForm() {
  const tipo = document.getElementById("clientProfileTipoContratacao")?.value || "pf_individual";
  const data = normalizeClientTitulares({ tipo_contratacao: tipo });
  document.querySelectorAll("[data-holder-field]").forEach((input) => {
    const field = input.dataset.holderField;
    const value = input.dataset.money ? toNumber(input.value) : String(input.value || "").trim();
    setNestedValue(data, field, value);
  });
  data.tipo_contratacao = tipo;
  return data;
}

function summarizeClientTitulares(titulares) {
  if (titulares.tipo_contratacao === "pj") {
    const empresa = titulares.pessoa_juridica.empresa;
    const socios = titulares.pessoa_juridica.socios.filter((socio) => socio.nome || socio.nascimento || Number(socio.lance_recursos_proprios || 0) > 0 || Number(socio.renda || 0) > 0);
    const rendaSocios = socios.reduce((sum, socio) => sum + Number(socio.renda || 0), 0);
    const lanceRecursosProprios = socios.reduce((sum, socio) => sum + Number(socio.lance_recursos_proprios || 0), 0);
    const faturamento = Number(empresa.faturamento_mensal || 0);
    return {
      nome: empresa.nome || "Empresa titular",
      nome_conjuge: "",
      data_nascimento: socios[0]?.nascimento || "",
      data_nascimento_conjuge: "",
      fgts_titular: 0,
      fgts_conjuge: 0,
      fgts: 0,
      lance_recursos_proprios: lanceRecursosProprios,
      renda_titular: faturamento + rendaSocios,
      renda_conjuge: 0,
      renda_total: faturamento + rendaSocios,
      resumo_label: empresa.nome || "Pessoa juridica",
      titulares_count: socios.length + (empresa.nome ? 1 : 0),
    };
  }
  const pessoas = titulares.pessoas_fisicas.filter((person) => person.nome || person.nascimento || Number(person.lance_fgts || 0) > 0 || Number(person.lance_recursos_proprios || 0) > 0 || Number(person.renda || 0) > 0);
  const fgts = pessoas.reduce((sum, person) => sum + Number(person.lance_fgts || 0), 0);
  const lanceRecursosProprios = pessoas.reduce((sum, person) => sum + Number(person.lance_recursos_proprios || 0), 0);
  const renda = pessoas.reduce((sum, person) => sum + Number(person.renda || 0), 0);
  return {
    nome: pessoas[0]?.nome || "",
    nome_conjuge: pessoas[1]?.nome || "",
    data_nascimento: pessoas[0]?.nascimento || "",
    data_nascimento_conjuge: pessoas[1]?.nascimento || "",
    fgts_titular: fgts,
    fgts_conjuge: 0,
    fgts,
    lance_recursos_proprios: lanceRecursosProprios,
    renda_titular: renda,
    renda_conjuge: 0,
    renda_total: renda,
    resumo_label: pessoas.map((person) => person.nome).filter(Boolean).join(" + ") || "Pessoa fisica",
    titulares_count: pessoas.length,
  };
}

function calculateAgeFromDateText(value) {
  const text = String(value || "").trim();
  if (!text) return null;
  const parts = text.includes("/") ? text.split("/").map(Number) : text.split("-").map(Number).reverse();
  if (parts.length !== 3 || parts.some((part) => !Number.isFinite(part))) return null;
  const [day, month, year] = parts;
  const birthDate = new Date(year, month - 1, day);
  if (birthDate.getFullYear() !== year || birthDate.getMonth() !== month - 1 || birthDate.getDate() !== day) return null;
  const today = new Date();
  let age = today.getFullYear() - year;
  const birthdayPending = today.getMonth() < month - 1 || (today.getMonth() === month - 1 && today.getDate() < day);
  if (birthdayPending) age -= 1;
  return age >= 0 ? age : null;
}

function preliminaryAgeSummary(people) {
  const ages = people.map((person) => calculateAgeFromDateText(person.nascimento)).filter((age) => age !== null);
  if (!ages.length) {
    return {
      ok: false,
      maiorIdade: null,
      label: "Idade nao validada",
    };
  }
  const hasMinor = ages.some((age) => age < 18);
  const oldest = Math.max(...ages);
  return {
    ok: !hasMinor,
    maiorIdade: oldest,
    label: hasMinor ? "menoridade detectada - inviavel" : `Maioridade confirmada - maior idade ${oldest} anos`,
  };
}

function preliminaryDecision(ok) {
  return ok ? "sem embutido" : "sim embutido";
}

function approvalStatusLabel(ok) {
  return ok ? "aprovado" : "reprovado";
}

function adminRuleTextToBool(value, defaultValue = true) {
  const normalized = normalizeText(value || "");
  if (!normalized) return defaultValue;
  if (normalized.startsWith("sim")) return true;
  if (normalized.startsWith("nao")) return false;
  return defaultValue;
}

function adminRuleBoolText(value, defaultValue = true) {
  return (value === undefined ? defaultValue : value) === false ? "Nao" : "Sim";
}

function administratorRuleBoolean(rule, key, defaultValue = true) {
  if (!rule || rule[key] === undefined || rule[key] === null || rule[key] === "") return defaultValue;
  return rule[key] !== false;
}

function rulePercentValue(rule, key) {
  const value = rule[key];
  if (typeof value === "number") return value > 1 ? value / 100 : value;
  return inputToPercentFromValue(value);
}

function administratorRuleCommitment(rule, key, defaultValue) {
  const percent = rulePercentValue(rule || {}, key);
  return percent > 0 ? percent : defaultValue;
}

function investorPreferenceNumber(value, isPercent = false) {
  if (value === null || value === undefined || value === "") return null;
  const normalized = String(value).replace("%", "").replace(/\s/g, "").replace(/\./g, "").replace(",", ".");
  const number = Number(normalized);
  if (!Number.isFinite(number)) return null;
  return isPercent || String(value).includes("%") ? (number > 1 ? number / 100 : number) : number;
}

function formatInvestorPreferenceValue(flag, value) {
  const number = investorPreferenceNumber(value, flag === "maior_lance_embutido");
  if (number === null) return "-";
  if (["menor_taxa_total", "menor_taxa_ano", "maior_lance_embutido"].includes(flag)) return formatPercent(number);
  if (flag === "maior_prazo_remanescente") return `${number} meses`;
  if (flag === "maior_media_contemplacoes") return `${number.toLocaleString("pt-BR", { maximumFractionDigits: 2 })} contemplações`;
  return formatMoney(number);
}

function applyInvestorPreferences(items, selectedFlags) {
  return items;
  const definitions = {
    menor_taxa_total: { field: "taxa_total", direction: "min", label: "Menor Taxa Total" },
    menor_taxa_ano: { field: "taxa_ano", direction: "min", label: "Menor Taxa Ano" },
    maior_parcela_reduzida: { field: "parcela_reduzida", direction: "max", label: "Maior Parcela Reduzida" },
    maior_prazo_remanescente: { field: "prazo_remanescente", direction: "max", label: "Maior Prazo Remanescente" },
    maior_lance_embutido: { field: "lance_embutido", direction: "max", label: "Maior Lance Embutido" },
    maior_media_contemplacoes: { field: "media_contemplacoes", direction: "max", label: "Maior Média de Contemplações", value: (item) => motor360QuotaCapacity(item)?.media_contemplacoes },
  };
  const scores = new Map(items.map((item) => [item, {}]));
  selectedFlags.forEach((flag) => {
    const definition = definitions[flag];
    const values = items.map((item) => investorPreferenceNumber(definition.value ? definition.value(item) : item[definition.field], flag === "maior_lance_embutido"));
    const valid = values.filter((value) => value !== null);
    const min = valid.length ? Math.min(...valid) : null;
    const max = valid.length ? Math.max(...valid) : null;
    items.forEach((item, index) => {
      const value = values[index];
      let score = 0;
      if (value !== null && min !== null && max !== null && max !== min) {
        score = definition.direction === "min" ? (max - value) / (max - min) : (value - min) / (max - min);
      }
      scores.get(item)[flag] = score;
    });
  });
  return items.map((item) => {
    const itemScores = scores.get(item);
    const scoreValues = selectedFlags.map((flag) => itemScores[flag]);
    const highlights = selectedFlags
      .filter((flag) => itemScores[flag] >= 0.999999)
      .map((flag) => {
        const definition = definitions[flag];
        const value = definition.value ? definition.value(item) : item[definition.field];
        return `${definition.label}: ${formatInvestorPreferenceValue(flag, value)}`;
      });
    return {
      ...item,
      indice_preferencia: scoreValues.length ? Math.round((scoreValues.reduce((sum, value) => sum + value, 0) / scoreValues.length) * 10000) / 100 : null,
      destaques_preferencia: highlights,
    };
  }).sort((a, b) => (
    (b.indice_preferencia ?? 0) - (a.indice_preferencia ?? 0)
    || (a.desvio_percentual === null ? 1 : 0) - (b.desvio_percentual === null ? 1 : 0)
    || (a.desvio_percentual ?? 0) - (b.desvio_percentual ?? 0)
    || (a.parcela_inicial ?? Number.POSITIVE_INFINITY) - (b.parcela_inicial ?? Number.POSITIVE_INFINITY)
    || (a.taxa_total ?? Number.POSITIVE_INFINITY) - (b.taxa_total ?? Number.POSITIVE_INFINITY)
    || String(a.grupo || "").localeCompare(String(b.grupo || ""), "pt-BR", { numeric: true })
  )).map((item, index) => ({ ...item, ranking: index + 1 }));
}

function renderCreditScenarioCell(item) {
  if (Array.isArray(item.cenarios)) {
    return `<div class="credit-scenario-cell">${item.cenarios.map((scenario) => {
      const title = scenario.id === "with_embedded"
        ? "Crédito contratado com lance embutido"
        : "Crédito contratado sem lance embutido";
      return `<div class="credit-scenario-block"><strong>${title}</strong><span>${formatMoney(scenario.credito_contratado)} - ${scenario.credit_compatible ? "OK" : "não atende"}</span><small>Lance do cliente: ${formatMoney(scenario.lance_cliente_total)} (${formatPercent(scenario.percentual_lance_cliente)}) | Lance embutido: ${formatMoney(scenario.lance_embutido)} | Lance total: ${formatMoney(scenario.lance_total_cenario)} | Saldo devedor: ${formatMoney(scenario.saldo_devedor)} | Prazo após lance: ${scenario.term_compatible === null ? "não analisado" : scenario.term_compatible ? "compatível" : "não compatível"}</small></div>`;
    }).join("")}</div>`;
  }
  const percent = item.percentual_lance_embutido;
  const withoutStatus = item.compativel_sem_embutido ? "OK" : "nao atende";
  const withStatus = item.compativel_com_embutido ? "OK" : "nao atende";
  const withEmbedded = percent === null || percent === undefined
    ? "Crédito contratado com lance embutido: indisponível"
    : `Crédito contratado com lance embutido (${formatPercent(percent)}): ${formatMoney(item.credito_necessario_com_embutido)} - ${withStatus}`;
  const withoutBalance = `Saldo devedor sem lance embutido: ${formatMoney(item.saldo_devedor_sem_embutido)}`;
  const withBalance = item.saldo_devedor_com_embutido === null || item.saldo_devedor_com_embutido === undefined
    ? "Saldo devedor com lance embutido: indisponível"
    : `Saldo devedor com lance embutido: ${formatMoney(item.saldo_devedor_com_embutido)}`;
  return `<div class="credit-scenario-cell"><div class="credit-scenario-block"><strong>Crédito contratado sem lance embutido</strong><span>${formatMoney(item.credito_necessario_sem_embutido)} - ${withoutStatus}</span><small>${withoutBalance}</small></div><div class="credit-scenario-block"><strong>${withEmbedded}</strong><small>${withBalance}</small></div></div>`;
}

function renderContemplationProfilesCell(item) {
  const scenarios = Array.isArray(item.cenarios) ? item.cenarios : [];
  const byId = Object.fromEntries(scenarios.map((scenario) => [scenario.id, scenario]));
  const profiles = byId.without_embedded?.perfis_contemplacao || byId.with_embedded?.perfis_contemplacao || [];
  if (!profiles.length) return "-";
  const scenarioValue = (scenario, profileId) => {
    const profile = (scenario?.perfis_contemplacao || []).find((item) => item.id === profileId);
    if (!profile || profile.percentual_referencia === null || profile.percentual_referencia === undefined) {
      return `<span class="motor360-profile-value is-empty">Não informado</span>`;
    }
    const status = profile.atinge_perfil ? "Atinge" : `Faltam ${formatMoney(profile.falta_para_ideal)}`;
    return `<span class="motor360-profile-value ${profile.atinge_perfil ? "is-hit" : "is-gap"}"><b>${formatPercent(profile.percentual_referencia)}</b><small>${status}</small></span>`;
  };
  return `<div class="motor360-profile-cell"><div class="motor360-profile-head"><span>Perfil</span><span>Sem embutido</span><span>Com embutido</span></div>${profiles.map((profile) => `<div class="motor360-profile-row"><strong>${escapeHtml(profile.label)}</strong>${scenarioValue(byId.without_embedded, profile.id)}${scenarioValue(byId.with_embedded, profile.id)}</div>`).join("")}<div class="motor360-profile-client-bid"><span>Lance ofertado</span><b>${formatMoney(byId.without_embedded?.lance_cliente_total ?? byId.with_embedded?.lance_cliente_total)}</b></div></div>`;
}

function motor360QuotaCapacity(item) {
  const selected = item?.capacidade_contemplacoes_selecionada;
  if (selected) return selected;
  const capacities = Object.values(item?.capacidade_contemplacoes || {});
  return capacities.find((capacity) => capacity?.perfil === item?.best_contemplation_strategy) || null;
}

function motor360HistoricalAverages(item) {
  const capacities = item?.capacidade_contemplacoes || {};
  const formatAverage = (strategy) => {
    const value = Number(capacities[strategy]?.media_contemplacoes);
    return Number.isFinite(value)
      ? new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 }).format(value)
      : "-";
  };
  return `<div class="motor360-history-averages" aria-label="Média de contemplações"><strong>Média de contemplações:</strong><span>Urgente (média 3m): ${formatAverage("urgent")}</span><span>Rápido (média 6m): ${formatAverage("fast")}</span><span>Moderado (média 12m): ${formatAverage("moderate")}</span></div>`;
}

function motor360HistoryTrigger(item) {
  const groupId = escapeHtml(String(item.grupo || item.grupo_id || ""));
  return `<button type="button" class="motor360-history-trigger" data-motor360-history-group="${groupId}" aria-label="Ver histórico dos últimos 12 meses do grupo ${groupId}" title="Histórico dos últimos 12 meses">i</button>`;
}

function motor360GroupAnchorId(groupId) {
  const normalized = String(groupId ?? "").trim().replace(/[^a-zA-Z0-9_-]+/g, "-");
  return `motor360-group-${normalized || "unknown"}`;
}

function focusMotor360Group(anchorId) {
  const target = document.getElementById(anchorId);
  if (!target) return;
  target.scrollIntoView({ behavior: "smooth", block: "start" });
  target.classList.remove("motor360-group--focus");
  void target.offsetWidth;
  target.classList.add("motor360-group--focus");
  window.setTimeout(() => target.classList.remove("motor360-group--focus"), 1800);
}

const motor360GroupCardCache = new Map();
function renderMotor360GroupCardUncached(item) {
  const scenarios = Array.isArray(item.cenarios) ? item.cenarios : [];
  const byId = Object.fromEntries(scenarios.map((scenario) => [scenario.id, scenario]));
  const profiles = item.composition_candidate
    ? (byId.without_embedded?.composition_totals?.perfis_contemplacao || byId.with_embedded?.composition_totals?.perfis_contemplacao || byId.without_embedded?.perfis_contemplacao || byId.with_embedded?.perfis_contemplacao || [])
    : (byId.without_embedded?.perfis_contemplacao || byId.with_embedded?.perfis_contemplacao || []);
  const requestedPreference = investorState.result?.preferencia_declarada;
  const objectiveCompatible = !requestedPreference || (item.compatible_contemplation_strategies || []).includes(requestedPreference);
  const hasCompleteScenario = scenarios.some((scenario) => (scenario.eligible === true || (scenario.credit_compatible === true && scenario.term_compatible === true && scenario.income_compatible !== false)) && scenario.credito_contratado != null && scenario.parcela_inicial != null && item.prazo_restante != null && item.prazo_restante !== "");
  const status = item.matrix_approved && hasCompleteScenario ? "Aprovado no perfil de contemplação" : item.alerts?.length ? formatMotor360Reason(item.alerts[0]) : objectiveCompatible ? "Indicador compatível" : "Requer análise";
  const groupId = String(item.grupo || item.grupo_id || "");
  const groupKey = motor360GroupKey(item);
  const auditId = escapeHtml(groupKey);
  const anchorId = motor360GroupAnchorId(groupId);
  const selected = investorState.selectedGroupIds.has(groupKey);
  const quotaCount = selected ? Math.min(50, Math.max(1, Number(investorState.quotaCounts.get(groupKey) || 1))) : 1;
  const selectedCompositionItems = selected ? selectedMotor360Items() : [];
  const compositionQuotas = selectedCompositionItems.reduce((total, entry) => total + quotaCountFor(entry), 0);
  const desiredCompositionCredit = Number(motor360ClientProfile().credito_liquido_desejado || 0);
  const quotaCapacity = motor360QuotaCapacity(item);
  const quotaLimit = Number.isFinite(Number(quotaCapacity?.limite_cotas)) ? Number(quotaCapacity.limite_cotas) : null;
  const quotaExceeded = selected && quotaLimit !== null && quotaCount > quotaLimit;
  const scaleMoney = (value) => value === null || value === undefined ? value : Number(value) * quotaCount;
  const compositionMetrics = (scenario) => selected && scenario && compositionQuotas > 0 && desiredCompositionCredit > 0
    ? selectedCompositionScenarioMetrics(selectedCompositionItems, scenario.id, desiredCompositionCredit)
    : null;
  const quotaControl = selected ? `<div class="motor360-quota-area ${quotaExceeded ? "is-warning" : ""}"><div class="motor360-quota-control"><span>Cotas</span><input class="motor360-quota-input" type="number" min="1" max="50" value="${quotaCount}" data-quota-action="input" data-group-id="${auditId}" aria-label="Quantidade de cotas do grupo ${auditId}"></div>${quotaExceeded ? `<div class="motor360-quota-warning" role="alert"><strong>Acima da média histórica</strong><span>${quotaCount} cotas excedem o limite de ${quotaLimit} para este perfil.</span></div>` : ""}</div>` : "";
  const selectedProfileId = motor360ClientProfileId();
  const focusProfileId = motor360FocusedProfileId();
  const focusProfileLabel = { conservative: "Conservador", moderate: "Moderado", aggressive: "Agressivo", super_aggressive: "Superagressivo", investor: "Investidor" }[focusProfileId] || "Todos os perfis";
  const compositionMinimums = scenarios
    .map((scenario) => ({ id: scenario.id, quotas: minimumQuotasFor(item, scenario.id) }))
    .filter((entry) => entry.quotas > 1);
  const compositionDataComplete = scenarios.some((scenario) =>
    scenario.creation_status === "created"
    && scenario.data_complete === true
    && scenario.credito_contratado != null
    && scenario.parcela_inicial != null
    && item.prazo_restante != null
  );
  const possibleComposition = !selected
    && item.requires_composition === true
    && (compositionDataComplete || (item.composition_candidate === true && scenarios.some((scenario) => scenario.eligible === true)))
    && compositionMinimums.length > 0;
  const configuredScenario = investorState.selectedGroupScenario;
  const visibleMinimum = (configuredScenario === "with_embedded"
    ? compositionMinimums.find((entry) => entry.id === "with_embedded")?.quotas
    : configuredScenario === "without_embedded"
      ? compositionMinimums.find((entry) => entry.id === "without_embedded")?.quotas
      : null) ?? Math.min(...compositionMinimums.map((entry) => entry.quotas));
  const minimumDetails = compositionMinimums
    .map((entry) => `${entry.quotas} cotas ${entry.id === "with_embedded" ? "com" : "sem"} embutido`)
    .join("; ");
  const scenarioRequirementStatus = (scenario) => {
    if (item.composition_candidate === true && !selected) {
      const minimum = Number(scenario.cotas_minimas || minimumQuotasFor(item, scenario.id) || 0);
      const ok = scenario.eligible === true;
      const profile = (scenario.composition_totals?.perfis_contemplacao || []).find((entry) => entry.id === selectedProfileId);
      const profilePending = ok && scenario.profile_compatible_in_composition === false;
      const profileGap = profilePending ? Math.max(0, Number(profile?.falta_para_ideal || 0)) : 0;
      return {
        ok,
        profilePending,
        failed: ok ? [] : ["Composição"],
        title: ok
          ? `${profilePending ? `Crédito e parcela cabem em composição com ${minimum} cotas, mas o lance não atinge o perfil selecionado${profileGap > 0 ? `; faltam ${formatMoney(profileGap)}` : ""}.` : `Esta opção é viável em composição com no mínimo ${minimum} cotas.`} Isso não é aprovação de uma cota isolada.`
          : "Esta composição não atende simultaneamente aos limites calculados de crédito, parcela/renda ou perfil.",
      };
    }
    const composed = compositionMetrics(scenario);
    if (composed) {
      const client = motor360ClientProfile();
      const assessment = selectedCompositionAssessment(composed, client, focusProfileId || allocationProfileId());
      const parcelWarning = assessment.parcelWarning ? `${assessment.parcelWarning} (alerta)` : "";
      return { ok: assessment.ok, failed: assessment.failures, parcelWarning, title: `${assessment.failures.length ? `Composição requer ajuste: ${assessment.failures.join("; ")}.` : "Composição atende aos critérios de crédito, parcela máxima e lance."}${parcelWarning ? ` ${parcelWarning}.` : ""}` };
    }
    const profileOk = !selectedProfileId || (scenario.perfis_contemplacao || []).some((profile) => profile.id === selectedProfileId && profileMeetsBid(item, scenario, profile));
    const requirements = [
      ["Crédito", scenario.credit_compatible === true],
      ["Prazo/renda", scenario.term_compatible !== false && scenario.income_compatible !== false],
      ["Perfil", profileOk],
    ];
    const failed = requirements.filter(([, ok]) => !ok).map(([label]) => label);
    const ok = failed.length === 0;
    return { ok, failed, title: ok ? "Todos os requisitos do cenário foram atendidos." : `Não atende: ${failed.join(", ")}.` };
  };
  const profileDisplayLabels = { conservative: "Conservador (24 meses)", moderate: "Moderado (12 meses)", aggressive: "Agressivo / Rápido (6 meses)", super_aggressive: "Super agressivo / Urgente (3 meses)" };
  const renderScenarioProfiles = (scenario) => {
    const profileRows = item.composition_candidate
      ? (scenario.composition_totals?.perfis_contemplacao || scenario.perfis_contemplacao || [])
      : (scenario.perfis_contemplacao || []);
    const values = profiles.map((profile) => {
      const value = profileRows.find((entry) => entry.id === profile.id);
      if (!value || value.percentual_referencia === null || value.percentual_referencia === undefined) return `<div class="motor360-profile-card-value is-empty"><small>Não informado</small></div>`;
      const idealLabel = scenario.id === "with_embedded" ? "Lance ideal em recursos do cliente" : "Lance ideal";
      const metrics = compositionMetrics(scenario);
      const metricEntry = metrics?.entries.find((entry) => motor360GroupKey(entry.item) === groupKey);
      const embeddedNote = scenario.id === "with_embedded" ? `<small>Embutido considerado: ${formatMoney(metricEntry?.embedded ?? scaleMoney(value.lance_embutido))}</small>` : "";
      const totalIdeal = metrics ? metricEntry?.profiles[value.id]?.ideal || 0 : motor360CompositionIdealBid(item, scenario, value.id);
      const available = metrics ? metricEntry?.profiles[value.id]?.available || 0 : item.composition_candidate
        ? Number(scenario.composition_totals?.lance_cliente_total ?? scenario.lance_cliente_total ?? 0)
        : allocatedClientBidFor(item, scenario, value.id);
      const meetsBid = totalIdeal <= 0 || available >= totalIdeal;
      const bidGap = { gap: Math.max(0, totalIdeal - available) };
      const bidStatusLabel = totalIdeal <= 0 ? "Sem lance próprio necessário" : meetsBid ? "Atinge o perfil" : `Faltam ${formatMoney(bidGap.gap)}`;
      const focused = profile.id === focusProfileId;
      return `<div class="motor360-profile-card-value ${meetsBid ? "is-hit" : "is-gap"} ${focused ? "is-focused" : ""}" ${focused ? 'aria-current="true"' : ""}><small>${escapeHtml(profileDisplayLabels[profile.id] || profile.label)}${focused ? '<span class="motor360-profile-focus-tag">Em foco</span>' : ""}</small><b>${formatPercent(value.percentual_referencia)}</b><span>${bidStatusLabel}</span><em>${idealLabel}: ${formatMoney(totalIdeal)}</em>${embeddedNote}</div>`;
    }).join("");
    const scenarioLabel = scenario.id === "with_embedded" ? "Com lance embutido" : "Sem lance embutido";
    const compositionTotals = item.composition_candidate ? scenario.composition_totals : null;
    const referenceBid = compositionTotals?.lance_cliente_total ?? scenario.lance_cliente_total;
    return `<section class="motor360-scenario-profiles"><div class="motor360-profile-section-title"><h4>Perfis · ${scenarioLabel}</h4><small>Foco: ${escapeHtml(focusProfileLabel)} · Referência: ${formatMoney(referenceBid)}</small></div><div class="motor360-profile-card-values">${values || "<p class=\"motor360-empty-inline\">Perfis não informados.</p>"}</div></section>`;
  };
  const scaledScenarioCards = scenarios.map((scenario) => {
    const title = (scenario.id === "with_embedded" ? "Crédito contratado com lance embutido" : "Crédito contratado sem lance embutido") + (minimumQuotasFor(item, scenario.id) > 1 ? ` · Composição: mínimo de ${minimumQuotasFor(item, scenario.id)} cotas` : "");
    const requirement = scenarioRequirementStatus(scenario);
    const compositionQuotaLabel = item.composition_candidate === true ? ` · mínimo de ${Number(scenario.cotas_minimas || minimumQuotasFor(item, scenario.id))} cotas` : "";
    const statusLabel = item.composition_candidate === true
      ? requirement.ok ? requirement.profilePending ? `Possível em composição · perfil pendente${compositionQuotaLabel}` : `Viável em composição${compositionQuotaLabel}` : "Composição não viável neste cenário"
      : requirement.ok ? `Requisitos atendidos${requirement.parcelWarning ? ` · ${requirement.parcelWarning}` : ""}` : "Requisitos não atendidos";
    const info = `<span class="motor360-requirement-info" title="${escapeHtml(requirement.title)}" aria-label="${escapeHtml(requirement.title)}" tabindex="0">i</span>`;
    const metrics = compositionMetrics(scenario);
    const metric = (field) => metrics ? metrics.entries.find((entry) => motor360GroupKey(entry.item) === groupKey)?.[field] : null;
    const aggregate = item.composition_candidate && !selected ? scenario.composition_totals : null;
    const cardCredit = metric("contractedCredit") ?? aggregate?.credito_contratado ?? scaleMoney(scenario.credito_contratado);
    const cardInstallment = metric("installment") ?? aggregate?.parcela_inicial ?? scaleMoney(scenario.parcela_inicial);
    const cardAfter = metric("installmentAfter") ?? aggregate?.parcela_pos_contemplacao ?? scaleMoney(scenario.parcela_pos_contemplacao);
    const cardBalance = metric("balance") ?? aggregate?.saldo_devedor ?? scaleMoney(scenario.saldo_devedor);
    const metricEntry = metrics?.entries.find((entry) => motor360GroupKey(entry.item) === groupKey);
    const cardClientBid = metrics ? clientResourceTotal() : Number(aggregate?.lance_cliente_total ?? scenario.lance_cliente_total ?? 0);
    const cardEmbedded = metrics?.embedded ?? aggregate?.lance_embutido ?? scaleMoney(scenario.lance_embutido);
    const cardScenarioBid = metrics ? cardClientBid + cardEmbedded : Number(aggregate?.lance_total_cenario ?? scaleMoney(scenario.lance_total_cenario));
    const cardLabel = metrics ? `<small class="motor360-scenario-note">Crédito acumulado: ${formatMoney(metrics.credit)} de ${formatMoney(desiredCompositionCredit)} · ${metrics.shortfall > 0 ? `Faltam ${formatMoney(metrics.shortfall)}` : "Crédito atendido"}</small>` : "";
    const clientBidPercent = metrics?.contractedCredit > 0
      ? cardClientBid / metrics.contractedCredit
      : aggregate?.credito_contratado > 0 ? cardClientBid / aggregate.credito_contratado : Number(scenario.percentual_lance_cliente || 0);
    const scenarioBidPercent = metrics?.contractedCredit > 0
      ? cardScenarioBid / metrics.contractedCredit
      : aggregate?.credito_contratado > 0 ? cardScenarioBid / aggregate.credito_contratado : Number(scenario.percentual_lance_efetivo || 0);
    const showPortfolioLabels = Boolean((metrics && metrics.totalQuotas > 1) || (aggregate && Number(aggregate.cotas_minimas) > 1));
    const compositionCreditGuidance = possibleComposition
      && minimumQuotasFor(item, scenario.id) > 1
      && requirement.failed.includes("Crédito")
      ? `1 cota não cobre o crédito desejado · mínimo de ${minimumQuotasFor(item, scenario.id)} cotas`
      : "";
    const readableFailures = requirement.failed.map((reason) => {
      if (reason !== "Crédito") return reason;
      const rawMinimum = item.credito_minimo ?? scenario.credito_minimo;
      const rawMaximum = item.credito_maximo ?? scenario.credito_maximo;
      const rawContractedCredit = scenario.credito_contratado;
      const groupMinimum = Number(rawMinimum);
      const groupMaximum = Number(rawMaximum);
      const contractedCredit = Number(rawContractedCredit);
      const hasCreditRange = rawMinimum != null && rawMaximum != null && rawContractedCredit != null
        && Number.isFinite(groupMinimum) && Number.isFinite(groupMaximum) && Number.isFinite(contractedCredit);
      return hasCreditRange
        ? "Crédito fora da faixa do grupo"
        : "Dados de crédito insuficientes para avaliar";
    });
    const failureMessage = compositionCreditGuidance || readableFailures.join(" · ") || requirement.title;
    const visibleFailure = !requirement.ok ? `<p class="motor360-scenario-failure" role="status">${escapeHtml(failureMessage)}</p>` : "";
    return `<article class="motor360-scenario-card ${requirement.ok ? "is-compatible" : "is-incompatible"}"><div class="motor360-scenario-title"><strong>${title}</strong><span>${statusLabel} ${info}</span></div>${visibleFailure}<div class="motor360-scenario-grid"><div><small>Crédito contratado${showPortfolioLabels ? " (composição do grupo)" : ""}</small><b>${formatMoney(cardCredit)}</b></div><div><small>${showPortfolioLabels ? "Lance do cliente na composição" : "Lance do cliente"}</small><b>${formatMoney(cardClientBid)} <em>(${formatPercent(clientBidPercent)})</em></b></div><div><small>${showPortfolioLabels ? "Lance embutido na composição" : "Lance embutido"}</small><b>${formatMoney(cardEmbedded)}</b></div><div><small>${showPortfolioLabels ? "Lance total da composição" : "Lance total do cenário"}</small><b>${formatMoney(cardScenarioBid)} <em>(${formatPercent(scenarioBidPercent)})</em></b></div><div><small>Saldo devedor</small><b>${formatMoney(cardBalance)}</b></div><div><small>Parcela inicial</small><b>${formatMoney(cardInstallment)}</b></div><div><small>Parcela pós-contemplação</small><b>${cardAfter == null ? "Não calculada" : formatMoney(cardAfter)}</b></div></div>${cardLabel}<small class="motor360-scenario-note">Prazo após lance: ${scenario.term_compatible === null ? "não analisado" : scenario.term_compatible ? "compatível" : "requer análise"}</small>${renderScenarioProfiles(scenario)}</article>`;
  }).join("");
  const selectedScenarioIds = selectedScenarioIdsForGroup(groupKey);
  const compositionViable = selected && [...selectedScenarioIds].some((id) => { const scenario = scenarios.find((entry) => entry.id === id); return scenario && scenarioRequirementStatus(scenario).ok; });
  const displayStatus = selected
    ? selectedScenarioIds.size
      ? compositionViable
        ? compositionQuotas > 1 ? "Viável em composição" : "Aprovado"
        : "Requer ajuste"
      : "Escolha um cenário"
    : possibleComposition
      ? `Possível em composição · mín. ${visibleMinimum} cotas`
      : status;
  const displayStatusTone = selected
    ? selectedScenarioIds.size
      ? compositionViable ? "approved" : "warning"
      : "neutral"
    : possibleComposition || status === "Indicador compatível" || status === "Requer análise"
      ? "neutral"
      : status === "Aprovado no perfil de contemplação" ? "approved" : "warning";
  const displayStatusDetail = selected && !selectedScenarioIds.size
    ? "Escolha um cenário para avaliar esta composição."
    : selected && selectedScenarioIds.size
    ? [...selectedScenarioIds].map((id) => { const scenario = scenarios.find((entry) => entry.id === id); return scenario ? scenarioRequirementStatus(scenario).title : ""; }).filter(Boolean).join(" · ")
    : possibleComposition
      ? `Opção viável somente em composição; não é aprovação de uma cota isolada. Mínimos por cenário: ${minimumDetails}.`
      : status;
  const bidSortLabel = investorState.selectedGroupSort === "bid" ? motor360BidSortLabel(item) : "";
  return `<article id="${anchorId}" class="motor360-group-card ${selected ? "is-selected" : ""}"><header class="motor360-group-card-header"><div class="motor360-group-identity"><span class="motor360-group-order">${escapeHtml(String(item.ranking || "-"))}</span><div><div class="motor360-group-title"><h3>Grupo ${escapeHtml(item.grupo || item.grupo_id || "-")}</h3>${motor360HistoryTrigger(item)}</div><p>${escapeHtml(item.administradora || "-")}</p>${motor360HistoricalAverages(item)}</div></div><div class="motor360-group-summary"><div><small>Data de Venc.</small><b>${escapeHtml(formatGroupDueDate(item.vencimento_parcela))}</b></div><div><small>Crédito máximo${selected && quotaCount > 1 ? " total" : ""}</small><b>${formatMoney(scaleMoney(item.credito_maximo))}</b></div><div><small>Prazo restante</small><b>${escapeHtml(String(item.prazo_restante ?? "-"))} meses</b></div><span class="motor360-group-status is-${displayStatusTone}" title="${escapeHtml(displayStatusDetail)}" aria-label="${escapeHtml(`${displayStatus}. ${displayStatusDetail}`)}">${escapeHtml(displayStatus)}</span><label class="motor360-group-select"><input type="checkbox" class="motor360-group-select-input" data-group-id="${auditId}" ${selected ? "checked" : ""}><span>Selecionar grupo</span></label>${quotaControl}<button type="button" class="btn btn-outline-secondary btn-sm motor360-group-audit-btn" data-group-id="${auditId}">Ver</button></div></header><section class="motor360-group-section"><h4>Cenários financeiros${selected && quotaCount > 1 ? ` · ${quotaCount} cotas` : ""}</h4><div class="motor360-scenario-list">${scaledScenarioCards}</div></section><div class="motor360-group-classification">Classificação: <strong>${escapeHtml(item.best_contemplation_strategy || "Não classificada")}</strong></div>${bidSortLabel ? `<p class="motor360-bid-sort-value" aria-label="${escapeHtml(bidSortLabel)}">${escapeHtml(bidSortLabel)}</p>` : ""}</article>`;
}

function renderMotor360GroupCard(item) {
  const compositionKey = [...investorState.selectedGroupIds].sort().map((id) => `${id}:${quotaCountFor(id)}:${[...selectedScenarioIdsForGroup(id)].sort().join(",")}`).join(";");
  const desiredCredit = Number(motor360ClientProfile().credito_liquido_desejado || 0);
  const key = `${motor360GroupKey(item)}|${investorState.selectedGroupProfile || "all"}|${investorState.selectedGroupScenario || "per_group"}|${investorState.selectedGroupSort || "original"}|${compositionKey}|${desiredCredit}`;
  if (!motor360GroupCardCache.has(key)) {
    if (motor360GroupCardCache.size >= 1500) {
      const oldestKey = motor360GroupCardCache.keys().next().value;
      if (oldestKey !== undefined) motor360GroupCardCache.delete(oldestKey);
    }
    motor360GroupCardCache.set(key, renderMotor360GroupCardUncached(item));
  }
  return motor360GroupCardCache.get(key);
}

function selectedMotor360Items() {
  const currentItems = new Map([
    ...(investorState.result?.final_items || investorState.result?.items || []),
  ].map((item) => [motor360GroupKey(item), item]));
  return [...investorState.selectedGroupIds].map((id) => {
    const item = currentItems.get(id) || investorState.selectedGroupData.get(id);
    return item ? { ...item, cenarios: selectedScenariosForItem(item) } : null;
  }).filter(Boolean);
}

function motor360FinalItems(result = investorState.result) {
  return result?.final_items || result?.items || [];
}

function motor360ClientProfile() {
  const resultClient = investorState.result?.cliente || {};
  const profile = collectClientProfile?.() || {};
  const merged = { ...profile, ...resultClient };
  return {
    ...merged,
    objetivo: merged.objetivo || profile.objetivo || "Não informado",
    credito_liquido_desejado: merged.credito_liquido_desejado ?? merged.credito_desejado ?? profile.credito_desejado,
    renda_total: merged.renda_total ?? profile.renda_total,
    parcela_maxima: merged.parcela_maxima ?? merged.parcela_limite ?? profile.parcela_limite,
    parcela_desejada: merged.parcela_desejada ?? merged.parcela_ideal ?? profile.parcela_desejada,
    fgts_total: merged.fgts_total ?? merged.fgts ?? profile.fgts_total ?? profile.fgts,
    lance_recursos_proprios: merged.lance_recursos_proprios ?? merged.lance_proprio ?? profile.lance_recursos_proprios ?? profile.lance_proprio,
    lance_cliente_total: merged.lance_cliente_total ?? merged.lance_total ?? profile.lance_cliente_total,
  };
}

function renderMotor360ClientProfileSummary(client = {}) {
  const ownResources = Number(client.lance_recursos_proprios ?? client.lance_proprio ?? 0);
  const fgts = Number(client.fgts_total ?? client.fgts ?? 0);
  const objective = client.objetivo || client.preferencia_declarada || "Não informado";
  const items = [
    ["Objetivo", objective],
    ["Crédito desejado", formatMoney(client.credito_liquido_desejado)],
    ["Renda total", formatMoney(client.renda_total)],
    ["Parcela máxima", formatMoney(client.parcela_maxima)],
    ["Parcela desejada", formatMoney(client.parcela_desejada)],
    ["Lance FGTS", formatMoney(fgts)],
    ["Lance recursos próprios", formatMoney(ownResources)],
    ["Lance total", formatMoney(client.lance_cliente_total ?? ownResources + fgts)],
  ];
  const hasData = items.some(([, value]) => value && value !== "R$ 0,00" && value !== "Não informado");
  if (!hasData) return "";
  return `<section class="motor360-client-profile-summary" aria-label="Resumo do perfil do cliente"><header><span>Referência do cliente</span><strong>Resumo do perfil</strong></header><div>${items.map(([label, value]) => `<article><small>${escapeHtml(label)}</small><b>${escapeHtml(String(value || "-"))}</b></article>`).join("")}</div></section>`;
}

function renderMotor360FloatingSelectionSummary() {
  const items = selectedMotor360Items();
  const minimizedClass = investorState.floatingSummaryMinimized ? " is-minimized" : "";
  const minimizeButton = `<button type="button" class="motor360-floating-minimize" data-floating-summary-toggle aria-expanded="${investorState.floatingSummaryMinimized ? "false" : "true"}" title="${investorState.floatingSummaryMinimized ? "Expandir composição" : "Minimizar composição"}">${investorState.floatingSummaryMinimized ? "+" : "−"}</button>`;
  if (!items.length) {
    return `<aside class="motor360-floating-summary is-empty${minimizedClass}" aria-live="polite"><div class="motor360-floating-summary-heading"><div><span>Composição atual</span><strong>Nenhum grupo selecionado</strong></div><div class="motor360-floating-heading-actions"><span class="motor360-floating-count">0</span>${minimizeButton}</div></div><p>Adicione grupos e cotas para acompanhar o atendimento ao crédito e à parcela do cliente.</p></aside>`;
  }
  const client = motor360ClientProfile();
  const desiredCredit = Number(client.credito_liquido_desejado || 0);
  const maximumInstallment = Number(client.parcela_maxima || 0);
  const entries = items.map((item) => {
    const groupId = String(item.grupo || item.grupo_id || "-");
    const quotas = quotaCountFor(item);
    return { item, quotas };
  });
  const totalQuotas = entries.reduce((sum, entry) => sum + entry.quotas, 0);
  const scenario = (scenarioId, label) => {
    const metrics = selectedCompositionScenarioMetrics(items, scenarioId, desiredCredit);
    if (!metrics.entries.length) return "";
    const credit = metrics.credit;
    const installment = metrics.installment;
    const balance = metrics.balance;
    const activeCompositionProfile = investorState.selectedGroupProfile && investorState.selectedGroupProfile !== "all" ? investorState.selectedGroupProfile : allocationProfileId();
    const assessment = selectedCompositionAssessment(metrics, client, activeCompositionProfile);
    const creditOk = desiredCredit > 0 && credit >= desiredCredit && metrics.creditCapacityOk;
    const viable = assessment.ok;
    const progress = desiredCredit > 0 ? Math.min(100, Math.max(0, credit / desiredCredit * 100)) : 0;
    const parcelNotice = assessment.parcelWarning ? ` · ${assessment.parcelWarning} (alerta)` : "";
    return `<section class="motor360-floating-scenario ${viable ? "is-ok" : "is-pending"}"><header><strong>${label}</strong><span>${viable ? "Viável" : "Requer ajuste"}</span></header><div class="motor360-floating-progress" aria-label="${progress.toFixed(0)}% do crédito desejado"><i style="width:${progress.toFixed(2)}%"></i></div><dl><div><dt>Crédito</dt><dd>${formatMoney(credit)} <small>de ${formatMoney(desiredCredit)}</small></dd></div><div><dt>Parcela</dt><dd>${formatMoney(installment)} <small>limite ${formatMoney(maximumInstallment)}</small></dd></div><div><dt>Saldo devedor</dt><dd>${formatMoney(balance)}</dd></div></dl><p>${assessment.failures.join(" · ") || "Crédito, parcela máxima e lance atendidos"}${parcelNotice}</p></section>`;
  };
  const selectedGroupLabels = items.map((item) => {
    const groupId = String(item.grupo || item.grupo_id || "-");
    const anchorId = motor360GroupAnchorId(groupId);
    const quotas = quotaCountFor(item);
    return `<button type="button" class="motor360-selected-group-label" data-selected-group-anchor="${escapeHtml(anchorId)}" title="Ir para o Grupo ${escapeHtml(groupId)}"><strong>Grupo ${escapeHtml(groupId)}</strong><small>${quotas} ${quotas === 1 ? "cota" : "cotas"}</small></button>`;
  }).join("");
  const currentComposition = selectedCompositionScenarioMetrics(items, "without_embedded", desiredCredit);
  return `<aside class="motor360-floating-summary${minimizedClass}" aria-live="polite"><div class="motor360-floating-summary-heading"><div><span>Composição atual</span><strong>${items.length} grupo(s) · ${totalQuotas} cota(s)</strong></div><div class="motor360-floating-heading-actions"><span class="motor360-floating-count">${totalQuotas}</span>${minimizeButton}</div></div><p class="motor360-composition-credit-summary">Crédito acumulado: ${formatMoney(currentComposition.credit)} de ${formatMoney(desiredCredit)} · Faltam ${formatMoney(currentComposition.shortfall)} · Total de cotas: ${totalQuotas}</p><div class="motor360-selected-group-labels" aria-label="Grupos selecionados">${selectedGroupLabels}</div>${renderMotor360ClientProfileSummary(client)}<div class="motor360-floating-scenarios">${scenario("without_embedded", "Sem embutido")}${scenario("with_embedded", "Com embutido")}</div><button class="btn btn-primary btn-sm motor360-floating-action" type="button" data-open-selected-groups-workspace>Analisar grupos selecionados</button></aside>`;
}

function renderMotor360FloatingSelectionSummaryIntoFold() {
  const host = document.getElementById("motor360FloatingSummary");
  if (!host) return;
  host.innerHTML = renderMotor360FloatingSelectionSummary();
  host.querySelector("[data-floating-summary-toggle]")?.addEventListener("click", openSelectedGroupsWorkspace);
  host.querySelector("[data-open-selected-groups-workspace]")?.addEventListener("click", openSelectedGroupsWorkspace);
  host.querySelectorAll("[data-selected-group-anchor]").forEach((button) => button.addEventListener("click", () => focusMotor360Group(button.dataset.selectedGroupAnchor)));
}

function openSelectedGroupsWorkspace() {
  const workspace = document.getElementById("selectedGroupsWorkspace");
  const body = document.getElementById("selectedGroupsWorkspaceBody");
  const results = document.getElementById("selectedGroupsResults");
  if (!workspace || !body || !results) return;
  const groupsWithoutScenario = [...investorState.selectedGroupIds].filter((groupId) => !selectedScenarioIdsForGroup(groupId).size);
  if (groupsWithoutScenario.length) {
    showToast("Para analisar, escolha pelo menos um cenário financeiro em cada grupo selecionado.", "warning");
    focusMotor360Group(motor360GroupAnchorId(groupsWithoutScenario[0].split("|").pop() || groupsWithoutScenario[0]));
    return;
  }
  const profileSummary = document.getElementById("selectedGroupsWorkspaceProfileSummary");
  if (profileSummary) profileSummary.innerHTML = renderMotor360ClientProfileSummary(motor360ClientProfile());
  const compositionSummary = document.getElementById("selectedGroupsWorkspaceCompositionSummary");
  if (compositionSummary) compositionSummary.textContent = `${investorState.selectedGroupIds.size} grupo(s) · ${[...investorState.selectedGroupIds].reduce((sum, id) => sum + quotaCountFor(id), 0)} cota(s)`;
  workspace.classList.remove("d-none");
  document.body.classList.add("selected-groups-workspace-open");
  renderSelectedGroupsScreen();
}

function closeSelectedGroupsWorkspace() {
  const workspace = document.getElementById("selectedGroupsWorkspace");
  if (!workspace) return;
  workspace.classList.add("d-none");
  document.body.classList.remove("selected-groups-workspace-open");
}

function renderSelectedGroupComparisonColumn(item, index) {
  const groupId = String(item.grupo || item.grupo_id || "-");
  const quotaCount = quotaCountFor(item);
  const scale = (value) => value === null || value === undefined ? value : Number(value) * quotaCount;
  const scenarios = Array.isArray(item.cenarios) ? item.cenarios : [];
  const byScenario = Object.fromEntries(scenarios.map((scenario) => [scenario.id, scenario]));
  let scenarioRows = ["without_embedded", "with_embedded"].map((scenarioId) => {
    const scenario = byScenario[scenarioId];
    if (!scenario) return "";
    const embedded = scenarioId === "with_embedded";
    return `<article class="selected-comparison-scenario"><div class="selected-comparison-scenario-title"><strong>${embedded ? "Com lance embutido" : "Sem lance embutido"}</strong><span>${scenario.credit_compatible ? "Crédito OK" : "Fora da faixa"}</span></div><dl><div><dt>Crédito líquido</dt><dd>${formatMoney(scale(scenario.credito_liquido_projetado ?? scenario.credito_contratado))}</dd></div><div><dt>Lance total</dt><dd>${item.composition_candidate ? "Rateado no resumo" : formatMoney(scenarioTotalBidFor(item, scenario))}</dd></div><div><dt>Saldo devedor</dt><dd>${formatMoney(scale(scenario.saldo_devedor))}</dd></div><div><dt>Parcela inicial</dt><dd>${formatMoney(scale(scenario.parcela_inicial))}</dd></div><div><dt>Parcela pós-contemplação</dt><dd>${item.composition_candidate || scenario.parcela_pos_contemplacao == null ? "Pendente da distribuição do lance" : formatMoney(scale(scenario.parcela_pos_contemplacao))}</dd></div></dl><small>Prazo após lance: ${item.composition_candidate ? "validado na composição" : scenario.term_compatible ? "compatível" : "não compatível"}</small></article>`;
  }).join("");
  scenarioRows = scenarioRows.replace(/<div><dt>Crédito líquido<\/dt><dd>.*?<\/dd><\/div>/g, "");
  const profiles = byScenario.without_embedded?.perfis_contemplacao || byScenario.with_embedded?.perfis_contemplacao || [];
  const historicalAverages = motor360HistoricalAverages(item);
  const groupFinancialInputs = motor360ScenarioSourceMetrics(item);
  const profileRows = profiles.map((profile) => {
    const values = ["without_embedded", "with_embedded"].map((scenarioId) => {
      const value = (byScenario[scenarioId]?.perfis_contemplacao || []).find((entry) => entry.id === profile.id);
      if (!value) return "";
      const meetsBid = profileMeetsBid(item, byScenario[scenarioId], value);
      const totalIdeal = Number(value.lance_ideal || 0) * quotaCount;
      const resultLabel = item.composition_candidate ? `Lance ideal ${formatMoney(totalIdeal)}` : meetsBid ? "Atinge o perfil" : `Faltam ${formatMoney(profileBidGap(item, byScenario[scenarioId], value).gap)}`;
      return `<div class="selected-comparison-profile-value ${item.composition_candidate ? "" : meetsBid ? "is-hit" : "is-gap"}"><small>${scenarioId === "with_embedded" ? "Com embutido" : "Sem embutido"}</small><b>${formatPercent(value.percentual_referencia)}</b><span>${resultLabel}</span></div>`;
    }).join("");
    return `<article class="selected-comparison-profile"><strong>${escapeHtml(profile.label)}</strong>${values}</article>`;
  }).join("");
  return `<article class="selected-comparison-column"><header><div class="selected-group-number">${index + 1}</div><div><h3>Grupo ${escapeHtml(groupId)}</h3><p>${escapeHtml(item.administradora || "-")} · ${quotaCount} ${quotaCount === 1 ? "cota" : "cotas"}</p></div></header><div class="selected-comparison-key-metrics"><span><small>Data de Venc.</small><b>${escapeHtml(formatGroupDueDate(item.vencimento_parcela))}</b></span><span><small>Crédito máximo</small><b>${formatMoney(scale(item.credito_maximo))}</b></span><span><small>Prazo restante</small><b>${escapeHtml(String(item.prazo_restante ?? "-"))} meses</b></span></div>${historicalAverages}<section class="selected-comparison-inputs"><h4>Premissas do grupo</h4>${groupFinancialInputs}</section><section><h4>Cenários financeiros</h4><div class="selected-comparison-scenarios">${scenarioRows}</div></section><section><h4>Perfis de contemplação</h4><div class="selected-comparison-profiles">${profileRows || "<p class=\"motor360-empty-inline\">Perfis não informados.</p>"}</div></section></article>`;
}

function selectedMotor360SnapshotItems() {
  const currentItems = new Map([
    ...(investorState.result?.final_items || investorState.result?.items || []),
  ].map((item) => [motor360GroupKey(item), item]));
  return [...investorState.selectedGroupIds].map((id) => {
    const item = currentItems.get(id) || investorState.selectedGroupData.get(id);
    if (!item) return null;
    return { ...item, cenarios: selectedScenariosForItem(item) };
  }).filter(Boolean);
}

function invalidateInvestorAnalysisForProfileChange() {
  investorAnalysisRequestId += 1;
  investorAnalysisController?.abort();
  investorAnalysisController = null;
  investorState.result = null;
  investorState.audit = null;
  investorState.selectedGroupIds.clear();
  investorState.selectedScenarioIds.clear();
  investorState.quotaCounts.clear();
  investorState.selectedGroupData.clear();
  persistMotor360Selection();
  setInvestorAnalysisState("empty");
  const selectedResults = document.getElementById("selectedGroupsResults");
  const selectedEmpty = document.getElementById("selectedGroupsEmpty");
  selectedResults?.classList.add("d-none");
  selectedEmpty?.classList.remove("d-none");
}

function renderSelectedGroupsOverview(items) {
  const metric = (label, value, note = "") => `<div class="selected-overview-kpi"><span>${label}</span><strong>${value}</strong>${note ? `<small>${note}</small>` : ""}</div>`;
  const rows = items.map((item, index) => {
    const groupId = String(item.grupo || item.grupo_id || "-");
    const scenario = (item.cenarios || []).find((entry) => entry.id === "without_embedded") || (item.cenarios || [])[0] || {};
    const profiles = scenario.perfis_contemplacao || [];
    const profileValue = (id) => {
      const value = profiles.find((profile) => profile.id === id);
      const scenario = (item.cenarios || []).find((entry) => entry.id === "without_embedded") || (item.cenarios || [])[0];
      const meetsBid = value && profileMeetsBid(item, scenario, value);
      return value ? `<b class="${meetsBid ? "is-hit" : "is-gap"}">${formatPercent(value.percentual_referencia)}</b>` : "-";
    };
    return `<tr><th><span>${index + 1}</span> Grupo ${escapeHtml(groupId)}<small>${escapeHtml(item.administradora || "-")}</small></th><td>${formatMoney(item.credito_maximo)}</td><td>${escapeHtml(String(item.prazo_restante ?? "-"))} meses</td><td>${formatAverageForOverview(item, "urgent")}</td><td>${formatAverageForOverview(item, "moderate")}</td><td>${profileValue("conservative")}</td><td>${profileValue("moderate")}</td></tr>`;
  }).join("");
  const maxCredit = Math.max(...items.map((item) => Number(item.credito_maximo || 0)), 0);
  const avgCredit = items.reduce((sum, item) => sum + Number(item.credito_maximo || 0), 0) / Math.max(items.length, 1);
  return `<section class="selected-groups-overview"><div class="selected-overview-heading"><div><span>Visão comparativa</span><h2>Leitura rápida dos grupos selecionados</h2></div><small>Compare capacidade, prazo, histórico e aderência ao perfil sem abrir cada detalhe.</small></div><div class="selected-overview-kpis">${metric("Grupos selecionados", items.length)}${metric("Maior crédito", formatMoney(maxCredit))}${metric("Crédito médio", formatMoney(avgCredit))}${metric("Menor prazo", `${Math.min(...items.map((item) => Number(item.prazo_restante || 9999)), 9999)} meses`)}</div><div class="selected-overview-table-wrap"><table class="selected-overview-table"><thead><tr><th>Grupo</th><th>Crédito máximo</th><th>Prazo restante</th><th>Histórico urgente</th><th>Histórico moderado</th><th>Conservador</th><th>Moderado</th></tr></thead><tbody>${rows}</tbody></table></div></section>`;
}

function formatAverageForOverview(item, strategy) {
  const value = item?.capacidade_contemplacoes?.[strategy]?.media_contemplacoes;
  return value === null || value === undefined ? "-" : String(value).replace(".", ",");
}

function selectedCompositionScenarioMetrics(items, scenarioId, desiredCreditOverride = null) {
  const { availableBid } = selectedGroupsClientFinancials();
  const client = investorState.result?.cliente || {};
  const desiredCredit = Number(desiredCreditOverride ?? client.credito_liquido_desejado ?? client.credito_desejado ?? 0);
  const totalQuotas = items.reduce((sum, item) => sum + quotaCountFor(item), 0);
  const targetPerQuota = desiredCredit > 0 && totalQuotas > 0 ? desiredCredit / totalQuotas : null;
  const entries = items.map((item) => {
    const sourceItem = investorState.selectedGroupData.get(motor360GroupKey(item)) || item;
    const scenario = (sourceItem.cenarios || item.cenarios || []).find((value) => value.id === scenarioId);
    const quotas = quotaCountFor(item);
    if (!scenario) return null;
    const rawCredit = Number(scenario.credito_liquido_projetado ?? scenario.credito_contratado ?? 0);
    const cap = Number(sourceItem.credito_maximo || item.credito_maximo || 0);
    const rawContractedCredit = Number(scenario.credito_contratado ?? rawCredit);
    const perQuotaCredit = targetPerQuota != null ? Math.min(cap > 0 ? cap : targetPerQuota, targetPerQuota) : Math.min(cap > 0 ? cap : rawCredit, rawCredit);
    const ratio = rawCredit > 0 ? perQuotaCredit / rawCredit : 0;
    const contractedCreditPerQuota = rawContractedCredit * ratio;
    const total = (field) => Number(scenario[field] ?? 0) * ratio * quotas;
    const profiles = Object.fromEntries((scenario.perfis_contemplacao || []).map((profile) => [profile.id, {
      ...profile,
      ideal: Number(profile.lance_ideal || 0) * ratio * quotas,
    }]));
    return {
      item, scenario, quotas, ratio, perQuotaCredit,
      credit: perQuotaCredit * quotas,
      contractedCredit: contractedCreditPerQuota * quotas,
      grossCreditPerQuota: contractedCreditPerQuota,
      creditCompatible: cap <= 0 || contractedCreditPerQuota <= cap + 0.01,
      targetCredit: (targetPerQuota ?? perQuotaCredit) * quotas,
      installment: total("parcela_inicial"),
      installmentAfter: scenario.parcela_pos_contemplacao == null ? null : total("parcela_pos_contemplacao"),
      balance: total("saldo_devedor"),
      embedded: total("lance_embutido"),
      totalBid: total("lance_total_cenario"),
      profiles,
    };
  }).filter(Boolean);
  const credit = entries.reduce((sum, entry) => sum + entry.credit, 0);
  const shortfall = desiredCredit > 0 ? Math.max(0, desiredCredit - credit) : 0;
  const profileRequirements = {};
  for (const profileId of ["investor", "conservative", "moderate", "aggressive", "super_aggressive"]) {
    const required = entries.reduce((sum, entry) => sum + Number(entry.profiles[profileId]?.ideal || 0), 0);
    profileRequirements[profileId] = required;
    for (const entry of entries) {
      const profile = entry.profiles[profileId];
      if (!profile) continue;
      profile.available = required > 0 ? availableBid * profile.ideal / required : 0;
      profile.meets = profile.ideal > 0 && profile.available >= profile.ideal;
    }
  }
  const creditCapacityOk = entries.length === items.length && entries.every((entry) => entry.creditCompatible);
  const creditCapacityIssues = entries.filter((entry) => !entry.creditCompatible).map((entry) => ({ groupId: String(entry.item.grupo || entry.item.grupo_id || "-"), contractedPerQuota: entry.grossCreditPerQuota, maximumPerQuota: Number(entry.item.credito_maximo || 0) }));
  return { entries, totalQuotas, desiredCredit, targetPerQuota, credit, contractedCredit: entries.reduce((sum, entry) => sum + entry.contractedCredit, 0), embedded: entries.reduce((sum, entry) => sum + entry.embedded, 0), shortfall, creditCapacityOk, creditCapacityIssues, profileRequirements, installment: entries.reduce((sum, entry) => sum + entry.installment, 0), installmentAfter: entries.some((entry) => entry.installmentAfter != null) ? entries.reduce((sum, entry) => sum + Number(entry.installmentAfter || 0), 0) : null, balance: entries.reduce((sum, entry) => sum + entry.balance, 0) };
}

function selectedCompositionAssessment(metrics, client = motor360ClientProfile(), profileId = allocationProfileId()) {
  const desiredCredit = Number(client.credito_liquido_desejado || 0);
  const maximumInstallment = Number(client.parcela_maxima || 0);
  const income = Number(client.renda_total ?? client.renda ?? selectedGroupsClientFinancials().income ?? 0);
  const commitmentLimit = selectedGroupsPercentValue(client.comprometimento_maximo ?? client.comprometimento_maximo_percentual ?? 30);
  const incomeLimit = income > 0 ? income * commitmentLimit / 100 : 0;
  const availableBid = Number(selectedGroupsClientFinancials().availableBid || 0);
  const requiredBid = Number(metrics.profileRequirements?.[profileId] || 0);
  const failures = [];
  if (desiredCredit > 0 && metrics.credit < desiredCredit) failures.push(`Faltam ${formatMoney(desiredCredit - metrics.credit)} de crédito`);
  if (!metrics.creditCapacityOk) failures.push(...(metrics.creditCapacityIssues || []).map((issue) => `Grupo ${issue.groupId}: ${formatMoney(issue.contractedPerQuota)} por cota excede o teto de ${formatMoney(issue.maximumPerQuota)}`));
  const installmentLimitOk = maximumInstallment <= 0 || metrics.installment <= maximumInstallment;
  const incomeOk = incomeLimit <= 0 || metrics.installment <= incomeLimit;
  if (!installmentLimitOk) failures.push(`Parcela ${formatMoney(metrics.installment)} acima do máximo de ${formatMoney(maximumInstallment)}`);
  if (!incomeOk) failures.push(`Parcela ${formatMoney(metrics.installment)} compromete mais que ${formatPercent(commitmentLimit / 100)} da renda (${formatMoney(incomeLimit)})`);
  if (requiredBid > availableBid) failures.push(`Faltam ${formatMoney(requiredBid - availableBid)} de lance para o perfil`);
  const desiredInstallment = Number(client.parcela_desejada || 0);
  const parcelWarning = desiredInstallment > 0 && metrics.installment > desiredInstallment ? `Parcela ${formatMoney(metrics.installment - desiredInstallment)} acima da desejada` : "";
  return { ok: failures.length === 0, failures, parcelWarning, requiredBid, availableBid, maximumInstallment, incomeLimit, installmentLimitOk, incomeOk };
}

function motor360ClientProfileId() {
  const profile = investorState.result?.perfil_contemplacao;
  return ({ urgent: "super_aggressive", fast: "aggressive", moderate: "moderate", conservative: "conservative", long_term: "investor" })[profile] || profile || "moderate";
}

function motor360FocusedProfileId() {
  return investorState.selectedGroupProfile && investorState.selectedGroupProfile !== "all"
    ? investorState.selectedGroupProfile
    : motor360ClientProfileId();
}

function motor360CompositionIdealBid(item, scenario, profileId = motor360FocusedProfileId()) {
  const profileRows = item?.composition_candidate && !investorState.selectedGroupIds.has(motor360GroupKey(item))
    ? (scenario?.composition_totals?.perfis_contemplacao || scenario?.perfis_contemplacao || [])
    : (scenario?.perfis_contemplacao || []);
  const profile = profileRows.find((entry) => entry.id === profileId);
  if (!profile || profile.lance_ideal == null || profile.lance_ideal === "") return null;
  const groupKey = motor360GroupKey(item);
  if (investorState.selectedGroupIds.has(groupKey)) {
    const metrics = selectedCompositionScenarioMetrics(selectedMotor360Items(), scenario.id);
    const entry = metrics.entries.find((value) => motor360GroupKey(value.item) === groupKey);
    const ideal = entry?.profiles?.[profileId]?.ideal;
    if (ideal === null || ideal === undefined || ideal === "") return null;
    const numericIdeal = Number(ideal);
    return Number.isFinite(numericIdeal) && numericIdeal >= 0 ? numericIdeal : null;
  }
  // The backend's scenario/profile lance_ideal is already expressed against
  // the client's desired total credit. Multiplying by the minimum quota count
  // repeats that credit target and inflates the aggregate bid.
  const aggregateIdealBid = Number(profile.lance_ideal);
  return Number.isFinite(aggregateIdealBid) && aggregateIdealBid >= 0 ? aggregateIdealBid : null;
}

function motor360ScenarioIdsForSort(item) {
  const available = (item.cenarios || item.scenarios || []).map((scenario) => scenario.id).filter(Boolean);
  const selectedScenario = investorState.selectedGroupScenario || "per_group";
  if (selectedScenario === "with_embedded" || selectedScenario === "without_embedded") {
    return available.includes(selectedScenario) ? [selectedScenario] : [];
  }
  const selectedForGroup = [...selectedScenarioIdsForGroup(motor360GroupKey(item))]
    .filter((scenarioId) => available.includes(scenarioId));
  if (selectedForGroup.length) return selectedForGroup;
  return available;
}

function motor360BidSortValue(item) {
  const profileId = motor360FocusedProfileId();
  const candidates = motor360ScenarioIdsForSort(item).map((scenarioId) => {
    const scenario = (item.cenarios || item.scenarios || []).find((entry) => entry.id === scenarioId);
    if (!scenario) return null;
    const value = motor360CompositionIdealBid(item, scenario, profileId);
    return value === null ? null : { value, scenarioId };
  }).filter(Boolean);
  const scenarioPriority = (scenarioId) => scenarioId === "without_embedded" ? 0 : 1;
  candidates.sort((a, b) => a.value - b.value || scenarioPriority(a.scenarioId) - scenarioPriority(b.scenarioId));
  return candidates[0] || null;
}

function motor360BidSortDescription() {
  const selected = investorState.selectedGroupScenario || "per_group";
  if (selected === "with_embedded") return "cenário com embutido";
  if (selected === "without_embedded") return "cenário sem embutido";
  if (selected === "all") return "menor lance próprio ideal agregado entre os dois cenários";
  return "cenário selecionado por grupo; sem seleção individual, menor valor entre os cenários disponíveis";
}

function motor360BidSortLabel(item) {
  const bid = motor360BidSortValue(item);
  if (!bid) return "Menor lance ideal · sem referência calculável";
  const scenarioLabel = bid.scenarioId === "with_embedded" ? "Com embutido" : "Sem embutido";
  return `Menor lance ideal · ${scenarioLabel}: ${formatMoney(bid.value)}`;
}

function sortMotor360ItemsByBid(items) {
  return items
    .map((item, originalIndex) => ({ item, originalIndex, bid: motor360BidSortValue(item) }))
    .sort((a, b) => (
      (a.bid === null ? 1 : 0) - (b.bid === null ? 1 : 0)
      || (a.bid?.value ?? Infinity) - (b.bid?.value ?? Infinity)
      || a.originalIndex - b.originalIndex
    ))
    .map(({ item }) => item);
}

function selectedGroupAnalytics(item, forcedScenarioId = null) {
  const groupKey = motor360GroupKey(item);
  const selectedIds = [...selectedScenarioIdsForGroup(groupKey)];
  const scenarioId = forcedScenarioId || (selectedIds.includes(investorState.selectedGroupScenario)
    ? investorState.selectedGroupScenario
    : selectedIds[0] || "");
  const clientFinancials = selectedGroupsClientFinancials();
  const compositionKey = [...investorState.selectedGroupIds].sort().map((id) => (
    `${id}:${quotaCountFor(id)}:${[...selectedScenarioIdsForGroup(id)].sort().join(",")}`
  )).join(";");
  const cacheKey = JSON.stringify([
    groupKey,
    scenarioId,
    investorState.selectedGroupProfile || "all",
    compositionKey,
    Number(clientFinancials.client.credito_liquido_desejado || 0),
    clientFinancials.own,
    clientFinancials.fgts,
    clientFinancials.availableBid,
    clientFinancials.income,
    Number(clientFinancials.client.parcela_maxima || clientFinancials.client.parcela_desejada || 0),
    Number(clientFinancials.client.comprometimento_maximo ?? clientFinancials.client.comprometimento_maximo_percentual ?? 30),
  ]);
  const cached = motor360GroupAnalyticsCache.get(cacheKey);
  if (cached?.item === item) return cached.analytics;
  const analytics = selectedGroupAnalyticsUncached(item, forcedScenarioId);
  if (motor360GroupAnalyticsCache.size >= 5000) {
    const oldestKey = motor360GroupAnalyticsCache.keys().next().value;
    if (oldestKey !== undefined) motor360GroupAnalyticsCache.delete(oldestKey);
  }
  motor360GroupAnalyticsCache.set(cacheKey, { item, analytics });
  return analytics;
}

function selectedGroupAnalyticsUncached(item, forcedScenarioId = null) {
  const groupId = String(item.grupo || item.grupo_id || "-");
  const selectedIds = [...selectedScenarioIdsForGroup(motor360GroupKey(item))];
  const scenarioId = forcedScenarioId || (selectedIds.includes(investorState.selectedGroupScenario)
    ? investorState.selectedGroupScenario
    : selectedIds[0] || "");
  const scenario = (item.cenarios || []).find((entry) => entry.id === scenarioId) || (item.cenarios || []).find((entry) => entry.id === "without_embedded") || (item.cenarios || [])[0] || {};
  const profiles = scenario.perfis_contemplacao || [];
  const compositionItems = investorState.selectedGroupIds.has(motor360GroupKey(item)) ? selectedMotor360Items() : [item];
  const composition = selectedCompositionScenarioMetrics(compositionItems, scenario.id);
  const compositionEntry = composition.entries.find((entry) => motor360GroupKey(entry.item) === motor360GroupKey(item));
  const profile = (id) => {
    const value = profiles.find((entry) => entry.id === id);
    const calculated = compositionEntry?.profiles[id];
    return value ? { ...value, lance_ideal: calculated?.ideal ?? Number(value.lance_ideal || 0) * quotaCountFor(item), composition_scaled: Boolean(compositionEntry), composition_available: calculated?.available, atinge_perfil: Boolean(calculated?.meets) } : {};
  };
  const historical = item.capacidade_contemplacoes || {};
  const history = (key) => Number(historical[key]?.media_contemplacoes ?? historical[key]?.media ?? 0);
  const quotaCount = quotaCountFor(item);
  const { client, income } = selectedGroupsClientFinancials();
  const desiredCredit = compositionEntry?.targetCredit ?? Number(client.credito_liquido_desejado || 0);
  const maxInstallment = Number(client.parcela_maxima || client.parcela_desejada || 0);
  const credit = compositionEntry?.credit ?? Number(scenario.credito_liquido_projetado ?? scenario.credito_contratado ?? item.credito_maximo ?? 0) * quotaCount;
  const contractedCredit = compositionEntry?.credit ?? credit;
  const grossContractedCredit = compositionEntry?.contractedCredit ?? contractedCredit;
  const groupMaxCredit = Number(item.credito_maximo ?? 0) * quotaCount;
  const installment = compositionEntry?.installment ?? Number(scenario.parcela_inicial || 0) * quotaCount;
  const focusProfile = motor360FocusedProfileId();
  const focusedProfile = profile(focusProfile);
  const idealBid = Number(focusedProfile.lance_ideal || 0);
  const availableBid = compositionEntry?.profiles[focusProfile]?.available ?? allocatedClientBidFor(item, scenario, focusProfile);
  const creditFit = desiredCredit > 0 ? Math.min(1, credit / desiredCredit) : 1;
  const installmentFit = maxInstallment > 0 ? Math.min(1, maxInstallment / Math.max(installment, 1)) : 1;
  const bidFit = idealBid > 0 ? Math.min(1, availableBid / idealBid) : 1;
  const historyFit = Math.min(1, history("moderate") / 6);
  const costRate = Number(item.taxa_total ?? item.taxa_administracao ?? 0);
  const costFit = costRate > 0 ? Math.max(0, 1 - Math.min(1, costRate / 0.30)) : .7;
  const term = Number(item.prazo_restante || 0);
  const termFit = term > 0 ? Math.min(1, term / 240) : .5;
  const adminRate = Number(item.taxa_adm ?? item.taxa_total ?? 0);
  const reserveRate = Number(item.fundo_reserva || 0);
  const totalPaid = (compositionEntry?.balance ?? Number(scenario.saldo_devedor ?? scenario.credito_contratado ?? 0) * quotaCount) * (1 + adminRate + reserveRate);
  const embedded = compositionEntry?.embedded ?? Number(scenario.lance_embutido || 0) * quotaCount;
  const creditLossRate = credit > 0 ? Math.min(1, embedded / Math.max(credit + embedded, 1)) : 0;
  const probability = Math.round(Math.min(100, Math.max(0, bidFit * 65 + historyFit * 35)));
  const probabilityLabel = probability >= 80 ? "Alta" : probability >= 60 ? "Moderada" : probability >= 40 ? "Baixa" : "Muito baixa";
  const commitment = income > 0 ? installment / income : null;
  const riskLabel = commitment == null ? "Não informado" : commitment <= .15 ? "Baixo" : commitment <= .25 ? "Moderado" : commitment <= .30 ? "Elevado" : "Crítico";
  const riskFit = commitment == null ? .5 : Math.max(0, 1 - Math.min(1, commitment / .30));
  const score = Math.round((creditFit * .30 + installmentFit * .20 + bidFit * .20 + historyFit * .15 + costFit * .05 + termFit * .05 + riskFit * .05) * 100);
  const scoreLabel = score >= 80 ? "Excelente" : score >= 65 ? "Adequada" : score >= 50 ? "Atenção" : "Inadequada";
  return {
    item, groupId, scenario, profile, history, quotaCount,
    credit, desiredCredit, contractedCredit, groupMaxCredit,
    installment,
    installmentAfter: compositionEntry?.installmentAfter ?? (scenario.parcela_pos_contemplacao == null ? null : Number(scenario.parcela_pos_contemplacao) * quotaCount),
    bid: scenarioTotalBidFor(item, scenario),
    balance: compositionEntry?.balance ?? Number(scenario.saldo_devedor || 0) * quotaCount,
    idealBid, availableBid, score, scoreLabel, focusProfile, adminRate, reserveRate, totalPaid, embedded, creditLossRate, creditFit, installmentFit, bidFit, historyFit, costFit, termFit,
    incomeCommitment: commitment, probability, probabilityLabel, riskLabel,
  };
}

let selectedGroupsCharts = [];

function selectedGroupsClientFinancials() {
  const client = investorState.result?.cliente || {};
  const own = Number(client.lance_proprio ?? client.lance_recursos_proprios ?? client.lance_maximo_recursos_proprios ?? client.own_resources_total ?? 0);
  const fgts = Number(client.fgts_total ?? client.fgts ?? 0);
  const declaredTotal = Number(client.lance_cliente_total ?? client.lance_total ?? 0);
  const availableBid = declaredTotal > 0 ? declaredTotal : Math.max(0, own + fgts);
  const income = Number(client.renda_total ?? client.renda ?? 0);
  return { client, own: Number.isFinite(own) ? own : 0, fgts: Number.isFinite(fgts) ? fgts : 0, availableBid: Number.isFinite(availableBid) ? availableBid : 0, income: Number.isFinite(income) ? income : 0 };
}

function selectedGroupsPercentValue(value) {
  if (value === null || value === undefined || value === "") return 0;
  const normalized = Number(String(value).replace("%", "").replace(",", "."));
  if (!Number.isFinite(normalized)) return 0;
  return normalized <= 1 ? normalized * 100 : normalized;
}

function renderSelectedGroupsAnalyticalPanel(items) {
  const analytics = items.map(selectedGroupAnalytics);
  const profileFilter = investorState.selectedGroupProfile || "all";
  const currentSort = investorState.selectedGroupSort || "original";
  const currentScenario = investorState.selectedGroupScenario || "per_group";
  const profileNames = { conservative: "Conservador", moderate: "Moderado", aggressive: "Agressivo", super_aggressive: "Super agressivo" };
  const { client } = selectedGroupsClientFinancials();
  const parcelaDesejada = Number(client.parcela_desejada ?? client.parcela_ideal ?? 0);
  const metricRows = [
    ["Crédito máx. grupo", (entry) => formatMoney(entry.groupMaxCredit)],
    ["Crédito des. líq.", (entry) => formatMoney(entry.desiredCredit)],
    ["Crédito contr.", (entry) => formatMoney(entry.contractedCredit)],
    ["Parcela des. cliente", () => formatMoney(parcelaDesejada)],
    ["Parcela inicial", (entry) => formatMoney(entry.installment)],
    ["Parcela pós-cont.", (entry) => entry.installmentAfter ? formatMoney(entry.installmentAfter) : "-"],
    ["Lance total", (entry) => formatMoney(entry.bid)],
    ["Saldo devedor", (entry) => formatMoney(entry.balance)],
    ["Prazo restante", (entry) => `${entry.item.prazo_restante ?? "-"} meses`],
    ["Comprom. renda", (entry) => entry.incomeCommitment == null ? "-" : formatPercent(entry.incomeCommitment)],
    ["Taxa adm.", (entry) => formatPercent(entry.adminRate)],
    ["Fundo reserva", (entry) => formatPercent(entry.reserveRate)],
    ["Índice de aderência", (entry) => `${entry.score}/100 · ${entry.scoreLabel}`],
  ];
  const profileRows = Object.entries(profileNames).map(([id, label]) => `<tr class="${profileFilter === id ? "is-focus" : ""}"><th>${label}</th>${analytics.map((entry) => { const value = entry.profile(id); const bidGap = profileBidGap(entry.item, entry.scenario, value); const passes = bidGap.ideal > 0 && bidGap.gap === 0; const state = passes ? "is-positive" : bidGap.ideal > 0 ? "is-negative" : "is-warning"; return `<td class="${state}"><strong>${formatPercent(value.percentual_referencia)}</strong><small>${passes ? "Lance suficiente" : bidGap.ideal > 0 ? `Faltam ${formatMoney(bidGap.gap)}` : "Sem referência"}</small></td>`; }).join("")}</tr>`).join("");
  const comparativeEntries = analytics.flatMap((entry) => {
    const selectedScenarioIds = currentScenario === "per_group" ? [...selectedScenarioIdsForGroup(motor360GroupKey(entry.item))] : [currentScenario];
    return selectedScenarioIds.map((scenarioId) => selectedGroupAnalytics(entry.item, scenarioId)).filter((value) => value?.scenario);
  });
  const comparativeRows = comparativeEntries.map((entry) => `<tr><th>Grupo ${escapeHtml(entry.groupId)}<small>${escapeHtml(entry.item.administradora || "-")} · ${entry.scenario.id === "with_embedded" ? "Com embutido" : "Sem embutido"}</small></th>${metricRows.map(([, formatter]) => `<td>${formatter(entry)}</td>`).join("")}</tr>`).join("");
  const comparativeHeaders = metricRows.map(([label]) => `<th>${label.replace(" ", "<br>")}</th>`).join("");
  const controls = `<div class="sg-toolbar"><div><span>Visão final</span><h2>Comparação de grupos</h2><p>Confira a composição final da carteira selecionada.</p></div></div>`;
  return `<section class="sg-dashboard" data-sg-dashboard>${controls}<div class="sg-fact-strip"><span><b>${analytics.length}</b> grupos comparados</span><span><b>${currentScenario === "with_embedded" ? "Com" : "Sem"}</b> lance embutido</span><span>Os gráficos exibem valores por grupo e cota selecionada.</span></div><div class="sg-chart-grid"><article class="sg-panel sg-panel-financial"><header><div><span>Financeiro</span><h3>Valores por grupo</h3></div><div class="sg-metric-switch" role="group" aria-label="Métrica financeira"><button type="button" data-sg-metric="credit" aria-pressed="true">Crédito</button><button type="button" data-sg-metric="installment">Parcela</button><button type="button" data-sg-metric="bid">Lance</button><button type="button" data-sg-metric="balance">Saldo</button></div></header><div class="sg-chart" id="sgFinancialChart" role="img" aria-label="Gráfico financeiro comparativo"></div></article><article class="sg-panel"><header><div><span>Histórico</span><h3>Contemplações por janela</h3></div><small>Médias informadas do grupo</small></header><div class="sg-chart" id="sgHistoryChart" role="img" aria-label="Gráfico de histórico de contemplações"></div></article></div><div class="sg-chart-grid sg-chart-grid-secondary"><article class="sg-panel"><header><div><span>Perfis</span><h3>Distribuição percentual</h3></div><small>Percentual de referência por perfil</small></header><div class="sg-chart" id="sgProfilesChart" role="img" aria-label="Gráfico radar de perfis de contemplação"></div></article><article class="sg-panel sg-table-panel"><header><div><span>Perfis</span><h3>Percentual e diferença de lance</h3></div><small>Valores não são recomendação</small></header><div class="sg-table-wrap"><table class="sg-matrix sg-profile-matrix"><thead><tr><th>Perfil</th>${analytics.map((entry) => `<th>Grupo ${escapeHtml(entry.groupId)}</th>`).join("")}</tr></thead><tbody>${profileRows}</tbody></table></div></article></div><article class="sg-panel sg-comparison-table"><header><div><span>Detalhamento comparativo</span><h3>Condições financeiras e operacionais</h3></div></header><div class="sg-table-wrap"><table class="sg-matrix"><thead><tr><th>Grupo</th>${comparativeHeaders}</tr></thead><tbody>${comparativeRows}</tbody></table></div></article></section>`;
}

function renderSelectedGroupsECharts(items) {
  selectedGroupsCharts.forEach((chart) => chart?.dispose?.());
  selectedGroupsCharts = [];
  if (!items.length) return;
  if (!window.echarts) {
    document.querySelectorAll("[data-sg-dashboard] .sg-chart").forEach((element) => { element.innerHTML = '<div class="sg-chart-error">Não foi possível carregar o componente de gráficos. Atualize a página ou verifique a conexão.</div>'; });
    // O painel possui fallback HTML; não depende de ECharts/CDN para funcionar.
    return;
  }
  const analytics = items.map(selectedGroupAnalytics);
  const colors = ["#1d7188", "#ef7a24", "#5a8d5b", "#8b5e9d", "#a44a52"];
  const init = (id, option) => {
    const element = document.getElementById(id);
    if (!element) return;
    try { const chart = window.echarts.init(element, null, { renderer: "svg" }); chart.setOption(option); selectedGroupsCharts.push(chart); } catch (error) { console.error("[selected-groups-chart]", id, error); element.innerHTML = '<div class="sg-chart-error">Dados indisponíveis para este gráfico.</div>'; }
  };
  const moneyAxis = (value) => value >= 1000000 ? `R$ ${(value / 1000000).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} mi` : `R$ ${(value / 1000).toLocaleString("pt-BR", { maximumFractionDigits: 0 })} mil`;
  const metricMap = { credit: ["Crédito máximo do grupo", "groupMaxCredit"], installment: ["Parcela inicial", "installment"], bid: ["Lance total", "bid"], balance: ["Saldo devedor", "balance"] };
  const metricKey = investorState.selectedGroupMetric || "credit";
  const [metricLabel, field] = metricMap[metricKey] || metricMap.credit;
  init("sgFinancialChart", {
    animationDuration: 420, color: colors, grid: { left: 110, right: 30, top: 22, bottom: 26 }, tooltip: { trigger: "axis", axisPointer: { type: "shadow" }, valueFormatter: (value) => formatMoney(value) }, xAxis: { type: "value", axisLabel: { formatter: moneyAxis }, splitLine: { lineStyle: { color: "#e7edef" } } }, yAxis: { type: "category", data: analytics.map((entry) => `Grupo ${entry.groupId}`), axisTick: { show: false }, axisLine: { show: false } }, series: [{ name: metricLabel, type: "bar", data: analytics.map((entry, index) => ({ value: entry[field], itemStyle: { color: colors[index % colors.length] } })), barMaxWidth: 30, label: { show: true, position: "right", formatter: ({ value }) => formatMoney(value), color: "#27404a", fontSize: 11 } }]
  });
  init("sgHistoryChart", {
    animationDuration: 420, color: ["#ef7a24", "#1d7188", "#5a8d5b"], legend: { bottom: 0, data: ["Urgente (3m)", "Rápido (6m)", "Moderado (12m)"] }, grid: { left: 42, right: 18, top: 24, bottom: 48 }, tooltip: { trigger: "axis", axisPointer: { type: "shadow" } }, xAxis: { type: "category", data: analytics.map((entry) => `Grupo ${entry.groupId}`), axisTick: { show: false } }, yAxis: { type: "value", name: "média", minInterval: 1, splitLine: { lineStyle: { color: "#e7edef" } } }, series: [{ name: "Urgente (3m)", type: "bar", data: analytics.map((entry) => entry.history("urgent")), barMaxWidth: 26 }, { name: "Rápido (6m)", type: "bar", data: analytics.map((entry) => entry.history("fast")), barMaxWidth: 26 }, { name: "Moderado (12m)", type: "bar", data: analytics.map((entry) => entry.history("moderate")), barMaxWidth: 26 }]
  });
  const radarAnalytics = analytics.map((entry) => ({ ...entry, profile: (id) => ({ ...entry.profile(id), percentual_referencia: selectedGroupsPercentValue(entry.profile(id).percentual_referencia) }) }));
  init("sgProfilesChart", {
    animationDuration: 420, color: colors, legend: { bottom: 0, data: radarAnalytics.map((entry) => `Grupo ${entry.groupId}`) }, tooltip: { trigger: "item", valueFormatter: (value) => `${Number(value).toLocaleString("pt-BR")}%` }, radar: { indicator: [{ name: "Conservador", max: 100 }, { name: "Moderado", max: 100 }, { name: "Agressivo", max: 100 }, { name: "Super agressivo", max: 100 }], splitArea: { areaStyle: { color: ["#fbfcfc", "#f3f7f8"] } } }, series: [{ type: "radar", data: radarAnalytics.map((entry) => ({ name: `Grupo ${entry.groupId}`, value: ["conservative", "moderate", "aggressive", "super_aggressive"].map((id) => Number(entry.profile(id).percentual_referencia || 0)), areaStyle: { opacity: .08 }, symbolSize: 6 })) }]
  });
  window.addEventListener("resize", () => selectedGroupsCharts.forEach((chart) => chart?.resize?.()), { once: true });
}

function renderSelectedGroupsExtraVisuals(items) {
  const dashboard = document.querySelector("[data-sg-dashboard]");
  if (!dashboard || !window.echarts || !items.length) return;
  dashboard.querySelector("[data-sg-extra-visuals]")?.remove();
  const analytics = items.map(selectedGroupAnalytics);
  const wrapper = document.createElement("div");
  wrapper.dataset.sgExtraVisuals = "true";
  wrapper.className = "sg-chart-grid sg-extra-visuals";
  wrapper.innerHTML = `<article class="sg-panel"><header><div><span>Eficiência</span><h3>Custo-benefício</h3></div><small>Crédito líquido por custo estimado</small></header><div class="sg-chart" id="sgCostBenefitChart" role="img" aria-label="Gráfico de custo benefício"></div></article><article class="sg-panel"><header><div><span>Decisão</span><h3>Risco x velocidade</h3></div><small>Quanto mais à direita e abaixo, melhor</small></header><div class="sg-chart" id="sgRiskSpeedChart" role="img" aria-label="Gráfico de risco e velocidade"></div></article>`;
  dashboard.appendChild(wrapper);
  const init = (id, option) => { const element = document.getElementById(id); if (!element) return; try { const chart = window.echarts.init(element, null, { renderer: "svg" }); chart.setOption(option); selectedGroupsCharts.push(chart); } catch (error) { console.error("[selected-groups-chart]", id, error); element.innerHTML = '<div class="sg-chart-error">Dados indisponíveis para este gráfico.</div>'; } };
  const names = analytics.map((entry) => `Grupo ${entry.groupId}`);
  const embeddedImpact = analytics.map((entry) => {
    const scenario = (entry.item.cenarios || []).find((value) => value.id === "with_embedded");
    const embeddedCredit = Number(scenario?.credito_liquido_projetado ?? scenario?.credito_contratado ?? 0) * entry.quotaCount;
    return { before: entry.credit, after: embeddedCredit, reduction: Math.max(0, entry.credit - embeddedCredit) };
  });
  init("sgCostBenefitChart", { animationDuration: 420, grid: { left: 76, right: 35, top: 38, bottom: 48 }, tooltip: { trigger: "item", formatter: ({ data }) => `<strong>${data.name}</strong><br/>Crédito líquido: ${formatMoney(data.value[1])}<br/>Custo total estimado: ${formatMoney(data.value[0])}<br/>Eficiência: ${formatMoney(data.value[1] / Math.max(data.value[0], 1))} de crédito por R$ 1 pago` }, xAxis: { type: "value", name: "Custo total (R$)", nameLocation: "middle", nameGap: 30, axisLabel: { formatter: (v) => formatMoney(v) } }, yAxis: { type: "value", name: "Crédito líquido (R$)", axisLabel: { formatter: (v) => formatMoney(v) } }, series: [{ type: "scatter", symbolSize: 22, data: analytics.map((entry, index) => ({ name: names[index], value: [entry.totalPaid, entry.credit], itemStyle: { color: ["#ef7a24", "#1d7188", "#5a8d5b", "#8b5e9d"][index % 4] }, label: { show: true, formatter: names[index], position: "top", color: "#27404a", fontSize: 11 } })) }] });
  init("sgRiskSpeedChart", { animationDuration: 420, grid: { left: 60, right: 35, top: 38, bottom: 48 }, tooltip: { trigger: "item", formatter: ({ data }) => `<strong>${data.name}</strong><br/>Prazo restante: ${data.value[0]} meses<br/>Comprometimento da renda: ${Number(data.value[1]).toFixed(1)}%<br/>Nota: ${data.score}/100<br/>Risco: ${data.risk}` }, xAxis: { type: "value", name: "Prazo restante (meses)", nameLocation: "middle", nameGap: 30 }, yAxis: { type: "value", name: "Renda comprometida (%)", max: 100 }, series: [{ type: "scatter", symbolSize: 24, data: analytics.map((entry, index) => ({ name: names[index], score: entry.score, risk: entry.riskLabel, value: [Number(entry.item.prazo_restante || 0), Number((entry.incomeCommitment || 0) * 100).toFixed(1)], itemStyle: { color: entry.score >= 70 ? "#1d9b59" : entry.score >= 50 ? "#ef7a24" : "#a44a52" }, label: { show: true, formatter: names[index], position: index % 2 ? "bottom" : "top", color: "#27404a", fontSize: 11 } })) }] });
}

function renderSelectedGroupsCartSummary(items) {
  const client = investorState.result?.cliente || {};
  const desiredCredit = Number(client.credito_liquido_desejado || 0);
  const desiredInstallment = Number(client.parcela_desejada || 0);
  const { availableBid } = selectedGroupsClientFinancials();
  const profileIds = ["investor", "conservative", "moderate", "aggressive", "super_aggressive"];
  const profileLabels = { investor: "Investidor", conservative: "Conservador", moderate: "Moderado", aggressive: "Agressivo", super_aggressive: "Super Agressivo" };
  const scenarioSummary = (scenarioId, label) => {
    const metrics = selectedCompositionScenarioMetrics(items, scenarioId, desiredCredit);
    if (!metrics.entries.length) return "";
    const credit = metrics.credit;
    const installment = metrics.installment;
    const balance = metrics.balance;
    const creditOk = credit >= desiredCredit && metrics.creditCapacityOk;
    const profiles = profileIds.map((profileId) => {
      const requirements = metrics.entries.map((entry) => ({ ...entry, groupId: String(entry.item.grupo || entry.item.grupo_id || "-"), required: Number(entry.profiles[profileId]?.ideal || 0) }));
      const requiredTotal = requirements.reduce((sum, entry) => sum + entry.required, 0);
      const pool = Math.min(availableBid, requiredTotal);
      const allocations = requirements.filter((entry) => entry.required > 0).map((entry) => ({
        groupId: entry.groupId,
        value: requiredTotal > 0 ? pool * entry.required / requiredTotal : 0,
      }));
      return { profileId, requiredTotal, gap: Math.max(0, requiredTotal - availableBid), allocations };
    }).filter((profile) => profile.requiredTotal > 0);
    const activeProfile = investorState.selectedGroupProfile && investorState.selectedGroupProfile !== "all" ? investorState.selectedGroupProfile : allocationProfileId();
    const assessment = selectedCompositionAssessment(metrics, client, activeProfile);
    const viable = assessment.ok;
    const parcelText = assessment.parcelWarning ? `${assessment.parcelWarning} (alerta)` : "Dentro da parcela desejada";
    const installmentChecks = [
      assessment.installmentLimitOk ? "Dentro da parcela máxima" : "Acima da parcela máxima",
      assessment.incomeOk ? "Dentro do limite de renda" : "Acima do limite de renda",
    ].join(" · ");
    return `<article class="motor360-cart-scenario"><header><strong>${label}</strong><span class="${viable ? "is-ok" : "is-warning"}">${viable ? "Viável" : "Requer ajuste"}</span></header><div class="motor360-cart-metrics"><div><small>Crédito acumulado</small><b>${formatMoney(credit)} de ${formatMoney(desiredCredit)}</b><em>${creditOk ? "Crédito atendido" : metrics.creditCapacityOk ? `Faltam ${formatMoney(Math.max(0, desiredCredit - credit))}` : assessment.failures.filter((reason) => reason.includes("teto")).join(" · ")}</em></div><div><small>Parcela total</small><b>${formatMoney(installment)}</b><em>${parcelText} · ${installmentChecks}</em></div><div><small>Saldo devedor total</small><b>${formatMoney(balance)}</b></div></div>${assessment.failures.length ? `<p class="motor360-composition-adjustment-reason" role="status">${assessment.failures.join(" · ")}</p>` : ""}<div class="motor360-cart-profiles">${profiles.map((profile) => `<div><strong>${profileLabels[profile.profileId]}</strong><span>Lance ideal: ${formatMoney(profile.requiredTotal)}</span><b class="${profile.gap ? "is-gap" : "is-hit"}">${profile.gap ? `Faltam ${formatMoney(profile.gap)}` : "Lance suficiente"}</b><small>${profile.allocations.map((allocation) => `Grupo ${escapeHtml(allocation.groupId)}: ${formatMoney(allocation.value)}`).join(" · ") || "Sem referência de lance"}</small></div>`).join("")}</div></article>`;
  };
  const totalQuotas = items.reduce((sum, item) => sum + quotaCountFor(item), 0);
  const composition = selectedCompositionScenarioMetrics(items, "without_embedded", desiredCredit);
  return `<section class="motor360-cart-summary"><div class="motor360-cart-heading"><div><span>Composição selecionada</span><h3>${items.length} grupo(s) · ${totalQuotas} cota(s)</h3></div><p>Crédito acumulado: ${formatMoney(composition.credit)} de ${formatMoney(desiredCredit)} · Faltam ${formatMoney(composition.shortfall)} · Total de cotas: ${totalQuotas}. O lance disponível é distribuído proporcionalmente ao lance ideal em cada perfil.</p></div><div class="motor360-cart-scenarios">${scenarioSummary("without_embedded", "Sem lance embutido")}${scenarioSummary("with_embedded", "Com lance embutido")}</div></section>`;
}

function renderSelectedGroupsDecisionVisuals(items) {
  const analytics = items.map(selectedGroupAnalytics);
  const best = [...analytics].sort((a, b) => b.score - a.score)[0];
  const { availableBid: available } = selectedGroupsClientFinancials();
  const profileNames = { conservative: "Conservador", moderate: "Moderado", aggressive: "Agressivo", super_aggressive: "Super agressivo" };
  const cards = Object.entries(profileNames).map(([id, label]) => { const bidGap = best ? profileBidGap(best.item, best.scenario, best.profile(id)) : { ideal: 0, available: 0, gap: 0 }; const covered = bidGap.ideal ? Math.min(100, bidGap.available / bidGap.ideal * 100) : 0; return `<article class="sg-gap-card ${bidGap.gap ? "is-alert" : "is-ok"}"><span>${label}</span><strong>${bidGap.gap ? `Faltam ${formatMoney(bidGap.gap)}` : "Perfil atingido"}</strong><small>Disponível ${formatMoney(bidGap.available)} · Ideal total ${formatMoney(bidGap.ideal)}</small><div><i style="width:${covered}%"></i></div><em>${covered.toFixed(1).replace(".", ",")}% coberto</em></article>`; }).join("");
  const score = best?.score || 0;
  const confidence = score >= 80 ? "Alta" : score >= 60 ? "Média" : "Baixa";
  const bestModerateMeetsBid = best ? profileMeetsBid(best.item, best.scenario, best.profile("moderate")) : false;
  return `<div class="sg-decision-visuals"><div class="sg-alert-banner ${best?.profile("moderate")?.atinge_perfil ? "is-ok" : "is-alert"}"><strong>${best?.profile("moderate")?.atinge_perfil ? "Perfil compatível" : "Nenhum grupo atinge integralmente o perfil"}</strong><span>${best ? `A recomendação do Grupo ${escapeHtml(best.groupId)} é relativa entre os grupos selecionados.` : "Sem dados para recomendar."}</span></div><div class="sg-decision-grid"><article class="sg-panel"><header><div><span>Lance comparativo</span><h3>Disponível x ideal</h3></div></header><div class="sg-gap-cards">${cards}</div></article><article class="sg-panel"><header><div><span>Transparência</span><h3>Nota e confiança</h3></div><small>${confidence}</small></header><div class="sg-score-detail"><strong>${score}/100</strong><span>Confiança ${confidence}</span><div><i style="width:${score}%"></i></div><p>Crédito, histórico e aderência combinados. A nota não representa aprovação financeira.</p></div></article></div></div>`;
}

function selectedGroupsFilterValues() {
  return investorState.selectedGroupFilters || (investorState.selectedGroupFilters = { minCredit: "", maxInstallment: "", maxBid: "", minHistory: "", maxCommitment: "", maxAdmin: "", maxReserve: "", maxTerm: "", administrator: "", compatibleOnly: false });
}

function applySelectedGroupsFiltersAndSort(items) {
  const filters = selectedGroupsFilterValues();
  const metrics = new Map();
  const scenarioFor = (item) => {
    const configured = investorState.selectedGroupScenario;
    if (configured === "with_embedded" || configured === "without_embedded") return configured;
    const selected = [...selectedScenarioIdsForGroup(motor360GroupKey(item))];
    return selected[0] || (item.cenarios || item.scenarios || [])[0]?.id || "without_embedded";
  };
  const filtered = items.filter((item) => {
    const metricKey = `${motor360GroupKey(item)}|${scenarioFor(item)}|${investorState.selectedGroupProfile || "all"}`;
    const entry = metrics.get(metricKey) || selectedGroupAnalytics(item, scenarioFor(item));
    metrics.set(metricKey, entry);
    const scenario = (item.cenarios || []).find((candidate) => candidate.id === scenarioFor(item)) || {};
    const rawInstallment = scenario.parcela_inicial;
    const installmentValue = rawInstallment === null || rawInstallment === undefined || rawInstallment === "" ? null : (typeof rawInstallment === "number" ? rawInstallment : Number(parseNumberInput(rawInstallment)));
    const history = entry.history("moderate");
    const compatible = entry.scenario.credit_compatible === true;
    const commitment = installmentValue == null || !selectedGroupsClientFinancials().income ? null : installmentValue / selectedGroupsClientFinancials().income * 100;
    const adminValue = item.taxa_adm ?? item.taxa_total;
    const reserveValue = item.fundo_reserva;
    const numericMax = (value, limit) => !limit || (value != null && Number.isFinite(Number(value)) && Number(value) <= Number(limit));
    return (!filters.administrator || String(item.administradora || "").toLowerCase().includes(String(filters.administrator).toLowerCase())) && (!filters.minCredit || (entry.groupMaxCredit != null && entry.groupMaxCredit >= Number(filters.minCredit))) && numericMax(installmentValue, filters.maxInstallment) && numericMax(entry.idealBid, filters.maxBid) && (!filters.minHistory || (history > 0 && history >= Number(filters.minHistory))) && (!filters.maxCommitment || (commitment != null && commitment <= Number(filters.maxCommitment))) && (!filters.maxAdmin || (adminValue != null && adminValue !== "" && Number(entry.adminRate) * 100 <= Number(filters.maxAdmin))) && (!filters.maxReserve || (reserveValue != null && reserveValue !== "" && Number(entry.reserveRate) * 100 <= Number(filters.maxReserve))) && (!filters.maxTerm || (item.prazo_restante != null && item.prazo_restante !== "" && Number(item.prazo_restante) <= Number(filters.maxTerm))) && (!filters.compatibleOnly || compatible);
  });
  const sort = investorState.selectedGroupSort || "original";
  const valueFor = (item) => {
    const selectedIds = selectedScenarioIdsForGroup(motor360GroupKey(item));
    const scenarioId = investorState.selectedGroupScenario !== "per_group" && investorState.selectedGroupScenario ? investorState.selectedGroupScenario : [...selectedIds][0];
    const scenario = (item.cenarios || []).find((candidate) => candidate.id === scenarioId) || (item.cenarios || [])[0] || {};
    const raw = scenario.parcela_inicial;
    if (raw === null || raw === undefined || raw === "") return null;
    return typeof raw === "number" ? raw : Number(parseNumberInput(raw));
  };
  const analyticsFor = (item, scenarioId = scenarioFor(item)) => { const key = `${motor360GroupKey(item)}|${scenarioId}|${investorState.selectedGroupProfile || "all"}`; if (!metrics.has(key)) metrics.set(key, selectedGroupAnalytics(item, scenarioId)); return metrics.get(key); };
  if (sort === "bid") return sortMotor360ItemsByBid(filtered);
  return [...filtered].sort((a, b) => {
    if (sort === "score") return analyticsFor(b).score - analyticsFor(a).score;
    if (sort === "credit") return analyticsFor(b).groupMaxCredit - analyticsFor(a).groupMaxCredit;
    if (sort === "installment") return (valueFor(a) == null ? 1 : 0) - (valueFor(b) == null ? 1 : 0) || (valueFor(a) ?? Infinity) - (valueFor(b) ?? Infinity);
    if (sort === "history") return Number(b.capacidade_contemplacoes?.moderate?.media_contemplacoes || 0) - Number(a.capacidade_contemplacoes?.moderate?.media_contemplacoes || 0);
    return 0;
  });
}

function renderMotor360SelectionFilters() {
  const host = document.getElementById("investorPreferencesPanel");
  if (!host) return;
  const existing = host.querySelector("[data-motor360-selection-filters]");
  if (existing) {
    const profileSelect = existing.querySelector('[data-motor360-filter="profile"]');
    const sortSelect = existing.querySelector('[data-motor360-filter="sort"]');
    if (profileSelect) profileSelect.value = investorState.selectedGroupProfile || "all";
    if (sortSelect) sortSelect.value = investorState.selectedGroupSort || "original";
    const bidSortHelp = existing.querySelector("[data-motor360-bid-sort-help]");
    if (bidSortHelp) bidSortHelp.textContent = `Menor lance ideal: lance próprio ideal agregado (${motor360BidSortDescription()}); R$ 0 é válido. Somente lance sem referência calculável fica ao final; crédito e histórico não alteram a posição.`;
    const filters = selectedGroupsFilterValues();
    existing.querySelectorAll("[data-motor360-advanced]").forEach((input) => {
      const value = filters[input.dataset.motor360Advanced];
      if (input.type === "checkbox") input.checked = Boolean(value);
      else input.value = value ?? "";
    });
    return;
  }
  const filters = selectedGroupsFilterValues();
  const panel = document.createElement("details");
  panel.open = true;
  panel.dataset.motor360SelectionFilters = "true";
  panel.className = "motor360-selection-filters";
  panel.innerHTML = `<summary>Filtros para escolha dos grupos</summary><div class="motor360-selection-filter-grid"><label>Perfil em foco<select data-motor360-filter="profile"><option value="all">Todos os perfis</option><option value="conservative">Conservador</option><option value="moderate">Moderado</option><option value="aggressive">Agressivo</option><option value="super_aggressive">Superagressivo</option></select></label><label>Ordenar grupos<select data-motor360-filter="sort"><option value="original">Ordem original</option><option value="score">Melhor aderência</option><option value="credit">Maior crédito</option><option value="installment">Menor parcela</option><option value="bid">Menor lance ideal</option><option value="history">Maior histórico</option></select></label><label>Crédito mínimo<input type="number" data-motor360-advanced="minCredit" value="${filters.minCredit}" min="0" step="1000"></label><label>Parcela máxima<input type="number" data-motor360-advanced="maxInstallment" value="${filters.maxInstallment}" min="0" step="100"></label><label>Lance ideal máximo<input type="number" data-motor360-advanced="maxBid" value="${filters.maxBid}" min="0" step="1000"></label><label>Histórico moderado mínimo<input type="number" data-motor360-advanced="minHistory" value="${filters.minHistory}" min="0" step="0.1"></label><label>Comprometimento máximo (%)<input type="number" data-motor360-advanced="maxCommitment" value="${filters.maxCommitment}" min="0" max="100"></label><label>Taxa adm. máxima (%)<input type="number" data-motor360-advanced="maxAdmin" value="${filters.maxAdmin}" min="0" max="100"></label><label>Fundo reserva máx. (%)<input type="number" data-motor360-advanced="maxReserve" value="${filters.maxReserve}" min="0" max="100"></label><label>Prazo máximo (meses)<input type="number" data-motor360-advanced="maxTerm" value="${filters.maxTerm}" min="0"></label><label class="motor360-filter-check"><input type="checkbox" data-motor360-advanced="compatibleOnly" ${filters.compatibleOnly ? "checked" : ""}> Apenas crédito compatível</label><button type="button" class="btn btn-outline-secondary btn-sm" data-motor360-clear-filters>Limpar filtros</button></div><p class="motor360-bid-sort-help" data-motor360-bid-sort-help aria-live="polite">Menor lance ideal: lance próprio ideal agregado (${motor360BidSortDescription()}); R$ 0 é válido. Somente lance sem referência calculável fica ao final; crédito e histórico não alteram a posição.</p>`;
  host.appendChild(panel);
  panel.querySelector('[data-motor360-filter="profile"]').value = investorState.selectedGroupProfile || "all";
  panel.querySelector('[data-motor360-filter="sort"]').value = investorState.selectedGroupSort || "original";
  let refreshTimer = null;
  const refresh = () => { clearTimeout(refreshTimer); refreshTimer = setTimeout(() => renderInvestorAnalysis(investorState.result), 700); };
  panel.querySelectorAll("[data-motor360-filter]").forEach((input) => input.addEventListener("change", () => { if (input.dataset.motor360Filter === "profile") investorState.selectedGroupProfile = input.value; if (input.dataset.motor360Filter === "sort") investorState.selectedGroupSort = input.value; refresh(); }));
  panel.querySelectorAll("[data-motor360-advanced]").forEach((input) => {
    const update = () => { const currentFilters = selectedGroupsFilterValues(); currentFilters[input.dataset.motor360Advanced] = input.type === "checkbox" ? input.checked : input.value; refresh(); };
    input.addEventListener(input.type === "checkbox" ? "change" : "input", update);
    if (input.type !== "checkbox") input.addEventListener("change", update);
  });
  panel.querySelector("[data-motor360-clear-filters]")?.addEventListener("click", () => { investorState.selectedGroupFilters = { minCredit: "", maxInstallment: "", maxBid: "", minHistory: "", maxCommitment: "", maxAdmin: "", maxReserve: "", maxTerm: "", administrator: "", compatibleOnly: false }; investorState.selectedGroupProfile = "all"; investorState.selectedGroupSort = "original"; investorState.selectedGroupScenario = "per_group"; refresh(); });
}

function renderMotor360FilterNotice(sourceItems, visibleItems) {
  const visibleKeys = new Set(visibleItems.map((item) => motor360GroupKey(item)));
  const hiddenSelected = selectedMotor360Items().filter((item) => !visibleKeys.has(motor360GroupKey(item)));
  const filteredCount = Math.max(0, sourceItems.length - visibleItems.length);
  if (!filteredCount && !hiddenSelected.length) return "";
  const preserved = hiddenSelected.length
    ? `${hiddenSelected.length} grupo(s) selecionado(s) continuam preservados, mas estão ocultos. Limpe ou ajuste os filtros para visualizá-los.`
    : "A seleção permanece preservada enquanto os filtros estiverem ativos.";
  return `<div class="motor360-filter-notice" role="status"><strong>${filteredCount} grupo(s) fora da lista atual pelos filtros.</strong><span>${preserved}</span></div>`;
}

function renderSelectedGroupsScoreBreakdown(items) {
  const dashboard = document.querySelector("[data-sg-dashboard]");
  if (!dashboard || dashboard.querySelector("[data-sg-score-breakdown]")) return;
  const analytics = items.flatMap((item) => [...selectedScenarioIdsForGroup(motor360GroupKey(item))].map((scenarioId) => selectedGroupAnalytics(item, scenarioId)));
  const { client } = selectedGroupsClientFinancials();
  const desiredInstallment = Number(client.parcela_desejada || 0);
  const profileLabels = { investor: "Investidor (36 meses)", conservative: "Conservador (24 meses)", moderate: "Moderado (12 meses)", aggressive: "Agressivo / Rápido (6 meses)", super_aggressive: "Super agressivo / Urgente (3 meses)" };
  const profileOrder = ["investor", "conservative", "moderate", "aggressive", "super_aggressive"];
  const checklist = (entry) => {
    const profileAliases = { investor: ["investor", "investidor"], conservative: ["conservative", "conservador"], moderate: ["moderate", "moderado"], aggressive: ["aggressive", "agressivo", "rapido", "rápido"], super_aggressive: ["super_aggressive", "super-agressivo", "super_agressivo", "urgente"] };
    const findProfile = (scenarioId, profileId) => {
      const values = ((entry.item.cenarios || []).find((scenario) => scenario.id === scenarioId)?.perfis_contemplacao || []);
      return values.find((profile) => profileAliases[profileId].includes(String(profile.id).toLowerCase()) || profileAliases[profileId].includes(String(profile.label || "").toLowerCase())) || {};
    };
    const selectedScenarioIds = [...selectedScenarioIdsForGroup(motor360GroupKey(entry.item))];
    const selectedScenarios = (entry.item.cenarios || []).filter((scenario) => selectedScenarioIds.includes(scenario.id));
    const scenariosForDisplay = selectedScenarios.length ? selectedScenarios : [];
    const allProfiles = (entry.item.cenarios || []).flatMap((scenario) => scenario.perfis_contemplacao || []);
    const profiles = profileOrder.filter((profileId) => profileId === "investor" || allProfiles.some((profile) => profileAliases[profileId].includes(String(profile.id).toLowerCase()) || profileAliases[profileId].includes(String(profile.label || "").toLowerCase())));
    return profiles.map((profileId) => {
      const withoutProfile = findProfile("without_embedded", profileId);
      const withProfile = findProfile("with_embedded", profileId);
      if (!Object.keys(withoutProfile).length && !Object.keys(withProfile).length) {
        return `<section class="sg-profile-check is-unavailable"><h4>${profileLabels[profileId]}</h4><div class="sg-profile-scenarios"><span>Sem embutido: Dados não informados</span><span>Com embutido: Dados não informados</span></div></section>`;
      }
      const selectedProfiles = scenariosForDisplay.map((scenario) => {
        const rawProfile = findProfile(scenario.id, profileId);
        const composition = selectedCompositionScenarioMetrics(items, scenario.id);
        const calculated = composition.entries.find((value) => motor360GroupKey(value.item) === motor360GroupKey(entry.item))?.profiles[profileId];
        return { scenario, profile: Object.keys(rawProfile).length ? { ...rawProfile, lance_ideal: calculated?.ideal ?? Number(rawProfile.lance_ideal || 0) * entry.quotaCount, composition_scaled: Boolean(calculated), composition_available: calculated?.available } : {} };
      }).filter((value) => Object.keys(value.profile).length);
      const profile = selectedProfiles[0]?.profile || {};
      const requiredBids = selectedProfiles.map((value) => ({
        label: value.scenario.id === "with_embedded" ? "Com embutido" : "Sem embutido",
        value: Number(value.profile.lance_ideal || 0),
      }));
      const passingScenarioCount = selectedProfiles.filter((value) => profileMeetsBid(entry.item, value.scenario, value.profile)).length;
      const bidPasses = selectedProfiles.length > 0 && passingScenarioCount === selectedProfiles.length;
      const requiredBidLabel = requiredBids.map((required) => `${required.label}: ${formatMoney(required.value)}`).join(" · ");
      const checks = [
        ["Lance para contemplação", bidPasses, `${selectedProfiles.length > 1 ? `${passingScenarioCount} de ${selectedProfiles.length} cenários atendem. ` : ""}${selectedProfiles.map((value) => `${value.scenario.id === "with_embedded" ? "Com embutido" : "Sem embutido"}: disponível ${formatMoney(allocatedClientBidFor(entry.item, value.scenario, profileId))}`).join(" · ")} · ideal total por cenário: ${requiredBidLabel || "não informado"}`],
        ["Parcela desejada (referência; não reprova)", true, desiredInstallment > 0 ? `Desejada ${formatMoney(desiredInstallment)} · inicial ${formatMoney(entry.installment)}${entry.installment > desiredInstallment ? ` · alerta: ${formatMoney(entry.installment - desiredInstallment)} acima da desejada` : " · dentro da desejada"}` : "Parcela desejada não informada."],
        ["Parcela pós-contemplação (referência)", true, desiredInstallment > 0 && entry.installmentAfter != null ? `Desejada ${formatMoney(desiredInstallment)} · pós-contemplação ${formatMoney(entry.installmentAfter)}${entry.installmentAfter > desiredInstallment ? ` · alerta: ${formatMoney(entry.installmentAfter - desiredInstallment)} acima da desejada` : " · dentro da desejada"}` : "Valor pós-contemplação ou parcela desejada não informado."],
        ["Crédito contratado x crédito desejado", entry.contractedCredit >= entry.desiredCredit, `Contratado ${formatMoney(entry.contractedCredit)} · desejado líquido ${formatMoney(entry.desiredCredit)}`],
      ];
      const scenarioSummary = selectedProfiles.map(({ scenario, profile: value }) => { const meetsBid = profileMeetsBid(entry.item, scenario, value); return `<span>${scenario.id === "with_embedded" ? "Com embutido" : "Sem embutido"}: ${meetsBid ? "Atende" : "Não atende"} · ideal total ${formatMoney(Number(value.lance_ideal || 0))}</span>`; }).join("");
      return `<section class="sg-profile-check"><h4>${profileLabels[profileId]}</h4><div class="sg-profile-scenarios">${scenarioSummary || "<span>Nenhum cenário escolhido</span>"}</div>${checks.map(([label, passes, detail]) => `<div class="sg-check-item ${passes ? "is-ok" : "is-fail"}"><span><b aria-hidden="true">${passes ? "✓" : "×"}</b>${label}</span><strong>${passes ? "Atende" : "Não atende"}</strong><small>${detail}</small></div>`).join("")}</section>`;
    }).join("");
  };
  const factors = [
    ["Crédito", "creditFit", "Compara o crédito líquido calculado com o crédito desejado pelo cliente. Fórmula: crédito disponível dividido pelo crédito desejado, limitado a 100%. Peso: 30%."],
    ["Parcela", "installmentFit", "Compara a parcela inicial do grupo com a parcela máxima aceita pelo cliente. Fórmula: parcela máxima dividida pela parcela inicial, limitado a 100%. Peso: 20%."],
    ["Lance", "bidFit", "Compara o lance disponível do cliente com o lance ideal do perfil selecionado. Fórmula: lance disponível dividido pelo lance ideal, limitado a 100%. Peso: 20%."],
    ["Histórico", "historyFit", "Mede a média de contemplações do grupo na janela moderada de 12 meses. Fórmula: média informada dividida por 6, limitada a 100%. Peso: 15%."],
    ["Custo", "costFit", "Mede o impacto da taxa de administração. Fórmula: 1 menos a taxa administrativa dividida por 30%, limitada entre 0% e 100%. Peso: 5%."],
    ["Prazo", "termFit", "Compara o prazo restante do grupo com a referência de 240 meses. Fórmula: prazo restante dividido por 240, limitado a 100%. Peso: 5%."]
  ];
  const panel = document.createElement("article");
  panel.dataset.sgScoreBreakdown = "true";
  panel.className = "sg-panel sg-score-breakdown";
  const compactProfiles = ["conservative", "moderate", "aggressive", "super_aggressive"];
  const compactLabels = { conservative: "Conservador · 24m", moderate: "Moderado · 12m", aggressive: "Rápido · 6m", super_aggressive: "Urgente · 3m" };
  const compactTable = analytics.map((entry) => { const scenarioClass = entry.scenario.id === "with_embedded" ? "sg-scenario-with-embedded" : "sg-scenario-without-embedded"; const scenarioLabel = entry.scenario.id === "with_embedded" ? "Com embutido" : "Sem embutido"; return `<tr class="${scenarioClass}"><th>Grupo ${escapeHtml(entry.groupId)}<small>${escapeHtml(entry.item.administradora || "-")} · <span class="sg-scenario-label">${scenarioLabel}</span></small></th>${compactProfiles.map((profileId) => { const profile = entry.profile(profileId); const bidGap = profileBidGap(entry.item, entry.scenario, profile); const ok = bidGap.gap === 0 && bidGap.ideal > 0; return `<td class="${ok ? "is-ok" : "is-fail"}"><b>${ok ? "✓" : "×"}</b><span>${bidGap.ideal ? formatMoney(bidGap.ideal) : "Sem dado"}</span>${!ok && bidGap.ideal ? `<button type="button" class="sg-info sg-compact-info" aria-label="Ver valor faltante" data-tooltip="Faltam ${formatMoney(bidGap.gap)} para atingir o lance ideal total. Disponível: ${formatMoney(bidGap.available)} · Ideal: ${formatMoney(bidGap.ideal)}">i</button>` : ""}</td>`; }).join("")}<td><strong>${formatMoney(entry.installment)}</strong><small>Pós ${formatMoney(entry.installmentAfter)}</small></td><td><strong>${entry.contractedCredit >= entry.desiredCredit ? "✓" : "×"}</strong><small>${formatMoney(entry.contractedCredit)}</small></td></tr>`; }).join("");
  const compactView = `<div class="sg-compact-summary"><p>Visão resumida dos ${items.length} grupo(s) selecionado(s). O valor em cada perfil é o lance ideal; ✓ indica que o lance disponível atende.</p><div class="sg-compact-table-wrap"><table class="sg-compact-table"><thead><tr><th>Grupo</th>${compactProfiles.map((id) => `<th>${compactLabels[id]}</th>`).join("")}<th>Parcelas</th><th>Crédito contratado</th></tr></thead><tbody>${compactTable}</tbody></table></div><details><summary>Ver checklist detalhado por grupo</summary><div class="sg-check-grid">${analytics.map((entry) => `<div class="sg-check-column"><strong>Grupo ${escapeHtml(entry.groupId)}</strong>${checklist(entry)}</div>`).join("")}</div></details></div>`;
  panel.innerHTML = `<header><div><span>Transparência</span><h3>Checklist de conformidade e assertividade</h3></div><small>Comparativo dos cenários financeiros em todos os perfis</small></header>${compactView}`;
  dashboard.appendChild(panel);
}

function renderSelectedGroupsRecommendationBoard(items) {
  const dashboard = document.querySelector("[data-sg-dashboard]");
  if (!dashboard || dashboard.querySelector("[data-sg-recommendations]")) return;
  const analytics = items.map(selectedGroupAnalytics);
  const recommendations = [
    ["Melhor grupo geral", [...analytics].sort((a, b) => b.score - a.score)[0]],
    ["Menor parcela", [...analytics].sort((a, b) => a.installment - b.installment)[0]],
    ["Contemplação mais rápida", [...analytics].sort((a, b) => b.history("urgent") - a.history("urgent"))[0]],
    ["Menor lance ideal", [...analytics].sort((a, b) => a.idealBid - b.idealBid)[0]],
    ["Maior crédito", [...analytics].sort((a, b) => b.credit - a.credit)[0]],
    ["Menor comprometimento", [...analytics].sort((a, b) => (a.incomeCommitment || 1) - (b.incomeCommitment || 1))[0]],
    ["Melhor custo-benefício", [...analytics].sort((a, b) => (b.credit / Math.max(b.installment, 1)) - (a.credit / Math.max(a.installment, 1)))[0]],
  ];
  const panel = document.createElement("article");
  panel.dataset.sgRecommendations = "true";
  panel.className = "sg-panel sg-recommendation-board";
  panel.innerHTML = `<header><div><span>Recomendação</span><h3>Melhor grupo por objetivo</h3></div><small>A escolha muda conforme a prioridade do cliente.</small></header><div class="sg-recommendation-cards">${recommendations.map(([label, entry]) => entry ? `<div><span>${label}</span><strong>Grupo ${escapeHtml(entry.groupId)}</strong><small>Nota ${entry.score}/100 · Crédito ${formatMoney(entry.credit)} · Parcela ${formatMoney(entry.installment)}</small></div>` : "").join("")}</div>`;
  dashboard.appendChild(panel);
}

function renderSelectedGroupsBidScenarios(items) {
  const dashboard = document.querySelector("[data-sg-dashboard]");
  if (!dashboard || dashboard.querySelector("[data-sg-bid-scenarios]")) return;
  const { own, fgts } = selectedGroupsClientFinancials();
  const total = own + fgts;
  const analytics = items.map(selectedGroupAnalytics);
  const scenarios = [["Somente recursos próprios", own], ["Somente FGTS", fgts], ["Recursos próprios + FGTS", total]];
  const panel = document.createElement("article");
  panel.dataset.sgBidScenarios = "true";
  panel.className = "sg-panel sg-bid-scenarios";
  panel.innerHTML = `<header><div><span>Cenários de lance</span><h3>Recursos disponíveis x lance ideal</h3></div><small>O embutido é demonstrado separadamente em cada grupo.</small></header><div class="sg-bid-scenario-grid">${scenarios.map(([label, available]) => `<div class="sg-bid-scenario"><strong>${label}</strong><b>${formatMoney(available)}</b><div>${analytics.map((entry) => { const coverage = entry.idealBid > 0 ? Math.min(100, available / entry.idealBid * 100) : 0; const status = coverage >= 100 ? "Suficiente" : coverage >= 80 ? "Próximo" : coverage >= 50 ? "Baixo" : "Insuficiente"; return `<span><em>Grupo ${escapeHtml(entry.groupId)}</em><i><b style="width:${coverage}%"></b></i><small>${coverage.toFixed(0)}% · ${status}</small></span>`; }).join("")}</div></div>`).join("")}</div><div class="sg-bid-embedded-note">Lance embutido considerado nos cenários: consulte o comparativo “Com lance embutido” para verificar a redução do crédito líquido.</div>`;
  dashboard.appendChild(panel);
}

function renderSelectedGroupsRiskProbability(items) {
  const dashboard = document.querySelector("[data-sg-dashboard]");
  if (!dashboard || dashboard.querySelector("[data-sg-risk-probability]")) return;
  const panel = document.createElement("article");
  panel.dataset.sgRiskProbability = "true";
  panel.className = "sg-panel sg-risk-probability";
  const analytics = items.map(selectedGroupAnalytics);
  panel.innerHTML = `<header><div><span>Risco e contemplação</span><h3>Estimativa comparativa por grupo</h3></div><small>Baseada na cobertura do lance e nas médias históricas; não representa garantia.</small></header><div class="sg-risk-probability-grid">${analytics.map((entry) => `<div><strong>Grupo ${escapeHtml(entry.groupId)}</strong><span class="sg-probability-value">${entry.probability}%</span><small>Chance relativa · ${entry.probabilityLabel}</small><i><b style="width:${entry.probability}%"></b></i><em>Risco financeiro: ${entry.riskLabel}</em></div>`).join("")}</div>`;
  dashboard.appendChild(panel);
}

function renderSelectedGroupsCoverageCharts(items) {
  const dashboard = document.querySelector("[data-sg-dashboard]");
  if (!dashboard || !window.echarts || dashboard.querySelector("[data-sg-coverage-charts]")) return;
  const analytics = items.map(selectedGroupAnalytics);
  const embeddedImpact = analytics.map((entry) => {
    const scenario = (entry.item.cenarios || []).find((value) => value.id === "with_embedded");
    const rawCredit = scenario?.credito_liquido_projetado ?? scenario?.credito_contratado ?? scenario?.credito_maximo ?? 0;
    const embeddedCredit = Number.isFinite(Number(rawCredit)) ? Number(rawCredit) * entry.quotaCount : 0;
    const before = Number.isFinite(Number(entry.credit)) ? Number(entry.credit) : 0;
    return { after: embeddedCredit, reduction: Math.max(0, before - embeddedCredit) };
  });
  const panel = document.createElement("div");
  panel.dataset.sgCoverageCharts = "true";
  panel.className = "sg-chart-grid sg-coverage-charts";
  panel.innerHTML = `<article class="sg-panel"><header><div><span>Adequação</span><h3>Crédito desejado x disponível</h3></div><small>Percentual de atendimento por grupo</small></header><div class="sg-chart" id="sgCreditCoverageChart" role="img" aria-label="Cobertura do crédito"></div></article><article class="sg-panel"><header><div><span>Lance embutido</span><h3>Crédito antes x depois do embutido</h3></div><small>Impacto sobre o crédito líquido</small></header><div class="sg-chart" id="sgEmbeddedImpactChart" role="img" aria-label="Impacto do lance embutido"></div></article>`;
  dashboard.appendChild(panel);
  const init = (id, option) => { const element = document.getElementById(id); if (!element) return; try { const chart = window.echarts.init(element, null, { renderer: "svg" }); chart.setOption(option); selectedGroupsCharts.push(chart); } catch (error) { console.error("[selected-groups-chart]", id, error); element.innerHTML = '<div class="sg-chart-error">Dados indisponíveis para este gráfico.</div>'; } };
  const labels = analytics.map((entry) => `Grupo ${entry.groupId}`);
  init("sgCreditCoverageChart", { grid: { left: 90, right: 25, top: 20, bottom: 30 }, tooltip: { trigger: "axis", valueFormatter: (v) => `${Number(v).toFixed(1)}%` }, xAxis: { type: "value", max: 120, axisLabel: { formatter: "{value}%" } }, yAxis: { type: "category", data: labels }, series: [{ type: "bar", data: analytics.map((entry) => ({ value: entry.creditFit * 100, itemStyle: { color: entry.creditFit >= 1 ? "#1d9b59" : "#ef7a24" } })), label: { show: true, position: "right", formatter: ({ value }) => `${Number(value).toFixed(0)}%` } }] });
  init("sgEmbeddedImpactChart", { animationDuration: 420, grid: { left: 90, right: 25, top: 20, bottom: 42 }, legend: { bottom: 0 }, tooltip: { trigger: "axis", axisPointer: { type: "shadow" }, valueFormatter: (v) => formatMoney(v) }, xAxis: { type: "category", data: labels }, yAxis: { type: "value", name: "Valor (R$)", axisLabel: { formatter: (v) => formatMoney(v) } }, series: [{ name: "Crédito após embutido", type: "bar", stack: "credit", data: embeddedImpact.map((value) => value.after), itemStyle: { color: "#1d7188" }, label: { show: true, position: "inside", formatter: ({ value }) => value ? formatMoney(value) : "" } }, { name: "Redução pelo embutido", type: "bar", stack: "credit", data: embeddedImpact.map((value) => value.reduction), itemStyle: { color: "#ef7a24" }, label: { show: true, position: "inside", formatter: ({ value }) => value ? formatMoney(value) : "" } }] });
}

function renderSelectedGroupsFinalMatrix(items) {
  const dashboard = document.querySelector("[data-sg-dashboard]");
  if (!dashboard || dashboard.querySelector("[data-sg-final-matrix]")) return;
  const analytics = items.map(selectedGroupAnalytics);
  const labels = analytics.map((entry) => `Grupo ${entry.groupId}`);
  const panel = document.createElement("div");
  panel.dataset.sgFinalMatrix = "true";
  panel.className = "sg-chart-grid sg-final-matrix";
  panel.innerHTML = `<article class="sg-panel"><header><div><span>Síntese</span><h3>Heatmap de critérios</h3></div><small>Verde indica melhor adequação relativa entre os grupos.</small></header><div class="sg-chart" id="sgCriteriaHeatmap" role="img" aria-label="Heatmap de critérios"></div></article><article class="sg-panel"><header><div><span>Perfis</span><h3>Cenários de contemplação</h3></div><small>Lance ideal e cobertura por perfil.</small></header><div class="sg-chart" id="sgProfileScenarioChart" role="img" aria-label="Cenários por perfil"></div></article><article class="sg-panel"><header><div><span>Orçamento</span><h3>Compatibilidade financeira</h3></div><small>Parcelas comparadas à capacidade financeira do cliente.</small></header><div class="sg-chart" id="sgFinancialCompatibilityChart" role="img" aria-label="Compatibilidade financeira por grupo"></div></article><article class="sg-panel"><header><div><span>Contemplação</span><h3>Lance disponível x lance ideal</h3></div><small>Composição do lance e referência do perfil selecionado.</small></header><div class="sg-chart" id="sgBidComparisonChart" role="img" aria-label="Lance disponível versus lance ideal"></div></article>`;
  dashboard.appendChild(panel);
  if (!window.echarts) {
    const renderBars = (id, title, rows) => {
      const element = document.getElementById(id);
      if (!element) return;
      element.classList.add("sg-static-chart");
      element.innerHTML = `<div class="sg-static-legend">${rows.map((row) => `<span><i style="background:${row.color}"></i>${row.name}</span>`).join("")}</div>${analytics.map((entry, index) => `<div class="sg-static-group"><strong>Grupo ${escapeHtml(entry.groupId)}</strong>${rows.map((row) => { const value = Number(row.values[index] || 0); const max = Math.max(...rows.flatMap((item) => item.values), 1); return `<div class="sg-static-bar"><small>${row.name}</small><b><i style="width:${Math.min(100, value / max * 100)}%;background:${row.color}"></i></b><em>${formatMoney(value)}</em></div>`; }).join("")}</div>`).join("")}`;
    };
    const client = investorState.result?.cliente || {};
    const desired = Number(client.parcela_desejada || 0);
    const income = Number(client.renda_total || client.renda || 0);
    const maxInstallment = Number(client.parcela_maxima || 0);
    renderBars("sgFinancialCompatibilityChart", "Compatibilidade financeira", [
      { name: "Parcela desejada", color: "#4f6fdc", values: analytics.map(() => desired) },
      { name: "Parcela inicial", color: "#ef7a24", values: analytics.map((entry) => entry.installment) },
      { name: "Pós-contemplação", color: "#1d9b59", values: analytics.map((entry) => entry.installmentAfter) },
      { name: "Renda disponível", color: "#65717a", values: analytics.map(() => income || maxInstallment) },
    ]);
    const { own, fgts } = selectedGroupsClientFinancials();
    const focusProfile = investorState.selectedGroupProfile && investorState.selectedGroupProfile !== "all" ? investorState.selectedGroupProfile : "moderate";
    renderBars("sgBidComparisonChart", "Lance disponível x lance ideal", [
      { name: "Lance próprio", color: "#4f6fdc", values: analytics.map(() => own) },
      { name: "Lance FGTS", color: "#a8cf32", values: analytics.map(() => fgts) },
      { name: "Lance embutido", color: "#ef7a24", values: analytics.map((entry) => entry.embedded) },
      { name: "Lance total", color: "#1d7188", values: analytics.map((entry) => entry.bid) },
      { name: "Lance ideal", color: "#b42318", values: analytics.map((entry) => Number(entry.profile(focusProfile).lance_ideal || 0) * entry.quotaCount) },
    ]);
    return;
  }
  const init = (id, option) => { const element = document.getElementById(id); if (!element) return; try { const chart = window.echarts.init(element, null, { renderer: "svg" }); chart.setOption(option); selectedGroupsCharts.push(chart); } catch (error) { console.error("[selected-groups-chart]", id, error); element.innerHTML = '<div class="sg-chart-error">Dados indisponíveis para este gráfico.</div>'; } };
  const criteria = [["Crédito", "creditFit"], ["Parcela", "installmentFit"], ["Lance", "bidFit"], ["Histórico", "historyFit"], ["Custo", "costFit"], ["Prazo", "termFit"]];
  init("sgCriteriaHeatmap", { grid: { left: 82, right: 20, top: 20, bottom: 48 }, tooltip: { position: "top", formatter: (p) => `${p.name}<br/>${criteria[p.value[0]][0]}: ${Number(p.value[2]).toFixed(0)}%` }, xAxis: { type: "category", data: criteria.map((c) => c[0]), splitArea: { show: true } }, yAxis: { type: "category", data: analytics.map((e) => `Grupo ${e.groupId}`), splitArea: { show: true } }, visualMap: { min: 0, max: 1, calculable: false, orient: "horizontal", left: "center", bottom: 0, inRange: { color: ["#f7d9c1", "#fff1e5", "#b9e3c8"] } }, series: [{ type: "heatmap", data: analytics.flatMap((entry, row) => criteria.map(([, key], col) => [col, row, Number(entry[key] || 0)])), label: { show: true, formatter: (p) => `${Math.round(p.value[2] * 100)}%` } }] });
  const profiles = [["Conservador", "conservative"], ["Moderado", "moderate"], ["Agressivo", "aggressive"], ["Superagressivo", "super_aggressive"]];
  init("sgProfileScenarioChart", { grid: { left: 90, right: 20, top: 20, bottom: 48 }, legend: { bottom: 0 }, tooltip: { trigger: "axis", valueFormatter: (v) => formatMoney(v) }, xAxis: { type: "category", data: analytics.map((e) => `Grupo ${e.groupId}`) }, yAxis: { type: "value", axisLabel: { formatter: (v) => formatMoney(v) } }, series: profiles.map(([name, id]) => ({ name, type: "bar", data: analytics.map((entry) => Number(entry.profile(id).lance_ideal || 0) * entry.quotaCount), barMaxWidth: 22 })) });
  const { client, own, fgts, availableBid } = selectedGroupsClientFinancials();
  const desiredInstallment = Number(client.parcela_desejada || 0);
  const maxInstallment = Number(client.parcela_maxima || 0);
  const financialData = analytics.map((entry) => ({ desired: desiredInstallment, initial: entry.installment, after: entry.installmentAfter, income: Number(client.renda_total || client.renda || 0) }));
  init("sgFinancialCompatibilityChart", { grid: { left: 92, right: 20, top: 38, bottom: 52 }, legend: { bottom: 0 }, tooltip: { trigger: "axis", axisPointer: { type: "shadow" }, valueFormatter: (v) => formatMoney(v) }, xAxis: { type: "category", data: labels }, yAxis: { type: "value", name: "Valor (R$)", axisLabel: { formatter: (v) => formatMoney(v) } }, series: [{ name: "Parcela máxima desejada", type: "bar", data: financialData.map((d) => d.desired), itemStyle: { color: "#4f6fdc" } }, { name: "Parcela inicial", type: "bar", data: financialData.map((d) => d.initial), itemStyle: { color: "#ef7a24" } }, { name: "Parcela pós-contemplação", type: "bar", data: financialData.map((d) => d.after), itemStyle: { color: "#1d9b59" } }, { name: "Renda disponível", type: "bar", data: financialData.map((d) => d.income), itemStyle: { color: "#65717a" } }] });
  const focusProfile = investorState.selectedGroupProfile && investorState.selectedGroupProfile !== "all" ? investorState.selectedGroupProfile : "moderate";
  init("sgBidComparisonChart", { grid: { left: 92, right: 20, top: 38, bottom: 52 }, legend: { bottom: 0 }, tooltip: { trigger: "axis", axisPointer: { type: "shadow" }, valueFormatter: (v) => formatMoney(v) }, xAxis: { type: "category", data: labels }, yAxis: { type: "value", name: "Valor (R$)", axisLabel: { formatter: (v) => formatMoney(v) } }, series: [{ name: "Lance próprio", type: "bar", stack: "available", data: analytics.map((entry) => Number(own) * entry.quotaCount), itemStyle: { color: "#4f6fdc" } }, { name: "Lance FGTS", type: "bar", stack: "available", data: analytics.map((entry) => Number(fgts) * entry.quotaCount), itemStyle: { color: "#a8cf32" } }, { name: "Lance embutido", type: "bar", data: analytics.map((entry) => entry.embedded), itemStyle: { color: "#ef7a24" } }, { name: "Lance total", type: "line", data: analytics.map((entry) => entry.bid), itemStyle: { color: "#1d7188" }, lineStyle: { width: 3 } }, { name: "Lance ideal", type: "line", data: analytics.map((entry) => Number(entry.profile(focusProfile).lance_ideal || 0) * entry.quotaCount), itemStyle: { color: "#b42318" }, lineStyle: { width: 3, type: "dashed" } }] });
}

function renderSelectedGroupsExecutiveAudit(items) {
  const dashboard = document.querySelector("[data-sg-dashboard]");
  if (!dashboard || dashboard.querySelector("[data-sg-executive-audit]")) return;
  const analytics = items.map(selectedGroupAnalytics);
  const best = [...analytics].sort((a, b) => b.score - a.score)[0];
  const client = investorState.result?.cliente || {};
  const warnings = [];
  analytics.forEach((entry) => {
    if (!entry.scenario.credit_compatible) warnings.push(`Grupo ${entry.groupId}: crédito fora da faixa no cenário selecionado.`);
    if (!entry.item.capacidade_contemplacoes) warnings.push(`Grupo ${entry.groupId}: histórico de contemplações não informado.`);
    if (!entry.item.taxa_adm && !entry.item.taxa_total) warnings.push(`Grupo ${entry.groupId}: taxa de administração não informada.`);
    if (entry.scenario.id === "with_embedded" && !entry.scenario.lance_embutido) warnings.push(`Grupo ${entry.groupId}: lance embutido não calculado.`);
  });
  const dataQuality = Math.max(0, 100 - warnings.length * 15);
  const confidence = dataQuality >= 85 && best?.score >= 70 ? "Alta" : dataQuality >= 60 ? "Média" : "Baixa";
  const panel = document.createElement("article");
  panel.dataset.sgExecutiveAudit = "true";
  panel.className = "sg-panel sg-executive-audit";
  panel.innerHTML = `<header><div><span>Painel executivo</span><h3>Decisão orientada por dados</h3></div><small>Confiança da análise: ${confidence}</small></header><div class="sg-executive-grid"><div><span>Grupo recomendado</span><strong>${best ? `Grupo ${escapeHtml(best.groupId)}` : "Não determinado"}</strong><small>${best ? `${best.score}/100 · ${best.scoreLabel}` : "Sem dados suficientes"}</small></div><div><span>Principal justificativa</span><strong>${best ? `Aderência de ${best.score}/100` : "Não disponível"}</strong><small>${best ? `Crédito ${Math.round(best.creditFit * 100)}% · lance ${Math.round(best.bidFit * 100)}%` : ""}</small></div><div><span>Qualidade dos dados</span><strong>${dataQuality}%</strong><small>${warnings.length ? `${warnings.length} alerta(s)` : "Sem alertas críticos"}</small></div><div><span>Decisão</span><strong>${best && best.score >= 65 && !warnings.length ? "Elegível para recomendação" : "Exige validação manual"}</strong><small>O dashboard não substitui a conferência dos dados de origem.</small></div></div>${warnings.length ? `<div class="sg-data-alerts"><strong>Alertas de qualidade</strong>${warnings.map((warning) => `<span>${escapeHtml(warning)}</span>`).join("")}</div>` : `<div class="sg-data-ok">Dados essenciais disponíveis para comparação relativa.</div>`}</article>`;
  dashboard.insertBefore(panel, dashboard.children[1] || null);
}

function renderSelectedGroupsAuditButton(items) {
  const results = document.getElementById("selectedGroupsResults");
  if (!results || !items.length || results.querySelector("[data-sg-audit-export]")) return;
  const button = document.createElement("button");
  button.type = "button";
  button.className = "sg-audit-export";
  button.dataset.sgAuditExport = "true";
  button.textContent = "Baixar log de auditoria";
  button.title = "Exporta o perfil, grupos, cenários, filtros e métricas usados nos gráficos";
  button.addEventListener("click", () => {
    const audit = { generated_at: new Date().toISOString(), scenario: investorState.selectedGroupScenario || "per_group", profile: investorState.selectedGroupProfile || "all", sort: investorState.selectedGroupSort || "original", filters: investorState.selectedGroupFilters || {}, client: investorState.result?.cliente || {}, groups: items.map((item) => ({ group_id: item.grupo || item.grupo_id, administrator: item.administradora, quotas: quotaCountFor(item), selected_scenario_ids: [...selectedScenarioIdsForGroup(motor360GroupKey(item))], raw_group: item, analytics: selectedGroupAnalytics(item) })) };
    const blob = new Blob([JSON.stringify(audit, null, 2)], { type: "application/json;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `crediclass-auditoria-grupos-${new Date().toISOString().replace(/[:.]/g, "-")}.json`;
    link.click();
    URL.revokeObjectURL(url);
  });
  results.appendChild(button);
}

function renderSelectedGroupsSafely(label, renderer, items) {
  try { renderer(items); } catch (error) { console.error(`[selected-groups-render] ${label}`, error); }
}

function renderSelectedGroupsScreen() {
  const empty = document.getElementById("selectedGroupsEmpty");
  const results = document.getElementById("selectedGroupsResults");
  if (!empty || !results) return;
  if (investorState.selectedGroupIds.size && !investorState.result) {
    empty.classList.remove("d-none");
    empty.querySelector("p").textContent = "A análise do Motor 360 está sendo recalculada. Os grupos selecionados serão exibidos quando os dados estiverem prontos.";
    results.classList.add("d-none");
    results.innerHTML = "";
    return;
  }
  const items = selectedMotor360Items();
  if (!items.length && investorState.selectedGroupIds.size) {
    empty.classList.add("d-none");
    results.classList.remove("d-none");
    results.innerHTML = '<section class="sg-dashboard sg-filter-empty-dashboard" data-sg-dashboard><div class="sg-filter-empty"><strong>Nenhum grupo atende aos filtros atuais.</strong><span>A seleção continua preservada. Ajuste os filtros ou use “Limpar filtros” para voltar a visualizar os grupos.</span></div></section>';
    return;
  }
  empty.classList.toggle("d-none", items.length > 0);
  results.classList.toggle("d-none", items.length === 0);
  results.innerHTML = items.length ? `${renderSelectedGroupsAnalyticalPanel(items)}${renderSelectedGroupsCartSummary(items)}` : "";
  results.querySelectorAll(".selected-comparison-column").forEach((column) => {
    const title = column.querySelector("h3");
    const groupId = title?.textContent?.replace(/[^0-9A-Za-z_-]/g, "").trim();
    if (!groupId || column.querySelector("[data-selected-group-anchor]")) return;
    const button = document.createElement("button");
    button.type = "button";
    button.className = "selected-group-jump";
    button.textContent = "Ir para o grupo";
    button.addEventListener("click", () => { closeSelectedGroupsWorkspace(); focusMotor360Group(motor360GroupAnchorId(groupId)); });
    title?.parentElement?.appendChild(button);
  });
  const scenarioFact = results.querySelector(".sg-fact-strip span:nth-child(2) b");
  if (scenarioFact) scenarioFact.textContent = "Por grupo";
  renderSelectedGroupsECharts(items);
  renderSelectedGroupsSafely("extra-visuals", renderSelectedGroupsExtraVisuals, items);
  if (items.length) renderSelectedGroupsScoreBreakdown(items);
  if (items.length) renderSelectedGroupsBidScenarios(items);
  if (items.length) renderSelectedGroupsRiskProbability(items);
  if (items.length) renderSelectedGroupsSafely("coverage-charts", renderSelectedGroupsCoverageCharts, items);
  if (items.length) renderSelectedGroupsSafely("final-matrix", renderSelectedGroupsFinalMatrix, items);
  if (items.length) renderSelectedGroupsAuditButton(items);
  results.querySelectorAll("[data-sg-metric]").forEach((button) => button.addEventListener("click", () => {
    investorState.selectedGroupMetric = button.dataset.sgMetric || "credit";
    results.querySelectorAll("[data-sg-metric]").forEach((candidate) => candidate.setAttribute("aria-pressed", String(candidate === button)));
    renderSelectedGroupsECharts(items);
  }));
}

function persistMotor360Selection() {
  localStorage.setItem("crediclass.motor360.selectedGroups", JSON.stringify([...investorState.selectedGroupIds]));
  localStorage.setItem("crediclass.motor360.selectedScenarios", JSON.stringify(Object.fromEntries(investorState.selectedScenarioIds)));
  localStorage.setItem("crediclass.motor360.quotaCounts", JSON.stringify(Object.fromEntries(investorState.quotaCounts)));
  localStorage.setItem("crediclass.motor360.selectedGroupData", JSON.stringify(Object.fromEntries(investorState.selectedGroupData)));
  localStorage.setItem("crediclass.motor360.administrator", investorState.administrator || "");
}

function selectedScenarioIdsForGroup(groupId) {
  const value = investorState.selectedScenarioIds.get(String(groupId));
  return new Set(Array.isArray(value) ? value : []);
}

function quotaCountFor(itemOrGroup) {
  const key = typeof itemOrGroup === "string" ? itemOrGroup : motor360GroupKey(itemOrGroup);
  return Math.min(50, Math.max(1, Number(investorState.quotaCounts.get(key) || 1)));
}

function minimumQuotasFor(item, scenarioId = null) {
  const scenario = scenarioId === "with_embedded" ? "cotas_minimas_com_embutido" : "cotas_minimas_sem_embutido";
  const value = Number(item?.[scenario] ?? 1);
  return Number.isFinite(value) && value > 0 ? Math.ceil(value) : 1;
}

function suggestedCompositionQuotas(item, scenarioId = "without_embedded") {
  const otherItems = selectedMotor360Items().filter((entry) => motor360GroupKey(entry) !== motor360GroupKey(item));
  if (!otherItems.length) return minimumQuotasFor(item, scenarioId);
  const client = motor360ClientProfile();
  const desired = Number(client.credito_liquido_desejado || 0);
  const perQuotaCapacity = Number(item?.credito_maximo || 0);
  if (desired <= 0 || perQuotaCapacity <= 0) return 1;
  let combinedCapacity = otherItems.reduce((sum, entry) => sum + Number(entry.credito_maximo || 0) * quotaCountFor(entry), 0) + perQuotaCapacity;
  for (const entry of otherItems) {
    const key = motor360GroupKey(entry);
    const capacity = Number(entry.credito_maximo || 0);
    let quotas = quotaCountFor(entry);
    while (quotas > 1 && combinedCapacity - capacity >= desired) {
      quotas -= 1;
      combinedCapacity -= capacity;
      investorState.quotaCounts.set(key, quotas);
    }
  }
  const alreadyCovered = combinedCapacity - perQuotaCapacity;
  const remaining = Math.max(0, desired - alreadyCovered);
  if (remaining <= 0) return 1;
  return Math.min(50, Math.max(1, Math.ceil(remaining / perQuotaCapacity)));
}

function clientResourceTotal() {
  const client = investorState.result?.cliente || {};
  return Number(client.lance_cliente_total ?? client.lance_total ?? client.own_resources_total ?? 0) || 0;
}

function scenarioTotalBidFor(item, scenario) {
  return allocatedClientBidFor(item, scenario) + Number(scenario?.lance_embutido || 0) * quotaCountFor(item);
}

function allocationProfileId() {
  const aliases = { urgent: "super_aggressive", fast: "aggressive", moderate: "moderate", conservative: "conservative", long_term: "investor" };
  return aliases[investorState.result?.perfil_contemplacao] || investorState.result?.perfil_contemplacao || "moderate";
}

function allocatedClientBidFor(item, scenario, profileId = allocationProfileId()) {
  const selectedItems = selectedMotor360Items();
  if (!selectedItems.some((entry) => motor360GroupKey(entry) === motor360GroupKey(item))) return clientResourceTotal();
  const requirements = selectedItems.map((entry) => {
    const selectedScenario = (entry.cenarios || []).find((candidate) => candidate.id === scenario?.id);
    const profile = (selectedScenario?.perfis_contemplacao || []).find((candidate) => candidate.id === profileId);
    return { entry, required: Number(profile?.lance_ideal || 0) * quotaCountFor(entry) };
  }).filter((entry) => entry.required > 0);
  const totalRequired = requirements.reduce((total, entry) => total + entry.required, 0);
  const current = requirements.find((entry) => motor360GroupKey(entry.entry) === motor360GroupKey(item));
  if (!current || totalRequired <= 0) return clientResourceTotal();
  return clientResourceTotal() * current.required / totalRequired;
}

function profileMeetsBid(item, scenario, profile) {
  const ideal = profile?.composition_scaled ? Number(profile.lance_ideal || 0) : Number(profile?.lance_ideal || 0) * quotaCountFor(item);
  const available = profile?.composition_scaled ? Number(profile.composition_available || 0) : allocatedClientBidFor(item, scenario, profile?.id);
  return ideal > 0 && available >= ideal;
}

function profileBidGap(item, scenario, profile) {
  const ideal = profile?.composition_scaled ? Number(profile.lance_ideal || 0) : Number(profile?.lance_ideal || 0) * quotaCountFor(item);
  const available = profile?.composition_scaled ? Number(profile.composition_available || 0) : allocatedClientBidFor(item, scenario, profile?.id);
  return { ideal, available, gap: Math.max(0, ideal - available) };
}

function selectedScenariosForItem(item) {
  const ids = selectedScenarioIdsForGroup(motor360GroupKey(item));
  return (item?.cenarios || []).filter((scenario) => ids.has(scenario.id));
}

function updateMotor360SelectionSummary() {
  const summary = document.getElementById("motor360SelectionSummary");
  const totalQuotas = [...investorState.selectedGroupIds].reduce((total, id) => total + Math.min(50, Math.max(1, Number(investorState.quotaCounts.get(id) || 1))), 0);
  if (summary) summary.textContent = `${investorState.selectedGroupIds.size} grupo(s) · ${totalQuotas} cota(s) selecionada(s) para a próxima etapa`;
}

function renderMotor360ChanceChart(items) {
  const groups = (items || []).filter((item) => Array.isArray(item.cenarios) && item.cenarios.length);
  if (!groups.length) return "";
  const profileIds = ["conservative", "moderate", "aggressive", "super_aggressive"];
  const profileLabels = {
    conservative: "Conservador",
    moderate: "Moderado",
    aggressive: "Agressivo",
    super_aggressive: "Super Agressivo",
  };
  const profileColors = {
    conservative: "#4f6872",
    moderate: "#1d9b59",
    aggressive: "#e5791b",
    super_aggressive: "#b84f32",
  };
  const byScenario = (item, id) => (item.cenarios || []).find((scenario) => scenario.id === id) || {};
  const countHits = (scenarioId, profileId) => groups.reduce((total, item) => {
    const scenario = byScenario(item, scenarioId);
    const profile = (scenario.perfis_contemplacao || []).find((entry) => entry.id === profileId);
    return total + (profile?.atinge_perfil ? 1 : 0);
  }, 0);
  const scenarioLabels = { without_embedded: "Sem embutido", with_embedded: "Com embutido" };
  const scenarioSummary = (scenarioId) => `
    <div class="motor360-chance-scenario-summary">
      <div class="motor360-chance-scenario-label">${scenarioLabels[scenarioId]}</div>
      <div class="motor360-chance-summary">
        ${profileIds.map((profileId) => `<div class="motor360-chance-summary-card"><span class="motor360-profile-marker motor360-profile-marker-${profileId}" aria-hidden="true"></span><strong>${profileLabels[profileId]}</strong><b>${countHits(scenarioId, profileId)}/${groups.length}</b><small>grupos que atingem</small></div>`).join("")}
      </div>
    </div>
  `;
  const canvasIds = {
    without_embedded: `motor360ChanceChart-without-${Date.now()}`,
    with_embedded: `motor360ChanceChart-with-${Date.now() + 1}`,
  };
  const buildDatasets = (scenarioId) => [
    {
      label: "Lance ofertado pelo cliente",
      data: groups.map((item) => {
        const scenario = byScenario(item, scenarioId);
        const value = scenario.percentual_lance_efetivo ?? scenario.percentual_lance_cliente;
        return value == null ? null : value * 100;
      }),
      backgroundColor: "#c84b3a",
      borderColor: "#c84b3a",
      borderWidth: 2,
      borderDash: [2, 4],
      pointStyle: "circle",
      pointRadius: 2,
      pointHoverRadius: 4,
      showLine: true,
    },
    ...profileIds.map((profileId) => ({
      label: profileLabels[profileId],
      data: groups.map((item) => {
        const profile = (byScenario(item, scenarioId).perfis_contemplacao || []).find((entry) => entry.id === profileId);
        return profile?.percentual_referencia == null ? null : profile.percentual_referencia * 100;
      }),
      borderColor: profileColors[profileId],
      backgroundColor: profileColors[profileId],
      pointStyle: "triangle",
      pointRadius: 5,
      pointHoverRadius: 7,
      showLine: false,
    })),
  ];
  setTimeout(() => {
    if (typeof Chart === "undefined") return;
    if (motor360ChanceChart) {
      if (Array.isArray(motor360ChanceChart)) motor360ChanceChart.forEach((chart) => chart.destroy());
      else motor360ChanceChart.destroy();
    }
    const labels = groups.map((item) => String(item.grupo || item.grupo_id || "-"));
    const charts = ["without_embedded", "with_embedded"].map((scenarioId) => {
      const canvas = document.getElementById(canvasIds[scenarioId]);
      if (!canvas) return null;
      return new Chart(canvas, {
        type: "line",
        data: { labels, datasets: buildDatasets(scenarioId) },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          interaction: { mode: "index", intersect: false },
          plugins: {
            legend: { position: "bottom", labels: { usePointStyle: true, boxWidth: 8, font: { size: 10 } } },
            tooltip: { callbacks: { label: (context) => `${context.dataset.label}: ${formatPercent((context.raw || 0) / 100)}` } },
          },
          scales: {
            y: { beginAtZero: true, suggestedMax: 100, ticks: { callback: (value) => `${value}%` } },
            x: { ticks: { maxRotation: 45, minRotation: 0, autoSkip: groups.length > 14 } },
          },
        },
      });
    }).filter(Boolean);
    motor360ChanceChart = charts;
  }, 0);
  return `
    <section class="motor360-chance-panel">
      <div class="motor360-chance-header">
        <div><h3>Comparativo de chances de contemplação</h3><p>Os cenários financeiros são analisados separadamente. O círculo representa o lance do cliente; o triângulo representa o percentual de referência de cada perfil.</p></div>
        <span class="motor360-chance-legend-note">${groups.length} grupos comparados</span>
      </div>
      <div class="motor360-chance-symbol-legend"><span><i class="motor360-symbol-client-bid" aria-hidden="true"></i>Lance do cliente</span><span><i class="motor360-symbol-triangle" aria-hidden="true"></i>Referência do perfil</span></div>
      <div class="motor360-chance-scenarios">
        <section class="motor360-chance-scenario"><header><h4>Crédito contratado sem lance embutido</h4><span>Cenário 1</span></header>${scenarioSummary("without_embedded")}<div class="motor360-chance-chart"><canvas id="${canvasIds.without_embedded}" aria-label="Chances por grupo no cenário sem lance embutido"></canvas></div></section>
        <section class="motor360-chance-scenario"><header><h4>Crédito contratado com lance embutido</h4><span>Cenário 2</span></header>${scenarioSummary("with_embedded")}<div class="motor360-chance-chart"><canvas id="${canvasIds.with_embedded}" aria-label="Chances por grupo no cenário com lance embutido"></canvas></div></section>
      </div>
    </section>
  `;
}

function auditDateTime(value) {
  const date = value ? new Date(value) : null;
  return date && !Number.isNaN(date.getTime()) ? date.toLocaleString("pt-BR") : "-";
}

function formatMotor360Reason(reason) {
  const labels = {
    prazo_restante_nao_informado: "Prazo restante não informado",
    taxa_administracao_nao_informada: "Taxa de administração não informada",
    fundo_reserva_nao_informado: "Fundo de reserva não informado",
    faixas_contemplacao_inconsistentes: "Faixas de lance incompletas ou inconsistentes",
    percentual_x_ausente: "Percentual de lance embutido não informado",
    percentual_x_zero: "Percentual de lance embutido igual a zero",
    percentual_x_invalido: "Percentual de lance embutido inválido",
    credito_fora_da_faixa: "Crédito fora da faixa P/V",
    lance_abaixo_das_faixas: "Lance abaixo das faixas BM:BQ",
    prazo_remanescente_insuficiente: "Prazo remanescente insuficiente",
    credito_minimo_nao_informado: "Crédito mínimo (P) não informado",
    credito_maximo_nao_informado: "Crédito máximo (V) não informado",
    identificacao_grupo_invalida: "Identificação do grupo inválida",
    composicao_parcela_maxima_excedida: "Composição excede a parcela máxima",
    composicao_credito_insuficiente_ou_limite_cotas: "Crédito insuficiente ou limite de 50 cotas",
    lance_insuficiente_para_perfil: "Lance insuficiente para o perfil selecionado",
    excluded_credit: "Fora da faixa de crédito",
    excluded_term_income: "Prazo ou limite de renda não atendido",
    excluded_contemplation: "Não atingiu o perfil de contemplação individual",
    excluded_composition: "Composição não viável nos limites calculados",
    excluded_invalid_identity: "Identificação do grupo inválida",
    excluded_data: "Dados insuficientes para análise",
    matrix_approved: "Aprovado individualmente na matriz",
    composition: "Possível em composição; não aprovado como cota isolada",
    rejected: "Reprovado em regra obrigatória",
  };
  const normalized = String(reason || "-");
  return labels[normalized] || normalized.replace(/^excluded_/, "").replaceAll("_", " ").replace(/^./, (letter) => letter.toLocaleUpperCase("pt-BR"));
}

function formatMotor360Result(result) {
  return formatMotor360Reason(result);
}

function formatMotor360Stage(stage) {
  const labels = {
    credito: "Crédito de uma cota fora da faixa",
    prazo: "Prazo ou renda de uma cota não atendido",
    administradora: "Regra da administradora não atendida",
    contemplacao: "Perfil de contemplação individual não atingido",
    composicao: "Composição não atende aos limites",
    status: "Status do grupo não elegível",
    identificacao: "Identificação do grupo inválida",
  };
  return labels[stage] || `Etapa: ${formatMotor360Reason(stage)}`;
}

function formatMotor360Duration(milliseconds) {
  const value = Number(milliseconds);
  if (!Number.isFinite(value) || value < 0) return "Não informado";
  const seconds = value >= 1000;
  return `${new Intl.NumberFormat("pt-BR", { minimumFractionDigits: seconds ? 2 : 1, maximumFractionDigits: seconds ? 2 : 1 }).format(seconds ? value / 1000 : value)} ${seconds ? "s" : "ms"}`;
}

function formatGroupDueDate(value) {
  const text = String(value ?? "").trim();
  return text || "Não informado";
}

function formatMotor360ServerTiming(header) {
  if (!header) return "";
  const labels = { sheet_load: "Leitura da planilha/cache", engine: "Motor 360", audit_save: "Gravação da auditoria", total: "Total no servidor" };
  return [...header.matchAll(/([\w-]+);dur=([\d.]+)/g)]
    .map(([, key, duration]) => `${labels[key] || key}: ${formatMotor360Duration(duration)}`)
    .join(" · ");
}

function renderMotor360Audit(audit) {
  if (!audit) return "";
  const metadata = audit.metadata || {};
  const summary = audit.summary || {};
  const client = audit.client_snapshot || {};
  const fieldRows = (client.raw_fields || []).map((field) => `
    <tr><td>${escapeHtml(field.field_name || "-")}</td><td>${escapeHtml(field.technical_name || "-")}</td><td>${escapeHtml(String(field.normalized_value ?? "-"))}</td><td>${escapeHtml(field.source_reference || field.source || "-")}</td></tr>`).join("");
  const filterRows = (audit.execution_steps || []).map((step) => `
    <tr><td>${escapeHtml(String(step.order))}</td><td>${escapeHtml(step.name)}</td><td>${escapeHtml(step.formula_or_rule)}</td><td>${step.input_count ?? 0}</td><td>${step.approved_count ?? 0}</td><td>${step.composition_count ?? 0}</td><td>${step.rejected_count ?? 0}</td><td>${step.incomplete_count ?? 0}</td></tr>`).join("");
  const columnRows = (audit.columns_used || []).map((column) => `<tr><td>${escapeHtml(column.column)}</td><td>${escapeHtml(column.header)}</td><td>${escapeHtml(column.technical_field)}</td><td>${escapeHtml(column.purpose)}</td></tr>`).join("");
  const mappingRows = Object.entries(audit.data_source?.mapping_by_administrator || {}).flatMap(([administrator, fields]) => Object.entries(fields || {}).map(([field, mapping]) => `<tr><td>${escapeHtml(administrator)}</td><td>${escapeHtml(field)}</td><td>${escapeHtml((mapping.columns || []).join(", ") || "-")}</td><td>${escapeHtml((mapping.headers || []).join(", ") || "-")}</td><td>${escapeHtml((mapping.sources || []).join(", ") || "-")}</td><td>${mapping.mapped_rows ?? 0}</td><td>${mapping.blank_value_rows ?? 0}</td><td>${mapping.missing_rows ?? 0}</td></tr>`)).join("");
  const formulaRows = (audit.formulas || []).map((formula) => `<article class="motor360-audit-formula"><strong>${escapeHtml(formula.name)}</strong><code>${escapeHtml(formula.expression)}</code><span>Resultado: ${escapeHtml(String(formula.result ?? "calculado por grupo"))}</span></article>`).join("");
  const excluded = audit.excluded_groups || [];
  const excludedRows = excluded.map((item) => `<tr><td>${escapeHtml(item.grupo)}</td><td>${escapeHtml(item.administradora)}</td><td>${escapeHtml(item.reason)}</td><td>${escapeHtml(item.detail)}</td></tr>`).join("");
  const matrixExcluded = summary.matrix_excluded_groups || [];
  const matrixExcludedRows = matrixExcluded.map((item) => `<tr><td>${escapeHtml(item.grupo || "-")}</td><td>${escapeHtml(item.administradora || "-")}</td><td>${escapeHtml(String(item.source_row ?? "-"))}</td><td>${escapeHtml(formatMotor360Result(item.result))}</td><td>${escapeHtml((item.justification || []).map(formatMotor360Reason).join(" · ") || "Sem cenário aprovado na matriz")}</td></tr>`).join("");
  const incompleteGroups = audit.incomplete_groups || [];
  const incompleteRows = incompleteGroups.flatMap((item) => (item.missing_fields || []).map((field) => `<tr><td>${escapeHtml(item.grupo)}</td><td>${escapeHtml(item.administradora)}</td><td>${escapeHtml(field.column || "-")}</td><td>${escapeHtml(field.field || "-")}</td><td>${escapeHtml(String(field.raw_value ?? "-"))}</td><td>${escapeHtml(field.reason || "-")}</td><td>${escapeHtml(field.impact || "-")}</td></tr>`)).join("");
  const groupRows = (audit.group_results || []).map((item) => {
    const scenario = (item.scenarios || []).find((entry) => entry.id === "without_embedded") || item.scenarios?.[0] || {};
    const embeddedScenario = (item.scenarios || []).find((entry) => entry.id === "with_embedded") || {};
    const stages = item.stage_results || {};
    const mark = (stage) => stages[stage]?.approved ? "Aprovado" : "Reprovado";
    const resultLabel = item.matrix_approved ? "Aprovado individualmente no perfil" : formatMotor360Result(item.result);
    const approvedScenarios = stages.contemplacao?.scenario_ids || [];
    return `<tr><td>${escapeHtml(item.grupo)}</td><td>${escapeHtml(item.administradora)}</td><td>${formatMoney(scenario.credito_contratado)}</td><td>${formatMoney(scenario.credito_minimo)} a ${formatMoney(scenario.credito_maximo)}</td><td>${mark("credito")}</td><td>${formatMoney(scenario.parcela_inicial)}<br><small>com emb.: ${formatMoney(embeddedScenario.parcela_inicial)}</small></td><td>${escapeHtml(String(scenario.prazo_apos_lance_limite_renda_meses ?? "-"))} / ${escapeHtml(String(item.source_values?.prazo_restante ?? "-"))}</td><td>${mark("prazo")}</td><td>${mark("contemplacao")}<br><small>${escapeHtml(approvedScenarios.length ? `cenário(s): ${approvedScenarios.join(", ")}` : "nenhum cenário aprovado")}</small></td><td>${resultLabel}</td></tr>`;
  }).join("");
  const warnings = (audit.warnings || []).map((warning) => `<li class="audit-warning-${escapeHtml(warning.level || "info")}">${escapeHtml(warning.message)}</li>`).join("");
  return `
    <details class="motor360-audit-panel">
      <summary><span><strong>Auditoria da Análise</strong><small>Entenda como o Motor 360 chegou aos grupos exibidos.</small></span><span class="audit-summary-action">Exibir auditoria completa</span></summary>
      <div class="motor360-audit-content">
        <div class="motor360-audit-meta">
          <span><small>Execução</small><b>${auditDateTime(metadata.completed_at)}</b></span>
          <span><small>Identificador</small><b>${escapeHtml(metadata.audit_id || "-")}</b></span>
          <span><small>Duração do cálculo interno</small><b>${escapeHtml(formatMotor360Duration(metadata.duration_ms))}</b></span>
          <span><small>Leitura da planilha/cache</small><b>${escapeHtml(formatMotor360Duration(audit.data_source?.load_duration_ms))}</b></span>
          <span><small>Tempo total do motor</small><b>${escapeHtml(formatMotor360Duration(metadata.engine_duration_ms))}</b></span>
          <span><small>Motor</small><b>${escapeHtml(metadata.engine_version || "-")}</b></span>
        </div>
        <div class="motor360-audit-actions"><a class="btn btn-primary btn-sm" href="/api/viabilidade-360/auditorias/${encodeURIComponent(metadata.audit_id || "")}/exportar.pdf">Baixar PDF</a><a class="btn btn-outline-secondary btn-sm" href="/api/viabilidade-360/auditorias/${encodeURIComponent(metadata.audit_id || "")}" target="_blank" rel="noopener">Exportar JSON</a><a class="btn btn-outline-secondary btn-sm" href="/api/viabilidade-360/auditorias/${encodeURIComponent(metadata.audit_id || "")}/exportar.md">Exportar Markdown</a></div>
        <details open><summary>1. Dados recebidos e consolidados</summary><div class="table-responsive"><table class="table motor360-audit-table"><thead><tr><th>Campo</th><th>Técnico</th><th>Valor usado</th><th>Origem</th></tr></thead><tbody>${fieldRows}</tbody></table></div></details>
        <details><summary>2. Base, parâmetros e colunas utilizadas</summary><p>Origem: <strong>${escapeHtml(audit.data_source?.source_name || "-")}</strong> | Modo: <strong>${escapeHtml(audit.data_source?.current_or_historical || "-")}</strong> | Linhas lidas: <strong>${audit.data_source?.total_rows ?? 0}</strong> | Hash: <strong>${escapeHtml(String(audit.data_source?.base_snapshot?.fingerprint || "-").slice(0, 16))}...</strong></p><p>Parâmetros aplicados: <strong>${escapeHtml(JSON.stringify(audit.parameters || {}))}</strong></p><div class="table-responsive"><table class="table motor360-audit-table"><thead><tr><th>Coluna</th><th>Campo</th><th>Técnico</th><th>Uso</th></tr></thead><tbody>${columnRows}</tbody></table></div>${mappingRows ? `<h4>Mapeamento comprovado por administradora</h4><div class="table-responsive"><table class="table motor360-audit-table"><thead><tr><th>Administradora</th><th>Campo</th><th>Coluna real</th><th>Cabeçalho/Fallback</th><th>Origem</th><th>Linhas com origem</th><th>Valores vazios</th><th>Origem ausente</th></tr></thead><tbody>${mappingRows}</tbody></table></div>` : "<p>O carregamento não forneceu metadados de mapeamento por administradora.</p>"}</details>
        <details><summary>3. Sequência de filtros</summary><div class="table-responsive"><table class="table motor360-audit-table"><thead><tr><th>#</th><th>Etapa</th><th>Regra</th><th>Entrada</th><th>Aprovados individualmente</th><th>Opções viáveis em composição</th><th>Eliminados</th><th>Incompletos</th></tr></thead><tbody>${filterRows}</tbody></table></div></details>
        <details><summary>4. Fórmulas e cálculos</summary><div class="motor360-audit-formulas">${formulaRows}</div></details>
        <details class="motor360-audit-omitted" open><summary>Grupos que não aparecem na lista do Motor 360 (${matrixExcluded.length})</summary><p>Estes grupos foram avaliados, mas não foram aprovados individualmente nem classificados como opção viável em composição nesta execução. A relação abaixo é nominal e inclui a linha de origem e o motivo.</p>${matrixExcluded.length ? `<div class="table-responsive"><table class="table motor360-audit-table"><thead><tr><th>Grupo</th><th>Administradora</th><th>Linha fonte</th><th>Resultado</th><th>Motivo</th></tr></thead><tbody>${matrixExcludedRows}</tbody></table></div>` : "<p class=\"motor360-audit-empty\">Nenhum grupo foi omitido nesta execução.</p>"}</details>
        <details><summary>5. Grupos aprovados na matriz e opções de composição</summary><p>${escapeHtml(audit.final_ordering?.execution_summary || "")}</p><ol>${(audit.final_ordering?.rules || []).map((rule) => `<li>${escapeHtml(rule)}</li>`).join("")}</ol><p>Aprovados individualmente: <strong>${summary.total_matrix_approved_groups ?? summary.total_post_matrix_groups ?? summary.total_preselected ?? 0}</strong> | Na lista total: <strong>${summary.total_displayed_groups ?? summary.total_post_matrix_groups ?? 0}</strong> | Crédito compatível: <strong>${summary.total_credit_compatible ?? 0}</strong> | Exigem composição estimada: <strong>${summary.total_requires_composition ?? 0}</strong> | Dados incompletos: <strong>${summary.groups_with_incomplete_data ?? 0}</strong> | Ocorrências incompletas: <strong>${summary.incomplete_field_occurrences ?? 0}</strong></p><p>Opções viáveis em composição são exploráveis pelo operador e não são apresentadas como aprovação de uma cota isolada.</p></details>
        <details><summary>6. Grupos fora da matriz e motivos (${excluded.length})</summary>${excluded.length ? `<div class="table-responsive"><table class="table motor360-audit-table"><thead><tr><th>Grupo</th><th>Administradora</th><th>Motivo</th><th>Detalhe</th></tr></thead><tbody>${excludedRows}</tbody></table></div>` : "<p>Nenhum grupo ficou fora da matriz.</p>"}</details>
        <details><summary>7. Dados incompletos por grupo (${incompleteGroups.length})</summary>${incompleteGroups.length ? `<div class="table-responsive"><table class="table motor360-audit-table"><thead><tr><th>Grupo</th><th>Administradora</th><th>Coluna</th><th>Campo</th><th>Valor original</th><th>Motivo</th><th>Impacto</th></tr></thead><tbody>${incompleteRows}</tbody></table></div>` : "<p>Nenhum dado obrigatório ausente.</p>"}</details>
        <details><summary>8. Auditoria por grupo (${(audit.group_results || []).length})</summary><div class="table-responsive"><table class="table motor360-audit-table"><thead><tr><th>Grupo</th><th>Administradora</th><th>Crédito contratado</th><th>Faixa P/V</th><th>Crédito</th><th>Parcela inicial<br><small>sem / com embutido</small></th><th>Prazo calculado / G</th><th>Prazo</th><th>Contemplação<br><small>cenário aprovado</small></th><th>Resultado</th></tr></thead><tbody>${groupRows}</tbody></table></div></details>
        <details><summary>9. Alertas e regras pendentes</summary><ul class="motor360-audit-warnings">${warnings}</ul></details>
      </div>
    </details>`;
}

function renderMotor360GroupAudit(groupId) {
  const audit = investorState.audit;
  if (!audit) return;
  const entry = (audit.group_results || []).find((item) => motor360GroupKey(item) === String(groupId) || String(item.grupo) === String(groupId));
  if (!entry) return;
  document.getElementById("motor360GroupAuditDialog")?.remove();
  const scenarios = (entry.scenarios || []).map((scenario) => {
    const scenarioTitle = scenario.id === "with_embedded" ? "Crédito contratado com lance embutido" : "Crédito contratado sem lance embutido";
    const installment = scenario.parcela_inicial;
    const formula = scenario.parcela_inicial_formula || "saldo devedor / prazo remanescente (coluna G)";
    const calculation = installment === null || installment === undefined
      ? "Não calculada: dados insuficientes"
      : `${formatMoney(scenario.saldo_devedor)} / ${escapeHtml(String(scenario.prazo_remanescente ?? "-"))} = ${formatMoney(installment)}`;
    const postInstallment = scenario.parcela_pos_contemplacao;
    const postFormula = scenario.parcela_pos_contemplacao_formula || "(saldo devedor - parcela inicial - lance total ofertado) / (prazo remanescente - 1)";
    const postCalculation = postInstallment === null || postInstallment === undefined
      ? "Não calculada: prazo remanescente deve ser maior que 1 e todos os valores precisam estar disponíveis"
      : `(${formatMoney(scenario.saldo_devedor)} - ${formatMoney(installment)} - ${formatMoney(scenario.lance_total_cenario)}) / (${escapeHtml(String(scenario.prazo_remanescente ?? "-"))} - 1) = ${formatMoney(postInstallment)}`;
    return `<article><strong>${scenarioTitle}</strong><span>Status: ${scenario.creation_status === "not_created" ? formatMotor360Reason(scenario.creation_reason) : "calculado"}</span><span>Crédito contratado: ${formatMoney(scenario.credito_contratado)}</span><span>Lance ofertado pelo cliente: ${formatMoney(scenario.lance_cliente_total)} (${formatPercent(scenario.percentual_lance_cliente)})</span><span>Lance embutido: ${formatMoney(scenario.lance_embutido)}</span><span>Lance total do cenário: ${formatMoney(scenario.lance_total_cenario)} (${formatPercent(scenario.percentual_lance_efetivo)})</span><span>Saldo devedor: ${formatMoney(scenario.saldo_devedor)}</span><span>Parcela inicial: ${formatMoney(installment)}</span><small>Fórmula: ${escapeHtml(formula)}</small><small>Cálculo: ${calculation}</small><span>Parcela pós-contemplação: ${postInstallment == null ? "Não calculada" : formatMoney(postInstallment)}</span><small>Fórmula: ${escapeHtml(postFormula)}</small><small>Cálculo: ${postCalculation}</small><span>Prazo: ${scenario.term_compatible === null ? "não analisado" : scenario.term_compatible ? "compatível" : "não compatível"}</span></article>`;
  }).join("");
  const dialog = document.createElement("dialog");
  dialog.id = "motor360GroupAuditDialog";
  dialog.className = "motor360-group-audit-dialog";
  const reasons = (entry.justification || []).map(formatMotor360Reason).join(", ");
  dialog.innerHTML = `<div class="motor360-group-audit-dialog-header"><div><h3>Justificativa do grupo ${escapeHtml(entry.grupo)}</h3><p>${escapeHtml(entry.administradora || "-")} · Resultado: ${escapeHtml(formatMotor360Result(entry.result))} · Ordem ${escapeHtml(String(entry.ranking || "-"))}</p></div><button class="btn btn-outline-secondary btn-sm" type="button">Fechar</button></div><div class="motor360-group-audit-scenarios">${scenarios}</div><div class="motor360-group-audit-alerts"><strong>Dados da base utilizados</strong><p>Prazo restante (F): ${escapeHtml(String(entry.source_values?.prazo_restante ?? "-"))} | Embutido (X): ${escapeHtml(String(entry.source_values?.percentual_lance_embutido ?? "-"))}</p><strong>Motivos e alertas</strong><p>${escapeHtml(reasons || "Nenhum alerta registrado.")}</p></div>`;
  dialog.querySelector("button")?.addEventListener("click", () => dialog.close());
  dialog.addEventListener("close", () => dialog.remove());
  document.body.append(dialog);
  dialog.showModal();
}

function motor360BlockingReasonAdvice(reason) {
  const advice = {
    prazo_restante_nao_informado: "Preencher o prazo remanescente do grupo na planilha antes de apresentá-lo como opção final.",
    taxa_administracao_nao_informada: "Preencher a taxa administrativa total do grupo na planilha para concluir o cálculo do cenário.",
    credito_minimo_nao_informado: "Informar o crédito mínimo do grupo e revisar a linha na base.",
    credito_maximo_nao_informado: "Informar o crédito máximo do grupo e revisar a linha na base.",
    credito_fora_da_faixa: "Ajustar o crédito desejado ou orientar o cliente que este grupo não comporta o valor solicitado.",
    prazo_remanescente_insuficiente: "Validar prazo e renda do cliente; o prazo disponível não suporta o cenário calculado.",
    lance_insuficiente_para_perfil: "Aumentar o lance simulado ou orientar o cliente a escolher um perfil de contemplação menos urgente.",
    percentual_lance_embutido_nao_informado: "Informar o percentual de lance embutido do grupo na planilha.",
    filtro_lance_embutido: "Revisar o filtro de lance embutido selecionado pelo operador.",
    filtro_parcela_reduzida: "Revisar o filtro de parcela reduzida selecionado pelo operador.",
  };
  return advice[reason] || "Revisar os dados do grupo e os parâmetros do perfil do cliente antes de apresentá-lo como opção final.";
}

function renderMotor360BlockingDiagnostics(audit) {
  const entries = audit?.group_results || [];
  const summary = audit?.summary || {};
  const rawOmissions = Array.isArray(summary.matrix_excluded_groups)
    ? summary.matrix_excluded_groups
    : entries.filter((entry) => entry.result !== "matrix_approved" && !entry.matrix_approved);
  const omissionKey = (item) => item.source_row != null
    ? `row:${item.source_row}`
    : `${item.administradora || "-"}|${item.grupo || item.grupo_id || "sem-identificador"}`;
  const omitted = [...new Map(rawOmissions.map((item) => [omissionKey(item), item])).values()];
  const omittedRows = omitted.map((item) => {
    const group = [item.grupo, item.grupo_id]
      .map((value) => String(value ?? "").trim())
      .find((value) => value && value !== "-" && value !== "–") || "";
    const missing = item.missing_fields || [];
    const reasons = [...new Set([
      ...(item.justification || []),
      ...missing.map((field) => field.reason),
    ].filter(Boolean).map(String))];
    const reasonLabels = [...new Set(reasons.map(formatMotor360Reason))];
    const stageFailures = Object.entries(item.stage_results || {})
      .filter(([, stage]) => stage?.approved === false)
      .map(([stage]) => stage);
    const details = [...reasonLabels, ...stageFailures.map(formatMotor360Stage)];
    const reason = [...new Set(details)].join(" · ") || "Motivo não registrado nesta execução";
    const identity = group || "Sem identificador de grupo";
    const sourceRowSearch = item.source_row == null ? "" : `linha ${item.source_row}`;
    const search = [identity, item.administradora, sourceRowSearch, reason].filter(Boolean).join(" ").toLocaleLowerCase("pt-BR");
    return `<tr data-omitted-search="${escapeHtml(search)}"><td>${escapeHtml(identity)}</td><td>${escapeHtml(item.administradora || "-")}</td><td>${escapeHtml(String(item.source_row ?? "Linha não informada"))}</td><td>${escapeHtml(formatMotor360Result(item.result))}</td><td>${escapeHtml(reason)}</td></tr>`;
  }).join("");
  const analyzedCount = Number(summary.total_analyzed ?? audit?.data_source?.total_rows ?? entries.length);
  const displayedCount = Number(summary.total_displayed_groups ?? summary.total_post_matrix_groups ?? summary.total_preselected ?? entries.filter((entry) => entry.matrix_approved || entry.result === "matrix_approved").length);
  const unidentifiedCount = omitted.filter((item) => ![item.grupo, item.grupo_id]
    .map((value) => String(value ?? "").trim())
    .some((identifier) => identifier && identifier !== "-" && identifier !== "–")).length;
  const advice = [...new Set(omitted.flatMap((item) => [
    ...(item.justification || []),
    ...(item.missing_fields || []).map((field) => field.reason),
  ].filter(Boolean).map(String)).map(motor360BlockingReasonAdvice))].join(" ");
  const omissionTable = omitted.length
    ? `<label class="motor360-omitted-search">Buscar grupo, administradora, linha ou motivo<input type="search" data-motor360-omitted-search placeholder="Ex.: 20370, Santander ou linha 308"></label><div class="table-responsive motor360-omitted-table-wrap"><table class="table motor360-audit-table"><thead><tr><th>Grupo / identificação</th><th>Administradora</th><th>Linha da planilha</th><th>Resultado</th><th>Motivo</th></tr></thead><tbody>${omittedRows}</tbody></table><p class="motor360-omitted-no-match d-none" data-motor360-omitted-no-match>Nenhum grupo corresponde à busca.</p></div>`
    : '<p class="table-state">Nenhum grupo foi omitido pela matriz nesta execução.</p>';
  const dialog = document.createElement("dialog");
  dialog.id = "motor360BlockingDiagnosticsDialog";
  dialog.className = "motor360-blocking-dialog";
  dialog.innerHTML = `<div class="motor360-blocking-dialog-header"><div><h3>O que está impedindo os grupos</h3><p>Diagnóstico da execução ${escapeHtml(audit?.metadata?.audit_id || "")}</p></div><button class="btn btn-outline-secondary btn-sm" type="button">Fechar</button></div><div class="motor360-blocking-dialog-body"><div class="motor360-blocking-summary"><span><small>Analisados</small><b>${analyzedCount}</b></span><span><small>Na lista</small><b>${displayedCount}</b></span><span><small>Omitidos</small><b>${omitted.length}</b></span><span><small>Sem identificação</small><b>${unidentifiedCount}</b></span></div><p class="motor360-blocking-intro">Os totais usam a mesma base de grupos: analisados = exibidos + omitidos. Cada linha abaixo representa um grupo omitido, sem truncamento; quando o número do grupo não existe na fonte, a linha da planilha permanece identificada.</p>${omissionTable}${advice ? `<p class="motor360-blocking-advice"><strong>Orientações:</strong> ${escapeHtml(advice)}</p>` : ""}</div>`;
  dialog.querySelector("button")?.addEventListener("click", () => dialog.close());
  const searchInput = dialog.querySelector("[data-motor360-omitted-search]");
  searchInput?.addEventListener("input", () => {
    const query = searchInput.value.trim().toLocaleLowerCase("pt-BR");
    let visibleRows = 0;
    dialog.querySelectorAll("[data-omitted-search]").forEach((row) => {
      const matches = !query || row.dataset.omittedSearch.includes(query);
      row.classList.toggle("d-none", !matches);
      if (matches) visibleRows += 1;
    });
    dialog.querySelector("[data-motor360-omitted-no-match]")?.classList.toggle("d-none", visibleRows !== 0);
  });
  dialog.addEventListener("close", () => dialog.remove(), { once: true });
  document.body.append(dialog);
  dialog.showModal();
}

function motor360ExecutionStepMessage(step) {
  const compositionCount = Number(step.composition_count || 0);
  const approvedLabel = step.order === 3 ? "aprovados individualmente" : "aprovados";
  const compositionLabel = compositionCount ? ` · opções em composição ${compositionCount}` : "";
  return `Entrada ${step.input_count ?? 0} · ${approvedLabel} ${step.approved_count ?? step.evaluated_count ?? 0}${compositionLabel} · eliminados ${step.rejected_count ?? 0} · ${formatMotor360Duration(step.duration_ms)}.`;
}

async function loadMotor360Audit(auditId) {
  if (!auditId) return;
  try {
    const response = await fetch(`/api/viabilidade-360/auditorias/${encodeURIComponent(auditId)}`, { credentials: "same-origin" });
    if (!response.ok) throw new Error("Auditoria não encontrada.");
    investorState.audit = await response.json();
    const audit = investorState.audit;
    syncMotor360BidExplorer();
    const metadata = audit.metadata || {};
    const snapshot = audit.data_source?.base_snapshot || {};
    addMotor360ExecutionLog("Auditoria técnica carregada", `${metadata.audit_id || auditId} · cálculo interno ${formatMotor360Duration(metadata.duration_ms)} · carga da base ${formatMotor360Duration(audit.data_source?.load_duration_ms)} · motor total ${formatMotor360Duration(metadata.engine_duration_ms)}.`);
    addMotor360ExecutionLog("Base identificada", `${audit.data_source?.total_rows ?? 0} linhas · SHA-256 ${String(snapshot.fingerprint || "não disponível").slice(0, 16)}...`);
    addMotor360ExecutionLog("Rastreabilidade preparada", `${(audit.columns_used || []).filter((column) => column.used_in_decision).length} colunas usadas na decisão · ${(audit.formulas || []).length} fórmulas registradas.`);
    (audit.execution_steps || []).forEach((step) => {
      addMotor360ExecutionLog(`Etapa ${step.order}: ${step.name}`, motor360ExecutionStepMessage(step));
    });
    addMotor360ExecutionLog("Auditoria por grupo disponível", `${(audit.group_results || []).length} grupos com decisão, cenários, colunas e motivos registrados.`);
    if (investorState.result) {
      const auditBlock = document.querySelector("[data-motor360-audit]");
      if (auditBlock) auditBlock.outerHTML = renderMotor360Audit(investorState.audit);
    }
  } catch (error) {
    showToast(error.message || "Não foi possível carregar a auditoria.", "warning");
  }
}

function motor360AdministratorName(item) {
  if (typeof item === "string") return item.trim();
  return String(item?.administradora || item?.adm || "").trim();
}

function motor360AdministratorKey(item) {
  return normalizeText(motor360AdministratorName(item)).replace(/[^a-z0-9]+/g, "");
}

function motor360GroupKey(itemOrAdministrator, groupId = null) {
  const item = groupId === null ? itemOrAdministrator : { administradora: itemOrAdministrator, grupo: groupId };
  const administrator = motor360AdministratorKey(item);
  const group = String(item?.grupo || item?.grupo_id || "").trim();
  return `${administrator}|${group}`;
}

function clearMotor360GroupSelection() {
  investorState.selectedGroupIds.clear();
  investorState.selectedScenarioIds.clear();
  investorState.quotaCounts.clear();
  investorState.selectedGroupData.clear();
  persistMotor360Selection();
}

function syncMotor360AdministratorFilter(sourceItems) {
  const select = document.getElementById("investorAdministratorFilter");
  const administratorByKey = new Map();
  sourceItems.forEach((item) => {
    const name = motor360AdministratorName(item);
    const key = motor360AdministratorKey(item);
    if (name && key && !administratorByKey.has(key)) administratorByKey.set(key, name);
  });
  const administrators = [...administratorByKey.values()]
    .sort((left, right) => left.localeCompare(right, "pt-BR"));
  const availableKeys = new Set(administrators.map(motor360AdministratorKey));
  const selectedAdministrator = [...investorState.selectedGroupIds]
    .map((id) => investorState.selectedGroupData.get(id))
    .map(motor360AdministratorName)
    .find(Boolean);

  // A persisted selection is authoritative while the analysis is being
  // re-rendered. Do not silently discard selected groups because an old
  // administrator filter was empty or stale; explicit filter changes are
  // handled by the change listener below and show a warning to the operator.
  if (selectedAdministrator) {
    investorState.administrator = selectedAdministrator;
  } else if (!investorState.administrator || !availableKeys.has(motor360AdministratorKey(investorState.administrator))) {
    investorState.administrator = "";
  } else {
    investorState.administrator = administratorByKey.get(motor360AdministratorKey(investorState.administrator));
  }

  if (select) {
    select.innerHTML = administrators.length
      ? `<option value="">Todas as administradoras</option>${administrators.map((administrator) => `<option value="${escapeHtml(administrator)}">${escapeHtml(administrator)}</option>`).join("")}`
      : '<option value="">Nenhuma administradora disponível</option>';
    select.value = investorState.administrator;
    select.disabled = !administrators.length;
  }
  localStorage.setItem("crediclass.motor360.administrator", investorState.administrator);
  persistMotor360Selection();
  return investorState.administrator;
}

function motor360ScenarioSourceMetrics(item) {
  const clientCredit = investorState.result?.cliente?.credito_liquido_desejado;
  return `<div class="motor360-scenario-source-metrics"><div><small>Taxa Adm</small><b>${formatPercent(item?.taxa_adm)}</b></div><div><small>Fundo de Reserva</small><b>${formatPercent(item?.fundo_reserva)}</b></div><div><small>Crédito desejado líquido</small><b>${formatMoney(clientCredit)}</b></div></div>`;
}

function renderMotor360ContemplationMatrix(items, selectedProfile, rejectedItems = []) {
  const profiles = [
    ["urgent", "Urgente"], ["fast", "Rápido"], ["moderate", "Moderado"],
    ["conservative", "Conservador"], ["long_term", "Investidor"],
  ];
  const profileAliases = { urgent: "super_aggressive", fast: "aggressive", moderate: "moderate", conservative: "conservative", long_term: "investor" };
  const rows = [...items, ...rejectedItems].filter((item) => (
    String(item?.administradora || "").trim() && String(item?.grupo || item?.grupo_id || "").trim()
  )).map((item) => {
    const scenarios = item.cenarios || item.scenarios || [];
    const cells = profiles.map(([id, label]) => {
      const profileId = profileAliases[id] || id;
      const matches = scenarios.map((scenario) => ({ scenario, profile: (scenario.perfis_contemplacao || []).find((entry) => entry.id === profileId || entry.id === id) })).filter((entry) => entry.profile);
      if (!matches.length || matches.every((entry) => entry.profile.atinge_perfil == null)) return `<td><span class="text-muted">Sem dado</span></td>`;
      const eligibleIds = Array.isArray(item.eligible_scenarios) ? new Set(item.eligible_scenarios) : null;
      const approved = matches.filter((entry) => entry.profile.atinge_perfil === true && (!eligibleIds || eligibleIds.has(entry.scenario.id)));
      const reference = (approved[0] || matches[0]).profile;
      const scenarioLabel = approved.length
        ? approved.map((entry) => entry.scenario.id === "with_embedded" ? "com embutido" : "sem embutido").join(" / ")
        : "";
      return `<td><strong class="${approved.length ? "text-success" : "text-danger"}">${approved.length ? "Atende" : "Não atende"}</strong> <small>${formatPercent(reference.percentual_referencia)}${scenarioLabel ? ` · ${scenarioLabel}` : ""}</small></td>`;
    }).join("");
    const rejected = rejectedItems.includes(item) ? " <small>(não selecionado)</small>" : "";
    const groupLabel = [item.administradora, item.grupo || item.grupo_id || "-"]
      .filter((value) => value !== null && value !== undefined && String(value).trim())
      .join(" · ");
    return `<tr><th>${escapeHtml(groupLabel || "-")}${rejected}</th>${cells}</tr>`;
  }).join("");
  if (!rows) return "";
  return `<details class="motor360-profile-matrix"><summary>Matriz de contemplação por grupo · perfil aplicado: ${escapeHtml(selectedProfile || "não informado")}</summary><div class="table-responsive"><table class="table"><thead><tr><th>Grupo</th>${profiles.map(([, label]) => `<th>${label}</th>`).join("")}</tr></thead><tbody>${rows}</tbody></table></div></details>`;
}

function renderInvestorAnalysis(result) {
  if (motor360AnalyticsCacheResult !== result) {
    motor360GroupAnalyticsCache.clear();
    motor360AnalyticsCacheResult = result;
  }
  if (motor360CardCacheResult !== result) {
    motor360GroupCardCache.clear();
    motor360CardCacheResult = result;
  }
  renderMotor360SelectionFilters();
  const scenarioState = investorState.selectedGroupScenario || "per_group";
  const withScenario = document.getElementById("investorFilterWithEmbedded");
  const withoutScenario = document.getElementById("investorFilterWithoutEmbedded");
  if (withScenario) withScenario.checked = scenarioState === "with_embedded" || scenarioState === "all";
  if (withoutScenario) withoutScenario.checked = scenarioState === "without_embedded" || scenarioState === "all";
  const status = document.getElementById("investorAnalysisStatus");
  const summary = document.getElementById("investorAnalysisSummary");
  const results = document.getElementById("investorAnalysisResults");
  if (!status || !summary || !results) return;
  renderMotor360FloatingSelectionSummaryIntoFold();
  const client = result.cliente || {};
  const totals = result.contadores || {};
  const finalItems = result.final_items || result.items || [];
  const contemplationRejected = (result.audit?.group_results || []).filter((item) => item.result === "excluded_contemplation");
  const auditedMatrixItems = (investorState.audit?.group_results || []).map((entry) => ({
    grupo: entry.grupo,
    administradora: entry.administradora,
    cenarios: entry.scenarios || [],
  }));
  const matrixItems = result.matrix_items || (auditedMatrixItems.length ? auditedMatrixItems : [...(result.items || []), ...contemplationRejected]);
  const matrixProfileAliases = { urgent: "super_aggressive", fast: "aggressive", moderate: "moderate", conservative: "conservative", long_term: "investor" };
  const matrixProfileId = matrixProfileAliases[result.perfil_contemplacao] || result.perfil_contemplacao;
  const matrixApprovedKeys = new Set(matrixItems.filter((item) => {
    const scenarios = item.cenarios || item.scenarios || [];
    return scenarios.some((scenario) => (scenario.perfis_contemplacao || []).some((profile) => profile.id === matrixProfileId && profile.atinge_perfil === true));
  }).map((item) => `${motor360AdministratorKey(item)}|${String(item.grupo || item.grupo_id || "")}`));
  const onlyMatrixApproved = (items) => items.filter((item) => matrixApprovedKeys.has(`${motor360AdministratorKey(item)}|${String(item.grupo || item.grupo_id || "")}`));
  const isCompositionCandidate = (item) => item.composition_candidate === true || item.selection_stage === "composition";
  const sourceItems = result.perfil_contemplacao
    ? finalItems.filter((item) => isCompositionCandidate(item) || matrixApprovedKeys.has(`${motor360AdministratorKey(item)}|${String(item.grupo || item.grupo_id || "")}`))
    : finalItems;
  const selectedAdministrator = syncMotor360AdministratorFilter([
    ...(result.administradoras_analisadas || []),
    ...sourceItems,
    ...matrixItems,
  ]);
  updateInvestorPreferenceSummary();
  const selectedAdministratorKey = motor360AdministratorKey(selectedAdministrator);
  const withEmbeddedFilter = investorState.selectedGroupScenario === "with_embedded" || investorState.selectedGroupScenario === "all" || document.getElementById("investorFilterWithEmbedded")?.checked === true;
  const withoutEmbeddedFilter = investorState.selectedGroupScenario === "without_embedded" || investorState.selectedGroupScenario === "all" || document.getElementById("investorFilterWithoutEmbedded")?.checked === true;
  const selectedScenarioIds = new Set([
    ...(withEmbeddedFilter ? ["with_embedded"] : []),
    ...(withoutEmbeddedFilter ? ["without_embedded"] : []),
  ]);
  const matchesSelectedScenario = (item) => {
    if (!selectedScenarioIds.size) return true;
    return (item.cenarios || item.scenarios || []).some((scenario) => (
      selectedScenarioIds.has(scenario.id)
      && (scenario.eligible === true || (scenario.credit_compatible === true && scenario.term_compatible === true))
    ));
  };
  const scoped = (items) => selectedAdministratorKey
    ? items.filter((item) => motor360AdministratorKey(item) === selectedAdministratorKey)
    : items;
  const scenarioFiltered = (items) => items.filter(matchesSelectedScenario);
  const scopedMatrixItems = scenarioFiltered(scoped(matrixItems));
  const scopedAudit = investorState.audit ? {
    ...investorState.audit,
    group_results: scoped(investorState.audit.group_results || []),
    excluded_groups: scoped(investorState.audit.excluded_groups || []),
    incomplete_groups: scoped(investorState.audit.incomplete_groups || []),
  } : investorState.audit;
  const scopedContemplationRejected = scoped(contemplationRejected);
  const scenarioSourceItems = scenarioFiltered(sourceItems);
  const administratorItems = selectedAdministratorKey
    ? sourceItems.filter((item) => motor360AdministratorKey(item) === selectedAdministratorKey).filter(matchesSelectedScenario)
    : scenarioSourceItems;
  const items = applySelectedGroupsFiltersAndSort(applyInvestorPreferences(administratorItems, investorState.preferences));
  const summaryItems = [
    ["Grupos analisados", result.total_grupos_analisados ?? 0],
    ["Crédito líquido desejado", formatMoney(client.credito_liquido_desejado)],
    ["Estratégia declarada", result.preferencia_declarada === "investment" ? "Investimento" : result.preferencia_declarada || "Não classificada"],
    ["Parcela máxima", formatMoney(client.parcela_maxima)],
    ["Lance ofertado", formatMoney(client.lance_cliente_total)],
    ["Administradora", selectedAdministrator || "-"],
    ["Aprovados individualmente", result.audit?.summary?.total_matrix_approved_groups ?? (result.matrix_items || []).length],
    ["Opções viáveis em composição", result.total_grupos_composicao ?? 0],
    ["Crédito compatível", result.total_grupos_credito_compativeis ?? 0],
    ["Exigem análise de prazo/renda", result.audit?.summary?.total_term_income_rejected ?? 0],
    ["Exigem composição estimada", result.audit?.summary?.total_requires_composition ?? 0],
    ["Dados incompletos", totals.dados_incompletos ?? 0],
    ["Grupos exibidos nesta administradora", items.length],
  ];
  summary.innerHTML = summaryItems.map(([label, value]) => (
    `<div class="smart-engine-summary-item"><span>${escapeHtml(label)}</span><strong>${escapeHtml(String(value))}</strong></div>`
  )).join("");
  updateMotor360SelectionSummary();
  if (!items.length) {
    const profileLabel = { urgent: "Urgente", fast: "Rápido", moderate: "Moderado", conservative: "Conservador", long_term: "Investidor" }[result.perfil_contemplacao] || "selecionado";
    const rejectedHtml = contemplationRejected.length ? `<details class="motor360-credit-excluded" open><summary>${contemplationRejected.length} grupo(s) não atingem o perfil ${profileLabel}</summary><div class="table-responsive"><table class="table"><thead><tr><th>Grupo</th><th>Administradora</th><th>Motivo</th></tr></thead><tbody>${contemplationRejected.map((item) => `<tr><td>${escapeHtml(item.grupo || "-")}</td><td>${escapeHtml(item.administradora || "-")}</td><td>Lance disponível abaixo da faixa do perfil selecionado.</td></tr>`).join("")}</tbody></table></div></details>` : "";
    const diagnosticButton = '<button type="button" class="btn btn-primary btn-sm motor360-blocking-diagnostics-trigger" data-motor360-blocking-diagnostics>Ver por que nenhum grupo foi encontrado</button>';
    const hasActiveSelectionFilters = Object.values(selectedGroupsFilterValues()).some((value) => value !== "" && value !== false);
    const explicitMessage = hasActiveSelectionFilters
      ? `<div class="motor360-no-match-alert" role="alert"><strong>Nenhum grupo atende aos filtros atuais.</strong><span>Ajuste os filtros ou use “Limpar filtros” para voltar a visualizar os grupos.</span></div>`
      : result.perfil_contemplacao
      ? `<div class="motor360-no-match-alert" role="alert"><strong>Nenhum grupo encontrado para o perfil ${profileLabel}</strong><span>O lance do cliente (${formatMoney(client.lance_cliente_total)}) não atende ao percentual mínimo de contemplação dos grupos compatíveis. Ajuste o lance ou selecione um perfil com prazo maior.</span>${diagnosticButton}</div>`
      : `<div class="motor360-no-match-alert" role="alert"><strong>Nenhum grupo encontrado</strong><span>Nenhum grupo passou por todas as validações do Motor 360.</span>${diagnosticButton}</div>`;
    results.innerHTML = `${explicitMessage}${renderMotor360ContemplationMatrix(scopedMatrixItems, result.perfil_contemplacao)}${rejectedHtml}${renderMotor360Audit(scopedAudit)}`;
    results.insertAdjacentHTML("afterbegin", renderMotor360FilterNotice(administratorItems, items));
    results.querySelector("[data-motor360-blocking-diagnostics]")?.addEventListener("click", () => renderMotor360BlockingDiagnostics(investorState.audit || result.audit));
    setInvestorAnalysisState("results");
    if (!document.getElementById("selectedGroupsWorkspace")?.classList.contains("d-none")) renderSelectedGroupsScreen();
    return;
  }
  results.innerHTML = `
    <button type="button" class="btn btn-outline-secondary btn-sm motor360-blocking-diagnostics-trigger" data-motor360-blocking-diagnostics>Ver impedimentos e orientações</button>
    ${renderMotor360ContemplationMatrix(scopedMatrixItems, result.perfil_contemplacao)}
    <div class="motor360-single-quota-note" role="note">
      <strong>Grupos compatíveis para composição da carteira</strong>
      <span>Exibimos grupos com crédito e prazo compatíveis. O perfil pode ser atingido pela composição de múltiplas cotas ou grupos; confira os requisitos de cada cenário antes de selecionar.</span>
    </div>
    <div class="motor360-group-list">${items.map(renderMotor360GroupCard).join("")}</div>

    ${scopedContemplationRejected.length ? `<details class="motor360-credit-excluded" open><summary>Grupos fora do perfil de contemplação selecionado (${scopedContemplationRejected.length})</summary><div class="table-responsive"><table class="table"><thead><tr><th>Grupo</th><th>Administradora</th><th>Motivo</th></tr></thead><tbody>${scopedContemplationRejected.map((item) => `<tr><td>${escapeHtml(item.grupo || "-")}</td><td>${escapeHtml(item.administradora || "-")}</td><td>Lance disponível abaixo da faixa do perfil selecionado.</td></tr>`).join("")}</tbody></table></div></details>` : ""}
    ${renderMotor360ChanceChart(items)}
    <div class="investor-engine-audit"><strong>Demonstrativo:</strong> ${escapeHtml((result.passos || []).join(" "))}</div>
    ${renderMotor360Audit(scopedAudit)}
  `;
  results.insertAdjacentHTML("afterbegin", renderMotor360FilterNotice(administratorItems, items));
  results.querySelectorAll(".motor360-scenario-card").forEach((card) => {
    const groupId = card.closest(".motor360-group-card")?.querySelector(".motor360-group-select-input")?.dataset.groupId;
    const groupItem = motor360FinalItems(result).find((item) => motor360GroupKey(item) === String(groupId || "") || String(item.grupo || item.grupo_id || "") === String(groupId || ""));
    card.querySelector(".motor360-scenario-grid")?.insertAdjacentHTML("beforeend", motor360ScenarioSourceMetrics(groupItem));
    const scenarioCards = [...(card.closest(".motor360-group-card")?.querySelectorAll(".motor360-scenario-card") || [])];
    const scenarioId = groupItem?.cenarios?.[scenarioCards.indexOf(card)]?.id || "";
    if (!scenarioId) return;
    card.dataset.scenarioId = scenarioId;
    const scenario = (groupItem?.cenarios || []).find((item) => item.id === scenarioId) || {};
    const groupSelected = investorState.selectedGroupIds.has(String(groupId));
    const action = `<label><input type="checkbox" class="motor360-scenario-select-input" data-group-id="${groupId}" data-scenario-id="${scenarioId}" ${selectedScenarioIdsForGroup(groupId).has(scenarioId) ? "checked" : ""} ${groupSelected ? "" : "disabled"}> Escolher para análise</label>`;
    card.querySelector(".motor360-scenario-title")?.insertAdjacentHTML("beforeend", action);
  });
  results.querySelectorAll("[data-screen-jump]").forEach((button) => button.addEventListener("click", () => activateScreen(button.dataset.screenJump)));
  results.querySelectorAll("[data-open-selected-groups-workspace]").forEach((button) => button.addEventListener("click", openSelectedGroupsWorkspace));
  results.querySelectorAll("[data-motor360-blocking-diagnostics]").forEach((button) => button.addEventListener("click", () => renderMotor360BlockingDiagnostics(investorState.audit || result.audit)));
  results.querySelectorAll(".motor360-scenario-select-input").forEach((input) => input.addEventListener("change", (event) => {
    const groupId = String(event.target.dataset.groupId || "");
    if (!investorState.selectedGroupIds.has(groupId)) {
      event.target.checked = false;
      showToast("Selecione o grupo antes de escolher o cenário.", "warning");
      return;
    }
    const ids = selectedScenarioIdsForGroup(groupId);
    event.target.checked ? ids.add(event.target.dataset.scenarioId) : ids.delete(event.target.dataset.scenarioId);
    if (ids.size) investorState.selectedScenarioIds.set(groupId, [...ids]);
    else investorState.selectedScenarioIds.delete(groupId);
    persistMotor360Selection();
    renderInvestorAnalysis(investorState.result);
    renderSelectedGroupsScreen();
  }));
  results.querySelectorAll("[data-group-anchor]").forEach((button) => button.addEventListener("click", () => focusMotor360Group(button.dataset.groupAnchor)));
  results.querySelectorAll("[data-floating-summary-toggle]").forEach((button) => button.addEventListener("click", () => {
    investorState.floatingSummaryMinimized = !investorState.floatingSummaryMinimized;
    const summaryCard = button.closest(".motor360-floating-summary");
    summaryCard?.classList.toggle("is-minimized", investorState.floatingSummaryMinimized);
    button.textContent = investorState.floatingSummaryMinimized ? "+" : "−";
    button.title = investorState.floatingSummaryMinimized ? "Expandir composição" : "Minimizar composição";
    button.setAttribute("aria-expanded", investorState.floatingSummaryMinimized ? "false" : "true");
  }));
  results.querySelectorAll(".motor360-group-select-input").forEach((input) => input.addEventListener("change", (event) => {
    const groupId = String(event.target.dataset.groupId || "");
    if (event.target.checked) {
      const selectedItem = motor360FinalItems()
        .find((item) => motor360GroupKey(item) === groupId);
      if (!investorState.administrator && selectedItem?.administradora) {
        investorState.administrator = selectedItem.administradora;
        const administratorSelect = document.getElementById("investorAdministratorFilter");
        if (administratorSelect) administratorSelect.value = selectedItem.administradora;
        persistMotor360Selection();
        updateInvestorPreferenceSummary();
      }
      if (investorState.administrator && motor360AdministratorKey(selectedItem) !== motor360AdministratorKey(investorState.administrator)) {
        event.target.checked = false;
        showToast("Selecione grupos de apenas uma administradora por composição.", "warning");
        return;
      }
      investorState.selectedGroupIds.add(groupId);
      if (selectedItem) investorState.selectedGroupData.set(groupId, selectedItem);
      if (!investorState.quotaCounts.has(groupId)) investorState.quotaCounts.set(groupId, suggestedCompositionQuotas(selectedItem, investorState.selectedGroupScenario === "with_embedded" ? "with_embedded" : "without_embedded"));
    } else {
      investorState.selectedGroupIds.delete(groupId);
      investorState.selectedScenarioIds.delete(groupId);
      investorState.quotaCounts.delete(groupId);
      investorState.selectedGroupData.delete(groupId);
      if (!investorState.selectedGroupIds.size) {
        investorState.administrator = "";
        const administratorSelect = document.getElementById("investorAdministratorFilter");
        if (administratorSelect) administratorSelect.value = "";
        persistMotor360Selection();
        updateInvestorPreferenceSummary();
      }
    }
    persistMotor360Selection();
    renderInvestorAnalysis(investorState.result);
    renderSelectedGroupsScreen();
  }));
  results.querySelectorAll("[data-quota-action]").forEach((control) => control.addEventListener(control.dataset.quotaAction === "input" ? "change" : "click", (event) => {
    const groupId = String(control.dataset.groupId || "");
    const current = Math.min(50, Math.max(1, Number(investorState.quotaCounts.get(groupId) || 1)));
    const requested = control.dataset.quotaAction === "increase"
      ? current + 1
      : control.dataset.quotaAction === "decrease"
        ? current - 1
        : Number(control.value);
    const nextQuotaCount = Math.min(50, Math.max(1, Number.isFinite(requested) ? requested : 1));
    investorState.quotaCounts.set(groupId, nextQuotaCount);
    const selectedItem = motor360FinalItems()
      .find((item) => motor360GroupKey(item) === groupId);
    const historicalLimit = Number(motor360QuotaCapacity(selectedItem)?.limite_cotas);
    if (Number.isFinite(historicalLimit) && nextQuotaCount > historicalLimit) {
      showToast(`A quantidade selecionada ultrapassa a média histórica de ${historicalLimit} cota(s) para o perfil deste grupo.`, "warning");
    }
    persistMotor360Selection();
    renderInvestorAnalysis(investorState.result);
    renderSelectedGroupsScreen();
  }));
  results.querySelectorAll(".motor360-group-audit-btn").forEach((button) => button.addEventListener("click", () => renderMotor360GroupAudit(button.dataset.groupId)));
  results.querySelectorAll("[data-motor360-history-group]").forEach((trigger) => {
    const showHistory = () => {
      const groupId = String(trigger.dataset.motor360HistoryGroup || "");
      const item = motor360FinalItems()
        .find((entry) => String(entry.grupo || entry.grupo_id || "") === groupId);
      showGroupHistoryHoverModal(trigger, item, motor360QuotaCapacity(item));
    };
    trigger.addEventListener("mouseenter", showHistory);
    trigger.addEventListener("focus", showHistory);
    trigger.addEventListener("mouseleave", () => scheduleHistoryHoverHide());
    trigger.addEventListener("blur", () => scheduleHistoryHoverHide());
  });
  setInvestorAnalysisState("results");
  if (!document.getElementById("selectedGroupsWorkspace")?.classList.contains("d-none")) renderSelectedGroupsScreen();
}

function renderInvestorPreferenceOptions() {
  const options = document.getElementById("investorPreferencesOptions");
  if (!options) return;
  options.innerHTML = investorPreferenceFlags.map((flag) => `
    <label class="investor-preference-option"><input type="checkbox" value="${flag.id}" ${investorState.preferences.includes(flag.id) ? "checked" : ""}> <span>${escapeHtml(flag.label)}</span></label>
  `).join("");
}

function updateInvestorPreferenceSummary() {
  const summary = document.getElementById("investorPreferencesSummary");
  if (!summary) return;
  const preferenceText = investorState.preferences.length
    ? `${investorState.preferences.length} preferência(s) aplicada(s)`
    : "Sem ordenação adicional";
  summary.textContent = investorState.administrator
    ? `${investorState.administrator} · ${preferenceText}`
    : preferenceText;
}

function setInvestorAnalysisState(state) {
  const status = document.getElementById("investorAnalysisStatus");
  const loading = document.getElementById("investorAnalysisLoading");
  const error = document.getElementById("investorAnalysisError");
  const empty = document.getElementById("investorAnalysisEmpty");
  const results = document.getElementById("investorAnalysisResults");
  const summary = document.getElementById("investorAnalysisSummary");
  const normalizedState = ["loading", "error", "results", "empty"].includes(state) ? state : "empty";

  loading?.classList.toggle("d-none", normalizedState !== "loading");
  error?.classList.toggle("d-none", normalizedState !== "error");
  empty?.classList.toggle("d-none", normalizedState !== "empty");
  results?.classList.toggle("d-none", normalizedState !== "results");
  if (normalizedState !== "results" && summary) summary.innerHTML = "";

  if (!status) return;
  const labels = {
    loading: "Processando...",
    error: "Erro no cálculo",
    results: "Análise concluída",
    empty: "Aguardando perfil",
  };
  const renderedGroupCount = results?.querySelectorAll(".motor360-group-card").length;
  status.textContent = normalizedState === "results" && results?.querySelector(".motor360-group-list")
    ? `${renderedGroupCount} grupos disponíveis exibidos`
    : labels[normalizedState];
  status.dataset.state = normalizedState;
}

function syncInvestorPreferencesFromInputs() {
  investorState.preferences = Array.from(
    document.querySelectorAll("#investorPreferencesOptions input:checked"),
    (input) => input.value,
  );
  updateInvestorPreferenceSummary();
  if (investorState.result) renderInvestorAnalysis(investorState.result);
}

async function loadInvestorAnalysis() {
  const status = document.getElementById("investorAnalysisStatus");
  if (!status) return;
  investorAnalysisController?.abort();
  const requestId = ++investorAnalysisRequestId;
  const startedAt = performance.now();
  const controller = new AbortController();
  investorAnalysisController = controller;
  addMotor360ExecutionLog("Execução do Motor 360 iniciada", `Requisição ${requestId}.`);
  // Administradora e cenário são filtros locais do Motor 360. Pedir todos os
  // grupos e cenários uma vez permite alterná-los sem nova análise no servidor.
  const profile = { ...collectClientProfile(), administradora: null, filtro_lance_embutido: null };
  const analysisKey = investorAnalysisCacheKey(profile);
  if (investorState.result && investorState.analysisKey === analysisKey) {
    renderInvestorAnalysis(investorState.result);
    return;
  }
  if (!investorState.result) {
    try {
      const cached = JSON.parse(sessionStorage.getItem(INVESTOR_ANALYSIS_CACHE_KEY) || "null");
      if (cached?.key === analysisKey && cached.result) {
        investorState.result = cached.result;
        investorState.analysisKey = cached.key;
        investorState.audit = cached.result.audit || null;
        syncMotor360BidExplorer();
        renderInvestorAnalysis(cached.result);
        return;
      }
    } catch (_) { /* cache inválido: recalcular */ }
  }
  if (!(Number(profile.credito_desejado) > 0)) {
    addMotor360ExecutionLog("Perfil não disponível para análise", "Crédito desejado ausente ou igual a zero.", "warning");
    status.textContent = "Aguardando perfil do cliente";
    setInvestorAnalysisState("empty");
    return;
  }
  status.textContent = "Processando...";
  setInvestorAnalysisState("loading");
  addMotor360ExecutionLog("Requisição enviada", `Crédito ${formatMoney(profile.credito_desejado)} · parcela ${formatMoney(profile.parcela_desejada)} · RP ${formatMoney(profile.lance_recursos_proprios ?? profile.lance_maximo_recursos_proprios)} · FGTS ${formatMoney(profile.fgts_total)} · renda ${formatMoney(profile.renda_total)}.`);
  try {
    const retryableStatuses = new Set([502, 503, 504]);
    const maxAttempts = 3;
    let response;
    let result = {};
    for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
      response = await fetch("/api/viabilidade-360/analisar", {
        method: "POST",
        cache: "no-store",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        signal: controller.signal,
        body: JSON.stringify(profile),
      });
      result = await response.json().catch(() => ({}));
      addMotor360ExecutionLog("Resposta recebida", `Tentativa ${attempt}/${maxAttempts} · HTTP ${response.status} · ${formatMotor360Duration(performance.now() - startedAt)} · ${result.request_id || "sem ID"}.`);
      const serverTiming = formatMotor360ServerTiming(response.headers.get("Server-Timing"));
      if (serverTiming) addMotor360ExecutionLog("Tempos detalhados do servidor", serverTiming);
      if (response.ok || !retryableStatuses.has(response.status) || attempt === maxAttempts) break;
      status.textContent = `Sincronizando base... ${attempt + 1}/${maxAttempts}`;
      addMotor360ExecutionLog("Nova tentativa programada", `Serviço temporariamente indisponível (HTTP ${response.status}).`, "warning");
      await new Promise((resolve) => setTimeout(resolve, attempt * 1000));
    }
    if (!response.ok) throw new Error(result.error || "Falha ao calcular a viabilidade dos grupos.");
    if (requestId !== investorAnalysisRequestId) return;
    investorState.result = result;
    investorState.analysisKey = analysisKey;
    investorState.audit = result.audit || null;
    try { sessionStorage.setItem(INVESTOR_ANALYSIS_CACHE_KEY, JSON.stringify({ key: analysisKey, result })); } catch (_) { /* cache cheio */ }
    syncMotor360BidExplorer();
    const compositionCount = Number(result.total_grupos_composicao ?? 0);
    const displayedCount = Number(result.total_grupos_preselecionados ?? result.total_grupos_viaveis ?? 0);
    const oneQuotaCount = Math.max(0, displayedCount - compositionCount);
    addMotor360ExecutionLog("Análise concluída", `${result.total_grupos_analisados ?? 0} analisados · ${displayedCount} exibidos (${oneQuotaCount} opção(ões) de 1 cota · ${compositionCount} que exigem composição).`);
    renderInvestorAnalysis(result);
    loadMotor360Audit(result.audit_id);
  } catch (error) {
    if (error.name === "AbortError" || requestId !== investorAnalysisRequestId) return;
    addMotor360ExecutionLog("Falha na análise", error.message || "Erro não identificado.", "error");
    status.textContent = "Erro no cálculo";
    setInvestorAnalysisState("error");
    showToast(error.message || "Não foi possível calcular a viabilidade dos grupos.", "danger");
  } finally {
    if (requestId === investorAnalysisRequestId) investorAnalysisController = null;
  }
}

function investorAnalysisCacheKey(profile) {
  return JSON.stringify(profile);
}

function evaluatePjCapacityScenarios({
  faturamento,
  rendaSocios,
  parcelaDesejada,
  age,
  rule = null,
}) {
  const acceptsPJ = administratorRuleBoolean(rule, "aceita_pj", true);
  const allowsPjSocios = administratorRuleBoolean(rule, "permite_composicao_pj_socios", true);
  const allowsCpfSocio = administratorRuleBoolean(rule, "permite_cpf_socio", true);
  const pjPercent = administratorRuleCommitment(rule, "percentual_comprometimento_pj", DEFAULT_PJ_COMMITMENT_PERCENT);
  const cpfPercent = administratorRuleCommitment(rule, "percentual_comprometimento_cpf", DEFAULT_CPF_COMMITMENT_PERCENT);
  const basePjSocios = faturamento + rendaSocios;
  const scenarios = [
    {
      key: "pj_pura",
      label: "Cenario 1 - CNPJ com renda PJ",
      approvalLabel: "Aprovacao somente pela PJ",
      allowed: acceptsPJ,
      base: faturamento,
      percent: pjPercent,
      capacity: faturamento * pjPercent,
      approved: acceptsPJ && parcelaDesejada > 0 && faturamento * pjPercent >= parcelaDesejada,
      alert: acceptsPJ ? "Administradora aceita CNPJ; avaliar PJ pura primeiro." : "Administradora nao aceita contratacao por CNPJ.",
    },
    {
      key: "pj_socios",
      label: "Cenario 2 - CNPJ com PJ + socio",
      approvalLabel: "Aprovacao PJ com composicao de renda dos socios",
      allowed: acceptsPJ && allowsPjSocios,
      base: basePjSocios,
      percent: pjPercent,
      capacity: basePjSocios * pjPercent,
      approved: acceptsPJ && allowsPjSocios && parcelaDesejada > 0 && basePjSocios * pjPercent >= parcelaDesejada,
      alert: acceptsPJ && allowsPjSocios ? "Usar se a PJ pura nao aprovar." : "Composicao PJ + socios nao permitida pela administradora.",
    },
    {
      key: "cpf_socios",
      label: "Cenario 3 - CPF do socio",
      approvalLabel: "Aprovacao somente pelo CPF dos socios",
      allowed: allowsCpfSocio,
      base: rendaSocios,
      percent: cpfPercent,
      capacity: rendaSocios * cpfPercent,
      approved: allowsCpfSocio && age.ok && parcelaDesejada > 0 && rendaSocios * cpfPercent >= parcelaDesejada,
      alert: allowsCpfSocio ? "Alternativa quando CNPJ nao for aceito, nao passar ou nao for recomendado." : "Analise pelo CPF do socio nao permitida pela administradora.",
    },
  ];
  const firstApproved = scenarios.find((scenario) => scenario.approved);
  return {
    acceptsPJ,
    allowsPjSocios,
    allowsCpfSocio,
    pjPercent,
    cpfPercent,
    basePjSocios,
    scenarios,
    approvedScenario: firstApproved?.approvalLabel || "Reprovado por capacidade financeira",
  };
}

function calculateClientPreliminaryAnalysis(titulares, holderSummary) {
  const objectiveByContemplationProfile = {
    urgent: "Contemplar - urgente - 3 meses",
    fast: "Contemplar - rapido - 6 meses",
    moderate: "Contemplar - moderado - 12 meses",
    conservative: "Contemplar - conservador - 24 meses",
    long_term: "Contemplar - investidor - 36 meses",
  };
  const selectedContemplationProfile = document.getElementById("clientProfileContemplacaoPerfil")?.value;
  const objetivo = objectiveByContemplationProfile[selectedContemplationProfile]
    || document.getElementById("clientProfileObjetivo").value;
  const credito = toNumber(document.getElementById("clientProfileCredito").value);
  const parcelaDesejada = toNumber(document.getElementById("clientProfileParcelaIdeal").value);
  const lanceManual = toNumber(document.getElementById("clientProfileLanceProprio").value);
  const lanceProprio = Number(holderSummary.lance_recursos_proprios || 0) || lanceManual;
  const pessoasAtivas = (titulares.pessoas_fisicas || []).filter((person) => (
    person.nome || person.nascimento || Number(person.lance_fgts || 0) > 0 || Number(person.renda || 0) > 0
  ));
  const pfRenda = pessoasAtivas.reduce((sum, person) => sum + Number(person.renda || 0), 0);
  const pfFgts = pessoasAtivas.reduce((sum, person) => sum + Number(person.lance_fgts || 0), 0);
  const pfParcelaMaxima = pfRenda * 0.3;
  const pfTotalLanceRP = lanceProprio;
  const pfCobertura = pfFgts + pfTotalLanceRP;
  const pfLinha1Ok = parcelaDesejada <= pfParcelaMaxima && parcelaDesejada > 0;
  const pfLinha2Ok = credito > 0 && pfCobertura >= credito;
  const pfAge = preliminaryAgeSummary(pessoasAtivas);
  const empresa = titulares.pessoa_juridica?.empresa || {};
  const sociosAtivos = (titulares.pessoa_juridica?.socios || []).filter((socio) => (
    socio.nome || socio.nascimento || Number(socio.renda || 0) > 0
  ));
  const pjFaturamento = Number(empresa.faturamento_mensal || 0);
  const pjRendaSocio = sociosAtivos.reduce((sum, socio) => sum + Number(socio.renda || 0), 0);
  const pjTotalLanceRP = lanceProprio;
  const pjLinha2Ok = credito > 0 && pjTotalLanceRP >= credito;
  const pjAge = preliminaryAgeSummary(sociosAtivos);
  const pjCapacity = evaluatePjCapacityScenarios({
    faturamento: pjFaturamento,
    rendaSocios: pjRendaSocio,
    parcelaDesejada,
    age: pjAge,
  });
  return {
    tipoContratacao: titulares.tipo_contratacao,
    pessoaFisica: {
      objetivo,
      credito,
      totalRenda: pfRenda,
      comprometimentoMaximo: pfParcelaMaxima,
      parcelaMaxima: pfParcelaMaxima,
      parcelaDesejada,
      totalLanceFGTS: pfFgts,
      totalLanceRP: pfTotalLanceRP,
      totalLanceFGTSRP: pfCobertura,
      percentualFGTS: credito > 0 ? pfFgts / credito : 0,
      percentualCobertura: credito > 0 ? pfCobertura / credito : 0,
      decisaoLinha1: preliminaryDecision(pfLinha1Ok),
      decisaoLinha2: preliminaryDecision(pfLinha2Ok),
      maiorIdade: pfAge.label,
      resultado: preliminaryDecision(pfLinha1Ok && pfLinha2Ok && pfAge.ok),
    },
    pessoaJuridica: {
      objetivo,
      credito,
      totalRendaPJ: pjFaturamento,
      totalRendaSocio: pjRendaSocio,
      totalRendaPJComSocio: pjCapacity.basePjSocios,
      comprometimentoMaximo: pjCapacity.scenarios[0].capacity,
      parcelaDesejada,
      parcelaMaximaPJ: pjCapacity.scenarios[0].capacity,
      parcelaMaximaPJComSocio: pjCapacity.scenarios[1].capacity,
      parcelaMaximaSocioPF: pjCapacity.scenarios[2].capacity,
      percentualComprometimentoPJ: pjCapacity.pjPercent,
      percentualComprometimentoCPF: pjCapacity.cpfPercent,
      cenariosCapacidade: pjCapacity.scenarios,
      cenarioAprovado: pjCapacity.approvedScenario,
      totalLanceRP: pjTotalLanceRP,
      percentualCoberturaPJ: credito > 0 ? pjFaturamento / credito : 0,
      percentualCoberturaSocio: credito > 0 ? pjRendaSocio / credito : 0,
      cnpjSomente: approvalStatusLabel(pjCapacity.scenarios[0].approved),
      cnpjComSocio: approvalStatusLabel(pjCapacity.scenarios[1].approved),
      cpfSocio: approvalStatusLabel(pjCapacity.scenarios[2].approved),
      decisaoLinha2: preliminaryDecision(pjLinha2Ok),
      maiorIdade: pjAge.label,
      resultado: preliminaryDecision(Boolean(pjCapacity.scenarios.find((scenario) => scenario.approved)) && pjLinha2Ok),
    },
  };
}

function renderPreliminaryRows(rows) {
  return rows.map(([label, value, percent = "", status = ""]) => `
    <div class="client-preliminary-row">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value)}</strong>
      <em>${escapeHtml(percent)}</em>
      <small>${escapeHtml(status)}</small>
    </div>
  `).join("");
}

function renderPreliminaryAuditTrail(title, steps) {
  return `
    <section class="client-preliminary-audit">
      <h4>${escapeHtml(title)}</h4>
      <ol>
        ${steps.map((step) => `<li>${escapeHtml(step)}</li>`).join("")}
      </ol>
    </section>
  `;
}

function renderPjScenarioRows(scenarios) {
  return (scenarios || []).map((scenario) => ([
    scenario.label,
    `Base ${formatMoney(scenario.base)} x ${formatPercent(scenario.percent)} = ${formatMoney(scenario.capacity)}`,
    "",
    scenario.allowed ? approvalStatusLabel(scenario.approved) : "nao permitido",
  ]));
}

function renderClientPreliminaryAnalysis(analysis) {
  const target = document.getElementById("clientPreliminaryAnalysis");
  if (!target) return;
  const pf = analysis.pessoaFisica;
  const pj = analysis.pessoaJuridica;
  const activeType = analysis.tipoContratacao === "pj" ? "pj" : "pf";
  if (activeType === "pj") {
    target.innerHTML = `
      <article class="client-preliminary-card active">
        <header>Pessoa Juridica</header>
        ${renderPreliminaryRows([
          ["Objetivo do consorcio", pj.objetivo || "-"],
          ["Credito desejado", formatMoney(pj.credito)],
          ["Total Renda PJ", formatMoney(pj.totalRendaPJ)],
          ["Total Renda Socio", formatMoney(pj.totalRendaSocio)],
          ["Total Renda PJ + Socio", formatMoney(pj.totalRendaPJComSocio)],
          ["Comprometimento maximo", `PJ ${formatPercent(pj.percentualComprometimentoPJ)} / CPF ${formatPercent(pj.percentualComprometimentoCPF)}`],
          ["Parcela Desejada", formatMoney(pj.parcelaDesejada)],
          ...renderPjScenarioRows(pj.cenariosCapacidade),
          ["Cenario aprovado", pj.cenarioAprovado],
          ["Total Lance RP", formatMoney(pj.totalLanceRP)],
          ["Maior idade (seguro)", pj.maiorIdade],
        ])}
        ${renderPreliminaryAuditTrail("Demonstrativo logico do calculo", [
          `O objetivo selecionado foi ${pj.objetivo || "-"} e o credito desejado informado foi ${formatMoney(pj.credito)}.`,
          `A parcela desejada considerada veio do campo Parcela maxima desejada: ${formatMoney(pj.parcelaDesejada)}.`,
          `Cenario 1: avaliacao do consorcio no CNPJ usando somente a renda da PJ. Faturamento ${formatMoney(pj.totalRendaPJ)} x ${formatPercent(pj.percentualComprometimentoPJ)} = ${formatMoney(pj.parcelaMaximaPJ)}. Status: ${pj.cnpjSomente}.`,
          `Cenario 2: se a renda da PJ sozinha nao aprovar, o sistema soma PJ + socio. ${formatMoney(pj.totalRendaPJ)} + ${formatMoney(pj.totalRendaSocio)} = ${formatMoney(pj.totalRendaPJComSocio)}; ${formatPercent(pj.percentualComprometimentoPJ)} = ${formatMoney(pj.parcelaMaximaPJComSocio)}. Status: ${pj.cnpjComSocio}.`,
          `Cenario 3: se a administradora nao aprovar consorcio para o CNPJ, o sistema avalia o CPF do socio. Renda socios ${formatMoney(pj.totalRendaSocio)} x ${formatPercent(pj.percentualComprometimentoCPF)} = ${formatMoney(pj.parcelaMaximaSocioPF)}. Status: ${pj.cpfSocio}.`,
          `Cenario recomendado pela ordem logica: ${pj.cenarioAprovado}.`,
          `O lance maximo com recurso proprio informado foi ${formatMoney(pj.totalLanceRP)} e foi usado como Total Lance RP.`,
          `A validacao de idade retornou: ${pj.maiorIdade}.`,
        ])}
      </article>
    `;
    return;
  }
  target.innerHTML = `
    <article class="client-preliminary-card active">
      <header>Pessoa Fisica</header>
      ${renderPreliminaryRows([
        ["Objetivo do consorcio", pf.objetivo || "-"],
        ["Credito desejado", formatMoney(pf.credito)],
        ["Total Renda", formatMoney(pf.totalRenda)],
        ["Comprometimento maximo", formatPercent(0.3)],
        ["Parcela Maxima", formatMoney(pf.parcelaMaxima)],
        ["Parcela Desejada", formatMoney(pf.parcelaDesejada)],
        ["Total Lance FGTS", formatMoney(pf.totalLanceFGTS), formatPercent(pf.percentualFGTS), "sem embutido"],
        ["Total Lance RP", formatMoney(pf.totalLanceRP)],
        ["Total Lance FGTS + RP", formatMoney(pf.totalLanceFGTSRP), formatPercent(pf.percentualCobertura), "sem embutido"],
        ["Maior idade (seguro)", pf.maiorIdade],
      ])}
      ${renderPreliminaryAuditTrail("Demonstrativo logico do calculo", [
        `O objetivo selecionado foi ${pf.objetivo || "-"} e o credito desejado informado foi ${formatMoney(pf.credito)}.`,
        `A renda total dos participantes foi somada em ${formatMoney(pf.totalRenda)}. Aplicando 30%, a parcela maxima ficou em ${formatMoney(pf.parcelaMaxima)}.`,
        `A parcela desejada considerada veio do campo Parcela maxima desejada: ${formatMoney(pf.parcelaDesejada)}.`,
        `O Total Lance FGTS foi a soma dos lances FGTS dos participantes: ${formatMoney(pf.totalLanceFGTS)}, equivalente a ${formatPercent(pf.percentualFGTS)} do credito desejado.`,
        `O Total Lance RP veio do campo Lance maximo com recurso proprio: ${formatMoney(pf.totalLanceRP)}.`,
        `Somando FGTS + recurso proprio, o total disponivel para lance ficou em ${formatMoney(pf.totalLanceFGTSRP)}, equivalente a ${formatPercent(pf.percentualCobertura)} do credito desejado.`,
        `A validacao de idade retornou: ${pf.maiorIdade}.`,
      ])}
    </article>
  `;
}

function updateClientProfileTotals() {
  const titulares = collectClientTitularesFromForm();
  const holderSummary = summarizeClientTitulares(titulares);
  const fgts = holderSummary.fgts;
  const lanceManual = toNumber(document.getElementById("clientProfileLanceProprio").value);
  // O lance próprio vem do campo global da operação quando não foi
  // informado individualmente nos cartões dos participantes.
  const lanceParticipantes = Number(holderSummary.lance_recursos_proprios || 0);
  const lance = lanceParticipantes > 0 ? lanceParticipantes : lanceManual;
  if (lanceParticipantes > 0) {
    setMoneyInputValue("clientProfileLanceProprio", lanceParticipantes);
  }
  const renda = holderSummary.renda_total;
  const objectiveRule = clientObjectiveRule(document.getElementById("clientProfileObjetivo").value);
  const conceito = objectiveRule.conceito || clientProfileConcept(objectiveRule.prazo);
  document.getElementById("clientProfileNome").value = holderSummary.nome;
  document.getElementById("clientProfileConjuge").value = holderSummary.nome_conjuge;
  document.getElementById("clientProfileNascimento").value = holderSummary.data_nascimento;
  document.getElementById("clientProfileNascimentoConjuge").value = holderSummary.data_nascimento_conjuge;
  document.getElementById("clientProfileFgtsTitular").value = holderSummary.fgts_titular;
  document.getElementById("clientProfileFgtsConjuge").value = holderSummary.fgts_conjuge;
  document.getElementById("clientProfileRendaTitular").value = holderSummary.renda_titular;
  document.getElementById("clientProfileRendaConjuge").value = holderSummary.renda_conjuge;
  document.getElementById("clientProfilePrazo").value = objectiveRule.prazo;
  // Tipo de bem só filtra grupos quando o operador o informa explicitamente.
  document.getElementById("clientProfileEstadoBem").value = objectiveRule.estadoBem || "Pronto";
  // The income limit is independent from the installment desired by the client.
  document.getElementById("clientProfileParcelaLimite").value = renda * DEFAULT_INCOME_COMMITMENT_PERCENT;
  document.getElementById("clientProfileFgtsTotal").value = formatMoney(fgts);
  document.getElementById("clientProfileTotalDisponivel").value = formatMoney(lance + fgts);
  document.getElementById("clientProfileRendaTotal").value = formatMoney(renda);
  document.getElementById("clientProfileConceito").value = conceito;
  const totals = { fgts, lance, lanceManual, renda, conceito, holderSummary, titulares };
  renderClientPreliminaryAnalysis(calculateClientPreliminaryAnalysis(titulares, holderSummary));
  return totals;
}

function collectClientProfile() {
  const totals = updateClientProfileTotals();
  const summary = totals.holderSummary;
  const objective = document.getElementById("clientProfileObjetivo").value;
  const objectiveProfile = objective.includes("urgente") ? "urgent" : objective.includes("rapido") ? "fast" : objective.includes("moderado") ? "moderate" : objective.includes("conservador") ? "conservative" : objective.includes("investidor") && objective.includes("36") ? "long_term" : "";
  const declaredBid = totals.lance;
  const hasSimulatedBid = investorState.simulatedBid !== null
    && investorState.simulatedBid !== undefined
    && Number.isFinite(Number(investorState.simulatedBid));
  const simulatedBid = hasSimulatedBid ? Number(investorState.simulatedBid) : declaredBid;
  const withEmbedded = document.getElementById("investorFilterWithEmbedded")?.checked === true;
  const withoutEmbedded = document.getElementById("investorFilterWithoutEmbedded")?.checked === true;
  const embeddedFilter = withEmbedded && withoutEmbedded ? "ambos" : withEmbedded ? "sim" : withoutEmbedded ? "nao" : null;
  return {
    tipo_contratacao: totals.titulares.tipo_contratacao,
    titulares: totals.titulares,
    nome: summary.nome,
    nome_conjuge: summary.nome_conjuge,
    credito_desejado: toNumber(document.getElementById("clientProfileCredito").value),
    prazo_desejado: Number(document.getElementById("clientProfilePrazo").value),
    conceito_ia: totals.conceito,
    lance_proprio: simulatedBid,
    lance_proprio_declarado: declaredBid,
    lance_simulado: simulatedBid,
    lance_proprio_participantes: simulatedBid,
    lance_proprio_manual: totals.lanceManual,
    own_resources_source: totals.lance > 0 ? "participants" : "manual",
    lance_recursos_proprios: simulatedBid,
    fgts_titular: summary.fgts_titular,
    fgts_conjuge: summary.fgts_conjuge,
    fgts: totals.fgts,
    renda_titular: summary.renda_titular,
    renda_conjuge: summary.renda_conjuge,
    renda_total: totals.renda,
    parcela_ideal: toNumber(document.getElementById("clientProfileParcelaIdeal").value),
    parcela_limite: toNumber(document.getElementById("clientProfileParcelaLimite").value) || toNumber(document.getElementById("clientProfileParcelaIdeal").value),
    parcela_desejada: toNumber(document.getElementById("clientProfileParcelaIdeal").value),
    data_nascimento: summary.data_nascimento,
    data_nascimento_conjuge: summary.data_nascimento_conjuge,
    objetivo: objective,
    administradora: investorState.administrator || null,
    contemplacao_perfil: document.getElementById("clientProfileContemplacaoPerfil")?.value || objectiveProfile || null,
    filtro_lance_embutido: embeddedFilter || document.getElementById("clientProfileFiltroLanceEmbutido")?.value || null,
    filtro_parcela_reduzida: document.getElementById("clientProfileFiltroParcelaReduzida")?.value || null,
    tipo_bem: document.getElementById("clientProfileTipoBem").value,
    tipo_bem_explicit: Boolean(document.getElementById("clientProfileTipoBem").value),
    estado_bem: document.getElementById("clientProfileEstadoBem").value,
    crm_oportunidade_id: document.getElementById("clientProfileCrmOpportunityId")?.value.trim() || "",
  };
}

function applyImportedCrmData(data, opportunityId) {
  const current = collectClientProfile();
  const imported = data || {};
  const importedPeople = Array.isArray(imported.titulares) ? imported.titulares : [];
  const firstHolder = current.titulares?.pessoas_fisicas?.[0] || {};
  const holder = {
    ...firstHolder,
    nome: imported.nome ?? "",
    nascimento: imported.data_nascimento ?? "",
    renda: imported.renda_total ?? "",
    lance_recursos_proprios: imported.lance_proprio ?? "",
  };
  const pessoas = importedPeople.length ? importedPeople.map((item) => ({
    ...emptyPessoaFisica(0),
    nome: item.nome || "",
    nascimento: item.nascimento || "",
    renda: item.renda || 0,
    lance_fgts: item.lance_fgts || 0,
    lance_recursos_proprios: item.lance_recursos_proprios || 0,
  })) : [holder];
  const titulares = { ...current.titulares, pessoas_fisicas: pessoas };
  const profile = {
    ...current,
    nome: imported.nome ?? "",
    nome_conjuge: "",
    data_nascimento: imported.data_nascimento ?? "",
    credito_desejado: imported.credito_desejado ?? "",
    lance_proprio: imported.lance_proprio ?? "",
    renda_total: imported.renda_total ?? "",
    renda_titular: imported.renda_titular ?? "",
    renda_conjuge: imported.renda_conjuge ?? "",
    fgts_titular: imported.fgts_titular ?? "",
    fgts_conjuge: imported.fgts_conjuge ?? "",
    fgts: imported.fgts ?? "",
    parcela_desejada: imported.parcela_desejada ?? "",
    tipo_bem: imported.tipo_bem ?? "",
    objetivo: imported.objetivo || "",
    nome_conjuge: imported.nome_conjuge || "",
    data_nascimento_conjuge: imported.data_nascimento_conjuge || "",
    tipo_contratacao: imported.tipo_contratacao || (pessoas.length > 1 ? "pf_conjuge" : "pf_individual"),
    titulares,
    crm_oportunidade_id: String(opportunityId),
  };
  renderClientProfileTitulares(profile);
  setInputValue("clientProfileTipoContratacao", profile.tipo_contratacao);
  setMoneyInputValue("clientProfileCredito", imported.credito_desejado ?? "");
  setMoneyInputValue("clientProfileParcelaIdeal", imported.parcela_desejada ?? "");
  setMoneyInputValue("clientProfileLanceProprio", imported.lance_proprio ?? "");
  setInputValue("clientProfileCrmOpportunityId", opportunityId);
  updateClientProfileTotals();
  saveClientProfile({ silent: true });
}

async function importClientProfileFromCrm() {
  const input = document.getElementById("clientProfileCrmOpportunityId");
  const status = document.getElementById("clientProfileCrmStatus");
  const button = document.getElementById("importClientProfileCrmBtn");
  const opportunityId = input?.value.trim();
  if (!opportunityId) {
    showToast("Informe o ID da oportunidade.", "warning");
    return;
  }
  button.disabled = true;
  status.textContent = "Consultando PipeRun...";
  try {
    const result = await apiGet(`/piperun/${encodeURIComponent(opportunityId)}`);
    applyImportedCrmData(result.dados, opportunityId);
    status.textContent = result.encontrado ? "Dados importados. Revise e ajuste se necessário." : "Nenhuma nota de formulário encontrada.";
    showToast(result.encontrado ? "Dados do CRM importados." : "Oportunidade encontrada, mas sem dados de formulário.", result.encontrado ? "success" : "warning");
  } finally {
    button.disabled = false;
  }
}

function applyClientProfileToFlow(profile) {
  const pairs = [
    ["Credito", "credito_desejado"],
    ["LanceProprio", "lance_proprio"],
    ["FgtsTitular", "fgts_titular"],
    ["FgtsConjuge", "fgts_conjuge"],
    ["RendaTitular", "renda_titular"],
    ["RendaConjuge", "renda_conjuge"],
    ["ParcelaIdeal", "parcela_ideal"],
    ["ParcelaLimite", "parcela_limite"],
    ["Nascimento", "data_nascimento"],
    ["NascimentoConjuge", "data_nascimento_conjuge"],
    ["PrazoDesejado", "prazo_desejado"],
    ["Objetivo", "objetivo"],
    ["EstadoBem", "estado_bem"],
  ];
  pairs.forEach(([suffix, key]) => {
    const viabilityTarget = document.getElementById(`viability${suffix === "ParcelaIdeal" ? "Parcela" : suffix}`);
    if (viabilityTarget) viabilityTarget.value = profile[key] ?? "";
  });
  const viabilityTipo = document.getElementById("viabilityTipoBem");
  if (viabilityTipo) viabilityTipo.value = profile.tipo_bem || "Imovel";
  updateViabilityTotals();
}

function saveClientProfile({ silent = false } = {}) {
  const profile = collectClientProfile();
  window.localStorage.setItem(CLIENT_PROFILE_STORAGE_KEY, JSON.stringify(profile));
  applyClientProfileToFlow(profile);
  if (!silent) showToast("Perfil do cliente salvo.", "success");
  return profile;
}

function loadClientProfile() {
  let profile = null;
  try {
    profile = JSON.parse(window.localStorage.getItem(CLIENT_PROFILE_STORAGE_KEY) || "null");
  } catch {
    profile = null;
  }
  if (!profile) {
    renderClientProfileTitulares({ tipo_contratacao: "pf_individual" });
    updateClientProfileTotals();
    return;
  }
  renderClientProfileTitulares(profile);
  setMoneyInputValue("clientProfileCredito", profile.credito_desejado);
  setMoneyInputValue("clientProfileLanceProprio", profile.lance_proprio);
  setMoneyInputValue("clientProfileParcelaIdeal", profile.parcela_ideal ?? profile.parcela_desejada);
  const objective = CLIENT_OBJECTIVE_RULES[profile.objetivo] ? profile.objetivo : "Contemplar - urgente - 3 meses";
  setInputValue("clientProfileObjetivo", objective);
  updateClientProfileTotals();
  investorState.simulatedBid = null;
  applyClientProfileToFlow(collectClientProfile());
  syncMotor360BidExplorer();
}

function resetClientProfile() {
  invalidateInvestorAnalysisForProfileChange();
  document.getElementById("clientProfileForm").reset();
  window.localStorage.removeItem(CLIENT_PROFILE_STORAGE_KEY);
  renderClientProfileTitulares({ tipo_contratacao: "pf_individual" });
  updateClientProfileTotals();
  investorState.simulatedBid = null;
  syncMotor360BidExplorer();
  showToast("Perfil do cliente limpo.", "success");
}

function advanceClientProfile() {
  saveClientProfile({ silent: true });
  activateScreen("motor360");
}

function setConfigState(state) {
  document.getElementById("configLoading").classList.toggle("d-none", state !== "loading");
  document.getElementById("configError").classList.toggle("d-none", state !== "error");
  document.getElementById("configContent").classList.toggle("d-none", state !== "ready");
}

function setInputValue(id, value) {
  const input = document.getElementById(id);
  if (input) input.value = value ?? "";
}

function percentToInput(value) {
  return percentToInputValue(value);
}

function inputToPercent(id) {
  const value = toNumber(document.getElementById(id).value);
  return value > 1 ? value / 100 : value;
}

function inputToPercentFromValue(rawValue) {
  const value = toNumber(rawValue);
  return value > 1 ? value / 100 : value;
}

function setSelectBool(id, value) {
  const select = document.getElementById(id);
  if (select) select.value = value === false ? "false" : "true";
}

function getSelectBool(id) {
  return document.getElementById(id).value === "true";
}

function applyTheme(theme) {
  const normalized = String(theme || "Claro").toLowerCase();
  document.body.dataset.theme = normalized.includes("escuro") ? "escuro" : "claro";
}

function renderBusinessRules(feedbacks = {}) {
  const body = document.getElementById("businessRulesBody");
  if (!body) return;
  body.innerHTML = businessRulesFlow.map((rule) => {
    const feedback = feedbacks[rule.id] || {};
    const status = feedback.status || "Pendente";
    const options = businessRuleStatuses.map((item) => `<option value="${escapeHtml(item)}" ${item === status ? "selected" : ""}>${escapeHtml(item)}</option>`).join("");
    return `
      <tr>
        <td><strong>${escapeHtml(rule.etapa)}</strong></td>
        <td>
          <ul class="business-rule-list">
            ${rule.regras.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}
          </ul>
        </td>
        <td>
          <textarea class="form-control business-rule-note-input" rows="4" data-business-rule-note="${escapeHtml(rule.id)}" placeholder="Descreva aqui o feedback da equipe sobre esta etapa">${escapeHtml(feedback.observacao || "")}</textarea>
        </td>
        <td>
          <select class="form-select" data-business-rule-status="${escapeHtml(rule.id)}">${options}</select>
        </td>
      </tr>
    `;
  }).join("");
}

function hasBusinessRuleFeedbackContent(feedbacks = {}) {
  return Object.values(feedbacks).some((feedback) => {
    const note = (feedback?.observacao || "").trim();
    const status = feedback?.status || "Pendente";
    return note || status !== "Pendente";
  });
}

function collectBusinessRuleFeedbacks({ preserveExistingWhenBlank = false } = {}) {
  const result = {};
  let allControlsRendered = true;
  businessRulesFlow.forEach((rule) => {
    const noteInput = document.querySelector(`[data-business-rule-note="${rule.id}"]`);
    const statusInput = document.querySelector(`[data-business-rule-status="${rule.id}"]`);
    if (!noteInput || !statusInput) {
      allControlsRendered = false;
    }
    const note = noteInput?.value.trim() || "";
    const status = statusInput?.value || "Pendente";
    result[rule.id] = { observacao: note, status };
  });
  const existingFeedbacks = configState.data?.regras_negocio_feedbacks || {};
  if (
    preserveExistingWhenBlank &&
    hasBusinessRuleFeedbackContent(existingFeedbacks) &&
    (!allControlsRendered || !hasBusinessRuleFeedbackContent(result))
  ) {
    return existingFeedbacks;
  }
  return result;
}

async function saveBusinessRuleFeedbacks() {
  const regrasNegocioFeedbacks = collectBusinessRuleFeedbacks();
  await apiPut("/configuracoes", { regras_negocio_feedbacks: regrasNegocioFeedbacks });
  configState.data = { ...(configState.data || {}), regras_negocio_feedbacks: regrasNegocioFeedbacks };
  showToast("Feedbacks das regras de negocio salvos.", "success");
  addOperationalLog("Feedbacks das regras de negocio salvos");
}

function renderConfiguracoes(data) {
  configState.data = data;
  const pref = data.preferencias || {};
  const params = data.parametros_financeiros || {};
  const sistema = data.sistema || {};

  applyTheme(pref.tema);

  setInputValue("configTaxaAdm", percentToInput(params.taxa_administracao_padrao));
  setInputValue("configFundoReserva", percentToInput(params.fundo_reserva_padrao));
  setInputValue("configLanceFixo", percentToInput(params.percentual_lance_fixo_padrao));
  setInputValue("configLanceModerado", percentToInput(params.percentual_lance_moderado_padrao));
  setInputValue("configLanceAgressivo", percentToInput(params.percentual_lance_agressivo_padrao));
  setInputValue("configPrazoMaximo", params.prazo_maximo);
  setInputValue("configPrazoMinimo", params.prazo_minimo);
  setInputValue("configIndiceCorrecao", params.indice_correcao_anual);

  document.getElementById("configUsersBody").innerHTML = (data.usuarios || []).map((user, index) => {
    const inactive = user.status !== "Ativo";
    const nextStatus = inactive ? "Ativo" : "Inativo";
    return `
    <tr>
      <td>${escapeHtml(user.nome)}</td>
      <td>${escapeHtml(user.email)}</td>
      <td>${escapeHtml(user.perfil)}</td>
      <td><span class="status-badge ${inactive ? "inactive" : ""}">${escapeHtml(user.status)}</span></td>
      <td>${escapeHtml(user.ultimo_acesso || "-")}</td>
      <td>
        <div class="row-actions">
          <button class="btn btn-sm btn-outline-secondary" type="button" data-config-user-action="editar" data-config-user-index="${index}">Editar</button>
          <button class="btn btn-sm btn-outline-secondary" type="button" data-config-user-action="status" data-config-user-index="${index}" data-next-status="${nextStatus}">${inactive ? "Ativar" : "Inativar"}</button>
          <button class="btn btn-sm btn-outline-danger" type="button" data-config-user-action="remover" data-config-user-index="${index}">Remover</button>
        </div>
      </td>
    </tr>
  `;
  }).join("");

  renderBusinessRules(data.regras_negocio_feedbacks || {});
  renderAdministratorRules(data.administradoras_regras || []);
  document.getElementById("configSystemGrid").innerHTML = [
    ["Aplicacao", sistema.app],
    ["Versao", sistema.version],
    ["Ambiente", sistema.environment],
    ["Debug", sistema.debug ? "Sim" : "Nao"],
    ["Google Sheets configurado", sistema.google_sheets_configurado ? "Sim" : "Nao"],
    ["Aba da planilha", sistema.google_sheet_name || "-"],
    ["Logs nesta sessao", operationalLogs.length],
  ].map(([label, value]) => detailField(label, value)).join("");
  renderOperationalLogs();
}

function adminRuleNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) && number > 0 ? number : "";
}

function renderAdministratorRules(rules) {
  document.getElementById("administratorRulesSubtitle").textContent = `${rules.length} administradora(s) cadastrada(s)`;
  document.getElementById("administratorRulesBody").innerHTML = rules.map((rule, index) => `
    <tr>
      <td>${escapeHtml(rule.administradora || "-")}</td>
      <td>${escapeHtml(rule.status_operacional || "Ativo")}</td>
      <td>${rule.seguro_obrigatorio ? "Sim" : "Nao"}</td>
      <td>${rule.idade_maxima || "-"}</td>
      <td>${rule.limite_sem_comprovacao_renda_texto ? escapeHtml(rule.limite_sem_comprovacao_renda_texto) : formatMoney(rule.limite_sem_comprovacao_renda)}</td>
      <td>${escapeHtml(rule.aceita_adesao_clientes_texto || "-")}</td>
      <td>${formatPercent(rule.percentual_lance_embutido || 0)}</td>
      <td>${rule.aceita_saida_fiscal ? "Sim" : "Nao"}</td>
      <td>${formatPercent(rule.taxa_adm || 0)}</td>
      <td>${formatPercent(rule.fundo_reserva || 0)}</td>
      <td>
        <div class="row-actions">
          <button class="btn btn-sm btn-outline-secondary" type="button" data-admin-rule-action="editar" data-admin-rule-index="${index}">Editar</button>
          <button class="btn btn-sm btn-outline-danger" type="button" data-admin-rule-action="remover" data-admin-rule-index="${index}">Remover</button>
        </div>
      </td>
    </tr>
  `).join("");
}

function clearAdministratorRuleForm() {
  configAdministratorRuleIndex = null;
  document.getElementById("administratorRulesForm").reset();
  document.getElementById("adminRuleStatusProduto").value = "Ativo";
  document.getElementById("adminRuleAceitaFgts").value = "true";
  document.getElementById("adminRuleAceitaPJ").value = "true";
  document.getElementById("adminRuleComposicaoPJSocios").value = "true";
  document.getElementById("adminRuleCpfSocio").value = "true";
  setInputValue("adminRuleComprometimentoPJ", percentToInput(DEFAULT_PJ_COMMITMENT_PERCENT));
  setInputValue("adminRuleComprometimentoCPF", percentToInput(DEFAULT_CPF_COMMITMENT_PERCENT));
  document.getElementById("saveAdministratorRuleBtn").textContent = "Salvar Administradora";
}

function collectAdministratorRuleForm() {
  const aceitaPJ = getSelectBool("adminRuleAceitaPJ");
  const permiteComposicao = getSelectBool("adminRuleComposicaoPJSocios");
  const permiteCpfSocio = getSelectBool("adminRuleCpfSocio");
  return {
    administradora: document.getElementById("adminRuleAdministradora").value.trim(),
    status_operacional: document.getElementById("adminRuleStatusProduto").value,
    data_cadastro_produto: document.getElementById("adminRuleDataProduto").value,
    responsavel_produto: document.getElementById("adminRuleResponsavelProduto").value.trim(),
    seguro_obrigatorio: getSelectBool("adminRuleSeguro"),
    idade_maxima: adminRuleNumber(document.getElementById("adminRuleIdadeMaxima").value) || null,
    limite_sem_comprovacao_renda: optionalNumber(document.getElementById("adminRuleLimiteRenda").value),
    limite_sem_comprovacao_renda_texto: document.getElementById("adminRuleLimiteRendaTexto").value.trim(),
    percentual_lance_embutido: inputToPercent("adminRuleLanceEmbutido"),
    tipo_lance_embutido: document.getElementById("adminRuleTipoLance").value,
    taxa_adm: inputToPercent("adminRuleTaxaAdm"),
    possui_negociacao_taxa: document.getElementById("adminRuleNegociacao").value.trim(),
    fundo_reserva: inputToPercent("adminRuleFundoReserva"),
    aceita_adesao_clientes_texto: document.getElementById("adminRuleAceitaAdesao").value.trim(),
    aceita_saida_fiscal: getSelectBool("adminRuleSaidaFiscal"),
    aceita_fgts: getSelectBool("adminRuleAceitaFgts"),
    aceita_pj: aceitaPJ,
    aceita_pj_texto: adminRuleBoolText(aceitaPJ, true),
    permite_composicao_pj_socios: permiteComposicao,
    permite_composicao_pj_socios_texto: adminRuleBoolText(permiteComposicao, true),
    permite_cpf_socio: permiteCpfSocio,
    permite_cpf_socio_texto: adminRuleBoolText(permiteCpfSocio, true),
    percentual_comprometimento_pj: inputToPercent("adminRuleComprometimentoPJ") || DEFAULT_PJ_COMMITMENT_PERCENT,
    percentual_comprometimento_cpf: inputToPercent("adminRuleComprometimentoCPF") || DEFAULT_CPF_COMMITMENT_PERCENT,
    observacoes_operacionais: document.getElementById("adminRuleObservacoes").value.trim(),
  };
}

function fillAdministratorRuleForm(rule, index) {
  configAdministratorRuleIndex = index;
  setInputValue("adminRuleAdministradora", rule.administradora);
  setInputValue("adminRuleStatusProduto", rule.status_operacional || "Ativo");
  setInputValue("adminRuleDataProduto", rule.data_cadastro_produto);
  setInputValue("adminRuleResponsavelProduto", rule.responsavel_produto);
  setSelectBool("adminRuleSeguro", rule.seguro_obrigatorio);
  setInputValue("adminRuleIdadeMaxima", rule.idade_maxima);
  setInputValue("adminRuleLimiteRenda", rule.limite_sem_comprovacao_renda);
  setInputValue("adminRuleLimiteRendaTexto", rule.limite_sem_comprovacao_renda_texto);
  setInputValue("adminRuleLanceEmbutido", percentToInput(rule.percentual_lance_embutido));
  setInputValue("adminRuleTipoLance", rule.tipo_lance_embutido || "Credito");
  setSelectBool("adminRuleSaidaFiscal", rule.aceita_saida_fiscal);
  setInputValue("adminRuleTaxaAdm", percentToInput(rule.taxa_adm));
  setInputValue("adminRuleNegociacao", rule.possui_negociacao_taxa);
  setInputValue("adminRuleFundoReserva", percentToInput(rule.fundo_reserva));
  setInputValue("adminRuleAceitaAdesao", rule.aceita_adesao_clientes_texto);
  setSelectBool("adminRuleAceitaFgts", rule.aceita_fgts !== false);
  setSelectBool("adminRuleAceitaPJ", rule.aceita_pj !== false);
  setSelectBool("adminRuleComposicaoPJSocios", rule.permite_composicao_pj_socios !== false);
  setSelectBool("adminRuleCpfSocio", rule.permite_cpf_socio !== false);
  setInputValue("adminRuleComprometimentoPJ", percentToInput(rule.percentual_comprometimento_pj || DEFAULT_PJ_COMMITMENT_PERCENT));
  setInputValue("adminRuleComprometimentoCPF", percentToInput(rule.percentual_comprometimento_cpf || DEFAULT_CPF_COMMITMENT_PERCENT));
  setInputValue("adminRuleObservacoes", rule.observacoes_operacionais);
  document.getElementById("saveAdministratorRuleBtn").textContent = "Atualizar Administradora";
  document.getElementById("adminRuleAdministradora").focus();
}

async function saveAdministratorRule() {
  const rule = collectAdministratorRuleForm();
  if (!rule.administradora) {
    showToast("Informe o nome da administradora.", "warning");
    return;
  }
  const rules = [...(configState.data?.administradoras_regras || [])];
  if (configAdministratorRuleIndex === null) {
    rules.push(rule);
  } else {
    rules[configAdministratorRuleIndex] = rule;
  }
  await apiPut("/configuracoes", { administradoras_regras: rules });
  configState.data.administradoras_regras = rules;
  renderAdministratorRules(rules);
  clearAdministratorRuleForm();
  showToast("Plano da administradora salvo.", "success");
  addOperationalLog("Plano de administradora salvo");
}

async function removeAdministratorRule(index) {
  const rules = [...(configState.data?.administradoras_regras || [])];
  const removed = rules.splice(index, 1)[0];
  await apiPut("/configuracoes", { administradoras_regras: rules });
  configState.data.administradoras_regras = rules;
  renderAdministratorRules(rules);
  clearAdministratorRuleForm();
  showToast(`Plano removido: ${removed?.administradora || "administradora"}.`, "success");
  addOperationalLog("Plano de administradora removido");
}

function collectConfiguracoesPayload() {
  return {
    parametros_financeiros: {
      taxa_administracao_padrao: inputToPercent("configTaxaAdm"),
      fundo_reserva_padrao: inputToPercent("configFundoReserva"),
      percentual_lance_fixo_padrao: inputToPercent("configLanceFixo"),
      percentual_lance_moderado_padrao: inputToPercent("configLanceModerado"),
      percentual_lance_agressivo_padrao: inputToPercent("configLanceAgressivo"),
      prazo_maximo: Number(document.getElementById("configPrazoMaximo").value || 0),
      prazo_minimo: Number(document.getElementById("configPrazoMinimo").value || 0),
      indice_correcao_anual: document.getElementById("configIndiceCorrecao").value.trim(),
    },
    administradoras_regras: configState.data?.administradoras_regras || [],
    regras_negocio_feedbacks: collectBusinessRuleFeedbacks({ preserveExistingWhenBlank: true }),
  };
}

async function loadConfiguracoes() {
  setConfigState("loading");
  try {
    const data = await apiGet("/configuracoes");
    renderConfiguracoes(data);
    setConfigState("ready");
    addOperationalLog("Configuracoes carregadas");
  } catch (error) {
    setConfigState("error");
    addOperationalLog("Falha ao carregar configuracoes");
  }
}

async function saveConfiguracoes() {
  await apiPut("/configuracoes", collectConfiguracoesPayload());
  showToast("Configuracoes salvas.", "success");
  addOperationalLog("Configuracoes salvas");
  loadConfiguracoes();
}

async function saveConfigUsers(usuarios, message = "Usuarios atualizados.") {
  await apiPut("/configuracoes", { usuarios });
  configState.data.usuarios = usuarios;
  renderConfiguracoes(configState.data);
  showToast(message, "success");
  addOperationalLog(message);
}

function ensureConfigUserModal() {
  if (!configUserModal) {
    configUserModal = new bootstrap.Modal(document.getElementById("configUserModal"));
  }
}

function openConfigUserForm(mode, index = null) {
  ensureConfigUserModal();
  configUserMode = mode;
  configUserIndex = index;
  const user = mode === "edit" ? (configState.data?.usuarios || [])[index] : null;

  document.getElementById("configUserModalTitle").textContent = mode === "edit" ? "Editar Usuario" : "Novo Usuario";
  document.getElementById("configUserNome").value = user?.nome || "";
  document.getElementById("configUserEmail").value = user?.email || "";
  document.getElementById("configUserPerfil").value = user?.perfil || "";
  document.getElementById("configUserStatus").value = user?.status || "Ativo";
  configUserModal.show();
}

async function submitConfigUserForm() {
  const usuarios = [...(configState.data?.usuarios || [])];
  const payload = {
    nome: document.getElementById("configUserNome").value.trim(),
    email: document.getElementById("configUserEmail").value.trim(),
    perfil: document.getElementById("configUserPerfil").value.trim(),
    status: document.getElementById("configUserStatus").value,
    ultimo_acesso: configUserMode === "edit" ? (usuarios[configUserIndex]?.ultimo_acesso || "") : "",
  };

  if (!payload.nome || !payload.email || !payload.perfil) {
    showToast("Preencha nome, e-mail e perfil.", "warning");
    return;
  }

  if (configUserMode === "edit" && usuarios[configUserIndex]) {
    usuarios[configUserIndex] = { ...usuarios[configUserIndex], ...payload };
  } else {
    usuarios.push(payload);
  }
  await saveConfigUsers(usuarios, configUserMode === "edit" ? "Referencia de usuario atualizada." : "Referencia de usuario cadastrada.");
  configUserModal.hide();
}

async function syncGoogleSheets() {
  const result = await apiPost("/reload", {});
  showToast(`Google Sheets sincronizado: ${result.total} linhas.`, "success");
  addOperationalLog(`Google Sheets sincronizado: ${result.total} linha(s)`);
}

function clearSystemCache() {
  operationalLogs.length = 0;
  renderOperationalLogs();
  renderConfiguracoes(configState.data);
  showToast("Cache visual e logs da sessao limpos.", "success");
}

async function reindexSystemData() {
  mapState.page = 1;
  await loadMapaGrupos();
  showToast(`Dados reindexados: ${mapState.total} grupo(s).`, "success");
  addOperationalLog(`Dados reindexados: ${mapState.total} grupo(s)`);
}

async function validateSystemIntegrity() {
  if (!mapState.items.length) {
    await loadMapaGrupos();
  }
  const invalidGroups = mapState.items.filter((item) => !item.grupo_id || !item.grupo || !item.administradora);
  if (invalidGroups.length) {
    showToast(`Integridade com alerta: ${invalidGroups.length} grupo(s) incompleto(s) na pagina atual.`, "warning");
    addOperationalLog(`Validacao encontrou ${invalidGroups.length} grupo(s) incompleto(s)`);
    return;
  }
  showToast("Integridade validada na pagina atual de grupos.", "success");
  addOperationalLog("Integridade de dados validada");
}

async function restartSystemSync() {
  await syncGoogleSheets();
  await loadMapaGrupos();
  await loadConfiguracoes();
  showToast("Sincronizacao reiniciada.", "success");
  addOperationalLog("Sincronizacao reiniciada");
}

async function loadHealth() {
  const health = await apiGet("/health");
  document.getElementById("environmentLabel").textContent = health.environment;
  document.getElementById("systemVersionLabel").textContent = health.version;
  const clientVersion = document.querySelector('meta[name="crediclass-build"]')?.content;
  if (clientVersion && health.version && clientVersion !== health.version) {
    showToast(`Nova versão disponível (${health.version}). Recarregue a página.`, "warning");
  }
}

function assemblyFilters() {
  return {
    administrator: document.getElementById("assemblyAdministratorFilter")?.value || "",
    month: Number(document.getElementById("assemblyMonthFilter")?.value || 1),
  };
}

function assemblyMatches(item, filters) {
  return !filters.administrator || item.administrator === filters.administrator;
}

function assemblyTooltip(items, label = "Orientação") {
  const notes = (items || []).filter(Boolean);
  if (!notes.length) return "";
  return `
    <span class="assembly-tooltip" tabindex="0" aria-label="${escapeHtml(label)}">
      <span class="assembly-tooltip-trigger" aria-hidden="true">i</span>
      <span class="assembly-tooltip-panel" role="tooltip">
        <strong>${escapeHtml(label)}</strong>
        <span>${notes.map((item) => escapeHtml(item)).join("</span><span>")}</span>
      </span>
    </span>
  `;
}

function renderAssemblyEventGuidance(data) {
  (data.event_types || []).forEach((event) => {
    const heading = document.querySelector(`[data-assembly-event="${event.id}"]`);
    if (!heading || heading.querySelector(".assembly-tooltip")) return;
    const notes = [event.guidance, ...(event.details || [])];
    heading.insertAdjacentHTML("beforeend", assemblyTooltip(notes, event.label));
  });
}

function assemblyEventDateValue(event, monthNumber, metadata = {}) {
  if (event?.iso_date) {
    const parsed = new Date(`${event.iso_date}T00:00:00`);
    return Number.isNaN(parsed.getTime()) ? null : parsed;
  }
  const day = Number(event?.value);
  const month = Number(monthNumber);
  const referenceYear = Number(metadata?.reference_year || 2026);
  const nextCycleYear = Number(metadata?.next_cycle_year || referenceYear + 1);
  const year = month === 1 && referenceYear < nextCycleYear ? nextCycleYear : referenceYear;
  if (!day || !month || !year) return null;
  const parsed = new Date(year, month - 1, day);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function assemblyFormatDate(date) {
  return new Intl.DateTimeFormat("pt-BR").format(date);
}

function renderAssemblyMap() {
  const data = assemblyState.data;
  if (!data) return;
  const filters = assemblyFilters();
  const monthName = data.schedules[0]?.months.find((month) => month.number === filters.month)?.name || "Mês";
  const schedules = data.schedules
    .filter((item) => assemblyMatches(item, filters))
    .sort((left, right) => {
      const leftMonth = left.months.find((entry) => entry.number === filters.month);
      const rightMonth = right.months.find((entry) => entry.number === filters.month);
      const leftDueDate = Number((leftMonth?.events || []).find((event) => event.id === "vencimento_parcela")?.value ?? Number.POSITIVE_INFINITY);
      const rightDueDate = Number((rightMonth?.events || []).find((event) => event.id === "vencimento_parcela")?.value ?? Number.POSITIVE_INFINITY);
      return leftDueDate - rightDueDate || String(left.administrator || "").localeCompare(String(right.administrator || ""), "pt-BR");
    });
  const rules = data.rules.filter((item) => assemblyMatches(item, filters));

  document.getElementById("assemblyMonthTitle").textContent = `${monthName} de 2026`;
  document.getElementById("assemblyCalendarSubtitle").textContent = `${schedules.length} calendário(s) exibido(s)`;
  document.getElementById("assemblyDateRule").textContent = filters.month === 12 ? "Próximo ciclo: janeiro de 2027" : "Dias do mês de referência";
  document.getElementById("assemblyEmpty").classList.toggle("d-none", schedules.length > 0);

  document.getElementById("assemblyCalendarBody").innerHTML = schedules.map((item) => {
    const month = item.months.find((entry) => entry.number === filters.month);
    const values = (month?.events || []).map((event) => {
      const date = assemblyEventDateValue(event, month?.number, data.metadata);
      const isNextCycle = Boolean(event.iso_date?.startsWith("2027-"));
      const className = isNextCycle ? "assembly-next-cycle" : "";
      const text = date ? assemblyFormatDate(date) : String(event.display || event.value || "-");
      return `<td><span class="assembly-date ${className}">${escapeHtml(text)}</span></td>`;
    }).join("");
    const guidance = assemblyTooltip(item.guidance, `Orientações de ${item.administrator}`);
    return `<tr><th scope="row"><span class="assembly-administrator">${escapeHtml(item.administrator)}${guidance}</span></th>${values}</tr>`;
  }).join("");

  document.getElementById("assemblyRulesGrid").innerHTML = rules.length ? rules.map((rule) => `
    <article class="assembly-rule-card">
      <header><div><strong><span>${escapeHtml(rule.administrator)}</span>${assemblyTooltip(rule.guidance, `Orientações de ${rule.administrator}`)}</strong></div><span>Regra</span></header>
      <dl>${rule.parameters.map((parameter) => {
        const event = data.event_types.find((item) => item.id === parameter.id);
        return `<div><dt>${escapeHtml(parameter.label)}${assemblyTooltip([event?.guidance, ...(event?.details || [])], parameter.label)}</dt><dd>${escapeHtml(parameter.value)}</dd></div>`;
      }).join("")}</dl>
    </article>
  `).join("") : `<p class="assembly-state">Nenhuma regra corresponde aos filtros.</p>`;
}

function populateAssemblyFilters(data) {
  const administrators = [...new Set([...data.schedules, ...data.rules].map((item) => item.administrator).filter(Boolean))].sort((a, b) => a.localeCompare(b, "pt-BR"));
  document.getElementById("assemblyAdministratorFilter").innerHTML = `<option value="">Todas</option>${administrators.map((value) => `<option>${escapeHtml(value)}</option>`).join("")}`;
  document.getElementById("assemblyMonthFilter").innerHTML = data.schedules[0].months.map((month) => `<option value="${month.number}">${escapeHtml(month.name)}</option>`).join("");
}

function validateAssemblyPayload(data) {
  if (!data || !Array.isArray(data.schedules) || !Array.isArray(data.rules) || !data.schedules.length) {
    throw new Error("O calendário recebido está incompleto.");
  }
  return data;
}

function renderAssemblyLoadError(error) {
  const container = document.getElementById("assemblyError");
  const message = error?.message || "Não foi possível carregar o calendário.";
  container.innerHTML = `
    <strong>Não foi possível carregar o calendário.</strong>
    <span>${escapeHtml(message)}</span>
    <button class="btn btn-outline-secondary btn-sm" type="button" data-assembly-retry>Tentar novamente</button>
  `;
  container.classList.remove("d-none");
  container.querySelector("[data-assembly-retry]")?.addEventListener("click", () => loadAssemblyMap(true));
}

async function loadAssemblyMap(force = false) {
  if (force) {
    assemblyState.loaded = false;
    assemblyState.data = null;
    assemblyState.loadingPromise = null;
  }
  if (assemblyState.loaded) {
    renderAssemblyMap();
    return;
  }
  if (assemblyState.loadingPromise) return assemblyState.loadingPromise;
  document.getElementById("assemblyLoading").classList.remove("d-none");
  document.getElementById("assemblyError").classList.add("d-none");
  document.getElementById("assemblyContent").classList.add("d-none");
  assemblyState.loadingPromise = apiGet("/mapa-assembleia", { timeoutMs: 30000 });
  try {
    const data = validateAssemblyPayload(await assemblyState.loadingPromise);
    assemblyState.data = data;
    assemblyState.loaded = true;
    populateAssemblyFilters(data);
    renderAssemblyEventGuidance(data);
    document.getElementById("assemblyScheduleCount").textContent = data.schedules.length;
    document.getElementById("assemblyRuleCount").textContent = data.rules.length;
    document.getElementById("assemblyContent").classList.remove("d-none");
    renderAssemblyMap();
  } catch (error) {
    renderAssemblyLoadError(error);
  } finally {
    assemblyState.loadingPromise = null;
    document.getElementById("assemblyLoading").classList.add("d-none");
  }
}

document.querySelectorAll(".nav-item").forEach((item) => {
  item.addEventListener("click", () => activateScreen(item.dataset.screen));
});

document.querySelectorAll("[data-screen-jump]").forEach((button) => {
  button.addEventListener("click", () => button.dataset.screenJump === "grupos-selecionados" ? openSelectedGroupsWorkspace() : activateScreen(button.dataset.screenJump));
});

document.getElementById("primaryAction").addEventListener("click", () => {
  if (document.getElementById("screen-perfil").classList.contains("active")) {
    saveClientProfile();
    return;
  }
  if (document.getElementById("screen-mapa").classList.contains("active")) {
    openGroupForm("create");
    return;
  }
  if (document.getElementById("screen-configuracoes").classList.contains("active")) {
    saveConfiguracoes().catch(() => setConfigState("error"));
    return;
  }
});
document.getElementById("reloadMapDataBtn").addEventListener("click", reloadMapData);
document.getElementById("assemblyAdministratorFilter")?.addEventListener("change", renderAssemblyMap);
document.getElementById("assemblyMonthFilter")?.addEventListener("change", renderAssemblyMap);
document.getElementById("assemblyClearFilters")?.addEventListener("click", () => {
  document.getElementById("assemblyAdministratorFilter").value = "";
  document.getElementById("assemblyMonthFilter").value = "1";
  renderAssemblyMap();
});
document.getElementById("openDefasagemBtn")?.addEventListener("click", openDefasagemModal);
document.getElementById("defasagemFilter").addEventListener("change", renderDefasagemRows);
document.getElementById("defasagemTableBody").addEventListener("change", (event) => {
  const grupoId = event.target?.dataset?.defasagemCheck;
  if (!grupoId) return;
  saveDefasagemTask(grupoId, event.target.checked).catch(() => {
    event.target.checked = !event.target.checked;
    showToast("Nao foi possivel registrar o check da defasagem.", "danger");
  });
});
document.getElementById("defasagemTableBody").addEventListener("focusout", (event) => {
  const grupoId = event.target?.dataset?.defasagemNote;
  if (!grupoId) return;
  const checked = document.querySelector(`[data-defasagem-check="${CSS.escape(grupoId)}"]`)?.checked || false;
  saveDefasagemTask(grupoId, checked).catch(() => showToast("Nao foi possivel salvar a observacao da defasagem.", "danger"));
});

document.getElementById("groupFilters").addEventListener("submit", (event) => {
  event.preventDefault();
});

["filterAdministradora", "filterTipoBem", "filterStatus", "filterCreditoMinimo", "filterCreditoMaximo", "filterPrazoMinimo", "filterPrazoMaximo"].forEach((id) => {
  document.getElementById(id).addEventListener("change", () => {
    mapState.page = 1;
    loadMapaGrupos();
  });
});

document.getElementById("filterBusca").addEventListener("input", () => {
  clearTimeout(window.mapSearchTimer);
  window.mapSearchTimer = setTimeout(() => {
    mapState.page = 1;
    loadMapaGrupos();
  }, 300);
});

document.getElementById("groupsTableBody").addEventListener("mouseover", (event) => {
  const trigger = event.target.closest("[data-history-index]");
  if (trigger) showHistoryHoverModal(trigger);
});

document.getElementById("groupsTableBody").addEventListener("mouseout", (event) => {
  const trigger = event.target.closest("[data-history-index]");
  if (!trigger) return;
  const related = event.relatedTarget;
  if (related && (trigger.contains(related) || document.getElementById("historyHoverModal")?.contains(related))) return;
  scheduleHistoryHoverHide();
});

document.getElementById("groupsTableBody").addEventListener("focusin", (event) => {
  const trigger = event.target.closest("[data-history-index]");
  if (trigger) showHistoryHoverModal(trigger);
});

document.getElementById("groupsTableBody").addEventListener("focusout", (event) => {
  const trigger = event.target.closest("[data-history-index]");
  if (trigger) scheduleHistoryHoverHide();
});

["historyHoverModal", "motor360HistoryHoverModal"].forEach((modalId) => {
  const modal = document.getElementById(modalId);
  if (!modal) return;
  modal.addEventListener("mouseenter", cancelHistoryHoverHide);
  modal.addEventListener("mouseleave", () => scheduleHistoryHoverHide());
  modal.addEventListener("focusin", cancelHistoryHoverHide);
  modal.addEventListener("focusout", () => scheduleHistoryHoverHide());
});

document.getElementById("clearFiltersBtn").addEventListener("click", () => {
  document.getElementById("groupFilters").reset();
  mapState.lanceSortField = "";
  mapState.lanceSortOrder = "";
  document.querySelectorAll("[data-lance-sort]").forEach((select) => {
    select.value = "";
    select.classList.remove("active");
  });
  mapState.page = 1;
  loadMapaGrupos();
});

document.querySelectorAll("[data-lance-sort]").forEach((select) => {
  select.addEventListener("change", (event) => {
    const target = event.currentTarget;
    mapState.lanceSortField = target.value ? target.dataset.lanceSort : "";
    mapState.lanceSortOrder = target.value;
    document.querySelectorAll("[data-lance-sort]").forEach((otherSelect) => {
      if (otherSelect !== target) {
        otherSelect.value = "";
        otherSelect.classList.remove("active");
      }
    });
    target.classList.toggle("active", Boolean(target.value));
    mapState.page = 1;
    loadMapaGrupos();
  });
});

document.getElementById("pageSizeSelect").addEventListener("change", (event) => {
  mapState.pageSize = Number(event.target.value);
  mapState.page = 1;
  loadMapaGrupos();
});

document.getElementById("exportGroupsCsvBtn")?.addEventListener("click", exportGroupsCsv);

document.getElementById("groupFormHistoryYear").addEventListener("change", () => {
  syncGroupFormVisibleHistory();
  renderHistoryEditor("groupFormHistory", groupFormHistoryData);
});

const moneyInputIds = [
  "filterCreditoMinimo",
  "filterCreditoMaximo",
  "clientProfileCredito",
  "clientProfileLanceProprio",
  "clientProfileParcelaIdeal",
  "clientProfileParcelaLimite",
  "groupFormCreditoMinimo",
  "groupFormCreditoMaximo",
  "historyCreditoMinimo",
  "historyCreditoMaximo",
  "adminRuleLimiteRenda",
];

moneyInputIds.forEach((id) => {
  const input = document.getElementById(id);
  input?.addEventListener("input", () => formatMoneyInputElement(input));
  input?.addEventListener("blur", () => formatMoneyInputById(id));
});

document.addEventListener("input", (event) => {
  const input = event.target.closest("[data-money], [data-sheet-field-mask=\"money\"]");
  if (input) formatMoneyInputElement(input);
});

document.getElementById("groupFormModal").addEventListener("blur", (event) => {
  const sheetInput = event.target.closest("[data-sheet-field-header]");
  if (sheetInput && String(sheetInput.value || "").trim()) {
    if (sheetInput.dataset.sheetFieldMask) {
      sheetInput.value = formatSheetFieldInputValue(sheetInput.dataset.sheetFieldHeader, sheetInput.value);
    }
  }
  const historyInput = event.target.closest("[data-history-field]");
  if (historyInput && historyInput.dataset.historyField !== "qtd_contemplacoes" && String(historyInput.value || "").trim()) {
    historyInput.value = formatDecimalInputValue(historyInput.value, 2, 2);
  }
}, true);

[
  "clientProfileCredito",
  "clientProfileLanceProprio",
  "clientProfileParcelaIdeal",
  "clientProfileParcelaLimite",
].forEach((id) => {
  document.getElementById(id).addEventListener("input", updateClientProfileTotals);
});

["clientProfilePrazo", "clientProfileObjetivo", "clientProfileContemplacaoPerfil", "clientProfileFiltroLanceEmbutido", "clientProfileFiltroParcelaReduzida", "clientProfileTipoBem", "clientProfileEstadoBem"].forEach((id) => {
  document.getElementById(id).addEventListener("change", updateClientProfileTotals);
});

let motor360BidExplorerTimer = null;
function motor360FirstRequiredBid() {
  const result = investorState.result;
  const profile = result?.perfil_contemplacao;
  if (!result || !profile) return null;
  const profileAliases = { urgent: "super_aggressive", fast: "aggressive", moderate: "moderate", conservative: "conservative", long_term: "investor" };
  const profileIds = new Set([profile, profileAliases[profile]].filter(Boolean));
  const auditedEligible = (investorState.audit?.group_results || []).filter((item) => item.stage_results?.credito?.approved && item.stage_results?.prazo?.approved);
  const source = result.final_items?.length || result.items?.length
    ? (result.final_items || result.items)
    : auditedEligible;
  const required = source.map((item) => {
    const scenarios = item.cenarios || item.scenarios || [];
    const scenario = scenarios.find((entry) => entry.id === "without_embedded") || scenarios[0];
    const row = (scenario?.perfis_contemplacao || []).find((entry) => profileIds.has(entry.id));
    return row?.lance_ideal;
  }).filter((value) => value !== null && value !== undefined && value !== "" && Number.isFinite(Number(value)) && Number(value) > 0);
  return required.length ? Math.min(...required.map(Number)) : null;
}
function syncMotor360BidExplorer() {
  const range = document.getElementById("motor360BidRange");
  const value = document.getElementById("motor360BidValue");
  const declared = document.getElementById("motor360DeclaredBid");
  const marker = document.getElementById("motor360FirstMatchMarker");
  if (!range || !value || !declared) return;
  const totals = updateClientProfileTotals();
  const declaredBid = Number(totals.lance || 0);
  const desiredCredit = toNumber(document.getElementById("clientProfileCredito")?.value) || 0;
  if (
    (investorState.lastDeclaredBid !== null && investorState.lastDeclaredBid !== declaredBid)
    || (investorState.lastDesiredCredit !== null && investorState.lastDesiredCredit !== desiredCredit)
  ) {
    investorState.simulatedBid = null;
  }
  investorState.lastDeclaredBid = declaredBid;
  investorState.lastDesiredCredit = desiredCredit;
  // The slider scale represents the requested credit. The client's current
  // bid remains the initial cursor position, while the operator may explore
  // the full 0..100% credit range dynamically for the selected profile.
  const max = Math.max(0, Math.ceil(desiredCredit / 1000) * 1000);
  range.max = String(max);
  const currentBid = investorState.simulatedBid == null ? declaredBid : Number(investorState.simulatedBid);
  const boundedBid = Math.max(0, Math.min(max, Number.isFinite(currentBid) ? currentBid : declaredBid));
  if (investorState.simulatedBid == null || currentBid !== boundedBid) investorState.simulatedBid = investorState.simulatedBid == null ? null : boundedBid;
  range.value = String(boundedBid);
  const simulatedBid = boundedBid;
  const bidPercent = desiredCredit > 0 ? simulatedBid / desiredCredit : null;
  const declaredPercent = desiredCredit > 0 ? declaredBid / desiredCredit : null;
  value.textContent = `${formatMoney(simulatedBid)} · ${bidPercent == null ? "-" : formatPercent(bidPercent)}`;
  declared.textContent = `${formatMoney(declaredBid)} · ${declaredPercent == null ? "-" : formatPercent(declaredPercent)}`;
  const firstRequired = motor360FirstRequiredBid();
  if (marker && firstRequired != null) {
    const position = max > 0 ? Math.max(0, Math.min(100, (firstRequired / max) * 100)) : 0;
    marker.style.left = `${position}%`;
    marker.hidden = false;
    marker.title = `Primeiro grupo compatível a partir de ${formatMoney(firstRequired)}`;
    const firstRequiredPercent = desiredCredit > 0 ? firstRequired / desiredCredit : null;
    marker.querySelector("span")?.replaceChildren(document.createTextNode(`Primeiro grupo: ${formatMoney(firstRequired)} · ${firstRequiredPercent == null ? "-" : formatPercent(firstRequiredPercent)}`));
  } else if (marker) marker.hidden = true;
}
document.getElementById("motor360BidRange")?.addEventListener("input", (event) => {
  investorState.simulatedBid = Number(event.target.value || 0);
  syncMotor360BidExplorer();
  clearTimeout(motor360BidExplorerTimer);
  motor360BidExplorerTimer = setTimeout(() => loadInvestorAnalysis(), 450);
});
document.getElementById("clientProfileLanceProprio")?.addEventListener("input", () => {
  investorState.simulatedBid = null;
  syncMotor360BidExplorer();
});
syncMotor360BidExplorer();

document.getElementById("clientProfileTipoContratacao").addEventListener("change", (event) => {
  const current = collectClientTitularesFromForm();
  current.tipo_contratacao = event.target.value;
  renderClientProfileTitulares(current);
  updateClientProfileTotals();
});

document.getElementById("clientProfileForm").addEventListener("input", (event) => {
  invalidateInvestorAnalysisForProfileChange();
  syncMotor360BidExplorer();
  if (!event.target.matches("[data-holder-field]")) return;
  updateClientProfileTotals();
});
document.getElementById("loadPipeRunPreviewBtn")?.addEventListener("click", loadPipeRunPreview);
document.getElementById("preparePipeRunPlanBtn")?.addEventListener("click", preparePipeRunPlan);
document.getElementById("executePipeRunBtn")?.addEventListener("click", async () => {
  if (!window.confirm("Confirmar execução controlada para a oportunidade 63416847?")) return;
  const response = await fetch("/api/piperun/63416847/sync?confirm=true", { method: "POST", credentials: "same-origin" });
  const payload = await response.json();
  showToast(payload.message || payload.error, payload.success ? "success" : "warning");
});

document.getElementById("clientProfileForm").addEventListener("change", () => {
  invalidateInvestorAnalysisForProfileChange();
  updateClientProfileTotals();
});

document.getElementById("clientProfileForm").addEventListener("blur", (event) => {
  if (event.target.matches("[data-holder-field][data-money]")) {
    event.target.value = formatMoneyInputValue(event.target.value);
    updateClientProfileTotals();
  }
}, true);

document.querySelector(".user-card")?.addEventListener("click", (event) => {
  if (event.target.closest("#logoutBtn")) return;
  const sidebar = document.querySelector(".sidebar");
  sidebar?.classList.toggle("user-menu-open");
});

document.querySelector(".preliminary-toggle")?.addEventListener("click", (event) => {
  const button = event.currentTarget;
  const section = button.closest(".client-preliminary-section");
  const expanded = section.classList.toggle("is-collapsed") === false;
  button.setAttribute("aria-expanded", String(expanded));
  const hint = button.querySelector("small");
  if (hint) hint.textContent = expanded ? "Ocultar análise" : "Exibir análise";
});

document.getElementById("saveClientProfileBtn").addEventListener("click", () => saveClientProfile());
document.getElementById("clearClientProfileBtn").addEventListener("click", resetClientProfile);
document.getElementById("importClientProfileCrmBtn").addEventListener("click", () => {
  importClientProfileFromCrm().catch(() => {
    document.getElementById("clientProfileCrmStatus").textContent = "Falha ao consultar o CRM.";
    showToast("Nao foi possivel importar os dados do CRM.", "danger");
  });
});
document.getElementById("advanceClientProfileBtn").addEventListener("click", advanceClientProfile);
renderInvestorPreferenceOptions();
updateInvestorPreferenceSummary();
document.getElementById("investorPreferencesOptions")?.addEventListener("change", syncInvestorPreferencesFromInputs);
["investorFilterWithEmbedded", "investorFilterWithoutEmbedded"].forEach((id) => {
  document.getElementById(id)?.addEventListener("change", () => {
    const withEmbedded = document.getElementById("investorFilterWithEmbedded")?.checked === true;
    const withoutEmbedded = document.getElementById("investorFilterWithoutEmbedded")?.checked === true;
    investorState.selectedGroupScenario = withEmbedded && withoutEmbedded ? "all" : withEmbedded ? "with_embedded" : withoutEmbedded ? "without_embedded" : "per_group";
    if (investorState.result) renderInvestorAnalysis(investorState.result);
  });
});
document.getElementById("investorAdministratorFilter")?.addEventListener("change", (event) => {
  const nextAdministrator = String(event.target.value || "");
  if (nextAdministrator === investorState.administrator) return;
  const hadSelectedGroups = investorState.selectedGroupIds.size > 0;
  clearMotor360GroupSelection();
  investorState.administrator = nextAdministrator;
  persistMotor360Selection();
  updateInvestorPreferenceSummary();
  if (hadSelectedGroups) showToast("A seleção anterior foi limpa para manter apenas uma administradora na composição.", "warning");
  if (investorState.result) renderInvestorAnalysis(investorState.result);
  renderSelectedGroupsScreen();
});
document.getElementById("recalculateInvestorAnalysisBtn")?.addEventListener("click", () => {
  investorState.result = null;
  investorState.analysisKey = null;
  try { sessionStorage.removeItem(INVESTOR_ANALYSIS_CACHE_KEY); } catch (_) { /* sem cache */ }
  loadInvestorAnalysis();
});
document.getElementById("clearInvestorPreferencesBtn")?.addEventListener("click", () => {
  investorState.preferences = [];
  renderInvestorPreferenceOptions();
  updateInvestorPreferenceSummary();
  if (investorState.result) renderInvestorAnalysis(investorState.result);
});

document.getElementById("prevPageBtn").addEventListener("click", () => {
  if (mapState.page > 1) {
    mapState.page -= 1;
    loadMapaGrupos();
  }
});

document.getElementById("nextPageBtn").addEventListener("click", () => {
  const totalPages = Math.max(1, Math.ceil(mapState.total / mapState.pageSize));
  if (mapState.page < totalPages) {
    mapState.page += 1;
    loadMapaGrupos();
  }
});

document.getElementById("groupsTableBody").addEventListener("click", (event) => {
  const button = event.target.closest("[data-map-action]");
  if (!button) return;
  if (button.dataset.mapAction === "visualizar") {
    openGroupDetails(button.dataset.groupId);
    return;
  }
  if (button.dataset.mapAction === "editar") {
    openGroupForm("edit", button.dataset.groupId);
    return;
  }
  if (button.dataset.mapAction === "duplicar") {
    openGroupForm("duplicate", button.dataset.groupId);
    return;
  }
  if (button.dataset.mapAction === "excluir") {
    if (!window.confirm("Marcar este grupo como Excluido na Google Sheets?")) return;
    deleteGroup(button.dataset.groupId).catch(() => showToast("Nao foi possivel excluir o grupo.", "danger"));
  }
});

document.getElementById("groupCrudForm").addEventListener("submit", (event) => {
  event.preventDefault();
  saveGroupForm().catch((error) => {
    setGroupFormHistoryState("error", error.message || "Nao foi possivel salvar o grupo.");
    showToast("Nao foi possivel salvar o grupo.", "danger");
  });
});

document.getElementById("historyUpdateForm").addEventListener("submit", (event) => {
  event.preventDefault();
  saveHistoryUpdate().catch((error) => setHistoryUpdateState("error", error.message || "Nao foi possivel atualizar o historico."));
});

document.querySelector('[data-bs-target="#detailsHistory"]').addEventListener("shown.bs.tab", () => detailsChart?.resize());

document.getElementById("downloadConfigBackupBtn").addEventListener("click", downloadConfigBackup);
document.getElementById("saveBusinessRulesFeedbackBtn").addEventListener("click", () => {
  saveBusinessRuleFeedbacks().catch(() => setConfigState("error"));
});

document.getElementById("newAdministratorRuleBtn").addEventListener("click", clearAdministratorRuleForm);
document.getElementById("cancelAdministratorRuleBtn").addEventListener("click", clearAdministratorRuleForm);
document.getElementById("saveAdministratorRuleBtn").addEventListener("click", () => {
  saveAdministratorRule().catch(() => setConfigState("error"));
});
document.getElementById("administratorRulesBody").addEventListener("click", (event) => {
  const button = event.target.closest("[data-admin-rule-action]");
  if (!button) return;
  const index = Number(button.dataset.adminRuleIndex);
  const rule = (configState.data?.administradoras_regras || [])[index];
  if (!rule) return;
  if (button.dataset.adminRuleAction === "editar") {
    fillAdministratorRuleForm(rule, index);
    return;
  }
  if (button.dataset.adminRuleAction === "remover") {
    if (!window.confirm("Remover este plano de administradora?")) return;
    removeAdministratorRule(index).catch(() => setConfigState("error"));
  }
});

document.getElementById("newConfigUserBtn").addEventListener("click", () => openConfigUserForm("create"));

document.getElementById("configUserForm").addEventListener("submit", (event) => {
  event.preventDefault();
  submitConfigUserForm().catch(() => setConfigState("error"));
});

document.getElementById("configUsersBody").addEventListener("click", (event) => {
  const button = event.target.closest("[data-config-user-action]");
  if (!button) return;

  const index = Number(button.dataset.configUserIndex);
  const usuarios = [...(configState.data?.usuarios || [])];
  const user = usuarios[index];
  if (!user) return;

  if (button.dataset.configUserAction === "editar") {
    openConfigUserForm("edit", index);
    return;
  }

  if (button.dataset.configUserAction === "status") {
    usuarios[index] = { ...user, status: button.dataset.nextStatus };
    saveConfigUsers(usuarios, `Usuario ${button.dataset.nextStatus.toLowerCase()}.`).catch(() => setConfigState("error"));
    return;
  }

  if (button.dataset.configUserAction === "remover") {
    if (!window.confirm("Remover esta referencia operacional?")) return;
    usuarios.splice(index, 1);
    saveConfigUsers(usuarios, "Referencia de usuario removida.").catch(() => setConfigState("error"));
  }
});

document.getElementById("clearSystemCacheBtn").addEventListener("click", clearSystemCache);

document.getElementById("clearMotor360ExecutionLogsBtn")?.addEventListener("click", () => {
  motor360ExecutionLogs.length = 0;
  renderMotor360ExecutionLogs();
});
document.getElementById("closeSelectedGroupsWorkspace")?.addEventListener("click", closeSelectedGroupsWorkspace);
document.getElementById("selectedGroupsWorkspaceStudy")?.addEventListener("click", () => {
  closeSelectedGroupsWorkspace();
  activateScreen("estudo");
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !document.getElementById("selectedGroupsWorkspace")?.classList.contains("d-none")) closeSelectedGroupsWorkspace();
});
renderMotor360FloatingSelectionSummaryIntoFold();

document.getElementById("reindexSystemBtn").addEventListener("click", () => {
  reindexSystemData().catch(() => showToast("Nao foi possivel reindexar os dados.", "danger"));
});

document.getElementById("validateSystemBtn").addEventListener("click", () => {
  validateSystemIntegrity().catch(() => showToast("Nao foi possivel validar a integridade.", "danger"));
});

document.getElementById("restartSyncBtn").addEventListener("click", () => {
  restartSystemSync().catch(() => showToast("Nao foi possivel reiniciar a sincronizacao.", "danger"));
});

document.getElementById("loginForm").addEventListener("submit", submitLogin);
document.getElementById("logoutBtn").addEventListener("click", logout);
bootApp().catch(() => showLogin("Nao foi possivel validar a sessao."));

