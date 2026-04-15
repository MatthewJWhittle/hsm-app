"""Tests for admin upload session endpoints."""

from __future__ import annotations

import importlib
import os
from contextlib import contextmanager
from unittest.mock import patch

from fastapi.testclient import TestClient


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
