# Fontes de dados

Todas as fontes são **públicas, governamentais e abertas**. Nenhuma exige
cadastro, chave de API ou aceite de termos. Todas foram acessadas e verificadas
em **10/09/2026**; a resposta bruta de cada consulta está congelada em
`data/raw/`.

O registro canônico em código é [`src/fontes.py`](../src/fontes.py) — este
documento é a versão legível dele.

---

## 1. IBGE — API de Localidades

| | |
|---|---|
| **Órgão** | Instituto Brasileiro de Geografia e Estatística |
| **Endpoint** | `https://servicodados.ibge.gov.br/api/v1/localidades/municipios` |
| **Documentação** | https://servicodados.ibge.gov.br/api/docs/localidades |
| **Formato** | JSON, sem autenticação |
| **Licença** | Dados abertos, uso livre com citação (Lei de Acesso à Informação 12.527/2011) |
| **Usado para** | Universo dos municípios, UF, região, mesorregião, microrregião |

**Nota importante:** a API devolve **5.571** registros. São os 5.570 municípios
brasileiros mais **Fernando de Noronha (PE, código 2605459)**, que é distrito
estadual e não município. Ele aparece no IBGE mas não no DATASUS. A tabela
analítica trabalha com os 5.570.

## 2. IBGE — SIDRA, tabela 5938 (PIB dos Municípios)

| | |
|---|---|
| **Endpoint** | `https://apisidra.ibge.gov.br/values/t/5938/n6/all/v/37,498,513,517,6575,525/p/{ano}` |
| **Documentação** | https://sidra.ibge.gov.br/tabela/5938 |
| **Cobertura** | 2002–2023, todos os municípios |
| **Variáveis usadas** | 37 = PIB a preços correntes · 498 = VAB total · 513 = VAB agropecuária · 517 = VAB indústria · **6575 = VAB serviços** (exclusive administração pública) · **525 = VAB administração**, defesa, educação e saúde públicas |
| **Unidade** | Mil reais correntes |

⚠️ **Os códigos não seguem a intuição, e isso já custou um erro.** `525` é
administração pública, **não** serviços; serviços é `6575`. E `543` é
*impostos líquidos de subsídios*, não administração pública. Conferido em
`https://servicodados.ibge.gov.br/api/v3/agregados/5938/metadados`.

⚠️ **Em 2022 e 2023 o IBGE publicou apenas o PIB total** — a abertura setorial
ainda não saiu. É uma lacuna real da fonte, e é a origem dos 20% de valores
ausentes nas colunas `pct_vab_*`, tratada na EDA como ausência estruturada.

A consulta é quebrada **ano a ano**: 5.570 municípios × 6 variáveis × 10 anos
estoura o limite de células por requisição do SIDRA (devolve HTTP 400).

## 3. IBGE — SIDRA, tabela 1301 (Área territorial)

| | |
|---|---|
| **Endpoint** | `https://apisidra.ibge.gov.br/values/t/1301/n6/all/v/615/p/all` |
| **Cobertura** | Censo 2010 |
| **Unidade** | km² |
| **Usado para** | Denominador da densidade demográfica |

Área é tratada como constante no período. Municípios com limite revisado depois
de 2010 carregam pequeno erro — irrelevante na escala de análise, mas
registrado.

## 4. DATASUS — População Residente, Estimativas para o TCU

| | |
|---|---|
| **Acesso** | TabNet, `ibge/cnv/poptbr.def` |
| **Cobertura** | 1992–2023, município × ano |
| **Fonte primária** | IBGE (estimativas enviadas ao Tribunal de Contas da União) |

**Por que esta e não a estimativa do SIDRA:** é o denominador oficial que o
Ministério da Saúde usa para calcular taxas. Usar o mesmo denominador do MS faz
nossos números serem comparáveis com os indicadores publicados. Além disso, a
série do SIDRA muda de metodologia depois do Censo 2022, criando um degrau
artificial em 2022 que não existe na série do TCU.

## 5. DATASUS — CNES, Leitos Complementares

| | |
|---|---|
| **Acesso** | TabNet, `cnes/cnv/leiutibr.def` |
| **Cobertura** | Competências mensais desde Ago/2005 |
| **Recorte usado** | Dezembro de cada ano, quantidade existente |
| **Usado para** | **Alvo da Etapa 1** (`tem_uti`) |

"Leitos complementares" é a categoria do CNES que reúne UTI (adulto, pediátrica,
neonatal, de queimados, coronariana) **e** unidades intermediárias, unidade de
isolamento e suporte ventilatório COVID. Só as categorias de UTI contam para o
alvo — a lista exata está em `LEITOS_UTI`, em [`src/fontes.py`](../src/fontes.py).

## 6. DATASUS — CNES, Leitos de Internação

| | |
|---|---|
| **Acesso** | TabNet, `cnes/cnv/leiintbr.def` |
| **Recorte usado** | Dezembro de cada ano; quantidade existente e quantidade SUS |
| **Usado para** | Atributos de oferta hospitalar |

## 7. DATASUS — CNES, Estabelecimentos por Tipo

| | |
|---|---|
| **Acesso** | TabNet, `cnes/cnv/estabbr.def` |
| **Recorte usado** | Dezembro de cada ano, por tipo de estabelecimento |
| **Usado para** | Contagem de UBS/postos, hospitais, pronto atendimento, apoio à diagnose |

## 8. DATASUS — SIH/SUS, Morbidade Hospitalar por local de **residência**

| | |
|---|---|
| **Acesso** | TabNet, `sih/cnv/nrbr.def` |
| **Cobertura** | Competências mensais desde Jan/2008 |
| **Recorte usado** | 12 competências de cada ano; incremento "Internações" |
| **Usado para** | **Alvo da Etapa 2** (`taxa_icsap`) e taxa de internação |

O DATASUS publica duas versões da mesma base: por local de **internação** e por
local de **residência**. Usamos residência. Ver seção 4 do
[guia](00-guia-do-projeto.md#8-as-cinco-perguntas-que-a-banca-faz).

## 9. DATASUS — SIM (Mortalidade)

| | |
|---|---|
| **Acesso** | TabNet, `sim/cnv/obt10br.def` |
| **Recorte usado** | Óbitos por residência, faixa etária "Menor 1 ano" |
| **Usado para** | Taxa de mortalidade infantil (atributo de desfecho) |

## 10. DATASUS — SINASC (Nascidos Vivos)

| | |
|---|---|
| **Acesso** | TabNet, `sinasc/cnv/nvbr.def` |
| **Recorte usado** | Nascimentos por residência da mãe × consultas de pré-natal |
| **Usado para** | `pct_prenatal_7mais` — indicador de acesso à atenção primária |

Sete ou mais consultas de pré-natal é o parâmetro do Ministério da Saúde para
pré-natal adequado.

## 11. IBGE — API de Malhas Territoriais

| | |
|---|---|
| **Endpoint** | `https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR?formato=application/vnd.geo+json&intrarregiao=municipio&qualidade=minima` |
| **Documentação** | https://servicodados.ibge.gov.br/api/docs/malhas |
| **Formato** | GeoJSON, ~3,6 MB, sem autenticação |
| **Usado para** | Centroide de área de cada município → `dist_uti_km` |

Devolve os 5.570 polígonos municipais numa única requisição. O centroide é
calculado pela fórmula do shoelace (média ponderada pela área, não média dos
vértices), e a distância entre municípios é haversine — sobre a esfera, não no
plano, o que importa numa escala de 4.300 km de norte a sul.

**Limitação declarada:** o centroide de área não é onde a população mora, e a
distância em linha reta não é a distância percorrida. Na Amazônia os dois erros
se somam: o deslocamento é fluvial e leva dias, não a hora que 175 km em linha
reta sugerem. A medida serve para comparar ordens de grandeza (30 km contra 400
km), não para estimar tempo de viagem. Ver `src/geografia.py`.

## 12. Portaria SAS/MS nº 221, de 17/04/2008

| | |
|---|---|
| **Órgão** | Ministério da Saúde — Secretaria de Atenção à Saúde |
| **Conteúdo** | Lista Brasileira de Internações por Condições Sensíveis à Atenção Primária: 19 grupos de causas em CID-10 |
| **Original** | https://bvsms.saude.gov.br/bvs/saudelegis/sas/2008/prt0221_17_04_2008.html |
| **Cópia usada** | Nota Técnica da SES/SC que reproduz a lista integral: https://www.cosemssc.org.br/wp-content/uploads/2022/02/5.pdf |
| **No repositório** | `data/raw/icsap_lista_brasileira.csv` |

O portal BVS/MS estava instável em 10/09/2026 (conexão recusada). A lista foi
transcrita da Nota Técnica da Secretaria de Estado da Saúde de Santa Catarina,
que a reproduz declarando a portaria como fonte. **A portaria continua sendo a
fonte primária citada no relatório.**

---

## Sobre o TabNet: por que tabulação e não microdado

O DATASUS distribui os microdados do SIH em arquivos `.dbc` mensais por UF
(`ftp.datasus.gov.br`), que bibliotecas como **PySUS** e **microdatasus**
baixam. Esse caminho dá a CID exata de cada internação.

Optamos pelo TabNet porque:

1. **Volume.** O SIH registrou **13,2 milhões** de internações em 2023 (número
   conferido — ver `docs/04`, S0). Dez anos de todas as UFs passam de 30 GB. Para uma tabela agregada por município × ano, isso é
   trabalho computacional sem retorno analítico.
2. **Disponibilidade.** O FTP do DATASUS cai com frequência; o TabNet é a
   interface oficial e estável.
3. **Reprodutibilidade.** As respostas do TabNet cabem no repositório. 30 GB de
   `.dbc` não cabem.

**O preço** é que o TabNet não expõe a CID em 3/4 caracteres no recorte
Brasil × município — só a *Lista de Morbidade CID-10* (333 grupos). Por isso o
alvo da Etapa 2 é uma aproximação declarada da Lista Brasileira. Todo o custo
dessa escolha está quantificado em
[`03-icsap-operacionalizacao.md`](03-icsap-operacionalizacao.md).
