"""Frontend del Sistema Inteligente de Optimización de Riego.

Ejecutar desde la raíz del proyecto:
    streamlit run src/app.py
"""
import pandas as pd
import streamlit as st

from analisis import (
    aplicar_prediccion, evaluacion_modelo, orden_zonas, preparar_plot,
    resumen_general, resumen_zonas,
)
from componentes import (
    COLORES_DECISION, COLORES_ESTADO, cifras, fmt, grafico_consumo,
    grafico_decisiones_zona, grafico_dispersion, grafico_dona, grafico_estados,
    grafico_histograma, grafico_humedad_zona, grafico_serie, hero, mostrar,
    parcela, tanque, titulo_seccion, vacio,
)
from datos import (
    COL_DECISION, COL_HAMB, COL_HSUELO, COL_TEMP, FEATURES, asignar_zonas,
    columnas_faltantes, etiqueta_dataset, info_desde_nombre, leer_archivo,
    limpiar, listar_datasets,
)
from estilos import inyectar_estilos

st.set_page_config(
    page_title="Riego inteligente",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="expanded",
)
inyectar_estilos()


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


# ------------------------------------------------------------ Consulta puntual
def consulta_rapida():
    """Condición actual ingresada a mano (la consigna pide este modo además de la carga de archivo)."""
    with st.sidebar.expander("Consulta rápida: condición actual"):
        with st.form("consulta"):
            t = st.number_input("Temperatura (°C)", -10.0, 60.0, 28.0, 0.5)
            ha = st.number_input("Humedad del aire (%)", 0.0, 100.0, 45.0, 1.0)
            hs = st.number_input("Humedad del suelo (%)", 0.0, 100.0, 29.0, 0.5)
            hora = st.slider("Hora del día", 0, 23, 14)
            cultivo = st.selectbox("Cultivo", ["Tomate", "Pimentón", "Lechuga", "Frutilla", "Pepino"])
            enviar = st.form_submit_button("Clasificar", width="stretch")
        if enviar:
            try:
                from predict import predecir_condicion

                r = predecir_condicion(t, ha, hs, hora=hora, cultivo=cultivo)
                (st.error if r["decision"] == "Regar" else st.success)(
                    f"**{r['decision']}** · estado {r['estado'].lower()}")
                st.caption(f"Probabilidad de necesitar riego: {r['probabilidad']:.0%} "
                           f"(se riega desde {r['umbral']:.0%}).")
            except Exception as e:
                st.warning(f"El modelo no está disponible: {e}")


# ------------------------------------------------------------ Barra lateral
def barra_lateral():
    with st.sidebar:
        st.markdown(
            '<div class="marca"><div class="marca-nombre">Riego inteligente</div>'
            '<div class="marca-sub">Decide dónde regar y cuánta agua ahorrar</div></div>',
            unsafe_allow_html=True,
        )

        st.markdown("**Datos de entrada**")
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

        st.markdown("**Parámetros**")
        litros = st.number_input("Agua por riego (litros)", min_value=1.0, value=50.0, step=5.0,
                                 help="Litros que se aplican cada vez que se abre la válvula.")
        horario = st.multiselect("Cronograma tradicional (horas)", list(range(24)), default=[6, 12, 18],
                                 help="Horas a las que hoy se riega por reloj. Es la referencia del ahorro.")
        horas_entre = st.slider("Horas mínimas entre riegos", 1, 12, 6,
                                help="Tras regar, el suelo queda repuesto: las horas críticas siguientes "
                                     "no cuentan como un riego nuevo.")
        costo = st.number_input("Costo del agua (Bs por m³)", min_value=0.0, value=5.0, step=0.5)
    return contenido, nombre, litros, tuple(sorted(horario)) or (6, 12, 18), horas_entre, costo


# ------------------------------------------------------------ Pestañas
def tab_resumen(df, res, plot, es_tiempo, general, modo):
    prom_t, prom_a, prom_s = df[COL_TEMP].mean(), df[COL_HAMB].mean(), df[COL_HSUELO].mean()

    if res is None:
        cifras([
            ("Lecturas cargadas", fmt(len(df)), "filas con datos completos"),
            ("Temperatura promedio", f"{fmt(prom_t, 1)} °C", f"entre {fmt(df[COL_TEMP].min(), 1)} y {fmt(df[COL_TEMP].max(), 1)} °C"),
            ("Humedad del aire", f"{fmt(prom_a, 0)} %", "promedio de las lecturas"),
            ("Humedad del suelo", f"{fmt(prom_s, 1)} %", "promedio de las lecturas", "agua"),
        ])
        titulo_seccion("Cómo se comporta el suelo", "Humedad del suelo lectura por lectura. Al analizar, cada punto se colorea según la decisión.")
        mostrar(grafico_serie(plot, es_tiempo, False))
        c1, c2, c3 = st.columns(3)
        with c1:
            mostrar(grafico_histograma(plot, "Temperatura", "Temperatura (°C)", "#E39A1B"))
        with c2:
            mostrar(grafico_histograma(plot, "Hum_ambiente", "Humedad del aire (%)", "#9DB8A6"))
        with c3:
            mostrar(grafico_histograma(plot, "Hum_suelo", "Humedad del suelo (%)", "#1B73C9"))
        return

    cifras([
        ("Lecturas analizadas", fmt(general["lecturas"]), f"{fmt(general['regar'])} piden riego"),
        ("Zonas que piden riego", f"{general['zonas_riego']} de {general['zonas_total']}",
         "prioridad alta o media", "alerta" if general["zonas_riego"] else "hoja"),
        ("Agua ahorrada", f"{fmt(general['ahorro'])} L", f"{fmt(general['pct_ahorro'], 1)} % frente al cronograma tradicional", "agua"),
        ("Lecturas con riego", f"{fmt(general['pct_regar'], 0)} %", f"{fmt(general['regar'])} de {fmt(general['lecturas'])}"),
    ])

    titulo_seccion("Decisión en cada lectura", "Cada punto es una lectura. Los azules son los momentos en que conviene regar.")
    mostrar(grafico_serie(plot, es_tiempo, True))

    conteo_dec = plot["Decision"].value_counts().rename_axis("Decision").reset_index(name="n")
    conteo_est = plot["Estado"].value_counts().rename_axis("Estado").reset_index(name="n")
    c1, c2 = st.columns(2)
    with c1:
        titulo_seccion("Regar o no regar")
        mostrar(grafico_dona(conteo_dec, "Decision", COLORES_DECISION, "Decisión"))
    with c2:
        titulo_seccion("Estado hídrico del cultivo")
        mostrar(grafico_estados(conteo_est))

    titulo_seccion("Temperatura frente a humedad del suelo", "Los puntos azules concentrados abajo muestran que el riego se activa con suelo seco, sobre todo si hace calor.")
    mostrar(grafico_dispersion(plot))

    titulo_seccion("Condiciones promedio")
    cifras([
        ("Temperatura", f"{fmt(prom_t, 1)} °C", "promedio de las lecturas"),
        ("Humedad del aire", f"{fmt(prom_a, 0)} %", "promedio de las lecturas"),
        ("Humedad del suelo", f"{fmt(prom_s, 1)} %", "promedio de las lecturas", "agua"),
    ])


def tab_zonas(res, plot, zonas):
    if res is None:
        vacio("Aún no hay predicciones por zona",
              "Pulsa «Analizar y predecir riego» para ver qué zonas necesitan agua y con qué prioridad.")
        return
    titulo_seccion("Estado de cada zona",
                   "El tubo muestra cuánta humedad tiene el suelo. La prioridad sale del porcentaje de lecturas que piden riego.")
    registros = zonas.to_dict("records")
    for i in range(0, len(registros), 3):
        cols = st.columns(3)
        for col, z in zip(cols, registros[i:i + 3]):
            with col:
                st.markdown(parcela(z), unsafe_allow_html=True)

    orden = orden_zonas(res)
    c1, c2 = st.columns(2)
    with c1:
        titulo_seccion("Decisiones por zona")
        mostrar(grafico_decisiones_zona(plot, orden))
    with c2:
        titulo_seccion("Humedad del suelo por zona")
        mostrar(grafico_humedad_zona(zonas, orden))


def tab_ahorro(res, zonas, general, litros, costo, horario):
    if res is None:
        vacio("Aún no hay cálculo de ahorro",
              "Pulsa «Analizar y predecir riego» para comparar el riego tradicional con el optimizado.")
        return
    horas_txt = ", ".join(f"{h} h" for h in horario)
    st.markdown(
        f"Con tu cronograma tradicional ibas a gastar **{fmt(general['agua_tradicional'])} L** "
        f"({fmt(general['riegos_tradicional'])} riegos a las {horas_txt}). Con la optimización de IA "
        f"gastarás **{fmt(general['agua_optimizada'])} L** ({fmt(general['riegos_ia'])} riegos)."
    )
    if general["ahorro"] < 0:
        st.info(
            "En este período el sistema riega **más** que el cronograma fijo: el horario tradicional se "
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
        ("Agua ahorrada", f"{fmt(general['ahorro'] / 1000, 2)} m³", f"{fmt(general['pct_ahorro'], 1)} % del consumo", "hoja"),
        ("Ahorro en costo", f"Bs {fmt(general['costo_ahorro'], 2)}", f"a Bs {fmt(costo, 2)} por m³"),
    ])

    orden = orden_zonas(res)
    largo = pd.concat([
        pd.DataFrame({"Zona": zonas["Zona"], "Tipo": "Riego tradicional", "Litros": zonas["Agua_tradicional"]}),
        pd.DataFrame({"Zona": zonas["Zona"], "Tipo": "Riego optimizado", "Litros": zonas["Agua_optimizada"]}),
    ])
    titulo_seccion("Consumo de agua por zona",
                   f"Cronograma tradicional frente a riego optimizado, a {fmt(litros)} L por riego.")
    mostrar(grafico_consumo(largo, orden))

    titulo_seccion("Plan de riego recomendado", "Las zonas con más lecturas en riego van primero.")
    plan = zonas.sort_values("Pct_regar", ascending=False)[
        ["Prioridad", "Zona", "Accion", "Pct_regar", "Agua_optimizada", "Recomendacion"]
    ].rename(columns={
        "Accion": "Acción", "Pct_regar": "Lecturas a regar",
        "Agua_optimizada": "Agua sugerida (L)", "Recomendacion": "Recomendación",
    })
    st.dataframe(
        plan, hide_index=True, width="stretch",
        column_config={
            "Lecturas a regar": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d%%"),
            "Agua sugerida (L)": st.column_config.NumberColumn(format="%d"),
            "Recomendación": st.column_config.TextColumn(width="large"),
        },
    )


def tab_datos(df, res, modo):
    if res is None:
        titulo_seccion("Datos cargados", "Vista previa del archivo. Las columnas de predicción aparecen después de analizar.")
        st.dataframe(df, width="stretch", hide_index=True)
        return

    titulo_seccion("Resultados lectura por lectura")
    f1, f2 = st.columns(2)
    zonas_sel = f1.multiselect("Zonas", orden_zonas(res), default=orden_zonas(res))
    dec_sel = f2.multiselect("Decisión", ["Regar", "No Regar"], default=["Regar", "No Regar"])
    vista = res[res["Zona"].isin(zonas_sel) & res["Pred_Decision"].isin(dec_sel)]
    st.dataframe(vista, width="stretch", hide_index=True)
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
                           f"Comparación con la columna {COL_DECISION} del dataset.")
            cifras([("Coincidencia con la etiqueta real", f"{fmt(acierto, 1)} %", "sobre todas las lecturas", "hoja")])
            st.dataframe(tabla, width="stretch")


# ------------------------------------------------------------ Flujo principal
contenido, nombre, litros, horario, horas_entre, costo = barra_lateral()
consulta_rapida()

if contenido is None:
    hero("Riego inteligente", "Carga un archivo con lecturas de temperatura, humedad del aire y humedad del suelo.", [], "Sin datos")
    vacio("Falta el archivo de datos",
          "Sube un .xlsx o .csv desde la barra lateral, o elige uno de los datasets del proyecto.")
    st.stop()

try:
    crudo = leer_archivo(contenido, nombre)
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

resultado = st.session_state.get("resultado")
if resultado is not None and resultado["clave"] != clave:
    resultado = None

modo = resultado["modo"] if resultado else "Sin analizar"
titulo = f"{info['cultivo']} en {info['localidad']}" if info["cultivo"] else info["titulo"]
detalle_suelo = f"Suelo {info['suelo'].lower()}. " if info["suelo"] else ""
hero(
    titulo,
    f"{detalle_suelo}{fmt(len(df))} lecturas de temperatura, humedad del aire y humedad del suelo, "
    f"de {n_zonas_real} {'invernadero' if n_zonas_real == 1 else 'invernaderos'}.",
    [f"{fmt(len(df))} lecturas", f"{n_zonas_real} {'zona' if n_zonas_real == 1 else 'zonas'}"],
    modo,
)

col_texto, col_boton = st.columns([3, 1.3], vertical_alignment="center")
with col_texto:
    st.markdown(
        "Cada lectura se clasifica como **Regar** o **No Regar** según la temperatura, "
        "la humedad del aire y la humedad del suelo."
    )
with col_boton:
    analizar = st.button("Analizar y predecir riego", type="primary", width="stretch", key="btn_analizar")

if analizar:
    with st.spinner("Analizando las condiciones de cada zona..."):
        pred, modo_pred, motivo = ejecutar_prediccion(df, info["cultivo"])
        res_nuevo = aplicar_prediccion(df, pred)
    st.session_state["resultado"] = {"clave": clave, "res": res_nuevo, "modo": modo_pred, "motivo": motivo}
    st.toast("Análisis completado")
    st.rerun()

if resultado and resultado["modo"] == "Modo simulado":
    st.caption(
        "El modelo entrenado todavía no está conectado, así que estas predicciones usan reglas de ejemplo. "
        f"Motivo técnico: {resultado['motivo']}"
    )

res = resultado["res"] if resultado else None
plot, es_tiempo = preparar_plot(res if res is not None else df)
zonas = resumen_zonas(res, litros, horario, horas_entre) if res is not None else None
general = resumen_general(res, zonas, litros, costo) if res is not None else None

t1, t2, t3, t4 = st.tabs(["Resumen", "Zonas", "Ahorro de agua", "Datos"])
with t1:
    tab_resumen(df, res, plot, es_tiempo, general, modo)
with t2:
    tab_zonas(res, plot, zonas)
with t3:
    tab_ahorro(res, zonas, general, litros, costo, horario)
with t4:
    tab_datos(df, res, modo)
