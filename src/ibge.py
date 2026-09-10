"""Acesso as APIs abertas do IBGE (Localidades e SIDRA).

Nenhuma das duas exige chave. As respostas sao guardadas em `data/raw/ibge/`
para congelar a base no repositorio.
"""

from __future__ import annotations

import gzip
import json
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

from fontes import DIR_RAW

DIR_IBGE = DIR_RAW / "ibge"
_UA = {"User-Agent": "Mozilla/5.0 (projeto academico CIN0144/UFPE)"}


def _baixar(url: str, destino: Path) -> bytes:
    """Baixa e congela a resposta em disco, comprimida.

    A resposta do SIDRA para 5.570 municipios x 6 variaveis passa de 10 MB em
    JSON e comprime ~20x -- por isso o `.gz`. Se o arquivo ja existe, nao vai
    a rede: a base do repositorio e reproduzivel offline.
    """
    destino = destino.with_suffix(destino.suffix + ".gz")
    if destino.exists():
        with gzip.open(destino, "rb") as arquivo:
            return arquivo.read()
    ultima: Exception | None = None
    for tentativa in range(4):
        try:
            with urllib.request.urlopen(
                urllib.request.Request(url, headers=_UA), timeout=300
            ) as resp:
                conteudo = resp.read()
            if conteudo[:2] == b"\x1f\x8b":
                conteudo = gzip.decompress(conteudo)
            destino.parent.mkdir(parents=True, exist_ok=True)
            with gzip.open(destino, "wb", compresslevel=9) as arquivo:
                arquivo.write(conteudo)
            return conteudo
        except Exception as exc:
            ultima = exc
            time.sleep(5 * (tentativa + 1))
    raise RuntimeError(f"falha ao baixar {url}: {ultima}")


def sem_acento(texto: str) -> str:
    return (
        unicodedata.normalize("NFKD", str(texto))
        .encode("ascii", "ignore")
        .decode("ascii")
        .upper()
        .strip()
    )


# --------------------------------------------------------------------------- #
# Localidades
# --------------------------------------------------------------------------- #
def municipios() -> pd.DataFrame:
    """Os 5.570 municipios + Fernando de Noronha, com UF, regiao e mesorregiao.

    O `cod_ibge6` (codigo sem o digito verificador) e a chave usada pelo DATASUS.
    """
    bruto = _baixar(
        "https://servicodados.ibge.gov.br/api/v1/localidades/municipios",
        DIR_IBGE / "localidades_municipios.json",
    )
    dados = json.loads(bruto)
    linhas = []
    for item in dados:
        micro = item["microrregiao"] or {}
        meso = micro.get("mesorregiao", {}) if micro else {}
        uf = (meso.get("UF") or {}) if meso else {}
        if not uf:  # Fernando de Noronha vem sem microrregiao em algumas versoes
            imediata = item.get("regiao-imediata") or {}
            intermediaria = imediata.get("regiao-intermediaria") or {}
            uf = intermediaria.get("UF") or {}
        regiao = uf.get("regiao") or {}
        linhas.append(
            {
                "cod_ibge7": item["id"],
                "cod_ibge6": int(str(item["id"])[:6]),
                "municipio": item["nome"],
                "municipio_norm": sem_acento(item["nome"]),
                "uf": uf.get("sigla"),
                "uf_nome": uf.get("nome"),
                "regiao": regiao.get("nome"),
                "mesorregiao": meso.get("nome"),
                "microrregiao": micro.get("nome"),
            }
        )
    return pd.DataFrame(linhas).sort_values("cod_ibge7").reset_index(drop=True)


# --------------------------------------------------------------------------- #
# SIDRA
# --------------------------------------------------------------------------- #
def sidra(tabela: int, variaveis: str, periodos: str, nivel: str = "n6/all") -> pd.DataFrame:
    """Consulta a API do SIDRA e devolve o resultado ja em formato longo.

    Ex.: `sidra(5938, "37,513,517,525,543", "2014-2023")`.
    """
    url = f"https://apisidra.ibge.gov.br/values/t/{tabela}/{nivel}/v/{variaveis}/p/{periodos}"
    apelido = f"sidra_{tabela}_{variaveis.replace(',', '-')}_{periodos}.json"
    bruto = _baixar(url, DIR_IBGE / apelido)
    registros = json.loads(bruto.decode("utf-8"))
    if len(registros) < 2:
        raise RuntimeError(f"SIDRA devolveu tabela vazia: {url}")
    corpo = pd.DataFrame(registros[1:])
    saida = pd.DataFrame(
        {
            "cod_ibge7": corpo["D1C"].astype(int),
            "variavel_cod": corpo["D2C"].astype(str),
            "variavel": corpo["D2N"].astype(str),
            "ano": corpo["D3C"].astype(int),
            "valor": pd.to_numeric(corpo["V"], errors="coerce"),
            "unidade": corpo["MN"].astype(str),
        }
    )
    return saida


def pib_municipal(ano_inicial: int, ano_final: int) -> pd.DataFrame:
    """PIB e valor adicionado bruto por setor, tabela SIDRA 5938 (em mil reais).

    A consulta e quebrada ano a ano de proposito: 5.570 municipios x 5 variaveis
    x 10 anos estoura o limite de celulas por requisicao do SIDRA (HTTP 400).
    """
    longo = pd.concat(
        [sidra(5938, "37,498,513,517,6575,525", str(ano)) for ano in range(ano_inicial, ano_final + 1)],
        ignore_index=True,
    )
    # ATENCAO: os codigos nao seguem a intuicao. 525 e administracao publica
    # (nao servicos) e 6575 e que e servicos exclusive administracao publica.
    # Conferido em https://servicodados.ibge.gov.br/api/v3/agregados/5938/metadados
    rotulos = {
        "37": "pib_mil_reais",
        "498": "vab_total",
        "513": "vab_agropecuaria",
        "517": "vab_industria",
        "6575": "vab_servicos",
        "525": "vab_adm_publica",
    }
    largo = (
        longo.assign(coluna=longo["variavel_cod"].map(rotulos))
        .pivot_table(index=["cod_ibge7", "ano"], columns="coluna", values="valor")
        .reset_index()
    )
    largo.columns.name = None
    return largo


def area_territorial() -> pd.DataFrame:
    """Area total em km2 (tabela SIDRA 1301, Censo 2010)."""
    longo = sidra(1301, "615", "all")
    return (
        longo.groupby("cod_ibge7", as_index=False)["valor"]
        .max()
        .rename(columns={"valor": "area_km2"})
    )
