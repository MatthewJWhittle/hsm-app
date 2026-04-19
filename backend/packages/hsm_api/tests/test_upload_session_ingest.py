"""Tests for upload session ingestion helpers."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from google.cloud.exceptions import NotFound
from google.cloud.storage import Bucket

from backend_api.schemas_upload import UploadSession
from backend_api.settings import Settings
from backend_api.upload_session_ingest import upload_session_gcs_uri


def _complete_session() -> UploadSession:
    return UploadSession(
        id="upload-1",
        project_id="proj-1",
        filename="env.tif",
        content_type="image/tiff",
        requested_size_bytes=100,
        uploaded_size_bytes=100,
        status="complete",
        stage="done",
        gcs_bucket="test-bucket",
        object_path="uploads/upload-1/env.tif",
        created_by_uid="u1",
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
    )


def _settings_for_test_bucket() -> Settings:
    with patch.dict(
        os.environ,
        {"STORAGE_BACKEND": "gcs", "GCS_BUCKET": "test-bucket"},
        clear=False,
    ):
        return Settings()


def _storage_client_with_blob(
    object_path: str,
) -> tuple[MagicMock, Bucket, object]:
    """Return (storage_client, bucket, blob) using real library Blob/Bucket types.

    ``client.bucket(...).blob(...)`` must return the *same* ``blob`` instance the
    test configures, because :func:`upload_session_gcs_uri` constructs the blob
    internally (it does not accept a blob from callers).

    The client is a MagicMock with only what :class:`Bucket` needs; ``blob.size``
    comes from ``google.cloud.storage`` property logic on ``_properties``.
    """
    client = MagicMock()
    client.project = "test-project"
    bucket = Bucket(client, "test-bucket")
    blob = bucket.blob(object_path)

    def _bucket(name: str) -> Bucket:
        assert name == "test-bucket"
        return bucket

    def _blob(path: str) -> object:
        assert path == object_path
        return blob

    client.bucket.side_effect = _bucket
    bucket.blob = _blob  # type: ignore[method-assign]

    return client, bucket, blob


def test_gcs_blob_size_comes_from_object_metadata_properties() -> None:
    """Document the contract we rely on: ``size`` is derived from loaded metadata.

    After a metadata fetch, GCS returns ``size`` as a string in JSON; the client
    exposes it as ``int`` on :attr:`google.cloud.storage.Blob.size`.
    """
    _, _, blob = _storage_client_with_blob("uploads/upload-1/env.tif")
    assert blob.size is None
    # Simulate JSON object resource (size is string in API responses).
    blob._properties["size"] = "42000"
    assert blob.size == 42_000


def test_upload_session_gcs_uri_uses_real_blob_size_after_reload() -> None:
    """Regression (issue #63): read size from real Blob after ``reload()`` fills metadata.

    This is not a shallow MagicMock chain: ``blob.size`` is the library property,
    and ``reload`` is patched only to stand in for the HTTP metadata GET.
    """
    settings = _settings_for_test_bucket()
    session = _complete_session()
    client, _, blob = _storage_client_with_blob(session.object_path)

    def _reload() -> None:
        blob._properties["size"] = "42000"

    blob.reload = _reload  # type: ignore[method-assign]

    with (
        patch(
            "backend_api.upload_session_ingest.get_upload_session",
            return_value=session,
        ),
        patch("backend_api.upload_session_ingest.storage.Client", return_value=client),
    ):
        uri, got_session, size = upload_session_gcs_uri(
            settings, session.id, purpose="test"
        )

    assert uri == "gs://test-bucket/uploads/upload-1/env.tif"
    assert got_session is session
    assert size == 42_000


def test_upload_session_gcs_uri_not_found_after_reload() -> None:
    settings = _settings_for_test_bucket()
    session = _complete_session()
    client, _, blob = _storage_client_with_blob(session.object_path)
    blob.reload = MagicMock(side_effect=NotFound("no such object"))  # type: ignore[method-assign]

    with (
        patch(
            "backend_api.upload_session_ingest.get_upload_session",
            return_value=session,
        ),
        patch("backend_api.upload_session_ingest.storage.Client", return_value=client),
    ):
        with pytest.raises(HTTPException) as exc_info:
            upload_session_gcs_uri(settings, session.id, purpose="test")

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail["code"] == "UPLOAD_OBJECT_MISSING"


def test_upload_session_gcs_uri_returns_none_size_when_reload_leaves_size_absent() -> None:
    """If metadata has no size (unexpected), propagate ``None`` for callers to reject."""
    settings = _settings_for_test_bucket()
    session = _complete_session()
    client, _, blob = _storage_client_with_blob(session.object_path)

    def _reload_empty() -> None:
        blob._properties.pop("size", None)

    blob.reload = _reload_empty  # type: ignore[method-assign]

    with (
        patch(
            "backend_api.upload_session_ingest.get_upload_session",
            return_value=session,
        ),
        patch("backend_api.upload_session_ingest.storage.Client", return_value=client),
    ):
        _, _, size = upload_session_gcs_uri(settings, session.id, purpose="test")

    assert size is None
