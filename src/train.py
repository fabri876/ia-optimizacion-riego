"""Entrenamiento del clasificador de riego (CRISP-DM, fases 4 y 5).

1. Lee los datasets del invernadero.
2. Entrena 4 modelos candidatos y elige el de mejor F1 en la clase "Regar"
   sobre el conjunto de validación.
3. Ajusta el umbral de decisión para que la exhaustividad de "Regar" sea >= 0,95.
4. Evalúa una sola vez sobre el conjunto de prueba.
5. Guarda el modelo en model/modelo_riego.pkl.

Uso (desde la raíz del proyecto):
    python src/train.py
    python src/train.py --datos data/datasets_combinados.csv
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, classification_report, confusion_matrix,
                             f1_score, precision_score, recall_score)
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

sys.path.insert(0, str(Path(__file__).resolve().parent))
import preparacion as prep  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
RUTA_DATOS = RAIZ / "data" / "datasets_combinados.csv"
RUTA_MODELO = RAIZ / "model" / "modelo_riego.pkl"
SEMILLA = 42
RECALL_MINIMO = 0.95


def candidatos() -> dict[str, Pipeline]:
    """Tabla 13 del informe. Árboles y bosques no necesitan escalado."""
    return {
        "Árbol de Decisión": Pipeline([("clf", DecisionTreeClassifier(
            max_depth=8, min_samples_leaf=5, class_weight="balanced", random_state=SEMILLA))]),
        "Random Forest": Pipeline([("clf", RandomForestClassifier(
            n_estimators=300, max_depth=16, max_features="sqrt", min_samples_leaf=2,
            class_weight="balanced", n_jobs=-1, random_state=SEMILLA))]),
        "Regresión Logística": Pipeline([("esc", StandardScaler()), ("clf", LogisticRegression(
            C=1.0, max_iter=2000, class_weight="balanced", random_state=SEMILLA))]),
        "Perceptrón Multicapa": Pipeline([("esc", StandardScaler()), ("clf", MLPClassifier(
            hidden_layer_sizes=(32, 16), activation="logistic", learning_rate_init=0.01,
            max_iter=600, early_stopping=True, random_state=SEMILLA))]),
    }


def metricas(y, p) -> dict[str, float]:
    return {"exactitud": accuracy_score(y, p),
            "precision": precision_score(y, p, zero_division=0),
            "exhaustividad": recall_score(y, p, zero_division=0),
            "f1": f1_score(y, p, zero_division=0)}


def ajustar_umbral(modelo, X, y) -> float:
    """Mayor umbral que todavía detecta al menos el 95 % de los casos 'Regar'."""
    prob = modelo.predict_proba(X)[:, 1]
    validos = [t for t in np.arange(0.05, 0.96, 0.01)
               if recall_score(y, (prob >= t).astype(int)) >= RECALL_MINIMO]
    return float(max(validos)) if validos else 0.5


def entrenar(ruta_datos: Path = RUTA_DATOS, ruta_modelo: Path = RUTA_MODELO,
             verbose: bool = True) -> dict:
    df, limpieza = prep.limpiar(prep.cargar(ruta_datos))
    df = prep.derivar_atributos(df)
    partes = prep.particionar(df, SEMILLA)
    X = {k: v[prep.FEATURES] for k, v in partes.items()}
    y = {k: v["regar"] for k, v in partes.items()}
    log = print if verbose else (lambda *a, **k: None)

    log(f"Registros válidos: {len(df)} (descartados por nulos: {limpieza['nulos']})")
    for k in X:
        log(f"  {k:13s} {len(X[k]):6d} registros")

    log("\nComparación en validación (umbral 0,5):")
    resultados, modelos = {}, {}
    for nombre, modelo in candidatos().items():
        modelo.fit(X["entrenamiento"], y["entrenamiento"])
        m = metricas(y["validacion"], modelo.predict(X["validacion"]))
        resultados[nombre], modelos[nombre] = m, modelo
        log(f"  {nombre:22s} exactitud={m['exactitud']:.4f}  F1={m['f1']:.4f}  "
            f"exhaustividad={m['exhaustividad']:.4f}")

    ganador = max(resultados, key=lambda n: resultados[n]["f1"])
    modelo = modelos[ganador]
    umbral = ajustar_umbral(modelo, X["validacion"], y["validacion"])

    pred = (modelo.predict_proba(X["prueba"])[:, 1] >= umbral).astype(int)
    prueba = metricas(y["prueba"], pred)
    cm = confusion_matrix(y["prueba"], pred)
    log(f"\nModelo elegido: {ganador}  |  umbral ajustado: {umbral:.2f}")
    log(f"Prueba -> exactitud {prueba['exactitud']:.4f}  exhaustividad {prueba['exhaustividad']:.4f}"
        f"  F1 {prueba['f1']:.4f}")
    log(f"Matriz de confusión [[VN FP] [FN VP]]: {cm.tolist()}")
    log(classification_report(y["prueba"], pred, target_names=["No Regar", "Regar"], digits=4))

    # Estado hídrico (Óptimo / Crítico / Saturado): lo pide la interfaz para mostrar
    # el estado de cada lectura. Es un modelo auxiliar; la decisión la toma el de arriba.
    estado = RandomForestClassifier(n_estimators=150, max_depth=14, class_weight="balanced",
                                    n_jobs=-1, random_state=SEMILLA)
    entren = partes["entrenamiento"].dropna(subset=["estado"])
    estado.fit(entren[prep.FEATURES], entren["estado"])
    exac_estado = accuracy_score(partes["prueba"]["estado"], estado.predict(X["prueba"]))
    log(f"Modelo de estado hídrico -> exactitud en prueba {exac_estado:.4f}")

    artefacto = {
        "modelo": modelo, "umbral": umbral, "modelo_estado": estado,
        "features": prep.FEATURES, "nombre_modelo": ganador,
        "metricas_validacion": resultados, "metricas_prueba": prueba,
        "matriz_confusion": cm.tolist(), "exactitud_estado": exac_estado,
        "limpieza": limpieza,
    }
    ruta_modelo.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artefacto, ruta_modelo, compress=3)
    resumen = {k: v for k, v in artefacto.items() if k not in ("modelo", "modelo_estado")}
    ruta_modelo.with_suffix(".json").write_text(
        json.dumps(resumen, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
    log(f"\nGuardado en {ruta_modelo.relative_to(RAIZ)}")
    return artefacto


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Entrena el clasificador de riego.")
    ap.add_argument("--datos", type=Path, default=RUTA_DATOS,
                    help="CSV/XLSX o carpeta con los dataset_*.xlsx")
    ap.add_argument("--salida", type=Path, default=RUTA_MODELO)
    a = ap.parse_args()
    entrenar(a.datos, a.salida)
