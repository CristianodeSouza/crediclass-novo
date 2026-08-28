# Motor 360: lógica atual de filtragem dos grupos

Data de referência da documentação: 27/08/2026

Objetivo deste documento:
- registrar, sem reinterpretar, a lógica que o sistema está usando hoje para filtrar grupos no Motor 360;
- deixar explícito quais campos do Perfil do Cliente entram no cálculo;
- mostrar quais colunas da base participam de cada etapa;
- separar o que é filtro eliminatório do que é apenas informação, classificação ou ordenação;
- facilitar a auditoria dos erros relatados antes de qualquer nova mudança de regra.

Arquivos-fonte desta documentação:
- `backend/consortium_viability_engine.py`
- `backend/motor360_math.py`
- `backend/main.py`
- `backend/static/js/app.js`

## 1. Entrada usada pelo Motor 360

Hoje o front monta o payload na função `collectClientProfile()` em `backend/static/js/app.js`.

Os principais campos enviados para `/api/viabilidade-360/analisar` são:
- `credito_desejado`
- `prazo_desejado`
- `objetivo`
- `tipo_bem`
- `tipo_bem_explicit`
- `renda_total`
- `parcela_desejada`
- `parcela_limite`
- `lance_proprio`
- `lance_proprio_participantes`
- `lance_proprio_manual`
- `own_resources_source`
- `fgts`
- `titulares`

## 2. Como o Perfil do Cliente é consolidado

O backend consolida os dados assim:

### 2.1 Crédito desejado
- Vem de `credito_desejado`.
- Se for vazio, zero ou inválido, o Motor 360 aborta com `credito_desejado_invalido`.

### 2.2 Renda total
- Vem de `renda_total`.
- Se for vazio, zero ou inválido, o Motor 360 aborta com `renda_total_invalida`.

### 2.3 Parcela desejada
- Prioridade:
  1. `parcela_desejada`
  2. `parcela_ideal`
- Se o valor final for vazio, zero ou inválido, o Motor 360 aborta com `parcela_desejada_invalida`.

### 2.4 Parcela máxima
- Prioridade:
  1. `parcela_limite`
  2. `renda_total * 30%`
- Se o resultado final for menor ou igual a zero, o Motor 360 aborta com `parcela_maxima_invalida`.

### 2.5 Recursos próprios
- O backend aceita três origens:
  - `lance_proprio`
  - `lance_proprio_participantes`
  - `lance_proprio_manual`
- A escolha depende de `own_resources_source`:
  - `participants`: usa `lance_proprio_participantes`
  - `manual`: usa `lance_proprio_manual`
  - qualquer outro caso: usa `lance_proprio`, senão `participants`, senão `manual`

Regra importante:
- se `own_resources_source` não for `participants` nem `manual`, e existirem ao mesmo tempo `manual` e `participants` com valores diferentes, o backend interrompe com `conflito_recurso_proprio`.

### 2.6 FGTS
- Vem de `fgts`.
- Se vier vazio, vira `0`.

### 2.7 Objetivo do consórcio
- O objetivo é lido do campo `objetivo`.
- Hoje ele é transformado em uma preferência de apresentação por `map_declared_objective_to_preference()`.

Mapeamento atual:
- texto contendo `urgente` ou `3 mes` -> `urgent`
- texto contendo `rapido` ou `6 mes` -> `fast`
- texto contendo `moderado` ou `12 mes` -> `moderate`
- texto contendo `conservador` ou `24 mes` -> `conservative`
- texto contendo `36 mes` -> `long_term`
- texto começando com `investidor` -> `investment`

Observação importante:
- `investment` e `long_term` não são a mesma chave interna.
- Para a capacidade de contemplação e para os perfis internos, o sistema usa `long_term`.
- Se o texto vier como `Investidor - 36 meses`, o código tende a reconhecer `36 mes` antes e mapear para `long_term`.
- Se vier somente começando com `Investidor` sem o trecho de 36 meses, mapeia para `investment`.

### 2.8 Tipo de bem
- O filtro por tipo só é aplicado se `tipo_bem_explicit` for `true`.
- Se o campo estiver vazio, o Motor 360 não elimina grupos por tipo de bem.

## 3. Colunas da base que o Motor 360 carrega

O backend declara como colunas usadas:
- `A` Administradora
- `B` Grupo
- `C` Tipo de bem
- `F` Prazo remanescente
- `O` Menor crédito
- `U` Maior crédito
- `V` Indexador
- `W` Modalidades de assembleia
- `X` Lance embutido
- `Y` Base de cálculo do embutido
- `Z` Modalidades do embutido
- `AA` Fundo de reserva total
- `AC` Taxa ADM total
- `AJ` Parcela inicial
- `AK` Parcela após lance
- `AL` Parcela reduzida
- `BL` Investidor - 36 meses
- `BM` Conservador - 24 meses
- `BN` Moderado - 12 meses
- `BO` Rápido - 6 meses
- `BP` Urgente - 3 meses

## 4. Colunas que realmente participam da decisão

Hoje a decisão do Motor 360 usa oficialmente:
- `A`
- `B`
- `F`
- `O`
- `U`
- `X`
- `AA`
- `AC`

E usa `C` também, mas só quando o tipo de bem foi informado explicitamente no Perfil do Cliente.

Importante:
- `AJ`, `AK` e `AL` não aprovam nem eliminam grupos nesta etapa.
- `BL:BP` não eliminam grupos da pré-seleção; hoje elas ficam como classificação informativa.

## 5. Etapas reais do filtro

O Motor 360 percorre todos os grupos e aplica as etapas abaixo.

### Etapa 1. Status
Regra:
- somente grupos com `status = Ativo`

Se reprovar:
- sai do fluxo imediatamente.

### Etapa 2. Tipo de bem
Regra:
- só roda se o cliente tiver informado explicitamente `tipo_bem`
- usa `compatible_tipo_bem("", tipo_bem_do_grupo, tipo_bem_solicitado)`

Se o cliente não informou o tipo:
- todos os grupos passam nessa etapa.

### Etapa 3. Montagem dos cenários financeiros

Para cada grupo, o backend monta até 2 cenários independentes:
- `without_embedded`
- `with_embedded`

Esses cenários são calculados em `calculate_scenario()` no arquivo `backend/motor360_math.py`.

#### 3.1 Cenário sem embutido
- `credito_contratado = credito_liquido_desejado`

#### 3.2 Cenário com embutido
- só existe se `X` for válido e estiver entre `0` e `1`
- fórmula:
  - `credito_contratado = credito_liquido_desejado / (1 - X)`

Se `X` estiver ausente ou inválido:
- o cenário com embutido não é criado;
- o grupo não é automaticamente excluído por isso;
- ele apenas perde esse cenário específico.

## 6. Fórmulas financeiras usadas em cada cenário

### 6.1 Lance embutido
- `valor_lance_embutido = credito_contratado * X`

### 6.2 Taxa administrativa
- `taxa_administracao = credito_contratado * AC`

### 6.3 Fundo de reserva
- `fundo_reserva = credito_contratado * AA`

Observação:
- se `AA` vier vazio, o sistema assume `0` para manter o cálculo;
- isso aparece como aviso informativo na auditoria.

### 6.4 Saldo devedor
- `saldo_devedor = credito_contratado + taxa_administracao + fundo_reserva`

### 6.5 Lance do cliente
- `lance_cliente_total = recurso_proprio + fgts`

### 6.6 Lance total do cenário
- `lance_total_cenario = recurso_proprio + fgts + valor_lance_embutido`

### 6.7 Percentual de lance do cliente
- `percentual_lance_cliente = lance_cliente_total / credito_contratado`

### 6.8 Percentual de lance efetivo do cenário
- `percentual_lance_efetivo = lance_total_cenario / credito_contratado`

### 6.9 Saldo após lance
- `saldo_apos_lance = max(0, saldo_devedor - lance_total_cenario)`

### 6.10 Crédito líquido projetado
- `credito_liquido_projetado = credito_contratado - valor_lance_embutido`

### 6.11 Liquidez preservada
- o código considera `liquidez_preservada = true` quando o crédito líquido projetado bate exatamente com o crédito líquido desejado, arredondado em centavos.

Na prática:
- no cenário sem embutido, isso costuma ser verdadeiro;
- no cenário com embutido, também tende a ser verdadeiro porque a fórmula foi montada exatamente para preservar a base líquida.

### 6.12 Prazo calculado para limite de renda
- `prazo_apos_lance_limite_renda = ceil(saldo_apos_lance / parcela_maxima)`

### 6.13 Compatibilidade de prazo/renda
- `term_compatible = prazo_remanescente >= ceil(saldo_apos_lance / parcela_maxima)`

Observação crítica:
- hoje o backend usa a `parcela_maxima` para aprovar prazo/renda;
- a `parcela_desejada` é calculada e auditada, mas não é o corte eliminatório principal nessa etapa.

### 6.14 Parcela inicial exibida
- calculada depois pelo backend com:
  - `parcela_inicial = saldo_devedor / prazo_remanescente`

### 6.15 Parcela pós-contemplação exibida
- calculada depois pelo backend com:
  - `(saldo_devedor - parcela_inicial - lance_total_cenario) / (prazo_remanescente - 1)`

## 7. Regras eliminatórias por etapa

### 7.1 Filtro de crédito
Um cenário entra como compatível por crédito quando:
- foi criado com sucesso;
- `credit_compatible = true`
- `liquidez_preservada = true`

E `credit_compatible = true` significa:
- `O <= credito_contratado <= U`

Se nenhum cenário do grupo passar nisso:
- o grupo é eliminado por crédito.

### 7.2 Filtro de prazo/renda
Depois do crédito, o backend mantém apenas cenários que tenham:
- `data_complete = true`
- `term_compatible = true`

Hoje `data_complete` exige:
- `O` informado
- `U` informado
- `AC` informado
- `F` informado

Observação:
- `AA` não entra em `data_complete`; vazio em `AA` não bloqueia.

Se o grupo passou no crédito mas nenhum cenário passou em prazo/renda:
- ele sai da pré-seleção;
- mas continua aparecendo em `credit_items`.

### 7.3 Regras da administradora
Hoje não existe filtro adicional implementado.

O código registra a etapa, mas faz `pass-through`.

### 7.4 Contemplação
Hoje a contemplação não elimina a pré-seleção final.

O código até calcula:
- se o percentual de lance efetivo atingiu alguma faixa `BL:BP`
- quais estratégias o grupo atende

Mas no fim:
- a pré-seleção usa `term_scenarios`
- não usa `contemplation_scenarios` como corte final

Resumo prático:
- contemplação hoje classifica e enriquece o card;
- não bloqueia a entrada do grupo em `items`.

## 8. Como a capacidade de contemplação é calculada hoje

O backend usa `_contemplation_capacity(group)`.

Janelas internas:
- `urgent` = 3 meses
- `fast` = 6 meses
- `moderate` = 12 meses
- `conservative` = 24 meses
- `long_term` = 36 meses

Para cada janela ele faz:
- pega os últimos `N` registros do histórico do grupo
- soma `qtd_contemplacoes`
- calcula:
  - `total_contemplacoes`
  - `meses_contemplados`
  - `media_contemplacoes = total_contemplacoes / quantidade_de_meses_da_janela`

Também grava:
- `regra_minima = 2`
- `atinge_regra_minima = media_contemplacoes >= 2`

Importante:
- a regra atual é de média de contemplações na janela;
- não é “teve contemplação em pelo menos 2 meses distintos”;
- por isso um grupo pode mostrar, por exemplo, `35 contemplações ÷ 3 meses = 11,67`.

## 9. Como as faixas BL:BP são usadas hoje

As colunas `BL:BP` viram percentuais de referência de perfis:
- `BL` Investidor - 36 meses
- `BM` Conservador - 24 meses
- `BN` Moderado - 12 meses
- `BO` Rápido - 6 meses
- `BP` Urgente - 3 meses

Para cada cenário, o Motor 360:
- calcula o percentual total de lance do cenário;
- compara com cada faixa disponível;
- registra quais perfis foram atingidos.

Isso alimenta:
- `perfis_contemplacao`
- `compatible_contemplation_strategies`
- `best_contemplation_strategy`

Mas isso hoje é usado como:
- informação de perfil;
- destaque visual;
- classificação informativa;
- seleção da “capacidade de contemplações” mais aderente à preferência.

Não é usado como corte eliminatório final da pré-seleção.

## 10. Como o objetivo do cliente influencia hoje

O objetivo do cliente hoje influencia em 3 pontos:

### 10.1 Preferência de apresentação
- gera `presentation_preference`

### 10.2 Escolha do destaque
- se o grupo atende vários perfis, o sistema tenta destacar o perfil igual ao objetivo do cliente

### 10.3 Seleção da capacidade de contemplações exibida
- `capacidade_contemplacoes_selecionada` tenta usar a janela do objetivo

O objetivo hoje não faz:
- corte eliminatório direto por perfil;
- exclusão automática de grupos que não batem com a faixa BL:BP do objetivo;
- alteração da regra de crédito;
- alteração da regra de prazo/renda.

## 11. Diferença entre `items`, `credit_items` e `composition_items`

### 11.1 `items`
São os grupos pré-selecionados de fato.

Para entrar aqui, o grupo precisa ter ao menos um mesmo cenário que passe:
- crédito
- liquidez
- prazo/renda

### 11.2 `credit_items`
São os grupos que passaram em crédito, mas podem ter falhado depois em prazo/renda.

Por isso:
- um grupo pode aparecer no bloco “compatíveis por crédito” e não aparecer entre os grupos viáveis.

### 11.3 `composition_items`
São grupos cuja cota individual não atende o crédito desejado, mas cuja faixa máxima pode justificar composição de múltiplas cotas.

Regra atual para entrar como candidato à composição:
- `U < credito_desejado`
- `U * 50 >= credito_desejado`
- `AC` informado
- `F` informado
- o grupo precisa permitir que pelo menos uma composição calculada chegue ao crédito desejado dentro do teto de 50 cotas

Importante:
- esse bloco é separado dos grupos compatíveis por crédito;
- ele não deve conter grupos que já atendem sozinhos o crédito.

## 12. Ordenação final aplicada hoje

Depois dos filtros, o backend ordena por:
1. maior prazo remanescente
2. menor taxa administrativa total
3. nome da administradora
4. número do grupo

Importante:
- isso é ordem preliminar;
- não é um ranking comercial definitivo.

## 13. Como a auditoria reflete o fluxo

A rota do Motor 360 é:
- `POST /api/viabilidade-360/analisar`

As auditorias ficam disponíveis em:
- `GET /api/viabilidade-360/auditorias/{audit_id}`
- `GET /api/viabilidade-360/auditorias/{audit_id}/exportar.md`
- `GET /api/viabilidade-360/auditorias/{audit_id}/exportar.pdf`

As etapas mostradas no front hoje são consolidadas assim:
- Etapa 1: Status
- Etapa 2: Tipo de bem
- Etapa 3: Faixa de crédito
- Etapa 4: Prazo e renda
- Etapa 5: Pré-seleção
- Etapa 6: Classificação de contemplação
- Etapa 7: Ordem preliminar

Observação importante:
- internamente o código ainda calcula também uma etapa técnica de “regras da administradora” e uma verificação de contemplação por cenário;
- mas a auditoria final exibida ao usuário substitui isso pelo bloco consolidado de `preselection` e pela `classificacao de contemplacao` apenas informativa.

## 14. Motivos de exclusão mais comuns hoje

Os motivos mais usados pelo backend são:
- `status_inativo`
- `status_nao_informado`
- `tipo_bem_incompativel`
- `credito_fora_da_faixa`
- `prazo_remanescente_insuficiente`
- `credito_liquido_nao_preservado`
- `credito_minimo_nao_informado`
- `credito_maximo_nao_informado`
- `taxa_administracao_nao_informada`
- `prazo_restante_nao_informado`
- `percentual_x_ausente`
- `percentual_x_invalido`

## 15. Regras que são apenas informativas hoje

O sistema hoje trata como informativo, e não como bloqueio:
- `AA` vazio: assume fundo de reserva zero
- `BL:BP` ausentes: grupo pode seguir na pré-seleção, mas sem classificação completa
- `AJ`, `AK`, `AL`: servem de referência visual e comparativa

## 16. Pontos que merecem revisão porque podem explicar divergências no front

Sem alterar comportamento, estes são os pontos do código atual que mais podem gerar diferença entre expectativa de negócio e resultado real:

### 16.1 O objetivo do cliente hoje não elimina grupos
- ele prioriza apresentação e classificação;
- não filtra de forma dura por `Urgente`, `Rápido`, `Moderado`, `Conservador` ou `Investidor`.

### 16.2 A etapa de contemplação hoje não elimina a pré-seleção
- o backend calcula as faixas;
- mas a lista final de `items` depende de crédito + prazo/renda, não de BL:BP.

### 16.3 A regra de contemplação atual é média de contemplações, não contagem de meses contemplados
- isso pode divergir da regra de negócio desejada em alguns prints e conversas anteriores.

### 16.4 Prazo/renda usa `parcela_maxima`
- não usa como corte principal a `parcela_desejada`.

### 16.5 `AA` vazio vira zero
- isso evita exclusão, mas pode mudar saldo, parcela e prazo calculado.

### 16.6 O bloco de composição é intencionalmente separado
- ele não lista grupos que já passaram em crédito com 1 cota;
- por isso ele pode ficar vazio mesmo quando existe tabela de “compatíveis por crédito, mas eliminados por prazo/renda”.

## 17. Resumo executivo da lógica atual

Hoje o Motor 360 funciona assim:
1. recebe o Perfil do Cliente consolidado pelo front;
2. valida crédito, renda e parcela;
3. define os recursos próprios e o FGTS;
4. lê todos os grupos com histórico;
5. elimina grupos inativos;
6. elimina por tipo de bem apenas se o cliente informou o tipo explicitamente;
7. monta dois cenários por grupo: sem embutido e com embutido;
8. aprova crédito quando o `credito_contratado` cai entre `O` e `U`;
9. aprova prazo/renda quando `F >= ceil(saldo_apos_lance / parcela_maxima)`;
10. considera a contemplação como classificação informativa, não como exclusão final;
11. envia:
   - `items`: grupos pré-selecionados
   - `credit_items`: grupos compatíveis por crédito
   - `composition_items`: candidatos à composição de múltiplas cotas

## 18. Conclusão

Este documento descreve a lógica atual do sistema, não a lógica de negócio desejada.

Se a próxima etapa for corrigir o Motor 360, a recomendação é usar este documento como linha-base e comparar item por item com:
- a regra comercial esperada;
- os prints de divergência;
- as auditorias reais que o sistema está gerando.
