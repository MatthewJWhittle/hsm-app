"""HTTP tests for GET /models (uses temp Firestore-shaped catalog file)."""

import importlib
import json

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    catalog = tmp_path / "firestore_models.json"
    catalog.write_text(
        json.dumps(
            {
                "collection_id": "models",
                "documents": [
                    {
                        "id": "test-bat--roosting",
                        "species": "Test bat",
                        "activity": "Roosting",
                        "artifact_root": "/data/cog",
                        "suitability_cog_path": "test_cog.tif",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("CATALOG_PATH", str(catalog))
    import backend_api.main as main

    importlib.reload(main)
    with TestClient(main.app) as c:
        yield c


def test_get_models_returns_list(client):
    r = client.get("/models")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["id"] == "test-bat--roosting"
    assert data[0]["species"] == "Test bat"
    assert data[0]["suitability_cog_path"] == "test_cog.tif"


def test_get_model_by_id(client):
    r = client.get("/models/test-bat--roosting")
    assert r.status_code == 200
    assert r.json()["activity"] == "Roosting"


def test_get_model_unknown_404(client):
    r = client.get("/models/does-not-exist")
    assert r.status_code == 404
