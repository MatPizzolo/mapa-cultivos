"""The four models of the 2×2 — defined in ONE place and iterated (SPEC §5).

Training and inference happen in Earth Engine (ee.Classifier). To stay inside
EE's 5-minute interactive limit, feature extraction is decoupled from training:

1. `muestrear_features()` samples the feature image at the points in parallel
   chunks (with an on-disk cache) — one heavy-but-bounded EE call per chunk.
2. `entrenar_y_clasificar()` trains an ee.Classifier on the materialized table
   and classifies the validation table. These calls carry literal values, so
   they are fast and independent of the S2 mosaic graph.

The classifier itself is NEVER reimplemented locally.
"""

import concurrent.futures
from pathlib import Path

import ee
import numpy as np
import pandas as pd

from .settings import SEED

MODELOS = {
    "clasicas-rf": ("clasicas", "rf"),
    "clasicas-knn": ("clasicas", "knn"),
    "embeddings-rf": ("embeddings", "rf"),
    "embeddings-knn": ("embeddings", "knn"),
}

_CHUNK = 200
_WORKERS = 6


def _clasificador(tipo: str) -> ee.Classifier:
    if tipo == "rf":
        return ee.Classifier.smileRandomForest(
            numberOfTrees=300, minLeafPopulation=5, bagFraction=0.5, seed=SEED
        )
    return ee.Classifier.smileKNN(k=5, metric="EUCLIDEAN")


def _muestrear_chunk(img: ee.Image, bandas: list[str], filas: pd.DataFrame, scale: int) -> pd.DataFrame:
    puntos = ee.FeatureCollection(
        [
            ee.Feature(ee.Geometry.Point([float(f.lon), float(f.lat)]), {"uid": int(uid)})
            for uid, f in filas.iterrows()
        ]
    )
    columnas = ["uid"] + bandas
    valores = (
        img.sampleRegions(collection=puntos, properties=["uid"], scale=scale, tileScale=4)
        .reduceColumns(ee.Reducer.toList().repeat(len(columnas)), columnas)
        .get("list")
        .getInfo()
    )
    return pd.DataFrame(dict(zip(columnas, valores)))


def muestrear_features(
    img: ee.Image,
    bandas: list[str],
    tabla: pd.DataFrame,
    scale: int = 10,
    cache: Path | None = None,
) -> pd.DataFrame:
    """Sample `img` at every point of `tabla` (uid = row index). Points whose
    features are masked (e.g. fully clouded window) are dropped by EE; the
    caller reports the effective n. Cached to disk: re-runs skip EE entirely.
    """
    if cache is not None and cache.exists():
        return pd.read_parquet(cache)

    chunks = [tabla.iloc[i : i + _CHUNK] for i in range(0, len(tabla), _CHUNK)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=_WORKERS) as pool:
        partes = list(pool.map(lambda c: _muestrear_chunk(img, bandas, c, scale), chunks))

    valores = pd.concat(partes, ignore_index=True)
    salida = valores.merge(
        tabla[["clase", "set"]].reset_index(names="uid"), on="uid", how="left"
    )
    if cache is not None:
        cache.parent.mkdir(parents=True, exist_ok=True)
        salida.to_parquet(cache)
    return salida


def _fc_tabla(tabla: pd.DataFrame, columnas: list[str]) -> ee.FeatureCollection:
    registros = tabla[columnas].round(6).to_dict("records")
    return ee.FeatureCollection([ee.Feature(None, r) for r in registros])


def entrenar_y_clasificar(
    train: pd.DataFrame,
    val: pd.DataFrame,
    bandas: list[str],
    tipo: str,
    estandarizar: bool = False,
    chunk_val: int = 800,
) -> pd.DataFrame:
    """Train one cell on the sampled table and classify the validation table.

    z-score (train stats only) applies exclusively to clasicas+kNN: mixed
    scales break euclidean distance. Embeddings come homogeneous and RF is
    scale-invariant — the asymmetry is deliberate (SPEC §5).
    """
    train = train.copy()
    val = val.copy()
    if estandarizar:
        media = train[bandas].mean()
        desvio = train[bandas].std(ddof=0).replace(0, 1.0)
        train[bandas] = (train[bandas] - media) / desvio
        val[bandas] = (val[bandas] - media) / desvio

    entrenado = _clasificador(tipo).train(
        features=_fc_tabla(train, bandas + ["clase"]),
        classProperty="clase",
        inputProperties=bandas,
    )

    partes = []
    for i in range(0, len(val), chunk_val):
        parte = val.iloc[i : i + chunk_val]
        clasificado = _fc_tabla(parte, bandas + ["uid", "clase"]).classify(entrenado)
        valores = clasificado.reduceColumns(
            ee.Reducer.toList().repeat(3), ["uid", "clase", "classification"]
        ).get("list").getInfo()
        partes.append(pd.DataFrame({"uid": valores[0], "clase": valores[1], "prediccion": valores[2]}))

    return pd.concat(partes, ignore_index=True).astype(int)
