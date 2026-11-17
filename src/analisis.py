"""Cálculos que alimentan los paneles: resúmenes, ahorro de agua y evaluación."""
import re
import warnings

import numpy as np
import pandas as pd

from datos import COL_DECISION, COL_HAMB, COL_HSUELO, COL_TEMP
from optimizacion import HORARIO_TRADICIONAL, HORAS_ENTRE_RIEGOS, comparar

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
MESES_CORTOS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]

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


def serie_tiempo(df):
    """Fecha y hora de cada lectura como serie de datetime (None si el archivo no trae fecha)."""
    tcol = columna_tiempo(df)
    if tcol is None:
        return None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return pd.to_datetime(df[tcol], errors="coerce")


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


def resumen_zonas(res, litros, horario=HORARIO_TRADICIONAL, horas_entre=HORAS_ENTRE_RIEGOS):
    """Resumen por zona. El agua se compara contra el cronograma tradicional
    (riego a horas fijas) y las horas críticas se agrupan en eventos de riego;
    ver optimizacion.py."""
    tcol = columna_tiempo(res)
    filas = []
    for zona in orden_zonas(res):
        g = res[res["Zona"] == zona]
        n = len(g)
        regar = int((g["Pred_Decision"] == "Regar").sum())
        pct = regar / n * 100
        prioridad = "Alta" if pct >= 60 else ("Media" if pct >= 30 else "Baja")
        accion = {"Alta": "Regar ahora", "Media": "Programar riego", "Baja": "No regar"}[prioridad]
        comp = comparar(g, g["Pred_Decision"] == "Regar", litros, tcol, horario, horas_entre)
        trad, opt = comp["agua_tradicional"], comp["agua_optimizada"]
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
            "Riegos_tradicional": comp["riegos_tradicional"],
            "Riegos_IA": comp["riegos_ia"],
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
    # Se suman las zonas: cada una consolida sus propios eventos de riego.
    trad, opt = float(zonas["Agua_tradicional"].sum()), float(zonas["Agua_optimizada"].sum())
    ahorro = trad - opt
    return {
        "lecturas": n,
        "regar": regar,
        "riegos_tradicional": int(zonas["Riegos_tradicional"].sum()),
        "riegos_ia": int(zonas["Riegos_IA"].sum()),
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


# ------------------------------------------------------------------
# Funciones nuevas para el panel "Qué pasó (historial)"
# ------------------------------------------------------------------
def fecha_corta(d):
    return f"{d.day} {MESES_CORTOS[d.month - 1]} {d.year}"


def periodo(res):
    """(inicio, fin, días) del archivo, o None si no trae fecha."""
    t = serie_tiempo(res)
    if t is None:
        return None
    t = t.dropna()
    if t.empty:
        return None
    ini, fin = t.min(), t.max()
    return ini, fin, (fin.normalize() - ini.normalize()).days + 1


def intervalo_lecturas(res):
    """Horas típicas entre dos lecturas seguidas (mediana), calculada en la zona con más datos."""
    t = serie_tiempo(res)
    if t is None:
        return None
    zona = res["Zona"].value_counts().idxmax()
    tz = t[res["Zona"] == zona].dropna().sort_values()
    if len(tz) < 2:
        return None
    return tz.diff().median().total_seconds() / 3600


def lecturas_por_mes(res):
    """Lecturas por mes y decisión del modelo; la suma de los meses debe dar el total."""
    t = serie_tiempo(res)
    if t is None:
        return None
    ok = t.notna()
    d = pd.DataFrame({"Mes": t[ok].dt.to_period("M").astype(str), "Decision": res.loc[ok, "Pred_Decision"]})
    tabla = d.groupby(["Mes", "Decision"]).size().unstack(fill_value=0)
    for c in ("Regar", "No Regar"):
        if c not in tabla.columns:
            tabla[c] = 0
    tabla["Total"] = tabla["Regar"] + tabla["No Regar"]
    tabla = tabla.reset_index().sort_values("Mes")

    def etiqueta(s):
        anio, mes = (int(x) for x in s.split("-"))
        return f"{MESES_CORTOS[mes - 1]} {anio}"

    tabla["Etiqueta"] = tabla["Mes"].map(etiqueta)
    return tabla[["Mes", "Etiqueta", "Regar", "No Regar", "Total"]]


_SIGNIFICADO_ESTADO = {
    "Óptimo": "La humedad del suelo está en el rango que el cultivo necesita.",
    "Crítico": "El suelo está demasiado seco para el cultivo.",
    "Saturado": "El suelo tiene exceso de agua.",
}


def tabla_estados(res):
    """Una fila por estado hídrico con números reales del dataset."""
    orden = ["Óptimo", "Crítico", "Saturado"]
    otros = [e for e in res["Pred_Estado"].unique() if e not in orden]
    filas = []
    for est in orden + sorted(otros):
        g = res[res["Pred_Estado"] == est]
        if g.empty:
            continue
        filas.append({
            "Estado": est,
            "Significado": _SIGNIFICADO_ESTADO.get(est, ""),
            "Lecturas": len(g),
            "Pct": len(g) / len(res) * 100,
            "Hum_suelo": g[COL_HSUELO].mean(),
            "Pct_regar": (g["Pred_Decision"] == "Regar").mean() * 100,
        })
    return filas


def regar_por_rango(res, col, ancho, minimo=15):
    """Porcentaje de lecturas donde el modelo indica regar, por tramos de una variable."""
    x = res[col]
    ini = np.floor(x.min() / ancho) * ancho
    fin = np.ceil(x.max() / ancho) * ancho
    if fin <= ini:
        fin = ini + ancho
    bordes = np.arange(ini, fin + ancho, ancho)
    cat = pd.cut(x, bins=bordes, right=False)
    d = pd.DataFrame({"r": cat, "regar": (res["Pred_Decision"] == "Regar")})
    g = d.groupby("r", observed=True).agg(Lecturas=("regar", "size"), Pct_regar=("regar", "mean")).reset_index()
    g["Pct_regar"] = g["Pct_regar"] * 100
    g["Inicio"] = g["r"].apply(lambda i: float(i.left))
    g["Rango"] = g["Inicio"].apply(lambda a: f"{a:.0f}–{a + ancho:.0f}")
    g = g[g["Lecturas"] >= minimo].sort_values("Inicio")
    return g[["Rango", "Inicio", "Lecturas", "Pct_regar"]].reset_index(drop=True)


def umbral_aproximado(tabla):
    """Humedad del suelo a partir de la cual el modelo deja de indicar riego (aproximada, por tramos)."""
    if tabla.empty:
        return None
    alto = tabla[tabla["Pct_regar"] >= 50]
    if alto.empty:
        return None
    ultimo_alto = alto["Inicio"].max()
    despues = tabla[(tabla["Pct_regar"] < 50) & (tabla["Inicio"] > ultimo_alto)]
    if despues.empty:
        return None
    return float(despues["Inicio"].min())


def contexto_humedad(res, hs, margen=5, minimo=20):
    """Qué hizo el modelo en el historial con humedades de suelo parecidas a hs."""
    sel = res[(res[COL_HSUELO] >= hs - margen) & (res[COL_HSUELO] <= hs + margen)]
    if len(sel) < minimo:
        return None
    return len(sel), float((sel["Pred_Decision"] == "Regar").mean() * 100)
