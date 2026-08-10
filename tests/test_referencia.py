import numpy as np

from mapa_cultivos import referencia as r


def caso(inv, ver):
    return int(r.cruzar(np.array([[inv]], dtype=np.uint8), np.array([[ver]], dtype=np.uint8))[0, 0])


def test_soja_de_primera():
    # Summer soy without winter cereal → soja (whatever the winter: fallow, etc.)
    assert caso(18, r.VER_SOJA) == 1
    assert caso(r.INV_NO_AGRICOLA, r.VER_SOJA) == 1


def test_trigo_soja_segunda():
    assert caso(r.INV_CEREAL, r.VER_SOJA) == 3


def test_maiz_incluso_tras_cereal():
    assert caso(18, r.VER_MAIZ) == 2
    assert caso(r.INV_CEREAL, r.VER_MAIZ) == 2


def test_mani():
    assert caso(18, r.VER_MANI) == 4


def test_verdeos():
    assert caso(18, r.VER_VERDEO_MAIZ) == 5
    assert caso(18, r.VER_VERDEO_SORGO) == 5


def test_no_agricola_requiere_ambas_temporadas():
    assert caso(r.INV_NO_AGRICOLA, r.VER_NO_AGRICOLA) == 0
    # No agrícola in only one season is NOT enough → excluded, not forced.
    assert caso(r.INV_NO_AGRICOLA, 21) == r.EXCLUIDO
    assert caso(18, r.VER_NO_AGRICOLA) == r.EXCLUIDO


def test_cultivos_fuera_de_leyenda_quedan_excluidos():
    for ver in [12, 13, 15, 17, 18, 26, 31, 255]:  # girasol, poroto, algodón, ...
        assert caso(18, ver) == r.EXCLUIDO
