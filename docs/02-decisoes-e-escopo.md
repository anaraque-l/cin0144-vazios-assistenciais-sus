# Escopo e decisões de projeto

Registro das decisões que moldaram a base. Cada uma tem alternativa descartada
e motivo — é isso que o enunciado chama de *"todas as decisões devem ser
explicitamente justificadas"*.

---

## D1 — O alvo da Etapa 1 não pode ser "tem estabelecimento de saúde"

**Decisão:** o alvo é `tem_uti` (o município tem ao menos um leito de UTI).

**Por quê:** praticamente 100% dos municípios brasileiros têm algum
estabelecimento de saúde cadastrado no CNES. Sem variação no alvo não existe
problema de classificação — o modelo aprenderia a constante. É preciso *subir na
escada de complexidade* até achar o serviço cuja presença ainda varia entre
municípios. UTI fica na faixa de ~13% de positivos: desbalanceamento genuíno.

**Alternativas consideradas:** serviço de oncologia, hemodiálise, maternidade de
alto risco. Todos serviriam; UTI foi escolhida por ser a de leitura mais direta
para quem lê o relatório, e por estar numa dimensão limpa do CNES
(`Leitos complementares`).

## D2 — Painel município × ano, não corte transversal

**Decisão:** 5.570 municípios × 10 anos (2014–2023) = 55.700 instâncias.

**Por quê:**
- o enunciado exige mais de 1.000 instâncias; o corte transversal daria 5.570 e
  o painel dá 55.700;
- `ano` entra como atributo sem custo, e com ele o choque da pandemia fica
  visível em vez de virar ruído;
- vazio assistencial é fenômeno persistente: observar o mesmo município dez
  vezes é informação sobre estabilidade, não repetição inútil.

**O preço, declarado:** as linhas **não são independentes**. Isso não afeta a
Entrega 1 (exploratória), mas obriga, na modelagem, validação cruzada agrupada
por município. Ver [`04`](04-melhorias-tradeoffs-sensibilidades.md#s1).

## D3 — Janela 2014–2023

**Por quê 2014 como início:** é o primeiro ano em que o CNES já está estável
após a reformulação do cadastro, e a série do SIH está madura.

**Por quê 2023 como fim:** é o último ano com PIB municipal do IBGE publicado
(tabela 5938) e com estimativa populacional TCU disponível no DATASUS. Puxar
para 2024/2025 quebraria o denominador de todas as taxas.

## D4 — Município de **residência**, não de internação

**Decisão:** todo indicador de uso (SIH), mortalidade (SIM) e natalidade
(SINASC) é atribuído ao município onde a pessoa **mora**.

**Por quê:** o SIH registra os dois. Quem mora em município pequeno se interna
na cidade média vizinha, que é onde está o hospital. Atribuindo ao município do
hospital, o pequeno apareceria com zero internações (parecendo saudável) e o
médio com internações de toda a região (parecendo doente). O viés seria enorme e
correlacionado exatamente com a variável que queremos explicar.

**É a decisão metodológica mais importante do projeto.**

## D5 — TabNet em vez de microdados

**Decisão:** toda a extração do DATASUS passa pelo TabNet.

**Por quê:** volume (30+ GB de `.dbc` contra alguns MB de HTML), estabilidade
(o FTP do DATASUS cai com frequência) e reprodutibilidade (as respostas do
TabNet cabem no repositório e ficam congeladas em `data/raw/`).

**O preço:** o alvo da Etapa 2 vira uma aproximação declarada da Lista
Brasileira de ICSAP. Custo detalhado em
[`03-icsap-operacionalizacao.md`](03-icsap-operacionalizacao.md).

## D6 — Dezembro como foto do CNES

**Decisão:** para CNES (leitos e estabelecimentos), o valor do ano é a
competência de **dezembro**.

**Por quê:** o CNES é um cadastro, não um fluxo. A competência de dezembro é a
foto do fim do ano — a mesma convenção usada nos indicadores do Ministério da
Saúde. Média das 12 competências seria defensável, mas suavizaria abertura e
fechamento de leito, que são justamente eventos de interesse.

**Consequência visível:** o pico de leitos de UTI em 2020–2021 (leitos COVID)
aparece na base. Isso é real e está marcado por `periodo_pandemia`.

## D7 — Ausência no CNES é zero, não valor faltante

**Decisão:** município que não aparece na tabulação do CNES recebe `0`, não `NaN`.

**Por quê:** o TabNet só devolve linha para município que **tem** o recurso. Não
aparecer significa "não existe leito de UTI aqui" — é ausência estrutural, um
zero verdadeiro. Tratar como faltante e imputar a média seria inventar UTI onde
não há.

**A mesma regra vale para SIH, SIM e SINASC:** município sem internação
registrada no ano recebe zero.

**O que *não* segue essa regra:** PIB (IBGE não publica para município recém
criado) e as taxas derivadas com denominador zero. Esses ficam `NaN` de verdade e
são diagnosticados na EDA.

## D8 — Nada é corrigido na Entrega 1

**Decisão:** `build_dataset.py` faz junção, agregação e as taxas que definem os
alvos. Nada de imputação, remoção de outlier, padronização, codificação ou
balanceamento.

**Por quê:** o enunciado é explícito — *"Esta entrega é exploratória: o foco está
em descrever, visualizar e diagnosticar os dados, e não em aplicar correções"*.
As correções entram na etapa de pré-processamento, e as hipóteses sobre elas
estão registradas no notebook e em [`04`](04-melhorias-tradeoffs-sensibilidades.md).

## D9 — Fernando de Noronha fica de fora

**Decisão:** a API do IBGE devolve 5.571 registros; a tabela analítica tem 5.570.

**Por quê:** Fernando de Noronha (2605459) é distrito estadual de Pernambuco, não
município. Aparece na malha do IBGE mas não no DATASUS, o que geraria uma linha
com todos os indicadores de saúde faltantes por construção.
