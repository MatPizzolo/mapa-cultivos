"""Export classified maps from EE to GCS as GeoTIFF (SPEC §3, §9).

The classifier is trained on the SAME cached feature tables the benchmark used
(single source of truth for training data); inference over the full department
runs server-side and lands in the bucket. Tiling happens later with 04_tiles.py.
"""

from pathlib import Path

import ee
import pandas as pd

from . import clasificar, features
from .settings import REPO_ROOT, settings
from .zonas import geometria


def _tabla_cacheada(zona: str, campania: str, feature_set: str) -> pd.DataFrame:
    ruta = REPO_ROOT / ".cache" / "features" / f"{zona}_{campania}_{feature_set}.parquet"
    if not ruta.exists():
        raise FileNotFoundError(
            f"Falta {ruta}: correr `make benchmark` primero — el export entrena con "
            "las mismas tablas de features que el benchmark."
        )
    return pd.read_parquet(ruta)


def exportar_mapa(zona: str, campania: str, modelo: str, corrida: str) -> ee.batch.Task:
    if not settings.gcs_tiles_bucket:
        raise RuntimeError(
            "PENDIENTE: falta GCS_TILES_BUCKET en .env — los exports de EE "
            "necesitan un bucket de destino."
        )
    feature_set, tipo = clasificar.MODELOS[modelo]
    geom = ee.Geometry(geometria(zona))
    img = getattr(features, feature_set)(geom, campania)
    bandas = img.bandNames().getInfo()

    tabla = _tabla_cacheada(zona, campania, feature_set)
    train = tabla[tabla["set"] == "entrenamiento"].copy()

    if feature_set == "clasicas" and tipo == "knn":
        media = train[bandas].mean()
        desvio = train[bandas].std(ddof=0).replace(0, 1.0)
        train[bandas] = (train[bandas] - media) / desvio
        img = (
            img.select(bandas)
            .subtract(ee.Image.constant(media[bandas].tolist()).rename(bandas))
            .divide(ee.Image.constant(desvio[bandas].tolist()).rename(bandas))
        )

    entrenado = clasificar._clasificador(tipo).train(
        features=clasificar._fc_tabla(train, bandas + ["clase"]),
        classProperty="clase",
        inputProperties=bandas,
    )

    mapa = img.classify(entrenado).toByte().clip(geom)
    tarea = ee.batch.Export.image.toCloudStorage(
        image=mapa,
        description=f"{zona}_{campania}_{modelo}"[:100].replace("/", "-"),
        bucket=settings.gcs_tiles_bucket,
        fileNamePrefix=f"exports/{corrida}/{zona}_{campania}_{modelo}",
        region=geom,
        scale=10,
        maxPixels=1e10,
        fileFormat="GeoTIFF",
        formatOptions={"cloudOptimized": True},
    )
    tarea.start()
    return tarea
