"""Department geometries and campaign windows.

The campaign window constant lives HERE and nowhere else (SPEC §3):
campaign YYYY/YY+1 runs July 1st of YYYY through June 30th of YYYY+1.
"""

import json
import re
from datetime import date

from .settings import DATA_DIR

ZONAS = {
    "rio-cuarto": {"nombre": "Río Cuarto", "provincia": "Córdoba"},
    "pergamino": {"nombre": "Pergamino", "provincia": "Buenos Aires"},
}

_CAMPANIA_RE = re.compile(r"^(\d{4})-(\d{2})$")


def ventana_campania(campania: str) -> tuple[date, date]:
    """'2024-25' → (2024-07-01, 2025-06-30). Every S2 filter uses this exact range."""
    m = _CAMPANIA_RE.match(campania)
    if not m:
        raise ValueError(f"Campaña inválida: {campania!r}. Formato esperado: '2024-25'")
    y0 = int(m.group(1))
    y1 = y0 + 1
    if int(m.group(2)) != y1 % 100:
        raise ValueError(f"Campaña inválida: {campania!r}. Los años deben ser consecutivos")
    return date(y0, 7, 1), date(y1, 6, 30)


def anios_embedding(campania: str) -> tuple[int, int]:
    """Calendar years whose AlphaEarth embeddings overlap the campaign (SPEC §4.2)."""
    inicio, fin = ventana_campania(campania)
    return inicio.year, fin.year


def geometria(zona: str) -> dict:
    """GeoJSON geometry for a department, from data/zonas.geojson (IGN limits)."""
    if zona not in ZONAS:
        raise KeyError(f"Zona desconocida: {zona!r}. Válidas: {sorted(ZONAS)}")
    path = DATA_DIR / "zonas.geojson"
    if not path.exists():
        # TODO(mateo/pipeline): descargar límites departamentales del IGN y guardarlos
        # en data/zonas.geojson (features con property "zona": "rio-cuarto"|"pergamino").
        # No se inventa una geometría plausible: sin el archivo, esto falla explícito.
        raise FileNotFoundError(
            "PENDIENTE: falta data/zonas.geojson con los límites del IGN. "
            "Ver data/README.md."
        )
    fc = json.loads(path.read_text())
    for feature in fc["features"]:
        if feature["properties"].get("zona") == zona:
            return feature["geometry"]
    raise KeyError(f"data/zonas.geojson no tiene la zona {zona!r}")
