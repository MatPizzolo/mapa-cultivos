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

import rasterio

from mapa_cultivos import tiles
from mapa_cultivos.referencia import capa_remapeada
from mapa_cultivos.settings import REPO_ROOT, settings
from mapa_cultivos.zonas import ZONAS


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

    colores, indice = tiles.paleta_leyenda()

    if args.mnc:
        for zona in [args.zona] if args.zona else list(ZONAS):
            capa = capa_remapeada(zona)
            n = tiles.tilear(capa.datos, capa.transform, capa.crs, destino,
                              partes=(args.corrida, zona, campania, "mnc"),
                              colores=colores, indice=indice)
            print(f"{zona}/mnc: {n} tiles")
    elif args.tif and args.zona and args.modelo:
        with rasterio.open(args.tif) as src:
            n = tiles.tilear(src.read(1), src.transform, src.crs, destino,
                              partes=(args.corrida, args.zona, campania, args.modelo),
                              colores=colores, indice=indice)
        print(f"{args.zona}/{args.modelo}: {n} tiles")
    else:
        parser.error("usar --mnc, o bien --tif con --zona y --modelo")


if __name__ == "__main__":
    main()
