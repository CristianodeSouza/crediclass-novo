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

function showToast(message, type = "success") {
  const region = document.getElementById("toastRegion");
  const toast = document.createElement("div");
  toast.className = `alert alert-${type} shadow-sm mb-2`;
  toast.textContent = message;
  region.appendChild(toast);
  setTimeout(() => toast.remove(), 3600);
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
  const entries = Object.entries(group.historico || {});
  setHistoryUpdateValues(entries);
  document.getElementById("detailsHistoryBody").innerHTML = entries.map(([month, item]) => `
    <tr>
      <td>${escapeHtml(month)}</td>
      <td>${formatPercent(item.maior_lance)}</td>
      <td>${formatPercent(item.menor_lance)}</td>
      <td>${item.qtd_contemplacoes ?? "-"}</td>
    </tr>
  `).join("") || `<tr><td colspan="4" class="text-center text-secondary">Historico nao encontrado.</td></tr>`;

  const labels = entries.map(([month]) => month);
  const maiores = entries.map(([, item]) => item.maior_lance ? item.maior_lance * 100 : null);
  const menores = entries.map(([, item]) => item.menor_lance ? item.menor_lance * 100 : null);

  if (detailsChart) detailsChart.destroy();
  const canvas = document.getElementById("detailsHistoryChart");
  detailsChart = new Chart(canvas, {
    type: "line",
    data: {
      labels,
      datasets: [
        { label: "Maior Lance (%)", data: maiores, borderColor: "#0d6efd", tension: 0.25 },
        { label: "Menor Lance (%)", data: menores, borderColor: "#16a34a", tension: 0.25 },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: { y: { beginAtZero: true } },
    },
  });
}

function inputPercent(value) {
  if (value === null || value === undefined) return "";
  return String(value * 100).replace(".", ",");
}

function setHistoryUpdateValues(entries) {
  const latest = entries.length ? entries[entries.length - 1] : [new Date().toISOString().slice(0, 7), {}];
  const [month, item] = latest;
  document.getElementById("historyUpdateMes").value = month;
  document.getElementById("historyUpdateMaior").value = inputPercent(item.maior_lance);
  document.getElementById("historyUpdateMenor").value = inputPercent(item.menor_lance);
  document.getElementById("historyUpdateQtd").value = item.qtd_contemplacoes ?? "";
  setHistoryUpdateState("");
}

function setHistoryUpdateState(state, message = "") {
  const status = document.getElementById("historyUpdateStatus");
  const button = document.getElementById("historyUpdateSaveBtn");
  button.disabled = state === "loading";
  button.textContent = state === "loading" ? "Salvando..." : "Salvar Historico";
  status.className = `history-update-status ${state === "success" ? "success" : state === "error" ? "error" : ""}`;
  status.classList.toggle("d-none", !message);
  status.textContent = message;
}

function collectHistoryUpdatePayload() {
  const maior = toNumber(document.getElementById("historyUpdateMaior").value);
  const menor = toNumber(document.getElementById("historyUpdateMenor").value);
  const qtdRaw = document.getElementById("historyUpdateQtd").value.trim();
  const payload = {
    mes: document.getElementById("historyUpdateMes").value,
  };
  if (document.getElementById("historyUpdateMaior").value.trim()) payload.maior_lance = maior > 1 ? maior / 100 : maior;
  if (document.getElementById("historyUpdateMenor").value.trim()) payload.menor_lance = menor > 1 ? menor / 100 : menor;
  if (qtdRaw) payload.qtd_contemplacoes = Number(qtdRaw);
  return payload;
}

async function saveHistoryUpdate() {
  if (!currentDetailsGroupId) return;
  const payload = collectHistoryUpdatePayload();
  if (!payload.mes) {
    setHistoryUpdateState("error", "Informe o mes do historico.");
    return;
  }
  const hasMetric = payload.maior_lance !== undefined || payload.menor_lance !== undefined || payload.qtd_contemplacoes !== undefined;
  if (!hasMetric) {
    setHistoryUpdateState("error", "Informe ao menos um valor de historico.");
    return;
  }
  setHistoryUpdateState("loading", "Salvando historico na Google Sheets...");
  await apiPut(`/grupos/${encodeURIComponent(currentDetailsGroupId)}/historico`, payload);
  await openGroupDetails(currentDetailsGroupId);
  setHistoryUpdateState("success", "Historico atualizado na Google Sheets.");
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
  if (!payload.administradora || !payload.grupo || !payload.tipo_bem || !payload.credito_minimo || !payload.credito_maximo || !payload.prazo_total) {
    showToast("Preencha os campos obrigatorios do grupo.", "warning");
    return;
  }
  if (groupFormMode === "edit" && groupFormId) {
    await apiPut(`/grupos/${encodeURIComponent(groupFormId)}`, payload);
    showToast("Grupo atualizado na Google Sheets.", "success");
  } else {
    const result = await apiPost("/grupos", payload);
    showToast(`Grupo criado: ${result.grupo_id}`, "success");
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
  } catch (error) {
    renderSummary([], 0);
    document.getElementById("tableSubtitle").textContent = "Erro ao carregar grupos";
    setMapState("error");
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
  const parcela = (creditoContratado + creditoContratado * taxaAdm + creditoContratado * fundoReserva) / prazo;
  return { creditoContratado, percentualEmbutido, lanceEmbutido, lanceProprio, fgts, lanceTotal, creditoDisponivel, prazo, parcela };
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
    ["Estado do bem", document.getElementById("viabilityEstadoBem").value || "Nao definido"],
  ];
  document.getElementById("studyClientGrid").innerHTML = fields.map(([label, value]) => studyField(label, value)).join("");
  document.getElementById("studyScenarioDate").textContent = `Data da analise: ${new Date().toLocaleDateString("pt-BR")}`;
}

function renderStudyGroup(group) {
  const fields = [
    ["Administradora", group.administradora || "-"],
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
  document.getElementById("studyGroupGrid").innerHTML = fields.map(([label, value]) => studyField(label, value)).join("");
  document.getElementById("studyGroupSubtitle").textContent = `${group.administradora || "Administradora"} - Grupo ${group.grupo || "-"}`;
}

function renderStudySummary(financial) {
  document.getElementById("studyCreditoOriginal").textContent = formatMoney(financial.creditoContratado);
  document.getElementById("studyLanceEmbutido").textContent = `${formatPercent(financial.percentualEmbutido)} / ${formatMoney(financial.lanceEmbutido)}`;
  document.getElementById("studyCreditoDisponivel").textContent = formatMoney(financial.creditoDisponivel);
  document.getElementById("studyLanceTotal").textContent = formatMoney(financial.lanceTotal);
  document.getElementById("studyParcelaInicial").textContent = formatMoney(financial.parcela);
}

function renderStudyStrategies(group, financial) {
  const strategies = [
    ["Lance Fixo", group.percentual_lance_fixo],
    ["Conservadora", group.conservador],
    ["Moderada", group.moderado],
    ["Agressiva", group.agressivo],
    ["Lance Total", financial.lanceTotal / financial.creditoContratado],
  ].map(([label, percent]) => [label, percent || 0]);

  document.getElementById("studyStrategiesBody").innerHTML = strategies.map(([label, percent]) => {
    const lanceTotal = financial.creditoContratado * percent;
    const lanceProprio = Math.max(0, lanceTotal - financial.lanceEmbutido);
    const prazoApos = Math.max(1, financial.prazo - Math.round(percent * financial.prazo));
    const chance = percent >= (group.agressivo || 0.5) ? "Alta" : percent >= (group.moderado || 0.3) ? "Media" : "Acompanhar";
    return `
      <tr>
        <td>${escapeHtml(label)}</td>
        <td>${formatPercent(percent)}</td>
        <td>${formatMoney(financial.lanceEmbutido)}</td>
        <td>${formatMoney(lanceProprio)}</td>
        <td>${formatMoney(financial.creditoDisponivel)}</td>
        <td>${formatMoney(financial.parcela)}</td>
        <td>${prazoApos} meses</td>
        <td>${chance}</td>
      </tr>
    `;
  }).join("");
}

function renderStudyHistory(group) {
  const entries = Object.entries(group.historico || {}).slice(-12);
  const maiores = entries.map(([, item]) => item.maior_lance ? item.maior_lance * 100 : null);
  const menores = entries.map(([, item]) => item.menor_lance ? item.menor_lance * 100 : null);
  const qtd = entries.map(([, item]) => item.qtd_contemplacoes || 0);
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

function renderStudyRecommendations(viabilityItem, financial) {
  const level = viabilityItem.afinidade >= 0.9 ? "Recomendacao forte" : viabilityItem.afinidade >= 0.8 ? "Recomendacao moderada" : "Recomendacao com acompanhamento";
  document.getElementById("studyRecommendationLevel").textContent = `${level} - afinidade ${formatPercent(viabilityItem.afinidade)}`;
  const recommendations = [
    `Grupo com afinidade ${formatPercent(viabilityItem.afinidade)} no ranking da Viabilidade.`,
    financial.parcela <= (currentStudy.payload.parcela_desejada || 0) ? "Parcela estimada dentro do limite informado." : "Parcela estimada exige validacao com o cliente.",
    "Acompanhar assembleias e historico mensal antes da oferta.",
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
    renderStudySummary(financial);
    renderStudyStrategies(group, financial);
    renderStudyHistory(group);
    renderStudyRecommendations(viabilityItem, financial);
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
      estado_bem: document.getElementById("viabilityEstadoBem").value || "",
    },
    grupo_id: currentStudy.groupId,
  };
  const result = await apiPost("/estudos", payload);
  currentStudy.savedStudyId = result.estudo_id;
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
  } catch (error) {
    renderHistorySummary([]);
    document.getElementById("historySubtitle").textContent = "Erro ao carregar estudos";
    setHistoryState("error");
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

function renderConfiguracoes(data) {
  configState.data = data;
  const empresa = data.empresa || {};
  const pref = data.preferencias || {};
  const params = data.parametros_financeiros || {};
  const integracoes = data.integracoes || {};
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
  setInputValue("configIdioma", pref.idioma);
  setInputValue("configAtualizacaoMinutos", pref.atualizacao_automatica_minutos);

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

  document.getElementById("configUsersBody").innerHTML = (data.usuarios || []).map((user) => `
    <tr>
      <td>${escapeHtml(user.nome)}</td>
      <td>${escapeHtml(user.email)}</td>
      <td>${escapeHtml(user.perfil)}</td>
      <td><span class="status-badge">${escapeHtml(user.status)}</span></td>
      <td>${escapeHtml(user.ultimo_acesso || "-")}</td>
      <td><button class="btn btn-sm btn-outline-secondary" type="button" data-config-user-action>Editar</button></td>
    </tr>
  `).join("");

  renderAccessPolicy(data.acesso || {});
  document.getElementById("configSystemGrid").innerHTML = [
    ["Aplicacao", sistema.app],
    ["Versao", sistema.version],
    ["Ambiente", sistema.environment],
    ["Debug", sistema.debug ? "Sim" : "Nao"],
    ["Google Sheets configurado", sistema.google_sheets_configurado ? "Sim" : "Nao"],
    ["Aba da planilha", sistema.google_sheet_name || "-"],
  ].map(([label, value]) => detailField(label, value)).join("");
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
      atualizacao_automatica_minutos: Number(document.getElementById("configAtualizacaoMinutos").value || 0),
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
  };
}

async function loadConfiguracoes() {
  setConfigState("loading");
  try {
    const data = await apiGet("/configuracoes");
    renderConfiguracoes(data);
    setConfigState("ready");
  } catch (error) {
    setConfigState("error");
  }
}

async function saveConfiguracoes() {
  await apiPut("/configuracoes", collectConfiguracoesPayload());
  showToast("Configuracoes salvas.", "success");
  loadConfiguracoes();
}

async function syncGoogleSheets() {
  const result = await apiPost("/reload", {});
  showToast(`Google Sheets sincronizado: ${result.total} linhas.`, "success");
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
  if (document.getElementById("screen-historico").classList.contains("active")) {
    loadHistoryStudies();
    return;
  }
  showToast("Funcionalidade sera implementada na etapa correspondente.", "info");
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

document.getElementById("testIntegrationsBtn").addEventListener("click", () => {
  syncGoogleSheets().catch(() => showToast("Nao foi possivel testar integracoes.", "danger"));
});

document.getElementById("syncSheetsBtn").addEventListener("click", () => {
  syncGoogleSheets().catch(() => showToast("Nao foi possivel sincronizar Google Sheets.", "danger"));
});

document.getElementById("configUsersBody").addEventListener("click", (event) => {
  if (event.target.closest("[data-config-user-action]")) {
    showToast("Usuarios sao apenas referencia operacional; todos visualizam os paineis.", "info");
  }
});

["clearSystemCacheBtn", "reindexSystemBtn", "validateSystemBtn", "restartSyncBtn"].forEach((id) => {
  document.getElementById(id).addEventListener("click", () => {
    syncGoogleSheets().catch(() => showToast("Nao foi possivel executar acao do sistema.", "danger"));
  });
});

loadHealth().catch(() => {
  document.getElementById("environmentLabel").textContent = "indisponivel";
});

loadMapaGrupos();
updateViabilityTotals();
openSharedStudyFromUrl().catch(() => showToast("Nao foi possivel abrir o estudo compartilhado.", "danger"));
