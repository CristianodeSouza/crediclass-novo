# Motor Oficial de Referencia de Lance

## Regra global

O motor usa o menor lance contemplado dos meses validos e acrescenta
0,25 ponto percentual (`0.0025`). O resultado e uma referencia operacional
e nao garante contemplacao.

O motor nao usa medias, regressao, chance estatistica, projecao matematica
nem reducao do prazo restante pelo percentual de lance.

## Perfis

| Perfil | Prazo operacional | Calculo |
| --- | --- | --- |
| Investidor | Sem urgencia | Sorteio e lance fixo entre 0% e 20%, sem historico |
| Super Conservador | 13 a 24 meses | Segundo menor lance dos ultimos 12 meses validos + 0,25 p.p. |
| Conservador | 7 a 12 meses | Segundo menor lance dos ultimos 12 meses validos + 0,25 p.p. |
| Moderado | 4 a 6 meses | Segundo menor lance dos ultimos 6 meses validos + 0,25 p.p. |
| Agressivo | 1 a 3 meses | Maior dos menores lances dos ultimos 3 meses validos + 0,25 p.p. |

No perfil Agressivo, usar o maior valor entre os tres menores lances produz
o percentual que teria atingido o menor lance contemplado em todos os tres
meses analisados.

## Campos gerados

- `lance_investidor`
- `lance_super_conservador`
- `lance_conservador`
- `lance_moderado`
- `lance_agressivo`

As colunas da planilha sao localizadas pelo significado do cabecalho, nunca
pela posicao.
