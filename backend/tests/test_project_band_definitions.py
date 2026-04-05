"""PATCH /projects/{id}/environmental-band-definitions (admin)."""

import importlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from tests.helpers import mock_firestore_client_for_documents

SAMPLE_PROJECT = {
    "id": "proj-1",
    "name": "Test project",
    "driver_artifact_root": "/data/projects/proj-1",
    "driver_cog_path": "environmental_cog.tif",
    "environmental_band_definitions": [
        {"index": 0, "name": "a", "label": None},
        {"index": 1, "name": "b", "label": None},
    ],
    "visibility": "public",
    "allowed_uids": [],
    "status": "active",
}


@pytest.fixture
def admin_client_proj():
    mock_storage = MagicMock()
    mock_client = mock_firestore_client_for_documents(
        [],
        project_documents=[SAMPLE_PROJECT],
    )
    claims: dict = {"uid": "admin-1", "email": "a@example.com", "admin": True}
    with (
        patch("backend_api.catalog_service.firestore.Client", return_value=mock_client),
        patch(
            "backend_api.auth_deps.auth.verify_id_token",
            return_value=claims,
        ),
        patch(
            "backend_api.storage.build_object_storage",
            return_value=mock_storage,
        ),
        patch("backend_api.routers.projects.Path") as mock_path_cls,
        patch("backend_api.routers.projects.count_bands_in_path", return_value=2),
        patch(
            "backend_api.routers.projects.reload_catalog_threaded",
            new_callable=AsyncMock,
        ),
    ):
        mock_path_cls.return_value.is_file.return_value = True
        import backend_api.main as main

        importlib.reload(main)
        with TestClient(main.app) as c:
            yield c


def test_patch_environmental_band_definitions_sets_labels(admin_client_proj):
    c = admin_client_proj
    r = c.patch(
        "/projects/proj-1/environmental-band-definitions",
        headers={"Authorization": "Bearer fake.token"},
        json=[
            {"index": 0, "name": "a", "label": "Elevation"},
            {"index": 1, "name": "b", "label": "Slope"},
        ],
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["environmental_band_definitions"][0]["label"] == "Elevation"
    assert body["environmental_band_definitions"][1]["label"] == "Slope"


def test_patch_environmental_band_definitions_wrong_count_422(admin_client_proj):
    c = admin_client_proj
    r = c.patch(
        "/projects/proj-1/environmental-band-definitions",
        headers={"Authorization": "Bearer fake.token"},
        json=[{"index": 0, "name": "a", "label": None}],
    )
    assert r.status_code == 422
    assert "2" in str(r.json().get("detail", ""))


def test_patch_environmental_band_definitions_unknown_project_404(admin_client_proj):
    c = admin_client_proj
    r = c.patch(
        "/projects/missing-id/environmental-band-definitions",
        headers={"Authorization": "Bearer fake.token"},
        json=[
            {"index": 0, "name": "a", "label": None},
            {"index": 1, "name": "b", "label": None},
        ],
    )
    assert r.status_code == 404
