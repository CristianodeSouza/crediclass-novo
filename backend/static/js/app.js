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

let detailsModal = null;
let detailsChart = null;
let studyChart = null;
let currentStudy = null;

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
    return;
  }
  const payload = {
    cliente: {
      nome: "Cliente em estudo",
      credito_desejado: currentStudy.payload.credito_desejado,
    },
    grupo_id: currentStudy.groupId,
  };
  const result = await apiPost("/estudos", payload);
  showToast(`Estudo salvo: ${result.estudo_id}`, "success");
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
["studyPdfBtn", "studyEmailBtn", "studyShareBtn"].forEach((id) => {
  document.getElementById(id).addEventListener("click", () => showToast("Acao sera finalizada na etapa de Historico e exportacao.", "info"));
});

loadHealth().catch(() => {
  document.getElementById("environmentLabel").textContent = "indisponivel";
});

loadMapaGrupos();
updateViabilityTotals();
