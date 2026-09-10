# Guia para dominar o projeto

> Leia este arquivo antes de qualquer outro. Ele existe para que qualquer pessoa
> do grupo consiga **explicar, rodar e mexer** no projeto sem depender de quem
> escreveu o código.

---

## 1. A ideia em um parágrafo

Todo município brasileiro tem *algum* serviço de saúde — então perguntar "tem
posto de saúde?" não prevê nada. A pergunta que ainda tem resposta variável é
outra, e ela vem em dois níveis:

| | Pergunta | Tipo de tarefa | Alvo |
|---|---|---|---|
| **Etapa 1** | O município tem **leito de UTI**? | Classificação binária desbalanceada | `tem_uti` |
| **Etapa 2** | Onde há atendimento, a **atenção primária está funcionando**? | Regressão | `taxa_icsap` |

E o produto final **não é a acurácia do modelo**. É a lista dos municípios em
que o modelo erra na Etapa 1 — os que, pelo porte, população e economia,
"deveriam" ter UTI e não têm. Isso é o que a literatura de saúde pública chama
de **vazio assistencial**.

## 2. Por que ICSAP é a parte interessante

**ICSAP = Internações por Condições Sensíveis à Atenção Primária.**

O raciocínio: se a atenção básica funciona no seu município, você **não** é
internado por pneumonia bacteriana, diabetes descompensado, hipertensão ou
infecção urinária — essas internações são evitáveis com acompanhamento
ambulatorial. Logo:

> taxa alta de ICSAP ⇒ a porta de entrada do SUS não está segurando o paciente

É um indicador de **função**, não de **prédio**. E não vem pronto em base
nenhuma: nós o construímos a partir do CID-10 de cada internação. Isso muda o
projeto de *"aplicamos sklearn num CSV"* para *"formulamos um problema"*.

A lista oficial é a da **Portaria SAS/MS nº 221, de 17/04/2008** (19 grupos de
causas). Como operacionalizamos essa lista — e onde a nossa versão diverge da
oficial — está em [`03-icsap-operacionalizacao.md`](03-icsap-operacionalizacao.md).
**Isso vai ser perguntado na apresentação. Leia esse arquivo.**

## 3. A base

- **Unidade de análise:** município × ano
- **Período:** 2014–2023 (10 anos)
- **Instâncias:** 55.700 (5.570 municípios × 10 anos)
- **Atributos:** 53 colunas, das quais **36 são candidatas a preditor**
  (9 são proibidas por vazamento, 3 são identificadores, 4 são alvo ou componente de alvo)
- **Formato:** `data/processed/municipio_ano.csv`

Tudo vem de fonte **governamental e aberta**: IBGE (malha municipal, PIB, área,
população) e DATASUS (CNES, SIH, SIM, SINASC). Nenhuma exige cadastro ou chave.
A ficha de cada fonte está em [`01-fontes-de-dados.md`](01-fontes-de-dados.md).

## 4. Como o código está organizado

```
src/
  fontes.py         Registro único de TODA fonte: URL, .def, licença, período.
                    Se você quer saber "de onde veio esse número", começa aqui.
  tabnet.py         Cliente do TabNet/DATASUS. Formulário HTML de 2003; o
                    módulo lê o formulário, monta o POST e parseia a resposta.
  ibge.py           APIs do IBGE: Localidades (malha) e SIDRA (PIB, área).
  icsap.py          A Lista Brasileira de ICSAP e o mapeamento dela para a
                    dimensão que o TabNet realmente expõe.
  geografia.py      Centroides da malha do IBGE e distância até o serviço
                    mais próximo. É o atributo que não é proxy de tamanho.
  ingestao.py       Uma função por fonte -> data/interim/*.csv
  build_dataset.py  Junta tudo -> data/processed/municipio_ano.csv
data/
  raw/              Base CONGELADA: HTML/JSON bruto de cada consulta. Versionado.
  interim/          Uma tabela por fonte, já com cod_ibge6 e ano.
  processed/        A tabela analítica final.
notebooks/
  01-eda.ipynb      A Entrega 1.
```

O fluxo é uma linha reta:

```
fontes públicas -> data/raw (congelado) -> data/interim -> data/processed -> notebook
```

### Ordem de leitura — o que priorizar

São ~1.500 linhas de Python, mas **elas não têm o mesmo peso**. Em ordem de
retorno por minuto lido:

| # | Arquivo | Linhas | Por que ler | Prioridade |
|---|---|---:|---|---|
| 1 | `build_dataset.py` | 233 | **Onde os dois alvos nascem** e onde cada taxa é definida. É o arquivo que responde "o que exatamente é `taxa_icsap`?" | 🔴 todo mundo |
| 2 | `fontes.py` | 180 | Catálogo, sem lógica. Responde "de onde veio esse número?" e é onde se muda período e definição de UTI | 🔴 todo mundo |
| 3 | `icsap.py` | 128 | O mapeamento portaria → TabNet, com a divergência declarada grupo a grupo. **É o que a banca vai questionar** | 🔴 todo mundo |
| 3b | `geografia.py` | 195 | Centroide e haversine. Explica **por que** o isolamento entrou e qual a limitação dele | 🔴 todo mundo |
| 4 | `notebooks/01-eda.ipynb` | 23 células | A entrega em si | 🔴 todo mundo |
| 5 | `ingestao.py` | 362 | Uma função por fonte, todas com a mesma forma. Leia **uma** (`leitos_uti`) e você leu as nove | 🟡 quem for mexer em fonte |
| 6 | `ibge.py` | 169 | APIs REST comuns. O único ponto não óbvio são os códigos de variável do SIDRA | 🟡 quem for mexer em fonte |
| 7 | `tabnet.py` | 314 | Encanamento: monta POST, parseia HTML. **Funciona e não precisa ser tocado** | 🟢 curiosidade |
| 8 | `gerar_dicionario.py` | 120 | Gera um `.md`. Só descrição de coluna | 🟢 se faltar coluna |

**Atalho para quem tem 20 minutos:** leia `build_dataset.py` inteiro, os
comentários `CONCEITO`/`INTERPRETAÇÃO` do notebook, e a tupla `MAPA` de
`icsap.py`. Isso cobre tudo que decide o resultado.

**O que dá para ignorar com tranquilidade:** o parsing de HTML em `tabnet.py`.
É código chato que resolve um site de 2003 — está explicado em
[`06-como-a-extracao-funciona.md`](06-como-a-extracao-funciona.md) se alguém
perguntar, mas ninguém precisa entender regex de `<TD>` sem fechamento para
defender o trabalho.

### Por que existe `data/raw` versionado

Portais de governo mudam de lugar, tiram base do ar e revisam número
retroativamente. Se o `raw` estiver no repositório, a análise de hoje continua
reproduzível em dezembro. É o mesmo motivo pelo qual o `tabnet.py` tem cache em
disco: rodar de novo **não** depende de rede.

## 5. Como rodar

```bash
pip install -r requirements.txt
python src/ingestao.py        # só precisa na primeira vez (usa cache depois)
python src/build_dataset.py
jupyter lab notebooks/01-eda.ipynb
```

A ingestão completa leva de 20 a 60 minutos na primeira vez (o TabNet é lento).
Depois disso é instantâneo, porque tudo vem do cache em `data/raw/tabnet/`.

## 6. Como mexer sem quebrar

| O que você quer fazer | Onde mexer |
|---|---|
| Mudar o período (ex.: 2010–2023) | `src/fontes.py`, constantes `ANO_INICIAL`/`ANO_FINAL` |
| Trocar o alvo da Etapa 1 (ex.: oncologia em vez de UTI) | `src/fontes.py` (`LEITOS_UTI`) e `build_dataset.py` (`tem_uti`) |
| Ajustar quais CIDs contam como ICSAP | `src/icsap.py`, tupla `MAPA` |
| Adicionar um atributo novo do DATASUS | nova função em `src/ingestao.py` + merge em `build_dataset.py` |
| Adicionar um atributo do IBGE | `src/ibge.py` (via `sidra()`) + merge |
| Ver que dimensões uma base do DATASUS tem | `python -c "import sys;sys.path.insert(0,'src');import tabnet;print(tabnet.descrever('sih/cnv/nrbr.def'))"` |

Ao trocar o período ou o alvo, **apague `data/interim/` e `data/processed/`** e
rode a ingestão de novo. O `data/raw/` pode ficar: o cache é indexado pelo
conteúdo da consulta, então consultas novas simplesmente não acham cache.

## 7. O que cada pessoa precisa saber explicar

Divisão sugerida (4 pessoas), pensada para que ninguém dependa de outro para
falar 3 minutos na apresentação:

| Pessoa | Frente | Precisa dominar |
|---|---|---|
| **1** | Fontes e ingestão | De onde vem cada coluna, por que TabNet e não microdado, o que é `data/raw` congelado |
| **2** | Construção dos alvos | O que é ICSAP, por que UTI e não "tem estabelecimento", a chave de 6 vs 7 dígitos |
| **3** | EDA numérica | Distribuições, assimetria, correlação, redundância, o desbalanceamento |
| **4** | Diagnóstico e hipóteses | Ausentes, outliers, taxa instável em município pequeno, o que fazer no pré-processamento |

## 8. As cinco perguntas que a banca faz

1. **"Por que município × ano e não só um ano?"**
   Painel dá 55.700 instâncias em vez de 5.570, e `ano` vira atributo — dá para
   ver o choque da pandemia. O custo é que as linhas não são independentes: o
   mesmo município aparece 10 vezes. Na modelagem isso obriga validação cruzada
   **agrupada por município**, senão o modelo "decora" o município no treino e
   reencontra ele no teste. Está registrado em
   [`04-melhorias-tradeoffs-sensibilidades.md`](04-melhorias-tradeoffs-sensibilidades.md).

2. **"Por que a acurácia não serve na Etapa 1?"**
   Com **10,8%** de positivos, um modelo que responde "não tem UTI" para tudo
   acerta **89,2%**. Métrica principal é AUC e F1 da classe positiva, com
   matriz de confusão.

3. **"Onde está o vazamento (*data leakage*)?"**
   Em dois lugares, e os dois são óbvios *depois* que alguém aponta:
   - `leitos_uti` e `leitos_complementares` **são** o alvo `tem_uti`. Não podem
     ser atributo. Nem `leitos_internacao`, que é quase determinístico.
   - `internacoes_icsap` e `internacoes_total` **são** o alvo `taxa_icsap`.
   Além disso, usar volume de internação para prever presença de UTI é
   circular: município com UTI interna mais *porque* tem UTI.

4. **"Município de residência ou de internação?"**
   **Residência**, sempre. O SIH registra os dois. Quem mora em município
   pequeno se interna na cidade grande vizinha; se atribuíssemos a internação ao
   município do hospital, o pequeno pareceria saudável (nenhuma internação) e o
   grande, doente. É a decisão metodológica mais importante do projeto.

5. **"A taxa não fica instável em município pequeno?"**
   Depende de qual taxa — e a EDA respondeu isso com número, não com palpite.
   Na versão **proporcional** (`taxa_icsap`) quase não fica: a mediana de
   internações por município-ano é **668** e só 2% das linhas ficam abaixo de
   100, então o denominador raramente é pequeno. Na versão **populacional**
   (`icsap_por_10mil`) fica, e muito: desvio-padrão **131** nos municípios de
   até 5 mil habitantes contra **41** nos acima de 100 mil. Foi isso que
   validou empiricamente a escolha da proporção como alvo principal.

## 9. Vocabulário mínimo

| Termo | O que é |
|---|---|
| **CNES** | Cadastro Nacional de Estabelecimentos de Saúde. Diz o que existe. |
| **SIH/SUS** | Sistema de Informações Hospitalares. Uma linha por internação paga pelo SUS. |
| **SIM** | Sistema de Informações sobre Mortalidade. |
| **SINASC** | Sistema de Informações sobre Nascidos Vivos. |
| **TabNet** | Tabulador oficial do DATASUS. Devolve tabela agregada em vez de microdado. |
| **SIDRA** | Banco de tabelas do IBGE, com API pública. |
| **ICSAP** | Internação por Condição Sensível à Atenção Primária. |
| **APS / atenção básica** | Primeiro nível de atenção: UBS, Saúde da Família. |
| **Leito complementar** | Categoria do CNES que reúne UTI e unidades intermediárias. |
| **`cod_ibge6` / `cod_ibge7`** | Código do município sem / com o dígito verificador. DATASUS usa 6; IBGE usa 7. |
