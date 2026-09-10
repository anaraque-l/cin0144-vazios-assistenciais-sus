"""Cliente para o TabNet do DATASUS.

O TabNet (http://tabnet.datasus.gov.br/) e o tabulador oficial do DATASUS. Ele
expoe, para cada base (CNES, SIH, SIM, SINASC, populacao IBGE), um arquivo `.def`
que descreve as dimensoes disponiveis. A interface e um formulario HTML antigo
(TabNet Win32 3.3) que responde POST com uma tabela HTML.

Este modulo faz tres coisas:

1. le o formulario de um `.def` e devolve as opcoes validas (`descrever`);
2. monta e envia a consulta (`consultar`), preenchendo TODAS as dimensoes de
   filtro com `TODAS_AS_CATEGORIAS__` -- se alguma faltar, o TabNet responde
   "Tabela de conversao nao encontrada";
3. guarda o HTML bruto de cada consulta em `data/raw/tabnet/`, para que a base
   fique congelada no repositorio e a analise seja reproduzivel sem rede.

Detalhes que custaram tempo e ficam registrados aqui:

* o site responde em latin-1, e os NOMES dos campos do formulario tambem contem
  acento em latin-1 (`SMunic\xedpio`). O corpo do POST precisa ser codificado em
  latin-1, nao em utf-8;
* as tags `<OPTION>` nao sao fechadas, entao o parser trabalha por regex sobre o
  HTML bruto em vez de usar um parser estrito;
* numeros vem no formato brasileiro (`1.234` = mil duzentos e trinta e quatro) e
  celulas vazias vem como `-`.
"""

from __future__ import annotations

import gzip
import hashlib
import html as _html
import json
import re
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

BASE_URL = "http://tabnet.datasus.gov.br/cgi/tabcgi.exe?"
CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "raw" / "tabnet"
TODAS = "TODAS_AS_CATEGORIAS__"

_UA = {"User-Agent": "Mozilla/5.0 (projeto academico CIN0144/UFPE)"}


class TabNetErro(RuntimeError):
    pass


# --------------------------------------------------------------------------- #
# HTTP
# --------------------------------------------------------------------------- #
def _http(url: str, corpo: bytes | None = None, timeout: int = 600) -> str:
    headers = dict(_UA)
    if corpo is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(url, data=corpo, headers=headers)
    ultima: Exception | None = None
    for tentativa in range(4):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("latin-1")
        except Exception as exc:  # rede do DATASUS cai com alguma frequencia
            ultima = exc
            time.sleep(5 * (tentativa + 1))
    raise TabNetErro(f"falha ao acessar {url}: {ultima}")


# --------------------------------------------------------------------------- #
# Leitura do formulario
# --------------------------------------------------------------------------- #
def _opcoes(html_bruto: str, campo: str) -> list[tuple[str, str]]:
    bloco = re.search(
        r'<SELECT[^>]*NAME="' + re.escape(campo) + r'"[^>]*>(.*?)</SELECT>',
        html_bruto,
        re.S | re.I,
    )
    if not bloco:
        return []
    return [
        (valor, _html.unescape(rotulo).strip())
        for valor, rotulo in re.findall(
            r'<OPTION VALUE="([^"]*)"[^>]*>([^<\r\n]*)', bloco.group(1)
        )
    ]


@dataclass
class Formulario:
    """Metadados de um `.def` do TabNet."""

    definicao: str
    titulo: str
    linha: list[tuple[str, str]]
    coluna: list[tuple[str, str]]
    incremento: list[tuple[str, str]]
    arquivos: list[tuple[str, str]]
    filtros: dict[str, list[tuple[str, str]]] = field(default_factory=dict)

    def arquivos_do_ano(self, ano: int, prefixo: str | None = None) -> list[str]:
        """Devolve os arquivos mensais/anuais cuja competencia cai em `ano`.

        O rotulo vem como `Jul/2026` (mensal) ou `2023` (anual).
        """
        alvo = str(ano)
        achados = []
        for valor, rotulo in self.arquivos:
            rotulo = rotulo.strip()
            if rotulo == alvo or rotulo.endswith("/" + alvo):
                if prefixo is None or valor.startswith(prefixo):
                    achados.append(valor)
        return achados


def descrever(definicao: str) -> Formulario:
    bruto = _http(BASE_URL + definicao)
    titulo = re.search(r'<H2 class="Nivel0">(.*?)</H2>', bruto, re.S | re.I)
    if not titulo:
        raise TabNetErro(f"{definicao}: DEF inexistente ou erro do TabNet")
    nomes_s = [
        nome
        for nome in re.findall(r'<SELECT[^>]*NAME="([^"]+)"', bruto, re.I)
        if nome.startswith("S") and not nome.lower().startswith("slistahidden")
    ]
    return Formulario(
        definicao=definicao,
        titulo=re.sub(r"\s+", " ", _html.unescape(titulo.group(1))).strip(),
        linha=_opcoes(bruto, "Linha"),
        coluna=_opcoes(bruto, "Coluna"),
        incremento=_opcoes(bruto, "Incremento"),
        arquivos=_opcoes(bruto, "Arquivos"),
        filtros={nome: _opcoes(bruto, nome) for nome in nomes_s},
    )


# --------------------------------------------------------------------------- #
# Consulta
# --------------------------------------------------------------------------- #
def _chave_cache(definicao: str, pares: list[tuple[str, str]]) -> Path:
    """Nome do arquivo de cache, derivado do CONTEUDO da consulta.

    Consulta diferente => digest diferente => cache novo. Por isso mudar o
    periodo em `fontes.py` nao exige limpar `data/raw/`.

    O HTML e guardado comprimido: as respostas do TabNet a nivel municipal tem
    centenas de KB cada e comprimem cerca de 20x, o que mantem a base congelada
    dentro de um tamanho razoavel para um repositorio Git.
    """
    assinatura = json.dumps([definicao, pares], ensure_ascii=False, sort_keys=False)
    digest = hashlib.sha1(assinatura.encode("utf-8")).hexdigest()[:16]
    apelido = definicao.replace("/", "_").replace(".def", "")
    return CACHE_DIR / f"{apelido}__{digest}.html.gz"


def consultar_html(
    definicao: str,
    linha: str,
    coluna: str = "--N\xe3o-Ativa--",
    incremento: str | None = None,
    arquivos: list[str] | None = None,
    filtros: dict[str, list[str]] | None = None,
    formulario: Formulario | None = None,
    usar_cache: bool = True,
) -> str:
    """Executa uma tabulacao e devolve o HTML bruto (com cache em disco)."""
    form = formulario or descrever(definicao)
    if incremento is None:
        incremento = form.incremento[0][0]
    if not arquivos:
        raise TabNetErro("e preciso informar ao menos um arquivo de competencia")

    filtros = filtros or {}
    pares: list[tuple[str, str]] = [
        ("Linha", linha),
        ("Coluna", coluna),
        ("Incremento", incremento),
    ]
    pares += [("Arquivos", arquivo) for arquivo in arquivos]
    for dimensao in form.filtros:
        escolhidos = filtros.get(dimensao)
        if escolhidos:
            pares += [(dimensao, str(codigo)) for codigo in escolhidos]
        else:
            pares.append((dimensao, TODAS))
    pares += [("formato", "table"), ("mostre", "Mostra")]

    destino = _chave_cache(definicao, pares)
    if usar_cache and destino.exists():
        with gzip.open(destino, "rt", encoding="latin-1") as arquivo:
            return arquivo.read()

    corpo = "&".join(
        urllib.parse.quote(chave, encoding="latin-1", safe="")
        + "="
        + urllib.parse.quote(str(valor), encoding="latin-1", safe="")
        for chave, valor in pares
    ).encode("latin-1")
    bruto = _http(BASE_URL + definicao, corpo)

    if "Tabela de conversao nao encontrada" in bruto:
        raise TabNetErro(f"{definicao}: combinacao Linha/Coluna invalida ({linha} x {coluna})")
    if "<TABLE" not in bruto.upper():
        texto = re.sub(r"\s+", " ", re.sub("<[^>]+>", " ", bruto))
        raise TabNetErro(f"{definicao}: resposta sem tabela -> {texto[:200]}")

    destino.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(destino, "wt", encoding="latin-1", compresslevel=9) as arquivo:
        arquivo.write(bruto)
    return bruto


# --------------------------------------------------------------------------- #
# Parsing da tabela
# --------------------------------------------------------------------------- #
def _numero(texto: str) -> float | None:
    texto = texto.replace("\xa0", " ").strip()
    if texto in {"", "-", "..."}:
        return None
    texto = texto.replace(".", "").replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return None


_RE_CELULA = re.compile(r"<T([HD])\b([^>]*)>(.*?)(?=<T[HD]\b|</?TR\b|</?T(?:BODY|HEAD|FOOT|ABLE)\b|$)", re.S | re.I)


def _celulas(fragmento: str) -> list[tuple[str, str, str]]:
    """Devolve (tipo, atributos, texto) de cada celula.

    O TabNet nao fecha `<TH>` nem `<TD>`, entao o corte e feito pela proxima
    abertura de celula ou fim de linha -- e nao por uma tag de fechamento.
    """
    saida = []
    for tipo, atributos, conteudo in _RE_CELULA.findall(fragmento):
        texto = _html.unescape(re.sub("<[^>]+>", " ", conteudo))
        saida.append((tipo.upper(), atributos, re.sub(r"\s+", " ", texto.replace("\xa0", " ")).strip()))
    return saida


def parse_tabela(bruto: str) -> pd.DataFrame:
    """Converte o HTML de resposta do TabNet num DataFrame.

    A primeira coluna e a dimensao de `Linha` (vem como `<codigo> <nome>`); as
    demais sao as categorias de `Coluna`. As linhas de titulo, de rodape e a
    linha `Total` sao descartadas.
    """
    tabela = re.search(r"<TABLE[^>]*>(.*?)</TABLE>", bruto, re.S | re.I)
    if not tabela:
        raise TabNetErro("resposta sem <TABLE>")
    corpo = re.sub(r"<TFOOT.*?</TFOOT>", "", tabela.group(1), flags=re.S | re.I)
    fragmentos = re.split(r"<TR\b[^>]*>", corpo, flags=re.I)[1:]

    cabecalho: list[str] | None = None
    dados: list[list[str]] = []
    for fragmento in fragmentos:
        celulas = _celulas(fragmento)
        if not celulas:
            continue
        if any("COLSPAN" in atributos.upper() for _, atributos, _ in celulas):
            continue  # faixa de titulo/rodape
        tipos = {tipo for tipo, _, _ in celulas}
        valores = [texto for _, _, texto in celulas]
        if tipos == {"H"}:
            if cabecalho is None or len(valores) > len(cabecalho):
                cabecalho = valores
        elif "D" in tipos:
            dados.append(valores)
    if cabecalho is None or not dados:
        raise TabNetErro("nao consegui identificar cabecalho/corpo da tabela")

    largura = max(len(linha) for linha in dados)
    if len(cabecalho) < largura:
        cabecalho = cabecalho + [f"col_{i}" for i in range(len(cabecalho), largura)]
    cabecalho = cabecalho[:largura]

    df = pd.DataFrame(
        [linha + [""] * (largura - len(linha)) for linha in dados], columns=cabecalho
    )
    df = df[df.iloc[:, 0].str.strip().str.lower() != "total"]
    for coluna in df.columns[1:]:
        df[coluna] = df[coluna].map(_numero)
    return df.reset_index(drop=True)


_RE_COD_NOME = re.compile(r"^\s*(\d+)\s+(.*)$")


def separar_codigo_nome(serie: pd.Series) -> pd.DataFrame:
    """Quebra `330490 SAO PAULO` em (codigo, nome)."""
    codigos, nomes = [], []
    for valor in serie.astype(str):
        achado = _RE_COD_NOME.match(valor)
        if achado:
            codigos.append(achado.group(1))
            nomes.append(achado.group(2).strip())
        else:
            codigos.append(None)
            nomes.append(valor.strip())
    return pd.DataFrame({"codigo": codigos, "nome": nomes})


def consultar(
    definicao: str,
    linha: str,
    **kwargs,
) -> pd.DataFrame:
    """`consultar_html` + `parse_tabela`."""
    return parse_tabela(consultar_html(definicao, linha, **kwargs))
