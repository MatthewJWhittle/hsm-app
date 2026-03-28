"""HTTP tests for GET /models (Firestore client mocked)."""

import importlib
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend_api.catalog_service import MODELS_COLLECTION_ID
from tests.helpers import mock_firestore_client_for_documents


@pytest.fixture
def client():
    documents = [
        {
            "id": "test-bat--roosting",
            "species": "Test bat",
            "activity": "Roosting",
            "artifact_root": "/data/cog",
            "suitability_cog_path": "test_cog.tif",
        }
    ]
    mock_client = mock_firestore_client_for_documents(documents)
    with patch("backend_api.catalog_service.firestore.Client", return_value=mock_client):
        import backend_api.main as main

        importlib.reload(main)
        with TestClient(main.app) as c:
            yield c, mock_client


def test_get_models_returns_list(client):
    c, mock_client = client
    r = c.get("/models")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["id"] == "test-bat--roosting"
    assert data[0]["species"] == "Test bat"
    assert data[0]["suitability_cog_path"] == "test_cog.tif"
    mock_client.collection.assert_called_once_with(MODELS_COLLECTION_ID)


def test_get_model_by_id(client):
    c, _ = client
    r = c.get("/models/test-bat--roosting")
    assert r.status_code == 200
    assert r.json()["activity"] == "Roosting"


def test_get_model_unknown_404(client):
    c, _ = client
    r = c.get("/models/does-not-exist")
    assert r.status_code == 404


@patch("backend_api.catalog_service.firestore.Client")
def test_firestore_backend_returns_empty_list_when_no_documents(mock_client_cls):
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
    mock_client.collection.assert_called_once_with(MODELS_COLLECTION_ID)


@patch("backend_api.catalog_service.firestore.Client")
def test_firestore_backend_returns_models(mock_client_cls):
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


@patch("backend_api.catalog_service.firestore.Client")
def test_catalog_validation_error_returns_503(mock_client_cls):
    doc = MagicMock()
    doc.id = "incomplete"
    doc.to_dict.return_value = {"species": "X"}
    mock_coll = MagicMock()
    mock_coll.stream.return_value = iter([doc])
    mock_client = MagicMock()
    mock_client.collection.return_value = mock_coll
    mock_client_cls.return_value = mock_client

    import backend_api.main as main

    importlib.reload(main)
    with TestClient(main.app) as c:
        r = c.get("/models")
    assert r.status_code == 503
    assert "schema" in r.json()["detail"].lower()


@patch("backend_api.catalog_service.firestore.Client")
def test_get_model_returns_503_when_catalog_invalid(mock_client_cls):
    doc = MagicMock()
    doc.id = "incomplete"
    doc.to_dict.return_value = {"species": "X"}
    mock_coll = MagicMock()
    mock_coll.stream.return_value = iter([doc])
    mock_client = MagicMock()
    mock_client.collection.return_value = mock_coll
    mock_client_cls.return_value = mock_client

    import backend_api.main as main

    importlib.reload(main)
    with TestClient(main.app) as c:
        r = c.get("/models/any-id")
    assert r.status_code == 503
