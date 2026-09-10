# CLAUDE.md

Instruções para agentes trabalhando neste repositório.

## O que é este projeto

Trabalho da disciplina **CIN0144 — Aprendizado de Máquina e Ciência de Dados**
(CIn/UFPE, 2026.1), grupo de 4 pessoas. Prevê (1) se um município brasileiro tem
leito de UTI e (2) a taxa de internações por condições sensíveis à atenção
primária (ICSAP). Leia [`docs/00-guia-do-projeto.md`](docs/00-guia-do-projeto.md)
antes de qualquer coisa.

A entrega atual é a **Entrega 1 — Análise Exploratória de Dados**.

## Regras inegociáveis

### 1. Nunca invente fonte de dados

Toda fonte deste projeto é **pública, governamental e verificada**. Se você
precisar de um dado novo:

1. encontre a fonte oficial (IBGE, DATASUS, Ministério da Saúde);
2. **teste o endpoint de verdade** antes de escrever código que dependa dele;
3. registre em `src/fontes.py` com URL, licença, cobertura e data de acesso;
4. documente em `docs/01-fontes-de-dados.md`.

Não use dataset do Kaggle como fonte primária. Não invente URL "que deveria
existir". Se uma fonte estiver fora do ar, diga isso — não substitua por
estimativa.

### 2. Não corrija dado na Entrega 1

O enunciado é explícito: esta entrega é **exploratória**. `build_dataset.py` faz
junção, agregação e as taxas que definem os alvos. Não imputa, não remove
outlier, não padroniza, não codifica, não balanceia. Hipóteses de
pré-processamento são **escritas**, não aplicadas.

### 3. Vazamento de atributo

A lista canônica é `src/fontes.py` (`VAZAMENTO_ETAPA1`/`VAZAMENTO_ETAPA2`) —
`src/gerar_dicionario.py` e `notebooks/01-eda.ipynb` validam contra ela com
`assert`. Ao mexer em qualquer lista de atributos, edite `fontes.py` primeiro
e releia `docs/04`, seção S2. Resumo (13 + 9 colunas, não repita esta lista de
cabeça em outro lugar do repositório — ela já divergiu entre CLAUDE.md, o
notebook e `docs/04` uma vez):

- Etapa 1 (`tem_uti`) não pode usar `leitos_uti`, `leitos_complementares`,
  `leitos_internacao`, `leitos_internacao_sus`, `leitos_por_mil_hab`,
  `leitos_sus_por_mil_hab`, `estab_hospital`, `internacoes_total`,
  `tx_internacao_por_mil`, `equip_manut_vida`, `dist_hospital_km`,
  `vazio_assistencial` — **nem `dist_uti_km`**, que vale **exatamente 0 quando
  `tem_uti = 1`** e nunca 0 quando é 0: a condição `== 0` *é* o alvo, e sozinha
  entrega AUC 1,0 (medido em `docs/04`, M-S2). Para modelar isolamento, use
  `dist_uti_externa_km`, que ignora o próprio município. Na EDA descritiva
  `dist_uti_km` continua válido **desde que filtrado a quem não tem UTI**, que é
  como o notebook já o usa.
- Etapa 2 (`taxa_icsap`) não pode usar `internacoes_icsap`, `internacoes_total`,
  `icsap_por_10mil`, `taxa_icsap_menor5`, `taxa_icsap_idoso`,
  `intern_menor5_total`, `intern_menor5_icsap`, `intern_idoso_total`,
  `intern_idoso_icsap` (mesmo alvo por faixa etária).

### 4. Município de residência, sempre

SIH, SIM e SINASC têm versão "por local de ocorrência". Nunca use. Ver `docs/02`, D4.

## Convenções de código

- **Português** em nomes, comentários e docstrings. Código sem acento (evita
  problema de encoding no Windows); texto de documentação **com** acento.
- **Comentários didáticos.** Este repositório é material de estudo do grupo.
  Comentário aqui explica **o conceito**, **por que a escolha** e **como
  interpretar o resultado** — não o que a linha de código faz.
- Toda fonte nova entra em `src/fontes.py`, nunca hardcoded no notebook.
- Nada de `pip install` de biblioteca pesada sem necessidade real. O projeto
  roda com pandas, numpy, matplotlib, seaborn e scikit-learn.

## Detalhes que já custaram tempo

- **TabNet responde em latin-1**, e os nomes dos campos do formulário também
  (`SMunicípio`). O corpo do POST precisa ser codificado em latin-1.
- **O TabNet não fecha `<TH>` nem `<TD>`.** O parser de `tabnet.py` corta a
  célula na próxima abertura, não numa tag de fechamento.
- **Toda dimensão de filtro precisa ir no POST** com `TODAS_AS_CATEGORIAS__`.
  Se faltar uma, a resposta é "Tabela de conversao nao encontrada".
- **DATASUS usa código IBGE de 6 dígitos**; o IBGE usa 7. A diferença é o dígito
  verificador. Junção sempre por `cod_ibge6`, exceto SIDRA, que usa 7.
- **SIDRA devolve HTTP 400** se a consulta tiver células demais. Quebre por ano.
- **A malha do IBGE devolve os 5.570 polígonos numa requisição** de 3,6 MB
  (`qualidade=minima`). O centroide é por área (shoelace), não média de vértices.
- **`ftp.datasus.gov.br` é instável** e estava inacessível em 10/09/2026. Não
  escreva pipeline que dependa dele sem fallback.

## Rodando

```bash
python src/ingestao.py [etapa ...]   # sem argumento roda tudo
python src/build_dataset.py
```

A ingestão tem cache em `data/raw/tabnet/`, indexado pelo conteúdo da consulta.
Consulta repetida não vai à rede. Ao mudar período ou alvo, apague
`data/interim/` e `data/processed/` — o `raw` pode ficar.

## Atribuição

Commits e PRs deste repositório levam **apenas a autoria da dona do
repositório**. Não adicione trailer `Co-Authored-By`, nem assinatura de
ferramenta em mensagem de commit ou descrição de PR.
