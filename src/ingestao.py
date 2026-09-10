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


def saneamento() -> pd.DataFrame:
    """M6 -- saneamento por municipio (Censo 2022)."""
    print("[IBGE/SIDRA] saneamento - Censo 2022 (tabelas 6803, 6805, 6892)")
    return _salvar(ibge.saneamento_censo2022(), "saneamento")


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


def equipes_saude() -> pd.DataFrame:
    """M2 -- equipes de atencao primaria por municipio (proxy de cobertura ESF).

    CONCEITO: **cobertura da Estrategia Saude da Familia**. E o indicador direto
    de atencao primaria, e portanto a variavel que *deveria* explicar a
    `taxa_icsap` melhor que qualquer outra: se a ESF cobre o territorio, a
    pneumonia nao vira internacao.

    POR QUE por aqui e nao pelo e-Gestor AB: o e-Gestor publica a cobertura
    oficial, mas a interface e JSF sem API -- exigiria automacao de navegador.
    O CNES registra as **equipes cadastradas**, e a cobertura oficial e derivada
    delas pela mesma formula que aplicamos em build_dataset.py.

    INTERPRETACAO: contamos as equipes em dezembro de cada ano, separando ESF
    (incluindo ribeirinha e fluvial) de EAB (modelo alternativo de atencao
    basica). Municipio sem equipe nao aparece na tabulacao -- vira zero.
    """
    print("[CNES] equipes de saude - dezembro de cada ano")
    form = tn.descrever(F.DEF_EQUIPES)
    anuais = []
    for ano in F.ANOS:
        arquivo = [v for v, rotulo in form.arquivos if rotulo.strip() == f"Dez/{ano}"]
        if not arquivo:
            print(f"  ! sem competencia Dez/{ano}")
            continue
        bruto = tn.consultar(
            F.DEF_EQUIPES,
            linha=F.LINHA_MUNICIPIO,
            coluna="Tipo_da_Equipe",
            arquivos=arquivo,
            formulario=form,
        )
        tabela = _com_codigo(bruto, bruto.columns[0])

        # O rotulo da coluna vem como "01 ESF - EQUIPE DE SAUDE DA FAMILIA":
        # o codigo de dois digitos no inicio e a chave confiavel, nao o texto.
        def somar(codigos: set[str]) -> pd.Series:
            escolhidas = [
                c for c in tabela.columns
                if c != "cod_ibge6" and _sem_acento(c)[:2] in codigos
            ]
            if not escolhidas:
                return pd.Series(0.0, index=tabela.index)
            return tabela[escolhidas].sum(axis=1, min_count=1).fillna(0)

        codigos_esf, codigos_eab = F.codigos_equipes(ano)
        anuais.append(
            pd.DataFrame(
                {
                    "cod_ibge6": tabela["cod_ibge6"],
                    "ano": ano,
                    "equipes_esf": somar(codigos_esf),
                    "equipes_ab_outras": somar(codigos_eab),
                }
            )
        )
        print(f"  {ano}: {len(tabela)} municipios com equipe cadastrada")
    return _salvar(pd.concat(anuais, ignore_index=True), "equipes_saude")


def equipamentos() -> pd.DataFrame:
    """M5 -- equipamentos por grupo (oferta de diagnostico e terapia)."""
    print("[CNES] equipamentos por grupo - dezembro de cada ano")
    form = tn.descrever(F.DEF_EQUIPAMENTOS)
    anuais = []
    for ano in F.ANOS:
        arquivo = [v for v, rotulo in form.arquivos if rotulo.strip() == f"Dez/{ano}"]
        if not arquivo:
            continue
        bruto = tn.consultar(
            F.DEF_EQUIPAMENTOS,
            linha=F.LINHA_MUNICIPIO,
            coluna="Grupo_de_Equipamentos",
            incremento="Equipamentos_em_Uso",
            arquivos=arquivo,
            formulario=form,
        )
        tabela = _com_codigo(bruto, bruto.columns[0])
        rotulos = {c: _sem_acento(c).upper() for c in tabela.columns if c != "cod_ibge6"}

        def somar(*chaves: str) -> pd.Series:
            escolhidas = [c for c, r in rotulos.items() if any(k in r for k in chaves)]
            if not escolhidas:
                return pd.Series(0.0, index=tabela.index)
            return tabela[escolhidas].sum(axis=1, min_count=1).fillna(0)

        anuais.append(
            pd.DataFrame(
                {
                    "cod_ibge6": tabela["cod_ibge6"],
                    "ano": ano,
                    "equip_total": somar("TOTAL"),
                    "equip_imagem": somar("IMAGEM"),
                    "equip_manut_vida": somar("MANUTENCAO DA VIDA"),
                }
            )
        )
        print(f"  {ano}: {len(tabela)} municipios")
    return _salvar(pd.concat(anuais, ignore_index=True), "equipamentos")


def internacoes_por_faixa() -> pd.DataFrame:
    """M4 -- ICSAP separada por faixa etaria.

    CONCEITO: a literatura de ICSAP calcula o indicador separadamente para
    **menores de 5 anos** e **idosos**, porque as condicoes sensiveis sao
    diferentes em cada extremo -- gastroenterite e pneumonia na infancia,
    diabetes e insuficiencia cardiaca na velhice. A taxa infantil e a mais
    sensivel a qualidade da atencao primaria: crianca com pneumonia que interna
    e, quase sempre, crianca que nao foi vista a tempo.

    POR QUE cabe no orcamento: usando `Faixa_Etaria_1` como COLUNA (e nao como
    filtro), uma unica consulta devolve municipio x faixa. Sao as mesmas 2
    consultas por ano que ja fazemos, com uma dimensao a mais.
    """
    print("[SIH] internacoes por faixa etaria (total e ICSAP)")
    form = tn.descrever(F.DEF_SIH_RESIDENCIA)
    codigos_icsap = icsap.codigos_lista_morb()
    dimensao_lista = next(d for d in form.filtros if _sem_acento(d).startswith("SLista_Morb"))
    coluna_faixa = next(v for v, _ in form.coluna if _sem_acento(v) == "Faixa_Etaria_1")

    # A faixa vem como rotulo de coluna: "Menor 1 ano", "1 a 4 anos", ...
    INFANTIL = ("MENOR 1 ANO", "1 A 4 ANOS")
    IDOSO = ("60 A 69 ANOS", "70 A 79 ANOS", "80 ANOS E MAIS")

    anuais = []
    for ano in F.ANOS:
        arquivos = form.arquivos_do_ano(ano)
        if not arquivos:
            continue
        # ATENCAO: as duas consultas NAO devolvem o mesmo conjunto de
        # municipios. A filtrada por ICSAP so traz quem teve internacao
        # sensivel naquela faixa etaria, e sao sempre menos linhas. Por isso a
        # juncao e por `cod_ibge6` -- assumir arrays alinhados quebra.
        pedacos = []
        for filtro, sufixo in [(None, "total"), ({dimensao_lista: codigos_icsap}, "icsap")]:
            bruto = tn.consultar(
                F.DEF_SIH_RESIDENCIA,
                linha=F.LINHA_MUNICIPIO,
                coluna=coluna_faixa,
                incremento="Interna\xe7\xf5es",
                arquivos=arquivos,
                filtros=filtro,
                formulario=form,
            )
            tabela = _com_codigo(bruto, bruto.columns[0])
            rotulos = {c: _sem_acento(c).upper().strip() for c in tabela.columns if c != "cod_ibge6"}

            def somar(chaves: tuple[str, ...]) -> pd.Series:
                escolhidas = [c for c, r in rotulos.items() if r in chaves]
                if not escolhidas:
                    return pd.Series(0.0, index=tabela.index)
                return tabela[escolhidas].sum(axis=1, min_count=1).fillna(0)

            pedacos.append(
                pd.DataFrame(
                    {
                        "cod_ibge6": tabela["cod_ibge6"].values,
                        f"intern_menor5_{sufixo}": somar(INFANTIL).values,
                        f"intern_idoso_{sufixo}": somar(IDOSO).values,
                    }
                )
            )

        juntos = pedacos[0].merge(pedacos[1], on="cod_ibge6", how="outer").assign(ano=ano)
        # Municipio sem ICSAP na faixa: ausencia estrutural, vira zero.
        anuais.append(juntos.fillna(0))
        print(f"  {ano}: {len(juntos)} municipios")
    return _salvar(pd.concat(anuais, ignore_index=True), "internacoes_faixa")


ETAPAS = {
    "municipios": municipios,
    "capitais": capitais,
    "area": area,
    "pib": pib,
    "saneamento": saneamento,
    "populacao": populacao,
    "leitos_uti": leitos_uti,
    "leitos_internacao": leitos_internacao,
    "estabelecimentos": estabelecimentos,
    "internacoes": internacoes,
    "obitos_infantis": obitos_infantis,
    "nascidos_vivos": nascidos_vivos,
    "equipes_saude": equipes_saude,
    "equipamentos": equipamentos,
    "internacoes_por_faixa": internacoes_por_faixa,
}


if __name__ == "__main__":
    pedidas = sys.argv[1:] or list(ETAPAS)
    for nome in pedidas:
        if nome not in ETAPAS:
            raise SystemExit(f"etapa desconhecida: {nome}. Opcoes: {', '.join(ETAPAS)}")
        ETAPAS[nome]()
    print("\nIngestao concluida.")
