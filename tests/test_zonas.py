from datetime import date

import pytest

from mapa_cultivos import zonas


def test_ventana_campania():
    assert zonas.ventana_campania("2024-25") == (date(2024, 7, 1), date(2025, 6, 30))


def test_ventana_campania_invalida():
    for mala in ["2024", "2024/25", "2024-26", "24-25"]:
        with pytest.raises(ValueError):
            zonas.ventana_campania(mala)


def test_anios_embedding():
    assert zonas.anios_embedding("2024-25") == (2024, 2025)


def test_geometria_carga_ambas_zonas():
    for zona in ["rio-cuarto", "pergamino"]:
        g = zonas.geometria(zona)
        assert g["type"] in ("Polygon", "MultiPolygon")
        assert g["coordinates"]


def test_zona_desconocida():
    with pytest.raises(KeyError):
        zonas.geometria("junin")
