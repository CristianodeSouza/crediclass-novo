const screens = {
  mapa: {
    letter: "A) MAPA DE GRUPOS",
    title: "Mapa de Grupos",
    subtitle: "Lista e manutenÃ§Ã£o da base de grupos",
    action: "Novo Grupo",
  },
  perfil: {
    letter: "B) PERFIL DO CLIENTE",
    title: "Perfil do Cliente",
    subtitle: "Entrevista, capacidade financeira e necessidade de crÃ©dito",
    action: "Salvar Perfil",
  },
  viabilidade: {
    letter: "C) MOTOR INTELIGENTE DE SELEÃ‡ÃƒO",
    title: "Motor Inteligente de SeleÃ§Ã£o",
    subtitle: "",
    action: "",
  },
  administradoras: {
    letter: "C) MOTOR INTELIGENTE DE SELEÃ‡ÃƒO",
    title: "Motor Inteligente de SeleÃ§Ã£o",
    subtitle: "ParÃ¢metros por administradora integrados Ã  seleÃ§Ã£o de grupos",
    action: "Salvar ParÃ¢metros",
  },
  estudo: {
    letter: "E) ESTUDO FINANCEIRO",
    title: "Estudo Financeiro",
    subtitle: "GeraÃ§Ã£o do estudo financeiro detalhado",
    action: "Salvar Estudo",
  },
  historico: {
    letter: "F) HISTÃ“RICO DE ESTUDOS",
    title: "HistÃ³rico de Estudos",
    subtitle: "Consulta e gestÃ£o dos estudos financeiros gerados",
    action: "Buscar Estudos",
  },
  configuracoes: {
    letter: "G) CONFIGURAÃ‡Ã•ES",
    title: "ConfiguraÃ§Ãµes",
    subtitle: "ConfiguraÃ§Ãµes do sistema e preferÃªncias",
    action: "Salvar ConfiguraÃ§Ãµes",
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

const historyState = {
  items: [],
};

const defasagemState = {
  report: null,
  modal: null,
};

const configState = {
  data: null,
};

const operationalLogs = [];
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
const DEFAULT_PJ_COMMITMENT_PERCENT = 0.3;
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
  {
    id: "estudo-financeiro",
    etapa: "5. Estudo Financeiro",
    regras: [
      "O estudo financeiro deve nascer de um cenario aprovado e herdar exatamente seus calculos.",
      "O historico salva a composicao completa: administradora, cartas, grupos, credito contratado, credito liquido, lance, parcela, alertas e score.",
      "O frontend exibe o calculo retornado pelo backend; as formulas financeiras ficam centralizadas no backend.",
    ],
  },
];
const studyOperatorFields = [
  ["observacoes_comerciais", "Observacoes comerciais", "studyFieldObservacoes"],
  ["comentario_cliente", "Comentario para o cliente", "studyFieldComentario"],
  ["beneficios_personalizados", "Beneficios personalizados", "studyFieldBeneficios"],
  ["condicoes_especiais", "Condicoes especiais", "studyFieldCondicoes"],
];

let detailsModal = null;
let detailsChart = null;
let studyChart = null;
let historyStrategyChart = null;
let historyEvolutionChart = null;
let currentStudy = null;
let groupFormModal = null;
let groupFormMode = "create";
let groupFormId = null;
let groupFormHistoryData = {};
let groupFormOriginalHistoryData = {};
let groupFormSheetFields = {};
let currentDetailsGroupId = null;
let studyDetailsModal = null;
let currentStudyStrategies = [];
let currentStudyStrategyTab = "";
let configUserModal = null;
let configUserMode = "create";
let configUserIndex = null;
let configAdministratorRuleIndex = null;
let scenarioAnalysisRequestId = 0;

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
  loadHealth().catch(() => {
    document.getElementById("environmentLabel").textContent = "indisponivel";
  });
  loadMapaGrupos();
  loadClientProfile();
  ensureClientProfileHoldersRendered();
  updateViabilityTotals();
  openSharedStudyFromUrl().catch(() => showToast("Nao foi possivel abrir o estudo compartilhado.", "danger"));
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

  document.querySelectorAll(".nav-item").forEach((item) => {
    item.classList.toggle("active", item.dataset.screen === screenName);
  });

  document.querySelectorAll(".screen-panel").forEach((panel) => {
    panel.classList.toggle("active", panel.id === `screen-${screenName}`);
  });

  document.getElementById("screenLetter").textContent = meta.letter;
  document.getElementById("screenTitle").textContent = meta.title;
  document.getElementById("screenSubtitle").textContent = meta.subtitle;
  const primaryAction = document.getElementById("primaryAction");
  primaryAction.textContent = meta.action;
  primaryAction.classList.toggle("d-none", screenName === "viabilidade");
  document.getElementById("reloadMapDataBtn").classList.toggle("d-none", screenName !== "mapa");

  if (screenName === "historico") {
    loadHistoryStudies();
  }
  if (screenName === "viabilidade") loadConfiguracoes();
  if (screenName === "viabilidade") loadScenarioAnalysis();
  if (screenName === "configuracoes") {
    loadConfiguracoes();
  }
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

function exportStudiesCsv() {
  if (!historyState.items.length) {
    showToast("Busque estudos antes de exportar.", "warning");
    return;
  }
  const rows = [
    ["ID Estudo", "Data/Hora", "Cliente", "Administradora", "Grupo", "Credito", "Estrategia", "Status", "Operador"],
    ...historyState.items.map((item) => {
      const cliente = item.cliente || {};
      const grupo = item.grupo || {};
      const financeiro = item.financeiro || {};
      return [
        item.estudo_id,
        item.criado_em,
        cliente.nome,
        grupo.administradora,
        grupo.grupo || item.grupo_id,
        cliente.credito_desejado || financeiro.credito,
        item.estrategia,
        item.status,
        item.operador,
      ];
    }),
  ];
  downloadCsv(`crediclass-estudos-${new Date().toISOString().slice(0, 10)}.csv`, rows);
  showToast("CSV de estudos gerado.", "success");
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
  const modal = document.getElementById("historyHoverModal");
  if (!item || !modal) return;
  modal.innerHTML = `
    <div class="history-hover-title">
      <strong>Historico dos ultimos 12 meses</strong>
      <span>${escapeHtml(item.administradora || "-")} - Grupo ${escapeHtml(item.grupo || item.grupo_id || "-")}</span>
    </div>
    <table>
      <thead>
        <tr><th>Mes</th><th>Maior Lance</th><th>Menor Lance</th><th>Qtd</th></tr>
      </thead>
      <tbody>${renderHistoryHoverRows(item.historico_12_meses || [])}</tbody>
    </table>
  `;
  modal.setAttribute("aria-hidden", "false");
  positionHistoryHoverModal(modal, trigger);
}

function hideHistoryHoverModal() {
  const modal = document.getElementById("historyHoverModal");
  if (!modal) return;
  modal.classList.add("d-none");
  modal.setAttribute("aria-hidden", "true");
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

const SMART_ENGINE_ITAU_DEFAULTS = {
  administradora: "ITAU",
  tipo_bem_filtro: "Imóvel / Automóvel",
  indexador: "INCC, Fixo 3% e 5%",
  prazo_remanescente: "46 meses",
  prazo_inicial: "-",
  primeira_assembleia: "-",
  assembleias: "Não",
  modalidades_lance: "Fixo e Livre",
  calculo_embutido: "Sobre o Crédito",
  limite_parcela: "Não",
  taxa_adm_ano: 0.0417,
  fundo_reserva_ano: 0.0078,
  taxa_adm: 0.16,
  fundo_reserva: 0.03,
  percentual_lance_embutido: 0.30,
  tipo_lance_embutido: "Credito",
  aceita_fgts: true,
};

function smartEngineField(id, value) {
  const target = document.querySelector(`[data-engine-field="${id}"]`);
  if (target) target.textContent = value;
}

function smartEngineGenericField(id, value) {
  const target = document.querySelector(`[data-generic-filter="${id}"]`);
  if (target) target.textContent = value;
}

function formatSmartEngineMoney(value) {
  if (!Number.isFinite(Number(value))) return "-";
  return formatMoney(Number(value));
}

function formatSmartEngineMonths(value) {
  if (!Number.isFinite(Number(value))) return "-";
  return String(Math.max(0, Math.round(Number(value))));
}

function findSmartEngineAdministratorRule(administradora) {
  const normalized = normalizeText(administradora);
  return (configState.data?.administradoras_regras || []).find((rule) => (
    normalizeText(rule.administradora) === normalized
  )) || null;
}

function smartEngineItauRule() {
  const rule = findSmartEngineAdministratorRule("ITAU") || {};
  return {
    ...SMART_ENGINE_ITAU_DEFAULTS,
    ...rule,
    taxa_adm: rulePercentValue(rule, "taxa_adm") || SMART_ENGINE_ITAU_DEFAULTS.taxa_adm,
    fundo_reserva: rulePercentValue(rule, "fundo_reserva") || SMART_ENGINE_ITAU_DEFAULTS.fundo_reserva,
    percentual_lance_embutido: rulePercentValue(rule, "percentual_lance_embutido") || SMART_ENGINE_ITAU_DEFAULTS.percentual_lance_embutido,
    aceita_fgts: administratorRuleBoolean(rule, "aceita_fgts", SMART_ENGINE_ITAU_DEFAULTS.aceita_fgts),
  };
}

function calculateSmartEngineScenario(profile, rule, withEmbedded) {
  const creditoDesejado = Number(profile.credito_desejado || 0);
  const parcelaDesejada = Number(profile.parcela_desejada || profile.parcela_ideal || 0);
  // Antes era Number(profile.renda_total || 0) * 0.30; agora respeita o limite informado no perfil.
  const parcelaLimiteRenda = Number(profile.parcela_limite || profile.parcela_ideal || profile.parcela_desejada || 0);
  const recursoProprio = Number(profile.lance_proprio || 0);
  const fgts = rule.aceita_fgts ? Number(profile.fgts || 0) : 0;
  const embeddedPercent = withEmbedded ? Number(rule.percentual_lance_embutido || 0) : 0;
  const creditoContratado = embeddedPercent > 0 && embeddedPercent < 1
    ? creditoDesejado / (1 - embeddedPercent)
    : creditoDesejado;
  const taxaAdm = creditoContratado * Number(rule.taxa_adm || 0);
  const fundoReserva = withEmbedded
    ? creditoDesejado * Number(rule.fundo_reserva || 0)
    : creditoContratado * Number(rule.fundo_reserva || 0);
  const saldoDevedor = creditoContratado + taxaAdm + fundoReserva;
  const valorEmbutido = creditoContratado * embeddedPercent;
  const lanceTotal = recursoProprio + fgts + valorEmbutido;
  const saldoAposLance = saldoDevedor - lanceTotal;
  return {
    creditoContratado,
    taxaAdm,
    fundoReserva,
    saldoDevedor,
    percentualLance: creditoContratado > 0 ? lanceTotal / creditoContratado : 0,
    lanceTotal,
    recursoProprio,
    fgts,
    valorEmbutido,
    prazoInicialDesejada: parcelaDesejada > 0 ? saldoDevedor / parcelaDesejada : null,
    prazoInicialLimiteRenda: parcelaLimiteRenda > 0 ? saldoDevedor / parcelaLimiteRenda : null,
    prazoAposLanceDesejada: parcelaDesejada > 0 ? saldoAposLance / parcelaDesejada : null,
    prazoAposLanceLimiteRenda: parcelaLimiteRenda > 0 ? saldoAposLance / parcelaLimiteRenda : null,
  };
}

function renderSmartEngine() {
  if (!document.querySelector("[data-engine-field]")) return;
  const profile = collectClientProfile();
  const rule = smartEngineItauRule();
  const semEmbutido = calculateSmartEngineScenario(profile, rule, false);
  const comEmbutido = calculateSmartEngineScenario(profile, rule, true);
  const values = {
    "itau-a-sem": formatSmartEngineMoney(semEmbutido.creditoContratado),
    "itau-a-com": formatSmartEngineMoney(comEmbutido.creditoContratado),
    "itau-a-taxa-sem": formatSmartEngineMoney(semEmbutido.taxaAdm),
    "itau-a-taxa-com": formatSmartEngineMoney(comEmbutido.taxaAdm),
    "itau-a-fundo-sem": formatSmartEngineMoney(semEmbutido.fundoReserva),
    "itau-a-fundo-com": formatSmartEngineMoney(comEmbutido.fundoReserva),
    "itau-a-saldo-sem": formatSmartEngineMoney(semEmbutido.saldoDevedor),
    "itau-a-saldo-com": formatSmartEngineMoney(comEmbutido.saldoDevedor),
    "itau-b-sem": formatPercent(semEmbutido.percentualLance),
    "itau-b-com": formatPercent(comEmbutido.percentualLance),
    "itau-b-total-sem": formatSmartEngineMoney(semEmbutido.lanceTotal),
    "itau-b-total-com": formatSmartEngineMoney(comEmbutido.lanceTotal),
    "itau-b-rp-sem": formatSmartEngineMoney(semEmbutido.recursoProprio),
    "itau-b-rp-com": formatSmartEngineMoney(comEmbutido.recursoProprio),
    "itau-b-fgts-sem": formatSmartEngineMoney(semEmbutido.fgts),
    "itau-b-fgts-com": formatSmartEngineMoney(comEmbutido.fgts),
    "itau-b-embutido-sem": formatSmartEngineMoney(semEmbutido.valorEmbutido),
    "itau-b-embutido-com": formatSmartEngineMoney(comEmbutido.valorEmbutido),
    "itau-c-sem": "Se - Investidor",
    "itau-c-com": "Se - Investidor",
    "itau-c-desejada-sem": formatSmartEngineMonths(semEmbutido.prazoInicialDesejada),
    "itau-c-desejada-com": formatSmartEngineMonths(comEmbutido.prazoInicialDesejada),
    "itau-c-renda-sem": formatSmartEngineMonths(semEmbutido.prazoInicialLimiteRenda),
    "itau-c-renda-com": formatSmartEngineMonths(comEmbutido.prazoInicialLimiteRenda),
    "itau-d-sem": "Se - Contemplação",
    "itau-d-com": "Se - Contemplação",
    "itau-d-desejada-sem": formatSmartEngineMonths(semEmbutido.prazoAposLanceDesejada),
    "itau-d-desejada-com": formatSmartEngineMonths(comEmbutido.prazoAposLanceDesejada),
    "itau-d-renda-sem": formatSmartEngineMonths(semEmbutido.prazoAposLanceLimiteRenda),
    "itau-d-renda-com": formatSmartEngineMonths(comEmbutido.prazoAposLanceLimiteRenda),
  };
  Object.entries(values).forEach(([id, value]) => smartEngineField(id, value));
  const genericValues = {
    tipo_bem: rule.tipo_bem_filtro,
    indexador: rule.indexador,
    prazo_remanescente: rule.prazo_remanescente,
    prazo_inicial: rule.prazo_inicial,
    primeira_assembleia: rule.primeira_assembleia,
    taxa_adm: formatPercent(rule.taxa_adm),
    taxa_adm_ano: formatPercent(rule.taxa_adm_ano),
    fundo_reserva: formatPercent(rule.fundo_reserva),
    fundo_reserva_ano: formatPercent(rule.fundo_reserva_ano),
    assembleias: rule.assembleias,
    lance_embutido: formatPercent(rule.percentual_lance_embutido),
    modalidades_lance: rule.modalidades_lance,
    calculo_embutido: rule.calculo_embutido,
    limite_parcela: rule.limite_parcela,
  };
  Object.entries(genericValues).forEach(([id, value]) => smartEngineGenericField(id, value));
}

function setScenarioAnalysisState(state) {
  const loading = document.getElementById("scenarioAnalysisLoading");
  const error = document.getElementById("scenarioAnalysisError");
  const empty = document.getElementById("scenarioAnalysisEmpty");
  const results = document.getElementById("scenarioAnalysisResults");
  if (!loading || !error || !empty || !results) return;
  loading.classList.toggle("d-none", state !== "loading");
  error.classList.toggle("d-none", state !== "error");
  empty.classList.toggle("d-none", state !== "empty");
  results.classList.toggle("d-none", state !== "ready");
}

function renderScenarioAnalysis(result) {
  const status = document.getElementById("scenarioAnalysisStatus");
  const summary = document.getElementById("scenarioAnalysisSummary");
  const results = document.getElementById("scenarioAnalysisResults");
  if (!status || !summary || !results) return;

  const summaryItems = [
    ["Grupos na base", result.total_grupos_base ?? result.total_grupos_analisados ?? 0],
    ["Elegíveis", result.total_grupos_elegiveis ?? 0],
    ["Após filtro do objetivo", result.total_grupos_pos_filtro_1 ?? 0],
    ["Cenários montados", result.total_cenarios ?? 0],
    ["Cenários viáveis", result.total_cenarios_viaveis ?? 0],
  ];
  summary.innerHTML = summaryItems.map(([label, value]) => `
    <div class="smart-engine-summary-item"><span>${escapeHtml(label)}</span><strong>${escapeHtml(String(value))}</strong></div>
  `).join("");

  const scenarios = Array.isArray(result.cenarios) ? result.cenarios.slice(0, 10) : [];
  if (!scenarios.length) {
    status.textContent = "Nenhum cenário compatível";
    results.innerHTML = `<div class="table-state">Nenhum grupo atendeu aos filtros financeiros e de objetivo.</div>`;
    setScenarioAnalysisState("ready");
    return;
  }

  status.textContent = `${scenarios.length} cenário(s) exibido(s)`;
  results.innerHTML = scenarios.map((scenario, index) => {
    const cards = Array.isArray(scenario.cartas) ? scenario.cartas : [];
    const groupNames = cards.map((card) => `${card.administradora || "-"} / ${card.grupo || "-"}`).join(", ") || "-";
    const statusLabel = scenario.status === "viavel" ? "Viável" : scenario.status === "viavel_com_alertas" ? "Viável com alertas" : "Inviável";
    const statusClass = scenario.status === "inviavel" ? "scenario-status-error" : "scenario-status-ok";
    return `
      <article class="smart-engine-scenario-row">
        <div class="smart-engine-scenario-heading">
          <strong>#${index + 1} · ${escapeHtml(groupNames)}</strong>
          <span class="${statusClass}">${escapeHtml(statusLabel)}</span>
        </div>
        <div class="smart-engine-scenario-metrics">
          <span><small>Crédito líquido</small><b>${formatMoney(scenario.credito_liquido_total)}</b></span>
          <span><small>Crédito contratado</small><b>${formatMoney(scenario.credito_contratado_total)}</b></span>
          <span><small>Parcela total</small><b>${formatMoney(scenario.parcela_total)}</b></span>
          <span><small>Lance total</small><b>${formatMoney(scenario.lance_total)}</b></span>
          <span><small>Prazo mínimo</small><b>${escapeHtml(String(cards.map((card) => card.prazo_minimo).filter(Number.isFinite).map((value) => Math.ceil(value)).join(" / ") || "-"))}</b></span>
          <span><small>Score</small><b>${formatPercent((Number(scenario.score_cenario) || 0) / 100)}</b></span>
        </div>
        ${scenario.alertas?.length ? `<p class="smart-engine-scenario-alert">Alertas: ${escapeHtml(scenario.alertas.join(", "))}</p>` : ""}
      </article>
    `;
  }).join("");
  setScenarioAnalysisState("ready");
}

async function loadScenarioAnalysis() {
  const status = document.getElementById("scenarioAnalysisStatus");
  if (!status) return;
  const profile = collectClientProfile();
  if (!(Number(profile.credito_desejado) > 0) || !(Number(profile.renda_total) > 0)) {
    status.textContent = "Aguardando perfil";
    setScenarioAnalysisState("empty");
    return;
  }

  const requestId = ++scenarioAnalysisRequestId;
  status.textContent = "Processando...";
  setScenarioAnalysisState("loading");
  try {
    const response = await fetch("/api/cenarios/analisar", {
      method: "POST",
      cache: "no-store",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...profile, considerar_lance_embutido: true }),
    });
    const result = await response.json().catch(() => ({}));
    if (requestId !== scenarioAnalysisRequestId) return;
    if (!response.ok) throw new Error(result.error || "Falha ao calcular cenários.");
    renderScenarioAnalysis(result);
  } catch (error) {
    if (requestId !== scenarioAnalysisRequestId) return;
    status.textContent = "Erro no cálculo";
    setScenarioAnalysisState("error");
    showToast(error.message || "Não foi possível calcular os melhores grupos.", "danger");
  }
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
  const objetivo = document.getElementById("clientProfileObjetivo").value;
  const credito = toNumber(document.getElementById("clientProfileCredito").value);
  const parcelaDesejada = toNumber(document.getElementById("clientProfileParcelaIdeal").value);
  const lanceProprio = toNumber(document.getElementById("clientProfileLanceProprio").value);
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
  const lance = toNumber(document.getElementById("clientProfileLanceProprio").value);
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
  document.getElementById("clientProfileTipoBem").value = objectiveRule.tipoBem || "Imovel";
  document.getElementById("clientProfileEstadoBem").value = objectiveRule.estadoBem || "Pronto";
  document.getElementById("clientProfileParcelaLimite").value = document.getElementById("clientProfileParcelaIdeal").value;
  document.getElementById("clientProfileFgtsTotal").value = formatMoney(fgts);
  document.getElementById("clientProfileTotalDisponivel").value = formatMoney(lance + fgts);
  document.getElementById("clientProfileRendaTotal").value = formatMoney(renda);
  document.getElementById("clientProfileConceito").value = conceito;
  const totals = { fgts, lance, renda, conceito, holderSummary, titulares };
  renderClientPreliminaryAnalysis(calculateClientPreliminaryAnalysis(titulares, holderSummary));
  return totals;
}

function collectClientProfile() {
  const totals = updateClientProfileTotals();
  const summary = totals.holderSummary;
  return {
    tipo_contratacao: totals.titulares.tipo_contratacao,
    titulares: totals.titulares,
    nome: summary.nome,
    nome_conjuge: summary.nome_conjuge,
    credito_desejado: toNumber(document.getElementById("clientProfileCredito").value),
    prazo_desejado: Number(document.getElementById("clientProfilePrazo").value),
    conceito_ia: totals.conceito,
    lance_proprio: toNumber(document.getElementById("clientProfileLanceProprio").value),
    lance_recursos_proprios: summary.lance_recursos_proprios || 0,
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
    objetivo: document.getElementById("clientProfileObjetivo").value,
    tipo_bem: document.getElementById("clientProfileTipoBem").value,
    estado_bem: document.getElementById("clientProfileEstadoBem").value,
  };
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
  renderSmartEngine();
  loadScenarioAnalysis();
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
    renderSmartEngine();
    return;
  }
  renderClientProfileTitulares(profile);
  setMoneyInputValue("clientProfileCredito", profile.credito_desejado);
  setMoneyInputValue("clientProfileLanceProprio", profile.lance_proprio);
  setMoneyInputValue("clientProfileParcelaIdeal", profile.parcela_ideal ?? profile.parcela_desejada);
  const objective = CLIENT_OBJECTIVE_RULES[profile.objetivo] ? profile.objetivo : "Contemplar - urgente - 3 meses";
  setInputValue("clientProfileObjetivo", objective);
  updateClientProfileTotals();
  applyClientProfileToFlow(collectClientProfile());
  renderSmartEngine();
}

function resetClientProfile() {
  document.getElementById("clientProfileForm").reset();
  window.localStorage.removeItem(CLIENT_PROFILE_STORAGE_KEY);
  renderClientProfileTitulares({ tipo_contratacao: "pf_individual" });
  updateClientProfileTotals();
  showToast("Perfil do cliente limpo.", "success");
}

function advanceClientProfile() {
  saveClientProfile({ silent: true });
  activateScreen("viabilidade");
  renderSmartEngine();
  loadScenarioAnalysis();
}

function setStudyState(state) {
  document.getElementById("studyEmpty").classList.toggle("d-none", state !== "empty");
  document.getElementById("studyLoading").classList.toggle("d-none", state !== "loading");
  document.getElementById("studyError").classList.toggle("d-none", state !== "error");
  document.getElementById("studyContent").classList.toggle("d-none", state !== "ready");
}

function studyField(label, value) {
  return detailField(label, value);
}

function computeStudy(payload, viabilityItem, group) {
  if (viabilityItem?.cartas?.length) {
    return {
      creditoContratado: viabilityItem.credito_contratado_total || 0,
      percentualEmbutido: viabilityItem.credito_contratado_total ? (viabilityItem.lance_embutido_total || 0) / viabilityItem.credito_contratado_total : 0,
      lanceEmbutido: viabilityItem.lance_embutido_total || 0,
      lanceProprio: viabilityItem.recurso_proprio_total || 0,
      fgts: viabilityItem.fgts_utilizado_total || 0,
      lanceTotal: viabilityItem.lance_total || 0,
      creditoDisponivel: viabilityItem.credito_liquido_total || 0,
      prazo: viabilityItem.cartas[0]?.prazo_restante || 0,
      parcela: viabilityItem.parcela_total || 0,
      custoTotal: viabilityItem.credito_contratado_total || 0,
      percentualLanceTotal: viabilityItem.percentual_lance_total || 0,
      prazoOperacional: viabilityItem.estrategia || "-",
      lanceReferencia: viabilityItem.cartas[0]?.referencia_lance,
    };
  }
  const creditoDesejado = payload.credito_desejado || viabilityItem.credito || 0;
  const percentualEmbutido = group.percentual_lance_embutido || 0;
  const creditoContratado = percentualEmbutido >= 1 ? creditoDesejado : creditoDesejado / (1 - percentualEmbutido);
  const lanceEmbutido = creditoContratado * percentualEmbutido;
  const lanceProprio = payload.lance_proprio || 0;
  const fgts = payload.fgts || 0;
  const lanceTotal = lanceEmbutido + lanceProprio + fgts;
  const creditoDisponivel = creditoContratado - lanceEmbutido;
  const prazo = group.prazo_restante || group.prazo_total || viabilityItem.prazo || 1;
  const taxaAdm = group.taxa_adm || 0;
  const fundoReserva = group.fundo_reserva || 0;
  const custoTotal = creditoContratado + creditoContratado * taxaAdm + creditoContratado * fundoReserva;
  const parcela = custoTotal / prazo;
  const percentualLanceTotal = creditoContratado ? lanceTotal / creditoContratado : 0;
  const prazoOperacional = viabilityItem.perfil_prazo_operacional || "-";
  const lanceReferencia = viabilityItem.lance_referencia_percentual;
  return { creditoContratado, percentualEmbutido, lanceEmbutido, lanceProprio, fgts, lanceTotal, creditoDisponivel, prazo, parcela, custoTotal, percentualLanceTotal, prazoOperacional, lanceReferencia };
}

function renderStudyClient(payload) {
  const clientFields = [
    ["Nome do cliente", "Pendente"],
    ["Nome do conjuge", "Pendente"],
    ["Data nascimento titular", payload.data_nascimento || "-"],
    ["Data nascimento conjuge", payload.data_nascimento_conjuge || "-"],
    ["Renda total", formatMoney(payload.renda_total)],
    ["Estado do bem", payload.estado_bem || "Nao definido"],
    ["Objetivo credito", payload.objetivo],
    ["Tipo de bem", payload.tipo_bem || "-"],
  ];
  const scenarioFields = [
    ["Credito desejado", formatMoney(payload.credito_desejado)],
    ["Prazo desejado", `${payload.prazo_desejado} meses`],
    ["Lance proprio disponivel", formatMoney(payload.lance_proprio)],
    ["FGTS total informado", formatMoney(payload.fgts)],
    ["Recurso total disponivel", formatMoney((payload.lance_proprio || 0) + (payload.fgts || 0))],
    ["Parcela maxima desejada", formatMoney(payload.parcela_desejada)],
    ["Renda total", formatMoney(payload.renda_total)],
    ["Perfil por prazo", currentStudy?.viabilityItem?.perfil_prazo_operacional || "-"],
  ];
  document.getElementById("studyClientGrid").innerHTML = clientFields.map(([label, value]) => studyField(label, value)).join("");
  document.getElementById("studyScenarioGrid").innerHTML = scenarioFields.map(([label, value]) => studyField(label, value)).join("");
  const now = new Date();
  document.getElementById("studyScenarioDate").textContent = `Criado em: ${now.toLocaleString("pt-BR")}`;
  document.getElementById("studyVersionDate").textContent = now.toLocaleString("pt-BR");
}

function renderStudyGroup(group) {
  const administradora = group.administradora || "Administradora";
  const fields = [
    ["Administradora", administradora],
    ["Grupo", group.grupo || "-"],
    ["Tipo de bem", group.tipo_bem || "-"],
    ["Inicio do grupo", group.primeira_assembleia || "-"],
    ["Termino do grupo", group.data_termino || group.ultima_assembleia || "-"],
    ["Prazo total", group.prazo_total ? `${group.prazo_total} meses` : "-"],
    ["Prazo restante", group.prazo_restante ? `${group.prazo_restante} meses` : "-"],
    ["Taxa de administracao", formatPercent(group.taxa_adm)],
    ["Fundo de reserva", formatPercent(group.fundo_reserva)],
    ["Meia parcela", formatBool(group.meia_parcela)],
    ["Status", group.status || "-"],
  ];
  document.getElementById("studyAdminLogo").textContent = initialsFromName(administradora);
  document.getElementById("studyAdminName").textContent = administradora;
  document.getElementById("studyGroupGrid").innerHTML = fields.map(([label, value]) => studyField(label, value)).join("");
  document.getElementById("studyGroupSubtitle").textContent = `Grupo ${group.grupo || "-"} - ${group.tipo_bem || "-"}`;
  document.getElementById("studyOperationalDates").innerHTML = [
    ["Proxima assembleia", group.proxima_assembleia || group.ultima_assembleia || "-"],
    ["Limite de adesao", group.limite_adesao || "-"],
    ["Vencimento 1a parcela", group.vencimento_primeira_parcela || group.vencimento_parcela || "-"],
    ["Vencimento do lance", group.vencimento_lance || "-"],
  ].map(([label, value]) => studyField(label, value)).join("");
}

function renderStudySummary(financial, group, viabilityItem) {
  document.getElementById("studyCreditoOriginal").textContent = formatMoney(financial.creditoContratado);
  document.getElementById("studyLanceEmbutido").textContent = `${formatPercent(financial.percentualEmbutido)} / ${formatMoney(financial.lanceEmbutido)}`;
  document.getElementById("studyCreditoDisponivel").textContent = formatMoney(financial.creditoDisponivel);
  document.getElementById("studyRecursoProprio").textContent = formatMoney(financial.lanceProprio + financial.fgts);
  document.getElementById("studyPercentualLanceTotal").textContent = formatPercent(financial.percentualLanceTotal);
  document.getElementById("studyLanceTotal").textContent = formatMoney(financial.lanceTotal);
  document.getElementById("studyParcelaInicial").textContent = formatMoney(financial.parcela);
  document.getElementById("studyParcelaApos").textContent = financial.lanceReferencia === null || financial.lanceReferencia === undefined ? "-" : formatPercent(financial.lanceReferencia);
  document.getElementById("studyPrazoApos").textContent = financial.prazoOperacional;
  document.getElementById("studyCustoTotal").textContent = formatMoney(financial.custoTotal);
  document.getElementById("studySeguroGarantia").textContent = formatBool(group.seguro_garantia);
  document.getElementById("studyProximaAssembleia").textContent = group.proxima_assembleia || group.ultima_assembleia || "-";
  document.getElementById("studyChanceContemplacao").textContent = "Referencia operacional";
  const score = Math.round((viabilityItem.afinidade || 0) * 100);
  document.getElementById("studyRankingPosition").textContent = score || "-";
  const profileByRange = {
    "1 a 3 meses": "Lance Agressivo",
    "4 a 6 meses": "Lance Moderado",
    "7 a 12 meses": "Lance Conservador",
    "13 a 24 meses": "Lance Super Conservador",
    "Sem urgencia": "Investidor",
  };
  const recommended = profileByRange[financial.prazoOperacional] || "Perfil operacional";
  const alternatives = {
    "Lance Agressivo": "Lance Moderado",
    "Lance Moderado": "Lance Conservador",
    "Lance Conservador": "Lance Super Conservador",
    "Lance Super Conservador": "Investidor",
    "Investidor": "Lance Super Conservador",
  };
  document.getElementById("studyRecommendedStrategy").textContent = recommended;
  document.getElementById("studyAlternativeStrategy").textContent = alternatives[recommended] || "Acompanhar historico";
  renderStudyTemplateTechnical(financial, group, viabilityItem);
  updateStudyCompletion();
}

function renderStudyStrategies(group, financial) {
  currentStudyStrategies = [
    ["Investidor", group.lance_investidor, "Sem urgencia"],
    ["Super Conservador", group.lance_super_conservador, "13 a 24 meses"],
    ["Conservador", group.lance_conservador, "7 a 12 meses"],
    ["Moderado", group.lance_moderado, "4 a 6 meses"],
    ["Agressivo", group.lance_agressivo, "1 a 3 meses"],
  ].map(([label, percent, prazoOperacional]) => {
    const percentual = percent ?? null;
    const lanceTotal = financial.creditoContratado * (percentual || 0);
    return {
      label,
      percent: percentual,
      lanceProprio: Math.max(0, lanceTotal - financial.lanceEmbutido),
      prazoOperacional,
      classificacao: percentual === null ? "Historico insuficiente" : "Referencia operacional",
    };
  });
  currentStudyStrategyTab = currentStudyStrategies.some((item) => item.label === currentStudyStrategyTab) ? currentStudyStrategyTab : "Investidor";
  renderStudyStrategyTabs();
  renderStudyStrategyTable();
}

function renderStudyStrategyTabs() {
  document.getElementById("studyStrategyTabs").innerHTML = currentStudyStrategies.map((strategy) => `
    <li class="nav-item" role="presentation">
      <button class="nav-link ${strategy.label === currentStudyStrategyTab ? "active" : ""}" type="button" data-study-strategy="${escapeHtml(strategy.label)}">${escapeHtml(strategy.label)}</button>
    </li>
  `).join("");
}

function renderStudyStrategyTable() {
  const financial = currentStudy?.financial;
  if (!financial) return;
  const strategies = currentStudyStrategies.filter((strategy) => strategy.label === currentStudyStrategyTab);
  document.getElementById("studyStrategiesBody").innerHTML = strategies.map((strategy) => {
    return `
      <tr>
        <td>${escapeHtml(strategy.label)}</td>
        <td>${strategy.percent === null ? "-" : formatPercent(strategy.percent)}</td>
        <td>${formatMoney(financial.lanceEmbutido)}</td>
        <td>${formatMoney(strategy.lanceProprio)}</td>
        <td>${formatMoney(financial.creditoDisponivel)}</td>
        <td>${formatMoney(financial.parcela)}</td>
        <td>${escapeHtml(strategy.prazoOperacional)}</td>
        <td>${escapeHtml(strategy.classificacao)}</td>
      </tr>
    `;
  }).join("");
}

function renderStudyHistory(group) {
  const entries = Object.entries(group.historico || {}).slice(-12);
  const maiores = entries.map(([, item]) => item.maior_lance ? item.maior_lance * 100 : null);
  const menores = entries.map(([, item]) => item.menor_lance ? item.menor_lance * 100 : null);
  const qtd = entries.map(([, item]) => item.qtd_contemplacoes || 0);
  const mediaMaior = averageNumber(maiores);
  const mediaMenor = averageNumber(menores);
  const mediaQtd = averageNumber(qtd);
  const totalQtd = qtd.reduce((sum, value) => sum + value, 0);

  document.getElementById("studyAvgMaiorLance").textContent = mediaMaior === null ? "-" : `${mediaMaior.toLocaleString("pt-BR", { maximumFractionDigits: 2 })}%`;
  document.getElementById("studyAvgMenorLance").textContent = mediaMenor === null ? "-" : `${mediaMenor.toLocaleString("pt-BR", { maximumFractionDigits: 2 })}%`;
  document.getElementById("studyAvgContemplacoes").textContent = mediaQtd === null ? "-" : mediaQtd.toLocaleString("pt-BR", { maximumFractionDigits: 1 });
  document.getElementById("studyTotalContemplacoes").textContent = totalQtd.toLocaleString("pt-BR");

  if (studyChart) studyChart.destroy();
  studyChart = new Chart(document.getElementById("studyHistoryChart"), {
    type: "bar",
    data: {
      labels: entries.map(([month]) => month),
      datasets: [
        { label: "Maior Lance (%)", data: maiores, backgroundColor: "#0d6efd" },
        { label: "Menor Lance (%)", data: menores, backgroundColor: "#16a34a" },
        { label: "Qtd Contemplacoes", data: qtd, backgroundColor: "#f59e0b" },
      ],
    },
    options: { responsive: true, maintainAspectRatio: false },
  });
}

function renderStudyRecommendations(viabilityItem, financial, group) {
  const level = viabilityItem.afinidade >= 0.9 ? "Recomendacao forte" : viabilityItem.afinidade >= 0.8 ? "Recomendacao moderada" : "Recomendacao com acompanhamento";
  document.getElementById("studyRecommendationLevel").textContent = viabilityItem.selo || level;
  const historyEntries = Object.values(group.historico || {}).slice(-12);
  const totalContemplacoes = historyEntries.reduce((sum, item) => sum + (item.qtd_contemplacoes || 0), 0);
  const estrategiaRecomendada = currentStudyStrategies.find((strategy) => strategy.percent === financial.lanceReferencia) || currentStudyStrategies[0];
  const recommendations = [
    totalContemplacoes > 0 ? `Grupo com bom historico: ${totalContemplacoes} contemplacao(oes) nos ultimos 12 meses.` : "Grupo sem contemplacoes registradas nos ultimos 12 meses; acompanhar historico antes da oferta.",
    `Estrategia recomendada: ${estrategiaRecomendada.label} com ${formatPercent(estrategiaRecomendada.percent)} de lance.`,
    `Prazo operacional do perfil: ${financial.prazoOperacional}.`,
    financial.parcela <= (currentStudy.payload.parcela_desejada || 0) ? "Parcela estimada dentro do limite informado." : "Parcela estimada exige validacao com o cliente.",
    "Necessidade de acompanhamento semanal das assembleias e do historico mensal.",
    "A analise nao garante contemplacao.",
  ];
  document.getElementById("studyRecommendations").innerHTML = recommendations.map((text) => `<li class="check-ok">${escapeHtml(text)}</li>`).join("");
  document.getElementById("studyRecommendationReasons").innerHTML = recommendations.slice(0, 5).map((text) => `<li>${escapeHtml(text)}</li>`).join("");
  updateStudyTemplatePreview();
}

function collectStudyOperatorFields() {
  return Object.fromEntries(studyOperatorFields.map(([key, , id]) => [key, document.getElementById(id)?.value.trim() || ""]));
}

function renderStudyTemplateFields(values = {}) {
  studyOperatorFields.forEach(([key, , id]) => {
    const input = document.getElementById(id);
    if (input) input.value = values[key] || "";
  });
  updateStudyCompletion();
  updateStudyTemplatePreview();
}

function updateStudyCompletion() {
  const values = collectStudyOperatorFields();
  const filled = studyOperatorFields.filter(([key]) => values[key]).length;
  const percent = Math.round(((8 + filled) / 12) * 100);
  document.getElementById("studyCompletionPercent").textContent = `${percent}%`;
  const missing = studyOperatorFields.filter(([key]) => !values[key]);
  document.getElementById("studyPendingFields").innerHTML = missing.length
    ? missing.map(([, label]) => `<li>${escapeHtml(label)}</li>`).join("")
    : `<li>Todos os campos do operador foram preenchidos</li>`;
}

function updateStudyTemplatePreview() {
  if (!currentStudy) return;
  const values = collectStudyOperatorFields();
  const group = currentStudy.group || {};
  const financial = currentStudy.financial || {};
  document.getElementById("studyTemplatePreviewText").textContent = [
    `Estudo para credito de ${formatMoney(currentStudy.payload.credito_desejado)} no grupo ${group.grupo || "-"} da ${group.administradora || "administradora selecionada"}.`,
    `Estrategia recomendada: ${document.getElementById("studyRecommendedStrategy")?.textContent || "-"} com referencia de ${formatPercent(financial.lanceReferencia)}.`,
    values.comentario_cliente ? `Comentario ao cliente: ${values.comentario_cliente}` : "Comentario ao cliente pendente.",
    values.condicoes_especiais ? `Condicoes especiais: ${values.condicoes_especiais}` : "Condicoes especiais pendentes.",
  ].join(" ");
}

function renderStudyTemplateTechnical(financial, group, viabilityItem) {
  document.getElementById("studyTemplateTechnicalGrid").innerHTML = [
    ["Grupo ID", group.grupo_id || "-"],
    ["Afinidade", formatPercent(viabilityItem.afinidade)],
    ["Lance referencia", formatPercent(financial.lanceReferencia)],
    ["Prazo operacional", financial.prazoOperacional],
    ["Credito contratado", formatMoney(financial.creditoContratado)],
    ["Parcela inicial", formatMoney(financial.parcela)],
  ].map(([label, value]) => studyField(label, value)).join("");
}

function activateStudyTemplateTab(tabName) {
  document.querySelectorAll("[data-study-template-tab]").forEach((button) => {
    button.classList.toggle("active", button.dataset.studyTemplateTab === tabName);
  });
  document.getElementById("studyTemplatePreview").classList.toggle("active", tabName === "preview");
  document.getElementById("studyTemplateFields").classList.toggle("active", tabName === "fields");
  document.getElementById("studyTemplateTechnical").classList.toggle("active", tabName === "technical");
}

async function openFinancialStudy(groupId, viabilityItem) {
  const payload = collectClientProfile();
  currentStudy = { groupId, viabilityItem, payload, group: null, cenario: viabilityItem?.cartas ? viabilityItem : null, templateCampos: {} };
  activateScreen("estudo");
  setStudyState("loading");
  try {
    const group = await apiGet(`/grupos/${encodeURIComponent(groupId)}`);
    currentStudy.group = group;
    const financial = computeStudy(payload, viabilityItem, group);
    currentStudy.financial = financial;
    renderStudyClient(payload);
    renderStudyGroup(group);
    renderStudySummary(financial, group, viabilityItem);
    renderStudyStrategies(group, financial);
    renderStudyHistory(group);
    renderStudyRecommendations(viabilityItem, financial, group);
    renderStudyTemplateFields(currentStudy.templateCampos);
    setStudyState("ready");
  } catch (error) {
    setStudyState("error");
  }
}

async function saveCurrentStudy() {
  if (!currentStudy) {
    showToast("Selecione um cenario na Viabilidade antes de salvar.", "warning");
    return null;
  }
  const payload = {
    cliente: {
      nome: currentStudy.payload.nome || "Cliente em estudo",
      nome_conjuge: currentStudy.payload.nome_conjuge || "",
      tipo_contratacao: currentStudy.payload.tipo_contratacao,
      titulares: currentStudy.payload.titulares,
      credito_desejado: currentStudy.payload.credito_desejado,
      objetivo: currentStudy.payload.objetivo,
      prazo_desejado: currentStudy.payload.prazo_desejado,
      lance_proprio: currentStudy.payload.lance_proprio,
      fgts: currentStudy.payload.fgts,
      renda_total: currentStudy.payload.renda_total,
      parcela_desejada: currentStudy.payload.parcela_desejada,
      data_nascimento: currentStudy.payload.data_nascimento,
      data_nascimento_conjuge: currentStudy.payload.data_nascimento_conjuge,
      estado_bem: currentStudy.payload.estado_bem || "",
    },
    grupo_id: currentStudy.groupId,
    cenario: currentStudy.cenario,
    template_campos: collectStudyOperatorFields(),
  };
  const result = await apiPost("/estudos", payload);
  currentStudy.savedStudyId = result.estudo_id;
  document.getElementById("studyDisplayId").textContent = result.estudo_id;
  showToast(`Estudo salvo: ${result.estudo_id}`, "success");
  loadHistoryStudies();
  return result;
}

async function exportStudyPdf(studyId) {
  let targetStudyId = studyId;
  if (!targetStudyId && currentStudy) {
    if (!currentStudy.savedStudyId) {
      const result = await saveCurrentStudy();
      targetStudyId = result?.estudo_id;
    } else {
      targetStudyId = currentStudy.savedStudyId;
    }
  }
  if (!targetStudyId) {
    showToast("Salve ou selecione um estudo antes de gerar o PDF.", "warning");
    return;
  }
  const result = await apiPost(`/estudos/${encodeURIComponent(targetStudyId)}/exportar-pdf`, {});
  showToast("PDF gerado.", "success");
  window.open(result.download_url, "_blank", "noopener");
}

async function ensureCurrentStudySaved() {
  if (!currentStudy) {
    showToast("Selecione um cenario na Viabilidade antes de compartilhar.", "warning");
    return null;
  }
  if (currentStudy.savedStudyId) return currentStudy.savedStudyId;
  const result = await saveCurrentStudy();
  return result?.estudo_id || null;
}

async function shareCurrentStudy() {
  const estudoId = await ensureCurrentStudySaved();
  if (!estudoId) return;
  const url = buildStudyShareUrl(estudoId);
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(url);
    showToast("Link do estudo copiado.", "success");
    return;
  }
  window.prompt("Link do estudo", url);
}

function buildStudyShareUrl(studyId) {
  return `${window.location.origin}${window.location.pathname}?estudo_id=${encodeURIComponent(studyId)}`;
}

function buildStudyEmailSubject(study) {
  const cliente = study?.cliente?.nome || "cliente";
  const grupo = study?.grupo?.grupo || study?.grupo_id || "";
  return `Estudo financeiro Crediclass - ${cliente}${grupo ? ` - Grupo ${grupo}` : ""}`;
}

function buildStudyEmailBody(study, shareUrl) {
  const cliente = study?.cliente || {};
  const grupo = study?.grupo || {};
  const financeiro = study?.financeiro || {};
  const lines = [
    "Ola,",
    "",
    "Segue o estudo financeiro Crediclass para consulta.",
    "",
    `Cliente: ${cliente.nome || "-"}`,
    `Administradora: ${grupo.administradora || "-"}`,
    `Grupo: ${grupo.grupo || study?.grupo_id || "-"}`,
    `Tipo de bem: ${grupo.tipo_bem || "-"}`,
    `Credito desejado: ${formatMoney(cliente.credito_desejado || financeiro.credito || null)}`,
    `Estrategia: ${study?.estrategia || "-"}`,
    `Status: ${study?.status || "-"}`,
    "",
    `Link do estudo: ${shareUrl}`,
    "",
    "Atenciosamente,",
    "Crediclass",
  ];
  return lines.join("\n");
}

function openEmailDraft(study) {
  const shareUrl = buildStudyShareUrl(study.estudo_id);
  const subject = encodeURIComponent(buildStudyEmailSubject(study));
  const body = encodeURIComponent(buildStudyEmailBody(study, shareUrl));
  window.location.href = `mailto:?subject=${subject}&body=${body}`;
  showToast("E-mail preparado no cliente de e-mail.", "success");
}

async function emailCurrentStudy() {
  const estudoId = await ensureCurrentStudySaved();
  if (!estudoId) return;
  const study = await apiGet(`/estudos/${encodeURIComponent(estudoId)}`);
  openEmailDraft(study);
}

async function emailHistoryStudy(studyId) {
  const study = await apiGet(`/estudos/${encodeURIComponent(studyId)}`);
  openEmailDraft(study);
}

function setHistoryState(state) {
  document.getElementById("historyLoading").classList.toggle("d-none", state !== "loading");
  document.getElementById("historyError").classList.toggle("d-none", state !== "error");
  document.getElementById("historyEmpty").classList.toggle("d-none", state !== "empty");
  document.getElementById("historyTableWrap").classList.toggle("d-none", state !== "ready");
}

function getHistoryFilters() {
  return {
    data_inicio: document.getElementById("historyStartDate").value,
    data_fim: document.getElementById("historyEndDate").value,
    cliente: document.getElementById("historyCliente").value.trim(),
    grupo: document.getElementById("historyGrupo").value.trim(),
    administradora: document.getElementById("historyAdministradora").value.trim(),
    tipo_bem: document.getElementById("historyTipoBem").value.trim(),
    status: document.getElementById("historyStatus").value,
    operador: document.getElementById("historyOperador").value,
    estrategia: document.getElementById("historyEstrategia").value,
    credito_minimo: document.getElementById("historyCreditoMinimo").value ? toNumber(document.getElementById("historyCreditoMinimo").value) : "",
    credito_maximo: document.getElementById("historyCreditoMaximo").value ? toNumber(document.getElementById("historyCreditoMaximo").value) : "",
  };
}

function renderHistorySummary(items) {
  document.getElementById("historyTotal").textContent = items.length;
  document.getElementById("historyDone").textContent = items.filter((item) => item.status === "Concluido").length;
  document.getElementById("historyOpen").textContent = items.filter((item) => item.status === "Em andamento").length;
  document.getElementById("historyCanceled").textContent = items.filter((item) => item.status === "Cancelado").length;
  document.getElementById("historyUpdated").textContent = new Date().toLocaleTimeString("pt-BR");
  renderHistoryCharts(items);
}

function last30DateLabels() {
  return Array.from({ length: 30 }, (_, index) => {
    const date = new Date();
    date.setDate(date.getDate() - (29 - index));
    return date.toISOString().slice(0, 10);
  });
}

function renderHistoryCharts(items) {
  const strategyCounts = items.reduce((acc, item) => {
    const key = item.estrategia || "Sem estrategia";
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});
  const strategyLabels = Object.keys(strategyCounts);
  const strategyData = strategyLabels.map((label) => strategyCounts[label]);

  if (historyStrategyChart) historyStrategyChart.destroy();
  historyStrategyChart = new Chart(document.getElementById("historyStrategyChart"), {
    type: "doughnut",
    data: {
      labels: strategyLabels.length ? strategyLabels : ["Sem estudos"],
      datasets: [{ data: strategyData.length ? strategyData : [1], backgroundColor: ["#0d6efd", "#16a34a", "#f59e0b", "#64748b", "#dc2626"] }],
    },
    options: { responsive: true, maintainAspectRatio: false },
  });

  const labels = last30DateLabels();
  const countsByDate = items.reduce((acc, item) => {
    const key = String(item.criado_em || "").slice(0, 10);
    if (key) acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});

  if (historyEvolutionChart) historyEvolutionChart.destroy();
  historyEvolutionChart = new Chart(document.getElementById("historyEvolutionChart"), {
    type: "line",
    data: {
      labels: labels.map((date) => date.slice(5)),
      datasets: [{ label: "Estudos", data: labels.map((date) => countsByDate[date] || 0), borderColor: "#0d6efd", backgroundColor: "rgba(13, 110, 253, 0.12)", tension: 0.25, fill: true }],
    },
    options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } },
  });
}

function renderHistoryTable(items) {
  document.getElementById("historyTableBody").innerHTML = items.map((item) => {
    const cliente = item.cliente || {};
    const grupo = item.grupo || {};
    const financeiro = item.financeiro || {};
    return `
      <tr>
        <td>${escapeHtml(item.estudo_id)}</td>
        <td>${escapeHtml(item.criado_em || "-")}</td>
        <td>${escapeHtml(cliente.nome || "-")}</td>
        <td>${escapeHtml(grupo.administradora || "-")}</td>
        <td>${escapeHtml(grupo.grupo || item.grupo_id || "-")}</td>
        <td>${formatMoney(cliente.credito_desejado || financeiro.credito || null)}</td>
        <td>${escapeHtml(item.estrategia || "-")}</td>
        <td><span class="status-badge">${escapeHtml(item.status || "-")}</span></td>
        <td>${escapeHtml(item.operador || "-")}</td>
        <td>
          <div class="row-actions">
            <button class="btn btn-sm btn-outline-primary" type="button" data-history-action="visualizar" data-study-id="${escapeHtml(item.estudo_id)}">Ver</button>
            <button class="btn btn-sm btn-outline-secondary" type="button" data-history-action="pdf" data-study-id="${escapeHtml(item.estudo_id)}">PDF</button>
            <button class="btn btn-sm btn-outline-secondary" type="button" data-history-action="email" data-study-id="${escapeHtml(item.estudo_id)}">E-mail</button>
            <button class="btn btn-sm btn-outline-secondary" type="button" data-history-action="duplicar" data-study-id="${escapeHtml(item.estudo_id)}">Duplicar</button>
            <button class="btn btn-sm btn-outline-danger" type="button" data-history-action="excluir" data-study-id="${escapeHtml(item.estudo_id)}">Excluir</button>
          </div>
        </td>
      </tr>
    `;
  }).join("");
}

function setStudyDetailsState(state) {
  document.getElementById("studyDetailsLoading").classList.toggle("d-none", state !== "loading");
  document.getElementById("studyDetailsError").classList.toggle("d-none", state !== "error");
  document.getElementById("studyDetailsContent").classList.toggle("d-none", state !== "ready");
}

function renderStudyDetails(item) {
  const cliente = item.cliente || {};
  const grupo = item.grupo || {};
  const financeiro = item.financeiro || {};
  const historico = financeiro.historico_12_meses || {};
  document.getElementById("studyDetailsTitle").textContent = `Detalhes do Estudo ${item.estudo_id}`;
  document.getElementById("studyDetailsSubtitle").textContent = `${cliente.nome || "Cliente"} - ${grupo.administradora || "Administradora"} ${grupo.grupo || item.grupo_id || ""}`;
  document.getElementById("studyDetailsMeta").textContent = `${item.operador || "Joyce"} - ${item.criado_em || "-"}`;
  document.getElementById("studyDetailsClientGrid").innerHTML = [
    ["Nome", cliente.nome || "-"],
    ["Objetivo", cliente.objetivo || "-"],
    ["Credito desejado", formatMoney(cliente.credito_desejado)],
    ["Prazo desejado", cliente.prazo_desejado ? `${cliente.prazo_desejado} meses` : "-"],
    ["Lance proprio", formatMoney(cliente.lance_proprio)],
    ["FGTS utilizado", formatMoney(cliente.fgts)],
    ["Renda total", formatMoney(cliente.renda_total)],
    ["Parcela desejada", formatMoney(cliente.parcela_desejada)],
    ["Data nascimento titular", cliente.data_nascimento || "-"],
    ["Data nascimento conjuge", cliente.data_nascimento_conjuge || "-"],
    ["Estado do bem", cliente.estado_bem || "-"],
  ].map(([label, value]) => detailField(label, value)).join("");
  document.getElementById("studyDetailsGroupGrid").innerHTML = [
    ["Administradora", grupo.administradora || "-"],
    ["Grupo", grupo.grupo || item.grupo_id || "-"],
    ["Tipo de bem", grupo.tipo_bem || "-"],
    ["Credito disponivel", formatMoney(financeiro.credito_disponivel)],
    ["Prazo total", grupo.prazo_total ? `${grupo.prazo_total} meses` : "-"],
    ["Prazo restante", grupo.prazo_restante ? `${grupo.prazo_restante} meses` : "-"],
    ["Status do grupo", grupo.status || "-"],
    ["Status do estudo", item.status || "-"],
  ].map(([label, value]) => detailField(label, value)).join("");
  document.getElementById("studyDetailsFinancialGrid").innerHTML = [
    ["Carta de credito", formatMoney(financeiro.credito_original || financeiro.credito)],
    ["Lance embutido", formatMoney(financeiro.lance_embutido)],
    ["Recurso proprio", formatMoney(financeiro.recurso_proprio)],
    ["Valor total do lance", formatMoney(financeiro.valor_total_lance)],
    ["Parcela estimada", formatMoney(financeiro.parcela_inicial)],
    ["Prazo operacional", financeiro.prazo_operacional || "-"],
    ["Classificacao", financeiro.chance_contemplacao || "-"],
    ["Total contemplacoes 12m", historico.total_contemplacoes ?? "-"],
  ].map(([label, value]) => detailField(label, value)).join("");
  document.getElementById("studyDetailsStrategiesBody").innerHTML = (financeiro.estrategias || []).map((strategy) => `
    <tr>
      <td>${escapeHtml(strategy.estrategia || "-")}</td>
      <td>${formatPercent(strategy.percentual_lance)}</td>
      <td>${formatMoney(strategy.lance_embutido)}</td>
      <td>${formatMoney(strategy.lance_proprio)}</td>
      <td>${formatMoney(strategy.credito_disponivel)}</td>
      <td>${formatMoney(financeiro.parcela_inicial)}</td>
      <td>${escapeHtml(strategy.prazo_operacional || "-")}</td>
      <td>${escapeHtml(strategy.chance_contemplacao || "-")}</td>
    </tr>
  `).join("") || `<tr><td colspan="8" class="text-center text-secondary">Estrategias nao encontradas.</td></tr>`;
}

async function openStudyDetails(studyId) {
  if (!studyDetailsModal) {
    studyDetailsModal = new bootstrap.Modal(document.getElementById("studyDetailsModal"));
  }
  studyDetailsModal.show();
  setStudyDetailsState("loading");
  try {
    const item = await apiGet(`/estudos/${encodeURIComponent(studyId)}`);
    renderStudyDetails(item);
    setStudyDetailsState("ready");
  } catch (error) {
    setStudyDetailsState("error");
  }
}

async function openSharedStudyFromUrl() {
  const params = new URLSearchParams(window.location.search);
  const estudoId = params.get("estudo_id");
  if (!estudoId) return;
  activateScreen("historico");
  loadHistoryStudies();
  await openStudyDetails(estudoId);
}

async function duplicateStudy(studyId) {
  const original = await apiGet(`/estudos/${encodeURIComponent(studyId)}`);
  const cliente = { ...(original.cliente || {}) };
  cliente.nome = cliente.nome ? `${cliente.nome} - copia` : "Cliente em estudo - copia";
  const result = await apiPost("/estudos", {
    cliente,
    grupo_id: original.grupo_id,
  });
  showToast(`Estudo duplicado: ${result.estudo_id}`, "success");
  loadHistoryStudies();
}

async function loadHistoryStudies() {
  setHistoryState("loading");
  try {
    const query = new URLSearchParams();
    Object.entries(getHistoryFilters()).forEach(([key, value]) => {
      if (value) query.set(key, value);
    });
    const data = await apiGet(`/estudos?${query.toString()}`);
    historyState.items = data.items || [];
    renderHistorySummary(historyState.items);
    renderHistoryTable(historyState.items);
    document.getElementById("historySubtitle").textContent = `${data.total} estudo(s) encontrado(s)`;
    setHistoryState(historyState.items.length ? "ready" : "empty");
    addOperationalLog(`Historico de Estudos carregado: ${data.total} estudo(s)`);
  } catch (error) {
    renderHistorySummary([]);
    document.getElementById("historySubtitle").textContent = "Erro ao carregar estudos";
    setHistoryState("error");
    addOperationalLog("Falha ao carregar Historico de Estudos");
  }
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
    renderSmartEngine();
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
}

document.querySelectorAll(".nav-item").forEach((item) => {
  item.addEventListener("click", () => activateScreen(item.dataset.screen));
});

document.querySelectorAll("[data-screen-jump]").forEach((button) => {
  button.addEventListener("click", () => activateScreen(button.dataset.screenJump));
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
  if (document.getElementById("screen-estudo").classList.contains("active")) {
    saveCurrentStudy().catch(() => setStudyState("error"));
    return;
  }
  if (document.getElementById("screen-historico").classList.contains("active")) {
    loadHistoryStudies();
    return;
  }
});
document.getElementById("reloadMapDataBtn").addEventListener("click", reloadMapData);
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
  hideHistoryHoverModal();
});

document.getElementById("groupsTableBody").addEventListener("focusin", (event) => {
  const trigger = event.target.closest("[data-history-index]");
  if (trigger) showHistoryHoverModal(trigger);
});

document.getElementById("groupsTableBody").addEventListener("focusout", (event) => {
  const trigger = event.target.closest("[data-history-index]");
  if (trigger) hideHistoryHoverModal();
});

document.getElementById("historyHoverModal").addEventListener("mouseleave", hideHistoryHoverModal);

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
];

moneyInputIds.forEach((id) => {
  document.getElementById(id)?.addEventListener("blur", () => formatMoneyInputById(id));
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

["clientProfilePrazo", "clientProfileObjetivo", "clientProfileTipoBem", "clientProfileEstadoBem"].forEach((id) => {
  document.getElementById(id).addEventListener("change", updateClientProfileTotals);
});

document.getElementById("clientProfileTipoContratacao").addEventListener("change", (event) => {
  const current = collectClientTitularesFromForm();
  current.tipo_contratacao = event.target.value;
  renderClientProfileTitulares(current);
  updateClientProfileTotals();
});

document.getElementById("clientProfileForm").addEventListener("input", (event) => {
  if (!event.target.matches("[data-holder-field]")) return;
  updateClientProfileTotals();
});

document.getElementById("clientProfileForm").addEventListener("blur", (event) => {
  if (event.target.matches("[data-holder-field][data-money]")) {
    event.target.value = formatMoneyInputValue(event.target.value);
    updateClientProfileTotals();
  }
}, true);

document.getElementById("saveClientProfileBtn").addEventListener("click", () => saveClientProfile());
document.getElementById("clearClientProfileBtn").addEventListener("click", resetClientProfile);
document.getElementById("advanceClientProfileBtn").addEventListener("click", advanceClientProfile);

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

document.getElementById("studyChangeGroupBtn").addEventListener("click", () => activateScreen("viabilidade"));
document.getElementById("studyViewStrategyBtn").addEventListener("click", () => {
  document.querySelector(".study-v4-strategy")?.scrollIntoView({ behavior: "smooth", block: "start" });
});
document.getElementById("studyHistoryShortcutBtn").addEventListener("click", () => activateScreen("historico"));
document.getElementById("studyCompareStrategiesBtn").addEventListener("click", () => {
  document.querySelector(".study-v4-strategy-tabs")?.scrollIntoView({ behavior: "smooth", block: "center" });
});
document.querySelectorAll("[data-study-template-tab]").forEach((button) => {
  button.addEventListener("click", () => activateStudyTemplateTab(button.dataset.studyTemplateTab));
});
studyOperatorFields.forEach(([, , id]) => {
  document.getElementById(id).addEventListener("input", () => {
    if (currentStudy) currentStudy.templateCampos = collectStudyOperatorFields();
    updateStudyCompletion();
    updateStudyTemplatePreview();
  });
});
document.getElementById("studyNewSimulationBtn").addEventListener("click", () => {
  activateScreen("viabilidade");
});
document.getElementById("studyStrategyTabs").addEventListener("click", (event) => {
  const button = event.target.closest("[data-study-strategy]");
  if (!button) return;
  currentStudyStrategyTab = button.dataset.studyStrategy;
  renderStudyStrategyTabs();
  renderStudyStrategyTable();
});
document.getElementById("studySaveBtn").addEventListener("click", () => {
  saveCurrentStudy().catch(() => setStudyState("error"));
});
document.getElementById("studyPdfBtn").addEventListener("click", () => {
  exportStudyPdf().catch(() => showToast("Nao foi possivel gerar o PDF.", "danger"));
});
document.getElementById("studyShareBtn").addEventListener("click", () => {
  shareCurrentStudy().catch(() => showToast("Nao foi possivel compartilhar o estudo.", "danger"));
});
document.getElementById("studyEmailBtn").addEventListener("click", () => {
  emailCurrentStudy().catch(() => showToast("Nao foi possivel preparar o e-mail.", "danger"));
});

document.getElementById("historyFilters").addEventListener("submit", (event) => {
  event.preventDefault();
  loadHistoryStudies();
});

document.getElementById("clearHistoryBtn").addEventListener("click", () => {
  document.getElementById("historyFilters").reset();
  loadHistoryStudies();
});

document.getElementById("exportStudiesCsvBtn").addEventListener("click", exportStudiesCsv);

document.getElementById("historyTableBody").addEventListener("click", async (event) => {
  const button = event.target.closest("[data-history-action]");
  if (!button) return;
  const studyId = button.dataset.studyId;
  if (button.dataset.historyAction === "visualizar") {
    openStudyDetails(studyId);
    return;
  }
  if (button.dataset.historyAction === "duplicar") {
    duplicateStudy(studyId).catch(() => showToast("Nao foi possivel duplicar o estudo.", "danger"));
    return;
  }
  if (button.dataset.historyAction === "excluir") {
    await apiDelete(`/estudos/${encodeURIComponent(studyId)}`);
    showToast("Estudo excluido.", "success");
    loadHistoryStudies();
    return;
  }
  if (button.dataset.historyAction === "pdf") {
    exportStudyPdf(studyId).catch(() => showToast("Nao foi possivel gerar o PDF.", "danger"));
    return;
  }
  if (button.dataset.historyAction === "email") {
    emailHistoryStudy(studyId).catch(() => showToast("Nao foi possivel preparar o e-mail.", "danger"));
  }
});

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
