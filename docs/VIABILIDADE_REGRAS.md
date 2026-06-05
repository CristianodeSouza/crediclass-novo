# Regras da Viabilidade

Este documento descreve as regras executadas pelo endpoint
`POST /api/viabilidade/analisar`.

## Perfis por prazo

| Prazo desejado | Perfil |
|---|---|
| 1 a 3 meses | Super Agressivo |
| 4 a 6 meses | Agressivo |
| 7 a 12 meses | Moderado |
| 13 a 24 meses | Conservador |
| Acima de 24 meses | Investidor |

## Filtros iniciais

Um grupo somente entra na analise quando:

- esta ativo;
- possui prazo restante;
- o credito desejado nao supera o credito maximo;
- o tipo de bem e compativel.

Credito abaixo do minimo permanece no resultado para auditoria, recebe zero no
criterio de credito e nao pode aprovar o cenario.

## Recursos e permissoes

- FGTS somente e utilizado quando o grupo permite FGTS.
- Lance embutido somente e calculado quando o grupo permite lance embutido.
- Lance proprio pode ser igual a zero.
- Nenhum valor artificial e acrescentado aos recursos disponiveis.

## Historico

Sao considerados somente os 12 meses validos mais recentes. O response informa:

- media do maior lance;
- media do menor lance;
- media mensal de contemplacoes;
- total de contemplacoes.

Grupo sem referencia de lance recebe zero no criterio de lance e o alerta
`historico_lance_insuficiente`.

## Afinidade

| Criterio | Peso |
|---|---:|
| Credito | 25% |
| Parcela | 25% |
| Lance | 25% |
| Prazo | 15% |
| Historico | 10% |

Selos:

- 90 a 100: Excelente;
- 80 a 89: Muito Bom;
- 70 a 79: Bom;
- 60 a 69: Regular;
- 0 a 59: Baixa Compatibilidade.

## Cenario final

O cenario somente e viavel quando pelo menos um grupo aprova simultaneamente
credito, renda, parcela, lance, prazo, tipo de bem e permissoes aplicaveis.

Quando uma data de nascimento e informada, ela e calculada. Se o grupo nao
possuir limite de idade, a analise nao reprova por idade e retorna
`idade_nao_validada`. Data ausente nunca e apresentada como idade compativel.

O estado do bem e preservado no response e no Estudo Financeiro.
