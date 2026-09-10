# Melhorias, trade-offs e sensibilidades

Três seções, com propósitos diferentes:

- **[Sensibilidades](#sensibilidades--validar-antes-de-entregar)** — o que
  **precisa ser validado antes de enviar o notebook**. É uma checklist.
- **[Trade-offs](#trade-offs-assumidos)** — escolhas com preço, já pagas
  conscientemente. Precisam estar na ponta da língua na apresentação.
- **[Melhorias](#melhorias-possíveis)** — o que fica para depois, ordenado por
  retorno.

---

## Sensibilidades — validar antes de entregar

> Marque cada item. O que não for validado tem de virar uma frase de limitação
> explícita no relatório.

### S0 — Os números batem com a fonte oficial?

- [x] **Total de internações SUS em 2023 — VALIDADO.** O painel soma
      **13.214.833**. A conferência foi feita de duas formas:
      (a) o total do TabNet por local de **residência** e por local de
      **internação** bate **exatamente** (13.215.017 nos dois), o que confirma
      que a soma das 12 competências está correta — são as mesmas AIHs vistas de
      dois ângulos;
      (b) a diferença de **184 internações** para o nosso painel é Fernando de
      Noronha, excluído pela decisão D9.
      Nota: `Internações` corresponde a 98,95% das `AIH aprovadas` (13.355.585),
      porque exclui AIH de continuação de longa permanência. A expectativa
      inicial de "~11 milhões" estava desatualizada — é o patamar de 2019.
- [x] **Leitos de UTI em 2023 — 62.359.** Compatível com a ordem de grandeza do
      parque de terapia intensiva brasileiro. As seis categorias de unidade
      intermediária, isolamento e suporte ventilatório COVID ficam de fora: em
      Recife, por exemplo, o total de leitos complementares é 1.971 e o de UTI
      é 1.723 — a diferença de 248 são exatamente essas categorias.
      Rastreamento completo em `docs/06`, seção 7.
- [x] **População do Brasil em 2023 — 203.077.589.** Bate com a estimativa TCU.
      A junção por `cod_ibge6` está correta.
- [x] **Nascidos vivos em 2023 — 2.537.481.** Dentro do esperado (~2,5 milhões).
      Conferência cruzada: o SINASC por residência da mãe (2.537.511) e por
      ocorrência (2.537.573) diferem em 62 registros, 0,002%.
- [x] **Óbitos de menores de 1 ano em 2023 — 32.001.**

Esse é o teste mais importante de todos. Um pipeline que agrega errado produz
uma EDA inteiramente plausível e inteiramente falsa.

### S1 — A não-independência das linhas

- [x] **Confirmado.** O notebook declara o painel explicitamente (célula 4,
      "CONCEITO — unidade de análise e painel") e escreve a consequência para a
      modelagem (`GroupKFold`/`StratifiedGroupKFold` agrupado por `cod_ibge7`).

Se alguém fizer `train_test_split` aleatório em 55.700 linhas, São Paulo cai no
treino **e** no teste. O modelo memoriza o município e a métrica sobe sem que o
modelo tenha aprendido nada generalizável. Não afeta a Entrega 1, mas se não
estiver escrito agora, alguém vai errar na Entrega 2.

### S2 — Vazamento de atributos

- [x] **Verificado e consolidado.** A lista de atributos candidatos da
      **Etapa 1** exclui `leitos_uti`, `leitos_complementares` (são o alvo),
      `leitos_internacao`, `leitos_internacao_sus`, `leitos_por_mil_hab`,
      `leitos_sus_por_mil_hab`, `estab_hospital` (quase determinam o alvo —
      quem tem UTI tem hospital), `internacoes_total`, `tx_internacao_por_mil`
      (circular: município com UTI interna mais *porque* tem UTI),
      `equip_manut_vida` (respiradores/monitores, ρ = 0,528 com `tem_uti`),
      `dist_hospital_km` (deriva de `leitos_internacao`, ρ = −0,25) e
      `vazio_assistencial` (definido usando `tem_uti == 0` — circular por
      construção).
- [x] **Verificado.** A lista da **Etapa 2** exclui `internacoes_icsap`,
      `internacoes_total`, `icsap_por_10mil` — são o alvo reescrito — e,
      desde o PR #1, também `taxa_icsap_menor5`/`taxa_icsap_idoso` (o mesmo
      alvo numa subpopulação, ρ = 0,65 e 0,84) e seus numeradores/
      denominadores `intern_menor5_*`/`intern_idoso_*`.
- Fonte única de verdade: `src/fontes.py` (`VAZAMENTO_ETAPA1`/
  `VAZAMENTO_ETAPA2`). `src/gerar_dicionario.py` e `notebooks/01-eda.ipynb`
  validam contra ela com `assert` — a lista já havia divergido entre
  CLAUDE.md, o notebook e este arquivo antes desta consolidação (três itens
  da Etapa 1 só estavam corretos em `docs/05-dicionario-de-dados.md`, gerado
  à parte; os itens por faixa etária da Etapa 2 vieram do PR #1).

### S3 — Estabilidade da taxa em município pequeno

- [x] **Feito** (notebook, seção 3.2, figura `10-funil-denominador.png`). O
      funil na versão proporcional (`taxa_icsap`) é fraco; na versão
      populacional (`icsap_por_10mil`) é forte — o que valida a escolha da
      proporção como alvo principal.
- [x] **Quantificado.** Mesmo fenômeno reaparece em `taxa_icsap_menor5`/
      `taxa_icsap_idoso` (relatório, §3.1): os 90 e 13 município-ano com
      denominador etário zero têm população mediana de 2.100 habitantes,
      contra 11.499 da base inteira.

Município com 2 mil habitantes e 3 internações ICSAP tem taxa de 100% por acaso.
Sem piso de denominador, esses pontos dominam a cauda da distribuição e o modelo
de regressão vai gastar capacidade tentando prever ruído.

### S4 — O choque da pandemia

- [x] **Feito** (notebook, seção 2.4, figura `04-serie-temporal.png`): queda
      sustentada de `taxa_icsap` com colapso adicional em 2020-2021.
- [x] **Feito**: `leitos_uti` nacional salta de 46 mil (2019) para 76 mil
      (2021).
- [x] **Decidido e escrito** (notebook, seção 2.4 e `docs/relatorio-entrega1.md`
      §4.2): manter os 10 anos com `periodo_pandemia` como atributo, preservando
      100% das instâncias — a expansão de leitos na pandemia também explica boa
      parte da queda de `vazio_assistencial` (seção 2.8), o que é um argumento
      **contra** excluir 2020-2021.

Em 2020 as pessoas deixaram de se internar por causa evitável — não porque a
atenção primária melhorou, mas porque ninguém ia ao hospital. Interpretar essa
queda como melhoria da APS seria um erro grave de leitura.

### S5 — A aproximação do ICSAP

- [x] **Confirmado.** O notebook declara `taxa_icsap` como **aproximação** da
      Lista Brasileira (seção 1.3), com o link para
      [`03-icsap-operacionalizacao.md`](03-icsap-operacionalizacao.md).
- [ ] **Ainda pendente.** Baixar o microdado do SIH de **uma UF, um ano**,
      calcular a taxa exata e comparar com a nossa (M3). Não foi feito nesta
      revisão — continua como item de maior retorno/esforço em aberto.

### S6 — Sanidade das junções

- [x] `cod_ibge7` único por município: 5.570 valores distintos. ✔
- [x] Nenhum município-ano duplicado: `df.duplicated(['cod_ibge7','ano']).sum() == 0`. ✔
- [x] Colunas de contagem sem valor negativo. ✔ (verificado nas 21 colunas de
      contagem/estabelecimento/leito/internação/nascimento/óbito/equipamento)
- [x] `pct_prenatal_7mais` e `taxa_icsap` dentro de [0, 1]. ✔
- [x] Percentuais de VAB somando ≈ 1 por linha. ✔ (média 1,000, desvio-padrão
      0,000008, nas 44.552 linhas em que os 4 percentuais existem)

### S7 — Padrão dos valores ausentes

- [x] **Feito** para todas as colunas com `NaN` (notebook, seção 3.1): todos os
      buracos são estruturados, com causa identificada — inclusive os dois
      padrões novos encontrados depois que a base cresceu para 70 colunas
      (`pct_esgoto_rede`/`pct_agua_rede` fora da cobertura do Censo 2022;
      `taxa_icsap_menor5`/`taxa_icsap_idoso` com denominador etário zero).

Ausência estruturada não pode ser imputada pela média — a média vem de uma
população diferente daquela que gerou o buraco.

### S8 — O básico do enunciado

- [x] Mais de 1.000 instâncias ✔ (55.700)
- [x] Mais de 10 atributos ✔ (70 colunas; 45 candidatas a preditor — 11
      proibidas por vazamento, 3 identificadores, 11 alvo ou componente de alvo)
- [x] Tipo de tarefa declarado, com variável-alvo identificada e justificada
      (seção 1.3/1.4 do notebook e do relatório)
- [x] **Toda figura acompanhada de interpretação** ✔ (11 figuras)
- [x] **Notebook executa do começo ao fim sem erro, com as saídas salvas.**
      O notebook chegou a descrever 53 colunas enquanto
      `data/processed/municipio_ano.csv` já tinha 70 (commit `0496b2b`, não
      propagado a tempo) — corrigido em `fix/eda-base-70-colunas` (PR #1,
      commit `2b0b5a1`) e complementado nesta revisão com `dist_hospital_km` e
      `vazio_assistencial` na lista de vazamento. Reexecutado via
      `jupyter nbconvert --execute` em 2026-09-10, sem erros (26 células de
      código, 11 figuras).

---

## Trade-offs assumidos

| # | Escolhemos | Em vez de | Ganho | Preço |
|---|---|---|---|---|
| T1 | TabNet agregado | Microdados `.dbc` via PySUS | Base cabe no repositório, reprodutível, sem 30 GB de download | `taxa_icsap` é aproximada, não exata |
| T2 | Painel município × ano | Corte transversal de um ano | 55.700 instâncias, `ano` como atributo, pandemia visível | Linhas não independentes; exige CV agrupada |
| T3 | `tem_uti` como alvo | "Tem estabelecimento de saúde" | Desbalanceamento genuíno (10,8%), problema com conteúdo | Alvo mede *cadastro*, não *funcionamento* |
| T4 | Município de residência | Município de internação | Elimina o viés de fluxo, que é enorme | Perde a leitura de "quanto o município atrai pacientes" |
| T5 | Dezembro como foto do CNES | Média das 12 competências | Convenção do MS, leitura direta | Sensível a abertura/fechamento pontual de leito |
| T6 | Estimativa TCU como população | Estimativa SIDRA / Censo 2022 | Mesmo denominador do Ministério da Saúde; série sem degrau | Não incorpora a revisão do Censo 2022 |
| T7 | Zero para ausência no CNES | `NaN` + imputação | Reflete a realidade: não existe leito ali | Confunde "não tem" com "não informou", se houver subnotificação |
| T8 | Área do Censo 2010 fixa | Área revisada ano a ano | Simplicidade; a variação é mínima | Pequeno erro em municípios com limite revisado |
| T9 | Distância haversine do centroide | Distância rodoviária/fluvial real | Uma requisição, sem dependência externa | Subestima muito o deslocamento amazônico |
| T10 | Cortes fixos no `vazio_assistencial` (20 mil hab., 100 km) | Limiar derivado dos dados | Leitura direta, questionável de forma explícita | Arbitrário; exige teste de sensibilidade |

---

## Melhorias possíveis

Ordenadas por **retorno analítico ÷ esforço**.

### ~~M1 — Distância até o município com UTI mais próxima~~ ✅ **IMPLEMENTADO**

Hoje o modelo não sabe nada sobre **vizinhança**. Um município sem UTI a 20 km
de uma capital é situação completamente diferente de um a 300 km da cidade mais
próxima com UTI — e os dois estão idênticos na base atual.

Como fazer: baixar os centroides da malha municipal
(`https://servicodados.ibge.gov.br/api/v3/malhas/municipios/{id}?formato=application/vnd.geo+json`)
ou a tabela de coordenadas de sedes municipais do IBGE, e calcular a distância
haversine até o município mais próximo com `tem_uti == 1`.

**Implementado em `src/geografia.py`** (commit `a03dee0`). Confirmou-se o que
se esperava: ρ com população = **0,078**, e o gradiente dose-resposta em
`taxa_icsap`, mortalidade infantil e cobertura de pré-natal.

**O que ficou pendente daqui:** a distância é em **linha reta**. Na Amazônia o
deslocamento é fluvial e leva dias — 175 km em linha reta não são uma hora de
viagem. Uma matriz de tempo real de deslocamento seria o refinamento natural, e
não encontramos fonte pública aberta para os 5.570 municípios.

### M2 — Cobertura da Estratégia Saúde da Família *(alto retorno)* ⚠️ **PARCIAL**

A cobertura de ESF por município é o indicador direto de atenção primária, e é
exatamente a variável que deveria explicar `taxa_icsap`. O indicador oficial
está no e-Gestor AB (`https://egestorab.saude.gov.br/`) — mas a interface é
JSF e não tem API, então continua exigindo download manual ou automação de
navegador; **isso não foi feito**.

**O que foi implementado (commit `0496b2b`) é um proxy**, `cobertura_esf =
min(1, equipes_esf × 3.450 / população)`, a partir de equipes *cadastradas* no
CNES — não das equipes *homologadas* que o e-Gestor usa. Discutido no
relatório, §4.3: a variável satura em 91,6% (2023) e correlaciona ~0 com
`taxa_icsap` — verificado nesta revisão com o valor exato, ρ = 0,011. Sem o
número oficial, não dá para saber se é a ESF que não discrimina mais município
nenhum no Brasil de hoje, ou se é o proxy que está inflado. Buscar o dado do
e-Gestor continua sendo o próximo passo para decidir entre as duas hipóteses.

### M3 — Validar a aproximação do ICSAP contra o microdado *(médio)*

Ver [S5](#s5--a-aproximação-do-icsap). Uma UF, um ano, um número. **Ainda não
feito** — continua sendo o item de maior retorno/esforço em aberto.

### M4 — ICSAP por faixa etária *(médio)* ✅ **IMPLEMENTADO E ANALISADO**

A literatura costuma calcular ICSAP separando menores de 5 anos e maiores de
60. Implementado em `build_dataset.py` (commit `0496b2b`) como
`taxa_icsap_menor5`/`taxa_icsap_idoso`. Discutido no relatório, §3.6: as duas
taxas correlacionam fortemente com o alvo principal (ρ = 0,65 e 0,84) e por
isso são vazamento — e são quase o dobro da geral (39,3% e 38,7% contra
23,6%), coerente com a literatura considerar a taxa infantil a mais sensível
à qualidade da APS.

### M5 — Equipamentos do CNES *(baixo, fácil)* ✅ **IMPLEMENTADO E ANALISADO**

`cnes/cnv/equipobr.def` traz mamógrafo, tomógrafo, raio-X e equipamentos de
manutenção da vida por município. Implementado (commit `0496b2b`) e discutido
no relatório, §3.6 — inclusive corrigindo a descrição inicial de
`equip_manut_vida` no dicionário de dados: não é presença exclusiva de
município com UTI (77,5% dos sem UTI também têm ao menos um), é diferença de
**escala** (mediana 300 unidades com UTI contra 5 sem UTI, ρ = 0,528).

### M6 — Indicadores sociais além do PIB *(médio)* ✅ **IMPLEMENTADO E ANALISADO** (parcial)

Saneamento (esgoto, água, lixo) do Censo 2022 foi implementado (commit
`0496b2b`) e discutido no relatório, §3.4 — correlação fraca com `taxa_icsap`
(ρ entre −0,05 e −0,13), mais fraca que o isolamento geográfico.
**Escolaridade e renda domiciliar, citadas nesta melhoria, não foram
implementadas** — só saneamento.

### M7 — Revisão do denominador populacional pós-Censo *(baixo)* ⚠️ **STATUS INCERTO**

Rodar a base com a série do SIDRA e comparar as taxas. Se o ordenamento dos
municípios não mudar, a escolha do denominador está validada como irrelevante.
A mensagem do commit `0496b2b` cita M7 entre as melhorias entregues, mas não
encontramos, no código ou nesta revisão, uma comparação TCU × SIDRA nem uma
coluna correspondente — **o teste comparativo não está implementado**, apesar
de citado. Não removemos a menção do commit (histórico do git não se edita),
mas registramos aqui que este item continua pendente e precisa ser confirmado
com quem escreveu aquele commit antes de ser dado como feito.
