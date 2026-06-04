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

let detailsModal = null;
let detailsChart = null;

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
}

function formatMoney(value) {
  if (value === null || value === undefined) return "-";
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

function parseNumberInput(value) {
  const text = String(value || "").trim();
  if (!text) return "";
  return text.replace(/\./g, "").replace(",", ".");
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
  const credito = items.reduce((sum, item) => sum + (item.credito_maximo || 0), 0);
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
            <button class="btn btn-sm btn-outline-secondary" type="button" data-map-action="editar">Editar</button>
            <button class="btn btn-sm btn-outline-secondary" type="button" data-map-action="duplicar">Duplicar</button>
            <button class="btn btn-sm btn-outline-danger" type="button" data-map-action="excluir">Excluir</button>
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

async function openGroupDetails(groupId) {
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

async function loadHealth() {
  const health = await apiGet("/health");
  document.getElementById("environmentLabel").textContent = health.environment;
}

document.querySelectorAll(".nav-item").forEach((item) => {
  item.addEventListener("click", () => activateScreen(item.dataset.screen));
});

document.getElementById("primaryAction").addEventListener("click", () => {
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
  showToast("Acao sera implementada nas proximas etapas.", "info");
});

document.getElementById("detailsEditBtn").addEventListener("click", () => {
  showToast("Edicao sera implementada na etapa CRUD Google Sheets.", "info");
});

loadHealth().catch(() => {
  document.getElementById("environmentLabel").textContent = "indisponivel";
});

loadMapaGrupos();
