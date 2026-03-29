"""Tests for admin POST/PUT /models (auth + storage mocked)."""

import importlib
from contextlib import contextmanager
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from tests.helpers import mock_firestore_client_for_documents


@pytest.fixture
def catalog_docs():
    return [
        {
            "id": "existing-id",
            "species": "Bat",
            "activity": "Roost",
            "artifact_root": "/data/models/existing-id",
            "suitability_cog_path": "suitability_cog.tif",
        }
    ]


@contextmanager
def _admin_client(documents: list[dict], mock_storage: MagicMock, admin: bool = True):
    mock_client = mock_firestore_client_for_documents(documents)
    claims: dict = {"uid": "admin-1", "email": "a@example.com"}
    if admin:
        claims["admin"] = True

    with (
        patch("backend_api.catalog_service.firestore.Client", return_value=mock_client),
        patch(
            "backend_api.auth_deps.auth.verify_id_token",
            return_value=claims,
        ),
        patch(
            "backend_api.cog_validation.validate_suitability_cog_bytes",
            return_value=None,
        ),
        patch("backend_api.main.upsert_model"),
        patch(
            "backend_api.storage.build_object_storage",
            return_value=mock_storage,
        ),
    ):
        import backend_api.main as main

        importlib.reload(main)
        with TestClient(main.app) as c:
            yield c


def test_post_models_requires_admin_claim():
    mock_storage = MagicMock()
    mock_storage.write_suitability_cog.return_value = ("/data/models/x", "suitability_cog.tif")
    docs = [
        {
            "id": "x",
            "species": "S",
            "activity": "A",
            "artifact_root": "/r",
            "suitability_cog_path": "a.tif",
        }
    ]
    mock_client = mock_firestore_client_for_documents(docs)
    with (
        patch("backend_api.catalog_service.firestore.Client", return_value=mock_client),
        patch(
            "backend_api.auth_deps.auth.verify_id_token",
            return_value={"uid": "u", "email": "u@example.com"},
        ),
        patch(
            "backend_api.storage.build_object_storage",
            return_value=mock_storage,
        ),
    ):
        import backend_api.main as main

        importlib.reload(main)
        with TestClient(main.app) as c:
            r = c.post(
                "/models",
                headers={"Authorization": "Bearer fake.token"},
                data={"species": "Sp", "activity": "Act"},
                files={"file": ("cog.tif", BytesIO(b"dummy"), "image/tiff")},
            )
    assert r.status_code == 403


def test_post_models_201_creates_model(catalog_docs):
    mock_storage = MagicMock()
    mock_storage.write_suitability_cog.return_value = (
        "/data/models/new-id",
        "suitability_cog.tif",
    )
    with _admin_client(catalog_docs, mock_storage) as c:
        r = c.post(
            "/models",
            headers={"Authorization": "Bearer fake.token"},
            data={
                "species": "New species",
                "activity": "Flight",
                "model_name": "m1",
            },
            files={"file": ("cog.tif", BytesIO(b"dummy"), "image/tiff")},
        )
    assert r.status_code == 201
    data = r.json()
    assert data["species"] == "New species"
    assert data["activity"] == "Flight"
    assert data["model_name"] == "m1"
    assert "id" in data
    mock_storage.write_suitability_cog.assert_called_once()


def test_put_models_updates_metadata(catalog_docs):
    mock_storage = MagicMock()
    mock_storage.write_suitability_cog.return_value = (
        "/data/models/existing-id",
        "suitability_cog.tif",
    )
    with _admin_client(catalog_docs, mock_storage) as c:
        r = c.put(
            "/models/existing-id",
            headers={"Authorization": "Bearer fake.token"},
            data={"species": "Updated"},
        )
    assert r.status_code == 200
    assert r.json()["species"] == "Updated"
    mock_storage.write_suitability_cog.assert_not_called()


def test_put_models_unknown_404(catalog_docs):
    mock_storage = MagicMock()
    with _admin_client(catalog_docs, mock_storage) as c:
        r = c.put(
            "/models/missing",
            headers={"Authorization": "Bearer fake.token"},
            data={"species": "X"},
        )
    assert r.status_code == 404
