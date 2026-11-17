"""Clasificación con el modelo entrenado.

Cumple el contrato que espera el frontend (docs/FRONTEND.md):

    predecir(df) -> DataFrame con las columnas
        Estado_hidrico  "Óptimo", "Crítico" o "Saturado"
        Decision        "Regar" o "No Regar"
        Prob_regar      probabilidad entre 0 y 1

Mismo número de filas y mismo orden que df. Usa Fecha_Hora y Cultivo si
vienen en df (mejoran la predicción); si no, igual funciona.

Si el modelo no existe todavía, lo entrena una vez (tarda menos de un minuto).
"""
from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import preparacion as prep  # noqa: E402

RUTA_MODELO = Path(__file__).resolve().parent.parent / "model" / "modelo_riego.pkl"


@lru_cache(maxsize=1)
def cargar_modelo(ruta: str = str(RUTA_MODELO)) -> dict:
    ruta = Path(ruta)
    if not ruta.exists():
        from train import entrenar
        entrenar(ruta_modelo=ruta, verbose=False)
    return joblib.load(ruta)


def predecir(df: pd.DataFrame, cultivo: str | None = None) -> pd.DataFrame:
    """Clasifica cada fila de df. `cultivo` se usa si df no trae la columna Cultivo."""
    art = cargar_modelo()
    X = prep.derivar_atributos(df, cultivo=cultivo)[prep.FEATURES]
    prob = art["modelo"].predict_proba(X)[:, 1]
    regar = prob >= art["umbral"]
    estado = art["modelo_estado"].predict(X)
    # Coherencia: si el modelo de decisión manda regar, el estado mostrado es Crítico;
    # si no manda regar, nunca se muestra Crítico.
    estado = np.where(regar, "Crítico", np.where(estado == "Crítico", "Óptimo", estado))
    return pd.DataFrame({"Estado_hidrico": estado,
                         "Decision": np.where(regar, "Regar", "No Regar"),
                         "Prob_regar": np.round(prob, 3)}, index=df.index)


def predecir_condicion(temperatura: float, humedad_ambiente: float, humedad_suelo: float,
                       hora: int = 12, cultivo: str | None = None) -> dict:
    """Consulta puntual: una sola lectura ingresada a mano."""
    fila = pd.DataFrame([{prep.COL_TEMP: temperatura, prep.COL_HAMB: humedad_ambiente,
                          prep.COL_HSUELO: humedad_suelo, "hora": int(hora)}])
    r = predecir(fila, cultivo=cultivo).iloc[0]
    return {"decision": r["Decision"], "estado": r["Estado_hidrico"],
            "probabilidad": float(r["Prob_regar"]), "umbral": cargar_modelo()["umbral"]}


def info_modelo() -> dict:
    art = cargar_modelo()
    return {"nombre": art["nombre_modelo"], "umbral": art["umbral"],
            "prueba": art["metricas_prueba"]}
