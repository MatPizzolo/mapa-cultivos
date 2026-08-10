"""Classified raster → XYZ tiles (zooms 9–13), palette PNG with legend colors.

Two sources (SPEC §9 + the inspector's MNC row):

  uv run python scripts/04_tiles.py --mnc                 # MNC cross as pseudo-model
  uv run python scripts/04_tiles.py --tif mapa.tif --zona rio-cuarto --modelo embeddings-rf

Tiles land in tiles/{corrida}/{zona}/{campania}/{modelo}/{z}/{x}/{y}.png (local,
gitignored). Upload to the GCS bucket is a separate manual step until the
bucket exists:  gsutil -m rsync -r tiles/ gs://<bucket>/tiles/

The PNG colors ARE the data contract: the pixel inspector in the frontend maps
tile colors back to classes via leyenda.json, so the palette must come from
there and from nowhere else.
"""

import argparse
import datetime
import json

import mercantile
import numpy as np
import rasterio
from PIL import Image
from rasterio.crs import CRS
from rasterio.transform import from_bounds
from rasterio.warp import Resampling, reproject

from mapa_cultivos.referencia import EXCLUIDO, capa_remapeada
from mapa_cultivos.settings import DATA_DIR, REPO_ROOT, settings
from mapa_cultivos.zonas import ZONAS

ZOOM_MIN, ZOOM_MAX = 9, 13
TAM = 256


def paleta() -> tuple[list[int], dict[int, int]]:
    """256-entry PIL palette from leyenda.json + code→palette-index map."""
    leyenda = json.loads((DATA_DIR / "leyenda.json").read_text())
    colores = [0] * 768
    indice = {}
    for i, clase in enumerate(leyenda["clases"]):
        r, g, b = (int(clase["color"][j : j + 2], 16) for j in (1, 3, 5))
        colores[i * 3 : i * 3 + 3] = [r, g, b]
        indice[clase["codigo"]] = i
    return colores, indice


def tilear(datos: np.ndarray, transform, crs, destino, corrida: str, zona: str,
           campania: str, modelo: str) -> int:
    colores, indice = paleta()
    remap = np.full(256, 255, dtype=np.uint8)
    for codigo, i in indice.items():
        remap[codigo] = i

    with rasterio.Env():
        bounds = rasterio.transform.array_bounds(*datos.shape, transform)
        lb = rasterio.warp.transform_bounds(crs, CRS.from_epsg(4326), *bounds)
        escritos = 0
        for z in range(ZOOM_MIN, ZOOM_MAX + 1):
            for tile in mercantile.tiles(*lb, [z]):
                tb = mercantile.xy_bounds(tile)
                destino_arr = np.full((TAM, TAM), EXCLUIDO, dtype=np.uint8)
                reproject(
                    source=datos,
                    destination=destino_arr,
                    src_transform=transform,
                    src_crs=crs,
                    dst_transform=from_bounds(tb.left, tb.bottom, tb.right, tb.top, TAM, TAM),
                    dst_crs=CRS.from_epsg(3857),
                    resampling=Resampling.nearest,
                    src_nodata=EXCLUIDO,
                    dst_nodata=EXCLUIDO,
                )
                if (destino_arr == EXCLUIDO).all():
                    continue
                img = Image.fromarray(remap[destino_arr], mode="P")
                img.putpalette(colores)
                img.info["transparency"] = 255
                ruta = destino / corrida / zona / campania / modelo / str(z) / str(tile.x)
                ruta.mkdir(parents=True, exist_ok=True)
                img.save(ruta / f"{tile.y}.png", transparency=255, optimize=True)
                escritos += 1
    return escritos


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mnc", action="store_true", help="tilear el cruce del MNC como pseudo-modelo")
    parser.add_argument("--tif", help="GeoTIFF clasificado exportado de EE (códigos de leyenda)")
    parser.add_argument("--zona", choices=list(ZONAS))
    parser.add_argument("--modelo")
    parser.add_argument("--corrida", default=datetime.date.today().isoformat())
    args = parser.parse_args()

    campania = settings.mnc_campania
    destino = REPO_ROOT / "tiles"

    if args.mnc:
        for zona in [args.zona] if args.zona else list(ZONAS):
            capa = capa_remapeada(zona)
            n = tilear(capa.datos, capa.transform, capa.crs, destino, args.corrida,
                       zona, campania, "mnc")
            print(f"{zona}/mnc: {n} tiles")
    elif args.tif and args.zona and args.modelo:
        with rasterio.open(args.tif) as src:
            n = tilear(src.read(1), src.transform, src.crs, destino, args.corrida,
                       args.zona, campania, args.modelo)
        print(f"{args.zona}/{args.modelo}: {n} tiles")
    else:
        parser.error("usar --mnc, o bien --tif con --zona y --modelo")


if __name__ == "__main__":
    main()
