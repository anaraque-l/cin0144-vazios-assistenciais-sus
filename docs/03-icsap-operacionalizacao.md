# ICSAP: da portaria ao número

Este é o documento que sustenta o alvo da Etapa 2. Se alguém do grupo só puder
ler um arquivo além do guia, que seja este.

---

## 1. O que a portaria define

A **Portaria SAS/MS nº 221, de 17 de abril de 2008** publica a *Lista Brasileira
de Internações por Condições Sensíveis à Atenção Primária* — 19 grupos de causas
definidos por códigos CID-10:

| # | Grupo | CID-10 (como na portaria) |
|---|---|---|
| 1 | Doenças preveníveis por imunização e condições sensíveis | A37, A36, A33 a A35, B26, B06, B05, A95, B16, G00.0, A17.0, A19, A15.0 a A15.3, A16.0, A16.2, A15.4 a A15.9, A16.3 a A16.9, A17.1 a A17.9, A18, I00 a I02, A51 a A53, B50 a B54, B77 |
| 2 | Gastroenterites infecciosas e complicações | E86, A00 a A09 |
| 3 | Anemia | D50 |
| 4 | Deficiências nutricionais | E40 a E46, E50 a E64 |
| 5 | Infecções de ouvido, nariz e garganta | H66, J00, J01, J02, J03, J06, J31 |
| 6 | Pneumonias bacterianas | J13, J14, J15.3, J15.4, J15.8, J15.9, J18.1 |
| 7 | Asma | J45, J46 |
| 8 | Doenças pulmonares | J20, J21, J40 a J44, J47 |
| 9 | Hipertensão | I10, I11 |
| 10 | Angina | I20 |
| 11 | Insuficiência cardíaca | I50, J81 |
| 12 | Doenças cerebrovasculares | I63 a I67, I69, G45 a G46 |
| 13 | Diabetes mellitus | E10 a E14 |
| 14 | Epilepsias | G40, G41 |
| 15 | Infecção no rim e trato urinário | N10, N11, N12, N30, N34, N39.0 |
| 16 | Infecção da pele e tecido subcutâneo | A46, L01 a L04, L08 |
| 17 | Doença inflamatória órgãos pélvicos femininos | N70 a N73, N75, N76 |
| 18 | Úlcera gastrointestinal | K25 a K28, K92.0 a K92.2 |
| 19 | Doenças relacionadas ao pré-natal e parto | O23, A50, P35.0 |

Transcrição integral em `data/raw/icsap_lista_brasileira.csv`.

## 2. O obstáculo

O TabNet do SIH, no recorte **Brasil × município**, **não expõe a CID em 3 ou 4
caracteres**. A dimensão mais fina disponível é a **Lista de Morbidade CID-10** —
a lista de tabulação do próprio CID-10, com 333 grupos.

Os grupos de tabulação em geral coincidem com categorias de 3 caracteres
(`124 = Diabetes mellitus = E10–E14`), mas em vários pontos são mais amplos que
o recorte da portaria (`193 = Pneumonia = J12–J18`, quando a portaria pede
apenas as pneumonias bacterianas).

## 3. A operacionalização

O alvo do projeto é **`taxa_icsap`**, definido como:

```
taxa_icsap = internações nos grupos mapeados / internações totais
```

sempre por **município de residência**, somando as 12 competências do ano.

O mapeamento de cada um dos 19 grupos da portaria para os grupos da Lista de
Morbidade está codificado em [`src/icsap.py`](../src/icsap.py), com um campo
`aderencia` (`exato` / `superestima` / `subestima`) e um campo `divergencia`
descrevendo o desvio em cada caso.

Para imprimir a tabela completa:

```bash
python src/icsap.py
```

## 4. Onde a aproximação erra, e quanto

| Grupo | Aderência | O que acontece |
|---|---|---|
| 6 — Pneumonias bacterianas | superestima | O grupo `193 Pneumonia` cobre J12–J18, incluindo pneumonia viral. **Maior fonte de superestimação**, porque pneumonia é um dos grupos ICSAP mais volumosos. |
| 10 — Angina | superestima | `172 Outras doenças isquêmicas do coração` cobre I20–I25; a portaria pede só I20 (angina). Puxa para dentro infarto crônico e doença isquêmica crônica. |
| 9 — Hipertensão | superestima | `170` acrescenta I12–I15 (hipertensão secundária e renal). Desvio pequeno. |
| 15 — Infecção renal/urinária | superestima | `241 Outras doenças do aparelho urinário` é mais amplo que N34 + N39.0. |
| 5 — Infecções ORL | superestima | `196` cobre J30–J34 e a portaria pede só J31. |
| 1 — Preveníveis por imunização | superestima | `140` é G00 inteiro (a portaria pede G00.0) e `73` é "outras helmintíases" (a portaria pede só B77). |
| 4, 11, 18, 19 | subestima | Alguns códigos da portaria (E50–E64 parcial, J81, K92.0–K92.2, O23, P35.0) caem em grupos amplos demais para incluir sem contaminar o alvo — foram deixados de fora. |
| 2, 3, 7, 8, 12, 13, 14, 16, 17 | **exato** | 9 dos 19 grupos batem código a código. |

**Direção do viés:** predominantemente **para cima**. A `taxa_icsap` calculada
aqui tende a ser maior que a taxa oficial ICSAP.

**Por que isso não invalida o projeto:** o viés é aproximadamente **sistemático**
— aplica-se a todos os municípios da mesma forma, porque a mesma regra de
tabulação vale para o Brasil inteiro. Para um problema de **regressão comparativa**
(quais municípios têm taxa mais alta que outros), um deslocamento comum de nível
não muda o ordenamento. O que mudaria seria se o viés fosse maior em uns
municípios que em outros — algo plausível apenas se o perfil epidemiológico for
muito diferente, e que fica registrado como limitação.

## 5. O caminho exato, se o grupo quiser subir a régua

Baixar os microdados do SIH (arquivos `RD{UF}{AAMM}.dbc`) e filtrar
`DIAG_PRINC` pela lista da portaria:

```python
# esboço — exige acesso a ftp.datasus.gov.br
from pysus.online_data.SIH import download
df = download("PE", 2023, 1)           # UF, ano, mês
icsap = df[df.DIAG_PRINC.str[:3].isin(CODIGOS_3CH) |
           df.DIAG_PRINC.isin(CODIGOS_4CH)]
agregado = icsap.groupby(["MUNIC_RES"]).size()
```

Custo: ~30 GB de download, 27 UFs × 120 competências, e o FTP do DATASUS é
instável. Ganho: a lista exata em vez da aproximada.

**Recomendação:** fazer isso para **uma UF e um ano** e comparar com a nossa
aproximação. Isso mede o erro de verdade em vez de argumentar sobre ele — e é a
única validação que transforma a limitação da seção 4 de "argumento" em
"número". Está listado como item de validação em
[`04-melhorias-tradeoffs-sensibilidades.md`](04-melhorias-tradeoffs-sensibilidades.md).
