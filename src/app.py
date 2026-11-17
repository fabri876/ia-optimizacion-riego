"""Frontend del Sistema Inteligente de Optimización de Riego.

Ejecutar desde la raíz del proyecto:
    streamlit run src/app.py
"""
import pandas as pd
import streamlit as st

from analisis import (
    MESES, aplicar_prediccion, contexto_humedad, evaluacion_modelo, fecha_corta,
    intervalo_lecturas, lecturas_por_mes, orden_zonas, periodo, preparar_plot,
    regar_por_rango, resumen_general, resumen_zonas, tabla_estados, umbral_aproximado,
)
from componentes import (
    cifras, ficha_decision, fmt, grafico_consumo, grafico_decisiones_zona, grafico_horas,
    grafico_humedad_zona, grafico_meses, grafico_regar_rango, hero, mostrar, nota, parcela,
    pasos, pie_grafico, tabla_comparativa, tabla_estados_html, tanque, titulo_seccion,
    vacio, veredicto,
)
from datos import (
    COL_DECISION, COL_HAMB, COL_HSUELO, COL_TEMP, FEATURES, asignar_zonas,
    columnas_faltantes, etiqueta_dataset, info_desde_nombre, leer_archivo,
    limpiar, listar_datasets,
)
from escenario import clasificar_condicion, conflictos_cronograma, meses_disponibles, simular_plan
from estilos import inyectar_estilos

st.set_page_config(
    page_title="Riego inteligente",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="expanded",
)
inyectar_estilos()

CULTIVOS = ["Tomate", "Pimentón", "Lechuga", "Frutilla", "Pepino"]


def signo(x, d=0):
    """Número con signo explícito para las diferencias: +1,2 o -0,8"""
    return f"+{fmt(x, d)}" if x > 0 else fmt(x, d)


# ------------------------------------------------------------ Predicción
def ejecutar_prediccion(X, cultivo=None):
    """Usa predict.predecir(df) si existe; si no, cae al simulador de reglas.

    X lleva todas las columnas del archivo: el modelo aprovecha Fecha_Hora y
    Cultivo además de las tres variables de entrada.
    """
    try:
        from predict import predecir

        pred = predecir(X.copy(), cultivo=cultivo)
        columnas_ok = isinstance(pred, pd.DataFrame) and {"Estado_hidrico", "Decision"} <= set(pred.columns)
        if not columnas_ok or len(pred) != len(X):
            raise ValueError("predecir(df) debe devolver un DataFrame con Estado_hidrico y Decision")
        return pred, "Modelo IA", None
    except Exception as e:
        from simulador import predecir as simular

        return simular(X[FEATURES].copy()), "Modo simulado", f"{type(e).__name__}: {e}"


# ------------------------------------------------------------ Barra lateral
def barra_lateral():
    with st.sidebar:
        st.markdown(
            '<div class="marca"><div class="marca-nombre">Riego inteligente</div>'
            '<div class="marca-sub">Decide cuándo regar y cuánta agua gastar</div></div>',
            unsafe_allow_html=True,
        )

        st.markdown("**Datos históricos**")
        archivos = listar_datasets()
        opciones = ["Datasets del proyecto", "Subir archivo"] if archivos else ["Subir archivo"]
        origen = st.radio("Origen", opciones, label_visibility="collapsed")

        contenido, nombre = None, None
        if origen == "Datasets del proyecto":
            elegido = st.selectbox("Dataset", archivos, format_func=lambda p: etiqueta_dataset(p.name))
            contenido, nombre = elegido.read_bytes(), elegido.name
        else:
            subido = st.file_uploader("Archivo .xlsx o .csv", type=["xlsx", "csv"])
            if subido is not None:
                contenido, nombre = subido.getvalue(), subido.name

        st.markdown("**Tu plan de riego actual**")
        horario = st.multiselect(
            "Horas de riego del cronograma", list(range(24)), default=[6, 12, 18],
            format_func=lambda h: f"{h:02d}:00",
            help="Cada hora elegida es un riego. Con 6:00 y 12:00 riegas 2 veces al día.",
        )
        litros = st.number_input(
            "Litros por riego", min_value=1.0, value=50.0, step=5.0,
            help="Litros que salen cada vez que se abre la válvula, en todo el invernadero. "
                 "No es por minuto ni por día: es por cada riego.",
        )
        horas_entre = st.slider(
            "Horas mínimas entre riegos", 1, 12, 6,
            help="Tras regar, el suelo queda repuesto: las horas críticas siguientes no cuentan como un riego nuevo.",
        )
        costo = st.number_input("Costo del agua (Bs por m³)", min_value=0.0, value=5.0, step=0.5)
        superficie = st.number_input(
            "Superficie del invernadero (m²)", min_value=1.0, value=100.0, step=10.0,
            help="Solo sirve para expresar el riego en litros por m². El valor inicial es un ejemplo: pon la real.",
        )

        if not horario:
            st.warning("Elige al menos una hora de riego. Mientras tanto uso 6:00, 12:00 y 18:00.")
        horario = tuple(sorted(horario)) or (6, 12, 18)
        st.caption(f"Tu cronograma tiene {len(horario)} {'riego' if len(horario) == 1 else 'riegos'} al día.")
        for a, b in conflictos_cronograma(horario, horas_entre):
            st.warning(f"Los riegos de las {a:02d}:00 y las {b:02d}:00 están a menos de {horas_entre} h de distancia.")

        st.markdown("---")
        recalcular = st.button("Volver a clasificar con el modelo", width="stretch",
                               help="Úsalo si cambiaste o reentrenaste el modelo.")
    return {
        "contenido": contenido, "nombre": nombre, "horario": horario, "litros": litros,
        "horas_entre": horas_entre, "costo": costo, "superficie": superficie, "recalcular": recalcular,
    }


# ------------------------------------------------------------ Pestaña 1: Simulador
def seccion_condicion(df, res, ent, info, clave):
    titulo_seccion(
        "¿Hay que regar ahora?",
        "Escribe las condiciones del invernadero y el modelo responde si conviene regar. "
        "Los valores iniciales son la mediana del historial.",
    )
    cultivos = sorted(df["Cultivo"].dropna().astype(str).unique()) if "Cultivo" in df.columns else CULTIVOS
    idx = cultivos.index(info["cultivo"]) if info["cultivo"] in cultivos else 0

    def mediana(col, lo, hi, d):
        return round(float(min(max(df[col].median(), lo), hi)), d)

    with st.form("condicion"):
        c1, c2, c3 = st.columns(3)
        t = c1.number_input("Temperatura (°C)", -10.0, 60.0, mediana(COL_TEMP, -10, 60, 1), 0.5)
        ha = c2.number_input("Humedad del aire (%)", 0.0, 100.0, mediana(COL_HAMB, 0, 100, 0), 1.0)
        hs = c3.number_input("Humedad del suelo (%)", 0.0, 100.0, mediana(COL_HSUELO, 0, 100, 1), 0.5)
        c4, c5 = st.columns(2)
        hora = c4.slider("Hora del día", 0, 23, 14)
        cultivo = c5.selectbox("Cultivo", cultivos, index=idx)
        enviar = st.form_submit_button("Consultar al modelo", type="primary", key="btn_condicion")

    if enviar:
        st.session_state["puntual"] = {
            "clave": clave, "hs": hs, "hora": hora,
            "r": clasificar_condicion(t, ha, hs, hora, cultivo),
        }

    p = st.session_state.get("puntual")
    if not p or p["clave"] != clave:
        return
    r = p["r"]
    ficha_decision(r["decision"], r["estado"], r["probabilidad"], r["umbral"])
    cifras([("Costo de regar ahora", f"Bs {fmt(ent['litros'] / 1000 * ent['costo'], 2)}",
             f"{fmt(ent['litros'])} L a Bs {fmt(ent['costo'], 2)} por m³")])
    ctx = contexto_humedad(res, p["hs"])
    if ctx:
        n, pct = ctx
        pie_grafico(
            f"Para comparar: en el historial hay {fmt(n)} lecturas con humedad del suelo entre "
            f"{fmt(p['hs'] - 5, 0)} % y {fmt(p['hs'] + 5, 0)} %, y en {fmt(pct, 0)} % de ellas el modelo indicó regar."
        )
    if r["modo"] == "Modo simulado":
        st.caption("El modelo entrenado no respondió, así que esta consulta usa reglas de ejemplo. "
                   f"Motivo técnico: {r['motivo']}")


def seccion_plan(res, ent):
    titulo_seccion(
        "Plan del mes: ¿alcanza tu cronograma?",
        "Elige un mes. El modelo revisa las condiciones de ese mes en el historial, calcula cuántas veces "
        "al día hacía falta regar y lo compara con tu cronograma.",
    )
    horas_txt = ", ".join(f"{h:02d}:00" for h in ent["horario"])
    st.markdown(
        f"**Tu cronograma:** {len(ent['horario'])} riegos al día ({horas_txt}), con {fmt(ent['litros'])} L por riego "
        f"y agua a Bs {fmt(ent['costo'], 2)} por m³. Puedes cambiarlo en la barra lateral."
    )

    meses = meses_disponibles(res)
    if not meses:
        vacio("No se puede simular un mes",
              "El archivo no trae una columna de fecha y hora, y sin ella no sé a qué mes corresponde cada lectura.")
        return
    dias_por_mes = dict(meses)
    c1, c2 = st.columns(2)
    mes = c1.selectbox("Mes a simular", [m for m, _ in meses],
                       format_func=lambda m: f"{MESES[m - 1].capitalize()} ({dias_por_mes[m]} días con datos)")
    zonas_lista = orden_zonas(res)
    if len(zonas_lista) > 1:
        zona = c2.selectbox("Invernadero", zonas_lista)
    else:
        zona = zonas_lista[0]
        c2.markdown(f"**Invernadero:** {zona}")

    sim = simular_plan(res, mes, zona, ent["litros"], ent["horario"], ent["horas_entre"], ent["costo"])
    if sim is None:
        vacio("Sin datos para ese mes", "No hay lecturas de ese invernadero en el mes elegido.")
        return

    nombre_mes = MESES[mes - 1]
    plan, mod = sim["riegos_dia_plan"], sim["riegos_dia_modelo"]
    dif = mod - plan
    extra_l = abs(dif) * ent["litros"] * sim["dias_mes"]
    extra_bs = extra_l / 1000 * ent["costo"]
    if dif > 0.5:
        veredicto(
            f"Tu cronograma se queda corto en {nombre_mes}",
            f"El modelo indicó regar unas {fmt(mod, 1)} veces al día y tu cronograma tiene {plan}. "
            f"Te faltarían unos {fmt(dif, 1)} riegos diarios: {fmt(extra_l)} L y Bs {fmt(extra_bs, 2)} más en el mes.",
            "alerta",
        )
    elif dif < -0.5:
        veredicto(
            f"Tu cronograma riega de más en {nombre_mes}",
            f"El modelo indicó regar unas {fmt(mod, 1)} veces al día y tu cronograma tiene {plan}. "
            f"Podrías ahorrar unos {fmt(-dif, 1)} riegos diarios: {fmt(extra_l)} L y Bs {fmt(extra_bs, 2)} en el mes.",
            "agua",
        )
    else:
        veredicto(
            f"Tu cronograma coincide con el modelo en {nombre_mes}",
            f"El modelo indicó regar unas {fmt(mod, 1)} veces al día y tu cronograma tiene {plan}.",
        )

    tabla_comparativa([
        ("Riegos al día", fmt(plan, 0), fmt(mod, 1), signo(mod - plan, 1)),
        ("Agua por día (L)", fmt(sim["agua_dia_plan"]), fmt(sim["agua_dia_modelo"]),
         signo(sim["agua_dia_modelo"] - sim["agua_dia_plan"])),
        (f"Agua en el mes (m³, {sim['dias_mes']} días)", fmt(sim["agua_mes_plan"] / 1000, 2),
         fmt(sim["agua_mes_modelo"] / 1000, 2),
         signo((sim["agua_mes_modelo"] - sim["agua_mes_plan"]) / 1000, 2)),
        ("Costo del mes (Bs)", fmt(sim["costo_mes_plan"], 2), fmt(sim["costo_mes_modelo"], 2),
         signo(sim["costo_mes_modelo"] - sim["costo_mes_plan"], 2)),
    ])
    pie_grafico(
        f"Cada riego de {fmt(ent['litros'])} L en {fmt(ent['superficie'])} m² equivale a "
        f"{fmt(ent['litros'] / ent['superficie'], 2)} L por m² (1 L por m² es 1 mm de lámina de agua)."
    )

    titulo_seccion(
        f"A qué horas pide riego el cultivo en {nombre_mes}",
        f"Cada barra indica en cuántos de los {sim['dias_con_datos']} días con datos el modelo marcó regar a esa hora. "
        "Las líneas ámbar son las horas de tu cronograma: si caen donde las barras son bajas, estás regando "
        "cuando el cultivo no lo pide.",
    )
    mostrar(grafico_horas(sim["horas"]))
    top = sim["horas"][sim["horas"]["Pct"] > 0].sort_values("Pct", ascending=False).head(3)
    if not top.empty:
        txt = ", ".join(f"{int(r.Hora)}:00 ({fmt(r.Pct, 0)} % de los días)" for r in top.itertuples())
        pie_grafico(f"Horas con más demanda: {txt}.")

    nota("Qué no calcula este sistema", [
        "Producción del cultivo: el dataset no tiene datos de producción, así que no se puede estimar cuánta "
        "cosecha se obtiene con un plan de riego.",
        "Cuánto sube la humedad del suelo con cada riego: el dataset no registra cuánta agua se aplicó. "
        "El modelo decide cuándo regar según las condiciones; los litros solo se usan para calcular gasto y costo.",
    ])


def tab_simulador(df, res, ent, info, clave):
    seccion_condicion(df, res, ent, info, clave)
    seccion_plan(res, ent)


# ------------------------------------------------------------ Pestaña 2: Historial
def tab_historial(df, res, zonas, modo):
    titulo_seccion(
        "Los datos con los que aprendió el modelo",
        "Esto es lo que ya ocurrió en el invernadero. Aquí no se predice nada nuevo: se muestra cómo el modelo "
        "clasifica cada lectura histórica.",
    )
    n = len(res)
    regar = int((res["Pred_Decision"] == "Regar").sum())
    per, inter = periodo(res), intervalo_lecturas(res)
    items = [
        ("Lecturas del archivo", fmt(n), f"una cada {fmt(inter, 1)} h aproximadamente" if inter else "el archivo no trae fecha"),
        ("Período", f"{fmt(per[2])} días" if per else "sin fecha",
         f"del {fecha_corta(per[0])} al {fecha_corta(per[1])}" if per else "no se puede calcular"),
        ("Lecturas donde conviene regar", f"{fmt(regar / n * 100, 0)} %", f"{fmt(regar)} de {fmt(n)} según el modelo"),
    ]
    if modo == "Modelo IA":
        ev = evaluacion_modelo(res)
        if ev is not None:
            items.append(("Coincidencia con la etiqueta real", f"{fmt(ev[0], 1)} %",
                          f"con la columna {COL_DECISION} del dataset", "hoja"))
    cifras(items)

    tabla_mes = lecturas_por_mes(res)
    if tabla_mes is not None:
        titulo_seccion("Lecturas por mes", "Cada barra es un mes; el número de arriba es el total de lecturas de ese mes. "
                       "Azul es Regar y gris es No Regar, según el modelo.")
        mostrar(grafico_meses(tabla_mes))
        suma = int(tabla_mes["Total"].sum())
        texto = f"Los {len(tabla_mes)} meses suman {fmt(suma)} lecturas, el total del archivo."
        if suma != n:
            texto = f"Los {len(tabla_mes)} meses suman {fmt(suma)} lecturas; las otras {fmt(n - suma)} no tienen fecha válida."
        pie_grafico(texto)

    titulo_seccion("Qué significa cada estado hídrico",
                   "El estado describe cómo está el suelo. Los números salen de este archivo.")
    tabla_estados_html(tabla_estados(res))

    titulo_seccion("Cuándo indica regar el modelo",
                   "Cada barra muestra, entre las lecturas de ese tramo, el porcentaje donde el modelo marcó regar. "
                   "Por encima de la línea punteada (50 %), en ese tramo lo habitual es regar.")
    c1, c2 = st.columns(2)
    por_suelo = regar_por_rango(res, COL_HSUELO, 10)
    por_temp = regar_por_rango(res, COL_TEMP, 5)
    with c1:
        st.markdown("**Según la humedad del suelo**")
        mostrar(grafico_regar_rango(por_suelo, "Humedad del suelo (%)"))
    with c2:
        st.markdown("**Según la temperatura**")
        mostrar(grafico_regar_rango(por_temp, "Temperatura (°C)"))
    umbral = umbral_aproximado(por_suelo)
    if umbral is not None:
        pie_grafico(f"Con el suelo por encima de aproximadamente {fmt(umbral, 0)} % de humedad, "
                    "el modelo casi siempre indica no regar.")

    titulo_seccion("Por invernadero" if len(zonas) > 1 else "Estado del invernadero",
                   "Necesidad de riego según el porcentaje de lecturas donde el modelo marcó regar: "
                   "alta desde 60 %, media desde 30 %, baja por debajo de 30 %.")
    registros = zonas.to_dict("records")
    for i in range(0, len(registros), 3):
        cols = st.columns(3)
        for col, z in zip(cols, registros[i:i + 3]):
            with col:
                st.markdown(parcela(z), unsafe_allow_html=True)
    if len(registros) > 1:
        orden = orden_zonas(res)
        plot, _ = preparar_plot(res)
        c1, c2 = st.columns(2)
        with c1:
            titulo_seccion("Decisiones por invernadero")
            mostrar(grafico_decisiones_zona(plot, orden))
        with c2:
            titulo_seccion("Humedad del suelo por invernadero")
            mostrar(grafico_humedad_zona(zonas, orden))


# ------------------------------------------------------------ Pestaña 3: Ahorro
def tab_ahorro(res, zonas, general, ent):
    litros, costo, horario = ent["litros"], ent["costo"], ent["horario"]
    titulo_seccion(
        "Qué habría pasado con el modelo",
        "Compara dos formas de regar el mismo período del historial: con tu cronograma fijo y regando solo cuando el "
        "modelo lo indica.",
    )
    per = periodo(res)
    horas_txt = ", ".join(f"{h} h" for h in horario)
    cuando = f"Entre el {fecha_corta(per[0])} y el {fecha_corta(per[1])}, " if per else "En este período, "
    st.markdown(
        f"{cuando}con tu cronograma tradicional se habrían gastado **{fmt(general['agua_tradicional'])} L** "
        f"({fmt(general['riegos_tradicional'])} riegos a las {horas_txt}). Con la optimización de IA se habrían "
        f"gastado **{fmt(general['agua_optimizada'])} L** ({fmt(general['riegos_ia'])} riegos)."
    )
    if general["ahorro"] < 0:
        st.info(
            "En este período el modelo riega **más** que el cronograma fijo: el horario tradicional se "
            "queda corto cuando hace calor y el suelo se seca. El valor del sistema aquí no es ahorrar, "
            "sino regar cuando el cultivo lo necesita."
        )
    tanque(general["agua_optimizada"], max(general["ahorro"], 0), max(general["pct_ahorro"], 0))

    st.write("")
    cifras([
        ("Riego tradicional", f"{fmt(general['agua_tradicional'])} L",
         f"{fmt(general['riegos_tradicional'])} riegos a horario fijo"),
        ("Riego optimizado", f"{fmt(general['agua_optimizada'])} L",
         f"{fmt(general['riegos_ia'])} riegos cuando el modelo lo indica", "agua"),
        ("Diferencia de agua", f"{signo(-general['ahorro'] / 1000, 2)} m³",
         f"{fmt(abs(general['pct_ahorro']), 1)} % {'menos' if general['ahorro'] >= 0 else 'más'} que el cronograma", "hoja"),
        ("Diferencia de costo", f"Bs {signo(-general['costo_ahorro'], 2)}", f"a Bs {fmt(costo, 2)} por m³"),
    ])

    orden = orden_zonas(res)
    largo = pd.concat([
        pd.DataFrame({"Zona": zonas["Zona"], "Tipo": "Riego tradicional", "Litros": zonas["Agua_tradicional"]}),
        pd.DataFrame({"Zona": zonas["Zona"], "Tipo": "Riego optimizado", "Litros": zonas["Agua_optimizada"]}),
    ])
    titulo_seccion("Consumo de agua por invernadero",
                   f"Cronograma tradicional frente a riego optimizado, a {fmt(litros)} L por riego.")
    mostrar(grafico_consumo(largo, orden))

    titulo_seccion("Detalle por invernadero", "Todos los números son del período completo del archivo.")
    detalle = zonas[["Zona", "Riegos_tradicional", "Riegos_IA", "Agua_tradicional", "Agua_optimizada", "Ahorro"]].rename(
        columns={
            "Riegos_tradicional": "Riegos con cronograma", "Riegos_IA": "Riegos con el modelo",
            "Agua_tradicional": "Agua con cronograma (L)", "Agua_optimizada": "Agua con el modelo (L)",
            "Ahorro": "Agua ahorrada (L)",
        }
    )
    st.dataframe(
        detalle, hide_index=True, width="stretch",
        column_config={c: st.column_config.NumberColumn(format="%d") for c in detalle.columns if c != "Zona"},
    )


# ------------------------------------------------------------ Pestaña 4: Datos
def tab_datos(res, modo):
    titulo_seccion(
        "Resultados lectura por lectura",
        "Las columnas Pred_Estado, Pred_Decision y Prob_regar son lo que respondió el modelo. "
        "Las demás son los datos originales.",
    )
    f1, f2 = st.columns(2)
    zonas_sel = f1.multiselect("Invernaderos", orden_zonas(res), default=orden_zonas(res))
    dec_sel = f2.multiselect("Decisión del modelo", ["Regar", "No Regar"], default=["Regar", "No Regar"])
    vista = res[res["Zona"].isin(zonas_sel) & res["Pred_Decision"].isin(dec_sel)]
    st.dataframe(vista, width="stretch", hide_index=True)
    st.caption(f"Mostrando {fmt(len(vista))} de {fmt(len(res))} lecturas.")
    st.download_button(
        "Descargar resultados (CSV)",
        data=res.to_csv(index=False).encode("utf-8-sig"),
        file_name="resultados_riego.csv",
        mime="text/csv",
    )

    if modo == "Modelo IA":
        ev = evaluacion_modelo(res)
        if ev is not None:
            acierto, tabla = ev
            titulo_seccion("Qué tan bien acierta el modelo",
                           f"Comparación con la columna {COL_DECISION} del dataset: filas son lo real, columnas lo predicho.")
            cifras([("Coincidencia con la etiqueta real", f"{fmt(acierto, 1)} %", "sobre todas las lecturas", "hoja")])
            st.dataframe(tabla, width="stretch")


# ------------------------------------------------------------ Flujo principal
ent = barra_lateral()

if ent["contenido"] is None:
    hero("Riego inteligente", "Carga un archivo con lecturas de temperatura, humedad del aire y humedad del suelo.", [], "Sin datos")
    vacio("Falta el archivo de datos",
          "Sube un .xlsx o .csv desde la barra lateral, o elige uno de los datasets del proyecto.")
    st.stop()

nombre = ent["nombre"]
try:
    crudo = leer_archivo(ent["contenido"], nombre)
except Exception as e:
    st.error(f"No pude leer «{nombre}». Revisa que sea un .xlsx o .csv válido. Detalle: {e}")
    st.stop()

faltan = columnas_faltantes(crudo)
if faltan:
    st.error(
        f"Al archivo le faltan las columnas: {', '.join(faltan)}. "
        f"Columnas encontradas: {', '.join(map(str, crudo.columns))}."
    )
    st.stop()

df, descartadas = limpiar(crudo)
if df.empty:
    st.error("Después de limpiar no quedaron lecturas válidas. Revisa que las columnas sean numéricas.")
    st.stop()
if descartadas:
    st.warning(f"Se descartaron {descartadas} filas con datos vacíos o no numéricos.")

info = info_desde_nombre(nombre)
df, n_zonas_real = asignar_zonas(df, f"Invernadero · {info['cultivo']}" if info["cultivo"] else "Invernadero")
clave = f"{nombre}|{n_zonas_real}|{len(df)}"

# El modelo clasifica el historial una sola vez por archivo; los demás paneles reutilizan ese resultado.
resultado = st.session_state.get("resultado")
if resultado is None or resultado["clave"] != clave or ent["recalcular"]:
    with st.spinner(f"Clasificando las {fmt(len(df))} lecturas con el modelo..."):
        pred, modo_pred, motivo = ejecutar_prediccion(df, info["cultivo"])
        resultado = {"clave": clave, "res": aplicar_prediccion(df, pred), "modo": modo_pred, "motivo": motivo}
    st.session_state["resultado"] = resultado

res, modo = resultado["res"], resultado["modo"]
zonas = resumen_zonas(res, ent["litros"], ent["horario"], ent["horas_entre"])
general = resumen_general(res, zonas, ent["litros"], ent["costo"])

titulo = f"{info['cultivo']} en {info['localidad']}" if info["cultivo"] else info["titulo"]
detalle_suelo = f"Suelo {info['suelo'].lower()}. " if info["suelo"] else ""
per = periodo(res)
etiquetas = [f"{fmt(len(df))} lecturas", f"{n_zonas_real} {'invernadero' if n_zonas_real == 1 else 'invernaderos'}"]
if per:
    etiquetas.append(f"{fecha_corta(per[0])} a {fecha_corta(per[1])}")
hero(
    titulo,
    f"{detalle_suelo}Este sistema usa el historial del invernadero para decidir cuándo conviene regar "
    "y calcular cuánta agua y cuánto dinero cuesta tu plan de riego.",
    etiquetas,
    modo,
)

inter = intervalo_lecturas(res)
pasos([
    ("Datos históricos",
     f"{fmt(len(df))} lecturas de temperatura, humedad del aire y humedad del suelo"
     + (f", una cada {fmt(inter, 1)} h aproximadamente." if inter else ".")),
    ("El modelo aprende",
     "Un modelo de clasificación aprende en qué condiciones el cultivo necesitaba riego. "
     "Responde Regar o No Regar para cada lectura."),
    ("Tú consultas",
     "Escribes una condición o tu cronograma de riego y el modelo responde si regar, "
     "cuántos riegos al día hacen falta, cuánta agua se gasta y cuánto cuesta."),
])

if modo == "Modo simulado":
    st.caption(
        "El modelo entrenado todavía no está conectado, así que las respuestas usan reglas de ejemplo. "
        f"Motivo técnico: {resultado['motivo']}"
    )

t1, t2, t3, t4 = st.tabs(["Simulador", "Qué pasó (historial)", "Ahorro con el modelo", "Datos"])
with t1:
    tab_simulador(df, res, ent, info, clave)
with t2:
    tab_historial(df, res, zonas, modo)
with t3:
    tab_ahorro(res, zonas, general, ent)
with t4:
    tab_datos(res, modo)
