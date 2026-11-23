# 🌱 Sistema Inteligente de Optimización de Riego

Este proyecto es un prototipo de software basado en **Inteligencia Artificial (Aprendizaje Supervisado y Clasificación)**. Analiza datos históricos y actuales de humedad y temperatura para clasificar el estado hídrico de un invernadero y optimizar el uso del agua de riego.

## 🛠️ Requisitos Previos
Antes de empezar, asegúrate de tener instalado en tu computadora:
- [Python 3.8 o superior](https://www.python.org/downloads/)
- [Git](https://git-scm.com/downloads)

---

## 🚀 Guía de Instalación y Ejecución Local

Sigue estos pasos para configurar el proyecto en tu máquina local:

### 1. Clonar el repositorio
Abre tu terminal y ejecuta el siguiente comando para descargar el código:
```bash
git clone https://github.com/fabri876/ia-optimizacion-riego.git
cd ia-optimizacion-riego

2. Crear un Entorno Virtual
Es obligatorio usar un entorno virtual para no causar conflictos con otras librerías de tu computadora.

Bash
python -m venv venv
3. Activar el Entorno Virtual
Dependiendo de la terminal y sistema operativo que uses, el comando varía:

En Windows (Git Bash):

Bash
source venv/Scripts/activate
En Windows (CMD o PowerShell):

Bash
.\venv\Scripts\activate
En Mac / Linux:

Bash
source venv/bin/activate
(Sabrás que funcionó si ves el prefijo (venv) al inicio de tu línea de comandos).

4. Instalar las Dependencias
Con el entorno virtual activado, instala todas las librerías necesarias (Pandas, Scikit-Learn, Streamlit, etc.) ejecutando:

Bash
pip install -r requirements.txt
5. Ejecutar la Aplicación (Frontend)
Para levantar la interfaz gráfica y probar el prototipo en tu navegador, ejecuta:

Bash
streamlit run src/app.py
Esto abrirá automáticamente una pestaña en tu navegador en la dirección http://localhost:8501.

📁 Estructura del Proyecto
El código está organizado bajo un patrón lógico para facilitar el trabajo en equipo:

data/: Contiene el archivo Excel con el historial de riego (Dataset).

model/: Carpeta donde se guardará el modelo de IA ya entrenado (.pkl).

src/:

app.py: Interfaz gráfica (Frontend desarrollado con Streamlit).

train.py: Script para entrenar la Inteligencia Artificial.

predict.py: Script (Backend) que conecta el modelo con la interfaz para hacer predicciones.

requirements.txt: Lista oficial de librerías del proyecto.

Nota para el equipo: Recuerden siempre activar el entorno virtual (venv) antes de ejecutar cualquier comando de Python o de instalar nuevas librerías.

---

## 🧠 Modelo de IA

El modelo ya viene entrenado en `model/modelo_riego.pkl` (las métricas están en `model/modelo_riego.json`). Para volver a entrenarlo:

```bash
python src/train.py
```

Compara Árbol de Decisión, Random Forest, Regresión Logística y Perceptrón Multicapa, elige el de mejor F1 en la clase «Regar» y ajusta el umbral para detectar al menos el 95 % de los estados críticos. Los hiperparámetros se eligen con validación cruzada agrupada por día. Resultado actual sobre el conjunto de prueba: **Random Forest**, umbral 0,28, exactitud 0,861, exhaustividad «Regar» 0,972 (21 falsos negativos de 747).

Los datos de `data/` son **sintéticos** (ver la hoja `Parametros` de cada Excel). `python src/evaluar.py` genera en `reports/` el aporte de los atributos, las métricas por invernadero, el ahorro estimado sobre todos los días de prueba y las figuras del informe.

| Archivo | Qué hace |
|---|---|
| `src/preparacion.py` | Limpieza y atributos del modelo (media móvil de 24 h, cultivo, hora cíclica, DPV en kPa) |
| `src/train.py` | Entrenamiento con validación cruzada, selección del modelo y evaluación |
| `src/evaluar.py` | Métricas por invernadero, ahorro sobre los días de prueba y figuras |
| `src/predict.py` | `predecir(df)` para la interfaz y `predecir_condicion(...)` para la consulta rápida |
| `src/optimizacion.py` | Litros del cronograma tradicional frente a los del sistema |
