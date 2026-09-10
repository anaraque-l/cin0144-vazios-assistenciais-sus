# Roteiro da apresentação — Entrega 1 (EDA)

**CIN0144 · Vazios assistenciais no SUS · ~10 minutos · grupo de 4**

Objetivo da banca: ver que o grupo **entendeu a base** antes de modelar — que
cada problema apontado tem evidência, e que as hipóteses de pré-processamento
decorrem dessa evidência, não de um checklist.

Regra de ouro na fala: **todo gráfico vem com uma frase de "e daí para a
modelagem"**. É o que o enunciado cobra explicitamente.

---

## Divisão sugerida (4 pessoas × ~2,5 min)

| Bloco | Slides | Quem |
|---|---|---|
| A — Problema e base | 1–3 | pessoa 1 |
| B — EDA: alvos e o achado central | 4–6 | pessoa 2 |
| C — EDA: tempo, correlação, isolamento | 7–9 | pessoa 3 |
| D — Diagnóstico e hipóteses | 10–12 | pessoa 4 |

Fechamento (30 s): qualquer um. Perguntas: quem for dono do bloco.

---

## Slide 1 — O problema em uma frase (40 s)

> Prever, de dados públicos do IBGE e do DATASUS, **se um município tem leito de
> UTI** (Etapa 1) e **quanta da sua internação seria evitável pela atenção
> primária** (Etapa 2) — e usar os **erros** da Etapa 1 para mapear os vazios
> assistenciais.

- **Não** perguntamos "tem estabelecimento de saúde?" — 100% têm, alvo
  degenerado. Subimos a escada até o serviço cuja presença ainda varia.
- O **produto não é a acurácia** — é a lista dos municípios em que o modelo
  erra: os que, pelo perfil, deveriam ter UTI e não têm. Isso tem nome na
  literatura de saúde pública: **vazio assistencial**.

## Slide 2 — A base (40 s)

- Unidade: **município × ano**. 5.570 municípios × 10 anos (2014–2023) =
  **55.700 instâncias**, **70 atributos**.
- Fontes 100% públicas e abertas (IBGE: malha, PIB, área; DATASUS: CNES, SIH,
  SIM, SINASC). Nenhuma exige cadastro ou chave. Resposta bruta congelada em
  `data/raw/` — **reproduzível sem rede**.
- Duas decisões de coleta que mudam o resultado: (i) **município de
  residência**, nunca de internação; (ii) ausência no CNES é **zero
  estrutural**, não valor faltante.

## Slide 3 — Tipos de variável e as duas tarefas (40 s)

- 3 identificadores · 4 nominais · 1 ordinal · 4 binárias · 1 temporal ·
  27 contagens · 30 contínuas. Dos 70: **47 candidatos a preditor**, 9 proibidos
  só por vazamento, 11 alvos ou componentes de alvo.
- **Etapa 1 — `tem_uti`**: classificação binária desbalanceada (~11% positivos).
- **Etapa 2 — `taxa_icsap`**: regressão. É uma **proporção** (ICSAP ÷ total),
  não contagem — separa *tamanho* de *intensidade*.
- ⚠️ dizer em voz alta: `taxa_icsap` é uma **aproximação declarada** da Lista
  Brasileira de ICSAP (Portaria 221/2008); o TabNet não expõe CID de 3–4
  dígitos no recorte município. O viés é para cima e ~sistemático, então
  **preserva o ordenamento** entre municípios.

## Slide 4 — Distribuição dos alvos (50 s) · fig. `02-distribuicao-dos-alvos.png`

- `tem_uti`: **10,8% de positivos, razão 8,2:1**. Desbalanceamento **genuíno**
  (veio do fenômeno, não da amostragem).
- **Frase-chave:** "um modelo que responde *não tem UTI* para tudo acerta
  **89,2%** sem aprender nada" → métrica principal é **AUC + F1 da classe
  positiva + revocação + matriz de confusão**, nunca acurácia.
- `taxa_icsap`: unimodal, média 0,236, mediana 0,214, assimetria 1,07 — alvo
  contínuo bem-comportado, resultado direto de ter escolhido proporção.

## Slide 5 — O achado central: o alvo 1 é quase o porte (60 s) · fig. `03-alvos-por-categoria.png`

| Porte | P(tem UTI) |
|---|---|
| até 5 mil | 0,00 |
| 20–50 mil | 0,11 |
| 50–100 mil | 0,53 |
| 100–500 mil | 0,86 |
| 500 mil + | 1,00 |

- Transição inteira entre **20 mil e 100 mil habitantes**.
- **Duas consequências opostas:** (i) espere AUC alta já com uma logística só de
  população — e **desconfie**; (ii) o valor está na **faixa de transição**, onde
  o modelo tem incerteza real — é ali que o falso positivo carrega informação.
  **Essa lista é o produto do projeto.**

## Slide 6 — O painel: o alvo é traço do município (40 s)

- **85,3% dos municípios nunca mudaram de status** de UTI em 10 anos.
- **Implicação metodológica (a mais fácil de errar):** validação cruzada da
  Etapa 1 **tem** de ser agrupada por município (`StratifiedGroupKFold`,
  `groups=cod_ibge7`). Um `train_test_split` aleatório põe São Paulo no treino
  e no teste — o modelo memoriza o município, a métrica sobe e nada foi
  aprendido.

## Slide 7 — Série temporal: 3 movimentos reais (45 s) · fig. `04-serie-temporal.png`

1. **Salto de UTI em 2020–2021** — leitos COVID; total nacional 46 mil → 76 mil
   → 62 mil. É política pública aparecendo na base.
2. **`taxa_icsap` cai** de forma sustentada, **despenca** na pandemia (17,8% em
   2021), volta parcial.
3. **Pré-natal adequado sobe** 13 pontos ao longo de todo o período.
- ⚠️ **Armadilha do projeto:** a queda de ICSAP em 2020 **não** é a APS
  melhorando — é gente deixando de ir ao hospital. Nenhuma métrica de regressão
  pega isso sozinha → `ano` e `periodo_pandemia` **entram** como atributos.

## Slide 8 — Correlação: tudo é tamanho (45 s) · fig. `05` e `06`

- **Spearman**, não Pearson (com assimetria 37 um outlier domina o Pearson).
- `tem_uti`: tudo que correlaciona forte é **escala** — leitos 0,53, estab. 0,52,
  internações 0,50, população 0,50, PIB 0,50. **Nada** captura necessidade ou
  isolamento.
- `taxa_icsap`: correlações fracas, e as fortes são **desconfortáveis** —
  `leitos_sus_por_mil_hab` +0,34 (**mais oferta, mais internação evitável**:
  demanda induzida pela oferta). A Etapa 2 vai ser **genuinamente difícil** —
  é o diferencial do projeto.

## Slide 9 — Isolamento: a variável que não é tamanho (60 s) · fig. `11-isolamento-mapa-e-gradiente.png`

- `dist_uti_km` = distância ao leito de UTI mais próximo, haversine entre
  centroides, **recalculada ano a ano**.
- **ρ(distância, população) = 0,078** entre municípios sem UTI — a **primeira**
  variável do projeto que não é tamanho disfarçado.
- **Gradiente dose-resposta** em três sistemas independentes (SIH, SIM,
  SINASC): de ≤25 km para >200 km, `taxa_icsap` 0,21 → 0,29, mortalidade
  infantil **+56%**, pré-natal 7+ cai 24 pontos.
- ⚠️ **associação, não causalidade** — isolamento vem com pobreza e baixa
  densidade (ρ = −0,65 com densidade). Separar os efeitos é modelagem.
- O mapa (dispersão de lon/lat colorida por distância) **redesenha o Brasil** só
  com centroides: Amazônia escura, Sul/Sudeste colados ao serviço.

## Slide 10 — Diagnóstico: valores ausentes e outliers (45 s) · fig. `08` e `09`

- **Todo buraco é estruturado, com causa:** 20% em `vab_*` = 2 anos que o IBGE
  não publicou; saneamento do Censo falta nos **mesmos** 26/9/1 municípios em
  todo ano; `area_km2` = 6 municípios criados após o Censo 2010;
  `taxa_icsap_menor5/idoso` = `NaN` por denominador zero na faixa etária.
- **Outliers:** nenhum valor fora de domínio, **mas** as 3 colunas de saneamento
  do Censo estão em **0–100** e o resto da base em **0–1** — escala misturada.
- `tx_mort_infantil` até 285/mil = ruído de denominador pequeno, não epidemia.

## Slide 11 — Diagnóstico: redundância, vazamento, painel (45 s)

- **22 pares com |ρ| > 0,90.** Três naturezas: identidade contábil
  (`pib_mil_reais` × `vab_total` = 1,000); duplicação do alvo (`leitos_uti` ×
  `tem_uti` = 0,998; e agora os blocos ICSAP por faixa etária); proxies de
  tamanho (bloco 0,93–0,98).
- **Variância intra-painel nula:** as 3 colunas do Censo 2022 são idênticas nos
  10 anos em 100% dos municípios — servem só no corte transversal.
- **Vazamento — a seção que separa o projeto que funciona do que só parece:**
  `leitos_uti` **é** o alvo; `equip_manut_vida` (respirador/monitor) só existe
  em UTI; `taxa_icsap_menor5/idoso` **são** o alvo numa subpopulação. E o
  vazamento **circular**: volume de internação prevê UTI porque quem tem UTI
  interna mais — a seta causal está invertida.

## Slide 12 — Hipóteses de pré-processamento (50 s)

Cada uma **decorre de uma evidência acima** — não é checklist:

| Evidência | Hipótese |
|---|---|
| Assimetria 7–37 | log₁₀ / `log1p` nas variáveis de tamanho |
| Escala 0–100 vs 0–1 | unificar antes de modelo baseado em distância |
| `vab_*` = não publicado | **não imputar**; usar `pib_per_capita` ou cortar 2022–2023 |
| Alvo 1 = traço do município | `StratifiedGroupKFold` por `cod_ibge7` |
| Desbalanceamento 8,2:1 | comparar sem tratamento / `class_weight` / SMOTE **dentro dos folds** |
| 22 pares redundantes | remoção manual das identidades + PCA no bloco de tamanho |
| kNN/MLP × árvores | padronização obrigatória só para os primeiros — **discussão, não detalhe** |

## Fechamento (30 s)

O que diferencia esta EDA: **cada exigência de pré-processamento tem
justificativa empírica**. Os ausentes são estruturados e têm causa, o
desbalanceamento é genuíno, a redundância existe de verdade, o vazamento é real
e fácil de cometer. O notebook roda de ponta a ponta e as 11 figuras são
geradas por ele.

---

## Perguntas que a banca provavelmente vai fazer — e a resposta curta

**"Vocês vão usar acurácia?"**
Não como métrica principal. Baseline trivial = 89,2%. Decidimos por AUC, F1 da
classe positiva, revocação e matriz de confusão.

**"Por que 70 atributos e não menos? Não é dimensionalidade demais para 55 mil linhas?"**
55.700 linhas para ~47 candidatos é folgado. E boa parte dos 47 é redundante
(22 pares |ρ|>0,90) — a EDA já aponta PCA no bloco de tamanho e remoção manual
das identidades contábeis. A dimensionalidade efetiva é bem menor.

**"`taxa_icsap` é aproximada. Isso não invalida a Etapa 2?"**
O viés é predominantemente para cima e ~sistemático (mesma regra de tabulação
para o Brasil inteiro), então **preserva o ordenamento** entre municípios — que
é o que a regressão comparativa usa. O que invalidaria seria viés *diferencial*
entre municípios; isso está registrado como limitação e o próximo passo é
validar contra o microdado do SIH para uma UF.

**"Por que Spearman e não Pearson?"**
Com assimetria de 37, um único outlier (São Paulo) domina o Pearson. Spearman
opera sobre postos e responde a pergunta certa: quando um sobe, o outro sobe?

**"Por que não remover os outliers de população?"**
Porque não são erros — são as capitais. A distribuição é log-normal; Tukey
pressupõe simetria e marca milhares de linhas legítimas. O tratamento é log,
não remoção.

**"O alvo 1 é quase determinístico. Qual é a graça de modelar isso?"**
Exatamente essa é a observação central. O valor não está na métrica global — a
logística acerta quase tudo — está na **faixa de 20–100 mil habitantes**, onde
o modelo tem incerteza real. Os falsos positivos ali são a lista de vazios
assistenciais, que é o produto do trabalho.

**"Vocês aplicaram algum tratamento?"**
Não. A entrega é exploratória. `build_dataset.py` faz junção, agregação e as
taxas que definem os alvos — não imputa, não remove outlier, não padroniza, não
balanceia. Toda hipótese de pré-processamento está **escrita**, não aplicada.

**"O que mudou desde a primeira versão da base?"**
A base cresceu de 53 para 70 colunas (saneamento do Censo 2022, equipes e
equipamentos do CNES, ICSAP por faixa etária). Reexecutamos a EDA inteira sobre
as 70 colunas — daí os diagnósticos novos de escala inconsistente e colunas
constantes no painel.
