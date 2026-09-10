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

- [ ] **Total de internações SUS em 2023.** Somar `internacoes_total` do ano e
      comparar com o painel do DATASUS. Ordem de grandeza esperada: ~11 milhões.
      Divergência acima de 5% indica erro na soma das 12 competências.
- [ ] **Leitos de UTI em 2023.** Somar `leitos_uti` e comparar com o total
      publicado pelo CNES. Se estiver muito acima, alguma categoria de unidade
      intermediária entrou na conta por engano (checar `LEITOS_UTI` em
      `src/fontes.py`).
- [ ] **População do Brasil em 2023.** Somar `populacao`. Esperado: ~203 milhões
      pela estimativa TCU. Se der muito diferente, a junção `cod_ibge6` falhou.
- [ ] **Nascidos vivos em 2023.** ~2,5 milhões.

Esse é o teste mais importante de todos e leva 5 minutos. Um pipeline que
agrega errado produz uma EDA inteiramente plausível e inteiramente falsa.

### S1 — A não-independência das linhas

- [ ] Confirmar no notebook que o painel está declarado como painel, e que a
      consequência (validação cruzada **agrupada por município** na modelagem)
      está escrita.

Se alguém fizer `train_test_split` aleatório em 55.700 linhas, São Paulo cai no
treino **e** no teste. O modelo memoriza o município e a métrica sobe sem que o
modelo tenha aprendido nada generalizável. Não afeta a Entrega 1, mas se não
estiver escrito agora, alguém vai errar na Entrega 2.

### S2 — Vazamento de atributos

- [ ] Verificar que a lista de atributos candidatos da **Etapa 1** exclui:
      `leitos_uti`, `leitos_complementares` (são o alvo),
      `leitos_internacao`, `leitos_internacao_sus`, `estab_hospital`
      (quase determinam o alvo — quem tem UTI tem hospital),
      `internacoes_total`, `tx_internacao_por_mil` (circular: município com UTI
      interna mais *porque* tem UTI).
- [ ] Verificar que a lista da **Etapa 2** exclui `internacoes_icsap`,
      `internacoes_total` e `icsap_por_10mil` — são o alvo reescrito.

### S3 — Estabilidade da taxa em município pequeno

- [ ] Plotar `taxa_icsap` contra `internacoes_total` e mostrar o funil: variância
      explode quando o denominador é pequeno.
- [ ] Quantificar: quantos municípios-ano têm menos de 30 internações no ano?
      Qual a taxa média deles contra a dos demais?

Município com 2 mil habitantes e 3 internações ICSAP tem taxa de 100% por acaso.
Sem piso de denominador, esses pontos dominam a cauda da distribuição e o modelo
de regressão vai gastar capacidade tentando prever ruído.

### S4 — O choque da pandemia

- [ ] Plotar `taxa_icsap` média por ano e verificar a queda em 2020–2021.
- [ ] Plotar `leitos_uti` total por ano e verificar o pico em 2020–2021.
- [ ] Decidir e **escrever** o que será feito: manter com `periodo_pandemia`
      como atributo, ou excluir os dois anos.

Em 2020 as pessoas deixaram de se internar por causa evitável — não porque a
atenção primária melhorou, mas porque ninguém ia ao hospital. Interpretar essa
queda como melhoria da APS seria um erro grave de leitura.

### S5 — A aproximação do ICSAP

- [ ] Confirmar que o notebook declara `taxa_icsap` como **aproximação** da
      Lista Brasileira, com o link para
      [`03-icsap-operacionalizacao.md`](03-icsap-operacionalizacao.md).
- [ ] *(se der tempo)* Baixar o microdado do SIH de **uma UF, um ano**, calcular
      a taxa exata e comparar com a nossa. Isso transforma a limitação de
      argumento em número.

### S6 — Sanidade das junções

- [ ] `cod_ibge7` único por município: 5.570 valores distintos.
- [ ] Nenhum município-ano duplicado: `df.duplicated(['cod_ibge7','ano']).sum() == 0`.
- [ ] Colunas de contagem sem valor negativo.
- [ ] `pct_prenatal_7mais` e `taxa_icsap` dentro de [0, 1].
- [ ] Percentuais de VAB somando ≈ 1 por linha.

### S7 — Padrão dos valores ausentes

- [ ] Para cada coluna com `NaN`, verificar se o padrão é aleatório ou
      estruturado. `pib_per_capita` faltando é aleatório? Ou concentra em
      município recém-criado?

Ausência estruturada não pode ser imputada pela média — a média vem de uma
população diferente daquela que gerou o buraco.

### S8 — O básico do enunciado

- [ ] Mais de 1.000 instâncias ✔ (55.700)
- [ ] Mais de 10 atributos ✔ (47 colunas)
- [ ] Tipo de tarefa declarado, com variável-alvo identificada e justificada
- [ ] **Toda figura acompanhada de interpretação** — o enunciado cobra isso
      explicitamente; é o item mais fácil de perder ponto
- [ ] Notebook executa do começo ao fim sem erro, com as saídas salvas

---

## Trade-offs assumidos

| # | Escolhemos | Em vez de | Ganho | Preço |
|---|---|---|---|---|
| T1 | TabNet agregado | Microdados `.dbc` via PySUS | Base cabe no repositório, reprodutível, sem 30 GB de download | `taxa_icsap` é aproximada, não exata |
| T2 | Painel município × ano | Corte transversal de um ano | 55.700 instâncias, `ano` como atributo, pandemia visível | Linhas não independentes; exige CV agrupada |
| T3 | `tem_uti` como alvo | "Tem estabelecimento de saúde" | Desbalanceamento genuíno (~13%), problema com conteúdo | Alvo mede *cadastro*, não *funcionamento* |
| T4 | Município de residência | Município de internação | Elimina o viés de fluxo, que é enorme | Perde a leitura de "quanto o município atrai pacientes" |
| T5 | Dezembro como foto do CNES | Média das 12 competências | Convenção do MS, leitura direta | Sensível a abertura/fechamento pontual de leito |
| T6 | Estimativa TCU como população | Estimativa SIDRA / Censo 2022 | Mesmo denominador do Ministério da Saúde; série sem degrau | Não incorpora a revisão do Censo 2022 |
| T7 | Zero para ausência no CNES | `NaN` + imputação | Reflete a realidade: não existe leito ali | Confunde "não tem" com "não informou", se houver subnotificação |
| T8 | Área do Censo 2010 fixa | Área revisada ano a ano | Simplicidade; a variação é mínima | Pequeno erro em municípios com limite revisado |

---

## Melhorias possíveis

Ordenadas por **retorno analítico ÷ esforço**.

### M1 — Distância até o município com UTI mais próxima *(alto retorno)*

Hoje o modelo não sabe nada sobre **vizinhança**. Um município sem UTI a 20 km
de uma capital é situação completamente diferente de um a 300 km da cidade mais
próxima com UTI — e os dois estão idênticos na base atual.

Como fazer: baixar os centroides da malha municipal
(`https://servicodados.ibge.gov.br/api/v3/malhas/municipios/{id}?formato=application/vnd.geo+json`)
ou a tabela de coordenadas de sedes municipais do IBGE, e calcular a distância
haversine até o município mais próximo com `tem_uti == 1`.

**É provavelmente o atributo mais forte que falta**, e é o que transforma o
resultado de "municípios pequenos não têm UTI" (óbvio) em "estes municípios
estão longe de tudo" (útil).

### M2 — Cobertura da Estratégia Saúde da Família *(alto retorno)*

A cobertura de ESF por município é o indicador direto de atenção primária, e é
exatamente a variável que deveria explicar `taxa_icsap`. Está no e-Gestor AB
(`https://egestorab.saude.gov.br/`), em relatório público — mas a interface é
JSF e não tem API, então exige download manual ou automação de navegador.

### M3 — Validar a aproximação do ICSAP contra o microdado *(médio)*

Ver [S5](#s5--a-aproximação-do-icsap). Uma UF, um ano, um número.

### M4 — ICSAP por faixa etária *(médio)*

A literatura costuma calcular ICSAP separando menores de 5 anos e maiores de 60.
O TabNet do SIH tem `Faixa_Etária_1` como dimensão de filtro — o custo é apenas
mais consultas. Daria três alvos em vez de um, e o de menores de 5 anos é o mais
sensível à qualidade da APS.

### M5 — Equipamentos do CNES *(baixo, fácil)*

`cnes/cnv/equipobr.def` traz mamógrafo, tomógrafo, raio-X por município. Entra
como atributo de oferta com o mesmo padrão dos demais.

### M6 — Indicadores sociais além do PIB *(médio)*

Saneamento, escolaridade e renda domiciliar do Censo 2022 (SIDRA) explicam
internação evitável melhor que PIB per capita, que é dominado por município com
indústria extrativa e distorce a leitura.

### M7 — Revisão do denominador populacional pós-Censo *(baixo)*

Rodar a base com a série do SIDRA e comparar as taxas. Se o ordenamento dos
municípios não mudar, a escolha do denominador está validada como irrelevante —
e isso é um resultado que vale uma frase no relatório.
