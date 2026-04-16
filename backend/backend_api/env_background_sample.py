"""Sample random pixels from the environmental COG into a Parquet background matrix for SHAP."""

from __future__ import annotations

import tempfile
from datetime import timedelta
from pathlib import Path
import re

import google.auth
import google.auth.transport.requests
import numpy as np
import pandas as pd
import pyarrow  # noqa: F401 — pandas needs pyarrow for DataFrame.to_parquet(engine="pyarrow")
import rasterio
from google.auth.exceptions import DefaultCredentialsError, RefreshError
from google.cloud import storage
from google.cloud.exceptions import GoogleCloudError
from rasterio.windows import Window

from backend_api.schemas_project import EnvironmentalBandDefinition
from backend_api.settings import Settings
from backend_api.storage import EXPLAINABILITY_BACKGROUND_FILENAME, ObjectStorage


def write_project_explainability_background_parquet(
    storage: ObjectStorage,
    settings: Settings,
    project_id: str,
    artifact_root: str,
    cog_path: str,
    band_defs: list[EnvironmentalBandDefinition],
    n_samples: int,
) -> str:
    """
    Sample pixels from the COG and write ``explainability_background.parquet`` under the project.

    Returns the relative catalog path (fixed filename).
    """
    uri = resolve_env_cog_uri_for_sampling(settings, artifact_root, cog_path)
    tmp_path = sample_background_parquet_to_tempfile(uri, band_defs, n_samples)
    try:
        storage.write_project_artifact_from_path(
            project_id, EXPLAINABILITY_BACKGROUND_FILENAME, str(tmp_path)
        )
    finally:
        tmp_path.unlink(missing_ok=True)
    return EXPLAINABILITY_BACKGROUND_FILENAME


def _looks_like_signing_capability_error(exc: Exception) -> bool:
    if isinstance(exc, (DefaultCredentialsError, RefreshError)):
        return True
    if isinstance(exc, GoogleCloudError):
        return True
    msg = str(exc).lower()
    return (
        "private key" in msg
        or "sign credentials" in msg
        or "could not automatically determine credentials" in msg
    )


def _mint_signed_read_url_for_gcs_uri(settings: Settings, gcs_uri: str) -> str:
    """Create a short-lived GET signed URL for a ``gs://`` object URI."""
    if not gcs_uri.startswith("gs://"):
        raise ValueError("gcs_uri must start with gs://")
    remainder = gcs_uri[5:]
    parts = remainder.split("/", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError("gcs_uri must include bucket and object path")
    bucket_name, object_path = parts

    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(object_path)
    kwargs = {
        "version": "v4",
        "expiration": timedelta(seconds=settings.gcs_signed_read_url_ttl_seconds),
        "method": "GET",
    }
    try:
        return blob.generate_signed_url(**kwargs)
    except Exception as direct_err:
        if not _looks_like_signing_capability_error(direct_err):
            raise
        credentials, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        signer_email = settings.gcs_signed_url_service_account or getattr(
            credentials, "service_account_email", None
        )
        if not signer_email or signer_email == "default":
            raise RuntimeError(
                "runtime credentials cannot sign directly; set "
                "GCS_SIGNED_URL_SERVICE_ACCOUNT to a signer service account email"
            ) from direct_err
        if credentials is None:
            raise RuntimeError(
                "storage client has no credentials available for IAM signed URL fallback"
            ) from direct_err
        access_token = getattr(credentials, "token", None)
        is_expired = bool(getattr(credentials, "expired", False))
        if not access_token or is_expired:
            request = google.auth.transport.requests.Request()
            credentials.refresh(request)
            access_token = getattr(credentials, "token", None)
        if not access_token:
            raise RuntimeError(
                "could not refresh access token for IAM signed URL fallback"
            ) from direct_err
        return blob.generate_signed_url(
            **kwargs,
            service_account_email=signer_email,
            access_token=access_token,
        )


def resolve_env_cog_uri_for_sampling(
    settings: Settings, artifact_root: str, cog_rel: str
) -> str:
    """
    Path or URI for rasterio to open the environmental COG.

    For GCS-backed roots, return ``/vsicurl/<signed-https-url>`` so rasterio/GDAL can
    perform cloud-friendly ranged reads without requiring GDAL ``gs://`` auth setup.
    """
    rel = cog_rel.strip()
    if rel.startswith("/"):
        return rel
    root = artifact_root.rstrip("/")
    if root.startswith("gs://"):
        gcs_uri = f"{root}/{rel}"
        signed_url = _mint_signed_read_url_for_gcs_uri(settings, gcs_uri)
        return f"/vsicurl/{signed_url}"
    return str(Path(root) / rel)


def sample_background_parquet_bytes(
    cog_uri: str,
    band_definitions: list[EnvironmentalBandDefinition],
    n_samples: int,
    *,
    seed: int | None = None,
) -> bytes:
    """
    Randomly sample ``n_samples`` pixels (all bands) into a Parquet file.

    Column names are ``EnvironmentalBandDefinition.name`` sorted by ``index``.
    Skips windows that contain NaN in any band.
    """
    tmp_path = sample_background_parquet_to_tempfile(
        cog_uri, band_definitions, n_samples, seed=seed
    )
    try:
        return tmp_path.read_bytes()
    finally:
        tmp_path.unlink(missing_ok=True)


def sample_background_parquet_to_tempfile(
    cog_uri: str,
    band_definitions: list[EnvironmentalBandDefinition],
    n_samples: int,
    *,
    seed: int | None = None,
) -> Path:
    """Randomly sample pixels and write Parquet directly to a temp file."""
    defs = sorted(band_definitions, key=lambda d: d.index)
    names = [d.name for d in defs]

    rng = np.random.default_rng(seed)
    with rasterio.open(cog_uri) as src:
        n_bands = int(src.count)
        if n_bands != len(defs):
            raise ValueError(
                f"band definitions count ({len(defs)}) does not match raster band count ({n_bands})"
            )
        height, width = int(src.height), int(src.width)
        if height < 1 or width < 1:
            raise ValueError("raster has invalid dimensions")

        rows = np.empty((n_samples, n_bands), dtype=np.float64)
        filled = 0
        max_attempts = max(n_samples * 20, n_samples + 100)
        attempts = 0
        while filled < n_samples and attempts < max_attempts:
            attempts += 1
            row = int(rng.integers(0, height))
            col = int(rng.integers(0, width))
            window = Window(col, row, 1, 1)
            data = src.read(window=window)
            if data.shape != (n_bands, 1, 1):
                continue
            vals = data[:, 0, 0].astype(np.float64)
            if not np.all(np.isfinite(vals)):
                continue
            rows[filled, :] = vals
            filled += 1

        if filled < n_samples:
            raise ValueError(
                f"could only sample {filled} valid pixels (try smaller n_samples or check nodata)"
            )

    with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    df = pd.DataFrame(rows, columns=names)
    df.to_parquet(tmp_path, engine="pyarrow", index=False)
    return tmp_path


def sanitize_exception_for_client(exc: Exception) -> str:
    """
    Strip URL query strings/tokens from exception text before returning to API clients.
    """
    msg = str(exc)
    # Drop query parameters that may contain signed URL tokens.
    msg = re.sub(r"https?://[^\s?]+[?][^\s]+", "<redacted-url>", msg)
    return msg
