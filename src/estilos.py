"""Estilos del frontend (CSS inyectado en Streamlit)."""
import streamlit as st

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700;12..96,800&family=Public+Sans:wght@400;500;600&display=swap');

:root {
  --ink: #12261C;
  --hoja: #2F8F5B;
  --agua: #1B73C9;
  --ambar: #E39A1B;
  --alerta: #D13F3F;
  --suave: #5A6E61;
  --borde: #D5E2D9;
}

.stApp { font-family: 'Public Sans', system-ui, sans-serif; }
.block-container { padding-top: 1.6rem; padding-bottom: 3rem; max-width: 1240px; }
#MainMenu, footer { visibility: hidden; }

/* ---------- Barra lateral ---------- */
section[data-testid="stSidebar"] { border-right: 1px solid var(--borde); }
.marca { margin: 4px 0 14px; }
.marca-nombre { font-family: 'Bricolage Grotesque', sans-serif; font-weight: 800; font-size: 1.45rem; letter-spacing: -0.02em; color: var(--ink); line-height: 1.1; }
.marca-sub { font-size: .82rem; color: var(--suave); margin-top: 2px; }

/* ---------- Encabezado ---------- */
.hero { background: var(--ink); color: #F4F8F5; border-radius: 4px; padding: 30px 36px 26px; margin-bottom: 18px; border-bottom: 6px solid var(--hoja); }
.hero h1 { font-family: 'Bricolage Grotesque', sans-serif; font-weight: 800; font-size: 2.7rem; letter-spacing: -0.03em; line-height: 1.05; color: #FFFFFF; margin: 0 0 10px; padding: 0; }
.hero p { color: #C9DACF; font-size: 1rem; max-width: 62ch; margin: 0; line-height: 1.5; }
.etiquetas { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 18px; }
.etiqueta { border: 1px solid #4F7360; color: #DCEBE1; padding: 4px 12px; border-radius: 999px; font-size: .82rem; }
.etiqueta.activa { background: var(--hoja); border-color: var(--hoja); color: #FFFFFF; font-weight: 600; }

/* ---------- Cómo funciona (tres pasos en secuencia) ---------- */
.pasos { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); background: #FFFFFF; border: 1px solid var(--borde); border-radius: 10px; overflow: hidden; margin: 0 0 8px; }
.paso { padding: 16px 20px; border-left: 1px solid var(--borde); }
.paso:first-child { border-left: none; }
.paso-num { font-family: 'Bricolage Grotesque', sans-serif; font-weight: 800; font-size: 1.7rem; line-height: 1; color: var(--hoja); }
.paso-titulo { font-weight: 600; margin: 4px 0 2px; color: var(--ink); }
.paso-texto { font-size: .86rem; color: var(--suave); line-height: 1.45; }

/* ---------- Cifras clave ---------- */
.cifras { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); border-top: 2px solid var(--ink); margin: 8px 0 14px; }
.cifra { padding: 14px 18px 10px; border-left: 1px solid var(--borde); }
.cifra:first-child { border-left: none; padding-left: 0; }
.cifra-valor { font-family: 'Bricolage Grotesque', sans-serif; font-weight: 700; font-size: 2.15rem; line-height: 1.1; letter-spacing: -0.02em; color: var(--ink); }
.cifra-etiqueta { font-size: .92rem; font-weight: 600; margin-top: 4px; color: var(--ink); }
.cifra-detalle { font-size: .82rem; color: var(--suave); margin-top: 1px; }
.t-agua { color: var(--agua); }
.t-alerta { color: var(--alerta); }
.t-hoja { color: var(--hoja); }

/* ---------- Secciones ---------- */
.titulo-seccion { font-family: 'Bricolage Grotesque', sans-serif; font-weight: 700; font-size: 1.3rem; letter-spacing: -0.01em; color: var(--ink); margin: 26px 0 2px; }
.sub-seccion { font-size: .88rem; color: var(--suave); margin-bottom: 10px; max-width: 74ch; line-height: 1.5; }
.pie-grafico { font-size: .84rem; color: var(--suave); margin: -4px 0 8px; max-width: 80ch; line-height: 1.5; }

.vacio { border: 1.5px dashed #B3CBBA; border-radius: 10px; padding: 26px 28px; color: var(--suave); margin: 10px 0 18px; }
.vacio b { display: block; font-family: 'Bricolage Grotesque', sans-serif; font-size: 1.15rem; color: var(--ink); margin-bottom: 4px; }

/* ---------- Veredicto (respuesta principal del simulador) ---------- */
.veredicto { border: 1px solid var(--borde); border-left: 6px solid var(--hoja); background: #EFF7F2; border-radius: 4px 12px 12px 4px; padding: 16px 22px; margin: 8px 0 14px; }
.veredicto-alerta { border-left-color: var(--alerta); background: #FDF1F1; }
.veredicto-agua { border-left-color: var(--agua); background: #EEF5FC; }
.veredicto-titulo { font-family: 'Bricolage Grotesque', sans-serif; font-weight: 700; font-size: 1.4rem; letter-spacing: -0.01em; color: var(--ink); }
.veredicto-texto { margin-top: 4px; color: var(--ink); max-width: 82ch; line-height: 1.5; }

/* ---------- Ficha de decisión (condición puntual) ---------- */
.ficha { display: flex; gap: 28px; align-items: center; flex-wrap: wrap; background: #FFFFFF; border: 1px solid var(--borde); border-radius: 14px; padding: 20px 26px; margin: 10px 0 6px; }
.ficha-resultado { min-width: 165px; }
.ficha-etiqueta { font-size: .78rem; color: var(--suave); font-weight: 600; text-transform: uppercase; letter-spacing: .04em; }
.ficha-decision { font-family: 'Bricolage Grotesque', sans-serif; font-weight: 800; font-size: 2.8rem; letter-spacing: -0.03em; line-height: 1; }
.ficha-estado { font-size: .95rem; font-weight: 600; margin-top: 6px; }
.ficha-prob { flex: 1; min-width: 260px; }
.ficha-metricas { display: flex; gap: 28px; align-items: baseline; }
.ficha-metricas div { display: flex; gap: 7px; align-items: baseline; }
.ficha-metricas span { color: var(--suave); font-size: .83rem; }
.ficha-metricas b { color: var(--ink); font-size: 1.2rem; }
.barra-prob { position: relative; height: 14px; background: #E3ECE6; border-radius: 7px; margin: 12px 0 4px; }
.barra-prob-relleno { height: 100%; border-radius: 7px; }
.barra-prob-marca { position: absolute; top: -5px; width: 2px; height: 24px; background: var(--ink); }
.barra-prob-escala { display: flex; justify-content: space-between; font-size: .74rem; color: var(--suave); }
.ficha-nota { font-size: .84rem; color: var(--suave); margin-top: 6px; }
.leyenda-colores { display: flex; gap: 16px; flex-wrap: wrap; align-items: center; padding: 9px 14px; border: 1px solid var(--borde); border-radius: 8px; color: var(--suave); font-size: .82rem; margin-bottom: 12px; }
.leyenda-colores b { color: var(--ink); margin-right: 4px; }
.leyenda-punto { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 5px; }
.leyenda-punto.critico { background: var(--alerta); }.leyenda-punto.optimo { background: var(--hoja); }.leyenda-punto.saturado { background: #7A5AC8; }.leyenda-punto.riego { background: var(--agua); }

/* ---------- Tablas de datos ---------- */
.tabla-scroll { overflow-x: auto; margin: 6px 0 10px; }
.tabla-datos { width: 100%; border-collapse: collapse; font-size: .9rem; background: #FFFFFF; border: 1px solid var(--borde); }
.tabla-datos th { text-align: left; font-weight: 600; color: var(--suave); padding: 10px 14px; border-bottom: 1px solid var(--borde); font-size: .82rem; }
.tabla-datos td { padding: 10px 14px; border-bottom: 1px solid #EAF1EC; vertical-align: top; color: var(--ink); }
.tabla-datos tr:last-child td { border-bottom: none; }
.tabla-datos .num { text-align: right; white-space: nowrap; }
.tabla-datos .sub { color: var(--suave); font-size: .82rem; }
.chip-estado { display: inline-block; padding: 2px 10px; border-radius: 6px; font-weight: 600; font-size: .82rem; color: #FFFFFF; }

/* ---------- Nota de alcance ---------- */
.nota { border: 1px solid var(--borde); border-left: 4px solid var(--ambar); background: #FFFBF2; border-radius: 4px 10px 10px 4px; padding: 14px 18px; margin: 14px 0; }
.nota b { display: block; color: var(--ink); margin-bottom: 4px; }
.nota p { margin: 4px 0; color: var(--ink); font-size: .9rem; line-height: 1.5; }

/* ---------- Parcelas (una por zona) ---------- */
.parcela { display: flex; gap: 16px; background: #FFFFFF; border: 1px solid var(--borde); border-radius: 14px; padding: 16px 18px; margin-bottom: 14px; }
.tubo { width: 16px; min-height: 124px; background: #E3ECE6; border-radius: 8px; position: relative; overflow: hidden; flex: none; align-self: stretch; }
.relleno { position: absolute; left: 0; right: 0; bottom: 0; }
.parcela-cuerpo { flex: 1; min-width: 0; }
.parcela-cab { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.parcela-nombre { font-weight: 600; color: var(--suave); font-size: .92rem; }
.prio { font-size: .76rem; font-weight: 600; padding: 3px 9px; border-radius: 6px; }
.prio-alta { background: #FBE4E4; color: #8E2222; }
.prio-media { background: #FCEFD3; color: #7A5200; }
.prio-baja { background: #E1F1E7; color: #1F6A41; }
.parcela-accion { font-family: 'Bricolage Grotesque', sans-serif; font-weight: 700; font-size: 1.35rem; letter-spacing: -0.01em; color: var(--ink); margin-top: 2px; }
.parcela-estado { font-size: .84rem; font-weight: 600; }
.parcela-datos { display: flex; gap: 18px; margin-top: 10px; flex-wrap: wrap; }
.parcela-datos b { display: block; font-size: 1rem; color: var(--ink); }
.parcela-datos span { font-size: .76rem; color: var(--suave); }
.parcela-pie { font-size: .82rem; color: var(--suave); margin-top: 10px; border-top: 1px solid var(--borde); padding-top: 8px; }

/* ---------- Tanque de agua ---------- */
.gran-cifra { font-family: 'Bricolage Grotesque', sans-serif; font-weight: 800; font-size: 3.8rem; letter-spacing: -0.03em; line-height: 1; color: var(--agua); }
.gran-texto { font-size: 1rem; color: var(--ink); margin: 6px 0 14px; max-width: 60ch; }
.tanque-barra { display: flex; height: 46px; border: 2px solid var(--ink); border-radius: 8px; overflow: hidden; background: #FFFFFF; }
.tanque-usado { background: var(--agua); }
.tanque-ahorrado { background: repeating-linear-gradient(135deg, #FFFFFF 0 7px, #D6E6F5 7px 14px); }
.tanque-leyenda { display: flex; gap: 26px; flex-wrap: wrap; margin-top: 10px; font-size: .88rem; color: var(--ink); }
.punto { display: inline-block; width: 12px; height: 12px; border-radius: 3px; margin-right: 6px; vertical-align: -1px; border: 1px solid var(--ink); }
.punto.usado { background: var(--agua); }
.punto.ahorrado { background: #D6E6F5; }

/* ---------- Pestañas y botón ---------- */
.stTabs [data-baseweb="tab-list"] { gap: 4px; border-bottom: 1px solid var(--borde); }
.stTabs [data-baseweb="tab"] { font-weight: 600; padding: 10px 18px; }
button[kind="primary"], button[data-testid="stBaseButton-primary"] { font-weight: 600; padding: 0.65rem 1rem; border-radius: 8px; }
</style>
"""


def inyectar_estilos():
    st.markdown(CSS, unsafe_allow_html=True)
