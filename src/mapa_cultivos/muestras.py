"""Stratified sampling over the remapped MNC (METODOLOGIA §2 and §3).

- Stratified BY CLASS, not by area: minority classes need statistical power.
  The sample is therefore NOT area-representative (area estimation corrects
  for this later via Olofsson).
- Border erosion before sampling: only lot interiors are sampled. The MNC is
  30 m, so one pixel of erosion ≈ 30 m (the spec's "2 px / 20 m" assumed 10 m
  data; intent preserved, actual figure reported honestly).
- Spatial split by 5×5 km blocks: a whole block goes to train or validation,
  never split. No validation pixel shares a lot with a training pixel.
- SEED fixed. Output CSVs are versioned in data/muestras/ for reproducibility.
"""

import numpy as np
import pandas as pd
import rasterio.warp
from scipy import ndimage

from .referencia import EXCLUIDO, CapaReferencia, capa_remapeada
from .settings import SEED

OBJETIVO_ENTRENAMIENTO = 500   # points per class per zone
OBJETIVO_VALIDACION = 300
MINIMO_POR_CLASE = 100         # below this the class is reported as low-support
BLOQUE_M = 5_000               # spatial block side
FRACCION_BLOQUES_ENTRENAMIENTO = 0.7
EROSION_PX = 1                 # ≈30 m on the MNC grid

CLASES = [0, 1, 2, 3, 4, 5]


def _erosionar(datos: np.ndarray) -> np.ndarray:
    """Per-class binary erosion; returns the layer with borders EXCLUIDO."""
    salida = np.full_like(datos, EXCLUIDO)
    for clase in CLASES:
        mascara = datos == clase
        interior = ndimage.binary_erosion(
            mascara, structure=np.ones((3, 3)), iterations=EROSION_PX
        )
        salida[interior] = clase
    return salida


def muestrear_zona(zona: str, campania: str) -> pd.DataFrame:
    """Sample one zone. Returns a table with lon, lat, clase, bloque and set."""
    capa = capa_remapeada(zona)
    datos = _erosionar(capa.datos)
    rng = np.random.default_rng(SEED)

    bloque_px = max(1, round(BLOQUE_M / capa.resolucion_m))
    filas, cols = np.nonzero(datos != EXCLUIDO)
    clases_px = datos[filas, cols]
    bloques = (filas // bloque_px).astype(np.int64) * 100_000 + (cols // bloque_px)

    # Whole blocks to train or validation — the shuffle is the only random draw
    # besides the per-class subsampling, both under the fixed seed.
    unicos = np.unique(bloques)
    rng.shuffle(unicos)
    n_train = int(len(unicos) * FRACCION_BLOQUES_ENTRENAMIENTO)
    bloques_train = set(unicos[:n_train].tolist())
    en_train = np.isin(bloques, list(bloques_train))

    partes = []
    for clase in CLASES:
        for set_nombre, en_set, objetivo in [
            ("entrenamiento", en_train, OBJETIVO_ENTRENAMIENTO),
            ("validacion_mnc", ~en_train, OBJETIVO_VALIDACION),
        ]:
            idx = np.nonzero((clases_px == clase) & en_set)[0]
            if len(idx) > objetivo:
                idx = rng.choice(idx, size=objetivo, replace=False)
            partes.append(
                pd.DataFrame(
                    {
                        "fila": filas[idx],
                        "col": cols[idx],
                        "clase": clase,
                        "bloque": bloques[idx],
                        "set": set_nombre,
                    }
                )
            )

    tabla = pd.concat(partes, ignore_index=True)

    # Pixel centers → lon/lat (EE samples features at these coordinates).
    xs, ys = rasterio.transform.xy(capa.transform, tabla["fila"], tabla["col"])
    lons, lats = rasterio.warp.transform(capa.crs, "EPSG:4326", xs, ys)
    tabla["lon"] = np.round(lons, 6)
    tabla["lat"] = np.round(lats, 6)
    tabla.insert(0, "campania", campania)
    tabla.insert(0, "zona", zona)

    return tabla[["zona", "campania", "clase", "lon", "lat", "fila", "col", "bloque", "set"]]


def reporte_soporte(tabla: pd.DataFrame) -> pd.DataFrame:
    """Support per class and set, flagging low-support classes explicitly."""
    soporte = tabla.groupby(["clase", "set"]).size().unstack(fill_value=0)
    soporte["bajo_soporte"] = soporte.min(axis=1) < MINIMO_POR_CLASE
    return soporte
