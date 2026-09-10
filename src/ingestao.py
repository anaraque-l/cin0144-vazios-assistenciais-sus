"""Ingestao das fontes -- uma funcao por fonte, saida em `data/interim/`.

Cada funcao devolve uma tabela longa `cod_ibge6 x ano x medida`. O HTML bruto de
cada consulta ao TabNet fica em `data/raw/tabnet/`, entao rodar de novo nao
depende de rede e o resultado e reproduzivel byte a byte.

Uso:

    python src/ingestao.py            # roda tudo
    python src/ingestao.py populacao  # roda so uma etapa
"""

from __future__ import annotations

import sys
import unicodedata
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fontes as F
import ibge
import icsap
import tabnet as tn


def _sem_acento(texto: str) -> str:
    return (
        unicodedata.normalize("NFKD", str(texto))
        .encode("ascii", "ignore")
        .decode("ascii")
        .strip()
    )


def _com_codigo(df: pd.DataFrame, coluna_linha: str) -> pd.DataFrame:
    """Troca a coluna de `Linha` do TabNet por `cod_ibge6`."""
    partes = tn.separar_codigo_nome(df[coluna_linha])
    saida = df.drop(columns=[coluna_linha]).copy()
    saida.insert(0, "cod_ibge6", pd.to_numeric(partes["codigo"], errors="coerce"))
    return saida.dropna(subset=["cod_ibge6"]).astype({"cod_ibge6": int})


def _salvar(df: pd.DataFrame, nome: str) -> pd.DataFrame:
    F.DIR_INTERIM.mkdir(parents=True, exist_ok=True)
    destino = F.DIR_INTERIM / f"{nome}.csv"
    df.to_csv(destino, index=False, encoding="utf-8")
    print(f"  -> {destino.name}: {df.shape[0]} linhas x {df.shape[1]} colunas")
    return df


# --------------------------------------------------------------------------- #
# IBGE
# --------------------------------------------------------------------------- #
def municipios() -> pd.DataFrame:
    print("[IBGE] malha municipal")
    return _salvar(ibge.municipios(), "municipios")


def pib() -> pd.DataFrame:
    print("[IBGE/SIDRA] PIB municipal (tabela 5938)")
    return _salvar(ibge.pib_municipal(F.ANO_INICIAL, F.ANO_FINAL), "pib")


def area() -> pd.DataFrame:
    print("[IBGE/SIDRA] area territorial (tabela 1301)")
    return _salvar(ibge.area_territorial(), "area")


# --------------------------------------------------------------------------- #
# TabNet
# --------------------------------------------------------------------------- #
def populacao() -> pd.DataFrame:
    print("[DATASUS] populacao residente - estimativas TCU")
    form = tn.descrever(F.DEF_POPULACAO)
    arquivos = [a for ano in F.ANOS for a in form.arquivos_do_ano(ano)]
    bruto = tn.consultar(
        F.DEF_POPULACAO,
        linha=F.LINHA_MUNICIPIO,
        coluna="Ano",
        arquivos=arquivos,
        formulario=form,
    )
    tabela = _com_codigo(bruto, bruto.columns[0])
    longo = tabela.drop(columns=[c for c in tabela.columns if c.strip() == "Total"]).melt(
        id_vars="cod_ibge6", var_name="ano", value_name="populacao"
    )
    longo["ano"] = pd.to_numeric(longo["ano"], errors="coerce")
    longo = longo.dropna(subset=["ano"]).astype({"ano": int})
    return _salvar(longo, "populacao")


def capitais() -> pd.DataFrame:
    """Lista das capitais, extraida da propria dimensao `Capital` do TabNet."""
    print("[DATASUS] capitais")
    form = tn.descrever(F.DEF_ESTABELECIMENTOS)
    bruto = tn.consultar(
        F.DEF_ESTABELECIMENTOS,
        linha="Capital",
        arquivos=form.arquivos_do_ano(F.ANO_FINAL)[:1],
        formulario=form,
    )
    tabela = _com_codigo(bruto, bruto.columns[0])
    tabela = tabela[["cod_ibge6"]].assign(capital=1)
    return _salvar(tabela, "capitais")


def leitos_uti() -> pd.DataFrame:
    print("[CNES] leitos complementares (UTI) - dezembro de cada ano")
    form = tn.descrever(F.DEF_LEITOS_UTI)
    anuais = []
    for ano in F.ANOS:
        arquivo = [v for v, rotulo in form.arquivos if rotulo.strip() == f"Dez/{ano}"]
        if not arquivo:
            print(f"  ! sem competencia Dez/{ano}")
            continue
        bruto = tn.consultar(
            F.DEF_LEITOS_UTI,
            linha=F.LINHA_MUNICIPIO,
            coluna="Leitos_complementares",
            incremento="Quantidade_existente",
            arquivos=arquivo,
            formulario=form,
        )
        tabela = _com_codigo(bruto, bruto.columns[0])
        colunas_uti = [
            c for c in tabela.columns
            if c != "cod_ibge6" and _sem_acento(c) in {_sem_acento(x) for x in F.LEITOS_UTI}
        ]
        total = [c for c in tabela.columns if c.strip() == "Total"]
        anuais.append(
            pd.DataFrame(
                {
                    "cod_ibge6": tabela["cod_ibge6"],
                    "ano": ano,
                    "leitos_uti": tabela[colunas_uti].sum(axis=1, min_count=1).fillna(0),
                    "leitos_complementares": tabela[total].sum(axis=1, min_count=1).fillna(0)
                    if total
                    else pd.NA,
                }
            )
        )
        print(f"  {ano}: {len(tabela)} municipios com leito complementar")
    return _salvar(pd.concat(anuais, ignore_index=True), "leitos_uti")


def leitos_internacao() -> pd.DataFrame:
    print("[CNES] leitos de internacao - dezembro de cada ano")
    form = tn.descrever(F.DEF_LEITOS_INTERNACAO)
    anuais = []
    for ano in F.ANOS:
        arquivo = [v for v, rotulo in form.arquivos if rotulo.strip() == f"Dez/{ano}"]
        if not arquivo:
            continue
        pedacos = {}
        for incremento, nome in [
            ("Quantidade_existente", "leitos_internacao"),
            ("Quantidade_SUS", "leitos_internacao_sus"),
        ]:
            bruto = tn.consultar(
                F.DEF_LEITOS_INTERNACAO,
                linha=F.LINHA_MUNICIPIO,
                incremento=incremento,
                arquivos=arquivo,
                formulario=form,
            )
            tabela = _com_codigo(bruto, bruto.columns[0])
            valor = tabela.columns[1]
            pedacos[nome] = tabela.set_index("cod_ibge6")[valor]
        juntos = pd.DataFrame(pedacos).reset_index().assign(ano=ano)
        anuais.append(juntos)
        print(f"  {ano}: {len(juntos)} municipios com leito de internacao")
    return _salvar(pd.concat(anuais, ignore_index=True), "leitos_internacao")


def estabelecimentos() -> pd.DataFrame:
    print("[CNES] estabelecimentos por tipo - dezembro de cada ano")
    form = tn.descrever(F.DEF_ESTABELECIMENTOS)
    anuais = []
    for ano in F.ANOS:
        arquivo = [v for v, rotulo in form.arquivos if rotulo.strip() == f"Dez/{ano}"]
        if not arquivo:
            continue
        bruto = tn.consultar(
            F.DEF_ESTABELECIMENTOS,
            linha=F.LINHA_MUNICIPIO,
            coluna="Tipo_de_Estabelecimento",
            arquivos=arquivo,
            formulario=form,
        )
        tabela = _com_codigo(bruto, bruto.columns[0])
        # A correspondencia e por rotulo EXATO, nao por substring: "PRONTO
        # SOCORRO DE HOSPITAL GERAL (ANTIGO)" contem "HOSPITAL GERAL" e seria
        # contado duas vezes num casamento por substring.
        colunas = {_sem_acento(c).upper(): c for c in tabela.columns if c != "cod_ibge6"}

        def somar(*rotulos: str) -> pd.Series:
            escolhidas = [colunas[r] for r in rotulos if r in colunas]
            if not escolhidas:
                return pd.Series(0.0, index=tabela.index)
            return tabela[escolhidas].sum(axis=1, min_count=1).fillna(0)

        anuais.append(
            pd.DataFrame(
                {
                    "cod_ibge6": tabela["cod_ibge6"],
                    "ano": ano,
                    "estab_total": somar("TOTAL"),
                    # Atencao primaria: posto, UBS e Saude da Familia.
                    "estab_atencao_basica": somar(
                        "POSTO DE SAUDE",
                        "CENTRO DE SAUDE/UNIDADE BASICA",
                        "UNIDADE DE SAUDE DA FAMILIA",
                    ),
                    "estab_hospital": somar("HOSPITAL GERAL", "HOSPITAL ESPECIALIZADO"),
                    "estab_urgencia": somar(
                        "PRONTO SOCORRO GERAL",
                        "PRONTO SOCORRO ESPECIALIZADO",
                        "PRONTO ATENDIMENTO",
                        "UNIDADE MISTA",
                    ),
                    "estab_apoio_diagnose": somar(
                        "UNIDADE DE APOIO DIAGNOSE E TERAPIA (SADT ISOLADO)"
                    ),
                    "estab_caps": somar("CENTRO DE ATENCAO PSICOSSOCIAL"),
                }
            )
        )
        print(f"  {ano}: {len(tabela)} municipios")
    return _salvar(pd.concat(anuais, ignore_index=True), "estabelecimentos")


def internacoes() -> pd.DataFrame:
    """Internacoes SUS por local de RESIDENCIA: total e ICSAP (aproximada)."""
    print("[SIH] internacoes por local de residencia (total e ICSAP)")
    form = tn.descrever(F.DEF_SIH_RESIDENCIA)
    codigos_icsap = icsap.codigos_lista_morb()
    dimensao_lista = next(d for d in form.filtros if _sem_acento(d).startswith("SLista_Morb"))
    anuais = []
    for ano in F.ANOS:
        arquivos = form.arquivos_do_ano(ano)
        if len(arquivos) != 12:
            print(f"  ! {ano}: {len(arquivos)} competencias mensais (esperado 12)")
        if not arquivos:
            continue
        total = _com_codigo(
            tn.consultar(
                F.DEF_SIH_RESIDENCIA,
                linha=F.LINHA_MUNICIPIO,
                incremento="Interna\xe7\xf5es",
                arquivos=arquivos,
                formulario=form,
            ),
            "Munic\xedpio",
        )
        total = total.rename(columns={total.columns[1]: "internacoes_total"})
        sensiveis = _com_codigo(
            tn.consultar(
                F.DEF_SIH_RESIDENCIA,
                linha=F.LINHA_MUNICIPIO,
                incremento="Interna\xe7\xf5es",
                arquivos=arquivos,
                filtros={dimensao_lista: codigos_icsap},
                formulario=form,
            ),
            "Munic\xedpio",
        )
        sensiveis = sensiveis.rename(columns={sensiveis.columns[1]: "internacoes_icsap"})
        juntos = total.merge(sensiveis, on="cod_ibge6", how="outer").assign(ano=ano)
        anuais.append(juntos)
        print(f"  {ano}: {len(juntos)} municipios de residencia")
    return _salvar(pd.concat(anuais, ignore_index=True), "internacoes")


def obitos_infantis() -> pd.DataFrame:
    print("[SIM] obitos de menores de 1 ano por residencia")
    form = tn.descrever(F.DEF_SIM)
    dimensao = next(d for d in form.filtros if _sem_acento(d) == "SFaixa_Etaria")
    menor_1 = [v for v, rotulo in form.filtros[dimensao] if "Menor 1" in rotulo]
    anuais = []
    for ano in F.ANOS:
        arquivos = form.arquivos_do_ano(ano)
        if not arquivos:
            continue
        bruto = tn.consultar(
            F.DEF_SIM,
            linha=F.LINHA_MUNICIPIO,
            incremento="\xd3bitos_p/Resid\xeanc",
            arquivos=arquivos,
            filtros={dimensao: menor_1},
            formulario=form,
        )
        tabela = _com_codigo(bruto, bruto.columns[0])
        tabela = tabela.rename(columns={tabela.columns[1]: "obitos_menor1"}).assign(ano=ano)
        anuais.append(tabela[["cod_ibge6", "ano", "obitos_menor1"]])
        print(f"  {ano}: {len(tabela)} municipios")
    return _salvar(pd.concat(anuais, ignore_index=True), "obitos_infantis")


def nascidos_vivos() -> pd.DataFrame:
    print("[SINASC] nascidos vivos por residencia da mae x consultas de pre-natal")
    form = tn.descrever(F.DEF_SINASC)
    anuais = []
    for ano in F.ANOS:
        arquivos = form.arquivos_do_ano(ano)
        if not arquivos:
            continue
        bruto = tn.consultar(
            F.DEF_SINASC,
            linha=F.LINHA_MUNICIPIO,
            coluna="Consult_pr\xe9-natal",
            incremento="Nascim_p/resid.m\xe3e",
            arquivos=arquivos,
            formulario=form,
        )
        tabela = _com_codigo(bruto, bruto.columns[0])
        rotulos = {c: _sem_acento(c).lower() for c in tabela.columns if c != "cod_ibge6"}

        def coluna(*chaves: str) -> pd.Series:
            escolhidas = [c for c, r in rotulos.items() if any(k in r for k in chaves)]
            return tabela[escolhidas].sum(axis=1, min_count=1).fillna(0) if escolhidas else 0.0

        anuais.append(
            pd.DataFrame(
                {
                    "cod_ibge6": tabela["cod_ibge6"],
                    "ano": ano,
                    "nascidos_vivos": coluna("total"),
                    "nasc_prenatal_7mais": coluna("7 ou mais"),
                    "nasc_prenatal_nenhuma": coluna("nenhuma"),
                    "nasc_prenatal_ignorado": coluna("ignorado"),
                }
            )
        )
        print(f"  {ano}: {len(tabela)} municipios")
    return _salvar(pd.concat(anuais, ignore_index=True), "nascidos_vivos")


ETAPAS = {
    "municipios": municipios,
    "capitais": capitais,
    "area": area,
    "pib": pib,
    "populacao": populacao,
    "leitos_uti": leitos_uti,
    "leitos_internacao": leitos_internacao,
    "estabelecimentos": estabelecimentos,
    "internacoes": internacoes,
    "obitos_infantis": obitos_infantis,
    "nascidos_vivos": nascidos_vivos,
}


if __name__ == "__main__":
    pedidas = sys.argv[1:] or list(ETAPAS)
    for nome in pedidas:
        if nome not in ETAPAS:
            raise SystemExit(f"etapa desconhecida: {nome}. Opcoes: {', '.join(ETAPAS)}")
        ETAPAS[nome]()
    print("\nIngestao concluida.")
