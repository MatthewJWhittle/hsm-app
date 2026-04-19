"""PATCH /projects/{id}/environmental-band-definitions (admin)."""

import importlib
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend_api.schemas_upload import UploadSession
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
    mock_storage.promote_upload_session_driver_cog.return_value = (
        "/data/projects/proj-1",
        "environmental_cog.tif",
    )
    mock_client = mock_firestore_client_for_documents(
        [],
        project_documents=[SAMPLE_PROJECT],
    )
    claims: dict = {"uid": "admin-1", "email": "a@example.com", "admin": True}
    with (
        patch.dict(
            os.environ,
            {
                "STORAGE_BACKEND": "gcs",
                "GCS_BUCKET": "hsm-dashboard-model-artifacts",
            },
            clear=False,
        ),
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
            c.mock_storage = mock_storage  # type: ignore[attr-defined]
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
    with (
        patch("backend_api.routers.projects.write_job") as mock_job,
        patch("backend_api.routers.projects.firestore.Client", return_value=MagicMock()),
        patch(
            "backend_api.routers.projects.schedule_background_http_task"
        ) as mock_sched,
    ):
        c = admin_client_proj
        r = c.post(
            "/api/projects/proj-1/explainability-background-sample",
            headers={"Authorization": "Bearer fake.token"},
            json={"sample_rows": 128},
        )
        assert r.status_code == 202, r.text
        body = r.json()
        assert body.get("job_id")
        assert body.get("status") == "pending"
        mock_job.assert_called_once()
        assert mock_job.call_args[0][1].sample_rows == 128
        mock_sched.assert_called_once()


def test_post_explainability_background_sample_unknown_project_404(admin_client_proj):
    c = admin_client_proj
    r = c.post(
        "/api/projects/missing-id/explainability-background-sample",
        headers={"Authorization": "Bearer fake.token"},
        json={},
    )
    assert r.status_code == 404


def test_post_explainability_background_sample_default_rows(admin_client_proj):
    with (
        patch("backend_api.routers.projects.write_job") as mock_job,
        patch("backend_api.routers.projects.firestore.Client", return_value=MagicMock()),
        patch("backend_api.routers.projects.schedule_background_http_task"),
    ):
        c = admin_client_proj
        r = c.post(
            "/api/projects/proj-1/explainability-background-sample",
            headers={"Authorization": "Bearer fake.token"},
            json={},
        )
        assert r.status_code == 202, r.text
        assert mock_job.call_args[0][1].sample_rows == 256
        body = r.json()
        assert body.get("job_id")
        assert body.get("status") == "pending"


def test_patch_project_metadata_only_does_not_run_upload_or_derivation(admin_client_proj):
    c = admin_client_proj
    with (
        patch("backend_api.routers.projects.upload_session_gcs_uri") as mock_upload_uri,
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
        mock_upload_uri.assert_not_called()
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


def test_post_replace_environmental_cog_uses_upload_session_clears_background_and_keeps_band_defs(
    admin_client_proj,
):
    c = admin_client_proj
    upload_session = UploadSession(
        id="upload-1",
        project_id="proj-1",
        filename="env_stack.tif",
        content_type="image/tiff",
        requested_size_bytes=123,
        uploaded_size_bytes=123,
        checksum_sha256=None,
        status="complete",
        stage="done",
        gcs_bucket="hsm-dashboard-model-artifacts",
        object_path="uploads/upload-1/env_stack.tif",
        created_by_uid="admin-1",
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
    )
    with (
        patch.dict(
            os.environ,
            {
                "STORAGE_BACKEND": "gcs",
                "GCS_BUCKET": "hsm-dashboard-model-artifacts",
            },
            clear=False,
        ),
        patch(
            "backend_api.routers.projects.upload_session_gcs_uri",
            return_value=(
                "gs://hsm-dashboard-model-artifacts/uploads/upload-1/env_stack.tif",
                upload_session,
                123,
            ),
        ) as mock_upload_uri,
        patch(
            "backend_api.routers.projects.resolve_env_cog_uri_for_sampling",
            return_value="/vsicurl/signed-url",
        ) as mock_resolve_uri,
        patch(
            "backend_api.routers.projects.validate_cog_uri_threaded",
            new_callable=AsyncMock,
        ) as mock_validate_uri,
        patch(
            "backend_api.routers.projects.write_project_explainability_background_parquet"
        ) as mock_bg,
        patch(
            "backend_api.routers.projects.band_definitions_for_upload_uri"
        ) as mock_band_defs_uri,
        patch("backend_api.routers.projects.best_effort_mark", return_value=upload_session),
        patch(
            "backend_api.routers.projects.reload_catalog_threaded",
            new_callable=AsyncMock,
        ),
        patch("backend_api.routers.projects.validate_cog_path_threaded") as mock_validate_path,
    ):
        mock_band_defs_uri.return_value = (
            [
                {"index": 0, "name": "a", "label": None, "description": None},
                {"index": 1, "name": "b", "label": None, "description": None},
            ],
            [],
        )
        r = c.post(
            "/api/projects/proj-1/environmental-cogs",
            headers={"Authorization": "Bearer fake.token"},
            data={"upload_session_id": "upload-1"},
        )
        assert r.status_code == 200, r.text
        mock_upload_uri.assert_called_once()
        mock_resolve_uri.assert_called_once()
        mock_validate_uri.assert_called_once()
        mock_band_defs_uri.assert_called_once()
        c.mock_storage.promote_upload_session_driver_cog.assert_called_once()  # type: ignore[attr-defined]
        mock_validate_path.assert_not_called()
        mock_bg.assert_not_called()
        body = r.json()
        assert body["id"] == "proj-1"
        assert body["driver_cog_path"] == "environmental_cog.tif"
        assert body["environmental_band_definitions"] == [
            {"index": 0, "name": "a", "label": None, "description": None},
            {"index": 1, "name": "b", "label": None, "description": None},
        ]
        assert body["explainability_background_path"] is None
