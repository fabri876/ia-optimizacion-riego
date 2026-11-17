"""Cálculos que alimentan los paneles: resúmenes, ahorro de agua y evaluación."""
import re
import warnings

import numpy as np
import pandas as pd

from datos import COL_DECISION, COL_HAMB, COL_HSUELO, COL_TEMP

_ESTADOS = {
    "optimo": "Óptimo", "óptimo": "Óptimo",
    "critico": "Crítico", "crítico": "Crítico",
    "saturado": "Saturado",
}


def normalizar_estado(valor):
    texto = str(valor).strip()
    return _ESTADOS.get(texto.lower(), texto)


def normalizar_decision(valor):
    texto = str(valor).strip().lower().replace("_", " ")
    return "Regar" if texto in ("regar", "1", "1.0", "si", "sí", "true") else "No Regar"


def aplicar_prediccion(df, pred):
    """Une las predicciones al dataset sin tocar las etiquetas originales."""
    res = df.copy()
    res["Pred_Estado"] = pd.Series(pred["Estado_hidrico"].values).map(normalizar_estado).values
    res["Pred_Decision"] = pd.Series(pred["Decision"].values).map(normalizar_decision).values
    if "Prob_regar" in pred.columns:
        res["Prob_regar"] = pred["Prob_regar"].values
    return res


def _natural(texto):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", str(texto))]


def orden_zonas(df):
    return sorted(df["Zona"].unique(), key=_natural)


def columna_tiempo(df):
    for c in df.columns:
        nombre = str(c).lower()
        if any(k in nombre for k in ("fecha", "hora", "time", "date")) and not pd.api.types.is_numeric_dtype(df[c]):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                t = pd.to_datetime(df[c], errors="coerce")
            if t.notna().mean() > 0.8:
                return c
    return None


def preparar_plot(df):
    """DataFrame con nombres de columna simples para los gráficos de Altair."""
    mapa = {
        COL_TEMP: "Temperatura",
        COL_HAMB: "Hum_ambiente",
        COL_HSUELO: "Hum_suelo",
        "Zona": "Zona",
        "Pred_Estado": "Estado",
        "Pred_Decision": "Decision",
    }
    p = df[[c for c in mapa if c in df.columns]].rename(columns=mapa).copy()
    tcol = columna_tiempo(df)
    if tcol:
        p["Eje"] = pd.to_datetime(df[tcol], errors="coerce")
        return p, True
    p["Eje"] = np.arange(1, len(df) + 1)
    return p, False


def recomendacion(z):
    if z["Prioridad"] == "Alta":
        return (f"Humedad del suelo promedio de {z['Hum_suelo']:.1f} % y {z['Pct_regar']:.0f} % de las "
                f"lecturas piden riego. Regar ahora.")
    if z["Prioridad"] == "Media":
        return (f"Programar riego en las próximas horas y vigilar la temperatura "
                f"({z['Temperatura']:.1f} °C).")
    if z["Estado"] == "Saturado":
        return "El suelo tiene exceso de humedad. Suspender el riego y revisar el drenaje."
    return "La humedad es adecuada. Mantener sin riego."


def resumen_zonas(res, litros):
    filas = []
    for zona in orden_zonas(res):
        g = res[res["Zona"] == zona]
        n = len(g)
        regar = int((g["Pred_Decision"] == "Regar").sum())
        pct = regar / n * 100
        prioridad = "Alta" if pct >= 60 else ("Media" if pct >= 30 else "Baja")
        accion = {"Alta": "Regar ahora", "Media": "Programar riego", "Baja": "No regar"}[prioridad]
        trad, opt = n * litros, regar * litros
        fila = {
            "Zona": zona,
            "Lecturas": n,
            "Regar": regar,
            "Pct_regar": pct,
            "Temperatura": g[COL_TEMP].mean(),
            "Hum_ambiente": g[COL_HAMB].mean(),
            "Hum_suelo": g[COL_HSUELO].mean(),
            "Estado": g["Pred_Estado"].mode().iloc[0],
            "Prioridad": prioridad,
            "Accion": accion,
            "Agua_tradicional": trad,
            "Agua_optimizada": opt,
            "Ahorro": trad - opt,
        }
        fila["Recomendacion"] = recomendacion(fila)
        filas.append(fila)
    return pd.DataFrame(filas)


def resumen_general(res, zonas, litros, costo_m3):
    n = len(res)
    regar = int((res["Pred_Decision"] == "Regar").sum())
    trad, opt = n * litros, regar * litros
    ahorro = trad - opt
    return {
        "lecturas": n,
        "regar": regar,
        "pct_regar": regar / n * 100 if n else 0,
        "agua_tradicional": trad,
        "agua_optimizada": opt,
        "ahorro": ahorro,
        "pct_ahorro": ahorro / trad * 100 if trad else 0,
        "costo_ahorro": ahorro / 1000 * costo_m3,
        "zonas_total": len(zonas),
        "zonas_riego": int((zonas["Prioridad"] != "Baja").sum()),
    }


def evaluacion_modelo(res):
    """Compara la predicción con la etiqueta real del dataset (si existe)."""
    if COL_DECISION not in res.columns:
        return None
    real = res[COL_DECISION].map(normalizar_decision)
    acierto = (real == res["Pred_Decision"]).mean() * 100
    tabla = pd.crosstab(real.rename("Real"), res["Pred_Decision"].rename("Predicho"))
    return acierto, tabla
