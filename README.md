# Vazios assistenciais no SUS

**CIN0144 — Aprendizado de Máquina e Ciência de Dados · CIn/UFPE · 2026.1**
Entrega 1 — Análise Exploratória de Dados

---

## Tema

> Prever, a partir de dados públicos do IBGE e do DATASUS, se um município
> brasileiro tem leito de UTI e qual fatia de suas internações seria evitável
> pela atenção primária — usando os **erros** do modelo para mapear os vazios
> assistenciais do SUS.

| | Pergunta | Tarefa | Alvo |
|---|---|---|---|
| **Etapa 1** | O município tem leito de UTI? | Classificação binária desbalanceada | `tem_uti` |
| **Etapa 2** | A atenção primária está segurando o paciente? | Regressão | `taxa_icsap` |

O produto final não é a acurácia do modelo — é a **lista dos municípios em que
o modelo erra** na Etapa 1: os que, pelo perfil, deveriam ter UTI e não têm.

## A base

- **Unidade:** município × ano · **Período:** 2014–2023
- **55.700 instâncias** (5.570 municípios × 10 anos) · **47 atributos**
- Fontes governamentais abertas: **IBGE** (malha, PIB, área) e **DATASUS**
  (CNES, SIH, SIM, SINASC). Nenhuma exige cadastro ou chave.
- Arquivo final: `data/processed/municipio_ano.csv`

## Como rodar

```bash
pip install -r requirements.txt
python src/ingestao.py          # baixa e congela as fontes (20-60 min na 1ª vez)
python src/build_dataset.py     # monta a tabela analítica
jupyter lab notebooks/01-eda.ipynb
```

A ingestão guarda a resposta bruta de cada consulta em `data/raw/`. Depois da
primeira execução tudo vem do cache — não depende mais de rede.

## Documentação

| Arquivo | Para quê |
|---|---|
| [`docs/00-guia-do-projeto.md`](docs/00-guia-do-projeto.md) | **Comece aqui.** Como entender, rodar e mexer no projeto. |
| [`docs/01-fontes-de-dados.md`](docs/01-fontes-de-dados.md) | Ficha de cada fonte: URL, licença, cobertura, o que foi extraído. |
| [`docs/02-decisoes-e-escopo.md`](docs/02-decisoes-e-escopo.md) | Cada decisão com alternativa descartada e motivo. |
| [`docs/03-icsap-operacionalizacao.md`](docs/03-icsap-operacionalizacao.md) | Como a Lista Brasileira de ICSAP virou número, e onde diverge. |
| [`docs/04-melhorias-tradeoffs-sensibilidades.md`](docs/04-melhorias-tradeoffs-sensibilidades.md) | Checklist antes de entregar · trade-offs · o que melhorar depois. |
| [`docs/05-dicionario-de-dados.md`](docs/05-dicionario-de-dados.md) | Cada coluna: tipo, origem, unidade, papel na modelagem. |
| [`docs/06-como-a-extracao-funciona.md`](docs/06-como-a-extracao-funciona.md) | De onde veio cada número e **como auditar um valor** até o HTML bruto. |
| [`docs/relatorio-entrega1.md`](docs/relatorio-entrega1.md) | **O relatório da Entrega 1** — descrição da base, EDA, diagnóstico e hipóteses. |

## Estrutura

```
src/
  fontes.py          registro único de toda fonte (URL, .def, licença, período)
  tabnet.py          cliente do TabNet/DATASUS com cache em disco
  ibge.py            APIs de Localidades e SIDRA
  icsap.py           Lista Brasileira de ICSAP e seu mapeamento
  ingestao.py        uma função por fonte -> data/interim/
  build_dataset.py   junta tudo -> data/processed/
data/
  raw/               respostas brutas congeladas (versionadas)
  interim/           uma tabela por fonte
  processed/         a tabela analítica
notebooks/
  01-eda.ipynb       a Entrega 1
```

## Fontes

- IBGE — [API de Localidades](https://servicodados.ibge.gov.br/api/docs/localidades) ·
  [SIDRA 5938 (PIB municipal)](https://sidra.ibge.gov.br/tabela/5938) ·
  [SIDRA 1301 (área)](https://sidra.ibge.gov.br/tabela/1301)
- DATASUS — [TabNet / Informações de Saúde](https://datasus.saude.gov.br/informacoes-de-saude-tabnet/) ·
  [CNES](https://cnes.datasus.gov.br/)
- Ministério da Saúde — [Portaria SAS/MS nº 221/2008](https://bvsms.saude.gov.br/bvs/saudelegis/sas/2008/prt0221_17_04_2008.html)
  (Lista Brasileira de ICSAP)
