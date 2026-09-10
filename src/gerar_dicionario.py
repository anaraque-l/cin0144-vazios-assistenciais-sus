"""Gera `docs/05-dicionario-de-dados.md` a partir da tabela analitica.

O dicionario e gerado, e nao escrito a mao, para nao dessincronizar da base:
contagem de ausentes, minimo e maximo saem do CSV toda vez que este script
roda. So a descricao e o papel de cada coluna sao redigidos aqui.

Uso:  python src/gerar_dicionario.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fontes as F

# coluna -> (tipo semantico, unidade, fonte, papel, descricao)
CATALOGO: dict[str, tuple[str, str, str, str, str]] = {
    "cod_ibge7": ("identificador", "-", "IBGE Localidades", "chave", "Codigo do municipio com digito verificador."),
    "cod_ibge6": ("identificador", "-", "IBGE Localidades", "chave", "Codigo sem digito verificador -- e o que o DATASUS usa."),
    "municipio": ("identificador", "-", "IBGE Localidades", "rotulo", "Nome do municipio."),
    "uf": ("nominal", "-", "IBGE Localidades", "atributo", "Sigla da unidade da federacao (27 categorias)."),
    "regiao": ("nominal", "-", "IBGE Localidades", "atributo", "Grande regiao (5 categorias)."),
    "mesorregiao": ("nominal", "-", "IBGE Localidades", "atributo", "Mesorregiao IBGE (137 categorias) -- one-hot inviavel."),
    "microrregiao": ("nominal", "-", "IBGE Localidades", "atributo", "Microrregiao IBGE (558 categorias) -- one-hot inviavel."),
    "ano": ("temporal", "ano", "construido", "atributo", "Ano de referencia da observacao."),
    "capital": ("binario", "0/1", "DATASUS TabNet", "atributo", "1 se o municipio e capital estadual."),
    "populacao": ("discreto", "pessoas", "IBGE/TCU via DATASUS", "atributo", "Populacao residente estimada."),
    "area_km2": ("continuo", "km2", "IBGE SIDRA 1301", "atributo", "Area territorial (Censo 2010, fixa no periodo)."),
    "densidade_demografica": ("continuo", "hab/km2", "derivado", "atributo", "populacao / area_km2."),
    "porte_populacional": ("ordinal", "-", "derivado", "atributo", "Faixa de populacao em 7 niveis ordenados."),
    "periodo_pandemia": ("binario", "0/1", "derivado", "atributo", "1 para 2020 e 2021."),
    "pib_mil_reais": ("continuo", "R$ mil", "IBGE SIDRA 5938", "atributo", "PIB municipal a precos correntes."),
    "pib_per_capita": ("continuo", "R$/hab", "derivado", "atributo", "1000 * pib_mil_reais / populacao."),
    "vab_total": ("continuo", "R$ mil", "IBGE SIDRA 5938", "atributo", "Valor adicionado bruto total. Redundante com o PIB (rho = 1,00)."),
    "pct_vab_agropecuaria": ("continuo", "proporcao", "derivado", "atributo", "Participacao da agropecuaria no VAB. Ausente em 2022-2023."),
    "pct_vab_industria": ("continuo", "proporcao", "derivado", "atributo", "Participacao da industria no VAB. Ausente em 2022-2023."),
    "pct_vab_servicos": ("continuo", "proporcao", "derivado", "atributo", "Participacao dos servicos (exclusive adm publica). Ausente em 2022-2023."),
    "pct_vab_adm_publica": ("continuo", "proporcao", "derivado", "atributo", "Participacao da administracao publica. Ausente em 2022-2023."),
    "estab_total": ("discreto", "unidades", "CNES", "atributo", "Estabelecimentos de saude de todos os tipos."),
    "estab_atencao_basica": ("discreto", "unidades", "CNES", "atributo", "Posto de saude + UBS + Unidade de Saude da Familia."),
    "estab_hospital": ("discreto", "unidades", "CNES", "VAZAMENTO Etapa 1", "Hospital geral + especializado."),
    "estab_urgencia": ("discreto", "unidades", "CNES", "atributo", "Pronto socorro, pronto atendimento e unidade mista."),
    "estab_apoio_diagnose": ("discreto", "unidades", "CNES", "atributo", "Unidade de apoio a diagnose e terapia (SADT isolado)."),
    "estab_caps": ("discreto", "unidades", "CNES", "atributo", "Centro de Atencao Psicossocial."),
    "estab_ab_por_10mil": ("continuo", "unid/10 mil hab", "derivado", "atributo", "Densidade de atencao basica."),
    "leitos_internacao": ("discreto", "leitos", "CNES", "VAZAMENTO Etapa 1", "Leitos de internacao existentes."),
    "leitos_internacao_sus": ("discreto", "leitos", "CNES", "VAZAMENTO Etapa 1", "Leitos de internacao disponiveis ao SUS."),
    "leitos_por_mil_hab": ("continuo", "leitos/mil hab", "derivado", "VAZAMENTO Etapa 1", "Oferta hospitalar normalizada."),
    "leitos_sus_por_mil_hab": ("continuo", "leitos/mil hab", "derivado", "VAZAMENTO Etapa 1", "Oferta hospitalar SUS normalizada."),
    "leitos_uti": ("discreto", "leitos", "CNES", "ALVO 1 (origem)", "Leitos de UTI. tem_uti = (leitos_uti > 0)."),
    "leitos_complementares": ("discreto", "leitos", "CNES", "VAZAMENTO Etapa 1", "UTI + unidades intermediarias + isolamento."),
    "internacoes_total": ("discreto", "internacoes", "SIH por residencia", "ALVO 2 (denominador)", "Internacoes SUS de residentes no ano."),
    "internacoes_icsap": ("discreto", "internacoes", "SIH por residencia", "ALVO 2 (numerador)", "Internacoes sensiveis a atencao primaria (aproximadas)."),
    "tx_internacao_por_mil": ("continuo", "intern/mil hab", "derivado", "VAZAMENTO Etapa 1", "Taxa geral de internacao."),
    "nascidos_vivos": ("discreto", "nascimentos", "SINASC", "atributo", "Nascidos vivos por residencia da mae."),
    "nasc_prenatal_7mais": ("discreto", "nascimentos", "SINASC", "atributo", "Nascimentos com 7 ou mais consultas de pre-natal."),
    "nasc_prenatal_nenhuma": ("discreto", "nascimentos", "SINASC", "atributo", "Nascimentos sem nenhuma consulta de pre-natal."),
    "nasc_prenatal_ignorado": ("discreto", "nascimentos", "SINASC", "atributo", "Numero de consultas nao informado."),
    "pct_prenatal_7mais": ("continuo", "proporcao", "derivado", "atributo", "Indicador de acesso a atencao primaria."),
    "obitos_menor1": ("discreto", "obitos", "SIM", "atributo", "Obitos de menores de 1 ano por residencia."),
    "tx_mort_infantil": ("continuo", "por mil nasc.", "derivado", "atributo", "Mortalidade infantil. Instavel onde ha poucos nascimentos."),
    "tem_uti": ("binario", "0/1", "derivado do CNES", "**ALVO 1**", "1 se o municipio tem ao menos um leito de UTI."),
    "taxa_icsap": ("continuo", "proporcao", "derivado do SIH", "**ALVO 2**", "internacoes_icsap / internacoes_total."),
    "icsap_por_10mil": ("continuo", "intern/10 mil hab", "derivado do SIH", "VAZAMENTO Etapa 2", "Versao populacional do alvo 2."),
}


def main() -> None:
    caminho = F.DIR_PROCESSED / "municipio_ano.csv"
    df = pd.read_csv(caminho)

    faltando = set(df.columns) ^ set(CATALOGO)
    if faltando:
        raise SystemExit(f"catalogo dessincronizado da base: {sorted(faltando)}")

    linhas = []
    for coluna in df.columns:
        tipo, unidade, fonte, papel, descricao = CATALOGO[coluna]
        serie = df[coluna]
        pct_na = 100 * serie.isna().mean()
        if pd.api.types.is_numeric_dtype(serie):
            faixa = f"{serie.min():,.2f} a {serie.max():,.2f}"
        else:
            faixa = f"{serie.nunique()} categorias"
        linhas.append(
            f"| `{coluna}` | {tipo} | {unidade} | {fonte} | {papel} | {faixa} | {pct_na:.2f}% | {descricao} |"
        )

    texto = f"""# Dicionário de dados

Gerado por `python src/gerar_dicionario.py` a partir de
`data/processed/municipio_ano.csv`.

**{df.shape[0]:,} instâncias · {df.shape[1]} atributos · município × ano ·
{df['ano'].min()}–{df['ano'].max()}**

A coluna **papel** indica como o atributo pode ser usado na modelagem:

- `atributo` — candidato a preditor nas duas etapas;
- `chave` / `rótulo` — identificador, **não entra no modelo**;
- `**ALVO 1**` / `**ALVO 2**` — variável a prever;
- `VAZAMENTO Etapa N` — **proibido** como preditor naquela etapa, porque
  carrega informação do alvo. Ver `docs/04-melhorias-tradeoffs-sensibilidades.md`, S2.

| Coluna | Tipo | Unidade | Fonte | Papel | Faixa | % ausente | Descrição |
|---|---|---|---|---|---|---|---|
{chr(10).join(linhas)}
"""
    destino = F.RAIZ / "docs" / "05-dicionario-de-dados.md"
    destino.write_text(texto, encoding="utf-8")
    print(f"gravado em {destino} ({df.shape[1]} colunas)")


if __name__ == "__main__":
    main()
