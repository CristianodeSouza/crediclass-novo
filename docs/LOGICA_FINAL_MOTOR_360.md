# Lógica Final do Motor 360

## Objetivo deste documento

Este documento descreve a lógica atualmente executada pelo código após o operador clicar em **Avançar para Motor de Inteligência** no Perfil do Cliente. O foco é explicar, em ordem, os dados recebidos, filtros aplicados, colunas da planilha usadas, fórmulas e critérios que produzem a lista final de grupos.

O motor atual se chama **Motor 360 de Viabilidade do Consórcio**. Ele é comum para objetivos de investimento e de contemplação: o objetivo declarado é preservado como preferência e informação de contexto, mas não força mais um filtro prematuro por tipo de bem ou por estratégia.

## Limite atual do motor

O Motor 360 identifica grupos com crédito compatível e monta cenários financeiros preliminares. Ele ainda não escolhe uma carta de crédito específica dentro de cada grupo. Por isso, parcela, prazo e recomendação final não são aprovados de forma definitiva nesta etapa quando faltam os dados da carta selecionada.

## 1. Início do fluxo

1. O operador preenche e salva o Perfil do Cliente.
2. Ao clicar em **Avançar para Motor de Inteligência**, o front-end salva silenciosamente o perfil e abre a tela técnica `investidor`, que hoje representa o Motor 360 para qualquer objetivo.
3. A tela envia um `POST` para:

   ```text
   /api/viabilidade-360/analisar
   ```

4. A API carrega a base atual de grupos e executa a análise grupo a grupo.
5. O resultado devolvido pela API é apresentado na tela do Motor 360.

O modo normal usa a base atual. A base histórica somente pode ser utilizada quando o pedido informar explicitamente `base_mode = historical_audit`.

## 2. Dados recebidos do Perfil do Cliente

| Campo no perfil | Uso no Motor 360 |
| --- | --- |
| Objetivo do consórcio | Mantido como objetivo declarado e convertido em preferência de contemplação quando aplicável. |
| Crédito Desejado Líquido | Base do crédito contratado em cada cenário. |
| Lance Recursos Próprios | Compõe o lance disponível do cliente. |
| FGTS dos participantes | Compõe o lance disponível do cliente. |
| Renda total | Base para o limite de renda quando não houver parcela-limite informada. |
| Parcela máxima desejada | Enviada como parcela desejada para contexto. |
| Parcela limite | Se informada, torna-se o limite de renda do motor. Caso contrário, é calculada em 30% da renda total. |
| Tipo de bem | Só filtra a base se o operador selecionar explicitamente um tipo. |

### 2.1. Origem do recurso próprio

O recurso próprio pode vir dos titulares cadastrados ou do campo manual do perfil. Quando os dois valores são enviados e são diferentes, o motor interrompe a análise com o erro `conflito_recurso_proprio`. Isso evita gerar um resultado com duas fontes contraditórias de lance.

### 2.2. Limite de renda

O limite usado como referência é:

```text
Parcela limite = parcela_limite informada
```

Quando esse campo não está preenchido:

```text
Parcela limite = renda total x 30%
```

O percentual de 30% é uma referência neutra do Perfil do Cliente nesta fase.

## 3. Colunas utilizadas da planilha de grupos

O Motor 360 lê a base de grupos já importada pelo sistema. As colunas relevantes são:

| Planilha | Campo interno | Uso atual |
| --- | --- | --- |
| A | `administradora` | Identificação da administradora. |
| B | `grupo` | Identificação e ordenação numérica do grupo. |
| C | `tipo_bem` | Filtro opcional, somente quando o tipo de bem foi escolhido explicitamente pelo operador. |
| F | `prazo_restante` | Necessário para validar os prazos estimados após o lance. |
| O | `credito_minimo` | Limite inferior de crédito, quando informado. Ausência não elimina, mas gera alerta. |
| U | `credito_maximo` | Limite superior de crédito; obrigatório para a compatibilidade de crédito. |
| X | `percentual_lance_embutido` | Percentual de lance embutido usado no cenário com embutido. |
| AA | `fundo_reserva` | Necessário para compor saldo devedor financeiro. |
| AC | `taxa_adm` | Necessária para compor saldo devedor financeiro. |
| AJ | `parcela_inicial_grupo` | Referência de parcela inicial; influencia ordenação, mas não aprova o grupo de forma definitiva. |
| BL | `lance_investidor` | Faixa de lance de longo prazo / investidor. |
| BM | `lance_conservador_24m` | Faixa de lance conservadora. |
| BN | `lance_moderado_12m` | Faixa de lance moderada. |
| BO | `lance_agressivo_6m` | Faixa de lance rápida. |
| BP | `lance_super_agressivo_3m` | Faixa de lance urgente. |

Campos como modalidades de assembleia, base de cálculo do embutido, modalidades de embutido, taxa anual, parcela após lance e parcela reduzida podem continuar existindo na base, mas não bloqueiam nem aprovam grupos no Motor 360 atual.

## 4. Filtros eliminatórios da base

Os grupos são processados em sequência. Um grupo eliminado em uma etapa não segue para as próximas.

### 4.1. Status da base

O grupo precisa ter status exatamente equivalente a **Ativo** após normalização do texto. Status vazio, inativo ou diferente de ativo não participa da análise.

### 4.2. Tipo de bem opcional

Se o tipo de bem não foi escolhido no Perfil do Cliente, não há filtro por tipo.

Se foi escolhido explicitamente, o grupo precisa ser compatível com o tipo informado. A comparação trata variações normalizadas, por exemplo, `Imóvel` e `Imovel`.

### 4.3. Crédito máximo obrigatório

A coluna U precisa conter um crédito máximo positivo. Sem esse valor, não existe base para saber se o grupo suporta o crédito contratado, portanto o grupo é descartado por crédito incompleto.

## 5. Construção dos cenários de crédito

Para cada grupo restante, o motor constrói dois cenários:

1. **Sem embutido**
2. **Com embutido**, quando a coluna X possui percentual válido entre 0% e 100%.

Os cálculos monetários usam arredondamento decimal para centavos, evitando imprecisões de ponto flutuante.

### 5.1. Cenário sem embutido

```text
Crédito contratado sem embutido =
    Crédito Desejado Líquido
    + Recursos Próprios
    + FGTS
```

Exemplo conceitual:

```text
Crédito desejado: R$ 950.000,00
Recursos próprios: R$ 100.000,00
FGTS: R$ 100.000,00

Crédito contratado sem embutido: R$ 1.150.000,00
```

### 5.2. Cenário com embutido

Primeiro é lido o percentual de lance embutido da coluna X.

```text
Crédito contratado com embutido =
    Crédito contratado sem embutido
    / (1 - Percentual de Lance Embutido)
```

Depois:

```text
Lance embutido =
    Crédito contratado com embutido
    x Percentual de Lance Embutido
```

O cenário com embutido só existe se o percentual da coluna X for válido. Um valor ausente, zero, negativo ou igual/superior a 100% não produz cenário com embutido.

## 6. Compatibilidade de crédito

Cada cenário é comparado com a faixa de crédito do grupo.

```text
Crédito compatível =
    Crédito contratado do cenário <= Crédito máximo do grupo (U)
    e
    Crédito contratado do cenário >= Crédito mínimo do grupo (O), quando O existir
```

Se a coluna O não estiver preenchida, o motor ainda pode aceitar a parte superior da faixa usando a coluna U. Nesse caso, o grupo recebe o alerta `credito_minimo_nao_informado`.

O grupo continua na lista quando pelo menos um dos dois cenários possui crédito compatível.

## 7. Lance disponível e percentual de lance

### 7.1. Lance total

No cenário sem embutido:

```text
Lance total sem embutido = Recursos Próprios + FGTS
```

No cenário com embutido:

```text
Lance total com embutido = Recursos Próprios + FGTS + Lance embutido
```

### 7.2. Percentual de lance

```text
Percentual de lance = Lance total / Crédito contratado do cenário
```

Esse percentual é comparado com as faixas históricas da planilha, mas não elimina sozinho o grupo nesta etapa. Ele indica quais estratégias de contemplação podem ser atendidas pelo lance calculado.

## 8. Estratégias de contemplação

Antes de classificar estratégias, a base precisa estar consistente:

```text
Urgente (BP) >= Rápida (BO) >= Moderada (BN) >= Conservadora (BM) >= Investidor (BL)
```

Todas as cinco colunas devem ter valores positivos. Se alguma estiver ausente ou em ordem incompatível, o grupo recebe o alerta `faixas_contemplacao_inconsistentes` e não recebe estratégia confiável.

Quando a sequência está consistente, o motor compara o percentual de lance de cada cenário compatível com os alvos abaixo:

| Estratégia exibida | Coluna | Condição |
| --- | --- | --- |
| Urgente | BP | Percentual do cliente >= lance super agressivo de 3 meses |
| Rápida | BO | Percentual do cliente >= lance agressivo de 6 meses |
| Moderada | BN | Percentual do cliente >= lance moderado de 12 meses |
| Conservadora | BM | Percentual do cliente >= lance conservador de 24 meses |
| Longo prazo | BL | Percentual do cliente >= lance investidor |

A melhor estratégia é a primeira atingida na ordem: urgente, rápida, moderada, conservadora e longo prazo.

O objetivo declarado pelo cliente serve como preferência visual quando corresponder a uma dessas estratégias. Objetivos de investimento são preservados no resultado como objetivo declarado, mas ainda não recebem classificação automática de investimento nesta versão do Motor 360.

## 9. Saldo devedor e prazo após o lance

Para que um cenário tenha análise financeira completa, o grupo precisa informar taxa de administração (AC), fundo de reserva (AA) e prazo restante (F).

### 9.1. Saldo devedor

```text
Saldo devedor =
    Crédito contratado
    + (Crédito contratado x Taxa de administração total)
    + (Crédito contratado x Fundo de reserva total)
```

### 9.2. Saldo após o lance

```text
Saldo após o lance = Saldo devedor - Lance total
```

### 9.3. Prazos necessários

O sistema calcula os meses necessários arredondando para cima:

```text
Prazo pela parcela desejada = teto(Saldo devedor / Parcela desejada)
Prazo pelo limite de renda = teto(Saldo devedor / Parcela limite)

Prazo após lance pela parcela desejada = teto(Saldo após o lance / Parcela desejada)
Prazo após lance pelo limite de renda = teto(Saldo após o lance / Parcela limite)
```

Os quatro prazos são comparados com o prazo restante da coluna F. O cenário só é marcado como compatível por prazo quando todos os quatro cálculos cabem no prazo restante.

Se AC, AA ou F estiverem ausentes, essa validação não é inventada com zero: o grupo é marcado com dados financeiros incompletos.

## 10. Parcela inicial da planilha

A coluna AJ representa a parcela inicial de referência do grupo.

```text
Referência dentro da renda = Parcela inicial (AJ) <= Parcela limite
```

Essa comparação é usada como apoio na ordenação. Ela não substitui a análise da carta específica e não torna o grupo automaticamente recomendável, pois a parcela efetiva depende da carta de crédito que será selecionada depois.

## 11. Seguro

O motor pode sinalizar a presença de seguro obrigatório quando essa informação existir no grupo. Porém, a elegibilidade de seguro está marcada como `not_analyzed`, ou seja, ainda não elimina nem aprova grupos nesta fase.

## 12. Status e classificação de cada grupo

Cada item retornado recebe os principais estados abaixo:

| Campo | Significado |
| --- | --- |
| `credit_compatible` | Pelo menos um cenário está dentro da faixa de crédito do grupo. |
| `financial_data_complete` | AC, AA e F foram encontrados e permitem cálculo financeiro. |
| `income_compatible` | Permanece sem decisão definitiva nesta etapa, pois não há carta específica selecionada. |
| `term_compatible` | Há cenário compatível por prazo, quando os dados necessários existem. |
| `recommendable` | Permanece `false` nesta etapa preliminar; a recomendação definitiva depende da carta de crédito. |
| `data_completeness` | `complete` ou `incomplete`, conforme dados essenciais do grupo. |
| `best_contemplation_strategy` | Melhor faixa de contemplação atingida pelo percentual de lance, quando as faixas são consistentes. |
| `alerts` | Lista de alertas, como crédito mínimo ausente, taxas ausentes, faixas inconsistentes ou seguro não analisado. |

Na interface, o grupo pode aparecer como **Recomendável** somente quando todas as condições futuras estiverem implementadas; atualmente a tela diferencia principalmente grupos compatíveis por crédito e grupos com dados incompletos.

## 13. Ordenação da lista final

Depois de filtrar os grupos por status, tipo opcional e crédito, a lista é ordenada por estes critérios, nesta ordem:

1. Dados financeiros completos antes dos incompletos.
2. Grupos recomendáveis antes dos demais. Na versão atual, esse campo ainda não é aprovado definitivamente.
3. Grupos compatíveis nos dois cenários de crédito antes dos compatíveis em apenas um cenário.
4. Grupos cuja parcela inicial de referência (AJ) cabe no limite de renda antes dos demais.
5. Grupos compatíveis por prazo antes dos incompatíveis ou não analisados.
6. Grupos que atendem a preferência declarada de contemplação antes dos demais.
7. Menor margem de crédito antes da maior margem.
8. Número do grupo em ordem crescente como desempate.

Margem de crédito é calculada como:

```text
Margem de crédito = Crédito máximo do grupo (U) - Crédito contratado do cenário
```

## 14. Resultado final apresentado

Para cada grupo compatível por crédito, o Motor 360 apresenta:

- grupo e administradora;
- faixa de crédito mínimo e máximo, quando disponível;
- cenário sem embutido e cenário com embutido;
- crédito contratado, lance total, percentual de lance, saldo e prazo após o lance;
- parcela inicial de referência;
- prazo restante;
- melhor estratégia de contemplação encontrada;
- alertas e completude dos dados;
- status preliminar do grupo.

Assim, a lista final não significa que a carta já foi aprovada. Ela é uma lista ordenada de grupos que passaram pela elegibilidade de crédito e possuem, em maior ou menor nível, dados para a continuidade da análise comercial e financeira.

## 15. Arquivos responsáveis pela lógica

| Arquivo | Responsabilidade |
| --- | --- |
| `backend/static/js/app.js` | Coleta o Perfil do Cliente, salva os dados, abre o Motor 360 e renderiza o resultado. |
| `backend/main.py` | Expõe o endpoint `POST /api/viabilidade-360/analisar`. |
| `backend/models.py` | Define e valida o contrato de entrada da análise. |
| `backend/consortium_viability_engine.py` | Executa filtros, cenários, faixas de contemplação, prazo, ordenação e montagem do resultado. |
| `backend/credit_liquidity.py` | Calcula os cenários monetários com e sem lance embutido. |
| `backend/sheets_client.py` | Mapeia as colunas da planilha para os campos internos da aplicação. |

## 16. Itens conscientemente fora desta fase

Os itens abaixo não bloqueiam a lista atual e devem ser tratados em etapas posteriores, com uma carta específica selecionada:

- validação definitiva de parcela;
- aprovação final por renda;
- elegibilidade de seguro;
- regras de FGTS, recurso próprio, modalidades e combinação de recursos por administradora;
- classificação específica de investimento;
- seleção da carta de crédito e envio para o Estudo Financeiro.

Essas limitações são intencionais: o Motor 360 atual evita transformar ausência de dado em aprovação ou reprovação artificial.
