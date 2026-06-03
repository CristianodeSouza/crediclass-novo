// Crediclass Dashboard V2 - Frontend
console.log('App.js carregado');

document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM carregado');

    // Inicializar elementos
    const btnNovoGrupo = document.getElementById('btnNovoGrupo');
    const btnAtualizarDados = document.getElementById('btnAtualizarDados');
    const tabelaGrupos = document.getElementById('tabelaGrupos');

    console.log('Elementos encontrados:', { btnNovoGrupo, btnAtualizarDados, tabelaGrupos });

    // Listeners básicos (serão implementados nas etapas seguintes)
    if (btnNovoGrupo) {
        btnNovoGrupo.addEventListener('click', function() {
            console.log('Botão Novo Grupo clicado');
        });
    }

    if (btnAtualizarDados) {
        btnAtualizarDados.addEventListener('click', function() {
            console.log('Botão Atualizar Dados clicado');
        });
    }

    // Atualizar tabela (será implementado na Etapa 3)
    updateTabela();
});

function updateTabela() {
    const tabelaGrupos = document.getElementById('tabelaGrupos');
    if (!tabelaGrupos) return;

    // Placeholder para as próximas etapas
    tabelaGrupos.innerHTML = `
        <tr>
            <td colspan="10" class="text-center text-muted py-4">
                Sistema pronto para conexão com Google Sheets
            </td>
        </tr>
    `;
}
