import numpy as np
import rasterio
from rasterio.transform import from_origin

from mapa_cultivos import tiles


def test_paleta_leyenda_cubre_las_seis_clases():
    colores, indice = tiles.paleta_leyenda()
    assert len(colores) == 768
    assert sorted(indice) == [0, 1, 2, 3, 4, 5]


def test_tilear_raster_sintetico(tmp_path):
    datos = np.full((256, 256), 255, dtype=np.uint8)
    datos[100:200, 100:200] = 1  # un cuadrado de "soja" cerca de Río Cuarto
    transform = from_origin(-64.4, -33.0, 0.001, 0.001)
    colores, indice = tiles.paleta_leyenda()
    n = tiles.tilear(
        datos, transform, rasterio.crs.CRS.from_epsg(4326),
        tmp_path, ("t", "z", "c", "m"), colores, indice,
    )
    assert n > 0
    assert any((tmp_path / "t" / "z" / "c" / "m").rglob("*.png"))
