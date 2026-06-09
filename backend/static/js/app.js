const screens = {
  mapa: {
    letter: "A) MAPA DE GRUPOS",
    title: "Mapa de Grupos",
    subtitle: "Lista e manutencao da base de grupos",
    action: "Novo Grupo",
  },
  perfil: {
    letter: "B) PERFIL DO CLIENTE",
    title: "Perfil do Cliente",
    subtitle: "Entrevista, capacidade financeira e necessidade de credito",
    action: "Salvar Perfil",
  },
  viabilidade: {
    letter: "D) VIABILIDADE GRUPOS",
    title: "Viabilidade Grupos",
    subtitle: "Selecao de grupos apos administradoras elegiveis",
    action: "Analisar Viabilidade",
  },
  administradoras: {
    letter: "C) ADMINISTRADORAS",
    title: "Administradoras",
    subtitle: "Planos por administradora para imoveis e automoveis",
    action: "Salvar Administradoras",
  },
  estudo: {
    letter: "E) ESTUDO FINANCEIRO",
    title: "Estudo Financeiro",
    subtitle: "Geracao do estudo financeiro detalhado",
    action: "Salvar Estudo",
  },
  historico: {
    letter: "F) HISTORICO DE ESTUDOS",
    title: "Historico de Estudos",
    subtitle: "Consulta e gestao dos estudos financeiros gerados",
    action: "Buscar Estudos",
  },
  configuracoes: {
    letter: "G) CONFIGURACOES",
    title: "Configuracoes",
    subtitle: "Configuracoes do sistema e preferencias",
    action: "Salvar Configuracoes",
  },
};

const mapState = {
  page: 1,
  pageSize: 25,
  total: 0,
  items: [],
  administradoras: [],
  lastLoadAt: null,
};

const viabilityState = {
  lastResult: null,
};

const historyState = {
  items: [],
};

const configState = {
  data: null,
};

const operationalLogs = [];
const HISTORY_START_MONTH = "2024-01";
const CLIENT_PROFILE_STORAGE_KEY = "crediclass.clientProfile.v1";
const authState = { user: null };
let appBootstrapped = false;
const administratorPlanDefaultNames = ["AUTO-CAIXA", "AUTO-CAOA", "AUTO-ITAU", "CAIXA", "CANOPUS", "CAOA", "ITAU", "PORTO", "RODOBENS"];
const administratorPlanRows = [
  { key: "data_cadastro_produto", label: "Data de cadastro do produto", type: "date" },
  { key: "responsavel_cadastro_produto", label: "Responsável pelo cadastro do produto", type: "text" },
  { key: "seguro_obrigatorio_texto", label: "Tem Seguro obrigatório?", type: "text" },
  { key: "idade_maxima", label: "Qual é a idade máxima (seguro obrigatório)", type: "text" },
  { key: "limite_sem_comprovacao_renda", label: "Limite adesão sem comprovação de renda", type: "money" },
  { key: "percentual_lance_embutido", label: "% de lance embutido", type: "percent" },
  { key: "tipo_lance_embutido", label: "Calculo do lance embutido", type: "text" },
  { key: "tem_furo_no_grupo", label: "Tem furo no grupo", type: "percent" },
  { key: "aceita_saida_fiscal_texto", label: "Aceita adesão de clientes com saída fiscal?", type: "text" },
  { key: "taxa_adm", label: "Taxa Administração", type: "percent" },
  { key: "possui_negociacao_taxa", label: "Tem negociação de Taxa?", type: "text" },
  { key: "fundo_reserva", label: "Fundo de reserva", type: "percent" },
  { key: "idade_maxima_ok", label: "Idade máxima ok?", type: "text" },
  { key: "credito_a_ser_contratado", label: "Crédito a ser contratado:", type: "money" },
  { key: "lance_embutido_valor", label: "Lance embutido (R$):", type: "money" },
  { key: "lance_proprio_usado", label: "Lance proprio usado:", type: "money" },
  { key: "lance_total_considerado", label: "Lance total considerado:", type: "money" },
  { key: "lance_maximo", label: "Lance máximo:", type: "percent" },
  { key: "taxa_administracao_valor", label: "Taxa Administracao (R$):", type: "money" },
  { key: "fundo_reserva_valor", label: "Fundo de reserva (R$):", type: "money" },
  { key: "prazo_minimo", label: "Prazo mínimo:", type: "number" },
];
const administratorPlanComputedFields = [
  "credito_a_ser_contratado",
  "lance_embutido_valor",
  "lance_proprio_usado",
  "lance_total_considerado",
  "lance_maximo",
  "taxa_administracao_valor",
  "fundo_reserva_valor",
  "prazo_minimo",
];
const businessRuleStatuses = ["Pendente", "Em revisao", "Revisado", "Corrigir regra"];
const administratorPlanRuleHelp = {
  seguro_obrigatorio_texto: "Usado na etapa de Administradoras para sinalizar se o cliente precisa cumprir regra de seguro obrigatorio antes da escolha de grupos.",
  idade_maxima: "Usado na validacao de idade da administradora. Se houver idade do titular ou conjuge, o sistema compara com esse limite.",
  limite_sem_comprovacao_renda: "Usado como referencia de regra da administradora para saber quando a operacao pode exigir comprovacao de renda.",
  percentual_lance_embutido: "Usado nas formulas oficiais: credito a contratar = credito desejado / (1 - percentual de lance embutido); lance maximo; e prazo minimo.",
  tipo_lance_embutido: "Usado para indicar como a administradora calcula o lance embutido, por exemplo sobre Credito. Orienta a revisao humana da regra.",
  aceita_saida_fiscal_texto: "Usado como regra operacional da administradora para validar se o perfil do cliente pode aderir com saida fiscal quando esse ponto for relevante.",
  taxa_adm: "Usada na formula de prazo minimo e parcela estimada. Taxa ADM em valor = credito a contratar * taxa administrativa.",
  fundo_reserva: "Usado na formula de prazo minimo e parcela estimada. Fundo de reserva em valor = credito a contratar * fundo reserva.",
  idade_maxima_ok: "Linha de conferencia da regra de idade. Ajuda o operador a validar se a idade do cliente esta dentro do limite da administradora.",
  credito_a_ser_contratado: "Campo calculado pela formula oficial F29: credito desejado / (1 - percentual de lance embutido).",
  lance_embutido_valor: "Valor calculado do lance embutido: credito a contratar * percentual de lance embutido.",
  lance_proprio_usado: "Valor do Perfil do Cliente usado nas formulas oficiais como lance maximo disponivel. FGTS nao entra nas formulas F30 e F31.",
  lance_total_considerado: "Lance total usado nas formulas F30 e F31: lance embutido em R$ + lance proprio disponivel.",
  lance_maximo: "Campo calculado pela formula oficial F30: ((credito a contratar * percentual de lance embutido) + lance proprio disponivel) / credito a contratar.",
  taxa_administracao_valor: "Valor calculado da taxa administrativa: credito a contratar * taxa administrativa da administradora.",
  fundo_reserva_valor: "Valor calculado do fundo de reserva: credito a contratar * fundo de reserva da administradora.",
  prazo_minimo: "Campo calculado pela formula oficial F31: (credito a contratar + taxa ADM + fundo reserva - lance total considerado) / parcela limite.",
};
const businessRulesFlow = [
  {
    id: "perfil-cliente",
    etapa: "1. Perfil do Cliente",
    regras: [
      "Recebe credito desejado liquido, prazo desejado, objetivo, tipo de bem e estado do bem. Exemplo: cliente quer R$ 450.000 liquidos para aquisicao de imovel pronto em 1 a 3 meses.",
      "Soma recursos proprios com FGTS apenas para exibir total disponivel do cliente. Exemplo: R$ 150.000 de lance proprio + R$ 100.000 de FGTS = R$ 250.000 exibidos como total disponivel.",
      "Soma renda titular e renda conjuge para renda total. Exemplo: titular R$ 8.000 + conjuge R$ 7.000 = renda total R$ 15.000.",
      "Calcula Conceito IA pelo prazo. Exemplo: 1 a 3 meses = Agressivo; 4 a 6 = Moderado; 7 a 12 = Conservador; 13 a 24 = Super Conservador; sem urgencia = Investidor.",
      "Data de nascimento valida idade minima de 18 anos na adesao. Exemplo: titular com 17 anos reprova a compatibilidade de idade.",
      "Quando a administradora tiver idade maxima cadastrada, o sistema calcula a idade do cliente na data de termino do grupo (coluna H do Google Sheets). Exemplo: nascido em 07/10/1978 e grupo terminando em 20/05/2060 = 81 anos no termino; com limite 80 anos, o grupo e excluido.",
      "Se a data de nascimento estiver ausente, o sistema gera alerta de idade nao validada, sem aprovar idade automaticamente. Se a administradora nao tiver idade maxima cadastrada, a validacao de idade no termino nao bloqueia o grupo.",
    ],
  },
  {
    id: "administradoras",
    etapa: "2. Administradoras",
    regras: [
      "Regras fixas por administradora sao usadas antes da selecao de grupos. Exemplo: CNP permite 50% de lance embutido, taxa ADM 15% e fundo reserva 5%.",
      "Credito a contratar = credito desejado / (1 - percentual de lance embutido). Exemplo: R$ 450.000 / (1 - 50%) = R$ 900.000.",
      "Lance maximo = ((credito a contratar * percentual de lance embutido) + lance proprio disponivel) / credito a contratar. Exemplo: ((R$ 900.000 * 50%) + R$ 150.000) / R$ 900.000 = 66,6667%.",
      "Prazo minimo = (credito a contratar + taxa ADM + fundo reserva - lance total considerado) / parcela limite. Exemplo: (R$ 900.000 + R$ 135.000 + R$ 45.000 - R$ 600.000) / R$ 6.000 = 80 meses.",
      "Nas formulas oficiais F30 e F31 nao entra FGTS; entra o lance proprio disponivel. Exemplo: mesmo com R$ 100.000 de FGTS informado, a formula usa R$ 150.000 de lance proprio.",
    ],
  },
  {
    id: "viabilidade-grupos",
    etapa: "3. Viabilidade de Grupos",
    regras: [
      "Busca somente grupos ativos e com tipo de bem compativel. Exemplo: cliente quer Imovel, entao grupo de Automovel nao entra na lista.",
      "Valida faixa do grupo usando credito a contratar, nao o credito liquido desejado. Exemplo: se o credito contratado calculado e R$ 900.000, um grupo com credito maximo R$ 800.000 nao serve.",
      "Valida prazo restante do grupo contra o prazo minimo calculado pela formula oficial. Exemplo: prazo minimo 80 meses; grupo com 62 meses restantes nao atende.",
      "Referencia de lance usa meses com contemplacao registrada no historico. Exemplo: se nos ultimos 6 meses apenas 1 mes teve contemplacao, o sistema marca historico insuficiente para perfil Moderado.",
      "Faixas do perfil: Agressivo 50%+; Moderado 40% a 50%; Conservador 30% a 40%; Super Conservador 20% a 30%; Investidor 0% a 20%. Exemplo: perfil Conservador espera referencia entre 30% e 40%.",
    ],
  },
  {
    id: "estrategias",
    etapa: "4. Estrategias",
    regras: [
      "Estrategia recomendada parte do perfil e do grupo selecionado na Viabilidade. Exemplo: perfil Moderado prioriza grupos com referencia operacional de 4 a 6 meses.",
      "Alternativas de lance sao comparadas sem alterar os dados originais do cliente. Exemplo: operador pode comparar Lance Conservador e Lance Moderado mantendo o mesmo credito desejado de R$ 450.000.",
      "A recomendacao deve explicar historico, prazo operacional, lance sugerido e riscos. Exemplo: informar que o grupo teve 2 contemplacoes em 6 meses, mas que a analise nao garante contemplacao.",
    ],
  },
  {
    id: "estudo-financeiro",
    etapa: "5. Estudo Financeiro",
    regras: [
      "Estudo herda Perfil do Cliente, grupo selecionado e estrategia escolhida. Exemplo: cliente R$ 450.000, grupo CNP 123 e estrategia Moderada seguem para o estudo.",
      "Simulacao financeira usa credito contratado, lance embutido, recurso proprio, taxa ADM, fundo reserva e prazo. Exemplo: R$ 900.000 contratado, R$ 450.000 embutido, R$ 150.000 proprio, taxa 15%, fundo 5% e prazo minimo 80 meses.",
      "Campos comerciais permanecem editaveis pelo operador antes de salvar/compartilhar o estudo. Exemplo: operador pode escrever observacoes comerciais e comentario ao cliente.",
      "A analise nao garante contemplacao; serve como referencia operacional. Exemplo: mesmo com lance maximo de 66,6667%, o estudo deve informar que a assembleia pode variar.",
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
let currentDetailsGroupId = null;
let studyDetailsModal = null;
let currentStudyStrategies = [];
let currentStudyStrategyTab = "";
let configUserModal = null;
let configUserMode = "create";
let configUserIndex = null;
let configAdministratorRuleIndex = null;
let viabilityAuditModal = null;

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

function isNotificationEnabled(key) {
  const settings = configState.data?.notificacoes || {};
  return settings[key] !== false;
}

function notifyWhen(key, message, type = "success") {
  if (isNotificationEnabled(key)) showToast(message, type);
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
  document.getElementById("primaryAction").textContent = meta.action;
  document.getElementById("reloadMapDataBtn").classList.toggle("d-none", screenName !== "mapa");

  if (screenName === "historico") {
    loadHistoryStudies();
  }
  if (screenName === "administradoras") {
    loadConfiguracoes();
  }
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
    minimumFractionDigits: 0,
    maximumFractionDigits: 3,
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
  button.disabled = true;
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
    button.disabled = false;
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
  const credito = items.reduce((sum, item) => {
    const value = Number(item.credito_maximo || 0);
    return Number.isFinite(value) && value <= 100000000 ? sum + value : sum;
  }, 0);
  const taxas = items.map((item) => item.taxa_adm).filter((value) => value !== null && value !== undefined);
  const taxaMedia = taxas.length ? taxas.reduce((sum, value) => sum + value, 0) / taxas.length : null;

  document.getElementById("summaryTotal").textContent = total;
  document.getElementById("summaryAdministradoras").textContent = totalAdministradoras ?? administradoras.size;
  document.getElementById("summaryCredito").textContent = formatMoney(credito);
  document.getElementById("summaryTaxa").textContent = formatPercent(taxaMedia);
  document.getElementById("summaryUpdated").textContent = mapState.lastLoadAt || "--";
}

function renderGroupsTable(items) {
  const tbody = document.getElementById("groupsTableBody");
  tbody.innerHTML = items.map((item) => {
    const inactive = String(item.status || "").toLowerCase() === "excluido";
    return `
      <tr>
        <td>${escapeHtml(item.grupo_id)}</td>
        <td>${escapeHtml(item.administradora)}</td>
        <td>${escapeHtml(item.tipo_bem)}</td>
        <td>${formatMoney(item.credito_minimo)}</td>
        <td>${formatMoney(item.credito_maximo)}</td>
        <td>${formatPercent(item.taxa_adm)}</td>
        <td>${item.prazo_total ?? "-"}</td>
        <td>${escapeHtml(item.primeira_assembleia || "-")}</td>
        <td>${escapeHtml(item.ultima_assembleia || "-")}</td>
        <td><span class="status-badge ${inactive ? "inactive" : ""}">${escapeHtml(item.status)}</span></td>
        <td>
          <div class="row-actions">
            <button class="btn btn-sm btn-outline-primary" type="button" data-map-action="visualizar" data-group-id="${escapeHtml(item.grupo_id)}">Ver</button>
            <button class="btn btn-sm btn-outline-secondary" type="button" data-map-action="editar" data-group-id="${escapeHtml(item.grupo_id)}">Editar</button>
            <button class="btn btn-sm btn-outline-secondary" type="button" data-map-action="duplicar" data-group-id="${escapeHtml(item.grupo_id)}">Duplicar</button>
            <button class="btn btn-sm btn-outline-danger" type="button" data-map-action="excluir" data-group-id="${escapeHtml(item.grupo_id)}">Excluir</button>
          </div>
        </td>
      </tr>
    `;
  }).join("");
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
  notifyWhen("alertar_historico_atualizado", "Historico mensal atualizado na Google Sheets.", "success");
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
  document.getElementById("groupFormAdministradora").value = group.administradora || "";
  document.getElementById("groupFormGrupo").value = group.grupo || "";
  document.getElementById("groupFormTipoBem").value = group.tipo_bem || "";
  setMoneyInputValue("groupFormCreditoMinimo", group.credito_minimo);
  setMoneyInputValue("groupFormCreditoMaximo", group.credito_maximo);
  document.getElementById("groupFormTaxaAdm").value = percentToInputValue(group.taxa_adm);
  document.getElementById("groupFormPrazoTotal").value = group.prazo_total ?? "";
  document.getElementById("groupFormStatus").value = group.status || "Ativo";
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
    notifyWhen("alertar_historico_atualizado", "Historico mensal atualizado na Google Sheets.", "success");
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
    if (document.getElementById("screen-administradoras")?.classList.contains("active") && configState.data) {
      renderAdministratorPlans();
    }
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
  if (prazo <= 3) return "Agressivo";
  if (prazo <= 6) return "Moderado";
  if (prazo <= 12) return "Conservador";
  if (prazo <= 24) return "Super Conservador";
  return "Investidor";
}

function updateClientProfileTotals() {
  const fgts = toNumber(document.getElementById("clientProfileFgtsTitular").value) + toNumber(document.getElementById("clientProfileFgtsConjuge").value);
  const lance = toNumber(document.getElementById("clientProfileLanceProprio").value);
  const renda = toNumber(document.getElementById("clientProfileRendaTitular").value) + toNumber(document.getElementById("clientProfileRendaConjuge").value);
  const conceito = clientProfileConcept(document.getElementById("clientProfilePrazo").value);
  document.getElementById("clientProfileFgtsTotal").value = formatMoney(fgts);
  document.getElementById("clientProfileTotalDisponivel").value = formatMoney(lance + fgts);
  document.getElementById("clientProfileRendaTotal").value = formatMoney(renda);
  document.getElementById("clientProfileConceito").value = conceito;
  renderClientProfileSummary({ fgts, lance, renda, conceito });
  return { fgts, lance, renda, conceito };
}

function collectClientProfile() {
  const totals = updateClientProfileTotals();
  return {
    nome: document.getElementById("clientProfileNome").value.trim(),
    nome_conjuge: document.getElementById("clientProfileConjuge").value.trim(),
    credito_desejado: toNumber(document.getElementById("clientProfileCredito").value),
    prazo_desejado: Number(document.getElementById("clientProfilePrazo").value),
    conceito_ia: totals.conceito,
    lance_proprio: toNumber(document.getElementById("clientProfileLanceProprio").value),
    fgts_titular: toNumber(document.getElementById("clientProfileFgtsTitular").value),
    fgts_conjuge: toNumber(document.getElementById("clientProfileFgtsConjuge").value),
    fgts: totals.fgts,
    renda_titular: toNumber(document.getElementById("clientProfileRendaTitular").value),
    renda_conjuge: toNumber(document.getElementById("clientProfileRendaConjuge").value),
    renda_total: totals.renda,
    parcela_ideal: toNumber(document.getElementById("clientProfileParcelaIdeal").value),
    parcela_limite: toNumber(document.getElementById("clientProfileParcelaLimite").value),
    parcela_desejada: toNumber(document.getElementById("clientProfileParcelaIdeal").value),
    data_nascimento: document.getElementById("clientProfileNascimento").value,
    data_nascimento_conjuge: document.getElementById("clientProfileNascimentoConjuge").value,
    objetivo: document.getElementById("clientProfileObjetivo").value,
    tipo_bem: document.getElementById("clientProfileTipoBem").value,
    estado_bem: document.getElementById("clientProfileEstadoBem").value,
  };
}

function renderClientProfileSummary(totals = null) {
  const current = totals || updateClientProfileTotals();
  document.getElementById("clientProfileSummary").innerHTML = [
    ["Conceito IA", current.conceito],
    ["Credito desejado", formatMoney(toNumber(document.getElementById("clientProfileCredito").value))],
    ["Recursos proprios", formatMoney(current.lance)],
    ["FGTS total", formatMoney(current.fgts)],
    ["Renda total", formatMoney(current.renda)],
    ["Parcela ideal", formatMoney(toNumber(document.getElementById("clientProfileParcelaIdeal").value))],
    ["Parcela limite", formatMoney(toNumber(document.getElementById("clientProfileParcelaLimite").value))],
  ].map(([label, value]) => `<div><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`).join("");
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
    updateClientProfileTotals();
    return;
  }
  setInputValue("clientProfileNome", profile.nome);
  setInputValue("clientProfileConjuge", profile.nome_conjuge);
  setMoneyInputValue("clientProfileCredito", profile.credito_desejado);
  setInputValue("clientProfilePrazo", profile.prazo_desejado || 3);
  setMoneyInputValue("clientProfileLanceProprio", profile.lance_proprio);
  setMoneyInputValue("clientProfileFgtsTitular", profile.fgts_titular);
  setMoneyInputValue("clientProfileFgtsConjuge", profile.fgts_conjuge);
  setMoneyInputValue("clientProfileRendaTitular", profile.renda_titular);
  setMoneyInputValue("clientProfileRendaConjuge", profile.renda_conjuge);
  setMoneyInputValue("clientProfileParcelaIdeal", profile.parcela_ideal ?? profile.parcela_desejada);
  setMoneyInputValue("clientProfileParcelaLimite", profile.parcela_limite);
  setInputValue("clientProfileNascimento", profile.data_nascimento);
  setInputValue("clientProfileNascimentoConjuge", profile.data_nascimento_conjuge);
  setInputValue("clientProfileObjetivo", profile.objetivo || "Aquisicao de Imovel");
  setInputValue("clientProfileTipoBem", profile.tipo_bem || "Imovel");
  setInputValue("clientProfileEstadoBem", profile.estado_bem || "Pronto");
  updateClientProfileTotals();
  applyClientProfileToFlow(collectClientProfile());
}

function resetClientProfile() {
  document.getElementById("clientProfileForm").reset();
  window.localStorage.removeItem(CLIENT_PROFILE_STORAGE_KEY);
  updateClientProfileTotals();
  showToast("Perfil do cliente limpo.", "success");
}

function advanceClientProfile() {
  saveClientProfile({ silent: true });
  activateScreen("administradoras");
}

function setViabilityState(state) {
  document.getElementById("viabilityLoading").classList.toggle("d-none", state !== "loading");
  document.getElementById("viabilityError").classList.toggle("d-none", state !== "error");
  document.getElementById("viabilityEmpty").classList.toggle("d-none", state !== "empty");
  document.getElementById("viabilityResults").classList.toggle("d-none", !["ready", "empty"].includes(state));
  const button = document.getElementById("analyzeViabilityBtn");
  button.disabled = state === "loading";
  button.textContent = state === "loading" ? "Analisando..." : "Analisar Viabilidade";
}

function collectViabilityPayload() {
  const profile = collectClientProfile();
  return {
    objetivo: profile.objetivo,
    credito_desejado: profile.credito_desejado,
    prazo_desejado: profile.prazo_desejado,
    lance_proprio: profile.lance_proprio,
    fgts: profile.fgts,
    fgts_titular: profile.fgts_titular,
    fgts_conjuge: profile.fgts_conjuge,
    renda_total: profile.renda_total,
    renda_titular: profile.renda_titular,
    renda_conjuge: profile.renda_conjuge,
    parcela_desejada: profile.parcela_ideal,
    parcela_ideal: profile.parcela_ideal,
    parcela_limite: profile.parcela_limite || profile.parcela_ideal,
    data_nascimento: profile.data_nascimento,
    data_nascimento_conjuge: profile.data_nascimento_conjuge,
    tipo_bem: profile.tipo_bem,
    estado_bem: profile.estado_bem,
  };
}

function validateViabilityPayload(payload) {
  const required = [
    ["credito_desejado", "Informe o credito desejado."],
    ["prazo_desejado", "Informe o prazo desejado."],
    ["renda_total", "Informe a renda total."],
    ["parcela_desejada", "Informe a parcela ideal."],
    ["parcela_limite", "Informe a parcela limite."],
  ];
  const missing = required.find(([key]) => !payload[key]);
  if (missing) {
    showToast(missing[1], "warning");
    return false;
  }
  if (!Number.isFinite(payload.lance_proprio) || payload.lance_proprio < 0) {
    showToast("Informe um lance proprio igual ou maior que zero.", "warning");
    return false;
  }
  return true;
}

function renderViabilityChecklist(checklist) {
  if (!document.getElementById("viabilityChecklist")) return;
  document.querySelectorAll("#viabilityChecklist li").forEach((item) => {
    const value = checklist?.[item.dataset.check];
    item.classList.toggle("check-ok", value === true);
    item.classList.toggle("check-fail", value === false);
  });
}

function renderViabilitySummary(result) {
  const items = result.melhores_grupos || [];
  document.getElementById("viabilityRankingSubtitle").textContent = `${items.length} grupo(s) candidato(s) - perfil ${result.perfil}`;
  const scenario = document.getElementById("viabilityScenario");
  if (scenario) scenario.textContent = `${result.cenario} - perfil ${result.perfil}`;
}

function renderViabilityEmpty(result) {
  const empty = document.getElementById("viabilityEmpty");
  const reasons = result?.motivos_reprovacao || [];
  if (reasons.includes("regras_administradoras_pendentes_analise_humana")) {
    empty.textContent = "Nenhum grupo passou nos filtros basicos do perfil. As regras das administradoras pendentes nao bloquearam a busca.";
    return;
  }
  empty.textContent = "Nenhum grupo compativel encontrado para este cenario.";
}

function viabilityAuditStatus(item) {
  const motivos = item.motivos || [];
  const alertas = item.alertas || [];
  const hasFailure = motivos.some((motivo) => /acima|abaixo|fora|sem historico/i.test(motivo));
  if (alertas.includes("regras_administradoras_pendentes_analise_humana")) return "preliminar";
  if (hasFailure || alertas.length) return "alerta";
  return "ok";
}

function auditStatusLabel(status) {
  if (status === "ok") return "Conforme";
  if (status === "preliminar") return "Analise preliminar";
  return "Revisar";
}

function auditStatusClass(status) {
  if (status === "ok") return "audit-ok";
  if (status === "preliminar") return "audit-warning";
  return "audit-danger";
}

function formatAuditToken(value) {
  return String(value || "").replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function auditRow(label, value, status = "ok", detail = "") {
  return `
    <tr>
      <td>${escapeHtml(label)}</td>
      <td>${escapeHtml(value)}</td>
      <td><span class="audit-status ${auditStatusClass(status)}">${escapeHtml(auditStatusLabel(status))}</span></td>
      <td>${escapeHtml(detail || "-")}</td>
    </tr>
  `;
}

function auditList(title, items) {
  const list = items?.length
    ? items.map((item) => `<li>${escapeHtml(formatAuditToken(item))}</li>`).join("")
    : "<li>Nenhum item registrado.</li>";
  return `
    <section class="audit-panel">
      <h3>${escapeHtml(title)}</h3>
      <ul class="audit-list-compact">${list}</ul>
    </section>
  `;
}

function ensureViabilityAuditModal() {
  let modal = document.getElementById("viabilityAuditModal");
  if (!modal) {
    document.body.insertAdjacentHTML("beforeend", `
      <div class="modal fade" id="viabilityAuditModal" tabindex="-1" aria-hidden="true">
        <div class="modal-dialog modal-xl modal-dialog-scrollable">
          <div class="modal-content">
            <div class="modal-header">
              <div>
                <h2 id="viabilityAuditTitle" class="modal-title h5">Auditoria da Viabilidade</h2>
                <p id="viabilityAuditSubtitle" class="modal-subtitle">Conferencia das regras aplicadas ao grupo</p>
              </div>
              <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Fechar"></button>
            </div>
            <div class="modal-body"><div id="viabilityAuditContent"></div></div>
            <div class="modal-footer"><button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Fechar</button></div>
          </div>
        </div>
      </div>
    `);
    modal = document.getElementById("viabilityAuditModal");
  }
  if (!viabilityAuditModal) viabilityAuditModal = new bootstrap.Modal(modal);
  return viabilityAuditModal;
}

function openViabilityAudit(groupId) {
  const item = viabilityState.lastResult?.melhores_grupos?.find((group) => group.grupo_id === groupId);
  if (!item) {
    showToast("Execute a Viabilidade antes de auditar o grupo.", "warning");
    return;
  }
  const modal = ensureViabilityAuditModal();
  const payload = collectViabilityPayload();
  const status = viabilityAuditStatus(item);
  const creditoOk = (item.credito_contratado || 0) >= (item.credito_minimo || 0) && (item.credito_contratado || 0) <= (item.credito_maximo || 0);
  const parcelaReferencia = payload.parcela_limite || payload.parcela_desejada || 0;
  const parcelaOk = (item.parcela_estimada || 0) <= parcelaReferencia;
  const prazoOk = (item.prazo || 0) >= (item.prazo_minimo || 0);
  const hasLanceHistory = item.lance_referencia_percentual !== null && item.lance_referencia_percentual !== undefined;
  const lanceOk = hasLanceHistory && (item.percentual_lance || 0) >= (item.lance_referencia_percentual || 0);

  document.getElementById("viabilityAuditTitle").textContent = `Auditoria do Grupo ${item.grupo}`;
  document.getElementById("viabilityAuditSubtitle").textContent = `${item.administradora} - ${item.tipo_bem} - ${auditStatusLabel(status)}`;
  document.getElementById("viabilityAuditContent").innerHTML = `
    <div class="audit-summary ${auditStatusClass(status)}">
      <strong>${escapeHtml(auditStatusLabel(status))}</strong>
      <span>${status === "preliminar" ? "Este grupo entrou como candidato porque as regras das administradoras ainda exigem revisao humana." : "Conferencia dos criterios calculados para este grupo."}</span>
    </div>
    <section class="audit-panel">
      <h3>Conferencia dos Requisitos</h3>
      <div class="table-responsive">
        <table class="table table-hover align-middle audit-table">
          <thead><tr><th>Criterio</th><th>Resultado</th><th>Status</th><th>Observacao</th></tr></thead>
          <tbody>
            ${auditRow("Status do grupo", "Ativo", "ok", "Somente grupos ativos entram na busca.")}
            ${auditRow("Tipo de bem", item.tipo_bem || "-", "ok", `Perfil solicitou ${payload.tipo_bem || "-"}.`)}
            ${auditRow("Faixa de credito", `${formatMoney(item.credito_minimo)} ate ${formatMoney(item.credito_maximo)}`, creditoOk ? "ok" : "alerta", `Credito a contratar: ${formatMoney(item.credito_contratado)}.`)}
            ${auditRow("Prazo", `${item.prazo} meses restantes`, prazoOk ? "ok" : "alerta", `Prazo minimo calculado: ${Number(item.prazo_minimo || 0).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} meses.`)}
            ${auditRow("Parcela", formatMoney(item.parcela_estimada), parcelaOk ? "ok" : "alerta", `Parcela de referencia: ${formatMoney(parcelaReferencia)}.`)}
            ${auditRow("Lance historico", hasLanceHistory ? formatPercent(item.lance_referencia_percentual) : "Sem historico suficiente", lanceOk ? "ok" : "alerta", `Lance maximo calculado do cliente: ${formatPercent(item.percentual_lance)}.`)}
            ${auditRow("Taxa ADM", formatPercent(item.taxa_adm), "ok", `Valor aplicado: ${formatMoney(item.taxa_administrativa_valor)}.`)}
            ${auditRow("Fundo reserva", formatPercent(item.fundo_reserva), item.fundo_reserva >= 1 ? "alerta" : "ok", `Valor aplicado: ${formatMoney(item.fundo_reserva_valor)}.`)}
          </tbody>
        </table>
      </div>
    </section>
    <div class="audit-grid">
      ${auditList("Motivos registrados pelo motor", item.motivos || [])}
      ${auditList("Alertas de conformidade", item.alertas || [])}
    </div>
  `;
  modal.show();
}

function renderViabilityRanking(items) {
  document.getElementById("viabilityRankingBody").innerHTML = items.map((item) => `
    <tr>
      <td>${item.ranking}</td>
      <td>${escapeHtml(item.administradora)}</td>
      <td>${escapeHtml(item.grupo)}</td>
      <td>${escapeHtml(item.tipo_bem)}</td>
      <td>${formatMoney(item.credito_minimo)}</td>
      <td>${formatMoney(item.credito_maximo)}</td>
      <td>${formatMoney(item.credito_contratado)}</td>
      <td>${item.prazo} meses</td>
      <td>${Number(item.prazo_minimo || 0).toLocaleString("pt-BR", { maximumFractionDigits: 1 })}</td>
      <td>${formatPercent(item.taxa_adm)}</td>
      <td>${formatPercent(item.fundo_reserva)}</td>
      <td>${formatMoney(item.parcela_estimada)}</td>
      <td><span class="audit-status ${auditStatusClass(viabilityAuditStatus(item))}">${escapeHtml(auditStatusLabel(viabilityAuditStatus(item)))}</span></td>
      <td>
        <div class="row-actions">
          <button class="btn btn-sm btn-outline-primary" type="button" data-viability-action="auditar" data-group-id="${escapeHtml(item.grupo_id)}">Auditar</button>
          <button class="btn btn-sm btn-outline-primary" type="button" data-viability-action="visualizar" data-group-id="${escapeHtml(item.grupo_id)}">Ver detalhes</button>
          <button class="btn btn-sm btn-outline-secondary" type="button" data-viability-action="estrategias" data-group-id="${escapeHtml(item.grupo_id)}">Selecionar</button>
        </div>
      </td>
    </tr>
  `).join("");
}

async function analyzeViability() {
  const payload = collectViabilityPayload();
  if (!validateViabilityPayload(payload)) return;

  setViabilityState("loading");
  try {
    const result = await apiPost("/viabilidade/analisar", payload);
    viabilityState.lastResult = result;
    renderViabilityChecklist(result.checklist);
    renderViabilitySummary(result);
    if (!result.melhores_grupos.length) {
      renderViabilityEmpty(result);
      setViabilityState("empty");
      return;
    }
    renderViabilityRanking(result.melhores_grupos);
    setViabilityState("ready");
    showToast("Analise de viabilidade concluida.", "success");
  } catch (error) {
    setViabilityState("error");
  }
}

function resetViabilityForm() {
  renderViabilityChecklist({});
  const scenario = document.getElementById("viabilityScenario");
  if (scenario) scenario.textContent = "Aguardando analise";
  document.getElementById("viabilityRankingBody").innerHTML = "";
  setViabilityState("idle");
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
  const payload = collectViabilityPayload();
  currentStudy = { groupId, viabilityItem, payload, group: null, templateCampos: {} };
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
    showToast("Selecione um grupo na Viabilidade antes de salvar.", "warning");
    return null;
  }
  const payload = {
    cliente: {
      nome: "Cliente em estudo",
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
    template_campos: collectStudyOperatorFields(),
  };
  const result = await apiPost("/estudos", payload);
  currentStudy.savedStudyId = result.estudo_id;
  document.getElementById("studyDisplayId").textContent = result.estudo_id;
  notifyWhen("alertar_estudo_salvo", `Estudo salvo: ${result.estudo_id}`, "success");
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
    showToast("Selecione um grupo na Viabilidade antes de compartilhar.", "warning");
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

function collectBusinessRuleFeedbacks() {
  const result = {};
  businessRulesFlow.forEach((rule) => {
    const note = document.querySelector(`[data-business-rule-note="${rule.id}"]`)?.value.trim() || "";
    const status = document.querySelector(`[data-business-rule-status="${rule.id}"]`)?.value || "Pendente";
    result[rule.id] = { observacao: note, status };
  });
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
  const empresa = data.empresa || {};
  const pref = data.preferencias || {};
  const params = data.parametros_financeiros || {};
  const integracoes = data.integracoes || {};
  const notificacoes = data.notificacoes || {};
  const sistema = data.sistema || {};

  setInputValue("configEmpresaNome", empresa.nome);
  setInputValue("configEmpresaCnpj", empresa.cnpj);
  setInputValue("configEmpresaEmail", empresa.email);
  setInputValue("configEmpresaTelefone", empresa.telefone);
  setInputValue("configEmpresaEndereco", empresa.endereco);
  setInputValue("configEmpresaLogo", empresa.logo);
  setInputValue("configMoeda", pref.moeda);
  setInputValue("configFormatoData", pref.formato_data);
  setInputValue("configTema", pref.tema);
  applyTheme(pref.tema);
  setInputValue("configIdioma", pref.idioma);
  setInputValue("configCasasValores", pref.casas_decimais_valores);
  setInputValue("configCasasPercentuais", pref.casas_decimais_percentuais);
  setInputValue("configAtualizacaoMinutos", pref.atualizacao_automatica_minutos);
  setSelectBool("configMeiaParcela", pref.ativar_meia_parcela);
  setSelectBool("configLanceEmbutido", pref.ativar_lance_embutido);
  setSelectBool("configHistorico36", pref.exibir_historico_36_meses);
  setSelectBool("notifySync", notificacoes.alertar_sincronizacao);
  setSelectBool("notifyStudySaved", notificacoes.alertar_estudo_salvo);
  setSelectBool("notifyHistoryUpdated", notificacoes.alertar_historico_atualizado);
  setSelectBool("notifyIntegrationFailure", notificacoes.alertar_falha_integracao);
  setSelectBool("integrationGoogleSheetsToggle", integracoes.google_sheets);
  setSelectBool("integrationPiperunToggle", integracoes.piperun_crm);
  setSelectBool("integrationEmailToggle", integracoes.email_smtp);
  setSelectBool("integrationBackupToggle", integracoes.backup_automatico);

  setInputValue("configTaxaAdm", percentToInput(params.taxa_administracao_padrao));
  setInputValue("configFundoReserva", percentToInput(params.fundo_reserva_padrao));
  setInputValue("configLanceFixo", percentToInput(params.percentual_lance_fixo_padrao));
  setInputValue("configLanceModerado", percentToInput(params.percentual_lance_moderado_padrao));
  setInputValue("configLanceAgressivo", percentToInput(params.percentual_lance_agressivo_padrao));
  setInputValue("configPrazoMaximo", params.prazo_maximo);
  setInputValue("configPrazoMinimo", params.prazo_minimo);
  setInputValue("configIndiceCorrecao", params.indice_correcao_anual);

  document.getElementById("integrationSheets").textContent = sistema.google_sheets_configurado && integracoes.google_sheets ? "Ativo" : "Pendente";
  document.getElementById("integrationPiperun").textContent = integracoes.piperun_crm ? "Ativo" : "Inativo";
  document.getElementById("integrationEmail").textContent = integracoes.email_smtp ? "Ativo" : "Inativo";
  document.getElementById("integrationBackup").textContent = integracoes.backup_automatico ? "Ativo" : "Inativo";
  document.getElementById("integrationSheetName").textContent = sistema.google_sheet_name || "-";

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

  renderAccessPolicy(data.acesso || {});
  renderBusinessRules(data.regras_negocio_feedbacks || {});
  renderAdministratorRules(data.administradoras_regras || []);
  renderAdministratorPlans();
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

function renderAccessPolicy(acesso) {
  document.getElementById("configAccessGrid").innerHTML = [
    ["Paineis", acesso.paineis_liberados ? "Liberados para todos" : "Restritos"],
    ["Dados", "Todos podem visualizar os dados dos paineis"],
    ["Observacao", acesso.descricao || "-"],
  ].map(([label, value]) => detailField(label, value)).join("");
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
      <td>${rule.seguro_obrigatorio ? "Sim" : "Nao"}</td>
      <td>${rule.idade_maxima || "-"}</td>
      <td>${formatMoney(rule.limite_sem_comprovacao_renda)}</td>
      <td>${formatPercent(rule.percentual_lance_embutido || 0)}</td>
      <td>${rule.aceita_saida_fiscal ? "Sim" : "Nao"}</td>
      <td>${formatPercent(rule.taxa_adm || 0)}</td>
      <td>${formatPercent(rule.fundo_reserva || 0)}</td>
      <td>${rule.aceita_fgts === false ? "Nao" : "Sim"}</td>
      <td>
        <div class="row-actions">
          <button class="btn btn-sm btn-outline-secondary" type="button" data-admin-rule-action="editar" data-admin-rule-index="${index}">Editar</button>
          <button class="btn btn-sm btn-outline-danger" type="button" data-admin-rule-action="remover" data-admin-rule-index="${index}">Remover</button>
        </div>
      </td>
    </tr>
  `).join("");
}

function activeAdministratorPlanKind() {
  return document.querySelector("[data-admin-plan-kind].active")?.dataset.adminPlanKind || "Imovel";
}

function administratorPlanRulesForKind(kind) {
  const rules = configState.data?.administradoras_regras || [];
  const byKind = rules.filter((rule) => (rule.tipo_bem || "Imovel") === kind);
  const knownNames = [
    ...(mapState.administradoras || []),
    ...administratorPlanDefaultNames,
    ...byKind.map((rule) => rule.administradora).filter(Boolean),
  ];
  const uniqueNames = [];
  knownNames.forEach((name) => {
    if (!name) return;
    const alreadyAdded = uniqueNames.some((existing) => normalizeText(existing) === normalizeText(name));
    if (!alreadyAdded) uniqueNames.push(name);
  });

  return uniqueNames.map((administradora) => {
    const savedRule = byKind.find((rule) => normalizeText(rule.administradora) === normalizeText(administradora));
    return {
      administradora,
      tipo_bem: kind,
      seguro_obrigatorio: false,
      seguro_obrigatorio_texto: "",
      aceita_saida_fiscal: false,
      aceita_saida_fiscal_texto: "",
      aceita_fgts: true,
      ...(savedRule || {}),
    };
  });
}

function administratorPlanCellValue(rule, row) {
  const value = rule[row.key];
  if (row.key === "credito_a_ser_contratado") {
    return formatAdministratorPlanNumber(administratorPlanCreditoContratado(rule), 2);
  }
  if (row.key === "lance_embutido_valor") {
    return formatAdministratorPlanNumber(administratorPlanLanceEmbutidoValor(rule), 2);
  }
  if (row.key === "lance_proprio_usado") {
    return formatAdministratorPlanNumber(currentClientProfileLanceProprio(), 2);
  }
  if (row.key === "lance_total_considerado") {
    return formatAdministratorPlanNumber(administratorPlanLanceTotalConsiderado(rule), 2);
  }
  if (row.key === "lance_maximo") {
    const lanceMaximo = administratorPlanLanceMaximo(rule);
    return lanceMaximo === null ? "" : formatAdministratorPlanNumber(lanceMaximo * 100, 4);
  }
  if (row.key === "taxa_administracao_valor") {
    return formatAdministratorPlanNumber(administratorPlanTaxaAdmValor(rule), 2);
  }
  if (row.key === "fundo_reserva_valor") {
    return formatAdministratorPlanNumber(administratorPlanFundoReservaValor(rule), 2);
  }
  if (row.key === "prazo_minimo") {
    return formatAdministratorPlanNumber(administratorPlanPrazoMinimo(rule), 0);
  }
  if (row.type === "percent") return percentToInput(value);
  if (row.type === "money") return value ?? "";
  if (row.key === "seguro_obrigatorio_texto" && value === undefined) return rule.seguro_obrigatorio ? "Sim" : "";
  if (row.key === "aceita_saida_fiscal_texto" && value === undefined) return rule.aceita_saida_fiscal ? "Sim" : "";
  return value ?? "";
}

function currentClientProfileNumber(inputId, profileKey) {
  const activeInput = document.getElementById(inputId);
  const activeValue = activeInput ? toNumber(activeInput.value) : 0;
  if (activeValue) return activeValue;
  try {
    const savedProfile = JSON.parse(window.localStorage.getItem(CLIENT_PROFILE_STORAGE_KEY) || "null");
    return Number(savedProfile?.[profileKey] || 0);
  } catch {
    return 0;
  }
}

function currentClientProfileCredit() {
  return currentClientProfileNumber("clientProfileCredito", "credito_desejado");
}

function currentClientProfileLanceProprio() {
  return currentClientProfileNumber("clientProfileLanceProprio", "lance_proprio");
}

function currentClientProfileParcelaLimite() {
  return currentClientProfileNumber("clientProfileParcelaLimite", "parcela_limite")
    || currentClientProfileNumber("clientProfileParcelaIdeal", "parcela_ideal");
}

function administratorPlanPercent(rule, key) {
  const value = rule[key];
  if (typeof value === "number") return value > 1 ? value / 100 : value;
  return inputToPercentFromValue(value);
}

function administratorPlanCreditoContratado(rule) {
  const creditoDesejado = currentClientProfileCredit();
  const percentualLanceEmbutido = administratorPlanPercent(rule, "percentual_lance_embutido");
  if (!creditoDesejado || percentualLanceEmbutido < 0 || percentualLanceEmbutido >= 1) return null;
  return creditoDesejado / (1 - percentualLanceEmbutido);
}

function administratorPlanLanceEmbutidoValor(rule) {
  const creditoContratado = administratorPlanCreditoContratado(rule);
  if (!creditoContratado) return null;
  return creditoContratado * administratorPlanPercent(rule, "percentual_lance_embutido");
}

function administratorPlanLanceTotalConsiderado(rule) {
  const lanceEmbutido = administratorPlanLanceEmbutidoValor(rule);
  if (lanceEmbutido === null) return null;
  return lanceEmbutido + currentClientProfileLanceProprio();
}

function administratorPlanLanceMaximo(rule) {
  const creditoContratado = administratorPlanCreditoContratado(rule);
  if (!creditoContratado) return null;
  const lanceTotal = administratorPlanLanceTotalConsiderado(rule);
  return lanceTotal === null ? null : lanceTotal / creditoContratado;
}

function administratorPlanTaxaAdmValor(rule) {
  const creditoContratado = administratorPlanCreditoContratado(rule);
  if (!creditoContratado) return null;
  return creditoContratado * administratorPlanPercent(rule, "taxa_adm");
}

function administratorPlanFundoReservaValor(rule) {
  const creditoContratado = administratorPlanCreditoContratado(rule);
  if (!creditoContratado) return null;
  return creditoContratado * administratorPlanPercent(rule, "fundo_reserva");
}

function administratorPlanPrazoMinimo(rule) {
  const creditoContratado = administratorPlanCreditoContratado(rule);
  const lanceTotal = administratorPlanLanceTotalConsiderado(rule);
  const parcelaMaxima = currentClientProfileParcelaLimite();
  if (!creditoContratado || lanceTotal === null || !parcelaMaxima) return null;
  const taxaAdmValor = administratorPlanTaxaAdmValor(rule) || 0;
  const fundoReservaValor = administratorPlanFundoReservaValor(rule) || 0;
  return (
    creditoContratado
    + taxaAdmValor
    + fundoReservaValor
    - lanceTotal
  ) / parcelaMaxima;
}

function formatAdministratorPlanNumber(value, maximumFractionDigits) {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) return "";
  return Number(value).toLocaleString("pt-BR", {
    minimumFractionDigits: maximumFractionDigits,
    maximumFractionDigits,
  });
}

function recalculateAdministratorPlanComputedCells() {
  const currentRules = collectAdministratorPlans();
  document.querySelectorAll("[data-admin-plan-field]").forEach((input) => {
    if (!administratorPlanComputedFields.includes(input.dataset.adminPlanField)) return;
    const index = Number(input.dataset.adminPlanIndex);
    const row = administratorPlanRows.find((item) => item.key === input.dataset.adminPlanField);
    if (!row || !currentRules[index]) return;
    input.value = administratorPlanCellValue(currentRules[index], row);
  });
}

function renderAdministratorPlanRowLabel(row) {
  const help = administratorPlanRuleHelp[row.key];
  if (!help) return escapeHtml(row.label);
  return `
    <span class="admin-plan-rule-label">
      ${escapeHtml(row.label)}
      <button class="admin-plan-rule-marker" type="button" data-rule-help="${escapeHtml(help)}" aria-label="Explicar uso do campo ${escapeHtml(row.label)}">*</button>
    </span>
  `;
}

function ensureRuleHelpPopover() {
  let popover = document.getElementById("adminRuleHelpPopover");
  if (!popover) {
    popover = document.createElement("div");
    popover.id = "adminRuleHelpPopover";
    popover.className = "admin-rule-help-popover d-none";
    popover.setAttribute("role", "tooltip");
    document.body.appendChild(popover);
  }
  return popover;
}

function showRuleHelpPopover(target) {
  const popover = ensureRuleHelpPopover();
  const rect = target.getBoundingClientRect();
  popover.textContent = target.dataset.ruleHelp || "";
  popover.style.left = `${Math.min(rect.left + window.scrollX + 12, window.scrollX + window.innerWidth - 340)}px`;
  popover.style.top = `${rect.bottom + window.scrollY + 8}px`;
  popover.classList.remove("d-none");
}

function hideRuleHelpPopover() {
  document.getElementById("adminRuleHelpPopover")?.classList.add("d-none");
}

function renderAdministratorPlans() {
  const kind = activeAdministratorPlanKind();
  const rules = administratorPlanRulesForKind(kind);
  document.getElementById("administratorPlansHead").innerHTML = `
    <tr>
      <th>2 - Planos Administradoras</th>
      ${rules.map((rule, index) => `
        <th>
          <input class="admin-plan-admin-input" data-admin-plan-admin="${index}" value="${escapeHtml(rule.administradora || "")}" aria-label="Administradora ${index + 1}">
        </th>
      `).join("")}
    </tr>
  `;
  document.getElementById("administratorPlansBody").innerHTML = administratorPlanRows.map((row) => `
    <tr>
      <th>${renderAdministratorPlanRowLabel(row)}</th>
      ${rules.map((rule, index) => `
        <td>
          <input class="admin-plan-cell" data-admin-plan-index="${index}" data-admin-plan-field="${escapeHtml(row.key)}" data-admin-plan-type="${escapeHtml(row.type)}" value="${escapeHtml(administratorPlanCellValue(rule, row))}" ${administratorPlanComputedFields.includes(row.key) ? "readonly" : ""}>
        </td>
      `).join("")}
    </tr>
  `).join("");
}

function addAdministratorPlanColumn() {
  const kind = activeAdministratorPlanKind();
  const rules = [...(configState.data?.administradoras_regras || [])];
  rules.push({
    administradora: "Nova",
    tipo_bem: kind,
    seguro_obrigatorio: false,
    seguro_obrigatorio_texto: "",
    aceita_saida_fiscal: false,
    aceita_saida_fiscal_texto: "",
    aceita_fgts: true,
  });
  configState.data = { ...(configState.data || {}), administradoras_regras: rules };
  renderAdministratorPlans();
}

function collectAdministratorPlans() {
  const kind = activeAdministratorPlanKind();
  const existing = configState.data?.administradoras_regras || [];
  const otherKinds = existing.filter((rule) => (rule.tipo_bem || "Imovel") !== kind);
  const currentRules = administratorPlanRulesForKind(kind);
  const collected = currentRules.map((rule, index) => ({
    ...rule,
    tipo_bem: kind,
    administradora: document.querySelector(`[data-admin-plan-admin="${index}"]`)?.value.trim() || rule.administradora || "",
  }));
  document.querySelectorAll("[data-admin-plan-field]").forEach((input) => {
    const index = Number(input.dataset.adminPlanIndex);
    const field = input.dataset.adminPlanField;
    const type = input.dataset.adminPlanType;
    if (!collected[index]) return;
    if (administratorPlanComputedFields.includes(field)) return;
    if (type === "percent") {
      collected[index][field] = inputToPercentFromValue(input.value);
    } else if (type === "money") {
      collected[index][field] = optionalNumber(input.value);
    } else if (type === "number") {
      collected[index][field] = optionalNumber(input.value);
    } else {
      collected[index][field] = input.value.trim();
    }
  });
  collected.forEach((rule) => {
    rule.seguro_obrigatorio = normalizeText(rule.seguro_obrigatorio_texto || "").startsWith("sim");
    rule.aceita_saida_fiscal = normalizeText(rule.aceita_saida_fiscal_texto || "").startsWith("sim");
    rule.aceita_fgts = rule.aceita_fgts !== false;
  });
  return [...otherKinds, ...collected.filter((rule) => rule.administradora)];
}

async function saveAdministratorPlans() {
  const rules = collectAdministratorPlans();
  await apiPut("/configuracoes", { administradoras_regras: rules });
  configState.data = { ...(configState.data || {}), administradoras_regras: rules };
  renderAdministratorRules(rules);
  renderAdministratorPlans();
  showToast("Administradoras salvas.", "success");
  addOperationalLog("Planos de administradoras salvos");
}

function clearAdministratorRuleForm() {
  configAdministratorRuleIndex = null;
  document.getElementById("administratorRulesForm").reset();
  document.getElementById("adminRuleAceitaFgts").value = "true";
  document.getElementById("saveAdministratorRuleBtn").textContent = "Salvar Administradora";
}

function collectAdministratorRuleForm() {
  return {
    administradora: document.getElementById("adminRuleAdministradora").value.trim(),
    seguro_obrigatorio: getSelectBool("adminRuleSeguro"),
    idade_maxima: adminRuleNumber(document.getElementById("adminRuleIdadeMaxima").value) || null,
    limite_sem_comprovacao_renda: optionalNumber(document.getElementById("adminRuleLimiteRenda").value),
    percentual_lance_embutido: inputToPercent("adminRuleLanceEmbutido"),
    tipo_lance_embutido: document.getElementById("adminRuleTipoLance").value,
    taxa_adm: inputToPercent("adminRuleTaxaAdm"),
    possui_negociacao_taxa: document.getElementById("adminRuleNegociacao").value.trim(),
    fundo_reserva: inputToPercent("adminRuleFundoReserva"),
    aceita_saida_fiscal: getSelectBool("adminRuleSaidaFiscal"),
    aceita_fgts: getSelectBool("adminRuleAceitaFgts"),
    observacoes_operacionais: document.getElementById("adminRuleObservacoes").value.trim(),
  };
}

function fillAdministratorRuleForm(rule, index) {
  configAdministratorRuleIndex = index;
  setInputValue("adminRuleAdministradora", rule.administradora);
  setSelectBool("adminRuleSeguro", rule.seguro_obrigatorio);
  setInputValue("adminRuleIdadeMaxima", rule.idade_maxima);
  setInputValue("adminRuleLimiteRenda", rule.limite_sem_comprovacao_renda);
  setInputValue("adminRuleLanceEmbutido", percentToInput(rule.percentual_lance_embutido));
  setInputValue("adminRuleTipoLance", rule.tipo_lance_embutido || "Credito");
  setSelectBool("adminRuleSaidaFiscal", rule.aceita_saida_fiscal);
  setInputValue("adminRuleTaxaAdm", percentToInput(rule.taxa_adm));
  setInputValue("adminRuleNegociacao", rule.possui_negociacao_taxa);
  setInputValue("adminRuleFundoReserva", percentToInput(rule.fundo_reserva));
  setSelectBool("adminRuleAceitaFgts", rule.aceita_fgts !== false);
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
    empresa: {
      nome: document.getElementById("configEmpresaNome").value.trim(),
      cnpj: document.getElementById("configEmpresaCnpj").value.trim(),
      email: document.getElementById("configEmpresaEmail").value.trim(),
      telefone: document.getElementById("configEmpresaTelefone").value.trim(),
      endereco: document.getElementById("configEmpresaEndereco").value.trim(),
      logo: document.getElementById("configEmpresaLogo").value.trim(),
    },
    preferencias: {
      moeda: document.getElementById("configMoeda").value.trim(),
      formato_data: document.getElementById("configFormatoData").value.trim(),
      tema: document.getElementById("configTema").value,
      idioma: document.getElementById("configIdioma").value.trim(),
      casas_decimais_valores: Number(document.getElementById("configCasasValores").value || 0),
      casas_decimais_percentuais: Number(document.getElementById("configCasasPercentuais").value || 0),
      atualizacao_automatica_minutos: Number(document.getElementById("configAtualizacaoMinutos").value || 0),
      ativar_meia_parcela: getSelectBool("configMeiaParcela"),
      ativar_lance_embutido: getSelectBool("configLanceEmbutido"),
      exibir_historico_36_meses: getSelectBool("configHistorico36"),
    },
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
    integracoes: {
      google_sheets: getSelectBool("integrationGoogleSheetsToggle"),
      piperun_crm: getSelectBool("integrationPiperunToggle"),
      email_smtp: getSelectBool("integrationEmailToggle"),
      backup_automatico: getSelectBool("integrationBackupToggle"),
    },
    notificacoes: {
      alertar_sincronizacao: getSelectBool("notifySync"),
      alertar_estudo_salvo: getSelectBool("notifyStudySaved"),
      alertar_historico_atualizado: getSelectBool("notifyHistoryUpdated"),
      alertar_falha_integracao: getSelectBool("notifyIntegrationFailure"),
    },
    administradoras_regras: configState.data?.administradoras_regras || [],
    regras_negocio_feedbacks: collectBusinessRuleFeedbacks(),
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
  notifyWhen("alertar_sincronizacao", `Google Sheets sincronizado: ${result.total} linhas.`, "success");
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
  if (document.getElementById("screen-administradoras").classList.contains("active")) {
    saveAdministratorPlans().catch(() => setConfigState("error"));
    return;
  }
  if (document.getElementById("screen-viabilidade").classList.contains("active")) {
    analyzeViability();
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

document.getElementById("clearFiltersBtn").addEventListener("click", () => {
  document.getElementById("groupFilters").reset();
  mapState.page = 1;
  loadMapaGrupos();
});

document.getElementById("pageSizeSelect").addEventListener("change", (event) => {
  mapState.pageSize = Number(event.target.value);
  mapState.page = 1;
  loadMapaGrupos();
});

document.getElementById("exportGroupsCsvBtn").addEventListener("click", exportGroupsCsv);

document.getElementById("groupFormHistoryYear").addEventListener("change", () => {
  syncGroupFormVisibleHistory();
  renderHistoryEditor("groupFormHistory", groupFormHistoryData);
});

const moneyInputIds = [
  "filterCreditoMinimo",
  "filterCreditoMaximo",
  "clientProfileCredito",
  "clientProfileLanceProprio",
  "clientProfileFgtsTitular",
  "clientProfileFgtsConjuge",
  "clientProfileRendaTitular",
  "clientProfileRendaConjuge",
  "clientProfileParcelaIdeal",
  "clientProfileParcelaLimite",
  "groupFormCreditoMinimo",
  "groupFormCreditoMaximo",
];

moneyInputIds.forEach((id) => {
  document.getElementById(id)?.addEventListener("blur", () => formatMoneyInputById(id));
});

[
  "clientProfileCredito",
  "clientProfileLanceProprio",
  "clientProfileFgtsTitular",
  "clientProfileFgtsConjuge",
  "clientProfileRendaTitular",
  "clientProfileRendaConjuge",
  "clientProfileParcelaIdeal",
  "clientProfileParcelaLimite",
].forEach((id) => {
  document.getElementById(id).addEventListener("input", updateClientProfileTotals);
});
["clientProfileCredito", "clientProfileLanceProprio", "clientProfileParcelaIdeal", "clientProfileParcelaLimite"].forEach((id) => {
  document.getElementById(id).addEventListener("input", recalculateAdministratorPlanComputedCells);
});

["clientProfilePrazo", "clientProfileObjetivo", "clientProfileTipoBem", "clientProfileEstadoBem"].forEach((id) => {
  document.getElementById(id).addEventListener("change", updateClientProfileTotals);
});

document.getElementById("saveClientProfileBtn").addEventListener("click", () => saveClientProfile());
document.getElementById("clearClientProfileBtn").addEventListener("click", resetClientProfile);
document.getElementById("advanceClientProfileBtn").addEventListener("click", advanceClientProfile);

document.getElementById("administratorPlansBody").addEventListener("mouseover", (event) => {
  const marker = event.target.closest(".admin-plan-rule-marker");
  if (marker) showRuleHelpPopover(marker);
});
document.getElementById("administratorPlansBody").addEventListener("mouseout", (event) => {
  if (event.target.closest(".admin-plan-rule-marker")) hideRuleHelpPopover();
});
document.getElementById("administratorPlansBody").addEventListener("focusin", (event) => {
  const marker = event.target.closest(".admin-plan-rule-marker");
  if (marker) showRuleHelpPopover(marker);
});
document.getElementById("administratorPlansBody").addEventListener("focusout", (event) => {
  if (event.target.closest(".admin-plan-rule-marker")) hideRuleHelpPopover();
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

document.getElementById("detailsEditBtn").addEventListener("click", () => {
  if (currentDetailsGroupId) openGroupForm("edit", currentDetailsGroupId);
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

document.querySelectorAll("[data-admin-plan-kind]").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll("[data-admin-plan-kind]").forEach((item) => item.classList.toggle("active", item === button));
    renderAdministratorPlans();
  });
});
document.getElementById("addAdministratorPlanBtn").addEventListener("click", addAdministratorPlanColumn);
document.getElementById("saveAdministratorPlansBtn").addEventListener("click", () => {
  saveAdministratorPlans().catch(() => setConfigState("error"));
});
document.getElementById("administratorPlansTable").addEventListener("input", (event) => {
  if (["percentual_lance_embutido", "taxa_adm", "fundo_reserva"].includes(event.target?.dataset?.adminPlanField)) {
    recalculateAdministratorPlanComputedCells();
  }
});

document.getElementById("analyzeViabilityBtn").addEventListener("click", analyzeViability);

document.getElementById("viabilityRankingBody").addEventListener("click", (event) => {
  const button = event.target.closest("[data-viability-action]");
  if (!button) return;
  if (button.dataset.viabilityAction === "auditar") {
    openViabilityAudit(button.dataset.groupId);
    return;
  }
  if (button.dataset.viabilityAction === "visualizar") {
    openGroupDetails(button.dataset.groupId);
    return;
  }
  const item = viabilityState.lastResult?.melhores_grupos?.find((group) => group.grupo_id === button.dataset.groupId);
  if (!item) {
    showToast("Execute a Viabilidade antes de selecionar o estudo.", "warning");
    return;
  }
  if (button.dataset.viabilityAction === "estrategias") {
    openFinancialStudy(button.dataset.groupId, item);
    return;
  }
});

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
  resetViabilityForm();
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

document.getElementById("saveConfigBtn").addEventListener("click", () => {
  saveConfiguracoes().catch(() => setConfigState("error"));
});

document.getElementById("configTema").addEventListener("change", (event) => {
  applyTheme(event.target.value);
});

document.getElementById("configureIntegrationsBtn").addEventListener("click", () => {
  document.getElementById("configIntegrationsForm").scrollIntoView({ behavior: "smooth", block: "center" });
  document.getElementById("integrationGoogleSheetsToggle").focus();
});

document.getElementById("testIntegrationsBtn").addEventListener("click", () => {
  syncGoogleSheets().catch(() => notifyWhen("alertar_falha_integracao", "Nao foi possivel testar integracoes.", "danger"));
});

document.getElementById("syncSheetsBtn").addEventListener("click", () => {
  syncGoogleSheets().catch(() => notifyWhen("alertar_falha_integracao", "Nao foi possivel sincronizar Google Sheets.", "danger"));
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
  reindexSystemData().catch(() => notifyWhen("alertar_falha_integracao", "Nao foi possivel reindexar os dados.", "danger"));
});

document.getElementById("validateSystemBtn").addEventListener("click", () => {
  validateSystemIntegrity().catch(() => notifyWhen("alertar_falha_integracao", "Nao foi possivel validar a integridade.", "danger"));
});

document.getElementById("restartSyncBtn").addEventListener("click", () => {
  restartSystemSync().catch(() => notifyWhen("alertar_falha_integracao", "Nao foi possivel reiniciar a sincronizacao.", "danger"));
});

document.getElementById("loginForm").addEventListener("submit", submitLogin);
document.getElementById("logoutBtn").addEventListener("click", logout);

bootApp().catch(() => showLogin("Nao foi possivel validar a sessao."));
