"""Shared tiler: classified raster → XYZ tiles (zooms 9-13), palette PNG.

Extracted from scripts/04_tiles.py so scripts/05 (disagreement viewer) can
reuse the same tiler with a different palette. The PNG colors ARE the data
contract: the pixel inspector in the frontend maps tile colors back to
classes, so the palette must always be an explicit parameter, never a
hidden default read from inside this module.
"""

import json
from pathlib import Path

import mercantile
import numpy as np
import rasterio
from PIL import Image
from rasterio.crs import CRS
from rasterio.transform import from_bounds
from rasterio.warp import Resampling, reproject

from mapa_cultivos.settings import DATA_DIR

ZOOM_MIN, ZOOM_MAX = 9, 13
TAM = 256


def paleta_leyenda() -> tuple[list[int], dict[int, int]]:
    """256-entry PIL palette from leyenda.json + code→palette-index map."""
    leyenda = json.loads((DATA_DIR / "leyenda.json").read_text())
    colores = [0] * 768
    indice = {}
    for i, clase in enumerate(leyenda["clases"]):
        r, g, b = (int(clase["color"][j : j + 2], 16) for j in (1, 3, 5))
        colores[i * 3 : i * 3 + 3] = [r, g, b]
        indice[clase["codigo"]] = i
    return colores, indice


def tilear(datos: np.ndarray, transform, crs, destino: Path, partes: tuple[str, ...],
           colores: list[int], indice: dict[int, int], nodata: int = 255) -> int:
    remap = np.full(256, nodata, dtype=np.uint8)
    for codigo, i in indice.items():
        remap[codigo] = i

    with rasterio.Env():
        bounds = rasterio.transform.array_bounds(*datos.shape, transform)
        lb = rasterio.warp.transform_bounds(crs, CRS.from_epsg(4326), *bounds)
        escritos = 0
        for z in range(ZOOM_MIN, ZOOM_MAX + 1):
            for tile in mercantile.tiles(*lb, [z]):
                tb = mercantile.xy_bounds(tile)
                destino_arr = np.full((TAM, TAM), nodata, dtype=np.uint8)
                reproject(
                    source=datos,
                    destination=destino_arr,
                    src_transform=transform,
                    src_crs=crs,
                    dst_transform=from_bounds(tb.left, tb.bottom, tb.right, tb.top, TAM, TAM),
                    dst_crs=CRS.from_epsg(3857),
                    resampling=Resampling.nearest,
                    src_nodata=nodata,
                    dst_nodata=nodata,
                )
                if (destino_arr == nodata).all():
                    continue
                img = Image.fromarray(remap[destino_arr], mode="P")
                img.putpalette(colores)
                img.info["transparency"] = nodata
                ruta = destino.joinpath(*partes) / str(z) / str(tile.x)
                ruta.mkdir(parents=True, exist_ok=True)
                img.save(ruta / f"{tile.y}.png", transparency=nodata, optimize=True)
                escritos += 1
    return escritos
