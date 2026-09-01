# Fluxo Atual: Perfil do Cliente ao Motor 360 de Viabilidade

> Estado inicial documentado em 22/07/2026, com base no commit `1c1eabd`.
>
> **Atualização de correção:** o código posterior a este diagnóstico passou a
> direcionar todos os objetivos para o Motor 360, exige status `Ativo`, remove o
> fallback histórico, trata AJ como referência e separa completude, crédito,
> renda, prazo e recomendação. As seções de “lacuna” abaixo foram preservadas
> como registro da auditoria que originou a correção.
>
> Este documento descreve o que o sistema **executa hoje** depois do botão
> **Avançar para Motor de Inteligência**. Ele não substitui as regras de negócio
> futuras; também registra as partes ainda legadas ou que não fazem seleção final.

## 1. Visão geral

O objetivo comercial é analisar todas as possibilidades de consórcio para um
cliente. O objetivo escolhido no Perfil do Cliente deve servir como preferência
de apresentação, e não como bloqueio de estratégias alternativas.

O núcleo novo implementado para isso é o **Motor 360 de Viabilidade do
Consórcio**:

1. Lê os dados consolidados do perfil.
2. Lê os grupos ativos da base.
3. Para cada grupo, monta cenários sem e com lance embutido.
4. Verifica se o crédito contratado cabe na faixa de crédito do grupo.
5. Calcula lance, saldo devedor e prazos matemáticos para cada cenário.
6. Classifica estratégias possíveis de investimento e contemplação.
7. Ordena e apresenta os grupos viáveis, priorizando a preferência declarada.

O endpoint do núcleo é `POST /api/viabilidade-360/analisar`, implementado em
`backend/main.py`. A regra está em
`backend/consortium_viability_engine.py`.

## 2. Disparo pelo botão

### 2.1 Botão

O botão `#advanceClientProfileBtn` chama `advanceClientProfile()` em
`backend/static/js/app.js`.

Antes de mudar de tela, a função chama `saveClientProfile({ silent: true })`.
Isso faz quatro ações:

1. Coleta os dados atuais do formulário com `collectClientProfile()`.
2. Salva o objeto no navegador, em `localStorage`, na chave
   `crediclass.clientProfile.v1`.
3. Atualiza os campos da área legada de viabilidade e a tabela de cálculo
   ilustrativa.
4. Solicita as análises atualmente registradas no front-end.

### 2.2 Destino atual do botão

O comportamento atual é:

| Objetivo selecionado | Tela aberta ao avançar | Motor chamado pela tela |
|---|---|---|
| Começa com `Investidor` | `Motor 360 de Viabilidade` (screen `investidor`) | `/api/viabilidade-360/analisar` |
| Começa com `Contemplar` | Tela legada `contemplar` | `/api/contemplar/analisar` |
| Outro/ausente | Tela legada `viabilidade` | Não é o fluxo principal do Motor 360 |

**Atenção:** isso significa que o botão ainda não direciona todo perfil
`Contemplar` para a nova tela do Motor 360. O Motor 360 existe e não restringe
estratégias, mas o roteamento do botão permanece parcialmente legado. Esta é a
principal divergência entre a arquitetura desejada e a navegação atual.

## 3. Construção do perfil de entrada

`collectClientProfile()` gera um único objeto para os motores. Os totais são
calculados por `updateClientProfileTotals()` a partir dos titulares cadastrados.

| Campo enviado | Origem no Perfil | Regra atual |
|---|---|---|
| `credito_desejado` | Crédito Desejado Líquido | Valor digitado pelo operador. |
| `parcela_desejada` / `parcela_ideal` | Parcela máxima desejada | Valor digitado pelo operador. |
| `renda_total` | Renda do Cliente dos participantes | Soma das rendas das pessoas físicas ativas. |
| `lance_proprio` | Lance Recursos Próprios | Soma dos recursos próprios dos participantes; se a soma for zero, usa o campo manual de lance como alternativa. |
| `fgts` | Lance FGTS | Soma do FGTS dos participantes ativos. |
| `parcela_limite` | Limite por renda | `renda_total x 30%` (`DEFAULT_PJ_COMMITMENT_PERCENT`). |
| `objetivo` | Objetivo do consórcio | Define a preferência de exibição, não o bloqueio no Motor 360. |
| `tipo_bem` | Regra derivada do objetivo | Atualmente é derivado pelo mapa `CLIENT_OBJECTIVE_RULES`. |
| `nome`, `nascimento` | Titulares | São mantidos no perfil, mas a idade não bloqueia o Motor 360 atual. |

## 4. Carregamento da base de grupos

O backend tenta primeiro `list_grupos(include_history=False)`. Se falhar, tenta
`list_grupos(include_history=True)`. A transformação da planilha é feita em
`backend/sheets_client.py`.

As posições abaixo são explícitas na base atual. Isto evita que a simples troca
do título de uma coluna mude silenciosamente a regra financeira.

| Dado do grupo | Coluna na planilha | Campo no sistema | Uso no Motor 360 |
|---|---:|---|---|
| Administradora | A | `administradora` | Identificação do resultado. |
| Grupo | B | `grupo` | Identificação e desempate de ordenação. |
| Tipo de bem | C | `tipo_bem` | Filtro de compatibilidade com o perfil. |
| Prazo restante | F | `prazo_remanescente` | Exibido; ainda não elimina grupos no Motor 360. |
| Crédito mínimo | O | `credito_minimo` | Limite inferior da faixa de crédito. |
| Crédito máximo | U | `credito_maximo` | Limite superior da faixa de crédito. |
| Lance embutido máximo | X | `percentual_lance_embutido` | Cria o cenário com embutido. |
| Fundo de reserva total | AA | `fundo_reserva` | Compõe o saldo devedor. |
| Taxa administrativa total | AC | `taxa_adm` | Compõe o saldo devedor. |
| Taxa administrativa ao ano | AD | `taxa_adm_ano` | Carregada, mas não entra no cálculo 360 atual. |
| Parcela inicial | AJ | `parcela_inicial_grupo` | Compara com o limite de renda e calcula proximidade. |
| Parcela após lance | AK | `parcela_apos_lance_grupo` | Carregada, mas ainda não é usada no Motor 360. |
| Parcela reduzida | AL | `parcela_reduzida` | Carregada, mas ainda não é usada no Motor 360. |
| Lance investidor | BL | `lance_investidor` | Referência para estratégia de 36 meses. |
| Lance conservador 24 meses | BM | `lance_conservador_24m` | Referência para estratégia conservadora. |
| Lance moderado 12 meses | BN | `lance_moderado_12m` | Referência para estratégia moderada. |
| Lance rápido 6 meses | BO | `lance_agressivo_6m` | Referência para estratégia rápida. |
| Lance urgente 3 meses | BP | `lance_super_agressivo_3m` | Referência para estratégia urgente. |
| Status | campo da base | `status` | Só grupos `Ativo` ou sem status seguem para análise. |

## 5. Filtros que realmente excluem grupos

O Motor 360 executa os filtros abaixo nesta ordem.

### 5.1 Status

Grupo com status diferente de `Ativo` é excluído. Grupo sem status é aceito.

### 5.2 Tipo de bem

O grupo precisa ser compatível com `tipo_bem` do perfil, através de
`compatible_tipo_bem(...)`.

### 5.3 Crédito máximo obrigatório

Se `credito_maximo` (coluna U) estiver vazio, o grupo é marcado como
incompleto e não entra no resultado.

### 5.4 Faixa de crédito por cenário

Para cada grupo são montados os cenários abaixo. Um grupo continua no resultado
quando **pelo menos um** deles cabe na faixa:

```text
Crédito mínimo do grupo (O) <= Crédito contratado <= Crédito máximo do grupo (U)
```

O grupo é excluído por crédito somente se os dois cenários forem incompatíveis.

### 5.5 Parcela inicial

A parcela inicial (AJ) é comparada com a parcela máxima por renda. No estado
atual, parcela acima do limite **não exclui** o grupo: registra o contador
`parcela` e deixa o grupo no resultado como alternativa financeira. Isso é
coerente com a visão 360, mas o operador deve interpretar `dentro_limite_renda`
antes de recomendar a opção.

## 6. Cálculos por cenário

### 6.1 Cenário A: sem lance embutido

```text
Crédito contratado sem embutido =
  Crédito líquido desejado + Recurso próprio + FGTS

Lance total sem embutido = Recurso próprio + FGTS
Percentual de lance sem embutido = Lance total / Crédito contratado
```

Validação de liquidez:

```text
Crédito contratado - Recurso próprio - FGTS = Crédito líquido desejado
```

### 6.2 Cenário B: com lance embutido

Só é criado se a coluna X contiver percentual válido maior que zero e menor que
100%.

```text
Base a preservar = Crédito líquido desejado + Recurso próprio + FGTS
Crédito contratado com embutido = Base a preservar / (1 - percentual embutido)
Valor do embutido = Crédito contratado com embutido x percentual embutido
Lance total com embutido = Recurso próprio + FGTS + Valor do embutido
Percentual de lance com embutido = Lance total com embutido / Crédito contratado
```

Validação de liquidez:

```text
Crédito contratado - Embutido - Recurso próprio - FGTS >= Crédito líquido desejado
```

### 6.3 Cálculo D: custo e saldo devedor

Em cada cenário:

```text
Taxa administrativa = Crédito contratado x Taxa ADM total (AC)
Fundo de reserva = Crédito contratado x Fundo de reserva total (AA)
Saldo devedor = Crédito contratado + Taxa administrativa + Fundo de reserva
Saldo após lance = max(0, Saldo devedor - Lance total)
```

**Importante:** AC e AA não alteram o crédito disponível nem entram na comparação
com U. Elas são usadas apenas para o saldo devedor.

### 6.4 Cálculos B e C: prazo matemático

O motor calcula, para informação, os prazos necessários antes e após o lance:

```text
Prazo mínimo pela parcela desejada = Saldo devedor / Parcela desejada
Prazo mínimo pelo limite de renda = Saldo devedor / Parcela máxima por renda

Prazo após lance pela parcela desejada = Saldo após lance / Parcela desejada
Prazo após lance pelo limite de renda = Saldo após lance / Parcela máxima por renda
```

Esses valores são devolvidos dentro de cada cenário. A coluna F é mostrada no
resultado, mas a comparação automática entre prazo calculado e prazo restante
ainda não elimina nem aprova grupos.

## 7. Classificação de estratégias

Depois da compatibilidade de crédito, o motor monta as estratégias possíveis.

| Estratégia | Condição atual |
|---|---|
| `investment` | Existe parcela inicial e `AJ <= parcela máxima por renda`. |
| `urgent` | Algum cenário válido tem percentual de lance >= BP. |
| `fast` | Algum cenário válido tem percentual de lance >= BO. |
| `moderate` | Algum cenário válido tem percentual de lance >= BN. |
| `conservative` | Algum cenário válido tem percentual de lance >= BM. |
| `long_term` | Algum cenário válido tem percentual de lance >= BL. |

O mesmo grupo pode receber mais de uma estratégia. Exemplo: uma carta pode ser
compatível com investimento, moderada e conservadora ao mesmo tempo.

## 8. Ordenação e destaque

O objetivo declarado seleciona a preferência:

- objetivo iniciado por `Investidor` => preferência `investment`;
- qualquer outro objetivo => preferência `contemplation`.

Depois, os grupos são ordenados por:

1. Grupo que atende a preferência declarada;
2. Grupo dentro do limite de renda;
3. Menor desvio percentual entre AJ e parcela desejada;
4. Menor identificador do grupo, como desempate.

O desvio é calculado apenas quando há parcela inicial e parcela desejada:

```text
desvio percentual = abs(Parcela inicial - Parcela desejada) / Parcela desejada
```

Não há teto de Top 10 no Motor 360: todos os grupos compatíveis por faixa de
crédito são retornados.

## 9. Saída exibida na tela

Cada linha devolvida contém:

- identificação do grupo, administradora e tipo de bem;
- faixa de crédito O a U;
- prazo restante F;
- parcela inicial AJ, desejada e máxima por renda;
- todos os cenários gerados, com crédito contratado, lance, percentual de
  lance, taxa, fundo, saldo e prazos;
- lista de estratégias possíveis;
- indicação de aderência à preferência declarada;
- indicação se a parcela inicial está dentro do limite de renda.

## 10. Escolha final de grupo: estado atual

O Motor 360 atual **analisa e ordena**, mas ainda não possui um botão ou ação
integrada na tabela para selecionar uma carta/grupo e transferi-lo diretamente
para o Estudo Financeiro.

Portanto, a sequência automática termina na lista de grupos viáveis. A etapa
de seleção de carta, criação de cenário e envio ao Estudo Financeiro ainda
precisa ser implementada sobre o resultado do Motor 360.

## 11. Rotas e arquivos de referência

| Responsabilidade | Arquivo / rota |
|---|---|
| Botão e coleta do perfil | `backend/static/js/app.js` (`advanceClientProfile`, `collectClientProfile`) |
| Armazenamento temporário do perfil | `localStorage: crediclass.clientProfile.v1` |
| Rota de cálculo unificado | `POST /api/viabilidade-360/analisar` em `backend/main.py` |
| Motor e filtros | `backend/consortium_viability_engine.py` |
| Fórmulas de crédito, embutido, taxa e fundo | `backend/credit_liquidity.py` |
| Mapeamento da planilha | `backend/sheets_client.py` (`MAPA_GRUPOS_COLUMN_INDEXES`) |
| Tela de apresentação | `backend/static/index.html` e `backend/static/js/app.js` (`renderInvestorAnalysis`) |

## 12. Pendências para o fluxo ficar integralmente 360

1. Fazer o botão avançar sempre abrir a tela Motor 360, inclusive para objetivo
   `Contemplar`.
2. Remover ou migrar a tela/rota legada `contemplar` para evitar dois
   comportamentos distintos.
3. Comparar automaticamente os prazos calculados com F para atribuir status de
   compatibilidade de prazo.
4. Definir se parcela acima do limite deve permanecer como alternativa, ser
   sinalizada em destaque ou ser eliminada em alguma aba específica.
5. Criar ação de “Selecionar carta” no resultado, persistindo o cenário escolhido
   e abrindo o Estudo Financeiro.
6. Integrar filtros de ranking (taxa, prazo, parcela reduzida e outros) ao Motor
   360, sem substituir os filtros financeiros de elegibilidade.
