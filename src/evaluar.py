"""Evaluación complementaria del modelo entrenado (apartado 5.7 del informe).

Genera, a partir de model/modelo_riego.pkl:
  - aporte de los atributos derivados (Tabla 17),
  - métricas por invernadero en el subconjunto de prueba,
  - estimación de ahorro sobre TODOS los días de prueba (media y rango por invernadero),
  - figuras: matriz de confusión, curva precisión-exhaustividad y cronograma de una semana.

Resultados en reports/evaluacion.json y reports/figuras/.

Supuestos de la estimación de ahorro: 25 L por riego, cronograma tradicional a las
06:00, 12:00 y 18:00 y al menos 6 h entre riegos del sistema. El historial sintético no
siguió ese cronograma y la humedad del suelo no reacciona a los riegos que propone el
modelo, por lo que el ahorro es una estimación bajo supuestos, no una medición.

Uso:  python src/evaluar.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.metrics import f1_score

sys.path.insert(0, str(Path(__file__).resolve().parent))
import optimizacion as opt  # noqa: E402
import preparacion as prep  # noqa: E402
from train import RUTA_DATOS, RUTA_MODELO, SEMILLA, metricas  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "reports"
LITROS = 25.0
VENTANA = opt.HORAS_ENTRE_RIEGOS  # un riego cubre esa hora y las 5 siguientes

ABLACION = [
    ("Variables base (T, HR amb., HR suelo)", ["temperatura", "humedad_ambiente", "humedad_suelo"]),
    ("+ hora cíclica", ["temperatura", "humedad_ambiente", "humedad_suelo", "hora_sen", "hora_cos"]),
    ("+ DPV (kPa)", ["temperatura", "humedad_ambiente", "humedad_suelo", "hora_sen", "hora_cos",
                     "dpv_kpa"]),
    ("+ media móvil 24 h", ["temperatura", "humedad_ambiente", "humedad_suelo", "hora_sen",
                            "hora_cos", "dpv_kpa", "humedad_suelo_media24"]),
    ("+ cultivo (vector completo)", prep.FEATURES),
]


def cubiertas(criticas: np.ndarray, eventos: np.ndarray) -> int:
    """Horas críticas (vector de 24 h) con un riego en esa hora o en las VENTANA-1 anteriores."""
    return int(sum(eventos[max(0, h - VENTANA + 1): h + 1].any() for h in np.flatnonzero(criticas)))


def _por_hora(horas: np.ndarray, valores: np.ndarray) -> np.ndarray:
    v = np.zeros(24, dtype=int)
    v[horas] = valores
    return v


def ahorro_por_dia(df: pd.DataFrame) -> pd.DataFrame:
    """Un día de prueba por fila. El cronograma tradicional riega 3 veces al día aunque falten
    lecturas del sensor; el sistema solo puede decidir en las horas con lectura."""
    trad = np.zeros(24, dtype=int)
    trad[list(opt.HORARIO_TRADICIONAL)] = 1
    filas = []
    for (inv, cultivo, dia), g in df.groupby([prep.COL_INVERNADERO, prep.COL_CULTIVO, "dia"]):
        g = g.sort_values(prep.COL_FECHA)
        horas = g[prep.COL_FECHA].dt.hour.to_numpy()
        ia = _por_hora(horas, opt.consolidar_eventos(g, g["pred"], prep.COL_FECHA).to_numpy())
        ref = _por_hora(horas, opt.consolidar_eventos(g, g["regar"], prep.COL_FECHA).to_numpy())
        crit = _por_hora(horas, g["regar"].to_numpy())
        filas.append({
            "invernadero": inv, "cultivo": cultivo, "dia": dia, "lecturas": len(g),
            "horas_criticas": int(crit.sum()),
            "riegos_tradicional": int(trad.sum()), "riegos_ia": int(ia.sum()),
            "riegos_referencia": int(ref.sum()),
            "cubiertas_ia": cubiertas(crit, ia), "cubiertas_tradicional": cubiertas(crit, trad),
        })
    d = pd.DataFrame(filas)
    d["ahorro_pct"] = (d.riegos_tradicional - d.riegos_ia) / d.riegos_tradicional * 100
    return d


def resumen_ahorro(d: pd.DataFrame) -> list[dict]:
    out = []
    for (inv, cultivo), g in list(d.groupby(["invernadero", "cultivo"])) + [(("Total", ""), d)]:
        crit = g.horas_criticas.sum()
        out.append({
            "invernadero": inv, "cultivo": cultivo, "dias": int(len(g)),
            "litros_tradicional": float(g.riegos_tradicional.sum() * LITROS),
            "litros_ia": float(g.riegos_ia.sum() * LITROS),
            "litros_referencia": float(g.riegos_referencia.sum() * LITROS),
            "ahorro_pct_total": float((g.riegos_tradicional.sum() - g.riegos_ia.sum())
                                      / g.riegos_tradicional.sum() * 100),
            "ahorro_pct_media": float(g.ahorro_pct.mean()),
            "ahorro_pct_min": float(g.ahorro_pct.min()), "ahorro_pct_max": float(g.ahorro_pct.max()),
            "horas_criticas": int(crit),
            # Proporción de horas críticas sin riego en las 6 h previas. Sin horas críticas
            # el cociente es 0/0 y se reporta como no definido (None).
            "deficit_ia": float(1 - g.cubiertas_ia.sum() / crit) if crit else None,
            "deficit_tradicional": float(1 - g.cubiertas_tradicional.sum() / crit) if crit else None,
        })
    return out


def figuras(art: dict, prueba: pd.DataFrame, destino: Path) -> dict:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    destino.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "serif", "font.serif": ["Times New Roman", "DejaVu Serif"],
                         "font.size": 11})
    rutas = {}

    cm = np.array(art["matriz_confusion"])
    fig, ax = plt.subplots(figsize=(4.6, 3.8), dpi=200)
    ax.imshow(cm, cmap="Greys", vmin=0, vmax=cm.max() * 1.6)
    for (i, j), v in np.ndenumerate(cm):
        ax.text(j, i, f"{v:,}".replace(",", " "), ha="center", va="center", fontsize=13)
    ax.set_xticks([0, 1], ["No Regar", "Regar"])
    ax.set_yticks([0, 1], ["No Regar", "Regar"])
    ax.set_xlabel("Decisión del modelo")
    ax.set_ylabel("Decisión del dataset")
    fig.tight_layout()
    rutas["matriz_confusion"] = destino / "matriz_confusion.png"
    fig.savefig(rutas["matriz_confusion"])
    plt.close(fig)

    pr = art["curva_pr_validacion"]
    prec, exh, umb = map(np.array, (pr["precision"], pr["exhaustividad"], pr["umbrales"]))
    i = int(np.argmin(np.abs(umb - art["umbral"])))
    fig, ax = plt.subplots(figsize=(5.2, 3.8), dpi=200)
    ax.plot(exh, prec, color="black", lw=1.4)
    ax.scatter([exh[i]], [prec[i]], color="black", zorder=3)
    ax.annotate(f"τ* = {art['umbral']:.2f}".replace(".", ","), (exh[i], prec[i]),
                xytext=(-80, -30), textcoords="offset points",
                arrowprops={"arrowstyle": "->", "lw": 0.8})
    ax.axvline(0.95, ls="--", lw=0.8, color="grey")
    ax.set_xlabel("Exhaustividad (Regar)")
    ax.set_ylabel("Precisión (Regar)")
    ax.set_xlim(0, 1.01)
    ax.set_ylim(0, 1.01)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    rutas["curva_pr"] = destino / "curva_pr.png"
    fig.savefig(rutas["curva_pr"])
    plt.close(fig)

    # Cronograma de una semana: días de prueba del invernadero 03 (lechuga).
    g = prueba[prueba[prep.COL_INVERNADERO].astype(str).str.zfill(2) == "03"]
    # Siete días de prueba consecutivos de mitad del período.
    todos = sorted(g["dia"].unique())
    dias = todos[len(todos) // 2 - 3: len(todos) // 2 + 4]
    fig, ax = plt.subplots(figsize=(7.2, 3.6), dpi=200)
    for k, dia in enumerate(dias):
        dd = g[g["dia"] == dia].sort_values(prep.COL_FECHA)
        horas = dd[prep.COL_FECHA].dt.hour.to_numpy()
        ev = opt.consolidar_eventos(dd, dd["pred"], prep.COL_FECHA).to_numpy()
        ax.scatter(horas[dd["regar"].to_numpy() == 1], [k] * int(dd["regar"].sum()),
                   marker="s", s=38, color="#d9d9d9", zorder=1)
        ax.scatter(horas[ev == 1], [k] * int(ev.sum()), marker="v", s=70, color="black", zorder=3)
        ax.scatter(list(opt.HORARIO_TRADICIONAL), [k] * 3, marker="o", s=30,
                   facecolors="none", edgecolors="black", zorder=2)
    ax.set_yticks(range(len(dias)), [pd.Timestamp(d).strftime("%d/%m/%Y") for d in dias])
    ax.invert_yaxis()
    ax.set_xticks(range(0, 24, 2), [f"{h:02d}:00" for h in range(0, 24, 2)], rotation=45)
    ax.set_xlim(-0.5, 23.5)
    ax.set_xlabel("Hora del día")
    ax.scatter([], [], marker="s", color="#d9d9d9", label="Hora crítica según el dataset")
    ax.scatter([], [], marker="v", color="black", label="Riego recomendado por el sistema")
    ax.scatter([], [], marker="o", facecolors="none", edgecolors="black", label="Cronograma tradicional")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.32), ncol=3, frameon=False, fontsize=9)
    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    rutas["cronograma_semana"] = destino / "cronograma_semana.png"
    fig.savefig(rutas["cronograma_semana"])
    plt.close(fig)
    return {k: str(v.relative_to(RAIZ)) for k, v in rutas.items()}


def evaluar(ruta_datos: Path = RUTA_DATOS, ruta_modelo: Path = RUTA_MODELO) -> dict:
    import joblib
    art = joblib.load(ruta_modelo)
    df, _ = prep.limpiar(prep.cargar(ruta_datos))
    df = prep.derivar_atributos(df)
    partes = prep.particionar(df, SEMILLA)
    modelo, umbral = art["modelo"], art["umbral"]

    # Aporte de los atributos: mismo Random Forest, umbral 0,5, en validación.
    ablacion = []
    for nombre, cols in ABLACION:
        m = clone(modelo.named_steps["clf"])
        m.fit(partes["entrenamiento"][cols], partes["entrenamiento"]["regar"])
        p = m.predict(partes["validacion"][cols])
        ablacion.append({"configuracion": nombre, "n": len(cols),
                         **metricas(partes["validacion"]["regar"], p)})

    prueba = partes["prueba"].copy()
    prueba["pred"] = (modelo.predict_proba(prueba[prep.FEATURES])[:, 1] >= umbral).astype(int)
    prueba["dia"] = prueba[prep.COL_FECHA].dt.strftime("%Y-%m-%d")
    por_inv = []
    for (inv, cultivo), g in prueba.groupby([prep.COL_INVERNADERO, prep.COL_CULTIVO]):
        por_inv.append({"invernadero": inv, "cultivo": cultivo, "registros": int(len(g)),
                        "regar": int(g["regar"].sum()), **metricas(g["regar"], g["pred"])})

    d = ahorro_por_dia(prueba)
    resultado = {
        "ablacion": ablacion, "por_invernadero": por_inv,
        "ahorro_dias_prueba": resumen_ahorro(d),
        "supuestos": {"litros_por_riego": LITROS, "horario_tradicional": opt.HORARIO_TRADICIONAL,
                      "horas_entre_riegos": opt.HORAS_ENTRE_RIEGOS},
        "registros_prueba_antes_limpieza": None,
        "figuras": figuras(art, prueba, SALIDA / "figuras"),
        "f1_prueba_umbral_05": float(f1_score(prueba["regar"],
                                              modelo.predict(prueba[prep.FEATURES]))),
    }
    crudo = prep.cargar(ruta_datos)
    resultado["registros_prueba_antes_limpieza"] = int(
        (crudo[prep.COL_PARTICION].map(prep.normalizar) == "prueba").sum())
    SALIDA.mkdir(exist_ok=True)
    (SALIDA / "evaluacion.json").write_text(
        json.dumps(resultado, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
    d.to_csv(SALIDA / "ahorro_por_dia_prueba.csv", index=False, encoding="utf-8-sig")
    return resultado


if __name__ == "__main__":
    r = evaluar()
    print(json.dumps({k: v for k, v in r.items() if k != "figuras"}, indent=1,
                     ensure_ascii=False, default=float))
