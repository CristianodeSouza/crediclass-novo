# Plano de Execucao do Motor de Inteligencia V4

## Objetivo

Evoluir o fluxo atual:

```text
Cliente -> Viabilidade -> Grupo -> Estudo
```

para:

```text
Cliente
-> Cenario de Viabilidade
-> Grupo Selecionado
-> Geracao de Estrategias
-> Ranking de Estrategias
-> Estrategia Recomendada e Alternativa
-> Template Preenchido
-> Revisao Humana
-> Estudo Financeiro Versionado
```

Google Sheets continuara sendo a fonte oficial dos grupos e historicos. Nao sera
introduzido banco SQL, React, Next.js, TypeScript ou outra stack.

## Decisoes de Arquitetura

1. Manter FastAPI, HTML, CSS e JavaScript atuais.
2. Separar os motores em modulos independentes:
   - `strategy_engine.py`: gera e calcula estrategias;
   - `strategy_ranking.py`: pontua, penaliza e ordena;
   - `template_engine.py`: resolve campos AUTO, OPERADOR e HIBRIDO;
   - `study_service.py`: cria, atualiza e versiona estudos.
3. O frontend nao devera recalcular regras financeiras. Ele apenas exibira os
   resultados produzidos pelo backend.
4. Grupos e historicos permanecem na Google Sheets.
5. Clientes, cenarios, estrategias, templates, textos, estudos, versoes e
   auditoria poderao usar JSON interno nesta fase, com persistencia adequada no
   Render. O armazenamento nao podera depender do disco efemero da instancia.
6. Os perfis de usuario dos documentos nao criarao restricoes de visualizacao.
   Todos continuarao podendo ver os dados, conforme decisao do projeto.

## Regras Oficiais das Estrategias

Cada grupo selecionado deve gerar seis estrategias:

1. Sorteio Geral;
2. Lance Fixo;
3. Conservadora;
4. Moderada;
5. Agressiva;
6. Super Agressiva.

Cada estrategia deve devolver:

- identificacao e tipo;
- percentual e valor do lance;
- credito contratado;
- lance embutido;
- FGTS utilizado;
- recurso proprio necessario;
- credito disponivel;
- parcela estimada;
- prazo estimado;
- chance operacional de contemplacao;
- scores parciais e final;
- selo;
- aprovada/reprovada;
- justificativas;
- alertas e motivos de reprovacao.

As permissoes de FGTS e lance embutido devem reutilizar as regras oficiais da
Viabilidade. O calculo da parcela deve reutilizar os valores explicitos da taxa
administrativa e do fundo de reserva.

## Ranking Oficial

Pesos:

| Criterio | Peso |
|---|---:|
| Compatibilidade com prazo | 30% |
| Recurso proprio necessario | 25% |
| Compatibilidade da parcela | 20% |
| Chance de contemplacao | 15% |
| Credito disponivel | 10% |

Penalidades:

- recurso insuficiente: -30;
- parcela acima do limite: -25;
- prazo superior a 150% do desejado: -20.

Reprovacoes:

- recurso necessario maior que o disponivel;
- parcela maior que 130% do limite;
- lance abaixo do minimo historico;
- credito disponivel menor que o desejado.

Selecao:

- recomendada: maior score entre estrategias aprovadas;
- alternativa: segundo maior score aprovado, desde que score >= 70.

Selos:

- 90 a 100: Excelente;
- 80 a 89: Muito Boa;
- 70 a 79: Boa;
- 60 a 69: Regular;
- 0 a 59: Nao Recomendada.

## Etapas de Execucao

### Etapa 1 - Contratos e Modelo de Dados V4

Criar modelos para Administradora, Cliente, Cenario, Estrategia, Template,
Campo de Template, Texto, Estudo, Versao e Auditoria.

Atualizar o mapeamento de grupos para incluir:

- proxima assembleia;
- limite de adesao;
- vencimento da primeira parcela;
- percentual de parcela reduzida;
- idade maxima;
- observacoes;
- identificacao estavel da administradora.

Testes:

- serializacao de todas as entidades;
- campos opcionais;
- compatibilidade com grupos existentes;
- leitura por nome de coluna.

Commit:

```text
feat(modelo-v4): adiciona contratos do motor de estrategias e templates
```

### Etapa 2 - Motor de Estrategias

Implementar as seis estrategias no backend.

Eliminar os calculos duplicados atualmente presentes em `app.js` e
`estudos.py`. O backend sera a unica fonte dos calculos.

Testes:

- uma suite por estrategia;
- FGTS permitido e bloqueado;
- lance embutido permitido e bloqueado;
- recurso proprio nunca negativo;
- credito e parcela;
- ausencia de percentual cadastrado;
- historico com menos de 12 meses.

Commit:

```text
feat(estrategias): implementa seis estrategias de contemplacao
```

### Etapa 3 - Classificacao da Chance

Implementar a classificacao operacional:

- Muito Baixa;
- Baixa;
- Media;
- Alta;
- Muito Alta.

Usar historico recente do grupo e registrar no response qual referencia gerou
a classificacao.

Testes:

- abaixo da media;
- proximo da media;
- acima da media;
- acima do maior lance medio;
- superior ao historico recente;
- historico insuficiente.

Commit:

```text
feat(estrategias): classifica chance operacional de contemplacao
```

### Etapa 4 - Ranking de Estrategias

Implementar scores parciais, pesos, penalidades, reprovacoes, selos,
justificativas e selecao da recomendada e alternativa.

Testes:

- todas as faixas de score;
- cada penalidade isolada;
- cada motivo de reprovacao;
- desempate;
- alternativa abaixo de 70;
- nenhuma estrategia aprovada.

Commit:

```text
feat(ranking): recomenda estrategia principal e alternativa
```

### Etapa 5 - API de Estrategias

Adicionar contratos e endpoints:

```http
POST /api/estrategias/analisar
GET /api/estrategias/{estrategia_id}
```

O endpoint recebera cenario e grupo e retornara as seis estrategias, ranking,
recomendada, alternativa, alertas e referencias utilizadas.

Testes:

- validacao de payload;
- grupo inexistente;
- response completo;
- tratamento de erro e logs.

Commit:

```text
feat(api-estrategias): expoe geracao e ranking de estrategias
```

### Etapa 6 - Integracao com a Tela Viabilidade

Na tabela de grupos, substituir a abertura direta do estudo por:

```text
Selecionar grupo -> Analisar estrategias
```

Exibir comparador contendo as seis estrategias, scores, selos, recursos,
parcela, prazo, chance, alertas e reprovacoes.

Permitir escolher recomendada ou alternativa antes de criar o estudo.

Estados obrigatorios:

- loading;
- vazio;
- erro;
- sucesso;
- nenhuma estrategia aprovada.

Commit:

```text
feat(viabilidade): integra comparador e ranking de estrategias
```

### Etapa 7 - Biblioteca de Templates

Criar o template base e as extensoes por administradora.

Classificacoes:

- AUTO;
- OPERADOR;
- HIBRIDO.

Implementar inicialmente:

- Itau;
- Caixa;
- Embracon;
- Rodobens;
- Porto.

As demais administradoras receberao o template base ate possuirem configuracao
especifica.

Criar cadastro de campos, origem, tipo, obrigatoriedade, editabilidade, versao e
status.

Commit:

```text
feat(templates): cria biblioteca versionada por administradora
```

### Etapa 8 - Biblioteca de Textos

Criar textos por administradora:

- institucional;
- beneficio;
- criterio de selecao;
- observacao padrao;
- alerta;
- rodape.

Os textos devem ser referenciados pelos templates, sem ficarem fixos no
frontend.

Commit:

```text
feat(textos): adiciona biblioteca comercial por administradora
```

### Etapa 9 - Motor de Preenchimento

Resolver os nove blocos:

1. dados do cliente;
2. cenario financeiro;
3. grupo selecionado;
4. estrategia recomendada;
5. simulacao financeira;
6. historico operacional;
7. datas operacionais;
8. motivos da recomendacao;
9. alertas e campos pendentes.

Calcular:

- status de cada campo;
- percentual AUTO;
- percentual OPERADOR;
- percentual PENDENTE;
- completeness total;
- campos pendentes;
- condicao de pronto para revisao.

Commit:

```text
feat(template-engine): preenche estudo e calcula completeness
```

### Etapa 10 - Nova Tela Estudo Financeiro

Reconstruir somente a aba Estudo Financeiro seguindo a referencia visual.

Cabecalho:

- voltar para Viabilidade;
- ver estrategia;
- historico de estudos;
- salvar;
- identificacao, status, datas e operador.

Area principal:

- dados do cliente;
- cenario financeiro;
- grupo selecionado;
- estrategia recomendada e alternativa;
- simulacao financeira;
- historico com grafico;
- datas operacionais;
- motivos da recomendacao;
- campos pendentes.

Barra lateral:

- progresso de preenchimento;
- percentuais AUTO, OPERADOR e PENDENTE;
- alerta de revisao;
- acoes;
- versoes do estudo.

Rodape:

- previa do template;
- campos do template;
- dados tecnicos.

Responsividade:

- desktop com barra lateral;
- tablet em duas colunas;
- celular em fluxo unico;
- nenhuma informacao ou botao fora da viewport.

Commit:

```text
feat(estudo-financeiro): implementa tela de template preenchido
```

### Etapa 11 - Edicao Humana e Workflow

Permitir edicao somente de campos OPERADOR e HIBRIDO.

Status:

- Rascunho;
- Pronto para Revisao;
- Aprovado para Envio;
- Enviado ao Cliente;
- Cancelado.

Regras:

- completeness >= 80%;
- grupo definido;
- estrategia recomendada definida;
- aprovacao manual antes de envio.

Commit:

```text
feat(estudos): adiciona revisao humana e workflow de status
```

### Etapa 12 - Persistencia, Versoes e Auditoria

Salvar como unidade:

```text
Cliente + Cenario + Grupo + Estrategia + Template + Campos
```

Toda alteracao deve gerar versao imutavel com:

- usuario;
- data;
- campo;
- valor anterior;
- valor novo;
- origem AUTO, OPERADOR ou HIBRIDO.

Corrigir a persistencia atual em `runtime_data/studies.json` para nao perder
dados em reinicios ou novos deploys do Render.

Commit:

```text
feat(estudos): persiste versoes e auditoria do template
```

### Etapa 13 - Historico de Estudos

Atualizar filtros e detalhes para:

- status V4;
- estrategia recomendada;
- score e selo;
- administradora e template;
- versao atual;
- completeness;
- operador;
- periodo.

Permitir visualizar versoes sem sobrescrever registros antigos.

Commit:

```text
feat(historico): adiciona versoes, estrategia e completeness
```

### Etapa 14 - Acoes do Estudo

Implementar:

- gerar previa;
- compartilhar link;
- enviar por e-mail;
- cancelar estudo.

O PDF atual deve ser tratado como exportacao separada. O Template Engine nao
deve depender da geracao de PDF.

Commit:

```text
feat(estudos): implementa acoes do estudo preenchido
```

### Etapa 15 - Homologacao e Deploy

Executar:

- testes unitarios de todos os motores;
- testes de contrato;
- testes de integracao FastAPI;
- UAT tela por tela;
- Playwright desktop, tablet e celular;
- verificacao de memoria no Render;
- teste com dados reais das administradoras;
- teste de persistencia apos redeploy.

Deploy incremental:

1. contratos sem alterar tela;
2. Strategy Engine;
3. Ranking Engine;
4. comparador na Viabilidade;
5. Template Engine;
6. nova tela Estudo Financeiro;
7. versoes e historico.

## Conflitos e Definicoes Necessarias

Os seguintes pontos nao possuem formula completa nos documentos e precisam ser
formalizados antes da respectiva etapa:

1. Formula exata do `prazo_estimado` de cada estrategia.
2. Limites numericos de "proxima da media" e "superior ao historico recente"
   para classificar chance.
3. Regra de uso do FGTS entre estrategias: total, parcial ou otimizado.
4. Regra de uso do lance embutido: maximo automatico ou percentual ajustavel.
5. Criterio de desempate quando duas estrategias tiverem o mesmo score.
6. Estrategia ausente na planilha: ocultar, reprovar ou gerar com alerta.
7. Local persistente no Render para entidades derivadas sem banco SQL.
8. Lista final das administradoras que receberao template especifico na
   primeira entrega.

Nenhuma dessas lacunas deve ser preenchida por interpretacao durante a
implementacao. Cada uma deve ser decidida antes da etapa que depende dela.

## Criterio Final de Sucesso

O trabalho estara concluido quando:

1. Todo grupo gerar seis estrategias auditaveis.
2. O ranking selecionar recomendada e alternativa pelas regras oficiais.
3. Nenhum calculo financeiro relevante existir somente no frontend.
4. O estudo for criado obrigatoriamente a partir de uma estrategia.
5. O template atingir e exibir completeness.
6. Campos AUTO, OPERADOR e HIBRIDO estiverem identificados.
7. Estudos forem versionados e auditados.
8. A nova tela seguir a referencia visual em desktop e mobile.
9. Dados persistirem depois de um deploy do Render.
10. Toda a suite automatizada e o UAT passarem.
