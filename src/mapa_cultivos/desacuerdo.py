"""Where the two feature sets disagree — computed from the exported maps."""

import numpy as np

NODATA = 255


def cruzar(a: np.ndarray, b: np.ndarray, nodata: int = NODATA) -> np.ndarray:
    valido = (a != nodata) & (b != nodata)
    salida = np.full(a.shape, nodata, dtype=np.uint8)
    salida[valido] = (a[valido] != b[valido]).astype(np.uint8)
    return salida


def porcentaje(cruce: np.ndarray, nodata: int = NODATA) -> float:
    validos = cruce != nodata
    if not validos.any():
        return 0.0
    return float((cruce[validos] == 1).mean())
