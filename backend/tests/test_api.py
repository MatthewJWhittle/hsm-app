"""HTTP tests for GET /models (uses temp Firestore-shaped catalog file)."""

import importlib
import json
from unittest.mock import MagicMock, patch

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


@patch("backend_api.catalog_service.firestore.Client")
def test_firestore_backend_returns_empty_list_when_no_documents(
    mock_client_cls, tmp_path, monkeypatch
):
    """CATALOG_BACKEND=firestore reads from Firestore (mocked; no network)."""
    monkeypatch.setenv("CATALOG_BACKEND", "firestore")
    monkeypatch.setenv("CATALOG_PATH", str(tmp_path / "ignored.json"))
    mock_coll = MagicMock()
    mock_coll.stream.return_value = iter([])
    mock_client = MagicMock()
    mock_client.collection.return_value = mock_coll
    mock_client_cls.return_value = mock_client

    import backend_api.main as main

    importlib.reload(main)
    with TestClient(main.app) as c:
        r = c.get("/models")
    assert r.status_code == 200
    assert r.json() == []
    mock_client.collection.assert_called_once_with("models")


@patch("backend_api.catalog_service.firestore.Client")
def test_firestore_backend_returns_models(mock_client_cls, tmp_path, monkeypatch):
    monkeypatch.setenv("CATALOG_BACKEND", "firestore")
    monkeypatch.setenv("CATALOG_PATH", str(tmp_path / "ignored.json"))

    doc = MagicMock()
    doc.id = "a-model"
    doc.to_dict.return_value = {
        "species": "S",
        "activity": "A",
        "artifact_root": "/r",
        "suitability_cog_path": "x.tif",
    }
    mock_coll = MagicMock()
    mock_coll.stream.return_value = iter([doc])
    mock_client = MagicMock()
    mock_client.collection.return_value = mock_coll
    mock_client_cls.return_value = mock_client

    import backend_api.main as main

    importlib.reload(main)
    with TestClient(main.app) as c:
        r = c.get("/models")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["id"] == "a-model"
    assert data[0]["species"] == "S"


@pytest.fixture
def invalid_catalog_client(tmp_path, monkeypatch):
    catalog = tmp_path / "invalid.json"
    catalog.write_text(
        json.dumps(
            {
                "collection_id": "models",
                "documents": [
                    {
                        "id": "incomplete",
                        "species": "X",
                        # missing activity, artifact_root, suitability_cog_path
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


def test_catalog_validation_error_returns_503(invalid_catalog_client):
    r = invalid_catalog_client.get("/models")
    assert r.status_code == 503
    assert "schema" in r.json()["detail"].lower()


def test_documents_not_array_returns_503(tmp_path, monkeypatch):
    catalog = tmp_path / "shape.json"
    catalog.write_text(json.dumps({"documents": "not-a-list"}), encoding="utf-8")
    monkeypatch.setenv("CATALOG_PATH", str(catalog))
    import backend_api.main as main

    importlib.reload(main)
    with TestClient(main.app) as c:
        r = c.get("/models")
    assert r.status_code == 503
    assert "documents array" in r.json()["detail"].lower()


@pytest.fixture
def malformed_json_catalog_client(tmp_path, monkeypatch):
    catalog = tmp_path / "not.json"
    catalog.write_text("{ not json", encoding="utf-8")
    monkeypatch.setenv("CATALOG_PATH", str(catalog))
    import backend_api.main as main

    importlib.reload(main)
    with TestClient(main.app) as c:
        yield c


def test_malformed_json_catalog_returns_503(malformed_json_catalog_client):
    r = malformed_json_catalog_client.get("/models")
    assert r.status_code == 503
    assert "valid json" in r.json()["detail"].lower()


def test_get_model_returns_503_when_catalog_invalid(invalid_catalog_client):
    r = invalid_catalog_client.get("/models/any-id")
    assert r.status_code == 503


@pytest.fixture
def duplicate_id_client(tmp_path, monkeypatch):
    catalog = tmp_path / "dup.json"
    catalog.write_text(
        json.dumps(
            {
                "collection_id": "models",
                "documents": [
                    {
                        "id": "same--id",
                        "species": "First",
                        "activity": "A",
                        "artifact_root": "/data/cog",
                        "suitability_cog_path": "a.tif",
                    },
                    {
                        "id": "same--id",
                        "species": "Second",
                        "activity": "B",
                        "artifact_root": "/data/cog",
                        "suitability_cog_path": "b.tif",
                    },
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


def test_duplicate_document_ids_last_wins_for_lookup(duplicate_id_client):
    r = duplicate_id_client.get("/models")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2
    assert [m["species"] for m in data] == ["First", "Second"]

    one = duplicate_id_client.get("/models/same--id")
    assert one.status_code == 200
    assert one.json()["species"] == "Second"
