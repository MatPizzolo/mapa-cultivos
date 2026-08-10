"""Earth Engine init with service account. All heavy compute lives in EE."""

import functools

import ee

from .settings import settings


class EENotConfigured(RuntimeError):
    pass


@functools.cache
def init() -> None:
    """Initialize EE once per process. Raises EENotConfigured if creds are missing."""
    if not settings.gee_service_account or not settings.gee_key_path:
        raise EENotConfigured(
            "PENDIENTE: faltan GEE_SERVICE_ACCOUNT y GEE_KEY_PATH en .env. "
            "El service account tiene que estar registrado en Earth Engine "
            "(paso aparte de crearlo)."
        )
    credentials = ee.ServiceAccountCredentials(
        settings.gee_service_account, settings.gee_key_path
    )
    ee.Initialize(credentials)


def ping() -> bool:
    """Cheap EE round-trip. False must NOT degrade the app: only explore mode."""
    try:
        init()
        ee.Number(1).getInfo()
        return True
    except Exception:
        return False
