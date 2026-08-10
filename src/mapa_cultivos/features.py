"""The two feature sets, both built server-side in Earth Engine (SPEC §4).

clasicas():   6 phenological windows × (10 bands + 4 indices) + 5 campaign-wide
              NDVI stats = 89 features. Cloud Score+ ``cs`` < 0.60 masked out.
embeddings(): AlphaEarth annual embeddings, the two calendar years overlapping
              the campaign concatenated = 128 features. The calendar/campaign
              mismatch is a DECLARED limitation, not a bug (METODOLOGIA §7.1).
"""

import ee

from .zonas import anios_embedding, ventana_campania

UMBRAL_CS = 0.60
BANDAS = ["B2", "B3", "B4", "B5", "B6", "B7", "B8", "B8A", "B11", "B12"]

# (suffix, month offsets from July 1st) — six two-month windows (SPEC §4.1)
VENTANAS = [("w1", 0), ("w2", 2), ("w3", 4), ("w4", 6), ("w5", 8), ("w6", 10)]


def _coleccion_s2(geom: ee.Geometry, inicio: ee.Date, fin: ee.Date) -> ee.ImageCollection:
    s2 = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(geom)
        .filterDate(inicio, fin)
    )
    csp = ee.ImageCollection("GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED")

    def enmascarar(img: ee.Image) -> ee.Image:
        cs = ee.Image(csp.filter(ee.Filter.eq("system:index", img.get("system:index"))).first())
        limpia = img.updateMask(cs.select("cs").gte(UMBRAL_CS)).select(BANDAS).divide(10_000)
        return ee.Image(limpia.copyProperties(img, ["system:time_start"]))

    return s2.map(enmascarar)


def _indices(img: ee.Image) -> ee.Image:
    ndvi = img.normalizedDifference(["B8", "B4"]).rename("ndvi")
    ndmi = img.normalizedDifference(["B8", "B11"]).rename("ndmi")
    ndre = img.normalizedDifference(["B8A", "B5"]).rename("ndre")
    evi = img.expression(
        "2.5 * (nir - red) / (nir + 6 * red - 7.5 * blue + 1)",
        {"nir": img.select("B8"), "red": img.select("B4"), "blue": img.select("B2")},
    ).rename("evi")
    return img.addBands([ndvi, evi, ndmi, ndre])


def clasicas(zona_geom: ee.Geometry, campania: str) -> ee.Image:
    inicio, _ = ventana_campania(campania)
    inicio_ee = ee.Date.fromYMD(inicio.year, inicio.month, inicio.day)
    coleccion = _coleccion_s2(zona_geom, inicio_ee, inicio_ee.advance(12, "month")).map(_indices)

    ventanas = []
    for sufijo, offset in VENTANAS:
        v0 = inicio_ee.advance(offset, "month")
        mediana = coleccion.filterDate(v0, v0.advance(2, "month")).median()
        ventanas.append(mediana.regexpRename("^(.*)$", f"$1_{sufijo}"))

    serie_ndvi = coleccion.select("ndvi")
    maximo = serie_ndvi.max().rename("ndvi_max")
    minimo = serie_ndvi.min().rename("ndvi_min")
    amplitud = maximo.subtract(minimo).rename("ndvi_amplitud")
    desvio = serie_ndvi.reduce(ee.Reducer.stdDev()).rename("ndvi_sd")

    # Day-of-year of the NDVI max: what separates early maize from late soy
    # without looking at magnitude (SPEC §4.1).
    con_doy = serie_ndvi.map(
        lambda img: img.addBands(
            ee.Image.constant(ee.Date(img.get("system:time_start")).getRelative("day", "year"))
            .toFloat()
            .rename("doy")
        )
    )
    doy_max = con_doy.qualityMosaic("ndvi").select("doy").rename("ndvi_doy_max")

    return ee.Image.cat(ventanas + [maximo, minimo, amplitud, desvio, doy_max]).toFloat()


def embeddings(zona_geom: ee.Geometry, campania: str) -> ee.Image:
    anio_inv, anio_ver = anios_embedding(campania)
    coleccion = ee.ImageCollection("GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL").filterBounds(zona_geom)

    def anual(anio: int, sufijo: str) -> ee.Image:
        img = ee.Image(
            coleccion.filterDate(f"{anio}-01-01", f"{anio + 1}-01-01").mosaic()
        )
        return img.regexpRename("^(.*)$", f"$1_{sufijo}")

    return ee.Image.cat([anual(anio_inv, "y1"), anual(anio_ver, "y2")]).toFloat()


def embeddings_un_anio(zona_geom: ee.Geometry, campania: str) -> ee.Image:
    """Ablation: only the summer-peak year, to quantify the calendar mismatch."""
    _, anio_ver = anios_embedding(campania)
    coleccion = ee.ImageCollection("GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL").filterBounds(zona_geom)
    return ee.Image(
        coleccion.filterDate(f"{anio_ver}-01-01", f"{anio_ver + 1}-01-01").mosaic()
    ).toFloat()
