"""Reference layer: the MNC (INTA) remapped to the project legend.

The MNC 2024/25 ships as TWO national rasters — winter 2024 and summer 2025
(Zenodo 10.5281/zenodo.17652712, CC-BY-4.0). The project legend is derived by
CROSSING both seasons per pixel; the rules live in data/leyenda.json
("mapeo_mnc.reglas_cruce") and are implemented here, in one place.

Design note (deviation from SPEC §3 as originally drafted): the MNC is read
LOCALLY with rasterio instead of being ingested as an EE asset, because EE
ingestion requires GCS staging and the bucket is a pending input. Sampling a
30 m raster clipped to two departments is light; features, training and
inference stay 100% in Earth Engine. Revisit if the MNC ever lands in EE.
"""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import rasterio
import rasterio.mask

from .settings import settings
from .zonas import geometria

# MNC source codes (from the official .qml files — see data/leyenda.json).
INV_CEREAL = 16
INV_NO_AGRICOLA = 20
VER_MAIZ = 10
VER_SOJA = 11
VER_MANI = 16
VER_NO_AGRICOLA = 22
VER_VERDEO_MAIZ = 27
VER_VERDEO_SORGO = 28

# Output value for "no class": excluded from sampling, never forced.
EXCLUIDO = 255


@dataclass
class CapaReferencia:
    datos: np.ndarray          # uint8, legend codes 0..5, EXCLUIDO elsewhere
    transform: rasterio.Affine
    crs: rasterio.crs.CRS
    resolucion_m: float


def _ruta_mnc(temporada: str) -> Path:
    # TODO(mateo): mover los .tif descargados de Zenodo a una ruta estable y
    # configurarla; por ahora se leen del directorio que indique MNC_DIR.
    base = Path(settings.mnc_dir).expanduser()
    nombre = {"invierno": "MNC_inv24.tif", "verano": "MNC_ver25.tif"}[temporada]
    ruta = base / nombre
    if not ruta.exists():
        raise FileNotFoundError(
            f"PENDIENTE: falta {ruta}. Descargar de Zenodo 10.5281/zenodo.17652712 "
            "y setear MNC_DIR en .env."
        )
    return ruta


def _leer_recorte(temporada: str, zona: str) -> tuple[np.ndarray, rasterio.Affine, rasterio.crs.CRS]:
    geom = geometria(zona)
    with rasterio.open(_ruta_mnc(temporada)) as src:
        datos, transform = rasterio.mask.mask(src, [geom], crop=True, nodata=EXCLUIDO)
        return datos[0], transform, src.crs


def cruzar(inv: np.ndarray, ver: np.ndarray) -> np.ndarray:
    """Pure winter × summer cross → legend codes. Rules mirror leyenda.json."""
    salida = np.full(inv.shape, EXCLUIDO, dtype=np.uint8)

    es_cereal_inv = inv == INV_CEREAL
    # Order matters only for soja vs trigo/soja: same summer code, split by winter.
    salida[(ver == VER_SOJA) & es_cereal_inv] = 3          # trigo/soja 2ª
    salida[(ver == VER_SOJA) & ~es_cereal_inv] = 1         # soja de primera
    salida[ver == VER_MAIZ] = 2                            # maíz (incl. cereal+maíz)
    salida[ver == VER_MANI] = 4                            # maní
    salida[(ver == VER_VERDEO_MAIZ) | (ver == VER_VERDEO_SORGO)] = 5  # pastura/verdeo
    salida[(inv == INV_NO_AGRICOLA) & (ver == VER_NO_AGRICOLA)] = 0   # no agrícola
    # Everything else (girasol, sorgo, poroto, papa, barbecho/barbecho, máscaras,
    # nodata) stays EXCLUIDO: it does not enter sampling nor evaluation.
    return salida


def capa_remapeada(zona: str) -> CapaReferencia:
    """Cross winter × summer MNC and remap to the 6-class legend for one zone."""
    inv, transform, crs = _leer_recorte("invierno", zona)
    ver, transform_v, _ = _leer_recorte("verano", zona)
    if inv.shape != ver.shape or transform != transform_v:
        raise ValueError(
            f"Los recortes de invierno y verano no están alineados para {zona}: "
            f"{inv.shape} vs {ver.shape}. Verificar que ambos .tif sean de la misma corrida."
        )

    salida = cruzar(inv, ver)

    if not crs.is_projected:
        # 30 m nominal; the exact ground size of a geographic pixel varies little
        # at these latitudes and only drives block/erosion sizing.
        res_m = abs(transform.a) * 111_320 * np.cos(np.deg2rad(-33.5))
    else:
        res_m = abs(transform.a)

    return CapaReferencia(datos=salida, transform=transform, crs=crs, resolucion_m=res_m)
