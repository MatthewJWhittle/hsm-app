"""PATCH /projects/{id}/environmental-band-definitions (admin)."""

import importlib
from pathlib import Path
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
    "explainability_background_path": "explainability_background.parquet",
    "explainability_background_sample_rows": 256,
    "explainability_background_generated_at": "2026-01-01T12:00:00+00:00",
    "visibility": "public",
    "allowed_uids": [],
    "status": "active",
}


@pytest.fixture
def admin_client_proj():
    mock_storage = MagicMock()
    mock_storage.write_project_driver_cog_from_path.return_value = (
        "/data/projects/proj-1",
        "environmental_cog.tif",
    )
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
        "/api/projects/proj-1/environmental-band-definitions",
        headers={"Authorization": "Bearer fake.token"},
        json=[
            {"index": 0, "name": "a", "label": "Elevation", "description": "Height above sea level"},
            {"index": 1, "name": "b", "label": "Slope", "description": None},
        ],
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["environmental_band_definitions"][0]["label"] == "Elevation"
    assert body["environmental_band_definitions"][0]["description"] == "Height above sea level"
    assert body["environmental_band_definitions"][1]["label"] == "Slope"
    assert not body["environmental_band_definitions"][1].get("description")


def test_patch_environmental_band_definitions_wrong_count_422(admin_client_proj):
    c = admin_client_proj
    r = c.patch(
        "/api/projects/proj-1/environmental-band-definitions",
        headers={"Authorization": "Bearer fake.token"},
        json=[{"index": 0, "name": "a", "label": None}],
    )
    assert r.status_code == 422
    assert "2" in str(r.json().get("detail", ""))


def test_patch_environmental_band_definitions_unknown_project_404(admin_client_proj):
    c = admin_client_proj
    r = c.patch(
        "/api/projects/missing-id/environmental-band-definitions",
        headers={"Authorization": "Bearer fake.token"},
        json=[
            {"index": 0, "name": "a", "label": None},
            {"index": 1, "name": "b", "label": None},
        ],
    )
    assert r.status_code == 404


def test_patch_environmental_band_definition_labels_partial(admin_client_proj):
    c = admin_client_proj
    r = c.patch(
        "/api/projects/proj-1/environmental-band-definitions/labels",
        headers={"Authorization": "Bearer fake.token"},
        json={"a": {"name": "Alpha", "description": "first band"}},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["environmental_band_definitions"][0]["label"] == "Alpha"
    assert body["environmental_band_definitions"][0]["description"] == "first band"
    assert body["environmental_band_definitions"][1]["label"] is None


def test_patch_environmental_band_definition_labels_label_wins_over_name(admin_client_proj):
    c = admin_client_proj
    r = c.patch(
        "/api/projects/proj-1/environmental-band-definitions/labels",
        headers={"Authorization": "Bearer fake.token"},
        json={"b": {"label": "Beta", "name": "Ignored"}},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["environmental_band_definitions"][1]["label"] == "Beta"


def test_patch_environmental_band_definition_labels_unknown_name_422(admin_client_proj):
    c = admin_client_proj
    r = c.patch(
        "/api/projects/proj-1/environmental-band-definitions/labels",
        headers={"Authorization": "Bearer fake.token"},
        json={"no_such_band": {"name": "X"}},
    )
    assert r.status_code == 422
    assert "unknown" in str(r.json().get("detail", "")).lower()


def test_patch_environmental_band_definition_labels_empty_body_422(admin_client_proj):
    c = admin_client_proj
    r = c.patch(
        "/api/projects/proj-1/environmental-band-definitions/labels",
        headers={"Authorization": "Bearer fake.token"},
        json={},
    )
    assert r.status_code == 422


def test_post_explainability_background_sample_ok(admin_client_proj):
    with patch(
        "backend_api.routers.projects.write_project_explainability_background_parquet"
    ) as mock_w:
        c = admin_client_proj
        r = c.post(
            "/api/projects/proj-1/explainability-background-sample",
            headers={"Authorization": "Bearer fake.token"},
            json={"sample_rows": 128},
        )
        assert r.status_code == 200, r.text
        mock_w.assert_called_once()
        assert mock_w.call_args[0][6] == 128
        body = r.json()
        assert body.get("explainability_background_path") is not None
        assert body.get("explainability_background_sample_rows") == 128
        assert body.get("explainability_background_generated_at")


def test_post_explainability_background_sample_unknown_project_404(admin_client_proj):
    with patch(
        "backend_api.routers.projects.write_project_explainability_background_parquet"
    ):
        c = admin_client_proj
        r = c.post(
            "/api/projects/missing-id/explainability-background-sample",
            headers={"Authorization": "Bearer fake.token"},
            json={},
        )
        assert r.status_code == 404


def test_post_explainability_background_sample_default_rows(admin_client_proj):
    with patch(
        "backend_api.routers.projects.write_project_explainability_background_parquet"
    ) as mock_w:
        c = admin_client_proj
        r = c.post(
            "/api/projects/proj-1/explainability-background-sample",
            headers={"Authorization": "Bearer fake.token"},
            json={},
        )
        assert r.status_code == 200, r.text
        assert mock_w.call_args[0][6] == 256
        body = r.json()
        assert body.get("explainability_background_sample_rows") == 256
        assert body.get("explainability_background_generated_at")


def test_patch_project_metadata_only_does_not_run_upload_or_derivation(admin_client_proj):
    c = admin_client_proj
    with (
        patch("backend_api.routers.projects.download_upload_session_to_tempfile") as mock_download,
        patch("backend_api.routers.projects.validate_cog_path_threaded") as mock_validate,
        patch(
            "backend_api.routers.projects.write_project_explainability_background_parquet"
        ) as mock_bg,
    ):
        r = c.patch(
            "/api/projects/proj-1",
            headers={"Authorization": "Bearer fake.token"},
            data={"name": "Renamed project"},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["name"] == "Renamed project"
        mock_download.assert_not_called()
        mock_validate.assert_not_called()
        mock_bg.assert_not_called()


def test_patch_project_rejects_upload_fields_with_422(admin_client_proj):
    c = admin_client_proj
    r = c.patch(
        "/api/projects/proj-1",
        headers={"Authorization": "Bearer fake.token"},
        data={"name": "Renamed project", "upload_session_id": "upload-1"},
    )
    assert r.status_code == 422
    assert "environmental-cogs" in str(r.json().get("detail", "")).lower()


def test_post_replace_environmental_cog_uses_upload_session(admin_client_proj):
    c = admin_client_proj
    with (
        patch(
            "backend_api.env_cog_replace_pipeline.download_upload_session_to_tempfile"
        ) as mock_download,
        patch(
            "backend_api.env_cog_replace_pipeline.validate_cog_path_threaded"
        ) as mock_validate,
        patch(
            "backend_api.env_cog_replace_pipeline.write_project_explainability_background_parquet"
        ) as mock_bg,
        patch(
            "backend_api.env_cog_replace_pipeline.band_definitions_for_upload_path"
        ) as mock_band_defs,
        patch("backend_api.env_cog_replace_pipeline.best_effort_mark") as mock_mark,
    ):
        fake_upload = MagicMock(spec=Path)
        fake_upload.__str__.return_value = "/tmp/fake-upload.tif"
        fake_upload.unlink = MagicMock()
        mock_download.return_value = (fake_upload, None)
        mock_band_defs.return_value = (
            [
                {"index": 0, "name": "a", "label": None},
                {"index": 1, "name": "b", "label": None},
            ],
            [],
        )
        mock_mark.return_value = None
        with patch("backend_api.env_cog_replace_pipeline.os.path.getsize", return_value=123):
            r = c.post(
                "/api/projects/proj-1/environmental-cogs",
                headers={"Authorization": "Bearer fake.token"},
                data={"upload_session_id": "upload-1"},
            )
        assert r.status_code == 200, r.text
        mock_download.assert_called_once()
        mock_validate.assert_called_once()
        mock_bg.assert_called_once()
        fake_upload.unlink.assert_called_once_with(missing_ok=True)
        body = r.json()
        assert body["id"] == "proj-1"
