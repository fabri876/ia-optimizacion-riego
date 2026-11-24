"""Comparación entre cultivos: resume cada dataset con el mismo cronograma y los mismos costos."""
from analisis import resumen_general, resumen_zonas, serie_tiempo
from datos import COL_HSUELO

DIAS_MES_TIPICO = 30


def resumen_por_archivo(res, info, ent):
    """Una fila por dataset. res son las lecturas ya clasificadas por el modelo."""
    zonas = resumen_zonas(res, ent["litros"], ent["horario"], ent["horas_entre"])
    gen = resumen_general(res, zonas, ent["litros"], ent["costo"])
    t = serie_tiempo(res)
    dias = int(t.dt.normalize().nunique()) if (gen["con_fecha"] and t is not None) else None
    plan = len(ent["horario"])
    modelo = gen["riegos_ia"] / (dias * max(len(zonas), 1)) if dias else None

    fila = {
        "Cultivo": info["cultivo"] or info["titulo"],
        "Localidad": info["localidad"] or "",
        "Suelo": info["suelo"] or "",
        "Lecturas": len(res),
        "Hum_suelo": float(res[COL_HSUELO].mean()),
        "Pct_regar": gen["pct_regar"],
        "Riegos_plan": plan,
        "Riegos_modelo": modelo,
        "Agua_mes_plan": None, "Agua_mes_modelo": None, "Dif_mes": None, "Veredicto": "sin fecha",
    }
    if modelo is not None:
        fila["Agua_mes_plan"] = plan * ent["litros"] * DIAS_MES_TIPICO / 1000
        fila["Agua_mes_modelo"] = modelo * ent["litros"] * DIAS_MES_TIPICO / 1000
        fila["Dif_mes"] = fila["Agua_mes_modelo"] - fila["Agua_mes_plan"]
        d = modelo - plan
        fila["Veredicto"] = "Se queda corto" if d > 0.5 else ("Riega de más" if d < -0.5 else "Coincide")
    return fila
