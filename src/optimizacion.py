"""Optimización del recurso hídrico (apartado 5.6 del informe).

Compara el agua del cronograma tradicional contra el agua que usaría el sistema.

Dos detalles que hacen que el número sea defendible:

1. El cronograma tradicional riega a horas fijas (por defecto 6, 12 y 18 h),
   no en cada lectura. Compararlo contra "regar en todas las lecturas" daría
   siempre ~74 % de ahorro con estos datos, sin importar lo que haga el modelo.

2. El modelo clasifica HORAS en estado crítico, no riegos. Si se riega a las
   14:00, a las 15:00 el suelo ya está repuesto aunque esa hora siga marcada
   como crítica. Por eso las horas críticas se agrupan en eventos de riego
   separados por al menos `horas_entre_riegos`.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

HORARIO_TRADICIONAL = (6, 12, 18)
HORAS_ENTRE_RIEGOS = 6


def horas_de(df: pd.DataFrame, col_fecha: str | None) -> pd.Series | None:
    if col_fecha and col_fecha in df.columns:
        h = pd.to_datetime(df[col_fecha], errors="coerce").dt.hour
        if h.notna().mean() > 0.8:
            return h
    return None


def riegos_tradicionales(df: pd.DataFrame, col_fecha: str | None,
                         horario=HORARIO_TRADICIONAL) -> int:
    """Cantidad de riegos que habría hecho el cronograma fijo en el período."""
    horas = horas_de(df, col_fecha)
    if horas is None:
        # Sin fecha no se sabe a qué hora fue cada lectura: se asume una lectura
        # por hora y se prorratea el cronograma diario.
        return int(round(len(df) / 24 * len(horario)))
    return int(horas.isin(horario).sum())


def consolidar_eventos(df: pd.DataFrame, regar: pd.Series, col_fecha: str | None,
                       horas_entre=HORAS_ENTRE_RIEGOS) -> pd.Series:
    """1 en las lecturas donde efectivamente se abre la válvula."""
    regar = regar.astype(bool)
    if horas_entre <= 1:
        return regar.astype(int)
    fechas = (pd.to_datetime(df[col_fecha], errors="coerce")
              if horas_de(df, col_fecha) is not None else None)
    orden = fechas.sort_values(kind="stable").index if fechas is not None else df.index
    eventos = pd.Series(0, index=df.index)
    ultimo_evento = None  # marca temporal del último riego abierto
    bloqueo = 0           # lecturas que faltan por saltar cuando no hay fechas
    for i in orden:
        if fechas is None:
            # Sin fecha no se puede medir el tiempo: se asume una lectura por hora
            # y se saltan las horas_entre - 1 lecturas siguientes a cada riego.
            if bloqueo > 0:
                bloqueo -= 1
                continue
            separado = True
        else:
            fecha = fechas.loc[i]
            if pd.isna(fecha):
                continue  # sin hora válida no se puede ubicar el riego en el tiempo
            separado = (ultimo_evento is None
                        or (fecha - ultimo_evento) >= pd.Timedelta(hours=horas_entre))
        if regar.loc[i] and separado:
            eventos.loc[i] = 1
            if fechas is None:
                bloqueo = horas_entre - 1
            else:
                ultimo_evento = fechas.loc[i]
    return eventos


def comparar(df: pd.DataFrame, regar: pd.Series, litros: float, col_fecha: str | None,
             horario=HORARIO_TRADICIONAL, horas_entre=HORAS_ENTRE_RIEGOS) -> dict:
    """Litros del cronograma tradicional vs. litros del sistema, para un grupo de lecturas."""
    n_trad = riegos_tradicionales(df, col_fecha, horario)
    eventos = consolidar_eventos(df, regar, col_fecha, horas_entre)
    n_ia = int(eventos.sum())
    trad, opt = n_trad * litros, n_ia * litros
    return {"riegos_tradicional": n_trad, "riegos_ia": n_ia,
            "agua_tradicional": trad, "agua_optimizada": opt, "ahorro": trad - opt,
            "pct_ahorro": (trad - opt) / trad * 100 if trad else 0.0,
            "eventos": eventos}
