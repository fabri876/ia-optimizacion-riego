"""Simulador: qué responde el modelo ante una condición puntual y ante un plan de riego.

- clasificar_condicion: "¿hay que regar ahora?" con temperatura, humedades, hora y cultivo.
- simular_plan: "¿alcanza mi cronograma en este mes?". Reutiliza las decisiones del modelo sobre
  el historial de ese mes y las consolida con optimizacion.comparar, la misma función que usa
  la pestaña de ahorro, para que los números de ambas pestañas sean coherentes.
"""
import calendar

import pandas as pd

from analisis import columna_tiempo, normalizar_decision, normalizar_estado, serie_tiempo
from datos import COL_HAMB, COL_HSUELO, COL_TEMP
from optimizacion import comparar
from simulador import predecir as simular_reglas


def clasificar_condicion(t, ha, hs, hora, cultivo):
    """Decisión del modelo para una condición puntual. Si predict.py no está disponible, usa reglas de ejemplo."""
    try:
        from predict import predecir_condicion

        r = predecir_condicion(t, ha, hs, hora=hora, cultivo=cultivo)
        return {
            "decision": normalizar_decision(r["decision"]),
            "estado": normalizar_estado(r["estado"]),
            "probabilidad": float(r["probabilidad"]),
            "umbral": float(r["umbral"]),
            "modo": "Modelo IA",
            "motivo": None,
        }
    except Exception as e:
        X = pd.DataFrame({COL_TEMP: [t], COL_HAMB: [ha], COL_HSUELO: [hs]})
        p = simular_reglas(X).iloc[0]
        return {
            "decision": normalizar_decision(p["Decision"]),
            "estado": normalizar_estado(p["Estado_hidrico"]),
            "probabilidad": float(p["Prob_regar"]),
            "umbral": 0.5,
            "modo": "Modo simulado",
            "motivo": f"{type(e).__name__}: {e}",
        }


def meses_disponibles(res):
    """[(número de mes, días con datos)] según la fecha de las lecturas."""
    t = serie_tiempo(res)
    if t is None:
        return []
    d = pd.DataFrame({"mes": t.dt.month, "dia": t.dt.normalize()}).dropna()
    cuenta = d.groupby("mes")["dia"].nunique()
    return [(int(m), int(n)) for m, n in cuenta.items()]


def conflictos_cronograma(horario, horas_entre):
    """Pares de riegos del cronograma separados por menos de las horas mínimas."""
    hs = sorted(horario)
    if len(hs) < 2:
        return []
    pares = []
    for a, b in zip(hs, hs[1:] + [hs[0] + 24]):
        if b - a < horas_entre:
            pares.append((a, b % 24))
    return pares


def simular_plan(res, mes, zona, litros, horario, horas_entre, costo):
    """Compara el cronograma del usuario con lo que habría indicado el modelo en ese mes."""
    t = serie_tiempo(res)
    if t is None:
        return None
    sel = (t.dt.month == mes) & (res["Zona"] == zona)
    g = res[sel]
    if g.empty:
        return None
    tg = t[sel]
    dias = int(tg.dt.normalize().nunique())
    mask = g["Pred_Decision"] == "Regar"

    comp = comparar(g, mask, litros, columna_tiempo(g), horario, horas_entre)
    riegos_modelo_dia = comp["riegos_ia"] / dias
    riegos_plan_dia = len(horario)

    anio = int(tg.dt.year.mode().iloc[0])
    dias_mes = calendar.monthrange(anio, mes)[1]

    # A qué horas indicó regar el modelo: en cuántos días del mes hubo al menos una lectura "Regar" a esa hora.
    tm = tg[mask]
    pares = pd.DataFrame({"dia": tm.dt.normalize(), "hora": tm.dt.hour}).drop_duplicates()
    cuenta = pares.groupby("hora").size()
    horas = pd.DataFrame({"Hora": range(24)})
    horas["Dias"] = horas["Hora"].map(cuenta).fillna(0).astype(int)
    horas["Pct"] = horas["Dias"] / dias * 100
    horas["En_plan"] = horas["Hora"].isin(horario)

    def mes_agua(riegos_dia):
        agua_dia = riegos_dia * litros
        agua_mes = agua_dia * dias_mes
        return agua_dia, agua_mes, agua_mes / 1000 * costo

    ad_p, am_p, cm_p = mes_agua(riegos_plan_dia)
    ad_m, am_m, cm_m = mes_agua(riegos_modelo_dia)
    return {
        "dias_con_datos": dias,
        "dias_mes": dias_mes,
        "riegos_dia_plan": riegos_plan_dia,
        "riegos_dia_modelo": riegos_modelo_dia,
        "agua_dia_plan": ad_p, "agua_dia_modelo": ad_m,
        "agua_mes_plan": am_p, "agua_mes_modelo": am_m,
        "costo_mes_plan": cm_p, "costo_mes_modelo": cm_m,
        "horas": horas,
    }
