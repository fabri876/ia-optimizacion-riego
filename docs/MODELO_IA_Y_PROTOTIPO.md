# Modelo de IA y desarrollo del prototipo

Este documento describe la resolución implementada para el sistema de optimización de riego y permite reproducir sus resultados. Corresponde a las secciones de Preparación de los Datos, Modelado, Evaluación, Especificaciones de Tecnologías y Desarrollo del Prototipo del Capítulo V del informe.

## Resolución del problema aplicando la técnica

El problema se resolvió mediante **aprendizaje supervisado de clasificación**. A partir de lecturas históricas etiquetadas como `Regar` o `No Regar`, el sistema aprende a decidir si cada condición nueva requiere riego. Además presenta un estado hídrico (`Óptimo`, `Crítico` o `Saturado`) para facilitar la interpretación de la decisión.

### Preparación de los datos

El entrenamiento consume `data/datasets_combinados.csv`, construido desde los archivos Excel de los cultivos. **Los datos son sintéticos**: se generaron por simulación (clima del invernadero, balance hídrico del suelo, riegos irregulares, ruido de sensor y faltantes), según la hoja `Parametros` de cada Excel; no son mediciones de campo. Se procesaron 21 936 registros iniciales y se conservaron 20 820 registros válidos; se descartaron 1 116 filas con valores nulos. La limpieza convierte las entradas a valores numéricos, valida los rangos físicos, elimina duplicados y conserva solo etiquetas válidas.

Las variables de entrada originales son:

| Variable | Uso |
| --- | --- |
| `Temperatura_C` | Temperatura del aire en grados Celsius. |
| `Humedad_ambiente_%` | Humedad relativa del ambiente. |
| `Humedad_suelo_%` | Humedad volumétrica del suelo. |
| `Fecha_Hora` y `Cultivo` | Contexto temporal y tipo de cultivo cuando están disponibles. |

Durante la preparación se derivan ocho atributos: las tres mediciones base, media móvil de humedad del suelo de 24 horas, hora en representación cíclica seno/coseno, déficit de presión de vapor en kPa (DPV = es(T)·(1 − HR/100)) y cultivo. No se usan el mes ni el día de la semana: cada invernadero cubre meses distintos, así que el mes funcionaba como identificador del invernadero. Los datos se separan en 14 475 registros de entrenamiento, 3 156 de validación y 3 189 de prueba (3 360 antes de quitar nulos), respetando la columna `Particion` (días completos asignados al azar).

### Modelado y selección

`src/train.py` compara cuatro clasificadores: Árbol de Decisión, Random Forest, Regresión Logística y Perceptrón Multicapa. Para cada uno busca hiperparámetros con validación cruzada de 5 pliegues agrupada por día (`GroupKFold`) sobre entrenamiento; en los modelos lineales el cultivo va en one-hot. La selección se hace por el mejor F1 de la clase positiva `Regar` sobre validación. El modelo elegido fue **Random Forest** (max_depth = 16, min_samples_leaf = 5) con F1 de 0.8203, superior a Árbol de Decisión (0.8056), Perceptrón Multicapa (0.7968) y Regresión Logística (0.7839).

Después de seleccionar el modelo, se ajusta el umbral de decisión. En lugar de usar solamente 0.50, se eligió **0.28**, el mayor valor que conserva una exhaustividad mínima de 0.95 para `Regar`. Esto prioriza detectar los casos que realmente necesitan agua y reduce el riesgo agronómico de dejar sin riego una condición crítica.

### Evaluación

En el conjunto de prueba, el clasificador obtuvo los siguientes resultados reproducidos localmente:

| Métrica para `Regar` | Resultado |
| --- | ---: |
| Exactitud global | 0.8608 |
| Precisión | 0.6319 |
| Exhaustividad | 0.9719 |
| F1 | 0.7658 |
| Exactitud del estado hídrico | 0.9163 |

La matriz de confusión, con el orden `[[VN, FP], [FN, VP]]`, fue `[[2019, 423], [21, 726]]`. Los 21 falsos negativos se mantienen bajos frente a 747 casos reales de `Regar`, coherente con la prioridad del sistema de no omitir riegos necesarios.

## Especificaciones de tecnologías

| Tecnología | Función en el prototipo |
| --- | --- |
| Python 3.12 | Lenguaje de ejecución del entrenamiento, predicción e interfaz. |
| pandas y openpyxl | Lectura, limpieza y manipulación de archivos CSV y Excel. |
| scikit-learn | Construcción, validación, métricas y selección de los clasificadores. |
| joblib | Serialización y carga del modelo entrenado en `model/modelo_riego.pkl`. |
| Streamlit | Interfaz web para cargar lecturas, consultar una condición y visualizar resultados. |
| Altair | Gráficos de decisiones, estados, zonas y consumo de agua. |
| NumPy | Transformaciones numéricas y variables temporales derivadas. |

Las versiones exactas usadas por el proyecto están fijadas en `requirements.txt`, lo que permite repetir la instalación con `pip install -r requirements.txt`.

## Desarrollo del prototipo

La implementación está separada por responsabilidades:

| Componente | Responsabilidad |
| --- | --- |
| `src/preparacion.py` | Carga, limpieza, ingeniería de atributos y partición de los datos. |
| `src/train.py` | Entrena los candidatos, selecciona Random Forest, ajusta el umbral y guarda el artefacto. |
| `src/evaluar.py` | Aporte de atributos, métricas por invernadero, ahorro estimado sobre todos los días de prueba y figuras en `reports/`. |
| `model/modelo_riego.pkl` | Modelo persistido que incluye clasificadores, umbral, atributos y métricas. |
| `src/predict.py` | Expone `predecir(df, cultivo)` para lotes y `predecir_condicion(...)` para una lectura manual. |
| `src/app.py` | Panel Streamlit para carga de archivos, consulta rápida, resultados y ahorro. |
| `src/optimizacion.py` y `src/analisis.py` | Transforman las predicciones en un plan de riego por zona y resumen de consumo. |

El frontend carga un Excel o CSV, valida las columnas requeridas y llama a `predecir`. La función devuelve una fila por lectura con `Estado_hidrico`, `Decision` y `Prob_regar`; por ello el panel puede mostrar la clasificación, priorizar zonas y recomendar riego.

El ahorro no se infiere directamente de una probabilidad. Se compara el volumen de un cronograma tradicional fijo con el volumen recomendado por las predicciones del modelo. Para cada zona, el usuario configura litros por riego, horas del cronograma, intervalo mínimo entre riegos y costo por metro cúbico. El sistema calcula litros tradicionales, litros optimizados, ahorro absoluto, porcentaje y ahorro económico.

## Pruebas de resolución y limitaciones

### Cómo reproducir la prueba

Desde la raíz del repositorio, con el entorno virtual activado:

```powershell
py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python src/train.py
python src/evaluar.py
streamlit run src/app.py
```

En la interfaz se debe cargar uno de los Excel del directorio `data/`, pulsar **Analizar y predecir riego** y comprobar que la etiqueta superior indique **Modelo IA**, no `Modo simulado`.

### Evidencia de validación local

La reproducción ejecutada en noviembre de 2026 confirmó el modelo Random Forest, el umbral 0.28 y las métricas de la tabla de evaluación. También se verificaron dos consultas puntuales:

| Condición | Resultado |
| --- | --- |
| 35 °C, 25 % de humedad ambiente, 15 % de humedad de suelo, tomate | `Regar`, estado `Crítico`, probabilidad 0.940. |
| 20 °C, 85 % de humedad ambiente, 60 % de humedad de suelo, tomate | `No Regar`, estado `Óptimo`, probabilidad 0.000. |

La aplicación Streamlit respondió correctamente en `http://localhost:8501` tras iniciar `streamlit run src/app.py`.

### Limitaciones

- Los datos son sintéticos; las métricas y el ahorro deben validarse con mediciones reales del invernadero.
- Las métricas solo representan los datasets disponibles; nuevos cultivos, sensores o condiciones climáticas requieren validación y posible reentrenamiento.
- El porcentaje, litros y costo ahorrados dependen del cronograma tradicional y de los parámetros configurados por el usuario; no son una medición física automática de caudal.
- El umbral bajo favorece la exhaustividad de `Regar`, por lo que acepta más falsos positivos para disminuir el riesgo de no regar un cultivo que lo necesita.
- Antes de una implementación productiva, se debe contrastar el plan recomendado con conocimiento agronómico y mediciones reales de caudal.
