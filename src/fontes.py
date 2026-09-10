"""Registro unico das fontes de dados do projeto.

Toda URL, todo `.def` do TabNet e todo codigo de tabela do SIDRA usado no
projeto esta declarado aqui. Nada de fonte espalhada pelo notebook.

Todas as fontes sao publicas, governamentais e foram acessadas em 10/09/2026.
Nenhuma exige cadastro, chave de API ou aceite de termos.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DIR_RAW = RAIZ / "data" / "raw"
DIR_INTERIM = RAIZ / "data" / "interim"
DIR_PROCESSED = RAIZ / "data" / "processed"

# Janela do painel. 2014 e o primeiro ano com CNES estavel apos a
# reformulacao do cadastro; 2023 e o ultimo ano com PIB municipal (IBGE) e
# estimativa populacional TCU publicados e com SIH fechado.
ANO_INICIAL = 2014
ANO_FINAL = 2023
ANOS = list(range(ANO_INICIAL, ANO_FINAL + 1))

# Rotulos do TabNet vem em latin-1; os valores dos campos tambem.
LINHA_MUNICIPIO = "Munic\xedpio"
COLUNA_INATIVA = "--N\xe3o-Ativa--"


@dataclass(frozen=True)
class Fonte:
    apelido: str
    orgao: str
    nome: str
    url_consulta: str
    url_documentacao: str
    licenca: str
    observacao: str = ""


FONTES: dict[str, Fonte] = {
    "ibge_localidades": Fonte(
        apelido="ibge_localidades",
        orgao="IBGE",
        nome="API de Localidades - malha politico-administrativa",
        url_consulta="https://servicodados.ibge.gov.br/api/v1/localidades/municipios",
        url_documentacao="https://servicodados.ibge.gov.br/api/docs/localidades",
        licenca="Dados abertos, uso livre com citacao da fonte (Lei 12.527/2011).",
        observacao="Devolve 5.571 registros: os 5.570 municipios + Fernando de Noronha (PE), "
        "que e distrito estadual e nao municipio.",
    ),
    "sidra_pib": Fonte(
        apelido="sidra_pib",
        orgao="IBGE",
        nome="Produto Interno Bruto dos Municipios - tabela SIDRA 5938",
        url_consulta="https://apisidra.ibge.gov.br/values/t/5938/n6/all/v/37,498,513,517,6575,525/p/{ano}",
        url_documentacao="https://sidra.ibge.gov.br/tabela/5938",
        licenca="Dados abertos IBGE.",
        observacao="Serie 2002-2023. Variaveis: 37 PIB a precos correntes; 498 VAB total; "
        "513 VAB agropecuaria; 517 VAB industria; 6575 VAB servicos (exclusive adm publica); "
        "525 VAB administracao/defesa/educacao e saude publicas. ATENCAO: em 2022 e 2023 o IBGE "
        "publicou apenas o PIB total -- a abertura setorial ainda nao saiu. E uma lacuna real da "
        "fonte, tratada como ausencia estruturada na EDA.",
    ),
    "sidra_area": Fonte(
        apelido="sidra_area",
        orgao="IBGE",
        nome="Area territorial - tabela SIDRA 1301 (Censo 2010)",
        url_consulta="https://apisidra.ibge.gov.br/values/t/1301/n6/all/v/615/p/all",
        url_documentacao="https://sidra.ibge.gov.br/tabela/1301",
        licenca="Dados abertos IBGE.",
        observacao="Area em km2. Fixa no periodo -- usada apenas para calcular densidade.",
    ),
    "ibge_malhas": Fonte(
        apelido="ibge_malhas",
        orgao="IBGE",
        nome="API de Malhas Territoriais - poligonos municipais",
        url_consulta="https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR"
        "?formato=application/vnd.geo+json&intrarregiao=municipio&qualidade=minima",
        url_documentacao="https://servicodados.ibge.gov.br/api/docs/malhas",
        licenca="Dados abertos IBGE.",
        observacao="Os 5.570 poligonos municipais em ~3,6 MB (qualidade minima). Usada para "
        "calcular o centroide de area de cada municipio e, dele, a distancia ate o servico "
        "mais proximo. Ver src/geografia.py.",
    ),
    "populacao_tcu": Fonte(
        apelido="populacao_tcu",
        orgao="IBGE / DATASUS",
        nome="Populacao Residente - Estimativas para o TCU",
        url_consulta="http://tabnet.datasus.gov.br/cgi/tabcgi.exe?ibge/cnv/poptbr.def",
        url_documentacao="https://datasus.saude.gov.br/populacao-residente/",
        licenca="Dados abertos do Ministerio da Saude / IBGE.",
        observacao="Estimativas anuais por municipio, 1992-2023. E o denominador oficial usado "
        "pelo Ministerio da Saude no calculo de taxas -- por isso preferido as estimativas "
        "do SIDRA, que mudam de metodologia depois do Censo 2022.",
    ),
    "cnes_leitos_uti": Fonte(
        apelido="cnes_leitos_uti",
        orgao="Ministerio da Saude / DATASUS",
        nome="CNES - Recursos Fisicos - Hospitalar - Leitos Complementares",
        url_consulta="http://tabnet.datasus.gov.br/cgi/tabcgi.exe?cnes/cnv/leiutibr.def",
        url_documentacao="https://cnes.datasus.gov.br/",
        licenca="Dados abertos do Ministerio da Saude.",
        observacao="Competencias mensais de Ago/2005 em diante. 'Leitos complementares' agrupa "
        "UTI (adulto, pediatrica, neonatal, queimados, coronariana) e unidades intermediarias.",
    ),
    "cnes_leitos_internacao": Fonte(
        apelido="cnes_leitos_internacao",
        orgao="Ministerio da Saude / DATASUS",
        nome="CNES - Recursos Fisicos - Hospitalar - Leitos de internacao",
        url_consulta="http://tabnet.datasus.gov.br/cgi/tabcgi.exe?cnes/cnv/leiintbr.def",
        url_documentacao="https://cnes.datasus.gov.br/",
        licenca="Dados abertos do Ministerio da Saude.",
        observacao="Leitos por especialidade (cirurgicos, clinicos, obstetricos, pediatricos, "
        "outras, hospital/dia), com recorte SUS / nao-SUS.",
    ),
    "cnes_estabelecimentos": Fonte(
        apelido="cnes_estabelecimentos",
        orgao="Ministerio da Saude / DATASUS",
        nome="CNES - Estabelecimentos por Tipo",
        url_consulta="http://tabnet.datasus.gov.br/cgi/tabcgi.exe?cnes/cnv/estabbr.def",
        url_documentacao="https://cnes.datasus.gov.br/",
        licenca="Dados abertos do Ministerio da Saude.",
        observacao="Contagem de estabelecimentos por tipo de unidade (posto, centro de saude, "
        "hospital geral, UPA, etc.).",
    ),
    "sih_morbidade_residencia": Fonte(
        apelido="sih_morbidade_residencia",
        orgao="Ministerio da Saude / DATASUS",
        nome="SIH/SUS - Morbidade Hospitalar por local de RESIDENCIA",
        url_consulta="http://tabnet.datasus.gov.br/cgi/tabcgi.exe?sih/cnv/nrbr.def",
        url_documentacao="https://datasus.saude.gov.br/informacoes-de-saude-tabnet/",
        licenca="Dados abertos do Ministerio da Saude.",
        observacao="Internacoes financiadas pelo SUS, competencias mensais desde Jan/2008. "
        "A versao 'por local de residencia' e obrigatoria aqui: ver docs/02-decisoes.md.",
    ),
    "sim_mortalidade": Fonte(
        apelido="sim_mortalidade",
        orgao="Ministerio da Saude / DATASUS",
        nome="SIM - Sistema de Informacoes sobre Mortalidade",
        url_consulta="http://tabnet.datasus.gov.br/cgi/tabcgi.exe?sim/cnv/obt10br.def",
        url_documentacao="https://datasus.saude.gov.br/informacoes-de-saude-tabnet/",
        licenca="Dados abertos do Ministerio da Saude.",
        observacao="Obitos por residencia, com faixa etaria -- usado para mortalidade infantil.",
    ),
    "sinasc_nascidos": Fonte(
        apelido="sinasc_nascidos",
        orgao="Ministerio da Saude / DATASUS",
        nome="SINASC - Sistema de Informacoes sobre Nascidos Vivos",
        url_consulta="http://tabnet.datasus.gov.br/cgi/tabcgi.exe?sinasc/cnv/nvbr.def",
        url_documentacao="https://datasus.saude.gov.br/informacoes-de-saude-tabnet/",
        licenca="Dados abertos do Ministerio da Saude.",
        observacao="Nascidos vivos por residencia da mae, com numero de consultas de pre-natal.",
    ),
    "portaria_icsap": Fonte(
        apelido="portaria_icsap",
        orgao="Ministerio da Saude - Secretaria de Atencao a Saude",
        nome="Portaria SAS/MS n. 221, de 17/04/2008 - Lista Brasileira de ICSAP",
        url_consulta="https://bvsms.saude.gov.br/bvs/saudelegis/sas/2008/prt0221_17_04_2008.html",
        url_documentacao="https://www.cosemssc.org.br/wp-content/uploads/2022/02/5.pdf",
        licenca="Ato normativo publico.",
        observacao="19 grupos de causas em CID-10. A lista integral usada no projeto esta em "
        "data/raw/icsap_lista_brasileira.csv, transcrita da Nota Tecnica da SES/SC que "
        "reproduz a portaria (o portal BVS/MS estava instavel em 10/09/2026).",
    ),
}

# --- `.def` do TabNet -------------------------------------------------------
DEF_LEITOS_UTI = "cnes/cnv/leiutibr.def"
DEF_LEITOS_INTERNACAO = "cnes/cnv/leiintbr.def"
DEF_ESTABELECIMENTOS = "cnes/cnv/estabbr.def"
DEF_SIH_RESIDENCIA = "sih/cnv/nrbr.def"
DEF_SIM = "sim/cnv/obt10br.def"
DEF_SINASC = "sinasc/cnv/nvbr.def"
DEF_POPULACAO = "ibge/cnv/poptbr.def"

# --- Codigos de leitos complementares que contam como UTI --------------------
# Fonte: opcoes da dimensao "Leitos complementares" em cnes/cnv/leiutibr.def.
# Ficam de fora as unidades intermediarias, a unidade de isolamento e o
# suporte ventilatorio COVID: nenhuma delas e leito de terapia intensiva.
LEITOS_UTI = {
    "UTI adulto I", "UTI adulto II", "UTI adulto III", "UTI adulto",
    "UTI adulto II COVID-19",
    "UTI pediatrica I", "UTI pediatrica II", "UTI pediatrica III", "UTI infantil",
    "UTI pediatrica II COVID-19",
    "UTI neonatal I", "UTI neonatal II", "UTI neonatal III", "UTI neonatal",
    "UTI de Queimados",
    "UTI coronariana tipo II -UCO tipo II",
    "UTI coronariana tipo III - UCO tipo III",
}
