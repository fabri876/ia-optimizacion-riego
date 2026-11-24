# Frontend del Sistema Inteligente de Optimización de Riego

## 1. Qué hice

Rediseñé por completo el frontend en Streamlit para que se vea como un panel de control agrícola y no como un prototipo. Separé el código en varios archivos pequeños para que cada parte se pueda revisar y cambiar sin tocar las demás. No agregué librerías nuevas: todo usa `streamlit`, `pandas`, `altair` y `openpyxl`, que ya están en mi `venv`.

## 2. Dónde puse cada archivo

```
ia-optimizacion-riego/
├── .streamlit/
│   └── config.toml        <- tema de colores (nuevo)
├── docs/
│   └── FRONTEND.md        <- este documento (nuevo)
└── src/
    ├── app.py             <- reemplaza el app.py anterior
    ├── estilos.py         <- CSS del panel (nuevo)
    ├── componentes.py     <- tarjetas, cifras y gráficos (nuevo)
    ├── datos.py           <- carga, limpieza y zonas (nuevo)
    ├── analisis.py        <- resúmenes, ahorro y evaluación (nuevo)
    └── simulador.py       <- predictor de reglas, solo mientras no exista el modelo (nuevo)
```

No toqué `train.py` ni `predict.py`, porque son del equipo de IA.

## 3. Cómo lo ejecuto

Desde la raíz del proyecto, con el entorno virtual activado:

```
streamlit run src/app.py
```

Es importante correrlo desde la raíz para que Streamlit encuentre `.streamlit/config.toml`.

## 4. Qué muestra el panel

| Parte | Qué contiene |
|---|---|
| Barra lateral | Elección del dataset del proyecto o carga de un archivo, número de zonas, litros por riego y costo del agua |
| Encabezado | Cultivo, localidad y suelo, sacados del nombre del archivo, más el modo de predicción activo |
| Resumen | Cifras clave, decisión lectura por lectura, reparto de decisiones y estados hídricos, y temperatura frente a humedad del suelo |
| Zonas | Una tarjeta por zona con humedad del suelo, prioridad y acción, más gráficos comparativos |
| Ahorro de agua | Litros ahorrados, comparación entre riego tradicional y optimizado, y plan de riego recomendado |
| Datos | Tabla filtrable, descarga en CSV y evaluación del modelo cuando hay etiqueta real |

Antes de analizar, la pestaña Resumen muestra la exploración del dataset (series e histogramas). Las otras pestañas piden pulsar **Analizar y predecir riego**.

## 5. Cómo conecto el modelo real

El frontend intenta importar `predecir` desde `src/predict.py`. Si no existe o falla, usa `simulador.py` y lo avisa en pantalla con el motivo técnico.

Para que mi frontend use el modelo real, `predict.py` debe exponer esta función:

```python
def predecir(df):
    # df trae solo: Temperatura_C, Humedad_ambiente_%, Humedad_suelo_%
    # debe devolver un DataFrame con el mismo número de filas y estas columnas:
    #   Estado_hidrico -> "Óptimo", "Crítico" o "Saturado"
    #   Decision       -> "Regar" o "No Regar"
    #   Prob_regar     -> (opcional) probabilidad entre 0 y 1
    ...
```

Cuando el modelo está activo y el dataset trae la columna `Decision`, la pestaña Datos calcula el porcentaje de coincidencia y la tabla de aciertos y errores.

## 6. Cómo defino las zonas

- Si el archivo trae una columna `Zona`, uso esa.
- Si no la trae, reparto las lecturas de forma rotativa entre el número de zonas que elijo en la barra lateral (lectura 1 a la Zona 1, lectura 2 a la Zona 2, y así).

La prioridad de cada zona sale del porcentaje de sus lecturas clasificadas como Regar:

| Lecturas a regar | Prioridad | Acción |
|---|---|---|
| 60 % o más | Alta | Regar ahora |
| Entre 30 % y 60 % | Media | Programar riego |
| Menos de 30 % | Baja | No regar |

## 7. Cómo calculo el ahorro de agua

- **Riego tradicional:** número de lecturas multiplicado por los litros por riego (se riega siempre).
- **Riego optimizado:** lecturas clasificadas como Regar multiplicadas por los litros por riego.
- **Ahorro:** la diferencia entre ambos, y su costo con el precio por m³ que ingreso en la barra lateral.

Los valores por defecto (50 L por riego y Bs 5 por m³) son supuestos míos para la demostración. Hay que ajustarlos a datos reales del cultivo antes de presentar cifras.

## 8. Qué debo revisar

- El simulador usa reglas simples y no representa al modelo entrenado. No debo presentar sus resultados como resultados de IA.
- Si mis datasets tienen una columna de fecha, el gráfico de series la usa como eje; si no, usa el número de lectura.
- Si algún dataset tiene otros nombres de columna, `datos.py` (constantes `COL_*`) es el único lugar donde debo cambiarlos.
