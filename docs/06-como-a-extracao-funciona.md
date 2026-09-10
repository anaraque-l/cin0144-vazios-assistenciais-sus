# Como a extração funciona

Este documento existe para responder uma pergunta específica: **de onde veio
cada número da tabela analítica, e como auditar isso.**

Ele descreve o mecanismo. *Quais* fontes foram usadas está em
[`01-fontes-de-dados.md`](01-fontes-de-dados.md); *por que* essas e não outras,
em [`02-decisoes-e-escopo.md`](02-decisoes-e-escopo.md).

---

## 1. O fluxo, em uma linha

```
TabNet/SIDRA  →  data/raw/*.gz  →  data/interim/*.csv  →  data/processed/municipio_ano.csv
   (rede)         (congelado)       (1 por fonte)              (tabela analítica)
    UMA VEZ        versionado       ingestao.py              build_dataset.py
```

A rede é tocada **uma única vez por consulta**. Depois disso tudo sai do disco.

## 2. Não baixamos CSV nenhum do DATASUS

Este é o ponto que costuma surpreender.

O TabNet exibe um botão **"Copia como .CSV"** na página de resultado — mas ele é
JavaScript que monta o arquivo **no navegador**, a partir da tabela já
renderizada. Não existe URL de CSV para requisitar. O que o servidor devolve a
um POST é **uma página HTML** com a tabulação dentro de um `<TABLE>`.

Então a extração é: **montar o POST → receber HTML → parsear a tabela → virar
DataFrame → gravar CSV nosso**. Os únicos CSV do projeto são os que nós
escrevemos (`data/interim/` e `data/processed/`).

O IBGE é diferente e mais simples: a API do SIDRA e a de Localidades devolvem
**JSON**, sem autenticação. Ver `src/ibge.py`.

## 3. Como uma consulta ao TabNet é montada

Todo `.def` do DATASUS (`cnes/cnv/leiutibr.def`, `sih/cnv/nrbr.def`, ...) é um
formulário HTML antigo — TabNet Win32 3.3. `src/tabnet.py` faz duas coisas:

**`descrever(definicao)`** — baixa o formulário e lê, por regex, as opções
válidas de cada campo:

| Campo | O que é |
|---|---|
| `Linha` | A dimensão que vira **linha** da tabela (para nós, quase sempre `Município`) |
| `Coluna` | A dimensão que vira coluna (`Leitos_complementares`, `Consult_pré-natal`, ou nenhuma) |
| `Incremento` | A **medida** (`Quantidade_existente`, `Internações`, `Óbitos_p/Residênc`) |
| `Arquivos` | As **competências** (`lubr2312.dbf` = Dez/2023) — aceita várias, e o TabNet soma |
| `S<dimensão>` | Os filtros (`SMunicípio`, `SLista_Morb__CID-10`, `SFaixa_Etária`...) |

**`consultar(...)`** — monta o corpo do POST com esses campos e envia.

### Os quatro detalhes que quebram tudo

Estão no docstring de `src/tabnet.py` e em `CLAUDE.md`, e repetidos aqui porque
são o que faz a diferença entre funcionar e não funcionar:

1. **Toda dimensão de filtro precisa ir no POST**, mesmo as que não queremos
   filtrar — com o valor `TODAS_AS_CATEGORIAS__`. Se faltar uma, a resposta é
   `Tabela de conversao nao encontrada`, e não um erro que diga o que houve.

2. **Tudo é latin-1.** Não só o conteúdo: os **nomes dos campos** também
   (`SMunicípio`, `Unidade_da_Federação`). O corpo do POST tem que ser
   percent-encoded a partir de bytes latin-1, não utf-8.

3. **O TabNet não fecha `<TH>` nem `<TD>`.** Um parser HTML estrito não separa
   as células. Por isso o corte é feito pela **próxima abertura** de célula ou
   pelo fim da linha — é o que faz `_RE_CELULA` em `tabnet.py`.

4. **Número vem em formato brasileiro** (`1.971` = mil novecentos e setenta e
   um) e célula vazia vem como `-`. Quem converter com `float()` direto obtém
   1,971 e erra por três ordens de grandeza.

### Filtrar por CID: o caso do ICSAP

O alvo da Etapa 2 usa o filtro `SLista_Morb__CID-10`, passando de uma vez os
~60 códigos de grupo que compõem a lista aproximada de ICSAP
(`icsap.codigos_lista_morb()`). O TabNet aceita o campo repetido e soma tudo.

É por isso que a base inteira sai em **~70 consultas** e não em milhões de
linhas de microdado: cada consulta já devolve o agregado município × ano.

## 4. Como o HTML vira DataFrame

`parse_tabela()` faz, em ordem:

1. recorta o `<TABLE>` e **descarta o `<TFOOT>`** (é o rodapé com a fonte);
2. quebra em linhas por `<TR`;
3. **ignora qualquer linha com `COLSPAN`** — são as faixas de título e de nota,
   não dados;
4. a linha só de `<TH>` vira o **cabeçalho**; as com `<TD>`, os dados;
5. **descarta a linha `Total`**;
6. converte as colunas numéricas com `_numero()`, que trata o separador
   brasileiro e devolve `NaN` para `-`.

Depois, `separar_codigo_nome()` quebra `261160 RECIFE` em código e nome. O
código do DATASUS tem **6 dígitos** — é o do IBGE sem o dígito verificador — e
é a chave `cod_ibge6` usada em toda junção com fonte de saúde. O SIDRA usa 7
dígitos (`cod_ibge7`).

## 5. O cache congelado

Cada resposta é gravada em `data/raw/tabnet/<def>__<sha1>.html.gz`, onde o
`sha1` é o hash **do conteúdo da consulta** (linha, coluna, incremento,
arquivos, filtros).

Duas consequências:

- **consulta idêntica não vai à rede** — a base do repositório roda offline;
- **consulta diferente gera arquivo novo** — mudar o período em `fontes.py` não
  exige limpar `data/raw/`, só `data/interim/` e `data/processed/`.

O `.gz` não é detalhe: as respostas a nível municipal somam ~224 MB e comprimem
para ~12 MB. Sem isso a base congelada não caberia com conforto num repositório
Git.

## 6. Da tabulação à tabela analítica

**`src/ingestao.py`** — uma função por fonte. Cada uma consulta, parseia,
renomeia para nomes de coluna nossos e grava um CSV em `data/interim/`.

**`src/build_dataset.py`** — junta tudo. Duas regras que definem o resultado:

- **parte do universo**: começa da lista completa dos 5.570 municípios do IBGE
  e traz o resto por `left join`. Se partisse do CNES, perderia exatamente os
  municípios sem serviço — que são o objeto do estudo;
- **ausência no CNES/SIH/SIM/SINASC vira `0`, não `NaN`**: o TabNet só devolve
  linha para município que tem o recurso, então não aparecer significa "não
  existe leito de UTI aqui". Ver [`02-decisoes-e-escopo.md`](02-decisoes-e-escopo.md), D7.

## 7. Como auditar um número

Esta é a parte que justifica o documento. Suponha que alguém questione os
**1.723 leitos de UTI do Recife em 2023**.

```python
import gzip, pathlib, re

# 1. achar o HTML bruto da competência certa
for f in sorted(pathlib.Path("data/raw/tabnet").glob("cnes_cnv_leiutibr__*.html.gz")):
    h = gzip.open(f, "rt", encoding="latin-1").read()
    periodo = re.search(r"Per&iacute;odo:</b>\s*([^<\r\n]+)", h)
    if periodo and periodo.group(1).strip() == "Dez/2023":
        print(f.name)
        i = h.find("261160 RECIFE")           # código de 6 dígitos
        print(re.sub(r"\s+", " ", re.sub("<[^>]+>", " | ", h[i:i+420])))
        break
```

Saída (uma coluna por tipo de leito complementar, na ordem do cabeçalho):

```
261160 RECIFE | 56 | 57 | 122 | 916 | 216 | 21 | 193 | 23 | 62 | 114 | 18 | 2 | 36 | - | 87 | 37 | 4 | 7 | - | 1.971
```

O `1.971` do fim é o **total de leitos complementares** — e é exatamente o que a
base traz em `leitos_complementares`. O `leitos_uti` = 1.723 é esse total menos
as seis categorias que **não** são terapia intensiva:

| Categoria excluída | Valor |
|---|---|
| Unidade intermediária neonatal | 56 |
| Unidade isolamento | 57 |
| Unidade de cuidados intermed neonatal convencional | 87 |
| Unidade de cuidados intermed neonatal canguru | 37 |
| Unidade de cuidados intermed pediátrico | 4 |
| Unidade de cuidados intermed adulto | 7 |
| **Soma** | **248** |

1.971 − 248 = **1.723**. ✔

A lista do que conta como UTI está em `LEITOS_UTI`, em
[`src/fontes.py`](../src/fontes.py) — e é a única coisa que precisa mudar para
redefinir o alvo da Etapa 1.

## 8. Reproduzir do zero

```bash
python src/ingestao.py         # usa data/raw se existir; só baixa o que faltar
python src/build_dataset.py
python src/gerar_dicionario.py
```

Com o `data/raw/` do repositório, isso roda **sem rede** e reproduz a mesma
tabela byte a byte. Foi assim que a base atual foi regerada depois de trocar o
cache para `.gz` — os números conferiram.
