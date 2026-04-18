"""Tests for admin POST/PUT /models (auth + storage mocked)."""

import importlib
import json
import os
from contextlib import contextmanager
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend_api.storage import SERIALIZED_MODEL_FILENAME
from backend_api.schemas_upload import UploadSession
from tests.helpers import mock_firestore_client_for_documents

SAMPLE_PROJECT = {
    "id": "proj-1",
    "name": "Test project",
    "driver_artifact_root": "/data/projects/proj-1",
    "driver_cog_path": "environmental_cog.tif",
    "explainability_background_path": "explainability_background.parquet",
    "environmental_band_definitions": [
        {"index": 0, "name": "a", "label": None},
        {"index": 1, "name": "b", "label": None},
    ],
    "visibility": "public",
    "allowed_uids": [],
    "status": "active",
}


@pytest.fixture
def catalog_docs():
    return [
        {
            "id": "existing-id",
            "project_id": "proj-1",
            "species": "Bat",
            "activity": "Roost",
            "artifact_root": "/data/models/existing-id",
            "suitability_cog_path": "suitability_cog.tif",
        }
    ]


@contextmanager
def _admin_client(
    documents: list[dict],
    mock_storage: object,
    admin: bool = True,
    *,
    project_documents: list[dict] | None = None,
):
    mock_client = mock_firestore_client_for_documents(
        documents,
        project_documents=project_documents or [],
    )
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
            "backend_api.routers.catalog_upload_utils.validate_suitability_cog_bytes",
            return_value=None,
        ),
        patch(
            "backend_api.routers.models.validate_cog_path_threaded",
            new_callable=AsyncMock,
        ),
        patch(
            "backend_api.routers.projects.validate_cog_path_threaded",
            new_callable=AsyncMock,
        ),
        patch("backend_api.routers.models.upsert_model"),
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
    mock_storage.write_suitability_cog_from_path.return_value = (
        "/data/models/x",
        "suitability_cog.tif",
    )
    docs = [
        {
            "id": "x",
            "species": "S",
            "activity": "A",
            "artifact_root": "/r",
            "suitability_cog_path": "a.tif",
        }
    ]
    mock_client = mock_firestore_client_for_documents(
        docs,
        project_documents=[SAMPLE_PROJECT],
    )
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
                    "/api/models",
                headers={"Authorization": "Bearer fake.token"},
                data={
                    "project_id": "proj-1",
                    "species": "Sp",
                    "activity": "Act",
                },
                files={"file": ("cog.tif", BytesIO(b"dummy"), "image/tiff")},
            )
    assert r.status_code == 403


def test_post_models_with_explainability_uploads(catalog_docs):
    mock_storage = MagicMock()
    mock_storage.write_suitability_cog.return_value = (
        "/data/models/new-id",
        "suitability_cog.tif",
    )
    mock_storage.write_suitability_cog_from_path.return_value = (
        "/data/models/new-id",
        "suitability_cog.tif",
    )
    with (
        patch("backend_api.routers.models.validate_explainability_artifacts_for_model"),
        patch("backend_api.routers.models.validate_driver_band_indices_for_model"),
    ):
        with _admin_client(
            catalog_docs,
            mock_storage,
            project_documents=[SAMPLE_PROJECT],
        ) as c:
            r = c.post(
                    "/api/models",
                headers={"Authorization": "Bearer fake.token"},
                data={
                    "project_id": "proj-1",
                    "species": "New species",
                    "activity": "Flight",
                    "metadata": json.dumps(
                        {"analysis": {"feature_band_names": ["a", "b"]}}
                    ),
                },
                files={
                    "file": ("cog.tif", BytesIO(b"dummy"), "image/tiff"),
                    "serialized_model_file": (
                        "m.pkl",
                        BytesIO(b"pk"),
                        "application/octet-stream",
                    ),
                },
            )
    assert r.status_code == 201
    body = r.json()
    assert body["metadata"]["analysis"]["serialized_model_path"] == SERIALIZED_MODEL_FILENAME
    assert body["metadata"]["analysis"]["feature_band_names"] == ["a", "b"]
    mid = body["id"]
    mock_storage.write_model_artifact_from_path.assert_called_once()
    call_args = mock_storage.write_model_artifact_from_path.call_args[0]
    assert call_args[0] == mid
    assert call_args[1] == SERIALIZED_MODEL_FILENAME
    assert isinstance(call_args[2], str)
    assert call_args[2]


def test_post_models_unknown_feature_band_names_400(catalog_docs):
    mock_storage = MagicMock()
    mock_storage.write_suitability_cog.return_value = (
        "/data/models/new-id",
        "suitability_cog.tif",
    )
    mock_storage.write_suitability_cog_from_path.return_value = (
        "/data/models/new-id",
        "suitability_cog.tif",
    )
    with _admin_client(
        catalog_docs,
        mock_storage,
        project_documents=[SAMPLE_PROJECT],
    ) as c:
        r = c.post(
                "/api/models",
            headers={"Authorization": "Bearer fake.token"},
            data={
                "project_id": "proj-1",
                "species": "Sp",
                "activity": "Act",
                "metadata": json.dumps(
                    {"analysis": {"feature_band_names": ["a", "not_in_manifest"]}}
                ),
            },
            files={"file": ("cog.tif", BytesIO(b"dummy"), "image/tiff")},
        )
    assert r.status_code == 400
    detail = r.json()["detail"]
    assert detail["error"] == "invalid_feature_band_names"
    assert "not_in_manifest" in detail["unknown_feature_band_names"]


def test_post_models_duplicate_409(catalog_docs):
    """Same project_id + species + activity as an existing model returns 409."""
    mock_storage = MagicMock()
    mock_storage.write_suitability_cog.return_value = (
        "/data/models/new-id",
        "suitability_cog.tif",
    )
    mock_storage.write_suitability_cog_from_path.return_value = (
        "/data/models/new-id",
        "suitability_cog.tif",
    )
    with _admin_client(
        catalog_docs,
        mock_storage,
        project_documents=[SAMPLE_PROJECT],
    ) as c:
        r = c.post(
                "/api/models",
            headers={"Authorization": "Bearer fake.token"},
            data={
                "project_id": "proj-1",
                "species": "Bat",
                "activity": "Roost",
            },
            files={"file": ("cog.tif", BytesIO(b"dummy"), "image/tiff")},
        )
    assert r.status_code == 409
    body = r.json()["detail"]
    assert body["code"] == "MODEL_DUPLICATE"
    assert body["context"]["existing_model_id"] == "existing-id"


def test_post_models_201_creates_model(catalog_docs):
    mock_storage = MagicMock()
    mock_storage.write_suitability_cog.return_value = (
        "/data/models/new-id",
        "suitability_cog.tif",
    )
    mock_storage.write_suitability_cog_from_path.return_value = (
        "/data/models/new-id",
        "suitability_cog.tif",
    )
    with _admin_client(
        catalog_docs,
        mock_storage,
        project_documents=[SAMPLE_PROJECT],
    ) as c:
        r = c.post(
                "/api/models",
            headers={"Authorization": "Bearer fake.token"},
            data={
                "project_id": "proj-1",
                "species": "New species",
                "activity": "Flight",
                "metadata": '{"card":{"title":"m1"}}',
            },
            files={"file": ("cog.tif", BytesIO(b"dummy"), "image/tiff")},
        )
    assert r.status_code == 201
    data = r.json()
    assert data["species"] == "New species"
    assert data["activity"] == "Flight"
    assert data["metadata"]["card"]["title"] == "m1"
    assert data["project_id"] == "proj-1"
    assert "id" in data
    mock_storage.write_suitability_cog_from_path.assert_called_once()


def test_post_models_201_with_upload_session_id(catalog_docs):
    mock_storage = MagicMock()
    mock_storage.__class__.__name__ = "GcsObjectStorage"
    mock_storage.promote_upload_session_suitability_cog.return_value = (
        "/data/models/new-id",
        "suitability_cog.tif",
    )
    upload_session = UploadSession(
        id="upload-1",
        project_id="proj-1",
        filename="suitability.tif",
        content_type="image/tiff",
        requested_size_bytes=10,
        uploaded_size_bytes=10,
        status="uploaded",
        stage="validate",
        gcs_bucket="hsm-dashboard-model-artifacts",
        object_path="uploads/upload-1/suitability.tif",
        created_by_uid="admin-1",
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
    )

    with (
        patch("backend_api.routers.models.validate_explainability_artifacts_for_model"),
        patch("backend_api.routers.models.validate_driver_band_indices_for_model"),
        patch("backend_api.routers.models.validate_cog_uri_threaded", new_callable=AsyncMock),
        patch(
            "backend_api.routers.models.upload_session_gcs_uri",
            return_value=(
                "gs://hsm-dashboard-model-artifacts/uploads/upload-1/suitability.tif",
                upload_session,
                10,
            ),
        ),
        patch(
            "backend_api.routers.models.resolve_env_cog_uri_for_sampling",
            return_value="/vsicurl/signed-model-upload",
        ),
        patch.dict(
            os.environ,
            {
                "STORAGE_BACKEND": "gcs",
                "GCS_BUCKET": "hsm-dashboard-model-artifacts",
            },
            clear=False,
        ),
    ):
        with _admin_client(
            catalog_docs,
            mock_storage,
            project_documents=[SAMPLE_PROJECT],
        ) as c:
            r = c.post(
                "/api/models",
                headers={"Authorization": "Bearer fake.token"},
                data={
                    "project_id": "proj-1",
                    "species": "New species",
                    "activity": "Flight",
                    "upload_session_id": "upload-1",
                },
            )
    assert r.status_code == 201
    mock_storage.promote_upload_session_suitability_cog.assert_called_once()


def test_post_models_upload_session_storage_failure_marks_failed(catalog_docs):
    mock_storage = MagicMock()
    mock_storage.__class__.__name__ = "GcsObjectStorage"
    mock_storage.promote_upload_session_suitability_cog.side_effect = RuntimeError("disk full")
    upload_session = UploadSession(
        id="upload-1",
        project_id="proj-1",
        filename="suitability.tif",
        content_type="image/tiff",
        requested_size_bytes=10,
        uploaded_size_bytes=10,
        status="uploaded",
        stage="validate",
        gcs_bucket="hsm-dashboard-model-artifacts",
        object_path="uploads/upload-1/suitability.tif",
        created_by_uid="admin-1",
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
    )

    with (
        patch("backend_api.routers.models.validate_explainability_artifacts_for_model"),
        patch("backend_api.routers.models.validate_driver_band_indices_for_model"),
        patch("backend_api.routers.models.validate_cog_uri_threaded", new_callable=AsyncMock),
        patch(
            "backend_api.routers.models.upload_session_gcs_uri",
            return_value=(
                "gs://hsm-dashboard-model-artifacts/uploads/upload-1/suitability.tif",
                upload_session,
                10,
            ),
        ),
        patch(
            "backend_api.routers.models.resolve_env_cog_uri_for_sampling",
            return_value="/vsicurl/signed-model-upload",
        ),
        patch("backend_api.upload_session_ingest.fail_upload_session") as mock_fail_upload_session,
        patch.dict(
            os.environ,
            {
                "STORAGE_BACKEND": "gcs",
                "GCS_BUCKET": "hsm-dashboard-model-artifacts",
            },
            clear=False,
        ),
    ):
        with _admin_client(
            catalog_docs,
            mock_storage,
            project_documents=[SAMPLE_PROJECT],
        ) as c:
            r = c.post(
                "/api/models",
                headers={"Authorization": "Bearer fake.token"},
                data={
                    "project_id": "proj-1",
                    "species": "New species",
                    "activity": "Flight",
                    "upload_session_id": "upload-1",
                },
            )
    assert r.status_code == 503
    assert mock_fail_upload_session.called


def test_put_models_updates_metadata(catalog_docs):
    mock_storage = MagicMock()
    mock_storage.write_suitability_cog.return_value = (
        "/data/models/existing-id",
        "suitability_cog.tif",
    )
    mock_storage.write_suitability_cog_from_path.return_value = (
        "/data/models/existing-id",
        "suitability_cog.tif",
    )
    with _admin_client(
        catalog_docs,
        mock_storage,
        project_documents=[SAMPLE_PROJECT],
    ) as c:
        r = c.put(
                "/api/models/existing-id",
            headers={"Authorization": "Bearer fake.token"},
            data={"species": "Updated"},
        )
    assert r.status_code == 200
    assert r.json()["species"] == "Updated"
    mock_storage.write_suitability_cog.assert_not_called()


def test_put_models_unknown_404(catalog_docs):
    mock_storage = MagicMock()
    with _admin_client(
        catalog_docs,
        mock_storage,
        project_documents=[SAMPLE_PROJECT],
    ) as c:
        r = c.put(
                "/api/models/missing",
            headers={"Authorization": "Bearer fake.token"},
            data={"species": "X"},
        )
    assert r.status_code == 404


def test_post_projects_upload_session_explainability_failure_not_ready():
    mock_storage = MagicMock()
    mock_storage.__class__.__name__ = "GcsObjectStorage"
    mock_storage.promote_upload_session_driver_cog.return_value = (
        "/data/projects/new-id",
        "environmental_cog.tif",
    )
    upload_session = UploadSession(
        id="upload-1",
        project_id="proj-1",
        filename="environmental.tif",
        content_type="image/tiff",
        requested_size_bytes=10,
        uploaded_size_bytes=10,
        status="uploaded",
        stage="validate",
        gcs_bucket="hsm-dashboard-model-artifacts",
        object_path="uploads/upload-1/environmental.tif",
        created_by_uid="admin-1",
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
    )

    with (
        patch(
            "backend_api.routers.projects.upload_session_gcs_uri",
            return_value=(
                "gs://hsm-dashboard-model-artifacts/uploads/upload-1/environmental.tif",
                upload_session,
                10,
            ),
        ),
        patch(
            "backend_api.routers.projects.resolve_env_cog_uri_for_sampling",
            return_value="/vsicurl/signed-project-upload",
        ),
        patch("backend_api.routers.projects.validate_cog_uri_threaded", new_callable=AsyncMock),
        patch(
            "backend_api.routers.projects.band_definitions_for_upload_uri",
            return_value=(
                [
                    {"index": 0, "name": "a", "label": None},
                    {"index": 1, "name": "b", "label": None},
                ],
                [],
            ),
        ),
        patch(
            "backend_api.routers.projects.write_project_explainability_background_parquet",
            side_effect=RuntimeError("bg failed"),
        ),
        patch("backend_api.upload_session_ingest.mark_upload_session") as mock_mark_upload_session,
        patch("backend_api.upload_session_ingest.fail_upload_session") as mock_fail_upload_session,
        patch.dict(
            os.environ,
            {
                "STORAGE_BACKEND": "gcs",
                "GCS_BUCKET": "hsm-dashboard-model-artifacts",
            },
            clear=False,
        ),
    ):
        mock_mark_upload_session.side_effect = (
            lambda settings, session, **kwargs: session.model_copy(
                update={"status": kwargs["status"], "stage": kwargs["stage"]}
            )
        )
        mock_fail_upload_session.side_effect = (
            lambda settings, session, **kwargs: session.model_copy(
                update={
                    "status": "failed",
                    "stage": kwargs["stage"],
                    "error_code": kwargs["error_code"],
                    "error_message": kwargs["error_message"],
                    "error_stage": kwargs["stage"],
                }
            )
        )
        with _admin_client(
            [],
            mock_storage,
            project_documents=[],
        ) as c:
            r = c.post(
                "/api/projects",
                headers={"Authorization": "Bearer fake.token"},
                data={
                    "name": "New Project",
                    "upload_session_id": "upload-1",
                },
            )
    assert r.status_code == 422
    assert mock_fail_upload_session.called
    mark_statuses = [call.kwargs.get("status") for call in mock_mark_upload_session.call_args_list]
    assert "ready" not in mark_statuses
    mock_storage.promote_upload_session_driver_cog.assert_called_once()


def test_post_models_upload_session_requires_gcs_backend(catalog_docs):
    mock_storage = MagicMock()
    with (
        patch.dict(
            os.environ,
            {
                "STORAGE_BACKEND": "local",
                "LOCAL_STORAGE_ROOT": "/tmp/hsm-local",
            },
            clear=False,
        ),
        _admin_client(
            catalog_docs,
            mock_storage,
            project_documents=[SAMPLE_PROJECT],
        ) as c,
    ):
        r = c.post(
            "/api/models",
            headers={"Authorization": "Bearer fake.token"},
            data={
                "project_id": "proj-1",
                "species": "New species",
                "activity": "Flight",
                "upload_session_id": "upload-1",
            },
        )
    assert r.status_code == 503
    detail = r.json().get("detail", {})
    assert isinstance(detail, dict)
    assert detail.get("code") == "STORAGE_BACKEND_UNSUPPORTED"


def test_post_projects_upload_session_requires_gcs_backend():
    mock_storage = MagicMock()
    with (
        patch.dict(
            os.environ,
            {
                "STORAGE_BACKEND": "local",
                "LOCAL_STORAGE_ROOT": "/tmp/hsm-local",
            },
            clear=False,
        ),
        _admin_client(
            [],
            mock_storage,
            project_documents=[],
        ) as c,
    ):
        r = c.post(
            "/api/projects",
            headers={"Authorization": "Bearer fake.token"},
            data={
                "name": "New Project",
                "upload_session_id": "upload-1",
            },
        )
    assert r.status_code == 503
    detail = r.json().get("detail", {})
    assert isinstance(detail, dict)
    assert detail.get("code") == "STORAGE_BACKEND_UNSUPPORTED"
