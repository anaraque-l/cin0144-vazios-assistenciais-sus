"""Geografia municipal: centroides e distancia ate o servico mais proximo.

POR QUE ESTE MODULO EXISTE
--------------------------
Sem ele, a base inteira e feita de *proxies de tamanho*: populacao, PIB,
numero de estabelecimentos, numero de internacoes -- todos correlacionados
entre si acima de 0,9 e todos correlacionados ~0,50 com `tem_uti`. O modelo so
tem uma informacao para dar: "este municipio e grande".

Isso torna a Etapa 1 quase trivial (0% de UTI abaixo de 5 mil habitantes, 100%
acima de 500 mil) e, pior, torna o **erro** do modelo ininterpretavel: um falso
positivo pode ser tanto um municipio genuinamente desassistido no meio do
Amazonas quanto um suburbio a 15 km de uma capital. Sao situacoes opostas.

A distancia ate o leito de UTI mais proximo resolve isso, e o dado mostra por
que: sua correlacao de Spearman com a populacao e **0,06**. E a primeira
variavel do projeto que nao e tamanho disfarcado.

CONCEITO: **centroide de area**. O IBGE nao publica a coordenada da sede
municipal numa API aberta, mas publica a *malha* (o poligono de cada
municipio). O centroide do poligono e calculado pela formula do shoelace --
media das coordenadas ponderada pela area, nao media simples dos vertices
(que enviesaria para onde a fronteira tem mais pontos).

LIMITACAO, declarada: o centroide da area nao e onde a populacao mora. Em
municipio grande e vazio da Amazonia, a sede fica na margem do rio e o
centroide no meio da mata. A distancia calculada e, nesses casos, uma
aproximacao -- que erra para mais ou para menos conforme o caso. Como estamos
comparando ordens de grandeza (30 km contra 400 km), a aproximacao serve.

CONCEITO: **distancia haversine**. Distancia sobre a esfera, nao em linha reta
no plano. Em escala continental a diferenca importa: o Brasil tem 4.300 km de
norte a sul, e projetar lat/lon como se fosse plano cartesiano erra dezenas de
quilometros. Tambem nao e distancia rodoviaria -- ver a limitacao acima.
"""

from __future__ import annotations

import gzip
import json
import math
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

from fontes import DIR_RAW

URL_MALHA = (
    "https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR"
    "?formato=application/vnd.geo+json&intrarregiao=municipio&qualidade=minima"
)
ARQUIVO_MALHA = DIR_RAW / "ibge" / "malha_municipios.geojson.gz"
RAIO_TERRA_KM = 6371.0


def _baixar_malha() -> dict:
    """Baixa (uma vez) a malha municipal do Brasil inteiro.

    Sao 5.570 poligonos em ~3,6 MB na qualidade minima -- resolucao mais que
    suficiente para centroide. A resposta fica congelada em data/raw como todas
    as outras fontes.
    """
    if ARQUIVO_MALHA.exists():
        with gzip.open(ARQUIVO_MALHA, "rb") as arquivo:
            return json.loads(arquivo.read())

    requisicao = urllib.request.Request(URL_MALHA, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(requisicao, timeout=300) as resposta:
        bruto = resposta.read()
    if bruto[:2] == b"\x1f\x8b":
        bruto = gzip.decompress(bruto)

    ARQUIVO_MALHA.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(ARQUIVO_MALHA, "wb", compresslevel=9) as arquivo:
        arquivo.write(bruto)
    return json.loads(bruto)


def _centroide_shoelace(geometria: dict) -> tuple[float, float] | None:
    """Centroide de area do maior anel exterior do poligono.

    Municipio costeiro ou com ilha vem como MultiPolygon; usamos o poligono de
    maior area, que e o continente -- nao a ilhota.
    """
    poligonos = (
        geometria["coordinates"]
        if geometria["type"] == "MultiPolygon"
        else [geometria["coordinates"]]
    )
    melhor, maior_area = None, -1.0
    for poligono in poligonos:
        anel = poligono[0]  # anel exterior; buracos internos sao ignorados
        area = soma_x = soma_y = 0.0
        for i in range(len(anel) - 1):
            x0, y0 = anel[i][:2]
            x1, y1 = anel[i + 1][:2]
            cruzado = x0 * y1 - x1 * y0
            area += cruzado
            soma_x += (x0 + x1) * cruzado
            soma_y += (y0 + y1) * cruzado
        if abs(area) < 1e-12:
            continue
        area *= 0.5
        if abs(area) > maior_area:
            maior_area = abs(area)
            melhor = (soma_x / (6 * area), soma_y / (6 * area))
    return melhor


def centroides() -> pd.DataFrame:
    """`cod_ibge7`, `lon`, `lat` para os 5.570 municipios."""
    malha = _baixar_malha()
    linhas = []
    for feicao in malha["features"]:
        centro = _centroide_shoelace(feicao["geometry"])
        if centro is None:
            continue
        linhas.append(
            {
                "cod_ibge7": int(feicao["properties"]["codarea"]),
                "lon": centro[0],
                "lat": centro[1],
            }
        )
    return pd.DataFrame(linhas)


def _para_cartesiano(lat_graus: np.ndarray, lon_graus: np.ndarray) -> np.ndarray:
    """Lat/lon -> vetor unitario 3D.

    Truque de desempenho: com os pontos na esfera unitaria, o cosseno do angulo
    entre dois deles e o **produto escalar**. Isso permite calcular a distancia
    de 5.570 municipios contra centenas de alvos com uma unica multiplicacao de
    matrizes, em vez de um laco duplo em Python.
    """
    lat = np.radians(lat_graus)
    lon = np.radians(lon_graus)
    return np.c_[np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)]


def distancia_ao_mais_proximo(
    lat: np.ndarray,
    lon: np.ndarray,
    possui_servico: np.ndarray,
    incluir_a_si_mesmo: bool = True,
) -> np.ndarray:
    """Distancia em km de cada municipio ate o mais proximo que tem o servico.

    `possui_servico` e um vetor booleano do mesmo tamanho. Municipio que tem o
    servico recebe distancia 0 (quando `incluir_a_si_mesmo`), porque para o
    morador dali a distancia e de fato zero.

    Devolve `NaN` se nenhum municipio tem o servico naquele ano.
    """
    pontos = _para_cartesiano(lat, lon)
    alvos = pontos[possui_servico]
    if len(alvos) == 0:
        return np.full(len(lat), np.nan)

    distancias = np.full(len(lat), np.nan)
    for i in range(len(lat)):
        if incluir_a_si_mesmo and possui_servico[i]:
            distancias[i] = 0.0
            continue
        cossenos = np.clip(alvos @ pontos[i], -1.0, 1.0)
        if not incluir_a_si_mesmo and possui_servico[i]:
            # exclui o proprio municipio: o cosseno 1,0 mais proximo de si
            cossenos = np.sort(cossenos)[:-1]
            if len(cossenos) == 0:
                continue
        distancias[i] = RAIO_TERRA_KM * math.acos(float(cossenos.max()))
    return distancias


def painel_de_distancias(base: pd.DataFrame) -> pd.DataFrame:
    """Calcula, para cada municipio x ano, a distancia ate a UTI mais proxima.

    POR QUE ANO A ANO e nao uma vez so: leitos de UTI abrem e fecham. Em
    2020-2021 o Brasil ganhou 30 mil leitos COVID, e municipios que estavam a
    200 km de uma UTI passaram a estar a 40 km. Congelar a distancia num ano so
    apagaria esse movimento -- que e justamente um dos achados do painel.
    """
    coords = centroides()
    saida = []
    for ano, fatia in base.groupby("ano"):
        fatia = fatia.merge(coords, on="cod_ibge7", how="left")
        valido = fatia["lat"].notna().values
        lat = fatia["lat"].fillna(0).values
        lon = fatia["lon"].fillna(0).values

        distancia_uti = distancia_ao_mais_proximo(lat, lon, fatia["tem_uti"].values == 1)
        distancia_hospital = distancia_ao_mais_proximo(
            lat, lon, fatia["leitos_internacao"].values > 0
        )
        # Distancia ate a UTI mais proxima IGNORANDO o proprio municipio.
        # Serve para responder "se a UTI daqui fechar, para onde vai o paciente?"
        distancia_externa = distancia_ao_mais_proximo(
            lat, lon, fatia["tem_uti"].values == 1, incluir_a_si_mesmo=False
        )

        saida.append(
            pd.DataFrame(
                {
                    "cod_ibge7": fatia["cod_ibge7"].values,
                    "ano": ano,
                    "lat": np.where(valido, lat, np.nan),
                    "lon": np.where(valido, lon, np.nan),
                    "dist_uti_km": np.where(valido, distancia_uti, np.nan),
                    "dist_hospital_km": np.where(valido, distancia_hospital, np.nan),
                    "dist_uti_externa_km": np.where(valido, distancia_externa, np.nan),
                }
            )
        )
    return pd.concat(saida, ignore_index=True)
