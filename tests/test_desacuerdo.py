import numpy as np

from mapa_cultivos import desacuerdo


def test_cruzar_marca_solo_diferencias_validas():
    a = np.array([[1, 1, 255], [2, 3, 4]], dtype=np.uint8)
    b = np.array([[1, 2, 1], [255, 3, 5]], dtype=np.uint8)
    c = desacuerdo.cruzar(a, b)
    esperado = np.array([[0, 1, 255], [255, 0, 1]], dtype=np.uint8)
    assert (c == esperado).all()


def test_porcentaje_ignora_nodata():
    c = np.array([[0, 1, 255, 255]], dtype=np.uint8)
    assert desacuerdo.porcentaje(c) == 0.5


def test_porcentaje_sin_validos_es_cero():
    c = np.full((2, 2), 255, dtype=np.uint8)
    assert desacuerdo.porcentaje(c) == 0.0
