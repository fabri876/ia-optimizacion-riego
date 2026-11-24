"""Simulador: qué responde el modelo ante una condición puntual y ante un plan de riego.

- clasificar_condicion: "¿hay que regar ahora?" con temperatura, humedades, hora y cultivo.
- curva_decision: cómo cambia la respuesta del modelo si varía la humedad del suelo.
- simular_plan: "¿alcanza mi cronograma en este mes?". Reutiliza las decisiones del modelo sobre
  el historial de ese mes y las consolida con optimizacion.comparar, la misma función que usa
  la pestaña de ahorro, para que los números de ambas pestañas sean coherentes.
- cronograma_sugerido: horas en las que conviene regar según la demanda que mostró el modelo.
"""
import calendar

import pandas as pd

from analisis import columna_tiempo, normalizar_decision, normalizar_estado, serie_tiempo
from datos import COL_HAMB, COL_HSUELO, COL_TEMP
from optimizacion import comparar
from simulador import predecir as simular_reglas


def clasificar_condicion(t, ha, hs, hora, cultivo, fecha_hora=None, media24=None):
    """Decisión del modelo para una condición puntual. Si predict.py no está disponible, usa reglas de ejemplo."""
    try:
        from predict import predecir_condicion

        r = predecir_condicion(t, ha, hs, hora=hora, cultivo=cultivo, fecha_hora=fecha_hora,
                               humedad_suelo_media24=media24)
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


def curva_decision(t, ha, hora, cultivo, paso=5, fecha_hora=None, media24=None):
    """Respuesta del modelo para humedades de suelo de 0 a 100 %, dejando fija la temperatura, la humedad
    del aire, la hora y el cultivo. Devuelve (tabla, umbral %, humedad donde deja de regar, modo)."""
    filas, umbral, modo = [], 0.5, "Modelo IA"
    for hs in range(0, 101, paso):
        r = clasificar_condicion(t, ha, float(hs), hora, cultivo, fecha_hora, media24)
        filas.append({"Hum_suelo": hs, "Probabilidad": r["probabilidad"] * 100, "Decision": r["decision"]})
        umbral, modo = r["umbral"], r["modo"]
    curva = pd.DataFrame(filas)
    # Primera humedad (de menor a mayor) donde el modelo deja de indicar riego, si antes sí lo indicaba.
    limite = None
    if curva["Decision"].iloc[0] == "Regar":
        no_riega = curva[curva["Decision"] == "No Regar"]
        if not no_riega.empty:
            limite = float(no_riega["Hum_suelo"].iloc[0])
    return curva, umbral * 100, limite, modo


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


def perfil_horario(res, horario, zona=None, mes=None):
    """A qué horas indicó regar el modelo: en cuántos días hubo al menos una lectura 'Regar' a cada hora.
    Devuelve (tabla de 24 horas, días con datos) o None si el archivo no trae fecha o no hay lecturas."""
    t = serie_tiempo(res)
    if t is None:
        return None
    sel = pd.Series(True, index=res.index)
    if mes is not None:
        sel &= (t.dt.month == mes)
    if zona is not None:
        sel &= (res["Zona"] == zona)
    g = res[sel]
    if g.empty:
        return None
    tg = t[sel]
    dias = int(tg.dt.normalize().nunique())
    tm = tg[g["Pred_Decision"] == "Regar"]
    pares = pd.DataFrame({"dia": tm.dt.normalize(), "hora": tm.dt.hour}).drop_duplicates()
    cuenta = pares.groupby("hora").size()
    horas = pd.DataFrame({"Hora": range(24)})
    horas["Dias"] = horas["Hora"].map(cuenta).fillna(0).astype(int)
    horas["Pct"] = horas["Dias"] / dias * 100
    horas["En_plan"] = horas["Hora"].isin(horario)
    return horas, dias


def cronograma_sugerido(horas, riegos_dia, horas_entre):
    """Elige las horas con más demanda, respetando las horas mínimas entre riegos.
    La cantidad de riegos es el promedio diario que indicó el modelo, redondeado."""
    n = int(round(riegos_dia))
    if n <= 0:
        return []
    elegidas = []
    for h in horas.sort_values("Pct", ascending=False)["Hora"]:
        if horas.loc[horas["Hora"] == h, "Pct"].iloc[0] <= 0:
            break
        if all(min((h - e) % 24, (e - h) % 24) >= horas_entre for e in elegidas):
            elegidas.append(int(h))
        if len(elegidas) == n:
            break
    return sorted(elegidas)


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

    horas, _ = perfil_horario(res, horario, zona=zona, mes=mes)
    sugerido = cronograma_sugerido(horas, riegos_modelo_dia, horas_entre)
    horas["En_sugerido"] = horas["Hora"].isin(sugerido)

    def mes_agua(riegos_dia):
        agua_dia = riegos_dia * litros
        agua_mes = agua_dia * dias_mes
        return agua_dia, agua_mes, agua_mes / 1000 * costo

    ad_p, am_p, cm_p = mes_agua(riegos_plan_dia)
    ad_m, am_m, cm_m = mes_agua(riegos_modelo_dia)
    _, am_s, cm_s = mes_agua(len(sugerido))
    return {
        "dias_con_datos": dias,
        "dias_mes": dias_mes,
        "riegos_dia_plan": riegos_plan_dia,
        "riegos_dia_modelo": riegos_modelo_dia,
        "agua_dia_plan": ad_p, "agua_dia_modelo": ad_m,
        "agua_mes_plan": am_p, "agua_mes_modelo": am_m,
        "costo_mes_plan": cm_p, "costo_mes_modelo": cm_m,
        "sugerido": sugerido, "agua_mes_sugerido": am_s, "costo_mes_sugerido": cm_s,
        "horas": horas,
    }
