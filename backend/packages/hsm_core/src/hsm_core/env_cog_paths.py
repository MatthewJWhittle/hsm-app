"""Resolve environmental COG paths without FastAPI dependencies."""

from __future__ import annotations

from pathlib import Path


def raster_storage_uri_readable(ref: str) -> bool:
    """True if ``ref`` can be passed to rasterio (local file exists or ``gs://`` URI)."""
    if ref.startswith("gs://"):
        return True
    return Path(ref).is_file()


def environmental_cog_readable_for_sampling(abs_path: str) -> bool:
    """True if sampling can read the COG (local file exists or cloud URI)."""
    return raster_storage_uri_readable(abs_path)


def split_gs_uri(uri: str) -> tuple[str, str]:
    """Return ``(bucket_name, object_name)`` for ``gs://bucket/object``."""
    if not uri.startswith("gs://"):
        raise ValueError("URI must start with gs://")
    rest = uri[5:]
    bucket, _, blob = rest.partition("/")
    if not bucket or not blob:
        raise ValueError(f"invalid GCS URI: {uri!r}")
    return bucket, blob


def gcs_uri_blob_exists(uri: str) -> bool:
    """Return whether a ``gs://`` object exists (uses Application Default Credentials)."""
    from google.cloud import storage

    bucket_name, blob_name = split_gs_uri(uri)
    client = storage.Client()
    return client.bucket(bucket_name).blob(blob_name).exists()


def artifact_uri_exists(uri: str) -> bool:
    """True if a local file exists or a ``gs://`` object exists."""
    if uri.startswith("gs://"):
        return gcs_uri_blob_exists(uri)
    return Path(uri).is_file()


def resolve_artifact_uri(artifact_root: str, rel: str) -> str:
    """
    Resolve ``rel`` under ``artifact_root``.

    - Absolute ``rel`` (leading ``/``): returned as-is (local absolute path).
    - ``artifact_root`` beginning with ``gs://``: join with POSIX semantics (no ``..`` in ``rel``).
    - Otherwise: resolve under local ``artifact_root``; reject ``..`` and paths that escape the root.
    """
    rel = rel.strip()
    if not rel:
        raise ValueError("empty path")
    root = artifact_root.strip()
    if not root:
        raise ValueError("empty artifact root")
    if rel.startswith("/"):
        return rel
    if ".." in Path(rel).parts:
        raise ValueError("path must not contain '..'")
    if root.startswith("gs://"):
        return f"{root.rstrip('/')}/{rel.lstrip('/')}"
    root_path = Path(root).expanduser().resolve()
    candidate = (root_path / rel).resolve()
    if candidate != root_path:
        try:
            candidate.relative_to(root_path)
        except ValueError as e:
            raise ValueError("path escapes artifact root") from e
    return str(candidate)


def resolve_env_cog_path_from_parts(
    artifact_root: str | None, driver_cog_path: str | None
) -> str | None:
    """Absolute path from storage root + relative COG path."""
    if not artifact_root or not driver_cog_path:
        return None
    root = artifact_root.rstrip("/")
    rel = driver_cog_path.strip()
    if rel.startswith("/"):
        return rel
    return f"{root}/{rel}"
