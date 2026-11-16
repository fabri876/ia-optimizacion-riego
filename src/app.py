import streamlit as st
import pandas as pd

# Configuración de la página
st.set_page_config(page_title="IA Riego | Dashboard", page_icon="🌱", layout="wide")

# Título y encabezado
st.title("🌱 Sistema Inteligente de Optimización de Riego")
st.markdown("""
Esta plataforma utiliza Inteligencia Artificial (Aprendizaje Supervisado) para analizar 
las condiciones ambientales y del suelo, clasificando si un cultivo requiere riego o no, 
con el objetivo de optimizar el recurso hídrico.
""")
st.divider()

# Crear dos columnas (Layout)
col1, col2 = st.columns([1, 2])

with col1:
    st.header("1. Cargar Datos")
    st.write("Sube el archivo Excel con las lecturas actuales de los sensores del invernadero.")
    archivo_cargado = st.file_uploader("Seleccionar archivo Excel (.xlsx)", type=["xlsx"])

with col2:
    st.header("2. Análisis y Clasificación")
    if archivo_cargado is not None:
        try:
            # Leer el archivo cargado
            df_actual = pd.read_excel(archivo_cargado)
            
            st.success("¡Archivo cargado correctamente!")
            st.write("Vista previa de los datos de entrada:")
            st.dataframe(df_actual.head()) # Muestra las primeras filas
            
            st.write("---")
            st.subheader("Ejecutar Modelo de Inteligencia Artificial")
            if st.button("Analizar Datos y Predecir Riego", type="primary"):
                with st.spinner('El modelo está procesando los datos...'):
                    # Aquí irá la conexión con predict.py más adelante
                    st.info("Simulación: El modelo clasificó 50 registros.")
                    st.warning("⚠️ **Resultado:** Se requiere riego en 12 zonas (Estado Crítico). 38 zonas en Estado Óptimo.")
                    st.success("💧 **Optimización:** Al no regar las 38 zonas óptimas, has ahorrado un 76% de agua hoy.")
                    
        except Exception as e:
            st.error(f"Error al leer el archivo: {e}")
    else:
        st.info("Esperando datos... Por favor, carga un archivo en el panel izquierdo.")