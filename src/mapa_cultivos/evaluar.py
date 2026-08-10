"""Metrics over prediction tables (METODOLOGIA §5). sklearn/scipy only —
this is the ONLY place the project computes metrics, and it never touches EE.

Naming is enforced here: metrics against the MNC are ACUERDO, never accuracy.
The caller decides which label applies by which validation set it passes in.
"""

import numpy as np
import pandas as pd
from scipy.stats import binomtest
from sklearn.metrics import cohen_kappa_score, confusion_matrix, precision_recall_fscore_support

CODIGOS = [0, 1, 2, 3, 4, 5]


def metricas(tabla: pd.DataFrame, nombres: dict[int, str]) -> dict:
    """Full metric set for one model. `tabla` needs columns clase / prediccion."""
    y_true = tabla["clase"].to_numpy()
    y_pred = tabla["prediccion"].to_numpy()
    n = len(y_true)

    overall = float((y_true == y_pred).mean())
    error_estandar = float(np.sqrt(overall * (1 - overall) / n))
    ic95 = [round(overall - 1.96 * error_estandar, 4), round(overall + 1.96 * error_estandar, 4)]

    user, producer, f1, soporte = precision_recall_fscore_support(
        y_true, y_pred, labels=CODIGOS, zero_division=0
    )
    por_clase = [
        {
            "codigo": c,
            "clase": nombres[c],
            # Zero-support classes report null, not a fake 0 (SPEC §2).
            "f1": round(float(f1[i]), 4) if soporte[i] else None,
            "producer": round(float(producer[i]), 4) if soporte[i] else None,
            "user": round(float(user[i]), 4) if soporte[i] else None,
            "soporte": int(soporte[i]),
        }
        for i, c in enumerate(CODIGOS)
    ]

    return {
        "n": n,
        "overall": round(overall, 4),
        "ic95": ic95,
        "kappa": round(float(cohen_kappa_score(y_true, y_pred, labels=CODIGOS)), 4),
        "por_clase": por_clase,
        "matriz_confusion": {
            "clases": CODIGOS,
            "filas": confusion_matrix(y_true, y_pred, labels=CODIGOS).tolist(),
        },
    }


def mcnemar(tabla_a: pd.DataFrame, tabla_b: pd.DataFrame) -> dict:
    """Paired McNemar over shared validation points (METODOLOGIA §5.3).

    Two models evaluated on the same sample are not independent; comparing
    separate confidence intervals is wrong. Exact binomial on discordant pairs.
    """
    par = tabla_a.merge(tabla_b, on="uid", suffixes=("_a", "_b"))
    acierta_a = par["prediccion_a"] == par["clase_a"]
    acierta_b = par["prediccion_b"] == par["clase_a"]
    n01 = int((acierta_a & ~acierta_b).sum())
    n10 = int((~acierta_a & acierta_b).sum())
    p = 1.0 if n01 + n10 == 0 else float(binomtest(min(n01, n10), n01 + n10, 0.5).pvalue)
    return {
        "n_pareado": len(par),
        "delta_overall": round(float(acierta_a.mean() - acierta_b.mean()), 4),
        "discordantes": [n01, n10],
        "p": round(p, 4),
        "significativo": p < 0.05,
    }
