.PHONY: install dev test muestras benchmark mapa tiles docker

install:
	uv sync

dev:
	uv run uvicorn mapa_cultivos.api.main:app --reload --port 8000

test:
	uv run pytest

muestras:
	uv run python scripts/01_muestrear.py

benchmark:
	uv run python scripts/02_benchmark.py

mapa:
	uv run python scripts/03_exportar_mapa.py

tiles:
	uv run python scripts/04_tiles.py

docker:
	docker build -t mapa-cultivos .
