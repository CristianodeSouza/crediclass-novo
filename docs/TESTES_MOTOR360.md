# Estratégia de testes do Motor 360

## Por que “todos os testes passaram” não significava “front aprovado”

A contagem anterior (212 testes) era da suíte inteira do produto, não 212 testes de navegador do Motor 360. A maior parte das verificações de front nessa suíte lia o código-fonte procurando nomes, mensagens ou fragmentos (`assertIn`). Esses testes conseguem detectar remoções acidentais, mas não provam que uma regra é alcançada, que o payload correto foi usado, que o HTML final mostra o mesmo número da ordenação, nem que cache e eventos funcionam na página.

Também havia testes de funções isoladas executadas em Node com DOM falso. Eles são úteis para lógica pura, mas não simulam o parser HTML, seletores, atributos, eventos nem o comportamento do cache/renderização no navegador.

## Camadas que devem ser reportadas separadamente

| Camada | O que prova | O que não prova |
| --- | --- | --- |
| Motor/backend (`unittest`) | Fórmulas e decisões do servidor em fixtures controladas | Renderização, CSS, acessibilidade ou se a interface está ligada ao campo certo |
| Contrato de API/dados | Formato, identidade e campos do payload entre servidor e cliente | Fidelidade à planilha de produção se a fixture não veio de uma leitura real |
| Chromium – componentes (`tests/test_motor360_browser.py`) | Funções reais de ordenação/renderização executadas em Chrome, DOM parseado, rótulos, cache e busca da lista de omitidos | Inicialização autenticada completa ou serviço de produção |
| Chromium – aplicação (`tests/test_motor360_application_browser.py`) | Inicializa o app real com API congelada; percorre login de fixture, perfil, Motor 360, cenários, ordenação, filtro, limpar filtros, contagem de chamadas e overflow horizontal em viewport 390 px | Backend/planilha de produção, autenticação real ou layout em todos os navegadores/dispositivos |
| Contrato de endpoint (`tests/test_motor360_api_contract.py`) | Executa o endpoint real com dependências de dados/auditoria isoladas e confirma que identidade, linha de origem, percentuais e tempos chegam ao JSON serializado | Fidelidade da fixture à planilha atual ou integração externa real |
| Smoke publicado | `/api/health`, versão e bundles realmente publicados | Correção funcional dos cálculos e fluxos autenticados |
| Auditoria operacional | Dados reais, passos visuais, Network/Console e estado restaurado | Não substitui regressão automatizada repetível |

Não somar essas camadas em uma afirmação única de “front aprovado”. Relatar contagem e resultado por camada, skips, versão/commit testados e critérios ainda sem evidência.

## Cobertura de navegador adicionada

O teste `tests/test_motor360_browser.py` carrega trechos completos das funções de produção de ordenação, renderização de cards e diagnóstico em Chromium headless, com fixtures determinísticas baseadas nos casos reais recorrentes:

- I227, 1011, 20399 (incluindo lance zero) e grupo sem lance calculável;
- comparação da ordem com o rótulo realmente renderizado no card;
- troca de “Ordem original” para “Menor lance ideal”, conferindo que o cache não mantém HTML antigo;
- grupo sem dados suficientes não recebe falso selo de aprovação e campos ausentes aparecem como ausentes;
- tabela nominal de omitidos, totais `analisados = na lista + omitidos`, linha sem identificador, motivo sem duplicação e busca por “linha N”.

As suítes de Chromium executam JavaScript de produção e consultam o DOM real. A suíte de aplicação inicia a página real e usa fixtures HTTP controladas para endpoints, sem acessar produção. O contrato do backend chama a função do endpoint real com armazenamento/auditoria substituídos. São regressões repetíveis; não substituem validação contra Google Sheets atual nem auditoria visual autenticada da produção.

## Execução

```powershell
python -m unittest discover -s tests -v
```

Para exigir que a camada de navegador não seja silenciosamente ignorada:

```powershell
$env:REQUIRE_MOTOR360_BROWSER = "1"
python -m unittest tests.test_motor360_browser tests.test_motor360_application_browser tests.test_motor360_api_contract -v
```

O workflow `.github/workflows/motor360-regression.yml` instala Chromium e executa a suíte completa com essa exigência ligada. Se Chromium faltar no CI, a execução falha em vez de contar o teste como aprovado.

## Critérios de aceite para mudanças futuras

1. Cada cálculo importante deve ter teste unitário com valores conhecidos e casos nulos/zero/limites.
2. A ordenação deve ser comparada ao mesmo valor legível renderizado no card, nos cenários sem seleção, com um cenário e com ambos.
3. Eventos, atualização dos campos e chaves de cache devem ser testados por transições de estado no navegador, não por busca textual no arquivo.
4. Cada resposta/payload de produção deve preservar identidade do grupo e campos de origem relevantes; dados desconhecidos não podem virar zero ou aprovação.
5. Contagens de grupos devem fechar sobre a mesma base e deduplicação documentada; testar grupo nomeado, grupo sem identificador e linha-fonte.
6. Smoke publicado deve descobrir a versão por `/api/health` e confirmar que o HTML referencia os bundles daquela versão. Smoke não deve usar uma versão fixa antiga.
7. Antes de declarar produção aprovada, ainda é necessária auditoria visual autenticada dos fluxos alterados, com versão/commit, evidência da fonte, Console/Network e restauração do estado.

## Limitação explícita

Os testes novos não certificam o conteúdo atual do Google Sheets, o cálculo integral do backend sob a base de produção, nem responsividade visual de toda a aplicação. Para esses pontos, guardar fixtures versionadas derivadas de amostras aprovadas da fonte e manter uma auditoria de Chrome publicada separada. Nunca inferir sucesso de produção apenas pela quantidade de testes locais.
