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


def _clasificar(X: pd.DataFrame, index) -> pd.DataFrame:
    """Aplica el modelo y el umbral a una matriz con las columnas de FEATURES."""
    art = cargar_modelo()
    prob = art["modelo"].predict_proba(X)[:, 1]
    regar = prob >= art["umbral"]
    estado = art["modelo_estado"].predict(X)
    # Coherencia: si el modelo de decisión manda regar, el estado mostrado es Crítico;
    # si no manda regar, nunca se muestra Crítico.
    estado = np.where(regar, "Crítico", np.where(estado == "Crítico", "Óptimo", estado))
    return pd.DataFrame({"Estado_hidrico": estado,
                         "Decision": np.where(regar, "Regar", "No Regar"),
                         "Prob_regar": np.round(prob, 3)}, index=index)


def predecir(df: pd.DataFrame, cultivo: str | None = None) -> pd.DataFrame:
    """Clasifica cada fila de df. `cultivo` se usa si df no trae la columna Cultivo."""
    X = prep.derivar_atributos(df, cultivo=cultivo)[prep.FEATURES]
    return _clasificar(X, df.index)


def predecir_condicion(temperatura: float, humedad_ambiente: float, humedad_suelo: float,
                       hora: int = 12, cultivo: str | None = None, fecha_hora=None,
                       humedad_suelo_media24: float | None = None) -> dict:
    """Consulta puntual con los mismos campos de una fila del dataset.

    fecha_hora (columna Fecha_Hora) fija la hora, el día de la semana y el mes que usa el
    modelo; sin ella se usa `hora` y un día/mes por defecto. humedad_suelo_media24 es el
    promedio de Humedad_suelo_% de las últimas 24 lecturas; sin ella se toma la lectura actual.
    """
    fila = {prep.COL_TEMP: temperatura, prep.COL_HAMB: humedad_ambiente,
            prep.COL_HSUELO: humedad_suelo, "hora": int(hora)}
    if fecha_hora is not None:
        fila[prep.COL_FECHA] = pd.Timestamp(fecha_hora)
    fila = pd.DataFrame([fila])
    X = prep.derivar_atributos(fila, cultivo=cultivo)[prep.FEATURES].copy()
    if humedad_suelo_media24 is not None:
        X["humedad_suelo_media24"] = float(humedad_suelo_media24)
    r = _clasificar(X, fila.index).iloc[0]
    return {"decision": r["Decision"], "estado": r["Estado_hidrico"],
            "probabilidad": float(r["Prob_regar"]), "umbral": cargar_modelo()["umbral"]}


def info_modelo() -> dict:
    art = cargar_modelo()
    return {"nombre": art["nombre_modelo"], "umbral": art["umbral"],
            "prueba": art["metricas_prueba"]}
