// Crediclass Dashboard V2 - Frontend - Etapa 8
let gruposOriginais = [];
let gruposFiltrados = [];

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
    const modal = new bootstrap.Modal(document.getElementById('modalGrupo'));
    document.getElementById('modalTitle').textContent = 'Novo Grupo';
    modal.show();
}

function abrirModalEditar(grupoId) {
    const grupo = gruposOriginais.find(g => g.grupo_id === grupoId);
    if (!grupo) {
        alert('Grupo não encontrado');
        return;
    }

    const modal = new bootstrap.Modal(document.getElementById('modalGrupo'));
    document.getElementById('modalTitle').textContent = `Editar Grupo: ${grupoId}`;
    modal.show();
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
