"""Single source of truth for configuration. Everything comes from env vars / .env."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
FRONTEND_DIR = REPO_ROOT / "frontend"

# Fixed sampling/training seed — changing it to improve a number is forbidden
# (see CLAUDE.md). If results vary across seeds, that variance IS the finding.
SEED = 42


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore")

    # TODO(mateo): GCP project with EE API enabled + service account REGISTERED
    # in Earth Engine (registration is a separate step from creation).
    gee_service_account: str = ""
    gee_key_path: str = ""

    # TODO(mateo): public-read GCS bucket with CORS enabled for the viewer domain.
    gcs_tiles_bucket: str = ""

    # MNC campaign is a parameter, not a constant: if 2024/25 isn't published
    # on GeoINTA yet, fall back to the latest available one.
    mnc_campania: str = "2024-25"

    # Directory holding the MNC national rasters downloaded from Zenodo
    # (MNC_inv24.tif / MNC_ver25.tif). They live OUTSIDE the repo: no GeoTIFFs in git.
    mnc_dir: str = "~/.gee/mnc"


settings = Settings()
