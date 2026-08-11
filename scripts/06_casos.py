"""Exploratory analysis: find candidate patches for the disagreement tour.

For each zone, crosses clasicas-rf vs embeddings-rf (mapa_cultivos.desacuerdo.cruzar),
labels 8-connected disagreement components (scipy.ndimage.label), keeps the 10
largest, and reports per patch: centroid lon/lat, approximate hectares (computed
from the pixel size at the patch's own latitude, not a hardcoded constant — pixel
size in degrees varies little across a department, but ground area per degree of
longitude shrinks with latitude), and the modal class each raster assigns within
the patch. This is how the three tour cases (scripts/06 output, curated into
frontend/app.js CASOS) get picked — see docs/SPEC.md §2 and task-8-brief.md.

This script is exploratory evidence, not a regenerated-artifact script like
02_benchmark.py or 05_desacuerdo.py: its stdout is read by a human, not written
back to a versioned JSON.

  uv run python scripts/06_casos.py --exports-dir /path/to/exports --campania 2024-25
"""

import argparse
import math
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage

from mapa_cultivos import desacuerdo
from mapa_cultivos.settings import DATA_DIR, settings
from mapa_cultivos.zonas import ZONAS

STRUCTURE_8CONN = np.ones((3, 3), dtype=int)
N_MAYORES = 10


def _nombres_clases() -> dict[int, str]:
    import json

    leyenda = json.loads((DATA_DIR / "leyenda.json").read_text())
    return {c["codigo"]: c["clase"] for c in leyenda["clases"]}


def _moda(valores: np.ndarray, n_clases: int) -> int:
    """Most frequent class code among the pixels of a patch."""
    conteo = np.bincount(valores, minlength=n_clases)
    return int(conteo.argmax())


def _hectareas_pixel(transform: rasterio.Affine, lat_deg: float) -> float:
    """Approximate hectares per pixel at a given latitude, for a raster in
    EPSG:4326 (degrees). Ground distance per degree of longitude shrinks with
    cos(latitude); per degree of latitude is ~constant. Not hardcoded: derived
    from the transform's own pixel size each time this is called.
    """
    ancho_deg = abs(transform.a)
    alto_deg = abs(transform.e)
    m_por_grado_lat = 111_320.0
    m_por_grado_lon = 111_320.0 * math.cos(math.radians(lat_deg))
    ancho_m = ancho_deg * m_por_grado_lon
    alto_m = alto_deg * m_por_grado_lat
    return (ancho_m * alto_m) / 10_000.0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--exports-dir", required=True, help="directorio con los GeoTIFF clasificados exportados de EE")
    parser.add_argument("--campania", default=settings.mnc_campania)
    args = parser.parse_args()

    exports_dir = Path(args.exports_dir)
    campania = args.campania
    nombres = _nombres_clases()
    n_clases = max(nombres) + 1

    for zona in ZONAS:
        ruta_a = exports_dir / f"{zona}_{campania}_clasicas-rf.tif"
        ruta_b = exports_dir / f"{zona}_{campania}_embeddings-rf.tif"
        for ruta in (ruta_a, ruta_b):
            if not ruta.exists():
                raise SystemExit(f"Falta el GeoTIFF esperado: {ruta}")

        with rasterio.open(ruta_a) as src_a, rasterio.open(ruta_b) as src_b:
            if src_a.shape != src_b.shape:
                raise SystemExit(
                    f"Shapes distintos para {zona}: "
                    f"{ruta_a.name} tiene {src_a.shape}, {ruta_b.name} tiene {src_b.shape}"
                )
            datos_a = src_a.read(1)
            datos_b = src_b.read(1)
            transform = src_a.transform

        cruce = desacuerdo.cruzar(datos_a, datos_b)
        etiquetas, n_componentes = ndimage.label(cruce == 1, structure=STRUCTURE_8CONN)
        if n_componentes == 0:
            print(f"\n=== {zona}: sin componentes de desacuerdo ===")
            continue

        tamanios = np.bincount(etiquetas.ravel())
        tamanios[0] = 0  # background is label 0, never a candidate
        mayores = np.argsort(tamanios)[::-1][:N_MAYORES]

        print(f"\n=== {zona}: {n_componentes} componentes, top {min(N_MAYORES, n_componentes)} ===")
        print(f"{'#':>3} {'px':>7} {'ha':>8} {'lat':>10} {'lon':>11}  {'clasicas-rf':<16} {'embeddings-rf':<16}")
        for rank, etiqueta in enumerate(mayores, start=1):
            if tamanios[etiqueta] == 0:
                break
            filas, cols = np.where(etiquetas == etiqueta)
            fila_c, col_c = filas.mean(), cols.mean()
            lon, lat = rasterio.transform.xy(transform, fila_c, col_c)

            n_px = len(filas)
            ha = n_px * _hectareas_pixel(transform, lat)

            clase_a = nombres[_moda(datos_a[filas, cols], n_clases)]
            clase_b = nombres[_moda(datos_b[filas, cols], n_clases)]

            print(
                f"{rank:>3} {n_px:>7} {ha:>8.1f} {lat:>10.5f} {lon:>11.5f}  "
                f"{clase_a:<16} {clase_b:<16}"
            )


if __name__ == "__main__":
    main()
