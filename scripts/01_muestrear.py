"""Stratified sampling over the remapped MNC → versioned CSVs in data/muestras/.

Local raster work only (no EE): the MNC lives as local GeoTIFFs from Zenodo.
Re-running with the same seed and inputs reproduces the exact same tables.
"""

from mapa_cultivos.muestras import muestrear_zona, reporte_soporte
from mapa_cultivos.settings import DATA_DIR, settings
from mapa_cultivos.zonas import ZONAS


def main() -> None:
    campania = settings.mnc_campania
    destino = DATA_DIR / "muestras"
    destino.mkdir(exist_ok=True)

    for zona in ZONAS:
        tabla = muestrear_zona(zona, campania)
        ruta = destino / f"{zona}_{campania}.csv"
        tabla.to_csv(ruta, index=False)
        print(f"\n== {zona} → {ruta.name} ({len(tabla)} puntos) ==")
        print(reporte_soporte(tabla).to_string())


if __name__ == "__main__":
    main()
