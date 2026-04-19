"""Pluggable storage for admin suitability COG uploads (local vs GCS)."""

from __future__ import annotations

import logging
import re
import shutil
from pathlib import Path
from typing import Protocol

from hsm_core.settings import Settings

logger = logging.getLogger(__name__)

SUITABILITY_FILENAME = "suitability_cog.tif"
ENVIRONMENTAL_DRIVER_FILENAME = "environmental_cog.tif"

# Fixed names under each model's artifact folder (see ``metadata.analysis.serialized_model_path``).
SERIALIZED_MODEL_FILENAME = "serialized_model.pkl"
EXPLAINABILITY_MODEL_FILENAME = SERIALIZED_MODEL_FILENAME  # legacy alias
EXPLAINABILITY_BACKGROUND_FILENAME = "explainability_background.parquet"


class ObjectStorage(Protocol):
    """Write suitability COG bytes for a model id; return catalog path fields."""

    def write_suitability_cog(self, model_id: str, content: bytes) -> tuple[str, str]:
        """
        Persist the COG and return ``(artifact_root, suitability_cog_path)``.

        ``suitability_cog_path`` may be relative to ``artifact_root`` or absolute
        (see ``resolve_cog_path`` in point_sampling).
        """

    def write_project_driver_cog(self, project_id: str, content: bytes) -> tuple[str, str]:
        """Persist shared environmental COG for a catalog project; return ``(artifact_root, path)``."""

    def write_suitability_cog_from_path(self, model_id: str, source_path: str) -> tuple[str, str]:
        """Persist suitability COG from a local on-disk path; return catalog path fields."""

    def write_project_driver_cog_from_path(self, project_id: str, source_path: str) -> tuple[str, str]:
        """Persist project environmental COG from a local on-disk path; return catalog path fields."""

    def promote_upload_session_suitability_cog(
        self,
        *,
        model_id: str,
        source_bucket: str,
        source_object_path: str,
    ) -> tuple[str, str]:
        """Promote uploaded object into model suitability COG location; return ``(artifact_root, path)``."""

    def promote_upload_session_driver_cog(
        self,
        *,
        project_id: str,
        source_bucket: str,
        source_object_path: str,
    ) -> tuple[str, str]:
        """Promote uploaded object into project environmental COG location; return ``(artifact_root, path)``."""

    def write_project_artifact(self, project_id: str, relative_name: str, content: bytes) -> None:
        """Write a non-COG file under ``projects/{project_id}/`` (e.g. explainability background Parquet)."""

    def write_project_artifact_from_path(
        self, project_id: str, relative_name: str, source_path: str
    ) -> None:
        """Write a non-COG file under ``projects/{project_id}/`` from a local path."""

    def write_model_artifact(self, model_id: str, relative_name: str, content: bytes) -> None:
        """Write a non-COG file under ``models/{model_id}/`` (e.g. sklearn pickle, parquet)."""

    def write_model_artifact_from_path(
        self, model_id: str, relative_name: str, source_path: str
    ) -> None:
        """Write a non-COG file under ``models/{model_id}/`` from a local path."""


class LocalObjectStorage:
    """Store under ``{root}/models/{model_id}/suitability_cog.tif``."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def write_suitability_cog(self, model_id: str, content: bytes) -> tuple[str, str]:
        safe_id = _safe_segment(model_id)
        dest_dir = self._root / "models" / safe_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / SUITABILITY_FILENAME
        dest_path.write_bytes(content)
        artifact_root = str(dest_dir)
        # Relative filename matches docs/data-models.md (folder-per-model + fixed name).
        return artifact_root, SUITABILITY_FILENAME

    def write_suitability_cog_from_path(self, model_id: str, source_path: str) -> tuple[str, str]:
        safe_id = _safe_segment(model_id)
        dest_dir = self._root / "models" / safe_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / SUITABILITY_FILENAME
        shutil.copyfile(source_path, dest_path)
        artifact_root = str(dest_dir)
        return artifact_root, SUITABILITY_FILENAME

    def write_project_driver_cog(self, project_id: str, content: bytes) -> tuple[str, str]:
        safe_id = _safe_segment(project_id)
        dest_dir = self._root / "projects" / safe_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / ENVIRONMENTAL_DRIVER_FILENAME
        dest_path.write_bytes(content)
        artifact_root = str(dest_dir)
        return artifact_root, ENVIRONMENTAL_DRIVER_FILENAME

    def write_project_driver_cog_from_path(self, project_id: str, source_path: str) -> tuple[str, str]:
        safe_id = _safe_segment(project_id)
        dest_dir = self._root / "projects" / safe_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / ENVIRONMENTAL_DRIVER_FILENAME
        shutil.copyfile(source_path, dest_path)
        artifact_root = str(dest_dir)
        return artifact_root, ENVIRONMENTAL_DRIVER_FILENAME

    def promote_upload_session_driver_cog(
        self,
        *,
        project_id: str,
        source_bucket: str,
        source_object_path: str,
    ) -> tuple[str, str]:
        raise NotImplementedError(
            "upload session promotion is only supported when STORAGE_BACKEND=gcs"
        )

    def promote_upload_session_suitability_cog(
        self,
        *,
        model_id: str,
        source_bucket: str,
        source_object_path: str,
    ) -> tuple[str, str]:
        raise NotImplementedError(
            "upload session promotion is only supported when STORAGE_BACKEND=gcs"
        )

    def write_project_artifact(self, project_id: str, relative_name: str, content: bytes) -> None:
        _validate_artifact_relative_name(relative_name)
        safe_id = _safe_segment(project_id)
        dest_dir = self._root / "projects" / safe_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        (dest_dir / relative_name).write_bytes(content)

    def write_project_artifact_from_path(
        self, project_id: str, relative_name: str, source_path: str
    ) -> None:
        _validate_artifact_relative_name(relative_name)
        safe_id = _safe_segment(project_id)
        dest_dir = self._root / "projects" / safe_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_path, str(dest_dir / relative_name))

    def write_model_artifact(self, model_id: str, relative_name: str, content: bytes) -> None:
        _validate_artifact_relative_name(relative_name)
        safe_id = _safe_segment(model_id)
        dest_dir = self._root / "models" / safe_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        (dest_dir / relative_name).write_bytes(content)

    def write_model_artifact_from_path(
        self, model_id: str, relative_name: str, source_path: str
    ) -> None:
        _validate_artifact_relative_name(relative_name)
        safe_id = _safe_segment(model_id)
        dest_dir = self._root / "models" / safe_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_path, str(dest_dir / relative_name))


class GcsObjectStorage:
    """Upload to ``gs://{bucket}/{prefix}models/{model_id}/suitability_cog.tif``."""

    def __init__(self, bucket_name: str, prefix: str) -> None:
        from google.cloud import storage

        self._client = storage.Client()
        self._bucket = self._client.bucket(bucket_name)
        self._prefix = normalize_gcs_prefix(prefix)

    def write_suitability_cog(self, model_id: str, content: bytes) -> tuple[str, str]:
        safe_id = _safe_segment(model_id)
        blob_name = f"{self._prefix}models/{safe_id}/{SUITABILITY_FILENAME}"
        blob = self._bucket.blob(blob_name)
        blob.upload_from_string(content, content_type="image/tiff")
        artifact_root = f"gs://{self._bucket.name}/{self._prefix}models/{safe_id}"
        return artifact_root, SUITABILITY_FILENAME

    def write_suitability_cog_from_path(self, model_id: str, source_path: str) -> tuple[str, str]:
        safe_id = _safe_segment(model_id)
        blob_name = f"{self._prefix}models/{safe_id}/{SUITABILITY_FILENAME}"
        blob = self._bucket.blob(blob_name)
        blob.upload_from_filename(source_path, content_type="image/tiff")
        artifact_root = f"gs://{self._bucket.name}/{self._prefix}models/{safe_id}"
        return artifact_root, SUITABILITY_FILENAME

    def write_project_driver_cog(self, project_id: str, content: bytes) -> tuple[str, str]:
        safe_id = _safe_segment(project_id)
        blob_name = f"{self._prefix}projects/{safe_id}/{ENVIRONMENTAL_DRIVER_FILENAME}"
        blob = self._bucket.blob(blob_name)
        blob.upload_from_string(content, content_type="image/tiff")
        artifact_root = f"gs://{self._bucket.name}/{self._prefix}projects/{safe_id}"
        return artifact_root, ENVIRONMENTAL_DRIVER_FILENAME

    def write_project_driver_cog_from_path(self, project_id: str, source_path: str) -> tuple[str, str]:
        safe_id = _safe_segment(project_id)
        blob_name = f"{self._prefix}projects/{safe_id}/{ENVIRONMENTAL_DRIVER_FILENAME}"
        blob = self._bucket.blob(blob_name)
        blob.upload_from_filename(source_path, content_type="image/tiff")
        artifact_root = f"gs://{self._bucket.name}/{self._prefix}projects/{safe_id}"
        return artifact_root, ENVIRONMENTAL_DRIVER_FILENAME

    def promote_upload_session_driver_cog(
        self,
        *,
        project_id: str,
        source_bucket: str,
        source_object_path: str,
    ) -> tuple[str, str]:
        safe_id = _safe_segment(project_id)
        if source_bucket != self._bucket.name:
            raise ValueError("upload session bucket does not match storage backend bucket")
        src_blob = self._bucket.blob(source_object_path)
        if not src_blob.exists():
            raise ValueError("upload source object not found in storage")
        dst_name = f"{self._prefix}projects/{safe_id}/{ENVIRONMENTAL_DRIVER_FILENAME}"
        self._bucket.copy_blob(src_blob, self._bucket, new_name=dst_name)
        artifact_root = f"gs://{self._bucket.name}/{self._prefix}projects/{safe_id}"
        return artifact_root, ENVIRONMENTAL_DRIVER_FILENAME

    def promote_upload_session_suitability_cog(
        self,
        *,
        model_id: str,
        source_bucket: str,
        source_object_path: str,
    ) -> tuple[str, str]:
        safe_id = _safe_segment(model_id)
        if source_bucket != self._bucket.name:
            raise ValueError("upload session bucket does not match storage backend bucket")
        src_blob = self._bucket.blob(source_object_path)
        if not src_blob.exists():
            raise ValueError("upload source object not found in storage")
        dst_name = f"{self._prefix}models/{safe_id}/{SUITABILITY_FILENAME}"
        self._bucket.copy_blob(src_blob, self._bucket, new_name=dst_name)
        artifact_root = f"gs://{self._bucket.name}/{self._prefix}models/{safe_id}"
        return artifact_root, SUITABILITY_FILENAME

    def write_project_artifact(self, project_id: str, relative_name: str, content: bytes) -> None:
        _validate_artifact_relative_name(relative_name)
        safe_id = _safe_segment(project_id)
        blob_name = f"{self._prefix}projects/{safe_id}/{relative_name}"
        blob = self._bucket.blob(blob_name)
        blob.upload_from_string(content)

    def write_project_artifact_from_path(
        self, project_id: str, relative_name: str, source_path: str
    ) -> None:
        _validate_artifact_relative_name(relative_name)
        safe_id = _safe_segment(project_id)
        blob_name = f"{self._prefix}projects/{safe_id}/{relative_name}"
        blob = self._bucket.blob(blob_name)
        blob.upload_from_filename(source_path)

    def write_model_artifact(self, model_id: str, relative_name: str, content: bytes) -> None:
        _validate_artifact_relative_name(relative_name)
        safe_id = _safe_segment(model_id)
        blob_name = f"{self._prefix}models/{safe_id}/{relative_name}"
        blob = self._bucket.blob(blob_name)
        blob.upload_from_string(content)

    def write_model_artifact_from_path(
        self, model_id: str, relative_name: str, source_path: str
    ) -> None:
        _validate_artifact_relative_name(relative_name)
        safe_id = _safe_segment(model_id)
        blob_name = f"{self._prefix}models/{safe_id}/{relative_name}"
        blob = self._bucket.blob(blob_name)
        blob.upload_from_filename(source_path)


def normalize_gcs_prefix(prefix: str) -> str:
    """Ensure non-empty prefix ends with '/' for safe concatenation."""
    p = (prefix or "").strip()
    if not p:
        return ""
    return p if p.endswith("/") else f"{p}/"


def _safe_segment(model_id: str) -> str:
    if not re.match(r"^[a-zA-Z0-9._-]+$", model_id):
        raise ValueError("model id contains invalid characters")
    return model_id


def _validate_artifact_relative_name(name: str) -> None:
    """Reject path traversal and odd filenames for model-scoped artefacts."""
    if not name or name.strip() != name:
        raise ValueError("invalid artifact name")
    if ".." in name or "/" in name or "\\" in name:
        raise ValueError("artifact name must be a single path segment")
    if not re.match(r"^[a-zA-Z0-9._-]+$", name):
        raise ValueError("artifact name contains invalid characters")


def build_object_storage(settings: Settings) -> ObjectStorage:
    backend = (settings.storage_backend or "local").strip().lower()
    if backend == "local":
        root = Path(settings.local_storage_root).expanduser().resolve()
        logger.info("Object storage: local root=%s", root)
        return LocalObjectStorage(root)
    if backend == "gcs":
        if not settings.gcs_bucket:
            raise RuntimeError("GCS_BUCKET is required when STORAGE_BACKEND=gcs")
        return GcsObjectStorage(settings.gcs_bucket, settings.gcs_object_prefix)
    raise RuntimeError(f"Unknown STORAGE_BACKEND={settings.storage_backend!r}")
