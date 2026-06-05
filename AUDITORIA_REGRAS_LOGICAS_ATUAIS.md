# Auditoria das Regras Logicas Atuais

Data: 05/06/2026

Objetivo: documentar as regras que existem hoje no codigo para Viabilidade Administradoras, Viabilidade Grupos e Estudo Financeiro. Este documento nao valida se as regras estao corretas para o negocio; ele descreve o que o sistema realmente faz agora.

## 1. Sequencia logica atualmente implementada

Fluxo desejado pelo negocio:

1. Entrevista / dados do cliente.
2. Planos das administradoras.
3. Viabilidade das administradoras.
4. Viabilidade dos grupos das administradoras elegiveis.
5. Estudo financeiro.

Fluxo tecnico atual:

1. A tela Viabilidade Administradoras coleta dados do cliente e chama `/api/viabilidade/administradoras`.
2. O backend busca as administradoras existentes nos grupos carregados da planilha.
3. Para cada administradora, tenta localizar uma regra cadastrada em `configuracoes.administradoras_regras`.
4. Administradoras sem regra cadastrada sao ignoradas.
5. A tela Viabilidade Grupos chama `/api/viabilidade/analisar`.
6. Esse endpoint recalcula a viabilidade das administradoras, filtra os grupos apenas das administradoras elegiveis, depois roda a analise dos grupos.
7. O Estudo Financeiro e aberto no frontend a partir de um grupo selecionado na Viabilidade Grupos.
8. Ao salvar estudo, o backend recalcula parte dos dados financeiros novamente.

Ponto critico: existem calculos financeiros no backend e tambem no frontend. A mesma decisao pode ser apresentada com regras diferentes dependendo da tela.

## 2. Regras atuais de Planos Administradoras

Arquivo principal: `backend/administrator_rules.py`

Cada administradora pode ter uma regra com os campos:

- `administradora`
- `seguro_obrigatorio`
- `idade_maxima`
- `limite_sem_comprovacao_renda`
- `percentual_lance_embutido`
- `tipo_lance_embutido`
- `taxa_adm`
- `possui_negociacao_taxa`
- `fundo_reserva`
- `aceita_saida_fiscal`
- `aceita_fgts`
- `observacoes_operacionais`

Como o sistema localiza uma regra:

- normaliza o nome da administradora;
- remove acentos;
- remove as palavras `CONSORCIO` e `CONSORCIOS`;
- compara com a administradora do grupo;
- se nao encontrar regra, a administradora nao entra na analise.

Regra criada por mim:

- nao existem regras padrao hardcoded;
- as regras devem vir do cadastro em Configuracoes > Planos Administradoras.

## 3. Regras atuais de Viabilidade Administradoras

Arquivo principal: `backend/administrator_feasibility.py`

### 3.1 Dados usados

O sistema usa:

- credito desejado;
- lance proprio;
- FGTS titular + FGTS conjuge, ou `fgts`;
- renda titular + renda conjuge, ou `renda_total`;
- parcela ideal;
- parcela limite;
- data de nascimento titular;
- data de nascimento conjuge;
- opcao considerar lance embutido;
- regra cadastrada da administradora.

### 3.2 Credito a contratar

Regra atual:

```txt
percentual_lance_embutido = regra.percentual_lance_embutido
se usuario escolher nao considerar lance embutido:
  percentual_lance_embutido = 0

credito_a_contratar =
credito_desejado / (1 - percentual_lance_embutido)
```

Limitacao:

- o percentual e limitado entre 0% e 95%;
- nao ha uso real de `tipo_lance_embutido`, apesar do campo existir.

### 3.3 Lance embutido

Regra atual:

```txt
lance_embutido_valor =
credito_a_contratar * percentual_lance_embutido
```

### 3.4 FGTS

Regra atual:

```txt
fgts_total = fgts_titular + fgts_conjuge

se administradora aceita FGTS:
  fgts_utilizado = fgts_total
senao:
  fgts_utilizado = 0
```

### 3.5 Lance total

Regra atual:

```txt
lance_total =
lance_embutido_valor + lance_proprio + fgts_utilizado
```

```txt
lance_maximo_percentual =
lance_total / credito_a_contratar
```

### 3.6 Prazo minimo

Regra atual:

```txt
taxa_adm_valor = credito_a_contratar * taxa_adm
fundo_reserva_valor = credito_a_contratar * fundo_reserva

prazo_minimo =
(credito_a_contratar + taxa_adm_valor + fundo_reserva_valor - lance_total)
/ parcela_limite
```

Depois o prazo minimo e travado para nao ficar abaixo de zero.

Ponto suspeito:

- o sistema subtrai `lance_total` para calcular prazo minimo;
- precisa confirmar se, no negocio, lance antes da contemplacao deve reduzir esse calculo dessa forma.

### 3.7 Idade

Regra atual:

- calcula idade do titular e do conjuge se informados;
- se nenhuma idade foi informada, `idade_compativel = false` e alerta `idade_nao_validada`;
- se `idade_maxima` existir, todos os informados precisam estar abaixo ou igual ao limite;
- se `idade_maxima` nao existir e alguma idade foi informada, idade passa.

### 3.8 Renda

Regra atual:

```txt
renda_compativel =
parcela_ideal * 3 <= renda_total
```

Ou seja, a renda precisa ser no minimo 3 vezes a parcela ideal.

Ponto suspeito:

- usa parcela ideal, nao parcela limite;
- nao considera regra especifica de comprovacao de renda por administradora alem do limite de credito.

### 3.9 Limite sem comprovacao de renda

Regra atual:

```txt
se limite_sem_comprovacao_renda nao existe:
  limite_compativel = true
senao:
  credito_a_contratar <= limite_sem_comprovacao_renda
```

Ponto suspeito:

- isso esta tratando o limite como reprova automatica.
- Pela regra de negocio, pode ser que acima do limite apenas exija comprovacao de renda, e nao reprove.

### 3.10 FGTS permitido

Regra atual:

```txt
fgts_permitido =
fgts_total <= 0 ou administradora.aceita_fgts
```

### 3.11 Lance embutido permitido

Regra atual:

```txt
lance_embutido_permitido =
percentual_lance_embutido > 0
```

Ponto critico:

- se o cliente escolher nao considerar lance embutido, o percentual vira 0;
- entao `lance_embutido_permitido` vira false;
- isso pode reprovar administradoras mesmo quando o cliente nao quer usar lance embutido.

### 3.12 Elegibilidade da administradora

Regra atual:

```txt
elegivel = true somente se todos forem true:
- idade_compativel
- renda_compativel
- parcela_compativel
- limite_compativel
- fgts_permitido
- lance_embutido_permitido
```

Pontos suspeitos:

- `seguro_obrigatorio` apenas gera alerta; nao reprova.
- `aceita_saida_fiscal` esta cadastrado, mas nao participa da elegibilidade.
- `possui_negociacao_taxa` esta cadastrado, mas nao participa da elegibilidade.
- `tipo_lance_embutido` esta cadastrado, mas nao muda formula.
- ausencia de idade reprova a administradora na pratica, porque `idade_compativel` fica false.

## 4. Regras atuais de Viabilidade Grupos

Arquivo principal: `backend/viabilidade.py`

### 4.1 Primeiro filtro feito pelo endpoint

Arquivo: `backend/main.py`

Antes de analisar grupos:

1. Busca todas as administradoras presentes nos grupos carregados.
2. Analisa administradoras com as regras cadastradas.
3. Monta lista de administradoras elegiveis.
4. Filtra os grupos para ficar somente com grupos de administradoras elegiveis.
5. Filtra ainda pelo tipo de bem solicitado.
6. So depois chama `analyze_viabilidade`.

Ponto critico:

- se nenhuma administradora tiver regra cadastrada ou elegivel, nenhum grupo sera analisado.

### 4.2 Perfil por prazo desejado

Arquivo: `backend/lance_reference.py`

Regra atual:

- ate 3 meses: `Agressivo`
- ate 6 meses: `Moderado`
- ate 12 meses: `Conservador`
- ate 24 meses: `Super Conservador`
- acima de 24 meses: `Investidor`

### 4.3 Compatibilidade de tipo de bem

Regra atual:

- se tipo pedido contem imovel, grupo precisa conter imovel;
- se auto/veiculo, grupo precisa conter auto ou veiculo;
- se servico, grupo precisa conter servico;
- se pesado, grupo precisa conter pesado;
- se outro, grupo precisa conter outro.

### 4.4 Filtros obrigatorios de grupo

Um grupo e ignorado se:

- `credito_maximo < credito_desejado`;
- status diferente de `Ativo`;
- prazo restante menor ou igual a zero;
- tipo de bem nao compativel.

Ponto suspeito:

- se `credito_maximo` esta vazio ou zerado, grupo e descartado.
- o filtro inicial nao verifica `credito_minimo`; isso fica para score/aprovacao depois.

### 4.5 FGTS no grupo

Regra atual:

```txt
se grupo.fgts = true:
  fgts_utilizado = fgts_total
senao:
  fgts_utilizado = 0
```

### 4.6 Lance embutido no grupo

Regra atual:

```txt
se grupo.lance_embutido = true:
  percentual_lance_embutido = grupo.percentual_lance_embutido
senao:
  percentual_lance_embutido = 0
```

Se percentual for menor que 0 ou maior/igual a 100%, vira 0.

### 4.7 Credito contratado e credito disponivel

Regra atual:

```txt
credito_contratado =
credito_desejado / (1 - percentual_lance_embutido)

lance_embutido =
credito_contratado * percentual_lance_embutido

credito_disponivel =
credito_contratado - lance_embutido
```

Na pratica, credito disponivel volta para o credito desejado quando a formula fecha.

### 4.8 Lance total e percentual de lance

Regra atual:

```txt
lance_total =
lance_embutido + lance_proprio + fgts_utilizado

percentual_lance =
lance_total / credito_contratado
```

### 4.9 Parcela estimada

Regra atual:

```txt
taxa_administrativa_valor = credito_contratado * taxa_adm
fundo_reserva_valor = credito_contratado * fundo_reserva

parcela_estimada =
(credito_contratado + taxa_administrativa_valor + fundo_reserva_valor)
/ prazo_total
```

Ponto critico:

- usa `prazo_total`, nao `prazo_restante`.
- nao subtrai lance.
- e diferente da logica de prazo minimo da administradora.

### 4.10 Historico dos ultimos 12 meses

Regra atual:

- pega os 12 meses mais recentes existentes no historico;
- calcula media do maior lance;
- calcula media do menor lance;
- calcula media de quantidade de contemplacoes;
- soma quantidade de contemplacoes.

### 4.11 Referencias de lance

Arquivo: `backend/lance_reference.py`

Regras atuais:

- Investidor: usa `percentual_lance_fixo`, limitado a no maximo 20%.
- Super Conservador: segundo menor `menor_lance` dos ultimos 12 meses + 0,25 p.p.
- Conservador: segundo menor `menor_lance` dos ultimos 12 meses + 0,25 p.p.
- Moderado: segundo menor `menor_lance` dos ultimos 6 meses + 0,25 p.p.
- Agressivo: maior `menor_lance` dos ultimos 3 meses + 0,25 p.p.

Ponto suspeito:

- Super Conservador e Conservador usam a mesma regra.
- Agressivo usa o maior dos menores lances, nao maior lance.
- O incremento fixo e 0,25 ponto percentual.

### 4.12 Scores de ranking

O sistema calcula:

- `credito_score`
- `parcela_score`
- `lance_score`
- `prazo_score`
- `historico_score`

Formula da afinidade:

```txt
afinidade_score =
credito_score * 25%
+ parcela_score * 25%
+ lance_score * 25%
+ prazo_score * 15%
+ historico_score * 10%
```

Depois divide por 100 e retorna como percentual decimal.

### 4.13 Selo do grupo

Regra atual:

- >= 90: Excelente
- >= 80: Muito Bom
- >= 70: Bom
- >= 60: Regular
- abaixo de 60: Baixa Compatibilidade

### 4.14 Aprovacao do grupo

Regra atual:

```txt
grupo_aprovado = true somente se:
- credito_minimo <= credito_desejado <= credito_maximo
- parcela_estimada * 3 <= renda_total
- parcela_estimada <= parcela_desejada
- percentual_lance >= lance_referencia
- prazo_restante >= prazo_desejado
- FGTS permitido
- lance embutido permitido
- idade compativel, se idade foi informada
```

Ponto critico:

- se idade nao foi informada, grupo pode aprovar, mas checklist marca idade como false.
- na administradora, idade ausente reprova; no grupo, idade ausente nao reprova.
- isso e uma contradicao.

### 4.15 Cenario viavel

Regra atual:

```txt
cenario_viavel = true se existir pelo menos um grupo aprovado
```

Essa regra esta alinhada com a correcao solicitada anteriormente.

### 4.16 Ranking retornado

Regra atual:

- todos os grupos analisados sao ordenados por afinidade;
- retorna somente os 10 primeiros;
- isso inclui grupos nao aprovados se eles ficarem no top 10.

Ponto suspeito:

- a tela pode mostrar ranking com grupo nao aprovado junto de grupos aprovados.

## 5. Regras atuais do Estudo Financeiro

Existem duas fontes de calculo:

1. Frontend: `backend/static/js/app.js`
2. Backend: `backend/estudos.py`

Isso e um problema estrutural.

### 5.1 Estudo Financeiro no frontend

Funcoes principais:

- `buildFinancialProjection`
- `renderStudyClient`
- `renderStudyGroup`
- `renderStudySummary`
- `renderStudyStrategies`
- `renderStudyRecommendations`
- `openFinancialStudy`

Regra atual do frontend:

```txt
creditoContratado =
viabilityItem.credito_contratado
ou group.credito_maximo
ou payload.credito_desejado

percentualEmbutido = group.percentual_lance_embutido
lanceEmbutido = creditoContratado * percentualEmbutido
lanceProprio = payload.lance_proprio
fgts = payload.fgts
lanceTotal = lanceEmbutido + lanceProprio + fgts
creditoDisponivel = creditoContratado - lanceEmbutido
prazo = group.prazo_restante ou group.prazo_total
custoTotal = creditoContratado * (1 + taxa_adm + fundo_reserva)
parcela = custoTotal / prazo
percentualLanceTotal = lanceTotal / creditoContratado
lanceReferencia = viabilityItem.lance_referencia_percentual
```

Pontos criticos:

- o frontend sempre usa `group.percentual_lance_embutido`, mesmo que a viabilidade tenha zerado ou limitado esse percentual.
- o frontend usa `payload.fgts` integral, sem conferir se grupo/administradora permite FGTS.
- o frontend usa `group.credito_maximo` como fallback para credito contratado.

### 5.2 Estrategias no frontend

Regra atual:

- usa os campos do grupo:
  - `lance_investidor`
  - `lance_super_conservador`
  - `lance_conservador`
  - `lance_moderado`
  - `lance_agressivo`

Para cada estrategia:

```txt
lanceTotal = creditoContratado * percentual
lanceProprio = max(0, lanceTotal - lanceEmbutido)
```

Ponto critico:

- essas estrategias podem nao ser iguais as referencias calculadas no backend por `lance_reference.py`.

### 5.3 Recomendacao no frontend

Regra atual:

- recomendacao forte se afinidade >= 90%;
- recomendacao moderada se afinidade >= 80%;
- recomendacao com acompanhamento abaixo disso;
- estrategia recomendada e a primeira cujo percentual e igual ao `lanceReferencia`; se nao achar, pega a primeira estrategia.

Ponto critico:

- comparar percentuais por igualdade exata pode falhar.
- se nao achar a estrategia correta, cai em `Investidor` ou primeira estrategia.

### 5.4 Estudo Financeiro no backend

Arquivo: `backend/estudos.py`

Ao salvar estudo, backend recalcula:

```txt
percentual_embutido = grupo.percentual_lance_embutido
credito_original =
credito_desejado / (1 - percentual_embutido)

lance_embutido =
credito_original * percentual_embutido

recurso_proprio =
lance_proprio + fgts

valor_total_lance =
lance_embutido + recurso_proprio

percentual_lance_total =
valor_total_lance / credito_original

credito_disponivel =
credito_original - lance_embutido

prazo =
grupo.prazo_restante ou grupo.prazo_total ou prazo_desejado

custo_total =
credito_original * (1 + taxa_adm + fundo_reserva)

parcela_inicial =
custo_total / prazo
```

Pontos criticos:

- backend tambem usa FGTS integral sem validar permissao.
- backend tambem usa percentual de lance embutido direto do grupo.
- backend nao usa o item de viabilidade selecionado para manter consistencia.
- backend nao recebe/salva a estrategia recomendada pela viabilidade; define sempre `Perfil definido na Viabilidade`.

### 5.5 Estrategias no backend

Regra atual:

- calcula referencias por `calculate_lance_references`;
- monta estrategias:
  - Investidor
  - Super Conservador
  - Conservador
  - Moderado
  - Agressivo

Para cada estrategia:

```txt
valor_total_lance = credito_original * percentual
lance_embutido = min(lance_embutido_base, valor_total_lance)
lance_proprio = max(0, valor_total_lance - lance_embutido)
```

Ponto critico:

- esse calculo pode gerar recurso proprio diferente do que o cliente disse que tem.
- nao limita lance proprio ao recurso proprio disponivel.

## 6. Principais conflitos logicos encontrados

### 6.1 Falta uma separacao formal entre entrevista, administradora e grupo

Hoje a entrevista aparece dentro de Viabilidade Administradoras e Viabilidade Grupos. Ainda nao existe um objeto unico de entrevista que siga pelo fluxo inteiro.

Impacto: os dados podem divergir entre etapas.

### 6.2 Viabilidade Administradoras reprova quando lance embutido nao e usado

Se `considerar_lance_embutido = false`, o percentual vira 0 e `lance_embutido_permitido` vira false. Isso reprova a administradora.

Provavel correcao: se o cliente nao usa lance embutido, o criterio deveria ser aprovado ou nao aplicavel.

### 6.3 Idade ausente tem tratamento diferente em administradoras e grupos

Administradora:

- idade ausente gera `idade_compativel = false`;
- isso reprova.

Grupo:

- idade ausente nao reprova o grupo;
- checklist marca idade como false.

Provavel correcao: definir uma regra unica.

### 6.4 Limite sem comprovacao de renda esta como reprovacao automatica

Hoje:

- se credito a contratar passa do limite, administradora reprova.

Mas pelo negocio pode significar apenas:

- exige comprovacao de renda.

### 6.5 Campos cadastrados de administradora nao entram na decisao

Campos sem uso decisorio real:

- `tipo_lance_embutido`
- `aceita_saida_fiscal`
- `possui_negociacao_taxa`
- `observacoes_operacionais`

### 6.6 Taxa ADM e fundo de reserva podem divergir entre administradora e grupo

Na administradora existe taxa/fundo.
No grupo tambem existe taxa/fundo.

Hoje:

- viabilidade de administradora usa taxa/fundo da administradora;
- viabilidade de grupo usa taxa/fundo do grupo;
- nao existe regra clara de prioridade.

### 6.7 Parcela estimada usa prazo total, nao prazo restante

Na Viabilidade Grupos:

```txt
parcela_estimada = custo_total / prazo_total
```

Mas no estudo financeiro:

```txt
parcela = custo_total / prazo_restante ou prazo_total
```

Isso pode gerar parcela diferente entre ranking e estudo.

### 6.8 Estudo financeiro recalcula em vez de congelar a decisao da viabilidade

O estudo recalcula credito, lance, parcela e estrategias usando dados do grupo.

Impacto: o estudo pode nao refletir exatamente o grupo aprovado/rankeado.

### 6.9 Estrategia recomendada nao esta persistida corretamente

Backend salva:

```txt
estrategia_recomendada = "Perfil definido na Viabilidade"
```

Ou seja, nao salva o nome real da estrategia recomendada.

### 6.10 Ranking pode mostrar grupo nao aprovado

O backend ordena todos os grupos por afinidade e retorna os 10 primeiros.

Impacto: pode aparecer grupo com boa afinidade mas reprovado.

### 6.11 Super Conservador e Conservador usam a mesma formula

Ambos usam:

```txt
segundo menor menor_lance dos ultimos 12 meses + 0,25 p.p.
```

Pode estar incorreto.

### 6.12 Agressivo usa maior dos menores lances, nao maior lance

Regra atual:

```txt
agressivo = maior menor_lance dos ultimos 3 meses + 0,25 p.p.
```

Precisa validar se deveria usar maior lance, menor lance, media ou outro criterio.

### 6.13 Recursos do cliente nao limitam estrategias

As estrategias calculam lance proprio necessario, mas nao verificam se o cliente tem recurso suficiente para aquela estrategia.

## 7. Regras criadas por inferencia, que precisam validacao do negocio

Estas regras foram criadas no codigo sem garantia de aderencia ao processo oficial:

1. Renda compativel = parcela * 3 <= renda.
2. Prazo minimo da administradora subtrai lance total.
3. Limite sem comprovacao de renda reprova automaticamente.
4. Lance embutido precisa ser maior que zero para administradora ser elegivel.
5. Scores com pesos 25/25/25/15/10.
6. Selo por faixas 90/80/70/60.
7. Referencias de lance por segundo menor menor_lance.
8. Incremento fixo de 0,25 p.p.
9. Super Conservador = Conservador.
10. Agressivo = maior menor_lance dos ultimos 3 meses.
11. Estudo financeiro recalcula a partir do grupo, nao do resultado aprovado.
12. Estrategia recomendada por igualdade exata de percentual no frontend.

## 8. Recomendacao para proxima correcao

Antes de implementar novas telas, recomendo travar a arquitetura logica assim:

1. Criar um objeto unico `EntrevistaCliente`.
2. Criar `PlanosAdministradoras` como fonte oficial das regras fixas.
3. Criar `RegrasPorGrupo` / `ParametrosGrupo` para dados variaveis.
4. Fazer Viabilidade Administradoras retornar:
   - aprovado/reprovado;
   - criterios obrigatorios;
   - criterios informativos;
   - alertas.
5. Fazer Viabilidade Grupos receber somente administradoras aprovadas.
6. Fazer Estudo Financeiro usar o resultado congelado da viabilidade, sem recalcular regras divergentes.
7. Centralizar todas as formulas no backend.
8. Frontend apenas exibe resultados e coleta entrada humana.

