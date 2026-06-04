const screens = {
  mapa: {
    letter: "A) MAPA DE GRUPOS",
    title: "Mapa de Grupos",
    subtitle: "Lista e manutencao da base de grupos",
    action: "Novo Grupo",
  },
  viabilidade: {
    letter: "B) VIABILIDADE",
    title: "Viabilidade",
    subtitle: "Analise de viabilidade e selecao dos melhores grupos",
    action: "Analisar Viabilidade",
  },
  estudo: {
    letter: "C) ESTUDO FINANCEIRO",
    title: "Estudo Financeiro",
    subtitle: "Geracao do estudo financeiro detalhado",
    action: "Salvar Estudo",
  },
  historico: {
    letter: "D) HISTORICO DE ESTUDOS",
    title: "Historico de Estudos",
    subtitle: "Consulta e gestao dos estudos financeiros gerados",
    action: "Buscar Estudos",
  },
  configuracoes: {
    letter: "E) CONFIGURACOES",
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

let detailsModal = null;
let detailsChart = null;
let studyChart = null;
let historyStrategyChart = null;
let historyEvolutionChart = null;
let currentStudy = null;
let groupFormModal = null;
let groupFormMode = "create";
let groupFormId = null;
let currentDetailsGroupId = null;
let studyDetailsModal = null;
let currentStudyStrategies = [];
let currentStudyStrategyTab = "";
let configUserModal = null;
let configUserMode = "create";
let configUserIndex = null;

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

  if (screenName === "historico") {
    loadHistoryStudies();
  }
  if (screenName === "configuracoes") {
    loadConfiguracoes();
  }
}

function formatMoney(value) {
  if (value === null || value === undefined || !Number.isFinite(Number(value)) || Number(value) > 100000000) return "-";
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(value);
}

function formatPercent(value) {
  if (value === null || value === undefined) return "-";
  return `${new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 3 }).format(value * 100)}%`;
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

function exportGroupsCsv() {
  if (!mapState.items.length) {
    showToast("Carregue grupos antes de exportar.", "warning");
    return;
  }
  const rows = [
    ["ID Grupo", "Administradora", "Tipo de Bem", "Credito Minimo", "Credito Maximo", "Taxa ADM", "Prazo", "1a Assembleia", "Ultima Assembleia", "Status"],
    ...mapState.items.map((item) => [
      item.grupo_id,
      item.administradora,
      item.tipo_bem,
      item.credito_minimo,
      item.credito_maximo,
      item.taxa_adm,
      item.prazo_total,
      item.primeira_assembleia,
      item.ultima_assembleia,
      item.status,
    ]),
  ];
  downloadCsv(`crediclass-grupos-${new Date().toISOString().slice(0, 10)}.csv`, rows);
  showToast("CSV de grupos gerado.", "success");
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
  const text = String(value || "").trim();
  if (!text) return "";
  return text.replace(/\./g, "").replace(",", ".");
}

function toNumber(value) {
  const parsed = Number(parseNumberInput(value));
  return Number.isFinite(parsed) ? parsed : 0;
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

function updateFilterOptions(items) {
  const administradoras = [...new Set(items.map((item) => item.administradora).filter(Boolean))].sort();
  const tipos = [...new Set(items.map((item) => item.tipo_bem).filter(Boolean))].sort();
  updateSelectOptions("filterAdministradora", administradoras, "Todas");
  updateSelectOptions("filterTipoBem", tipos, "Todos");
}

function renderSummary(items, total) {
  const administradoras = new Set(items.map((item) => item.administradora).filter(Boolean));
  const credito = items.reduce((sum, item) => {
    const value = Number(item.credito_maximo || 0);
    return Number.isFinite(value) && value <= 100000000 ? sum + value : sum;
  }, 0);
  const taxas = items.map((item) => item.taxa_adm).filter((value) => value !== null && value !== undefined);
  const taxaMedia = taxas.length ? taxas.reduce((sum, value) => sum + value, 0) / taxas.length : null;

  document.getElementById("summaryTotal").textContent = total;
  document.getElementById("summaryAdministradoras").textContent = administradoras.size;
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
  document.getElementById("detailsHistoryBody").innerHTML = entries.map(([month, item]) => `
    <tr>
      <td><strong>${escapeHtml(historyMonthLabel(month))}</strong><small>${escapeHtml(month)}</small></td>
      <td>${formatPercent(item.maior_lance)}</td>
      <td>${formatPercent(item.menor_lance)}</td>
      <td>${item.qtd_contemplacoes ?? "-"}</td>
    </tr>
  `).join("") || `<tr><td colspan="4" class="text-center text-secondary">Historico nao encontrado.</td></tr>`;

  const chartEntries = entries.filter(([, item]) => item.maior_lance !== null || item.menor_lance !== null || item.qtd_contemplacoes !== null);
  const labels = chartEntries.map(([month]) => formatChartMonth(month));
  const maiores = chartEntries.map(([, item]) => item.maior_lance !== null && item.maior_lance !== undefined ? item.maior_lance * 100 : null);
  const menores = chartEntries.map(([, item]) => item.menor_lance !== null && item.menor_lance !== undefined ? item.menor_lance * 100 : null);
  const qtd = chartEntries.map(([, item]) => item.qtd_contemplacoes ?? null);
  const percentValues = [...maiores, ...menores].filter((value) => value !== null);
  const maxPercent = percentValues.length ? Math.min(100, Math.ceil(Math.max(...percentValues) / 10) * 10) : 100;

  if (detailsChart) detailsChart.destroy();
  const canvas = document.getElementById("detailsHistoryChart");
  detailsChart = new Chart(canvas, {
    type: "bar",
    data: {
      labels,
      datasets: [
        { type: "line", label: "Maior Lance", data: maiores, borderColor: "#0d6efd", backgroundColor: "rgba(13, 110, 253, 0.12)", borderWidth: 2.5, tension: 0.32, pointRadius: 3, yAxisID: "y" },
        { type: "line", label: "Menor Lance", data: menores, borderColor: "#16a34a", backgroundColor: "rgba(22, 163, 74, 0.12)", borderWidth: 2.5, tension: 0.32, pointRadius: 3, yAxisID: "y" },
        { label: "Contemplacoes", data: qtd, backgroundColor: "rgba(245, 158, 11, 0.28)", borderColor: "#f59e0b", borderWidth: 1, borderRadius: 6, yAxisID: "y1" },
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
              if (context.dataset.yAxisID === "y") return `${context.dataset.label}: ${context.parsed.y}%`;
              return `${context.dataset.label}: ${context.parsed.y}`;
            },
          },
        },
      },
      scales: {
        x: { grid: { display: false }, ticks: { maxRotation: 0, autoSkipPadding: 18 } },
        y: { beginAtZero: true, suggestedMax: maxPercent, ticks: { callback: (value) => `${value}%` }, title: { display: true, text: "Lance" } },
        y1: { beginAtZero: true, position: "right", grid: { drawOnChartArea: false }, ticks: { precision: 0 }, title: { display: true, text: "Contemplacoes" } },
      },
    },
  });
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
  if (value === null || value === undefined) return "";
  return String(value * 100).replace(".", ",");
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

function renderHistoryEditor(prefix, historico = {}, extraMonths = []) {
  const grid = document.getElementById(`${prefix}Grid`);
  if (!grid) return;
  const rows = buildHistoryRows(historico, extraMonths);
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

function addHistoryEditorMonth(prefix) {
  const input = document.getElementById(`${prefix}ExtraMes`);
  const grid = document.getElementById(`${prefix}Grid`);
  const month = input?.value;
  if (!month || !grid) return;
  if (grid.querySelector(`[data-history-month="${month}"]`)) {
    setHistoryUpdateStateForPrefix(prefix, "error", "Este mes ja esta na grade.");
    return;
  }
  const head = grid.querySelector(".history-edit-head");
  const row = document.createElement("div");
  row.innerHTML = historyEditorRow(prefix, month, {}).trim();
  grid.insertBefore(row.firstElementChild, head?.nextElementSibling || null);
  const rows = [...grid.querySelectorAll(".history-edit-row")].sort((a, b) => compareMonthKeys(a.dataset.historyMonth, b.dataset.historyMonth));
  rows.forEach((item) => grid.appendChild(item));
  input.value = "";
  setHistoryUpdateStateForPrefix(prefix, "success", "Mes adicionado para preenchimento.");
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
  for (const payload of payloads) {
    await apiPut(`/grupos/${encodeURIComponent(currentDetailsGroupId)}/historico`, payload);
  }
  await openGroupDetails(currentDetailsGroupId);
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
  document.getElementById("groupFormCreditoMinimo").value = group.credito_minimo ?? "";
  document.getElementById("groupFormCreditoMaximo").value = group.credito_maximo ?? "";
  document.getElementById("groupFormTaxaAdm").value = group.taxa_adm !== null && group.taxa_adm !== undefined ? String(group.taxa_adm * 100).replace(".", ",") : "";
  document.getElementById("groupFormPrazoTotal").value = group.prazo_total ?? "";
  document.getElementById("groupFormStatus").value = group.status || "Ativo";
  setGroupFormHistoryValues(group.historico || {});
}

function setGroupFormHistoryValues(historico) {
  renderHistoryEditor("groupFormHistory", historico || {});
  setGroupFormHistoryState("");
}

function setGroupFormHistoryState(state, message = "") {
  const status = document.getElementById("groupFormHistoryStatus");
  status.className = `history-update-status ${state === "success" ? "success" : state === "error" ? "error" : ""}`;
  status.classList.toggle("d-none", !message);
  status.textContent = message;
}

function collectGroupFormPayload() {
  const taxa = toNumber(document.getElementById("groupFormTaxaAdm").value);
  return {
    administradora: document.getElementById("groupFormAdministradora").value.trim(),
    grupo: document.getElementById("groupFormGrupo").value.trim(),
    tipo_bem: document.getElementById("groupFormTipoBem").value.trim(),
    credito_minimo: toNumber(document.getElementById("groupFormCreditoMinimo").value),
    credito_maximo: toNumber(document.getElementById("groupFormCreditoMaximo").value),
    taxa_adm: taxa > 1 ? taxa / 100 : taxa,
    prazo_total: Number(document.getElementById("groupFormPrazoTotal").value || 0),
    status: document.getElementById("groupFormStatus").value,
  };
}

async function openGroupForm(mode, groupId = null) {
  ensureGroupFormModal();
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

  try {
    const group = await apiGet(`/grupos/${encodeURIComponent(groupId)}`);
    setGroupFormValues(group);
    if (mode === "duplicate") {
      document.getElementById("groupFormGrupo").value = `${group.grupo}-COPIA`;
      groupFormId = null;
    }
    groupFormModal.show();
  } catch (error) {
    showToast("Nao foi possivel carregar o grupo para edicao.", "danger");
  }
}

async function saveGroupForm() {
  const payload = collectGroupFormPayload();
  let historyPayloads = [];
  try {
    historyPayloads = collectHistoryBatchPayloads("groupFormHistory");
  } catch (error) {
    setGroupFormHistoryState("error", error.message || "Revise os valores do historico.");
    return;
  }
  if (!payload.administradora || !payload.grupo || !payload.tipo_bem || !payload.credito_minimo || !payload.credito_maximo || !payload.prazo_total) {
    showToast("Preencha os campos obrigatorios do grupo.", "warning");
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
    for (const historyPayload of historyPayloads) {
      await apiPut(`/grupos/${encodeURIComponent(targetGroupId)}/historico`, historyPayload);
    }
    notifyWhen("alertar_historico_atualizado", "Historico mensal atualizado na Google Sheets.", "success");
  }
  groupFormModal.hide();
  loadMapaGrupos();
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
  setMapState("loading");
  try {
    const data = await apiGet(`/grupos?${buildQuery(getMapFilters())}`);
    mapState.total = data.total;
    mapState.items = data.items;
    mapState.lastLoadAt = new Date().toLocaleString("pt-BR");
    updateFilterOptions(data.items);
    renderSummary(data.items, data.total);
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

function updateViabilityTotals() {
  const fgts = toNumber(document.getElementById("viabilityFgtsTitular").value) + toNumber(document.getElementById("viabilityFgtsConjuge").value);
  const renda = toNumber(document.getElementById("viabilityRendaTitular").value) + toNumber(document.getElementById("viabilityRendaConjuge").value);
  document.getElementById("viabilityFgtsTotal").value = formatMoney(fgts);
  document.getElementById("viabilityRendaTotal").value = formatMoney(renda);
  return { fgts, renda };
}

function setViabilityState(state) {
  document.getElementById("viabilityLoading").classList.toggle("d-none", state !== "loading");
  document.getElementById("viabilityError").classList.toggle("d-none", state !== "error");
  document.getElementById("viabilityEmpty").classList.toggle("d-none", state !== "empty");
  document.getElementById("viabilityResults").classList.toggle("d-none", state !== "ready");
}

function collectViabilityPayload() {
  const totals = updateViabilityTotals();
  return {
    objetivo: document.getElementById("viabilityObjetivo").value,
    credito_desejado: toNumber(document.getElementById("viabilityCredito").value),
    prazo_desejado: Number(document.getElementById("viabilityPrazoDesejado").value),
    lance_proprio: toNumber(document.getElementById("viabilityLanceProprio").value),
    fgts: totals.fgts,
    renda_total: totals.renda,
    parcela_desejada: toNumber(document.getElementById("viabilityParcela").value),
    data_nascimento: document.getElementById("viabilityNascimento").value,
    data_nascimento_conjuge: document.getElementById("viabilityNascimentoConjuge").value,
    tipo_bem: "Imovel",
  };
}

function validateViabilityPayload(payload) {
  const required = [
    ["credito_desejado", "Informe o credito desejado."],
    ["prazo_desejado", "Informe o prazo desejado."],
    ["lance_proprio", "Informe o lance proprio disponivel."],
    ["renda_total", "Informe a renda total."],
    ["parcela_desejada", "Informe a parcela maxima desejada."],
  ];
  const missing = required.find(([key]) => !payload[key]);
  if (missing) {
    showToast(missing[1], "warning");
    return false;
  }
  return true;
}

function renderViabilityChecklist(checklist) {
  document.querySelectorAll("#viabilityChecklist li").forEach((item) => {
    const value = checklist?.[item.dataset.check];
    item.classList.toggle("check-ok", value === true);
    item.classList.toggle("check-fail", value === false);
  });
}

function renderViabilitySummary(result) {
  const items = result.melhores_grupos || [];
  const administradoras = new Set(items.map((item) => item.administradora).filter(Boolean));
  const top = items.filter((item) => item.afinidade >= 0.8).length;
  const bestInstallment = items.reduce((best, item) => best === null || item.parcela_estimada < best ? item.parcela_estimada : best, null);
  const maxCredit = items.reduce((best, item) => Math.max(best, item.credito || 0), 0);

  document.getElementById("viabilityAdministradoras").textContent = administradoras.size;
  document.getElementById("viabilityTotal").textContent = result.total_grupos_encontrados;
  document.getElementById("viabilityTop").textContent = top;
  document.getElementById("viabilityBestInstallment").textContent = formatMoney(bestInstallment);
  document.getElementById("viabilityMaxCredit").textContent = formatMoney(maxCredit);
  document.getElementById("viabilityRankingSubtitle").textContent = `${items.length} grupo(s) no ranking - perfil ${result.perfil}`;
  document.getElementById("viabilityScenario").textContent = `${result.cenario} - perfil ${result.perfil}`;
}

function renderViabilityRanking(items) {
  document.getElementById("viabilityRankingBody").innerHTML = items.map((item) => `
    <tr>
      <td>${item.ranking}</td>
      <td>${escapeHtml(item.grupo)}</td>
      <td>${escapeHtml(item.administradora)}</td>
      <td>${escapeHtml(item.tipo_bem)}</td>
      <td>${formatMoney(item.credito)}</td>
      <td>${formatMoney(item.parcela_estimada)}</td>
      <td>${formatPercent(item.lance_sugerido_percentual)}</td>
      <td>${formatMoney(item.lance_sugerido_valor)}</td>
      <td>${item.prazo} meses</td>
      <td><span class="status-badge">${formatPercent(item.afinidade)}</span></td>
      <td>
        <div class="row-actions">
          <button class="btn btn-sm btn-outline-primary" type="button" data-viability-action="visualizar" data-group-id="${escapeHtml(item.grupo_id)}">Ver</button>
          <button class="btn btn-sm btn-outline-secondary" type="button" data-viability-action="estudo" data-group-id="${escapeHtml(item.grupo_id)}">Estudo</button>
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
    if (!result.melhores_grupos.length) {
      setViabilityState("empty");
      return;
    }
    renderViabilitySummary(result);
    renderViabilityRanking(result.melhores_grupos);
    setViabilityState("ready");
    showToast("Analise de viabilidade concluida.", "success");
  } catch (error) {
    setViabilityState("error");
  }
}

function resetViabilityForm() {
  document.getElementById("viabilityForm").reset();
  updateViabilityTotals();
  renderViabilityChecklist({});
  document.getElementById("viabilityScenario").textContent = "Aguardando analise";
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
  const prazoApos = Math.max(1, prazo - Math.round(percentualLanceTotal * prazo));
  const parcelaApos = custoTotal / prazoApos;
  return { creditoContratado, percentualEmbutido, lanceEmbutido, lanceProprio, fgts, lanceTotal, creditoDisponivel, prazo, parcela, custoTotal, percentualLanceTotal, prazoApos, parcelaApos };
}

function renderStudyClient(payload) {
  const fields = [
    ["Objetivo", payload.objetivo],
    ["Prazo desejado", `${payload.prazo_desejado} meses`],
    ["Credito desejado", formatMoney(payload.credito_desejado)],
    ["Lance proprio disponivel", formatMoney(payload.lance_proprio)],
    ["FGTS utilizado", formatMoney(payload.fgts)],
    ["Renda total informada", formatMoney(payload.renda_total)],
    ["Parcela maxima desejada", formatMoney(payload.parcela_desejada)],
    ["Data nascimento titular", payload.data_nascimento || "-"],
    ["Data nascimento conjuge", payload.data_nascimento_conjuge || "-"],
    ["Estado do bem", document.getElementById("viabilityEstadoBem").value || "Nao definido"],
  ];
  document.getElementById("studyClientGrid").innerHTML = fields.map(([label, value]) => studyField(label, value)).join("");
  document.getElementById("studyScenarioDate").textContent = `Data da analise: ${new Date().toLocaleDateString("pt-BR")}`;
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
  document.getElementById("studyGroupSubtitle").textContent = `${administradora} - Grupo ${group.grupo || "-"}`;
}

function renderStudySummary(financial, group, viabilityItem) {
  document.getElementById("studyCreditoOriginal").textContent = formatMoney(financial.creditoContratado);
  document.getElementById("studyLanceEmbutido").textContent = `${formatPercent(financial.percentualEmbutido)} / ${formatMoney(financial.lanceEmbutido)}`;
  document.getElementById("studyCreditoDisponivel").textContent = formatMoney(financial.creditoDisponivel);
  document.getElementById("studyRecursoProprio").textContent = formatMoney(financial.lanceProprio + financial.fgts);
  document.getElementById("studyPercentualLanceTotal").textContent = formatPercent(financial.percentualLanceTotal);
  document.getElementById("studyLanceTotal").textContent = formatMoney(financial.lanceTotal);
  document.getElementById("studyParcelaInicial").textContent = formatMoney(financial.parcela);
  document.getElementById("studyParcelaApos").textContent = formatMoney(financial.parcelaApos);
  document.getElementById("studyPrazoApos").textContent = `${financial.prazoApos} meses`;
  document.getElementById("studyCustoTotal").textContent = formatMoney(financial.custoTotal);
  document.getElementById("studySeguroGarantia").textContent = formatBool(group.seguro_garantia);
  document.getElementById("studyProximaAssembleia").textContent = group.proxima_assembleia || group.ultima_assembleia || "-";
  document.getElementById("studyChanceContemplacao").textContent = financial.percentualLanceTotal >= (group.agressivo || 0.5) ? "Alta" : financial.percentualLanceTotal >= (group.moderado || 0.3) ? "Media" : "Acompanhar";
  document.getElementById("studyRankingPosition").textContent = viabilityItem.ranking ? `${viabilityItem.ranking}o lugar` : "-";
}

function renderStudyStrategies(group, financial) {
  currentStudyStrategies = [
    ["Lance Fixo", group.percentual_lance_fixo],
    ["Lance Conservador", group.conservador],
    ["Lance Moderado", group.moderado],
    ["Lance Agressivo", group.agressivo],
    ["Lance Total", financial.lanceTotal / financial.creditoContratado],
  ].map(([label, percent]) => {
    const percentual = percent || 0;
    const lanceTotal = financial.creditoContratado * percentual;
    return {
      label,
      percent: percentual,
      lanceProprio: Math.max(0, lanceTotal - financial.lanceEmbutido),
      prazoApos: Math.max(1, financial.prazo - Math.round(percentual * financial.prazo)),
      chance: percentual >= (group.agressivo || 0.5) ? "Alta" : percentual >= (group.moderado || 0.3) ? "Media" : "Acompanhar",
    };
  });
  currentStudyStrategyTab = currentStudyStrategies.some((item) => item.label === currentStudyStrategyTab) ? currentStudyStrategyTab : "Lance Fixo";
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
        <td>${formatPercent(strategy.percent)}</td>
        <td>${formatMoney(financial.lanceEmbutido)}</td>
        <td>${formatMoney(strategy.lanceProprio)}</td>
        <td>${formatMoney(financial.creditoDisponivel)}</td>
        <td>${formatMoney(financial.parcela)}</td>
        <td>${strategy.prazoApos} meses</td>
        <td>${strategy.chance}</td>
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
  document.getElementById("studyRecommendationLevel").textContent = `${level} - afinidade ${formatPercent(viabilityItem.afinidade)}`;
  const historyEntries = Object.values(group.historico || {}).slice(-12);
  const totalContemplacoes = historyEntries.reduce((sum, item) => sum + (item.qtd_contemplacoes || 0), 0);
  const prazoAdequado = financial.prazoApos <= (currentStudy.payload.prazo_desejado || financial.prazo);
  const estrategiaRecomendada = currentStudyStrategies.find((strategy) => strategy.label === "Lance Total") || currentStudyStrategies[0];
  const recommendations = [
    totalContemplacoes > 0 ? `Grupo com bom historico: ${totalContemplacoes} contemplacao(oes) nos ultimos 12 meses.` : "Grupo sem contemplacoes registradas nos ultimos 12 meses; acompanhar historico antes da oferta.",
    `Estrategia recomendada: ${estrategiaRecomendada.label} com ${formatPercent(estrategiaRecomendada.percent)} de lance.`,
    prazoAdequado ? "Prazo adequado ao cenario informado pelo cliente." : "Prazo apos lance acima do desejado; revisar expectativa do cliente.",
    financial.parcela <= (currentStudy.payload.parcela_desejada || 0) ? "Parcela estimada dentro do limite informado." : "Parcela estimada exige validacao com o cliente.",
    "Necessidade de acompanhamento semanal das assembleias e do historico mensal.",
    "A analise nao garante contemplacao.",
  ];
  document.getElementById("studyRecommendations").innerHTML = recommendations.map((text) => `<li class="check-ok">${escapeHtml(text)}</li>`).join("");
}

async function openFinancialStudy(groupId, viabilityItem) {
  const payload = collectViabilityPayload();
  currentStudy = { groupId, viabilityItem, payload, group: null };
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
      estado_bem: document.getElementById("viabilityEstadoBem").value || "",
    },
    grupo_id: currentStudy.groupId,
  };
  const result = await apiPost("/estudos", payload);
  currentStudy.savedStudyId = result.estudo_id;
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
    ["Parcela apos contemplacao", formatMoney(financeiro.parcela_apos_contemplacao)],
    ["Chance", financeiro.chance_contemplacao || "-"],
    ["Total contemplacoes 12m", historico.total_contemplacoes ?? "-"],
  ].map(([label, value]) => detailField(label, value)).join("");
  document.getElementById("studyDetailsStrategiesBody").innerHTML = (financeiro.estrategias || []).map((strategy) => `
    <tr>
      <td>${escapeHtml(strategy.estrategia || "-")}</td>
      <td>${formatPercent(strategy.percentual_lance)}</td>
      <td>${formatMoney(strategy.lance_embutido)}</td>
      <td>${formatMoney(strategy.lance_proprio)}</td>
      <td>${formatMoney(strategy.credito_disponivel)}</td>
      <td>${formatMoney(strategy.parcela_apos_contemplacao)}</td>
      <td>${strategy.prazo_apos_lance ? `${strategy.prazo_apos_lance} meses` : "-"}</td>
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
  return value === null || value === undefined ? "" : String(value * 100).replace(".", ",");
}

function inputToPercent(id) {
  const value = toNumber(document.getElementById(id).value);
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

document.getElementById("primaryAction").addEventListener("click", () => {
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
  saveGroupForm().catch(() => showToast("Nao foi possivel salvar o grupo.", "danger"));
});

document.getElementById("historyUpdateForm").addEventListener("submit", (event) => {
  event.preventDefault();
  saveHistoryUpdate().catch((error) => setHistoryUpdateState("error", error.message || "Nao foi possivel atualizar o historico."));
});

document.getElementById("historyUpdateAddMonthBtn").addEventListener("click", () => addHistoryEditorMonth("historyUpdate"));
document.getElementById("groupFormHistoryAddMonthBtn").addEventListener("click", () => addHistoryEditorMonth("groupFormHistory"));

document.getElementById("viabilityForm").addEventListener("submit", (event) => {
  event.preventDefault();
  analyzeViability();
});

["viabilityFgtsTitular", "viabilityFgtsConjuge", "viabilityRendaTitular", "viabilityRendaConjuge"].forEach((id) => {
  document.getElementById(id).addEventListener("input", updateViabilityTotals);
});

document.getElementById("clearViabilityBtn").addEventListener("click", resetViabilityForm);

document.getElementById("viabilityRankingBody").addEventListener("click", (event) => {
  const button = event.target.closest("[data-viability-action]");
  if (!button) return;
  if (button.dataset.viabilityAction === "visualizar") {
    openGroupDetails(button.dataset.groupId);
    return;
  }
  const item = viabilityState.lastResult?.melhores_grupos?.find((group) => group.grupo_id === button.dataset.groupId);
  if (!item) {
    showToast("Execute a Viabilidade antes de selecionar o estudo.", "warning");
    return;
  }
  openFinancialStudy(button.dataset.groupId, item);
});

document.getElementById("studyChangeGroupBtn").addEventListener("click", () => activateScreen("viabilidade"));
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

loadHealth().catch(() => {
  document.getElementById("environmentLabel").textContent = "indisponivel";
});

loadMapaGrupos();
updateViabilityTotals();
openSharedStudyFromUrl().catch(() => showToast("Nao foi possivel abrir o estudo compartilhado.", "danger"));
