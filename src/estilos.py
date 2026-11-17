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
.sub-seccion { font-size: .88rem; color: var(--suave); margin-bottom: 10px; max-width: 70ch; }

.vacio { border: 1.5px dashed #B3CBBA; border-radius: 10px; padding: 26px 28px; color: var(--suave); margin: 10px 0 18px; }
.vacio b { display: block; font-family: 'Bricolage Grotesque', sans-serif; font-size: 1.15rem; color: var(--ink); margin-bottom: 4px; }

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
.parcela-accion { font-family: 'Bricolage Grotesque', sans-serif; font-weight: 700; font-size: 1.45rem; letter-spacing: -0.01em; color: var(--ink); margin-top: 2px; }
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
