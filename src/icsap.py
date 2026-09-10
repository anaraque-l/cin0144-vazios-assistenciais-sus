"""Operacionalizacao da Lista Brasileira de ICSAP dentro do TabNet.

ICSAP = Internacoes por Condicoes Sensiveis a Atencao Primaria. A lista oficial
e a da Portaria SAS/MS n. 221, de 17/04/2008: 19 grupos de causas definidos em
codigos CID-10 de 3 e 4 caracteres (`J15.3`, `N39.0`, ...).

O problema pratico
------------------
O TabNet do SIH nao expoe a CID em 3/4 caracteres no recorte Brasil x municipio.
A dimensao disponivel e a **Lista de Morbidade CID-10** -- a lista de tabulacao
do proprio CID-10, com 333 grupos. Ela e mais fina do que os capitulos, mas mais
grossa do que a categoria de 3 caracteres em alguns pontos.

Consequencia: o alvo do projeto e `taxa_icsap_aprox`, uma **aproximacao** da
Lista Brasileira, montada mapeando cada um dos 19 grupos da portaria para os
grupos da Lista de Morbidade que os contem. Onde o grupo da Lista de Morbidade
e mais amplo do que o da portaria, a aproximacao **superestima** -- e isso esta
declarado grupo a grupo em `MAPA`, no campo `divergencia`.

A alternativa exata seria baixar os microdados do SIH (arquivos RD*.dbc em
ftp.datasus.gov.br, via PySUS ou microdatasus) e filtrar `DIAG_PRINC` pela lista
da portaria. Isso foi deixado como refinamento: exige ~30 GB de download, o FTP
do DATASUS e instavel, e a granularidade extra nao muda a natureza do problema
de aprendizado. Ver docs/03-icsap-operacionalizacao.md.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from fontes import DIR_RAW


@dataclass(frozen=True)
class GrupoICSAP:
    grupo: int
    nome: str
    #: codigos da dimensao "Lista_Morb__CID-10" do TabNet do SIH
    codigos_lista_morb: tuple[int, ...]
    #: "exato" | "superestima" | "subestima"
    aderencia: str
    divergencia: str = ""


MAPA: tuple[GrupoICSAP, ...] = (
    GrupoICSAP(
        1,
        "Doencas preveniveis por imunizacao e condicoes sensiveis",
        (7, 8, 9, 10, 11, 12, 13, 14, 15, 19, 20, 21, 22, 29, 30, 31, 41, 47, 48, 49, 52, 56, 57, 58, 59, 60, 73, 140, 167),
        "superestima",
        "140 e 'Meningite bacteriana NCOP' (G00 inteiro) e a portaria pede so G00.0; "
        "73 e 'Outras helmintiases' e a portaria pede so B77 (ascaridiase).",
    ),
    GrupoICSAP(2, "Gastroenterites infecciosas e complicacoes", (1, 2, 3, 4, 5, 6, 130), "exato",
               "A00-A09 corresponde exatamente aos grupos 1-6; E86 ao grupo 130."),
    GrupoICSAP(3, "Anemia", (117,), "exato", "117 = 'Anemia por deficiencia de ferro' = D50."),
    GrupoICSAP(4, "Deficiencias nutricionais", (125, 126, 127), "subestima",
               "Cobre desnutricao (E40-E46) e deficiencias vitaminicas; parte de E50-E64 cai em "
               "'Outros transt endocrinos' (131), grupo amplo demais para incluir."),
    GrupoICSAP(5, "Infeccoes de ouvido, nariz e garganta", (164, 189, 191, 196), "superestima",
               "196 e 'Outras doencas do nariz e seios paranasais' (J30-J34) e a portaria pede so J31."),
    GrupoICSAP(6, "Pneumonias bacterianas", (193,), "superestima",
               "193 e 'Pneumonia' (J12-J18) e inclui pneumonia viral, que a portaria exclui. "
               "E a maior fonte de superestimacao do alvo."),
    GrupoICSAP(7, "Asma", (200,), "exato", "200 = 'Asma' = J45-J46."),
    GrupoICSAP(8, "Doencas pulmonares", (194, 199, 201), "exato",
               "194 = J20-J21; 199 = J40-J44; 201 = J47."),
    GrupoICSAP(9, "Hipertensao", (169, 170), "superestima",
               "170 = 'Outras doencas hipertensivas' (I12-I15); a portaria pede so I10-I11."),
    GrupoICSAP(10, "Angina", (172,), "superestima",
               "172 = 'Outras doencas isquemicas do coracao' (I20-I25); a portaria pede so I20. "
               "Segunda maior fonte de superestimacao."),
    GrupoICSAP(11, "Insuficiencia cardiaca", (175,), "subestima",
               "175 = I50. J81 (edema pulmonar) fica em 'Outras doencas do aparelho respiratorio', "
               "grupo amplo demais para incluir."),
    GrupoICSAP(12, "Doencas cerebrovasculares", (150, 178, 179, 180), "exato",
               "150 = G45-G46; 178 = I63; 179 = I64; 180 = I65-I69."),
    GrupoICSAP(13, "Diabetes mellitus", (124,), "exato", "124 = 'Diabetes mellitus' = E10-E14."),
    GrupoICSAP(14, "Epilepsias", (148,), "exato", "148 = 'Epilepsia' = G40-G41."),
    GrupoICSAP(15, "Infeccao no rim e trato urinario", (237, 240, 241), "superestima",
               "241 = 'Outras doencas do aparelho urinario' e mais amplo que N34 + N39.0."),
    GrupoICSAP(16, "Infeccao da pele e tecido subcutaneo", (222,), "exato",
               "222 = 'Infeccoes da pele e do tecido subcutaneo' = L00-L08 (+A46 em 28)."),
    GrupoICSAP(17, "Doenca inflamatoria orgaos pelvicos femininos", (248, 249, 250), "exato",
               "248 = N70; 249 = N72; 250 = N71+N73-N77."),
    GrupoICSAP(18, "Ulcera gastrointestinal", (207,), "subestima",
               "207 = K25-K28. K92.0-K92.2 (hemorragia digestiva) fica em grupo amplo, nao incluido."),
    GrupoICSAP(19, "Doencas relacionadas ao pre-natal e parto", (29,), "subestima",
               "29 = 'Sifilis congenita' = A50. O23 e P35.0 caem em grupos obstetricos/perinatais "
               "amplos demais para incluir sem contaminar o alvo."),
)


def codigos_lista_morb() -> list[str]:
    """Codigos da dimensao `SLista_Morb__CID-10` que compoem o alvo aproximado."""
    juntos: set[int] = set()
    for grupo in MAPA:
        juntos.update(grupo.codigos_lista_morb)
    return [str(codigo) for codigo in sorted(juntos)]


def tabela_mapa() -> pd.DataFrame:
    """Mapa portaria -> Lista de Morbidade, para citar no relatorio."""
    return pd.DataFrame(
        [
            {
                "grupo_icsap": g.grupo,
                "nome_grupo": g.nome,
                "n_grupos_lista_morb": len(g.codigos_lista_morb),
                "codigos_lista_morb": ",".join(str(c) for c in g.codigos_lista_morb),
                "aderencia": g.aderencia,
                "divergencia": g.divergencia,
            }
            for g in MAPA
        ]
    )


def lista_oficial() -> pd.DataFrame:
    """Lista Brasileira de ICSAP como publicada na Portaria SAS/MS 221/2008."""
    return pd.read_csv(DIR_RAW / "icsap_lista_brasileira.csv", sep=";")


if __name__ == "__main__":
    print(f"{len(codigos_lista_morb())} grupos da Lista de Morbidade compoem o alvo")
    print(tabela_mapa().to_string(index=False))
