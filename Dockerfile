FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src/ src/
COPY data/ data/
COPY frontend/ frontend/
RUN uv sync --frozen --no-dev

# La key del service account NO va en la imagen: se monta como secret en Cloud Run
# y su ruta llega por GEE_KEY_PATH.
ENV PORT=8080
CMD ["uv", "run", "--no-sync", "uvicorn", "mapa_cultivos.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
