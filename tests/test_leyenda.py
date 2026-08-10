import json
import re

from mapa_cultivos.settings import DATA_DIR


def leer():
    return json.loads((DATA_DIR / "leyenda.json").read_text())


def test_seis_clases_codigos_0_a_5():
    clases = leer()["clases"]
    assert sorted(c["codigo"] for c in clases) == [0, 1, 2, 3, 4, 5]


def test_colores_hex_validos_y_unicos():
    colores = [c["color"] for c in leer()["clases"]]
    assert all(re.fullmatch(r"#[0-9A-Fa-f]{6}", c) for c in colores)
    assert len(set(colores)) == len(colores)


def test_metrics_no_rotula_acuerdo_como_accuracy():
    # The MNC comparison must never be labeled accuracy (METODOLOGIA §1).
    metrics = json.loads((DATA_DIR / "metrics.json").read_text())
    for zona in metrics["zonas"].values():
        for modelo in zona["modelos"].values():
            assert "acuerdo_mnc" in modelo
            assert "accuracy_mnc" not in modelo
