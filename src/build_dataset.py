"""Monta a tabela analitica `municipio x ano` a partir de `data/interim/`.

CONCEITO: **unidade de analise**. Uma linha = um municipio num ano. Isso se
chama *painel* (ou dados longitudinais). A alternativa seria um *corte
transversal* (um ano so, 5.570 linhas). Escolhemos painel por tres razoes:

1. o enunciado pede mais de 1.000 instancias -- o painel entrega 55.700;
2. `ano` vira atributo de graca, e com ele da para ver o choque da pandemia;
3. o fenomeno que queremos medir (vazio assistencial) e persistente: ver o mesmo
   municipio dez vezes e informacao, nao ruido.

O preco esta documentado em docs/04-melhorias-tradeoffs-sensibilidades.md: as
linhas **nao sao independentes**, e isso muda como a validacao cruzada tem de
ser feita mais adiante (agrupada por municipio, nao aleatoria).

REGRA DE OURO DESTE ARQUIVO: aqui **nao se corrige nada**. Nada de imputar,
remover outlier, padronizar ou balancear. A Entrega 1 e exploratoria: o objetivo
e *enxergar* os problemas da base, nao escondê-los. As unicas transformacoes
permitidas sao as que constroem a unidade de analise (juncao, agregacao) e as
taxas que sao a propria definicao do alvo.

Uso:  python src/build_dataset.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fontes as F
import geografia


def _ler(nome: str) -> pd.DataFrame:
    caminho = F.DIR_INTERIM / f"{nome}.csv"
    if not caminho.exists():
        raise SystemExit(f"falta {caminho}. Rode antes: python src/ingestao.py {nome}")
    return pd.read_csv(caminho)


def montar() -> pd.DataFrame:
    # ----------------------------------------------------------------- #
    # 1. Esqueleto: TODO municipio x TODO ano
    # ----------------------------------------------------------------- #
    # CONCEITO: **left join a partir do universo**. Comecamos da lista completa
    # do IBGE e trazemos o resto por left join. Se comecassemos pelo CNES,
    # perderiamos exatamente os municipios sem servico -- que sao o objeto do
    # estudo. Esse e o erro classico de "sobrevivencia" em base administrativa.
    municipios = _ler("municipios")
    # Fernando de Noronha (2605459) e distrito estadual de PE, nao municipio.
    # Aparece na malha do IBGE e nao no DATASUS -- manter geraria uma linha com
    # todos os indicadores de saude faltantes por construcao. Ver docs/02, D9.
    municipios = municipios[municipios["cod_ibge7"] != 2605459]
    esqueleto = municipios.merge(pd.DataFrame({"ano": F.ANOS}), how="cross")

    capitais = _ler("capitais")
    base = esqueleto.merge(capitais, on="cod_ibge6", how="left")
    base["capital"] = base["capital"].fillna(0).astype(int)

    # ----------------------------------------------------------------- #
    # 2. Denominadores: populacao e area
    # ----------------------------------------------------------------- #
    base = base.merge(_ler("populacao"), on=["cod_ibge6", "ano"], how="left")
    base = base.merge(_ler("area"), on="cod_ibge7", how="left")

    # ----------------------------------------------------------------- #
    # 3. Economia (IBGE/SIDRA, chave de 7 digitos)
    # ----------------------------------------------------------------- #
    base = base.merge(_ler("pib"), on=["cod_ibge7", "ano"], how="left")

    # ----------------------------------------------------------------- #
    # 4. Oferta de servico (CNES, chave de 6 digitos)
    # ----------------------------------------------------------------- #
    # INTERPRETACAO: o TabNet so devolve linha para municipio que TEM o recurso.
    # Ausencia no CNES nao e dado faltante -- e zero de verdade ("nao existe
    # leito de UTI aqui"). Por isso estas colunas levam fillna(0), e as do bloco
    # 5 tambem. Todas as demais mantem NaN, que sera diagnosticado na EDA.
    for nome, colunas in [
        ("leitos_uti", ["leitos_uti", "leitos_complementares"]),
        ("leitos_internacao", ["leitos_internacao", "leitos_internacao_sus"]),
        ("estabelecimentos", [
            "estab_total", "estab_atencao_basica", "estab_hospital",
            "estab_urgencia", "estab_apoio_diagnose", "estab_caps",
        ]),
    ]:
        base = base.merge(_ler(nome), on=["cod_ibge6", "ano"], how="left")
        base[colunas] = base[colunas].fillna(0)

    # ----------------------------------------------------------------- #
    # 5. Uso e desfecho (SIH, SIM, SINASC -- todos por RESIDENCIA)
    # ----------------------------------------------------------------- #
    for nome, colunas in [
        ("internacoes", ["internacoes_total", "internacoes_icsap"]),
        ("obitos_infantis", ["obitos_menor1"]),
        ("nascidos_vivos", [
            "nascidos_vivos", "nasc_prenatal_7mais",
            "nasc_prenatal_nenhuma", "nasc_prenatal_ignorado",
        ]),
    ]:
        base = base.merge(_ler(nome), on=["cod_ibge6", "ano"], how="left")
        base[colunas] = base[colunas].fillna(0)

    return base


def derivar(base: pd.DataFrame) -> pd.DataFrame:
    df = base.copy()

    # ----------------------------------------------------------------- #
    # ALVO 1 (classificacao): o municipio tem leito de UTI?
    # ----------------------------------------------------------------- #
    # CONCEITO: **alvo binario desbalanceado**. Escolhemos UTI, e nao "tem
    # estabelecimento de saude", porque praticamente 100% dos municipios tem
    # algum estabelecimento -- sem variacao nao ha o que prever. UTI fica na
    # faixa de ~10-15% de positivos, que e desbalanceamento de verdade.
    # INTERPRETACAO: um FALSO POSITIVO do modelo (municipio que pelo perfil
    # "deveria" ter UTI e nao tem) e justamente o vazio assistencial que
    # queremos mapear. O produto final nao e a acuracia -- e essa lista.
    df["tem_uti"] = (df["leitos_uti"] > 0).astype(int)

    # ----------------------------------------------------------------- #
    # ALVO 2 (regressao): proporcao de internacoes sensiveis a atencao primaria
    # ----------------------------------------------------------------- #
    # CONCEITO: **indicador de desempenho, nao de estrutura**. ICSAP mede se a
    # porta de entrada do SUS funciona: pneumonia, diabetes descompensado e
    # infeccao urinaria nao deveriam virar internacao se a atencao basica
    # resolvesse. Taxa alta => a atencao primaria nao esta segurando.
    # ATENCAO: e uma APROXIMACAO da Lista Brasileira -- ver src/icsap.py.
    df["taxa_icsap"] = np.where(
        df["internacoes_total"] > 0,
        df["internacoes_icsap"] / df["internacoes_total"],
        np.nan,
    )
    # Versao populacional (por 10 mil habitantes). A proporcional depende do
    # denominador "quem foi internado"; a populacional nao. Guardamos as duas
    # para poder discutir a diferenca na EDA.
    df["icsap_por_10mil"] = np.where(
        df["populacao"] > 0, 10_000 * df["internacoes_icsap"] / df["populacao"], np.nan
    )

    # ----------------------------------------------------------------- #
    # Atributos derivados
    # ----------------------------------------------------------------- #
    # CONCEITO: **normalizacao por exposicao**. Contagem bruta em municipio
    # grande e sempre maior -- o modelo aprenderia "populacao" e nada mais.
    # Transformar em "por mil habitantes" separa TAMANHO de INTENSIDADE.
    df["densidade_demografica"] = df["populacao"] / df["area_km2"]
    df["pib_per_capita"] = 1_000 * df["pib_mil_reais"] / df["populacao"]

    # CONCEITO: **composicao setorial**. O que importa nao e quanto o municipio
    # produz, e sim *de que* ele vive. Um municipio de 20 mil habitantes que vive
    # de administracao publica tem outra estrutura de servico de saude que um que
    # vive de industria.
    # ATENCAO: em 2022 e 2023 o IBGE ainda nao publicou a abertura setorial --
    # so o PIB total. Isso gera ~20% de ausentes nestas quatro colunas, e a
    # ausencia e ESTRUTURADA (por ano), nao aleatoria. Nao imputar pela media.
    for setor in ["agropecuaria", "industria", "servicos", "adm_publica"]:
        df[f"pct_vab_{setor}"] = df[f"vab_{setor}"] / df["vab_total"]

    df["leitos_por_mil_hab"] = 1_000 * df["leitos_internacao"] / df["populacao"]
    df["leitos_sus_por_mil_hab"] = 1_000 * df["leitos_internacao_sus"] / df["populacao"]
    df["estab_ab_por_10mil"] = 10_000 * df["estab_atencao_basica"] / df["populacao"]
    df["tx_internacao_por_mil"] = 1_000 * df["internacoes_total"] / df["populacao"]

    # CONCEITO: **indicador de acesso a atencao primaria pelo pre-natal**.
    # Sete ou mais consultas e o parametro do Ministerio da Saude para pre-natal
    # adequado. E um bom termometro de APS *independente* do SIH -- por isso
    # entra como atributo, nao como alvo.
    df["pct_prenatal_7mais"] = np.where(
        df["nascidos_vivos"] > 0, df["nasc_prenatal_7mais"] / df["nascidos_vivos"], np.nan
    )
    df["tx_mort_infantil"] = np.where(
        df["nascidos_vivos"] > 0, 1_000 * df["obitos_menor1"] / df["nascidos_vivos"], np.nan
    )

    # CONCEITO: **variavel ordinal**. Porte populacional tem ordem natural, ao
    # contrario de `regiao`, que e nominal. Faz diferenca no pre-processamento:
    # ordinal aceita codificacao por inteiro, nominal exige one-hot.
    faixas = [0, 5_000, 10_000, 20_000, 50_000, 100_000, 500_000, np.inf]
    rotulos = ["ate 5k", "5k-10k", "10k-20k", "20k-50k", "50k-100k", "100k-500k", "500k+"]
    df["porte_populacional"] = pd.cut(df["populacao"], bins=faixas, labels=rotulos, right=False)

    # A pandemia nao e ruido: e um choque real que muda internacao e leito de
    # UTI ao mesmo tempo. Marcar permite tratar (ou excluir) esses anos depois.
    df["periodo_pandemia"] = df["ano"].isin([2020, 2021]).astype(int)

    # ----------------------------------------------------------------- #
    # Isolamento geografico
    # ----------------------------------------------------------------- #
    # CONCEITO: **atributo de vizinhanca**. Todos os outros atributos descrevem
    # o municipio olhando so para dentro dele. Este olha para fora: a que
    # distancia esta o servico mais proximo.
    # POR QUE: sem ele, um municipio sem UTI a 15 km de uma capital e um a 500
    # km de tudo sao IDENTICOS na base -- e sao situacoes opostas. O primeiro e
    # especializacao metropolitana normal; o segundo e vazio assistencial.
    # INTERPRETACAO: a correlacao de Spearman desta coluna com a populacao e
    # ~0,06. E a unica variavel do projeto que NAO e tamanho disfarcado.
    print("  calculando distancias geograficas (pode levar ~1 min)...")
    distancias = geografia.painel_de_distancias(df)
    df = df.merge(distancias, on=["cod_ibge7", "ano"], how="left")

    # CONCEITO: **indice composto**. Isolado sozinho nao basta (um municipio
    # isolado com 800 habitantes nao "deveria" ter UTI); populoso sozinho
    # tambem nao. O vazio assistencial e a INTERSECAO: gente suficiente para
    # justificar o servico E longe demais para alcanca-lo.
    # Os cortes (20 mil hab., 100 km) sao os parametros de referencia usados na
    # discussao de regionalizacao do SUS -- e estao aqui explicitos justamente
    # para poderem ser questionados.
    df["vazio_assistencial"] = (
        (df["tem_uti"] == 0) & (df["populacao"] >= 20_000) & (df["dist_uti_km"] >= 100)
    ).astype(int)

    return df


ORDEM_COLUNAS = [
    # identificadores -- NAO entram no modelo
    "cod_ibge7", "cod_ibge6", "municipio", "uf", "regiao", "mesorregiao", "microrregiao", "ano",
    # contexto
    "capital", "populacao", "area_km2", "densidade_demografica", "porte_populacional",
    "periodo_pandemia",
    # economia
    "pib_mil_reais", "pib_per_capita", "vab_total",
    "pct_vab_agropecuaria", "pct_vab_industria", "pct_vab_servicos", "pct_vab_adm_publica",
    # oferta
    "estab_total", "estab_atencao_basica", "estab_hospital", "estab_urgencia",
    "estab_apoio_diagnose", "estab_caps", "estab_ab_por_10mil",
    "leitos_internacao", "leitos_internacao_sus", "leitos_por_mil_hab", "leitos_sus_por_mil_hab",
    "leitos_uti", "leitos_complementares",
    # isolamento geografico
    "lat", "lon", "dist_uti_km", "dist_uti_externa_km", "dist_hospital_km",
    # uso e desfecho
    "internacoes_total", "internacoes_icsap", "tx_internacao_por_mil",
    "nascidos_vivos", "nasc_prenatal_7mais", "nasc_prenatal_nenhuma", "nasc_prenatal_ignorado",
    "pct_prenatal_7mais", "obitos_menor1", "tx_mort_infantil",
    # alvos
    "tem_uti", "taxa_icsap", "icsap_por_10mil", "vazio_assistencial",
]


if __name__ == "__main__":
    tabela = derivar(montar())
    faltando = [c for c in ORDEM_COLUNAS if c not in tabela.columns]
    if faltando:
        raise SystemExit(f"colunas ausentes: {faltando}")
    tabela = tabela[ORDEM_COLUNAS]

    F.DIR_PROCESSED.mkdir(parents=True, exist_ok=True)
    destino = F.DIR_PROCESSED / "municipio_ano.csv"
    tabela.to_csv(destino, index=False, encoding="utf-8")

    print(f"tabela analitica: {tabela.shape[0]} linhas x {tabela.shape[1]} colunas")
    print(f"gravada em {destino}")
    print(f"anos: {tabela['ano'].min()}-{tabela['ano'].max()}")
    print(f"municipios: {tabela['cod_ibge7'].nunique()}")
    print(f"prevalencia de tem_uti: {tabela['tem_uti'].mean():.1%}")
    print(f"taxa_icsap media: {tabela['taxa_icsap'].mean():.1%}")
    print(f"distancia mediana ate UTI (quem nao tem): "
          f"{tabela.loc[tabela.tem_uti == 0, 'dist_uti_km'].median():.0f} km")
    print(f"municipios-ano em vazio assistencial: {tabela['vazio_assistencial'].sum():,} "
          f"({tabela['vazio_assistencial'].mean():.1%})")
