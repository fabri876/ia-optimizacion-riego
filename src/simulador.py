"""Predictor de ejemplo (reglas simples).

Se usa solo cuando predict.py todavía no expone predecir(df).
Devuelve el mismo formato que debe devolver el modelo real:
un DataFrame con las columnas Estado_hidrico y Decision (y opcionalmente Prob_regar).
"""
import numpy as np
import pandas as pd

from datos import COL_HAMB, COL_HSUELO, COL_TEMP


def predecir(X):
    temp = X[COL_TEMP].astype(float)
    hamb = X[COL_HAMB].astype(float)
    hsuelo = X[COL_HSUELO].astype(float)

    # El calor y el aire seco suben el umbral de humedad mínima del suelo.
    ajuste = ((temp - 25) * 0.2).clip(-3, 5) + ((50 - hamb) * 0.05).clip(-2, 3)
    umbral_critico = 30 + ajuste
    umbral_saturado = 75

    estado = np.where(
        hsuelo < umbral_critico, "Crítico",
        np.where(hsuelo > umbral_saturado, "Saturado", "Óptimo"),
    )
    cerca_del_limite = (hsuelo < umbral_critico + 6) & (temp > 30)
    decision = np.where((estado == "Crítico") | cerca_del_limite, "Regar", "No Regar")

    prob_regar = 1 / (1 + np.exp((hsuelo - (umbral_critico + 4)) / 4))

    return pd.DataFrame(
        {
            "Estado_hidrico": estado,
            "Decision": decision,
            "Prob_regar": np.round(prob_regar, 3),
        },
        index=X.index,
    )
