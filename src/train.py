"""Entrenamiento del clasificador de riego (CRISP-DM, fases 4 y 5).

1. Lee el dataset combinado (datos sintéticos, ver la hoja Parametros de los Excel).
2. Para cada uno de los 4 modelos candidatos busca hiperparámetros con validación
   cruzada de 5 particiones agrupadas por día (GroupKFold) sobre el subconjunto de
   entrenamiento, optimizando F1 de la clase "Regar".
3. Compara los 4 modelos ajustados en el subconjunto de validación y elige el de mejor F1.
4. Ajusta el umbral de decisión τ* para que la exhaustividad de "Regar" en validación
   sea >= 0,95 y reporta precisión y exhaustividad de validación con ese umbral.
5. Evalúa una sola vez sobre el subconjunto de prueba.
6. Guarda el modelo en model/modelo_riego.pkl y un resumen en model/modelo_riego.json.

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
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, classification_report, confusion_matrix,
                             f1_score, precision_recall_curve, precision_score, recall_score)
from sklearn.model_selection import GridSearchCV, GroupKFold
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier

sys.path.insert(0, str(Path(__file__).resolve().parent))
import preparacion as prep  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
RUTA_DATOS = RAIZ / "data" / "datasets_combinados.csv"
RUTA_MODELO = RAIZ / "model" / "modelo_riego.pkl"
SEMILLA = 42
RECALL_MINIMO = 0.95
PLIEGUES = 5


def _lineal():
    """Escala los atributos numéricos y codifica el cultivo en one-hot.

    Un código entero 1-5 le impone un orden y una distancia falsos al cultivo; los
    árboles lo toleran porque solo hacen cortes, los modelos lineales no.
    """
    return ColumnTransformer([
        ("num", StandardScaler(), prep.NUMERICAS),
        ("cultivo", OneHotEncoder(handle_unknown="ignore"), prep.CATEGORICAS),
    ])


def candidatos() -> dict[str, tuple[Pipeline, dict]]:
    """Tabla 13 del informe: modelo y grilla de hiperparámetros explorada."""
    return {
        "Árbol de Decisión": (
            Pipeline([("clf", DecisionTreeClassifier(class_weight="balanced", random_state=SEMILLA))]),
            {"clf__max_depth": [6, 8, 12], "clf__min_samples_leaf": [5, 20]}),
        "Random Forest": (
            Pipeline([("clf", RandomForestClassifier(
                n_estimators=300, max_features="sqrt", class_weight="balanced",
                n_jobs=-1, random_state=SEMILLA))]),
            {"clf__max_depth": [12, 16, None], "clf__min_samples_leaf": [2, 5]}),
        "Regresión Logística": (
            Pipeline([("prep", _lineal()), ("clf", LogisticRegression(
                max_iter=2000, class_weight="balanced", random_state=SEMILLA))]),
            {"clf__C": [0.1, 1.0, 10.0]}),
        "Perceptrón Multicapa": (
            Pipeline([("prep", _lineal()), ("clf", MLPClassifier(
                activation="logistic", learning_rate_init=0.01, max_iter=600,
                early_stopping=True, random_state=SEMILLA))]),
            {"clf__hidden_layer_sizes": [(32, 16), (64, 32)], "clf__alpha": [1e-4, 1e-3]}),
    }


def metricas(y, p) -> dict[str, float]:
    return {"exactitud": accuracy_score(y, p),
            "precision": precision_score(y, p, zero_division=0),
            "exhaustividad": recall_score(y, p, zero_division=0),
            "f1": f1_score(y, p, zero_division=0)}


def ajustar_umbral(prob, y) -> float:
    """Mayor umbral que todavía detecta al menos el 95 % de los casos 'Regar'."""
    validos = [t for t in np.round(np.arange(0.05, 0.96, 0.01), 2)
               if recall_score(y, (prob >= t).astype(int)) >= RECALL_MINIMO]
    return float(max(validos)) if validos else 0.5


def dias(df):
    """Grupo de cada lectura para la validación cruzada: invernadero + día."""
    fecha = df[prep.COL_FECHA].dt.strftime("%Y-%m-%d")
    inv = df[prep.COL_INVERNADERO].astype(str) if prep.COL_INVERNADERO in df else ""
    return (inv + "_" + fecha).to_numpy()


def entrenar(ruta_datos: Path = RUTA_DATOS, ruta_modelo: Path = RUTA_MODELO,
             verbose: bool = True) -> dict:
    df, limpieza = prep.limpiar(prep.cargar(ruta_datos))
    df = prep.derivar_atributos(df)
    partes = prep.particionar(df, SEMILLA)
    X = {k: v[prep.FEATURES] for k, v in partes.items()}
    y = {k: v["regar"] for k, v in partes.items()}
    log = print if verbose else (lambda *a, **k: None)

    log(f"Registros válidos: {len(df)}  limpieza: {limpieza}")
    for k in X:
        log(f"  {k:13s} {len(X[k]):6d} registros")

    log(f"\nBúsqueda de hiperparámetros (GroupKFold por día, {PLIEGUES} pliegues, F1):")
    resultados, modelos, mejores, cv = {}, {}, {}, {}
    grupos = dias(partes["entrenamiento"])
    for nombre, (modelo, grilla) in candidatos().items():
        busqueda = GridSearchCV(modelo, grilla, scoring="f1", cv=GroupKFold(PLIEGUES), n_jobs=1)
        busqueda.fit(X["entrenamiento"], y["entrenamiento"], groups=grupos)
        modelo = busqueda.best_estimator_
        m = metricas(y["validacion"], modelo.predict(X["validacion"]))
        resultados[nombre], modelos[nombre] = m, modelo
        mejores[nombre] = {k.replace("clf__", ""): (list(v) if isinstance(v, tuple) else v)
                           for k, v in busqueda.best_params_.items()}
        cv[nombre] = {"f1_media": float(busqueda.best_score_),
                      "f1_desv": float(busqueda.cv_results_["std_test_score"][busqueda.best_index_])}
        log(f"  {nombre:22s} {mejores[nombre]}  F1-CV={cv[nombre]['f1_media']:.4f}"
            f"±{cv[nombre]['f1_desv']:.4f} | validación: exactitud={m['exactitud']:.4f} "
            f"precisión={m['precision']:.4f} exhaustividad={m['exhaustividad']:.4f} F1={m['f1']:.4f}")

    ganador = max(resultados, key=lambda n: resultados[n]["f1"])
    modelo = modelos[ganador]
    prob_val = modelo.predict_proba(X["validacion"])[:, 1]
    umbral = ajustar_umbral(prob_val, y["validacion"])
    validacion_umbral = metricas(y["validacion"], (prob_val >= umbral).astype(int))
    prec, exh, umb = precision_recall_curve(y["validacion"], prob_val)

    pred = (modelo.predict_proba(X["prueba"])[:, 1] >= umbral).astype(int)
    prueba = metricas(y["prueba"], pred)
    cm = confusion_matrix(y["prueba"], pred)
    log(f"\nModelo elegido: {ganador}  |  umbral ajustado: {umbral:.2f}")
    log(f"Validación con τ*: {validacion_umbral}")
    log(f"Prueba -> {prueba}")
    log(f"Matriz de confusión [[VN FP] [FN VP]]: {cm.tolist()}")
    log(classification_report(y["prueba"], pred, target_names=["No Regar", "Regar"], digits=4))

    # Estado hídrico (Óptimo / Saturado) para mostrar en la interfaz. La decisión de regar la
    # toma el modelo de arriba: si decide Regar, el estado mostrado es Crítico (predict.py).
    estado = RandomForestClassifier(n_estimators=150, max_depth=14, class_weight="balanced",
                                    n_jobs=-1, random_state=SEMILLA)
    entren = partes["entrenamiento"].dropna(subset=["estado"])
    estado.fit(entren[prep.FEATURES], entren["estado"])
    exac_estado = accuracy_score(partes["prueba"]["estado"], estado.predict(X["prueba"]))
    log(f"Modelo de estado hídrico -> exactitud en prueba {exac_estado:.4f}")

    importancias = {}
    clf = modelo.named_steps["clf"]
    if hasattr(clf, "feature_importances_"):
        importancias = dict(sorted(zip(prep.FEATURES, map(float, clf.feature_importances_)),
                                   key=lambda kv: -kv[1]))

    artefacto = {
        "modelo": modelo, "umbral": umbral, "modelo_estado": estado,
        "features": prep.FEATURES, "nombre_modelo": ganador,
        "hiperparametros": mejores, "validacion_cruzada": cv,
        "metricas_validacion": resultados, "validacion_con_umbral": validacion_umbral,
        "curva_pr_validacion": {"precision": prec.tolist(), "exhaustividad": exh.tolist(),
                                "umbrales": umb.tolist()},
        "metricas_prueba": prueba, "matriz_confusion": cm.tolist(),
        "exactitud_estado": exac_estado, "importancias": importancias,
        "registros": {k: int(len(v)) for k, v in X.items()}, "limpieza": limpieza,
    }
    ruta_modelo.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artefacto, ruta_modelo, compress=3)
    resumen = {k: v for k, v in artefacto.items()
               if k not in ("modelo", "modelo_estado", "curva_pr_validacion")}
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
