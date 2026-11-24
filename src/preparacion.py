"""Preparación de datos para el modelo (CRISP-DM, fases 2 y 3).

Limpia los registros, deriva los atributos y arma la matriz X que usan
train.py y predict.py. No depende de Streamlit.

Atributos del vector X (apartado 5.4 del informe):
    temperatura, humedad_ambiente, humedad_suelo, humedad_suelo_media24,
    hora_sen, hora_cos, dpv_kpa, cultivo_cod

No se usan el mes ni el día de la semana: cada invernadero cubre meses
distintos, así que el mes funcionaba como identificador del invernadero, y el
día de la semana no tiene sentido agronómico.

Los datos son sintéticos (ver la hoja Parametros de cada Excel).
"""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

COL_TEMP = "Temperatura_C"
COL_HAMB = "Humedad_ambiente_%"
COL_HSUELO = "Humedad_suelo_%"
COL_FECHA = "Fecha_Hora"
COL_ESTADO = "Estado_hidrico"
COL_DECISION = "Decision"
COL_PARTICION = "Particion"
COL_INVERNADERO = "Invernadero"
COL_CULTIVO = "Cultivo"

ENTRADAS = [COL_TEMP, COL_HAMB, COL_HSUELO]

FEATURES = [
    "temperatura",
    "humedad_ambiente",
    "humedad_suelo",
    "humedad_suelo_media24",
    "hora_sen",
    "hora_cos",
    "dpv_kpa",
    "cultivo_cod",
]

# Columnas numéricas (se escalan) y categórica (one-hot en los modelos lineales).
NUMERICAS = FEATURES[:-1]
CATEGORICAS = ["cultivo_cod"]

# El cultivo fija el umbral de humedad crítica (hoja Parametros de cada Excel):
# lechuga sobre suelo arcilloso 37,4 % (39,4 % con alta demanda) y pepino sobre
# franco arenoso 23,4 % (25,4 %). Sin esta variable el modelo aprende un umbral
# promedio que no sirve para ningún invernadero.
CULTIVOS = {"tomate": 1, "pimenton": 2, "lechuga": 3, "frutilla": 4, "pepino": 5}

RANGOS = {COL_TEMP: (-10.0, 60.0), COL_HAMB: (0.0, 100.0), COL_HSUELO: (0.0, 100.0)}

VENTANA_HORAS = 24


def normalizar(texto) -> str:
    """Minúsculas, sin tildes ni espacios sobrantes."""
    if pd.isna(texto):
        return ""
    t = unicodedata.normalize("NFKD", str(texto).strip().lower())
    return "".join(c for c in t if not unicodedata.combining(c))


def cultivo_desde_nombre(nombre: str | None) -> str | None:
    """dataset_01_tomate_franco_cochabamba.xlsx -> 'tomate'."""
    if not nombre:
        return None
    m = re.match(r"dataset_\d+_([a-z]+)_", Path(nombre).stem.lower())
    return m.group(1) if m else None


def cargar(ruta: str | Path) -> pd.DataFrame:
    ruta = Path(ruta)
    if ruta.is_dir():
        partes = []
        for archivo in sorted(ruta.glob("dataset_*.xlsx")):
            df = pd.read_excel(archivo)
            df[COL_CULTIVO] = cultivo_desde_nombre(archivo.name)
            df[COL_INVERNADERO] = archivo.stem.split("_")[1]
            partes.append(df)
        return pd.concat(partes, ignore_index=True)
    if ruta.suffix.lower() == ".csv":
        df = pd.read_csv(ruta, encoding="utf-8-sig")
    else:
        df = pd.read_excel(ruta)
        if COL_CULTIVO not in df.columns:
            df[COL_CULTIVO] = cultivo_desde_nombre(ruta.name)
    df.columns = [str(c).replace("﻿", "").strip() for c in df.columns]
    return df


def limpiar(df: pd.DataFrame, con_etiqueta: bool = True) -> tuple[pd.DataFrame, dict]:
    """Reglas de limpieza de la Tabla 12 del informe. Devuelve (df, reporte)."""
    reporte = {"filas_iniciales": len(df)}
    df = df.copy()
    for c in ENTRADAS:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    if COL_FECHA in df.columns:
        df[COL_FECHA] = pd.to_datetime(df[COL_FECHA], errors="coerce")

    antes = len(df)
    df = df.dropna(subset=ENTRADAS)
    reporte["nulos"] = antes - len(df)

    antes = len(df)
    for c, (lo, hi) in RANGOS.items():
        df = df[df[c].between(lo, hi)]
    reporte["fuera_de_rango"] = antes - len(df)

    antes = len(df)
    claves = [c for c in (COL_INVERNADERO, COL_FECHA) if c in df.columns]
    df = df.drop_duplicates(subset=claves or None)
    reporte["duplicados"] = antes - len(df)

    if con_etiqueta:
        antes = len(df)
        dec = df[COL_DECISION].map(normalizar)
        df = df[dec.isin(["regar", "no regar"])].copy()
        df["regar"] = (df[COL_DECISION].map(normalizar) == "regar").astype(int)
        if COL_ESTADO in df.columns:
            df["estado"] = df[COL_ESTADO].map(normalizar).map(
                {"optimo": "Óptimo", "critico": "Crítico", "saturado": "Saturado"})
        reporte["etiqueta_invalida"] = antes - len(df)

    reporte["filas_finales"] = len(df)
    return df, reporte


def dpv_kpa(temperatura, humedad_ambiente):
    """Déficit de presión de vapor en kPa: es(T) · (1 − HR/100), con es de Tetens (FAO-56)."""
    es = 0.6108 * np.exp(17.27 * temperatura / (temperatura + 237.3))
    return es * (1 - humedad_ambiente / 100)


def derivar_atributos(df: pd.DataFrame, cultivo: str | None = None) -> pd.DataFrame:
    """Agrega las columnas de FEATURES sin alterar el orden de las filas."""
    df = df.copy()
    df["temperatura"] = df[COL_TEMP].astype(float)
    df["humedad_ambiente"] = df[COL_HAMB].astype(float)
    df["humedad_suelo"] = df[COL_HSUELO].astype(float)

    fechas = (pd.to_datetime(df[COL_FECHA], errors="coerce")
              if COL_FECHA in df.columns else pd.Series(pd.NaT, index=df.index))
    hora = fechas.dt.hour.fillna(df.get("hora", 12)).astype(int)
    df["hora_sen"] = np.sin(2 * np.pi * hora / 24)
    df["hora_cos"] = np.cos(2 * np.pi * hora / 24)
    df["dpv_kpa"] = dpv_kpa(df["temperatura"], df["humedad_ambiente"])

    if COL_CULTIVO in df.columns:
        cod = df[COL_CULTIVO].map(normalizar).map(CULTIVOS)
    else:
        cod = pd.Series(np.nan, index=df.index)
    if cultivo:
        cod = cod.fillna(CULTIVOS.get(normalizar(cultivo), np.nan))
    df["cultivo_cod"] = cod.fillna(0).astype(int)

    df["humedad_suelo_media24"] = _media_movil(df, fechas)
    return df


def _media_movil(df: pd.DataFrame, fechas: pd.Series) -> pd.Series:
    """Media de las últimas 24 lecturas de humedad del suelo, por invernadero.

    Distingue un suelo que se está secando de uno estable en el mismo valor.
    Con una sola lectura (consulta puntual) toma el valor instantáneo.
    """
    suelo = df["humedad_suelo"]
    if fechas.isna().all() or len(df) < 2:
        return suelo.copy()
    aux = pd.DataFrame({"s": suelo, "f": fechas,
                        "g": df[COL_INVERNADERO] if COL_INVERNADERO in df.columns else 0})
    aux = aux.sort_values(["g", "f"])
    media = aux.groupby("g")["s"].transform(
        lambda s: s.rolling(VENTANA_HORAS, min_periods=1).mean())
    return media.reindex(df.index).fillna(suelo)


def particionar(df: pd.DataFrame, semilla: int = 42) -> dict[str, pd.DataFrame]:
    """Respeta la columna Particion del dataset; si no existe, 70/15/15 estratificado."""
    if COL_PARTICION in df.columns:
        clave = df[COL_PARTICION].map(normalizar)
        partes = {"entrenamiento": df[clave.str.startswith("entren")],
                  "validacion": df[clave.str.startswith("valid")],
                  "prueba": df[clave.str.startswith("prueba")]}
        if all(len(p) for p in partes.values()):
            return partes
    from sklearn.model_selection import train_test_split
    resto, prueba = train_test_split(df, test_size=0.15, random_state=semilla, stratify=df["regar"])
    entren, valid = train_test_split(resto, test_size=0.1765, random_state=semilla,
                                     stratify=resto["regar"])
    return {"entrenamiento": entren, "validacion": valid, "prueba": prueba}
