# Analise do layout do Estudo Financeiro

## Referencia analisada

Documento: `EF Melhores Consorcios - Itau - taxa especial (Antonio Queiroz - Apex).pdf`.

O PDF possui sete paginas e combina: apresentacao ao cliente, necessidade financeira, simulacao de oportunidade, resumo do consorcio, cartas selecionadas, historico de lances, estrategias de contemplacao, prazos operacionais e observacoes legais.

## Estrutura do documento de referencia

1. Capa, saudacao e contexto do estudo.
2. Necessidade do cliente e simulacao de uso de recursos proprios.
3. Resumo da solucao de consorcio e da administradora.
4. Cartas e grupos selecionados.
5. Historico mensal de lances dos grupos.
6. Projecoes por estrategia de contemplacao.
7. Prazos operacionais e observacoes legais.

## Mapeamento de campos

| Secao | Campo do layout | Origem real no sistema | Campo tecnico | Disponibilidade |
|---|---|---|---|---|
| Cliente | Nome do cliente | Perfil do Cliente | `profile.nome` ou nomes em `profile.titulares` | Disponivel |
| Cliente | Tipo de contratacao | Perfil do Cliente | `profile.tipo_contratacao` | Disponivel |
| Cliente | Objetivo do consorcio | Perfil do Cliente | `profile.objetivo` | Disponivel |
| Cliente | Tipo de bem | Perfil do Cliente | `profile.tipo_bem` | Disponivel quando informado |
| Cliente | Data de emissao | Sistema | data atual no momento da geracao | Disponivel |
| Necessidade | Credito liquido desejado | Perfil do Cliente | `profile.credito_desejado` | Disponivel |
| Necessidade | Parcela desejada | Perfil do Cliente | `profile.parcela_desejada` ou `profile.parcela_ideal` | Disponivel |
| Capacidade | Parcela maxima | Analise preliminar | `profile.parcela_limite` | Disponivel |
| Capacidade | Renda total | Analise preliminar | `profile.renda_total` | Disponivel |
| Lance | Recursos proprios | Perfil do Cliente | `profile.lance_proprio` | Disponivel |
| Lance | FGTS | Perfil do Cliente | `profile.fgts` | Disponivel |
| Selecao | Administradora escolhida | Grupos Selecionados | `item.administradora` | Disponivel |
| Selecao | Grupo | Grupos Selecionados | `item.grupo` ou `item.grupo_id` | Disponivel |
| Selecao | Quantidade de cotas | Selecao do Motor 360 | `investorState.quotaCounts` | Disponivel, de 1 a 10 |
| Grupo | Credito maximo | Base de grupos/Motor 360 | `item.credito_maximo` | Disponivel |
| Grupo | Prazo remanescente | Base de grupos, coluna F | `item.prazo_restante` | Disponivel |
| Cenario | Credito contratado sem embutido | Motor 360 | cenario `without_embedded.credito_contratado` | Disponivel |
| Cenario | Parcela inicial sem embutido | Motor 360 | cenario `without_embedded.parcela_inicial` | Disponivel |
| Cenario | Credito contratado com embutido | Motor 360 | cenario `with_embedded.credito_contratado` | Disponivel quando o cenario existe |
| Cenario | Parcela inicial com embutido | Motor 360 | cenario `with_embedded.parcela_inicial` | Disponivel quando o cenario existe |
| Cenario | Saldo devedor e lance | Motor 360 | campos dos cenarios em `item.cenarios` | Disponivel para detalhamento futuro |
| Contemplacao | Conservador, Moderado, Agressivo e Super Agressivo | Motor 360/base de grupos | `cenario.perfis_contemplacao` | Disponivel quando a base possui referencia |
| Contemplacao | Percentual de referencia | Motor 360/base de grupos | `percentual_referencia` | Disponivel quando preenchido |
| Contemplacao | Atinge o perfil / valor faltante | Motor 360 | `atinge_perfil` e `falta_para_ideal` | Disponivel quando calculado |
| Estudo | Classificacao do grupo | Motor 360 | `item.best_contemplation_strategy` | Disponivel quando classificado |

## Informacoes apenas parcialmente disponiveis

Estes dados existem em partes da plataforma ou da base, mas ainda nao chegam de forma garantida ao objeto de cada grupo selecionado. Por isso nao sao exibidos no primeiro layout:

- taxa de administracao total e anual;
- fundo de reserva total e anual;
- historico mensal de maior lance, menor lance e quantidade de contemplados;
- dados cadastrais completos da administradora e beneficios contratuais;
- datas de assembleia e vencimentos;
- lance fixo e regras especiais, quando o grupo nao possui esses campos completos.

Antes de usa-los no documento final, o backend deve enriquecer o grupo selecionado com os respectivos campos da base e registrar a origem de cada valor.

## Informacoes que o sistema atual nao consegue obter

O sistema nao possui fonte real e estruturada para os itens abaixo. Eles nao devem ser calculados, estimados ou exibidos sem novo cadastro ou integracao:

- rentabilidade anual de uma aplicacao alternativa;
- custo de oportunidade e rendimento perdido;
- ganho de investimento projetado;
- valor de resgate futuro de investimento;
- condicao comercial especial, desconto negociado ou taxa aprovada individualmente;
- responsavel comercial pelo estudo e dados de contato personalizados;
- prazo de validade da proposta;
- datas operacionais de reserva, adesao, assembleia, primeira parcela e pagamento do lance;
- promessa ou probabilidade garantida de contemplacao;
- textos de beneficios especificos da administradora sem cadastro estruturado;
- valores de compra a vista, entrada ou financiamento externo nao informados pelo cliente.

## Regra de integridade do documento

1. Exibir somente valores presentes no Perfil do Cliente, no Motor 360 ou nos Grupos Selecionados.
2. Omitir blocos opcionais sem fonte real.
3. Usar `Nao informado` apenas em campos essenciais de identificacao.
4. Nao transformar percentuais historicos em garantia de contemplacao.
5. Multiplicar valores do grupo pela quantidade de cotas somente nos campos monetarios consolidados.
6. Manter sem e com embutido como cenarios independentes.

## Plano objetivo de implementacao

### Fase 1 - Documento dinamico

- criar a aba `Estudo Financeiro` depois de `Grupos Selecionados`;
- carregar o perfil salvo e os grupos efetivamente selecionados;
- montar capa, cliente, necessidade, resumo financeiro, grupos e perfis de contemplacao;
- permitir ocultar ou exibir secoes sem alterar os dados;
- permitir impressao e geracao de PDF em A4 paisagem;
- apresentar aviso de ausencia de grupos quando nada estiver selecionado.

### Fase 2 - Enriquecimento rastreavel

- criar endpoint de detalhe dos grupos selecionados;
- incluir taxa administrativa, fundo de reserva e historico mensal apenas quando presentes na base;
- registrar coluna de origem, linha de origem e data da sincronizacao;
- omitir automaticamente campos incompletos.

### Fase 3 - Conteudo comercial configuravel

- criar cadastro estruturado de beneficios e observacoes por administradora;
- criar campos opcionais para consultor, validade e contatos;
- permitir salvar modelos de secoes sem permitir valores inventados;
- manter os avisos legais separados dos calculos do motor.

### Fase 4 - Persistencia do estudo

- salvar um snapshot do perfil, dos grupos, das cotas e das formulas utilizadas;
- gerar identificador e versao do estudo;
- armazenar o PDF e o snapshot no Historico de Estudos;
- garantir reproducao da auditoria mesmo que a base de grupos seja atualizada depois.

## Implementacao inicial realizada

A aba `Estudo Financeiro` foi adicionada ao fluxo. O layout inicial usa exclusivamente os dados reais ja disponiveis, permite personalizar as secoes visiveis e pode ser impresso ou salvo em PDF no formato A4 paisagem.
