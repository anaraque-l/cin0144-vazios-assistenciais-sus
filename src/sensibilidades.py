# -*- coding: utf-8 -*-
"""Mede o PESO de cada decisao de modelagem, sem tomar nenhuma delas.

Executar: python src/sensibilidades.py

POR QUE ISTO EXISTE NUMA ENTREGA EXPLORATORIA

  docs/04 ja lista as sensibilidades S1-S8, e elas foram conferidas. Mas eram
  conferencias QUALITATIVAS: "confirmar que a lista de atributos exclui X",
  "uma logistica so com populacao provavelmente ja entrega AUC alta". Uma
  hipotese sem numero e palpite, e o enunciado pede que as hipoteses decorram
  das evidencias.

  Este modulo transforma quatro daquelas verificacoes em medida:
  quanto exatamente a validacao aleatoria infla o resultado? quanto vale cada
  atributo suspeito de vazamento? balancear ajuda de verdade com 10,8% de
  positivos? a pandemia atrapalha o treino?

  ISTO NAO E A MODELAGEM DA ENTREGA 2. A diferenca importa:
    - a Entrega 2 escolhe o melhor modelo e reporta o desempenho dele;
    - aqui roda UM protocolo fixo e simples, e o que se compara e sempre a
      DIFERENCA entre duas versoes. O modelo e instrumento de medida, como um
      termometro. Nenhum numero daqui vira "o desempenho do nosso modelo".

  A base entregue em data/processed/ continua sem imputacao, sem remocao de
  outlier e sem codificacao. Toda transformacao testada aqui acontece DENTRO
  dos folds, num Pipeline, e morre no fim da funcao.
"""

import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.model_selection import (StratifiedGroupKFold, StratifiedKFold,
                                     cross_val_score)
from sklearn.pipeline import Pipeline

warnings.filterwarnings("ignore")

RAIZ = Path(__file__).resolve().parent.parent
SEMENTE = 42
ARVORES = 200

# ---------------------------------------------------------------------------
# Conjuntos de atributos
# ---------------------------------------------------------------------------
# O conjunto "honesto" da Etapa 1: o que descreve o municipio SEM descrever o
# alvo. Vem de docs/04, S2, com um acrescimo que S2 nao previa - ver S2 abaixo.

HONESTAS_E1 = [
    "populacao", "area_km2", "densidade_demografica", "ano",
    "pib_mil_reais", "pib_per_capita", "vab_total",
    "pct_vab_agropecuaria", "pct_vab_industria", "pct_vab_servicos",
    "pct_vab_adm_publica",
    "pct_esgoto_rede", "pct_agua_rede", "pct_lixo_coletado",
    "estab_total", "estab_atencao_basica", "estab_urgencia",
    "estab_apoio_diagnose", "estab_caps", "estab_ab_por_10mil",
    "equipes_esf", "equipes_ab_outras", "cobertura_esf",
    "equipes_ab_por_10mil",
    "lat", "lon",
    "nascidos_vivos", "pct_prenatal_7mais", "tx_mort_infantil",
]

# Atributos posteriores ao alvo ou derivados dele. Os cinco primeiros estao em
# docs/04, S2. Os dois ultimos NAO estavam - e sao os piores.
VAZAMENTOS_E1 = {
    "leitos_uti": "e o proprio alvo, em contagem",
    "leitos_complementares": "inclui os leitos de UTI",
    "leitos_internacao": "quem tem UTI tem leito de internacao",
    "estab_hospital": "quase determina o alvo",
    "internacoes_total": "circular: municipio com UTI interna mais PORQUE tem UTI",
    "dist_uti_km": "VALE ZERO exatamente quando tem_uti=1 - vazamento perfeito",
    "vazio_assistencial": "e definido a partir de tem_uti",
}


def _dados(colunas=None):
    caminho = RAIZ / "data" / "processed" / "municipio_ano.csv"
    if not caminho.exists():
        raise SystemExit("Falta %s. Rode antes: python src/build_dataset.py" % caminho)
    return pd.read_csv(caminho, usecols=colunas)


def _pipeline():
    """Imputacao DENTRO do fold, senao a mediana do teste entra no treino."""
    return Pipeline([
        ("imp", SimpleImputer(strategy="median")),
        ("modelo", RandomForestClassifier(n_estimators=ARVORES,
                                          random_state=SEMENTE, n_jobs=-1)),
    ])


def _auc(X, y, grupos=None, agrupado=False, modelo=None):
    """AUC media em 5 folds. Com agrupado=True, nenhum municipio aparece nos
    dois lados da particao."""
    p = _pipeline() if modelo is None else modelo
    if agrupado:
        cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=SEMENTE)
        s = cross_val_score(p, X, y, groups=grupos, cv=cv, scoring="roc_auc", n_jobs=1)
    else:
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEMENTE)
        s = cross_val_score(p, X, y, cv=cv, scoring="roc_auc", n_jobs=1)
    return s.mean(), s.std()


# ---------------------------------------------------------------------------
# S1 - a nao-independencia das linhas, medida
# ---------------------------------------------------------------------------

def s1_particao(d):
    print("\n" + "=" * 76)
    print("S1  PARTICAO - aleatoria x agrupada por municipio")
    print("=" * 76)
    print("  docs/04 dizia: 'o modelo memoriza o municipio e a metrica sobe'.")
    print("  Aqui esta o quanto.\n")

    X, y, g = d[HONESTAS_E1], d["tem_uti"], d["cod_ibge7"]
    aleat, sa = _auc(X, y, agrupado=False)
    agrup, sg = _auc(X, y, grupos=g, agrupado=True)

    print("    StratifiedKFold aleatorio        AUC %.4f (+/-%.4f)" % (aleat, sa))
    print("    StratifiedGroupKFold p/ municipio AUC %.4f (+/-%.4f)" % (agrup, sg))
    print("    otimismo da particao aleatoria:  %+.4f" % (aleat - agrup))
    print()
    print("  Por que o efeito e este tamanho: 85,3%% dos municipios NUNCA tiveram")
    print("  UTI em 10 anos e 8,7%% sempre tiveram. Com particao aleatoria, o mesmo")
    print("  municipio cai no treino e no teste em anos diferentes - o modelo so")
    print("  precisa reconhece-lo e repetir a resposta.")
    return {"aleatoria": aleat, "agrupada": agrup}


# ---------------------------------------------------------------------------
# S2 - vazamento, medido um a um
# ---------------------------------------------------------------------------

def s2_vazamento(d):
    print("\n" + "=" * 76)
    print("S2  VAZAMENTO - quanto vale cada atributo proibido")
    print("=" * 76)
    print("  AUC com particao AGRUPADA (a honesta), alvo tem_uti.\n")

    X, y, g = d[HONESTAS_E1], d["tem_uti"], d["cod_ibge7"]
    base, _ = _auc(X, y, grupos=g, agrupado=True)
    print("    %-24s AUC %.4f   (referencia)" % ("conjunto honesto", base))

    linhas = [("conjunto honesto", base, 0.0, "")]
    for col, motivo in VAZAMENTOS_E1.items():
        if col not in d.columns:
            continue
        Xv = d[HONESTAS_E1 + [col]]
        auc, _ = _auc(Xv, y, grupos=g, agrupado=True)
        print("    + %-22s AUC %.4f   %+.4f  | %s" % (col, auc, auc - base, motivo))
        linhas.append((col, auc, auc - base, motivo))
    return pd.DataFrame(linhas, columns=["atributo", "auc", "delta", "motivo"])


# ---------------------------------------------------------------------------
# S3 - balanceamento: ajuda mesmo?
# ---------------------------------------------------------------------------

def s3_balanceamento(d):
    print("\n" + "=" * 76)
    print("S3  BALANCEAMENTO - com 10,8%% de positivos, class_weight ajuda?")
    print("=" * 76)
    print("  A pergunta importa porque 'a base e desbalanceada, logo balanceie'")
    print("  e exatamente o tipo de passo que se da sem medir.\n")

    from sklearn.model_selection import cross_validate

    X, y, g = d[HONESTAS_E1], d["tem_uti"], d["cod_ibge7"]
    cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=SEMENTE)
    metricas = ["roc_auc", "f1", "recall", "precision"]

    print("    %-24s %-8s %-8s %-8s %s"
          % ("", "AUC", "F1", "recall", "precisao"))
    guardado = {}
    for rotulo, peso in [("sem class_weight", None),
                         ("class_weight=balanced", "balanced")]:
        p = Pipeline([
            ("imp", SimpleImputer(strategy="median")),
            ("modelo", RandomForestClassifier(n_estimators=ARVORES, n_jobs=-1,
                                              random_state=SEMENTE, class_weight=peso)),
        ])
        r = cross_validate(p, X, y, groups=g, cv=cv, scoring=metricas, n_jobs=1)
        vals = [r["test_" + m].mean() for m in metricas]
        guardado[rotulo] = vals
        print("    %-24s %-8.4f %-8.4f %-8.4f %.4f" % (rotulo, *vals))

    a = guardado["sem class_weight"]
    b = guardado["class_weight=balanced"]
    print("    %-24s %+-8.4f %+-8.4f %+-8.4f %+.4f"
          % ("diferenca", b[0] - a[0], b[1] - a[1], b[2] - a[2], b[3] - a[3]))
    print()
    print("  Aqui esta a razao de medir em vez de supor: a AUC mal se move, porque")
    print("  e insensivel ao limiar - class_weight reordena pouco. O efeito, se")
    print("  existir, tem de aparecer em RECALL da classe positiva, que e o que")
    print("  interessa: encontrar o municipio que deveria ter UTI e nao tem.")
    print("  A decisao de balancear se toma por recall e F1, nunca por AUC.")


# ---------------------------------------------------------------------------
# S4 - o choque da pandemia
# ---------------------------------------------------------------------------

def s4_pandemia(d):
    print("\n" + "=" * 76)
    print("S4  PANDEMIA - excluir 2020-2021 do treino melhora ou piora?")
    print("=" * 76)
    print("  Os leitos COVID levaram o total nacional de 46 mil a 76 mil. docs/04")
    print("  argumenta que excluir e pior porque parte dos leitos permaneceu.\n")

    for rotulo, sub in [("base inteira (2014-2023)", d),
                        ("sem 2020-2021", d[~d["ano"].isin([2020, 2021])])]:
        X, y, g = sub[HONESTAS_E1], sub["tem_uti"], sub["cod_ibge7"]
        auc, s = _auc(X, y, grupos=g, agrupado=True)
        print("    %-26s AUC %.4f (+/-%.4f)  n=%d" % (rotulo, auc, s, len(sub)))


def main():
    colunas = sorted(set(HONESTAS_E1) | set(VAZAMENTOS_E1) |
                     {"tem_uti", "cod_ibge7", "ano"})
    d = _dados(colunas)
    print("Analise de sensibilidade - %d linhas, %d municipios"
          % (len(d), d["cod_ibge7"].nunique()))
    print("Protocolo fixo: floresta aleatoria (%d arvores), 5 folds, semente %d."
          % (ARVORES, SEMENTE))
    print("Taxa de positivos em tem_uti: %.4f" % d["tem_uti"].mean())

    s1_particao(d)
    tabela = s2_vazamento(d)
    s3_balanceamento(d)
    s4_pandemia(d)

    destino = RAIZ / "reports" / "sensibilidades-vazamento.csv"
    destino.parent.mkdir(parents=True, exist_ok=True)
    tabela.to_csv(destino, index=False, encoding="utf-8")
    print("\nTabela S2 gravada em %s" % destino.relative_to(RAIZ))


if __name__ == "__main__":
    main()
