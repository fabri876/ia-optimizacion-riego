"""Carga y preparación de datos para el frontend."""
import io
import re
from pathlib import Path

import pandas as pd
import streamlit as st

RAIZ = Path(__file__).resolve().parent.parent
DIR_DATOS = RAIZ / "data"

COL_TEMP = "Temperatura_C"
COL_HAMB = "Humedad_ambiente_%"
COL_HSUELO = "Humedad_suelo_%"
COL_ESTADO = "Estado_hidrico"
COL_DECISION = "Decision"
FEATURES = [COL_TEMP, COL_HAMB, COL_HSUELO]

_SUELOS = {"franco": "Franco", "francoarenoso": "Franco arenoso", "arcilloso": "Arcilloso"}
_CULTIVOS = {"pimenton": "Pimentón"}


def listar_datasets():
    """Archivos .xlsx y .csv dentro de la carpeta data/."""
    if not DIR_DATOS.exists():
        return []
    archivos = list(DIR_DATOS.glob("*.xlsx")) + list(DIR_DATOS.glob("*.csv"))
    return sorted(a for a in archivos if not a.name.startswith("~$"))


def info_desde_nombre(nombre):
    """Extrae cultivo, suelo y localidad de nombres tipo dataset_01_tomate_franco_cochabamba.xlsx"""
    base = Path(nombre).stem.lower()
    m = re.match(r"dataset_(\d+)_([a-z]+)_([a-z]+)_([a-z]+)", base)
    if not m:
        titulo = Path(nombre).stem.replace("_", " ").capitalize()
        return {"cultivo": None, "suelo": None, "localidad": None, "titulo": titulo}
    _, cultivo, suelo, localidad = m.groups()
    return {
        "cultivo": _CULTIVOS.get(cultivo, cultivo.capitalize()),
        "suelo": _SUELOS.get(suelo, suelo.capitalize()),
        "localidad": localidad.capitalize(),
        "titulo": None,
    }


def etiqueta_dataset(nombre):
    info = info_desde_nombre(nombre)
    if info["cultivo"]:
        return f"{info['cultivo']} en {info['localidad']} (suelo {info['suelo'].lower()})"
    return info["titulo"]


@st.cache_data(show_spinner=False)
def leer_archivo(contenido, nombre):
    buf = io.BytesIO(contenido)
    if nombre.lower().endswith(".csv"):
        df = pd.read_csv(buf, encoding="utf-8-sig")  # el CSV del proyecto trae BOM
    else:
        df = pd.read_excel(buf)
    df.columns = [str(c).replace("﻿", "").strip() for c in df.columns]
    return df


def columnas_faltantes(df):
    return [c for c in FEATURES if c not in df.columns]


def limpiar(df):
    """Convierte las variables de entrada a número y descarta filas incompletas."""
    df = df.copy()
    for c in FEATURES:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    antes = len(df)
    df = df.dropna(subset=FEATURES).reset_index(drop=True)
    return df, antes - len(df)


def asignar_zonas(df, nombre_unico="Invernadero"):
    """Cada zona es un lugar físico real.

    - Si el archivo trae 'Zona', se respeta.
    - Si trae 'Invernadero' (datasets_combinados.csv), cada invernadero es una zona.
    - Si no, todo el archivo es un solo invernadero (los dataset_0X.xlsx son uno cada uno).

    Antes las lecturas se repartían por turno (lectura 1 -> Zona 1, lectura 2 -> Zona 2...),
    con lo que una "zona" era un conjunto de horas sueltas y no un lugar.
    """
    df = df.copy()
    if "Zona" in df.columns:
        df["Zona"] = df["Zona"].astype(str)
    elif "Invernadero" in df.columns:
        cult = df["Cultivo"].astype(str) if "Cultivo" in df.columns else None
        num = df["Invernadero"].astype(str).str.zfill(2)
        df["Zona"] = ("Inv. " + num + (" · " + cult if cult is not None else "")).astype(str)
    else:
        df["Zona"] = nombre_unico
    return df, df["Zona"].nunique()
