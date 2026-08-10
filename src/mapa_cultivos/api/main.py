"""FastAPI app, minimal (SPEC §6). Everything that can be static is served static."""

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .. import ee_client
from ..settings import DATA_DIR, FRONTEND_DIR, REPO_ROOT
from .schemas import ClasificarRequest, ClasificarResponse

app = FastAPI(title="Mapa de Cultivos con IA", docs_url=None, redoc_url=None)

# Local tiles for development. In production the frontend points TILES_BASE to
# the GCS bucket and this mount simply has nothing to serve.
if (REPO_ROOT / "tiles").is_dir():
    app.mount("/tiles", StaticFiles(directory=REPO_ROOT / "tiles"), name="tiles")


@app.get("/health")
def health() -> dict:
    # ee=false does NOT degrade the app: only explore mode depends on it.
    return {"status": "ok", "ee": ee_client.ping()}


@app.get("/metrics")
def metrics() -> FileResponse:
    return FileResponse(DATA_DIR / "metrics.json", media_type="application/json")


@app.get("/leyenda")
def leyenda() -> FileResponse:
    return FileResponse(DATA_DIR / "leyenda.json", media_type="application/json")


@app.get("/zonas")
def zonas() -> FileResponse:
    return FileResponse(DATA_DIR / "zonas.geojson", media_type="application/geo+json")


@app.get("/desacuerdo")
def desacuerdo() -> FileResponse:
    return FileResponse(DATA_DIR / "desacuerdo.json", media_type="application/json")


@app.post("/clasificar", response_model=ClasificarResponse)
def clasificar(req: ClasificarRequest) -> ClasificarResponse:
    # TODO(capa 4): clasificación en vivo contra Earth Engine — límite 5.000 ha,
    # polígono dentro de Argentina, timeout 25 s. Hasta entonces, 503 honesto:
    # el frontend lo muestra como aviso y no rompe el resto de la vista.
    raise HTTPException(
        status_code=503,
        detail=(
            "El modo explorar todavía no está disponible: faltan las credenciales "
            "de Earth Engine y los modelos entrenados."
        ),
    )


# Mounted last so API routes take precedence.
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
