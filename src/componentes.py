"""Componentes visuales reutilizables del frontend."""
import html
import math

import altair as alt
import streamlit as st

COLORES_ESTADO = {"Óptimo": "#2F8F5B", "Crítico": "#D13F3F", "Saturado": "#7A5AC8"}
COLORES_DECISION = {"Regar": "#1B73C9", "No Regar": "#9DB8A6"}
COLORES_CONSUMO = {"Riego tradicional": "#C5D3C9", "Riego optimizado": "#1B73C9"}


def fmt(n, d=0):
    """Número con formato español: 1.234,5"""
    s = f"{n:,.{d}f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".")


# ---------------------------------------------------------------- HTML
def hero(titulo, subtitulo, etiquetas, modo):
    chips = "".join(f'<span class="etiqueta">{html.escape(e)}</span>' for e in etiquetas)
    activa = "activa" if modo == "Modelo IA" else ""
    chips += f'<span class="etiqueta {activa}">{html.escape(modo)}</span>'
    st.markdown(
        f'<div class="hero"><h1>{html.escape(titulo)}</h1>'
        f'<p>{html.escape(subtitulo)}</p><div class="etiquetas">{chips}</div></div>',
        unsafe_allow_html=True,
    )


def cifras(items):
    """items: lista de (etiqueta, valor, detalle, tono) con tono opcional: agua, alerta, hoja."""
    celdas = ""
    for it in items:
        etiqueta, valor, detalle = it[0], it[1], it[2]
        tono = it[3] if len(it) > 3 else ""
        celdas += (
            f'<div class="cifra"><div class="cifra-valor t-{tono}">{html.escape(str(valor))}</div>'
            f'<div class="cifra-etiqueta">{html.escape(etiqueta)}</div>'
            f'<div class="cifra-detalle">{html.escape(detalle)}</div></div>'
        )
    st.markdown(f'<div class="cifras">{celdas}</div>', unsafe_allow_html=True)


def titulo_seccion(titulo, sub=""):
    st.markdown(f'<div class="titulo-seccion">{html.escape(titulo)}</div>', unsafe_allow_html=True)
    if sub:
        st.markdown(f'<div class="sub-seccion">{html.escape(sub)}</div>', unsafe_allow_html=True)


def vacio(titulo, texto):
    st.markdown(
        f'<div class="vacio"><b>{html.escape(titulo)}</b>{html.escape(texto)}</div>',
        unsafe_allow_html=True,
    )


def parcela(z):
    """Tarjeta de una zona. El tubo de la izquierda se llena según la humedad del suelo."""
    color = COLORES_ESTADO.get(z["Estado"], "#9DB8A6")
    prio = {"Alta": "alta", "Media": "media", "Baja": "baja"}[z["Prioridad"]]
    nivel = max(0, min(100, z["Hum_suelo"]))
    return (
        f'<div class="parcela">'
        f'<div class="tubo"><div class="relleno" style="height:{nivel:.0f}%;background:{color}"></div></div>'
        f'<div class="parcela-cuerpo">'
        f'<div class="parcela-cab"><span class="parcela-nombre">{html.escape(str(z["Zona"]))}</span>'
        f'<span class="prio prio-{prio}">Prioridad {z["Prioridad"].lower()}</span></div>'
        f'<div class="parcela-accion">{html.escape(z["Accion"])}</div>'
        f'<div class="parcela-estado" style="color:{color}">Estado hídrico: {html.escape(z["Estado"])}</div>'
        f'<div class="parcela-datos">'
        f'<div><b>{fmt(z["Hum_suelo"], 1)} %</b><span>humedad del suelo</span></div>'
        f'<div><b>{fmt(z["Temperatura"], 1)} °C</b><span>temperatura</span></div>'
        f'<div><b>{fmt(z["Hum_ambiente"], 0)} %</b><span>humedad del aire</span></div></div>'
        f'<div class="parcela-pie">{fmt(z["Pct_regar"], 0)} % de las lecturas piden riego. '
        f'Ahorro estimado: {fmt(z["Ahorro"])} L.</div>'
        f'</div></div>'
    )


def tanque(usada, ahorrada, pct_ahorro):
    st.markdown(
        f'<div class="gran-cifra">{fmt(ahorrada)} L</div>'
        f'<div class="gran-texto">de agua que no se gastan al regar solo cuando hace falta '
        f'({fmt(pct_ahorro, 1)} % menos que regar en todas las lecturas).</div>'
        f'<div class="tanque-barra">'
        f'<div class="tanque-usado" style="width:{100 - pct_ahorro:.2f}%"></div>'
        f'<div class="tanque-ahorrado" style="width:{pct_ahorro:.2f}%"></div></div>'
        f'<div class="tanque-leyenda">'
        f'<div><i class="punto usado"></i>Agua usada con riego optimizado: {fmt(usada)} L</div>'
        f'<div><i class="punto ahorrado"></i>Agua ahorrada: {fmt(ahorrada)} L</div></div>',
        unsafe_allow_html=True,
    )


# ------------------------------------------------------------- Gráficos
def _muestra(p, n=4000):
    if len(p) <= n:
        return p
    return p.iloc[:: math.ceil(len(p) / n)]


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


def grafico_serie(p, es_tiempo, con_decision):
    p = _muestra(p)
    x = alt.X("Eje:T", title="Fecha") if es_tiempo else alt.X("Eje:Q", title="Número de lectura")
    y = alt.Y("Hum_suelo:Q", title="Humedad del suelo (%)", scale=alt.Scale(zero=False))
    linea = alt.Chart(p).mark_line(color="#9DB8A6", strokeWidth=1.5).encode(x=x, y=y)
    if not con_decision:
        return _estilo(linea, 320)
    tooltip = [
        "Zona:N",
        alt.Tooltip("Hum_suelo:Q", format=".1f", title="Humedad del suelo"),
        alt.Tooltip("Temperatura:Q", format=".1f", title="Temperatura"),
        "Decision:N",
    ]
    puntos = alt.Chart(p).mark_circle(size=48, opacity=0.8).encode(
        x=x, y=y, color=_color("Decision", COLORES_DECISION, "Decisión"), tooltip=tooltip
    )
    return _estilo(alt.layer(linea, puntos), 320)


def grafico_histograma(p, col, titulo, color):
    c = alt.Chart(p).mark_bar(color=color, opacity=0.9, cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
        x=alt.X(f"{col}:Q", bin=alt.Bin(maxbins=22), title=titulo),
        y=alt.Y("count()", title="Lecturas"),
    )
    return _estilo(c, 240)


def grafico_dona(conteos, campo, mapa, titulo):
    c = alt.Chart(conteos).mark_arc(innerRadius=62, outerRadius=105, cornerRadius=3).encode(
        theta=alt.Theta("n:Q"),
        color=_color(campo, mapa, titulo),
        tooltip=[f"{campo}:N", alt.Tooltip("n:Q", title="Lecturas")],
    )
    return _estilo(c, 260)


def grafico_estados(conteos):
    c = alt.Chart(conteos).mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4).encode(
        y=alt.Y("Estado:N", sort=list(COLORES_ESTADO), title=None),
        x=alt.X("n:Q", title="Lecturas"),
        color=_color("Estado", COLORES_ESTADO, "Estado hídrico"),
        tooltip=["Estado:N", alt.Tooltip("n:Q", title="Lecturas")],
    )
    return _estilo(c, 260)


def grafico_dispersion(p):
    p = _muestra(p)
    c = alt.Chart(p).mark_circle(size=46, opacity=0.65).encode(
        x=alt.X("Temperatura:Q", title="Temperatura (°C)", scale=alt.Scale(zero=False)),
        y=alt.Y("Hum_suelo:Q", title="Humedad del suelo (%)", scale=alt.Scale(zero=False)),
        color=_color("Decision", COLORES_DECISION, "Decisión"),
        tooltip=[
            "Zona:N",
            alt.Tooltip("Temperatura:Q", format=".1f"),
            alt.Tooltip("Hum_suelo:Q", format=".1f", title="Humedad del suelo"),
            "Decision:N",
        ],
    )
    return _estilo(c, 300)


def grafico_decisiones_zona(p, orden):
    c = alt.Chart(p[["Zona", "Decision"]]).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
        x=alt.X("Zona:N", sort=orden, title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("count()", title="Lecturas"),
        color=_color("Decision", COLORES_DECISION, "Decisión"),
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
