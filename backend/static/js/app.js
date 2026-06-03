// Crediclass Dashboard V2 - Frontend - Etapa 9 (Modal com Abas)
let gruposOriginais = [];
let gruposFiltrados = [];
let grupoEmEdicao = null;

document.addEventListener('DOMContentLoaded', function() {
    // Inicializar elementos
    const btnNovoGrupo = document.getElementById('btnNovoGrupo');
    const btnAtualizarDados = document.getElementById('btnAtualizarDados');
    const filtroAdministradora = document.getElementById('filtroAdministradora');
    const buscaGrupo = document.getElementById('buscaGrupo');

    // Event listeners
    if (btnNovoGrupo) {
        btnNovoGrupo.addEventListener('click', abrirModalNovoGrupo);
    }

    if (btnAtualizarDados) {
        btnAtualizarDados.addEventListener('click', carregarGrupos);
    }

    if (filtroAdministradora) {
        filtroAdministradora.addEventListener('change', aplicarFiltros);
    }

    if (buscaGrupo) {
        buscaGrupo.addEventListener('input', aplicarFiltros);
    }

    // Carregar grupos na inicialização
    carregarGrupos();
});

function carregarGrupos() {
    const tabelaGrupos = document.getElementById('tabelaGrupos');
    tabelaGrupos.innerHTML = `
        <tr>
            <td colspan="10" class="text-center text-muted py-4">
                <span>Carregando grupos...</span>
            </td>
        </tr>
    `;

    fetch('/api/grupos')
        .then(response => {
            if (!response.ok) {
                throw new Error(`Erro ${response.status}: ${response.statusText}`);
            }
            return response.json();
        })
        .then(dados => {
            gruposOriginais = dados;
            gruposFiltrados = dados;
            preencherFiltroAdministradora();
            renderizarTabela(dados);
        })
        .catch(erro => {
            console.error('Erro ao carregar grupos:', erro);
            tabelaGrupos.innerHTML = `
                <tr>
                    <td colspan="10" class="text-center text-danger py-4">
                        Erro ao carregar grupos: ${erro.message}
                    </td>
                </tr>
            `;
        });
}

function renderizarTabela(grupos) {
    const tabelaGrupos = document.getElementById('tabelaGrupos');

    if (grupos.length === 0) {
        tabelaGrupos.innerHTML = `
            <tr>
                <td colspan="10" class="text-center text-muted py-4">
                    Nenhum grupo encontrado
                </td>
            </tr>
        `;
        return;
    }

    const linhas = grupos.map(grupo => {
        const menorCredito = formatarMoeda(grupo.menor_credito);
        const maiorCredito = formatarMoeda(grupo.maior_credito);
        const prestacaoIntegral = formatarMoeda(grupo.prestacao_integral);
        const taxaAdmin = grupo.taxa_administracao ? grupo.taxa_administracao.toFixed(2) + '%' : '-';
        const statusBadge = grupo.status === 'Ativo'
            ? '<span class="badge bg-success">Ativo</span>'
            : '<span class="badge bg-secondary">Inativo</span>';

        return `
            <tr>
                <td>${grupo.administradora}</td>
                <td>${grupo.grupo}</td>
                <td>${grupo.tipo_bem || '-'}</td>
                <td>${menorCredito}</td>
                <td>${maiorCredito}</td>
                <td>${grupo.prazo_grupo || '-'}</td>
                <td>${prestacaoIntegral}</td>
                <td>${taxaAdmin}</td>
                <td>${statusBadge}</td>
                <td>
                    <button class="btn btn-sm btn-primary" onclick="abrirModalEditar('${grupo.grupo_id}')">
                        Editar
                    </button>
                    <button class="btn btn-sm btn-danger" onclick="deletarGrupo('${grupo.grupo_id}')">
                        Deletar
                    </button>
                </td>
            </tr>
        `;
    }).join('');

    tabelaGrupos.innerHTML = linhas;
}

function preencherFiltroAdministradora() {
    const filtro = document.getElementById('filtroAdministradora');
    const administradoras = [...new Set(gruposOriginais.map(g => g.administradora))];

    // Manter a opção "Todas"
    const optionTodas = filtro.querySelector('option[value=""]');
    filtro.innerHTML = '';
    filtro.appendChild(optionTodas);

    administradoras.forEach(admin => {
        const option = document.createElement('option');
        option.value = admin;
        option.textContent = admin;
        filtro.appendChild(option);
    });
}

function aplicarFiltros() {
    const filtroAdministradora = document.getElementById('filtroAdministradora').value;
    const buscaGrupo = document.getElementById('buscaGrupo').value.toLowerCase();

    gruposFiltrados = gruposOriginais.filter(grupo => {
        const passaFiltroAdmin = !filtroAdministradora || grupo.administradora === filtroAdministradora;
        const passaBusca = !buscaGrupo ||
                          grupo.grupo.toLowerCase().includes(buscaGrupo) ||
                          grupo.grupo_id.toLowerCase().includes(buscaGrupo);
        return passaFiltroAdmin && passaBusca;
    });

    renderizarTabela(gruposFiltrados);
}

function abrirModalNovoGrupo() {
    grupoEmEdicao = null;
    limparFormulario();
    document.getElementById('modalTitle').textContent = 'Novo Grupo';
    document.getElementById('inputAdministradora').disabled = false;
    document.getElementById('inputGrupo').disabled = false;
    const modal = new bootstrap.Modal(document.getElementById('modalGrupo'));
    modal.show();
}

function abrirModalEditar(grupoId) {
    const grupo = gruposOriginais.find(g => g.grupo_id === grupoId);
    if (!grupo) {
        alert('Grupo não encontrado');
        return;
    }

    grupoEmEdicao = grupo;
    preencherFormulario(grupo);
    document.getElementById('modalTitle').textContent = `Editar Grupo: ${grupoId}`;
    document.getElementById('inputAdministradora').disabled = true;
    document.getElementById('inputGrupo').disabled = true;

    const modal = new bootstrap.Modal(document.getElementById('modalGrupo'));
    modal.show();
}

function limparFormulario() {
    document.getElementById('formDadosGerais').reset();
    document.getElementById('historico2024-container').innerHTML = '';
    document.getElementById('historico2025-container').innerHTML = '';
    document.getElementById('historico2026-container').innerHTML = '';
}

function preencherFormulario(grupo) {
    // Preencher Dados Gerais
    document.getElementById('inputAdministradora').value = grupo.administradora || '';
    document.getElementById('inputGrupo').value = grupo.grupo || '';
    document.getElementById('inputTipoBem').value = grupo.tipo_bem || '';
    document.getElementById('inputCategoria').value = grupo.categoria || '';
    document.getElementById('inputMenorCredito').value = grupo.menor_credito || '';
    document.getElementById('inputMaiorCredito').value = grupo.maior_credito || '';
    document.getElementById('inputPrazoGrupo').value = grupo.prazo_grupo || '';
    document.getElementById('inputPrazoRestante').value = grupo.prazo_restante || '';
    document.getElementById('inputTaxaAdmin').value = grupo.taxa_administracao || '';
    document.getElementById('inputPrestacao').value = grupo.prestacao_integral || '';
    document.getElementById('inputFundoReserva').value = grupo.fundo_reserva || '';
    document.getElementById('inputPrimeiraAssembleia').value = grupo.primeira_assembleia || '';
    document.getElementById('inputDataTermino').value = grupo.data_termino || '';
    document.getElementById('inputStatus').value = grupo.status || 'Ativo';

    // Preencher Históricos (serão preenchidos quando carregarmos dados completos na Etapa 10)
    document.getElementById('historico2024-container').innerHTML = '<p class="text-muted">Histórico será carregado em breve...</p>';
    document.getElementById('historico2025-container').innerHTML = '<p class="text-muted">Histórico será carregado em breve...</p>';
    document.getElementById('historico2026-container').innerHTML = '<p class="text-muted">Histórico será carregado em breve...</p>';
}

function adicionarMesHistorico(ano) {
    const containerId = `historico${ano}-container`;
    const container = document.getElementById(containerId);

    const mesCard = document.createElement('div');
    mesCard.className = 'historico-mes position-relative';
    mesCard.innerHTML = `
        <button type="button" class="btn btn-sm btn-close position-absolute" style="top: 10px; right: 10px;" onclick="this.parentElement.remove()"></button>
        <div class="row">
            <div class="col-md-6">
                <label class="form-label">Mês</label>
                <select class="form-select form-select-sm" required>
                    <option value="">Selecionar mês</option>
                    <option value="01">Janeiro</option>
                    <option value="02">Fevereiro</option>
                    <option value="03">Março</option>
                    <option value="04">Abril</option>
                    <option value="05">Maio</option>
                    <option value="06">Junho</option>
                    <option value="07">Julho</option>
                    <option value="08">Agosto</option>
                    <option value="09">Setembro</option>
                    <option value="10">Outubro</option>
                    <option value="11">Novembro</option>
                    <option value="12">Dezembro</option>
                </select>
            </div>
            <div class="col-md-6">
                <label class="form-label">Assembleia</label>
                <input type="text" class="form-control form-control-sm" placeholder="Data/local da assembleia">
            </div>
        </div>
        <div class="row mt-2">
            <div class="col-md-6">
                <label class="form-label">Atas Publicadas</label>
                <input type="text" class="form-control form-control-sm" placeholder="Descrição">
            </div>
            <div class="col-md-6">
                <label class="form-label">Notas</label>
                <input type="text" class="form-control form-control-sm" placeholder="Observações">
            </div>
        </div>
    `;

    container.appendChild(mesCard);
}

function salvarGrupo() {
    const admin = document.getElementById('inputAdministradora').value.trim();
    const grupo = document.getElementById('inputGrupo').value.trim();

    if (!admin || !grupo) {
        alert('Administradora e Grupo são campos obrigatórios');
        return;
    }

    const dadosGerais = {
        administradora: admin,
        grupo: grupo,
        tipo_bem: document.getElementById('inputTipoBem').value.trim(),
        categoria: document.getElementById('inputCategoria').value.trim(),
        menor_credito: parseFloat(document.getElementById('inputMenorCredito').value) || null,
        maior_credito: parseFloat(document.getElementById('inputMaiorCredito').value) || null,
        prazo_grupo: parseInt(document.getElementById('inputPrazoGrupo').value) || null,
        prazo_restante: parseInt(document.getElementById('inputPrazoRestante').value) || null,
        taxa_administracao: parseFloat(document.getElementById('inputTaxaAdmin').value) || null,
        prestacao_integral: parseFloat(document.getElementById('inputPrestacao').value) || null,
        fundo_reserva: parseFloat(document.getElementById('inputFundoReserva').value) || null,
        primeira_assembleia: document.getElementById('inputPrimeiraAssembleia').value.trim(),
        data_termino: document.getElementById('inputDataTermino').value.trim(),
        status: document.getElementById('inputStatus').value
    };

    const payload = {
        dados_gerais: dadosGerais
    };

    const metodo = grupoEmEdicao ? 'PUT' : 'POST';
    const url = grupoEmEdicao
        ? `/api/grupos/${grupoEmEdicao.grupo_id}`
        : '/api/grupos';

    const btnSalvar = document.getElementById('btnSalvarGrupo');
    btnSalvar.disabled = true;
    btnSalvar.textContent = 'Salvando...';

    fetch(url, {
        method: metodo,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
        .then(response => {
            if (!response.ok) throw new Error(`Erro ${response.status}`);
            return response.json();
        })
        .then(resultado => {
            alert(grupoEmEdicao ? 'Grupo atualizado com sucesso!' : 'Grupo criado com sucesso!');
            bootstrap.Modal.getInstance(document.getElementById('modalGrupo')).hide();
            carregarGrupos();
        })
        .catch(erro => {
            console.error('Erro ao salvar grupo:', erro);
            alert('Erro ao salvar grupo: ' + erro.message);
        })
        .finally(() => {
            btnSalvar.disabled = false;
            btnSalvar.textContent = 'Salvar';
        });
}

function deletarGrupo(grupoId) {
    if (!confirm(`Tem certeza que deseja deletar o grupo ${grupoId}?`)) {
        return;
    }

    fetch(`/api/grupos/${grupoId}`, { method: 'DELETE' })
        .then(response => {
            if (!response.ok) throw new Error(`Erro ${response.status}`);
            return response.json();
        })
        .then(resultado => {
            alert('Grupo deletado com sucesso');
            carregarGrupos();
        })
        .catch(erro => {
            console.error('Erro ao deletar grupo:', erro);
            alert('Erro ao deletar grupo: ' + erro.message);
        });
}

function formatarMoeda(valor) {
    if (!valor && valor !== 0) return '-';
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(valor);
}