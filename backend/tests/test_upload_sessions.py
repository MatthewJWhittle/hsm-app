"""Tests for admin upload session endpoints."""

from __future__ import annotations

import importlib
import os
from contextlib import contextmanager
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from backend_api.upload_session_runtime import mark_upload_session
from backend_api.settings import Settings
from backend_api.schemas_upload import UploadSession


class _FakeDoc:
    def __init__(self, doc_id: str, store: dict[str, dict]) -> None:
        self._id = doc_id
        self._store = store

    @property
    def id(self) -> str:
        return self._id

    @property
    def exists(self) -> bool:
        return self._id in self._store

    def to_dict(self) -> dict | None:
        return self._store.get(self._id)

    def set(self, data: dict) -> None:
        self._store[self._id] = dict(data)

    def get(self) -> "_FakeDoc":
        return self


class _FakeCollection:
    def __init__(self, store: dict[str, dict]) -> None:
        self._store = store

    def document(self, doc_id: str) -> _FakeDoc:
        return _FakeDoc(doc_id, self._store)

    def stream(self):
        for doc_id, data in self._store.items():
            doc = _FakeDoc(doc_id, self._store)
            doc.set(data)
            yield doc


class _FakeFirestoreClient:
    def __init__(self) -> None:
        self._collections: dict[str, dict[str, dict]] = {}

    def collection(self, name: str) -> _FakeCollection:
        if name not in self._collections:
            self._collections[name] = {}
        return _FakeCollection(self._collections[name])


@contextmanager
def _admin_client():
    fake_client = _FakeFirestoreClient()
    fake_storage_client = _FakeStorageClient()
    with (
        patch(
            "backend_api.auth_deps.auth.verify_id_token",
            return_value={"uid": "admin-1", "admin": True},
        ),
        patch("google.cloud.firestore.Client", return_value=fake_client),
        patch("backend_api.routers.uploads.storage.Client", return_value=fake_storage_client),
        patch.dict(
            os.environ,
            {
                "STORAGE_BACKEND": "gcs",
                "GCS_BUCKET": "hsm-dashboard-model-artifacts",
            },
            clear=False,
        ),
    ):
        import backend_api.main as main

        importlib.reload(main)
        with TestClient(main.app) as client:
            yield client


def test_upload_init_get_and_complete_lifecycle():
    with _admin_client() as c:
        init = c.post(
            "/api/uploads/init",
            headers={"Authorization": "Bearer fake.token"},
            json={
                "project_id": "proj-1",
                "filename": "env_stack.tif",
                "content_type": "image/tiff",
                "size_bytes": 12345,
            },
        )
        assert init.status_code == 201
        session = init.json()
        upload_id = session["id"]
        assert session["status"] == "pending"
        assert session["stage"] == "upload"
        assert session["gcs_bucket"] == "hsm-dashboard-model-artifacts"
        assert session["object_path"].startswith(f"uploads/{upload_id}/")
        assert session["upload_url"].startswith("https://signed-upload.local/")

        fetched = c.get(
            f"/api/uploads/{upload_id}",
            headers={"Authorization": "Bearer fake.token"},
        )
        assert fetched.status_code == 200
        assert fetched.json()["status"] == "pending"
        assert fetched.json()["stage"] == "upload"
        assert fetched.json()["upload_url"] is None

        complete = c.post(
            f"/api/uploads/{upload_id}/complete",
            headers={"Authorization": "Bearer fake.token"},
            json={"size_bytes": 12345, "checksum_sha256": "a" * 64},
        )
        assert complete.status_code == 200
        body = complete.json()
        assert body["status"] == "uploaded"
        assert body["stage"] == "validate"
        assert body["uploaded_size_bytes"] == 12345
        assert body["checksum_sha256"] == "a" * 64


def test_upload_complete_unknown_returns_404():
    with _admin_client() as c:
        r = c.post(
            "/api/uploads/missing/complete",
            headers={"Authorization": "Bearer fake.token"},
            json={},
        )
        assert r.status_code == 404


def test_upload_complete_failed_status_returns_409():
    with _admin_client() as c:
        init = c.post(
            "/api/uploads/init",
            headers={"Authorization": "Bearer fake.token"},
            json={
                "filename": "env_stack.tif",
            },
        )
        assert init.status_code == 201
        upload_id = init.json()["id"]

        # Simulate worker marking a terminal failure.
        from backend_api.upload_sessions import get_upload_session, upsert_upload_session
        from backend_api.settings import Settings

        settings = Settings()
        existing = get_upload_session(settings, upload_id)
        assert existing is not None
        failed = existing.model_copy(
            update={
                "status": "failed",
                "stage": "validate",
                "error_code": "COG_VALIDATION",
                "error_message": "invalid CRS",
                "error_stage": "validate",
            }
        )
        upsert_upload_session(settings, failed)

        r = c.post(
            f"/api/uploads/{upload_id}/complete",
            headers={"Authorization": "Bearer fake.token"},
            json={},
        )
        assert r.status_code == 409


def test_mint_signed_upload_url_falls_back_to_iam_signing():
    class _Creds:
        service_account_email = "hsm-api-staging@hsm-dashboard.iam.gserviceaccount.com"

        def __init__(self):
            self.token = None

        def refresh(self, _request):
            self.token = "ya29.token"

    class _Blob:
        def __init__(self):
            self.calls: list[dict] = []

        def generate_signed_url(self, **kwargs):
            self.calls.append(kwargs)
            if "service_account_email" not in kwargs:
                raise RuntimeError("you need a private key to sign credentials")
            return "https://signed-upload.local/fallback"

    class _Bucket:
        def __init__(self, blob):
            self._blob = blob

        def blob(self, _path):
            return self._blob

    class _Client:
        def __init__(self, blob):
            self._credentials = _Creds()
            self._blob = blob

        def bucket(self, _name):
            return _Bucket(self._blob)

    from backend_api.routers import uploads as uploads_router

    blob = _Blob()
    with (
        patch("backend_api.routers.uploads.storage.Client", return_value=_Client(blob)),
        patch.dict(
            os.environ,
            {
                "GCS_SIGNED_URL_SERVICE_ACCOUNT": "hsm-api-staging@hsm-dashboard.iam.gserviceaccount.com",
            },
            clear=False,
        ),
    ):
        url = uploads_router._mint_signed_upload_url(
            settings=Settings(),
            bucket_name="hsm-dashboard-model-artifacts",
            object_path="uploads/u/file.tif",
            content_type="image/tiff",
        )
    assert url.endswith("/fallback")
    assert len(blob.calls) == 2
    assert "service_account_email" in blob.calls[1]
    assert blob.calls[1]["access_token"] == "ya29.token"


def test_mark_upload_session_rejects_invalid_transition():
    session = UploadSession(
        id="upload-1",
        project_id=None,
        filename="env.tif",
        content_type="image/tiff",
        requested_size_bytes=10,
        uploaded_size_bytes=10,
        checksum_sha256=None,
        status="failed",
        stage="validate",
        gcs_bucket="hsm-dashboard-model-artifacts",
        object_path="uploads/upload-1/env.tif",
        created_by_uid="admin-1",
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
        error_code="VALIDATION",
        error_message="bad file",
        error_stage="validate",
    )
    with patch("backend_api.upload_session_runtime.upsert_upload_session"):
        with pytest.raises(ValueError, match="invalid upload session status transition"):
            mark_upload_session(
                Settings(),
                session,
                status="ready",
                stage="done",
            )


class _FakeStorageBlob:
    def __init__(self, path: str) -> None:
        self._path = path

    def generate_signed_url(self, **_kwargs) -> str:
        return f"https://signed-upload.local/{self._path}"


class _FakeStorageBucket:
    def blob(self, object_path: str) -> _FakeStorageBlob:
        return _FakeStorageBlob(object_path)


class _FakeStorageClient:
    def bucket(self, _bucket_name: str) -> _FakeStorageBucket:
        return _FakeStorageBucket()
