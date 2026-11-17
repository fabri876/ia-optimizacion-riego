"""Componentes visuales reutilizables del frontend."""
import html

import altair as alt
import streamlit as st

COLORES_ESTADO = {"Óptimo": "#2F8F5B", "Crítico": "#D13F3F", "Saturado": "#7A5AC8"}
COLORES_DECISION = {"Regar": "#1B73C9", "No Regar": "#9DB8A6"}
COLORES_CONSUMO = {"Riego tradicional": "#C5D3C9", "Riego optimizado": "#1B73C9"}


def fmt(n, d=0):
    """Número con formato español: 1.234,5"""
    s = f"{n:,.{d}f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".")


def _e(x):
    return html.escape(str(x))


# ---------------------------------------------------------------- HTML
def hero(titulo, subtitulo, etiquetas, modo):
    chips = "".join(f'<span class="etiqueta">{_e(e)}</span>' for e in etiquetas)
    activa = "activa" if modo == "Modelo IA" else ""
    chips += f'<span class="etiqueta {activa}">{_e(modo)}</span>'
    st.markdown(
        f'<div class="hero"><h1>{_e(titulo)}</h1>'
        f'<p>{_e(subtitulo)}</p><div class="etiquetas">{chips}</div></div>',
        unsafe_allow_html=True,
    )


def pasos(items):
    """Tres pasos en secuencia: items = [(título, texto), ...]."""
    celdas = ""
    for i, (titulo, texto) in enumerate(items, start=1):
        celdas += (
            f'<div class="paso"><div class="paso-num">{i}</div>'
            f'<div class="paso-titulo">{_e(titulo)}</div>'
            f'<div class="paso-texto">{_e(texto)}</div></div>'
        )
    st.markdown(f'<div class="pasos">{celdas}</div>', unsafe_allow_html=True)


def cifras(items):
    """items: lista de (etiqueta, valor, detalle, tono) con tono opcional: agua, alerta, hoja."""
    celdas = ""
    for it in items:
        etiqueta, valor, detalle = it[0], it[1], it[2]
        tono = it[3] if len(it) > 3 else ""
        celdas += (
            f'<div class="cifra"><div class="cifra-valor t-{tono}">{_e(valor)}</div>'
            f'<div class="cifra-etiqueta">{_e(etiqueta)}</div>'
            f'<div class="cifra-detalle">{_e(detalle)}</div></div>'
        )
    st.markdown(f'<div class="cifras">{celdas}</div>', unsafe_allow_html=True)


def titulo_seccion(titulo, sub=""):
    st.markdown(f'<div class="titulo-seccion">{_e(titulo)}</div>', unsafe_allow_html=True)
    if sub:
        st.markdown(f'<div class="sub-seccion">{_e(sub)}</div>', unsafe_allow_html=True)


def pie_grafico(texto):
    st.markdown(f'<div class="pie-grafico">{_e(texto)}</div>', unsafe_allow_html=True)


def vacio(titulo, texto):
    st.markdown(
        f'<div class="vacio"><b>{_e(titulo)}</b>{_e(texto)}</div>',
        unsafe_allow_html=True,
    )


def nota(titulo, parrafos):
    cuerpo = "".join(f"<p>{_e(p)}</p>" for p in parrafos)
    st.markdown(f'<div class="nota"><b>{_e(titulo)}</b>{cuerpo}</div>', unsafe_allow_html=True)


def veredicto(titulo, texto, tono=""):
    """Respuesta principal en una frase. tono: '' (verde), 'alerta' o 'agua'."""
    clase = f" veredicto-{tono}" if tono else ""
    st.markdown(
        f'<div class="veredicto{clase}"><div class="veredicto-titulo">{_e(titulo)}</div>'
        f'<div class="veredicto-texto">{_e(texto)}</div></div>',
        unsafe_allow_html=True,
    )


def ficha_decision(decision, estado, probabilidad, umbral):
    """Resultado de la consulta puntual: decisión grande y barra de probabilidad con su umbral."""
    color = COLORES_DECISION["Regar"] if decision == "Regar" else "#2F8F5B"
    color_estado = COLORES_ESTADO.get(estado, "#5A6E61")
    p, u = max(0, min(100, probabilidad * 100)), max(0, min(100, umbral * 100))
    st.markdown(
        f'<div class="ficha">'
        f'<div><div class="ficha-decision" style="color:{color}">{_e(decision)}</div>'
        f'<div class="ficha-estado" style="color:{color_estado}">Estado hídrico: {_e(estado)}</div></div>'
        f'<div class="ficha-prob">'
        f'<div class="ficha-prob-titulo">Probabilidad de que el cultivo necesite riego: {fmt(p, 0)} %</div>'
        f'<div class="barra-prob"><div class="barra-prob-relleno" style="width:{p:.1f}%;background:{color}"></div>'
        f'<div class="barra-prob-marca" style="left:{u:.1f}%"></div></div>'
        f'<div class="barra-prob-escala"><span>0 %</span><span>el modelo riega desde {fmt(u, 0)} %</span><span>100 %</span></div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )


def tabla_estados_html(filas):
    """Glosario de estados hídricos con números reales del dataset."""
    cuerpo = ""
    for f in filas:
        color = COLORES_ESTADO.get(f["Estado"], "#5A6E61")
        cuerpo += (
            f'<tr><td><span class="chip-estado" style="background:{color}">{_e(f["Estado"])}</span></td>'
            f'<td>{_e(f["Significado"])}</td>'
            f'<td class="num">{fmt(f["Lecturas"])}</td>'
            f'<td class="num">{fmt(f["Pct"], 1)} %</td>'
            f'<td class="num">{fmt(f["Hum_suelo"], 1)} %</td>'
            f'<td class="num">{fmt(f["Pct_regar"], 0)} %</td></tr>'
        )
    st.markdown(
        '<div class="tabla-scroll"><table class="tabla-datos"><thead><tr>'
        '<th>Estado</th><th>Qué significa</th><th class="num">Lecturas</th><th class="num">% del total</th>'
        '<th class="num">Humedad del suelo promedio</th><th class="num">Modelo indica regar</th>'
        f'</tr></thead><tbody>{cuerpo}</tbody></table></div>',
        unsafe_allow_html=True,
    )


def tabla_comparativa(filas, cabecera=("", "Tu cronograma", "Según el modelo", "Diferencia")):
    """filas: lista de (concepto, valor_plan, valor_modelo, diferencia) ya formateados como texto."""
    ths = "".join(f'<th class="{"num" if i else ""}">{_e(c)}</th>' for i, c in enumerate(cabecera))
    cuerpo = ""
    for concepto, a, b, d in filas:
        cuerpo += (
            f'<tr><td>{_e(concepto)}</td><td class="num">{_e(a)}</td>'
            f'<td class="num">{_e(b)}</td><td class="num">{_e(d)}</td></tr>'
        )
    st.markdown(
        f'<div class="tabla-scroll"><table class="tabla-datos"><thead><tr>{ths}</tr></thead>'
        f'<tbody>{cuerpo}</tbody></table></div>',
        unsafe_allow_html=True,
    )


def parcela(z):
    """Tarjeta de una zona. El tubo de la izquierda se llena según la humedad promedio del suelo."""
    color = COLORES_ESTADO.get(z["Estado"], "#9DB8A6")
    prio = {"Alta": "alta", "Media": "media", "Baja": "baja"}[z["Prioridad"]]
    nivel = max(0, min(100, z["Hum_suelo"]))
    dif = z["Ahorro"]
    texto_agua = (f"ahorra {fmt(dif)} L" if dif >= 0 else f"gasta {fmt(-dif)} L más")
    return (
        f'<div class="parcela">'
        f'<div class="tubo"><div class="relleno" style="height:{nivel:.0f}%;background:{color}"></div></div>'
        f'<div class="parcela-cuerpo">'
        f'<div class="parcela-cab"><span class="parcela-nombre">{_e(z["Zona"])}</span>'
        f'<span class="prio prio-{prio}">{fmt(z["Pct_regar"], 0)} % de lecturas piden riego</span></div>'
        f'<div class="parcela-accion">Necesidad de riego {z["Prioridad"].lower()}</div>'
        f'<div class="parcela-estado" style="color:{color}">Estado hídrico más frecuente: {_e(z["Estado"])}</div>'
        f'<div class="parcela-datos">'
        f'<div><b>{fmt(z["Hum_suelo"], 1)} %</b><span>humedad del suelo</span></div>'
        f'<div><b>{fmt(z["Temperatura"], 1)} °C</b><span>temperatura</span></div>'
        f'<div><b>{fmt(z["Hum_ambiente"], 0)} %</b><span>humedad del aire</span></div></div>'
        f'<div class="parcela-pie">Con el cronograma tradicional: {fmt(z["Riegos_tradicional"])} riegos. '
        f'Con el modelo: {fmt(z["Riegos_IA"])} riegos ({texto_agua}).</div>'
        f'</div></div>'
    )


def tanque(usada, ahorrada, pct_ahorro):
    st.markdown(
        f'<div class="gran-cifra">{fmt(ahorrada)} L</div>'
        f'<div class="gran-texto">de agua que no se gastan al regar solo cuando hace falta '
        f'({fmt(pct_ahorro, 1)} % menos que con el cronograma tradicional).</div>'
        f'<div class="tanque-barra">'
        f'<div class="tanque-usado" style="width:{100 - pct_ahorro:.2f}%"></div>'
        f'<div class="tanque-ahorrado" style="width:{pct_ahorro:.2f}%"></div></div>'
        f'<div class="tanque-leyenda">'
        f'<div><i class="punto usado"></i>Agua usada con riego optimizado: {fmt(usada)} L</div>'
        f'<div><i class="punto ahorrado"></i>Agua ahorrada: {fmt(ahorrada)} L</div></div>',
        unsafe_allow_html=True,
    )


# ------------------------------------------------------------- Gráficos
def _estilo(chart, alto=300):
    return (
        chart.properties(height=alto, background="transparent")
        .configure_view(strokeWidth=0)
        .configure_axis(
            labelColor="#5A6E61", titleColor="#12261C", gridColor="#E1EBE4",
            domainColor="#C3D4C8", labelFont="Public Sans", titleFont="Public Sans",
            titleFontWeight=600,
        )
        .configure_legend(
            orient="bottom", labelColor="#12261C", titleColor="#12261C",
            labelFont="Public Sans", titleFont="Public Sans",
        )
    )


def _color(campo, mapa, titulo):
    return alt.Color(
        f"{campo}:N",
        scale=alt.Scale(domain=list(mapa), range=list(mapa.values())),
        legend=alt.Legend(title=titulo),
    )


def mostrar(chart):
    st.altair_chart(chart, width="stretch")


def grafico_meses(tabla):
    """Barras apiladas por mes con el total encima: la suma de los meses es el total del archivo."""
    largo = tabla.melt(id_vars=["Mes", "Etiqueta", "Total"], value_vars=["Regar", "No Regar"],
                       var_name="Decision", value_name="Lecturas")
    orden = list(tabla["Etiqueta"])
    barras = alt.Chart(largo).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
        x=alt.X("Etiqueta:N", sort=orden, title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("Lecturas:Q", title="Lecturas"),
        color=_color("Decision", COLORES_DECISION, "Decisión del modelo"),
        tooltip=["Etiqueta:N", "Decision:N", alt.Tooltip("Lecturas:Q", format=",.0f")],
    )
    totales = alt.Chart(tabla).mark_text(dy=-8, fontWeight=600, color="#12261C").encode(
        x=alt.X("Etiqueta:N", sort=orden),
        y=alt.Y("Total:Q"),
        text=alt.Text("Total:Q", format=",.0f"),
    )
    return _estilo(alt.layer(barras, totales), 300)


def grafico_regar_rango(tabla, titulo_x):
    """% de lecturas donde el modelo indica regar, por tramos de una variable. La línea marca el 50 %."""
    orden = list(tabla["Rango"])
    barras = alt.Chart(tabla).mark_bar(color="#1B73C9", cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
        x=alt.X("Rango:N", sort=orden, title=titulo_x, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("Pct_regar:Q", title="% de lecturas con riego", scale=alt.Scale(domain=[0, 100])),
        tooltip=["Rango:N", alt.Tooltip("Lecturas:Q", format=",.0f"),
                 alt.Tooltip("Pct_regar:Q", format=".0f", title="% con riego")],
    )
    mitad = alt.Chart(alt.Data(values=[{"y": 50}])).mark_rule(
        color="#12261C", strokeDash=[4, 4]).encode(y="y:Q")
    return _estilo(alt.layer(barras, mitad), 260)


def grafico_horas(horas):
    """% de días del mes en que el modelo indicó regar a cada hora. Las líneas ámbar son las horas del cronograma."""
    escala = alt.Scale(domain=[-0.5, 23.5])
    barras = alt.Chart(horas).mark_bar(size=14, color="#1B73C9", cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
        x=alt.X("Hora:Q", scale=escala, axis=alt.Axis(values=list(range(24)), title="Hora del día", labelAngle=0)),
        y=alt.Y("Pct:Q", title="% de los días con riego", scale=alt.Scale(domain=[0, 100])),
        tooltip=[alt.Tooltip("Hora:Q", title="Hora"), alt.Tooltip("Dias:Q", title="Días con riego"),
                 alt.Tooltip("Pct:Q", format=".0f", title="% de los días")],
    )
    plan = horas[horas["En_plan"]]
    reglas = alt.Chart(plan).mark_rule(color="#E39A1B", strokeWidth=3, strokeDash=[5, 3]).encode(
        x=alt.X("Hora:Q", scale=escala))
    return _estilo(alt.layer(barras, reglas), 280)


def grafico_decisiones_zona(p, orden):
    c = alt.Chart(p[["Zona", "Decision"]]).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
        x=alt.X("Zona:N", sort=orden, title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("count()", title="Lecturas"),
        color=_color("Decision", COLORES_DECISION, "Decisión del modelo"),
        tooltip=["Zona:N", "Decision:N", alt.Tooltip("count()", title="Lecturas")],
    )
    return _estilo(c, 280)


def grafico_humedad_zona(zonas, orden):
    c = alt.Chart(zonas).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
        x=alt.X("Zona:N", sort=orden, title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("Hum_suelo:Q", title="Humedad del suelo promedio (%)"),
        color=_color("Estado", COLORES_ESTADO, "Estado hídrico"),
        tooltip=["Zona:N", alt.Tooltip("Hum_suelo:Q", format=".1f", title="Humedad del suelo"), "Estado:N"],
    )
    return _estilo(c, 280)


def grafico_consumo(largo, orden):
    c = alt.Chart(largo).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
        x=alt.X("Zona:N", sort=orden, title=None, axis=alt.Axis(labelAngle=0)),
        xOffset="Tipo:N",
        y=alt.Y("Litros:Q", title="Agua (litros)"),
        color=_color("Tipo", COLORES_CONSUMO, "Tipo de riego"),
        tooltip=["Zona:N", "Tipo:N", alt.Tooltip("Litros:Q", format=",.0f")],
    )
    return _estilo(c, 300)
