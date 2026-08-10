from fastapi.testclient import TestClient

from mapa_cultivos.api.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    # True with working credentials, False without — either way the app is up.
    assert isinstance(body["ee"], bool)


def test_metrics_contract():
    r = client.get("/metrics")
    assert r.status_code == 200
    body = r.json()
    assert set(body["zonas"]) == {"rio-cuarto", "pergamino"}
    assert body["semilla"] == 42


def test_leyenda():
    r = client.get("/leyenda")
    assert r.status_code == 200
    assert len(r.json()["clases"]) == 6


def test_zonas_contract():
    r = client.get("/zonas")
    assert r.status_code == 200
    body = r.json()
    assert body["type"] == "FeatureCollection"
    assert {f["properties"]["zona"] for f in body["features"]} == {"rio-cuarto", "pergamino"}


def test_clasificar_503_en_espanol_sin_romper():
    r = client.post(
        "/clasificar",
        json={
            "geometry": {"type": "Polygon", "coordinates": [[[-64.3, -33.1]]]},
            "campania": "2024-25",
            "modelo": "embeddings-rf",
        },
    )
    assert r.status_code == 503
    assert "modo explorar" in r.json()["detail"]


def test_clasificar_valida_modelo():
    r = client.post(
        "/clasificar",
        json={"geometry": {}, "campania": "2024-25", "modelo": "red-neuronal"},
    )
    assert r.status_code == 422


def test_frontend_servido():
    r = client.get("/")
    assert r.status_code == 200
    assert "Mapa de Cultivos" in r.text
