from __future__ import annotations

from hsm_core.storage import (
    ENVIRONMENTAL_DRIVER_FILENAME,
    GcsObjectStorage,
    SUITABILITY_FILENAME,
)


class _FakeBlob:
    def __init__(self, name: str, *, exists: bool = True, delete_error: Exception | None = None) -> None:
        self.name = name
        self._exists = exists
        self._delete_error = delete_error
        self.deleted = False

    def exists(self) -> bool:
        return self._exists

    def delete(self) -> None:
        if self._delete_error is not None:
            raise self._delete_error
        self.deleted = True


class _FakeBucket:
    name = "hsm-dashboard-model-artifacts"

    def __init__(self, source_blob: _FakeBlob) -> None:
        self.source_blob = source_blob
        self.copied_to: list[str] = []

    def blob(self, name: str) -> _FakeBlob:
        assert name == self.source_blob.name
        return self.source_blob

    def copy_blob(self, source_blob: _FakeBlob, bucket: "_FakeBucket", *, new_name: str) -> _FakeBlob:
        assert source_blob is self.source_blob
        assert bucket is self
        self.copied_to.append(new_name)
        return _FakeBlob(new_name)


def _storage_with_bucket(bucket: _FakeBucket) -> GcsObjectStorage:
    storage = GcsObjectStorage.__new__(GcsObjectStorage)
    storage._bucket = bucket
    storage._prefix = ""
    return storage


def test_promote_upload_session_suitability_cog_deletes_staged_source() -> None:
    source = _FakeBlob("uploads/upload-1/suitability.tif")
    bucket = _FakeBucket(source)
    storage = _storage_with_bucket(bucket)

    artifact_root, path = storage.promote_upload_session_suitability_cog(
        model_id="model-1",
        source_bucket=bucket.name,
        source_object_path=source.name,
    )

    assert artifact_root == "gs://hsm-dashboard-model-artifacts/models/model-1"
    assert path == SUITABILITY_FILENAME
    assert bucket.copied_to == ["models/model-1/suitability_cog.tif"]
    assert source.deleted is True


def test_promote_upload_session_driver_cog_deletes_staged_source() -> None:
    source = _FakeBlob("uploads/upload-1/environmental.tif")
    bucket = _FakeBucket(source)
    storage = _storage_with_bucket(bucket)

    artifact_root, path = storage.promote_upload_session_driver_cog(
        project_id="project-1",
        source_bucket=bucket.name,
        source_object_path=source.name,
    )

    assert artifact_root == "gs://hsm-dashboard-model-artifacts/projects/project-1"
    assert path == ENVIRONMENTAL_DRIVER_FILENAME
    assert bucket.copied_to == ["projects/project-1/environmental_cog.tif"]
    assert source.deleted is True


def test_promote_upload_session_delete_failure_is_non_fatal() -> None:
    source = _FakeBlob("uploads/upload-1/suitability.tif", delete_error=RuntimeError("nope"))
    bucket = _FakeBucket(source)
    storage = _storage_with_bucket(bucket)

    artifact_root, path = storage.promote_upload_session_suitability_cog(
        model_id="model-1",
        source_bucket=bucket.name,
        source_object_path=source.name,
    )

    assert artifact_root == "gs://hsm-dashboard-model-artifacts/models/model-1"
    assert path == SUITABILITY_FILENAME
    assert bucket.copied_to == ["models/model-1/suitability_cog.tif"]
    assert source.deleted is False
