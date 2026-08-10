"""Run the full 2×2 benchmark + ablations and REGENERATE data/metrics.json and
docs/BENCHMARK.md. These two files are never edited by hand: if they need a
manual fix, the bug is here.

Runs per zone: the 4 cells, ablation A (single-year embeddings), and — Río
Cuarto only — ablation B (random split vs spatial blocks, RF cells).
"""

import datetime
import json

import numpy as np
import pandas as pd

from mapa_cultivos import clasificar, ee_client, evaluar, features, zonas
from mapa_cultivos.settings import DATA_DIR, REPO_ROOT, SEED, settings

NOMBRES = {0: "no agrícola", 1: "soja", 2: "maíz", 3: "trigo/soja 2ª", 4: "maní", 5: "pastura/verdeo"}
ORDEN_DOC = [0, 1, 2, 3, 4, 5]
MODELOS = list(clasificar.MODELOS)
PARES_MCNEMAR = [("clasicas-rf", "embeddings-rf"), ("clasicas-knn", "embeddings-knn")]


def log(msg: str) -> None:
    print(f"[{datetime.datetime.now():%H:%M:%S}] {msg}", flush=True)


def split_aleatorio(tabla: pd.DataFrame) -> pd.DataFrame:
    """Ablation B: same points, block structure ignored (the common mistake)."""
    rng = np.random.default_rng(SEED)
    tabla = tabla.copy()
    for clase, grupo in tabla.groupby("clase"):
        idx = rng.permutation(grupo.index.to_numpy())
        n_train = int(len(idx) * 0.7)
        tabla.loc[idx[:n_train], "set"] = "entrenamiento"
        tabla.loc[idx[n_train:], "set"] = "validacion_mnc"
    return tabla


def correr_zona(zona: str, campania: str) -> dict:
    import ee

    tabla = pd.read_csv(DATA_DIR / "muestras" / f"{zona}_{campania}.csv")
    geom = ee.Geometry(zonas.geometria(zona))
    imagenes = {
        "clasicas": features.clasicas(geom, campania),
        "embeddings": features.embeddings(geom, campania),
        "embeddings-1a": features.embeddings_un_anio(geom, campania),
    }

    # Feature extraction happens ONCE per set, chunked and cached: the cells,
    # the ablations and any re-run reuse the same sampled tables.
    tablas, bandas = {}, {}
    cache_dir = REPO_ROOT / ".cache" / "features"
    for fs, img in imagenes.items():
        bandas[fs] = img.bandNames().getInfo()
        log(f"{zona} · muestreando features «{fs}» ({len(bandas[fs])} bandas)…")
        tablas[fs] = clasificar.muestrear_features(
            img, bandas[fs], tabla, cache=cache_dir / f"{zona}_{campania}_{fs}.parquet"
        )
        log(f"  n efectivo = {len(tablas[fs])} de {len(tabla)}")

    def celda(fs: str, tipo: str, tabla_f: pd.DataFrame | None = None) -> pd.DataFrame:
        t = tablas[fs] if tabla_f is None else tabla_f
        return clasificar.entrenar_y_clasificar(
            t[t["set"] == "entrenamiento"],
            t[t["set"] == "validacion_mnc"],
            bandas[fs],
            tipo,
            estandarizar=fs == "clasicas" and tipo == "knn",
        )

    predicciones, modelos_json = {}, {}
    for modelo in MODELOS:
        feature_set, tipo = clasificar.MODELOS[modelo]
        log(f"{zona} · {modelo}…")
        pred = celda(feature_set, tipo)
        met = evaluar.metricas(pred, NOMBRES)
        predicciones[modelo] = pred
        modelos_json[modelo] = {
            "acuerdo_mnc": {"overall": met["overall"], "kappa": met["kappa"], "ic95": met["ic95"], "n": met["n"]},
            "accuracy_independiente": {"overall": None, "ic95": [None, None]},
            "por_clase": met["por_clase"],
            "matriz_confusion": met["matriz_confusion"],
        }
        log(f"  acuerdo={met['overall']:.4f} kappa={met['kappa']:.4f} n={met['n']}")

    log(f"{zona} · ablación A (embeddings de un solo año)…")
    ablacion_a = evaluar.metricas(celda("embeddings-1a", "rf"), NOMBRES)["overall"]
    log(f"  un año={ablacion_a:.4f}")

    comparaciones = []
    for a, b in PARES_MCNEMAR:
        mc = evaluar.mcnemar(predicciones[a], predicciones[b])
        comparaciones.append({"a": a, "b": b, **mc})

    resultado = {
        "campania_validada": campania,
        "muestras": {
            "entrenamiento": int((tabla["set"] == "entrenamiento").sum()),
            "validacion_mnc": int((tabla["set"] == "validacion_mnc").sum()),
            "validacion_independiente": 0,
        },
        "modelos": modelos_json,
        "ablacion_embeddings_un_anio": {"overall": ablacion_a},
        "comparaciones": comparaciones,
    }

    if zona == "rio-cuarto":
        # Same sampled features, block structure ignored: no extra EE sampling.
        aleatoria = split_aleatorio(tabla)["set"].rename_axis("uid").reset_index()
        ablacion_b = {}
        for modelo in ["clasicas-rf", "embeddings-rf"]:
            feature_set, tipo = clasificar.MODELOS[modelo]
            log(f"{zona} · ablación B ({modelo}, split aleatorio)…")
            tabla_rand = tablas[feature_set].drop(columns="set").merge(aleatoria, on="uid")
            met_rand = evaluar.metricas(celda(feature_set, tipo, tabla_rand), NOMBRES)
            ablacion_b[modelo] = {
                "bloques": modelos_json[modelo]["acuerdo_mnc"]["overall"],
                "aleatorio": met_rand["overall"],
            }
            log(f"  aleatorio={met_rand['overall']:.4f}")
        resultado["ablacion_split_aleatorio"] = ablacion_b

    return resultado


# ---------------------------------------------------------------- markdown ---

def fmt(v, pct=True):
    if v is None:
        return "`—`"
    return f"{v * 100:.1f} %" if pct else f"{v:.3f}"


def tabla_2x2(mods: dict, campo: str) -> str:
    def cel(m):
        return fmt(mods[m]["acuerdo_mnc"][campo], pct=campo == "overall")
    return (
        "| | Random Forest | kNN |\n|---|---|---|\n"
        f"| **Clásicas** (89 features) | {cel('clasicas-rf')} | {cel('clasicas-knn')} |\n"
        f"| **Embeddings** (128 features) | {cel('embeddings-rf')} | {cel('embeddings-knn')} |"
    )


def matriz_md(modelo_json: dict) -> str:
    encabezado = "| ref \\ pred | " + " | ".join(NOMBRES[c] for c in ORDEN_DOC) + " |"
    sep = "|---" * (len(ORDEN_DOC) + 1) + "|"
    filas = [
        f"| {NOMBRES[c]} | " + " | ".join(str(v) for v in modelo_json["matriz_confusion"]["filas"][i]) + " |"
        for i, c in enumerate(ORDEN_DOC)
    ]
    return "\n".join([encabezado, sep] + filas)


def por_clase_md(mods: dict) -> str:
    filas = ["| Clase | Modelo | F1 | Producer's | User's | Soporte |", "|---|---|---|---|---|---|"]
    for c in ORDEN_DOC:
        negrita = "**" if c == 4 else ""
        for modelo in MODELOS:
            pc = next(p for p in mods[modelo]["por_clase"] if p["codigo"] == c)
            filas.append(
                f"| {negrita}{NOMBRES[c]}{negrita} | {modelo} | {fmt(pc['f1'], pct=False) if pc['f1'] is not None else '`—`'} "
                f"| {fmt(pc['producer'], pct=False) if pc['producer'] is not None else '`—`'} "
                f"| {fmt(pc['user'], pct=False) if pc['user'] is not None else '`—`'} | {pc['soporte']} |"
            )
    return "\n".join(filas)


def mcnemar_md(metrics: dict) -> str:
    filas = [
        "| Zona | Comparación | Δ acuerdo | p (McNemar) | Conclusión |",
        "|---|---|---|---|---|",
    ]
    for zona_slug, zona_nombre in [("rio-cuarto", "Río Cuarto"), ("pergamino", "Pergamino")]:
        for comp in metrics["zonas"][zona_slug]["comparaciones"]:
            concl = (
                "difieren" if comp["significativo"] else "**no se distinguen con esta muestra**"
            )
            filas.append(
                f"| {zona_nombre} | {comp['a']} vs {comp['b']} | {comp['delta_overall'] * 100:+.1f} pp "
                f"| {comp['p']:.4f} | {concl} |"
            )
    return "\n".join(filas)


def generar_benchmark_md(metrics: dict) -> str:
    rc = metrics["zonas"]["rio-cuarto"]
    pg = metrics["zonas"]["pergamino"]
    fecha = metrics["generado"][:10]
    abl_b = rc.get("ablacion_split_aleatorio", {})

    def abl_b_fila(modelo):
        d = abl_b.get(modelo)
        if not d:
            return f"| Río Cuarto | {modelo} | `—` | `—` | `—` |"
        return (
            f"| Río Cuarto | {modelo} | {fmt(d['bloques'])} | {fmt(d['aleatorio'])} "
            f"| {(d['aleatorio'] - d['bloques']) * 100:+.1f} pp |"
        )

    matrices = "\n\n".join(
        f"### {zona_nombre} · {modelo}\n\n" + matriz_md(zona["modelos"][modelo])
        for zona_nombre, zona in [("Río Cuarto", rc), ("Pergamino", pg)]
        for modelo in MODELOS
    )

    return f"""# BENCHMARK — features clásicas vs Satellite Embeddings de AlphaEarth

> ⚠️ **Este archivo se regenera con `make benchmark` (`scripts/02_benchmark.py`). No se edita a
> mano.** Todo valor `PENDIENTE` o `—` es un número que todavía no corrió. Si aparece un número que
> no salió de una corrida, es un bug del proceso, no un dato.

**Estado:** 🟢 corrida completa contra el MNC · accuracy independiente `PENDIENTE`.
**Última corrida:** {metrics["generado"]} · **Semilla:** {metrics["semilla"]}

Cómo leer estos números —qué se puede llamar accuracy, qué es acuerdo, y qué no se puede concluir—
está en [`METODOLOGIA.md`](METODOLOGIA.md). Leerlo antes de citar cualquier valor de acá.

**Todos los números de este archivo son ACUERDO con el MNC, salvo donde se diga accuracy.** Los
puntos de validación independiente fotointerpretados todavía no están etiquetados; hasta entonces,
las tablas de accuracy quedan en `—` y ninguna conclusión se apoya en ellas.

---

## Setup

| | |
|---|---|
| Zonas | Departamento Río Cuarto (Córdoba) · Partido de Pergamino (Buenos Aires) |
| Campaña validada | {rc["campania_validada"]} (contra MNC; validación independiente `PENDIENTE`) |
| Campaña sin validar | `PENDIENTE` — objetivo 2025/26, capa 3 |
| Clases | soja · maíz · trigo/soja 2ª · maní · pastura/verdeo · no agrícola |
| Split | Bloques espaciales de 5 × 5 km, bloque entero a train o validación |
| Erosión de bordes | 1 píxel sobre la grilla del MNC (~25–30 m; la spec decía «2 px / 20 m» asumiendo dato de 10 m) |
| Resolución | Features a 10 m; referencia MNC a ~25–30 m |

### Muestras

| Zona | Entrenamiento | Validación MNC | Validación independiente | Indeterminados excluidos |
|---|---|---|---|---|
| Río Cuarto | {rc["muestras"]["entrenamiento"]} | {rc["muestras"]["validacion_mnc"]} | `—` | `—` |
| Pergamino | {pg["muestras"]["entrenamiento"]} | {pg["muestras"]["validacion_mnc"]} | `—` | `—` |

**Clases sin soporte en el cruce del MNC:** `pastura/verdeo` no existe en el MNC 2024/25 de ninguna
de las dos zonas (los códigos de verdeo no aparecen en los recortes) y `maní` no existe en Pergamino.
Se reportan con soporte 0 y quedan fuera de los promedios macro — no se rellenan.

### Versiones de datos

| Fuente | Versión / fecha de acceso |
|---|---|
| `COPERNICUS/S2_SR_HARMONIZED` | acceso {fecha} |
| `GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED` | acceso {fecha}, umbral cs ≥ 0.60 |
| `GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL` | acceso {fecha} |
| Mapa Nacional de Cultivos (INTA) | campaña 2024/25 v1, Zenodo `10.5281/zenodo.17652712` (CC-BY-4.0), descargado {fecha} |
| Accuracy que reporta el MNC para esa campaña | `PENDIENTE` — leer del informe oficial; es el techo del acuerdo |

---

## Resultado principal — el 2×2

Comparar **filas**: es la pregunta del proyecto (¿qué aportan los embeddings?). Comparar columnas
responde otra cosa (¿qué clasificador anda mejor?) y es secundaria.

### Río Cuarto — accuracy independiente, IC 95 %

`PENDIENTE` — faltan los puntos fotointerpretados.

### Río Cuarto — acuerdo con el MNC

*Acuerdo, no accuracy. Ver [`METODOLOGIA.md → 1`](METODOLOGIA.md#1-el-mapa-nacional-de-cultivos-es-referencia-no-verdad-de-campo).*

{tabla_2x2(rc["modelos"], "overall")}

### Pergamino — accuracy independiente, IC 95 %

`PENDIENTE` — faltan los puntos fotointerpretados.

### Pergamino — acuerdo con el MNC

{tabla_2x2(pg["modelos"], "overall")}

### Kappa

Se reporta porque se espera verlo. **Ninguna conclusión se apoya en kappa** — ver
[`METODOLOGIA.md → 5.2`](METODOLOGIA.md#52-sobre-kappa).

| Zona | clásicas-rf | clásicas-knn | embeddings-rf | embeddings-knn |
|---|---|---|---|---|
| Río Cuarto | {" | ".join(fmt(rc["modelos"][m]["acuerdo_mnc"]["kappa"], pct=False) for m in MODELOS)} |
| Pergamino | {" | ".join(fmt(pg["modelos"][m]["acuerdo_mnc"]["kappa"], pct=False) for m in MODELOS)} |

### ¿Las diferencias son reales?

Test de McNemar sobre aciertos pareados. `p ≥ 0.05` significa **"no se distinguen con esta muestra"**,
y eso es lo que se publica — no el modelo que quedó medio punto arriba.

{mcnemar_md(metrics)}

---

## Matrices de confusión

Filas = referencia (MNC), columnas = predicción. Las de Pergamino conservan la fila y la columna de
`maní` vacías: la clase no existe en esa zona y se excluye del promedio macro, no se cuenta como
cero. Ídem `pastura/verdeo` en las dos zonas.

{matrices}

---

## Por clase

F1, producer's y user's accuracy, con soporte al lado — un F1 sin soporte no se lee. `maní` va en
negrita porque es la clase que decide el benchmark.

### Río Cuarto

{por_clase_md(rc["modelos"])}

### Pergamino

{por_clase_md(pg["modelos"])}

---

## Ablaciones

Cada una aísla una decisión de método. Son resultados por derecho propio, no notas al pie.

### A. El desfase calendario / campaña de los embeddings

Configuración principal: embeddings de los **dos** años calendario que solapan la campaña (128
features). Ablación: **solo el segundo año**, el del verano (64 features). Ambas con RF.

| Zona | Dos años (128) | Un año (64) | Δ |
|---|---|---|---|
| Río Cuarto | {fmt(rc["modelos"]["embeddings-rf"]["acuerdo_mnc"]["overall"])} | {fmt(rc["ablacion_embeddings_un_anio"]["overall"])} | {(rc["ablacion_embeddings_un_anio"]["overall"] - rc["modelos"]["embeddings-rf"]["acuerdo_mnc"]["overall"]) * 100:+.1f} pp |
| Pergamino | {fmt(pg["modelos"]["embeddings-rf"]["acuerdo_mnc"]["overall"])} | {fmt(pg["ablacion_embeddings_un_anio"]["overall"])} | {(pg["ablacion_embeddings_un_anio"]["overall"] - pg["modelos"]["embeddings-rf"]["acuerdo_mnc"]["overall"]) * 100:+.1f} pp |

Cuantifica cuánto cuesta que el dataset esté indexado por año calendario y la campaña no lo esté.
Ver [`METODOLOGIA.md → 7.1`](METODOLOGIA.md#7-limitaciones-declaradas).

### B. Cuánto infla el split aleatorio

Mismo modelo, misma muestra, dos maneras de partirla.

| Zona | Modelo | Bloques 5 km | Aleatorio | Δ (inflación) |
|---|---|---|---|---|
{abl_b_fila("clasicas-rf")}
{abl_b_fila("embeddings-rf")}

Sirve para comparar contra benchmarks publicados con split aleatorio, que es la mayoría.

---

## Superficie sembrada estimada

`PENDIENTE` — la corrección por matriz de error (Olofsson et al., 2014) se calcula después de la
validación independiente; hacerla contra el acuerdo con el MNC mediría el área del MNC, no la
del mapa.

---

## Lectura de los resultados

`PENDIENTE` — se escribe a mano después de revisar esta corrida (es interpretación, no dato: es la
única sección de este archivo que se edita, y el regenerador la pisa marcada como pendiente hasta
que exista la validación independiente).

## Cómo reproducir

```bash
cp .env.example .env    # GEE_SERVICE_ACCOUNT, GEE_KEY_PATH, MNC_DIR
make install
make muestras           # solo si cambian las zonas o la campaña
make benchmark          # corre las 4 celdas + ablaciones y reescribe este archivo
```

Las muestras están versionadas en `data/muestras/`, así que `make benchmark` reproduce estos números
exactos sin volver a muestrear. La semilla es {metrics["semilla"]} y está en `settings.py`.
"""


def main() -> None:
    ee_client.init()
    campania = settings.mnc_campania

    metrics = {
        "generado": datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "semilla": SEED,
        "zonas": {zona: correr_zona(zona, campania) for zona in zonas.ZONAS},
    }

    ruta_json = DATA_DIR / "metrics.json"
    ruta_json.write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n")
    log(f"escrito {ruta_json}")

    ruta_md = REPO_ROOT / "docs" / "BENCHMARK.md"
    ruta_md.write_text(generar_benchmark_md(metrics))
    log(f"escrito {ruta_md}")


if __name__ == "__main__":
    main()
