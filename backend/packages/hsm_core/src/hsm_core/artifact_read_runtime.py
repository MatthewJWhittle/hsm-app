"""Read-time artefact access: prepare URIs and library inputs for rasterio, pyarrow/pandas, and opaque bytes."""

from __future__ import annotations

import logging
from datetime import timedelta
from pathlib import Path
from typing import Any

import google.auth
import google.auth.transport.requests
import pandas as pd
import pyarrow.fs as pafs
import pyarrow.parquet as pq
from google.auth.exceptions import DefaultCredentialsError, RefreshError
from google.cloud import storage
from google.cloud.exceptions import GoogleCloudError

from hsm_core.env_cog_paths import split_gs_uri
from hsm_core.settings import WorkerSettings

logger = logging.getLogger(__name__)


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


class ArtifactReadRuntime:
    """
    Thin read-side runtime: signing config from settings, plus library-facing prep for:

    * **Raster** — ``rasterio.open`` via ``/vsicurl`` for ``gs://`` (ranged HTTP reads); use
      :meth:`raster_band_count` / :meth:`rasterio_open_uri` so GDAL never sees raw ``gs://``.
    * **Columnar** — Parquet via pyarrow filesystem for ``gs://``, pandas for local paths.
    * **Opaque** — full byte reads for pickle and similar.
    """

    def __init__(self, settings: WorkerSettings) -> None:
        self._settings = settings
        self._gcs_storage_client: storage.Client | None = None

    def _storage_client(self) -> storage.Client:
        """One client per runtime instance (connection pooling friendly)."""
        if self._gcs_storage_client is None:
            self._gcs_storage_client = storage.Client()
        return self._gcs_storage_client

    def mint_signed_get_url(self, gcs_uri: str) -> str:
        """
        Short-lived HTTPS GET URL for a ``gs://`` object.

        Subclasses may override or wrap for URL reuse (not implemented here).
        """
        if not gcs_uri.startswith("gs://"):
            raise ValueError("gcs_uri must start with gs://")
        remainder = gcs_uri[5:]
        parts = remainder.split("/", 1)
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise ValueError("gcs_uri must include bucket and object path")
        bucket_name, object_path = parts

        bucket = self._storage_client().bucket(bucket_name)
        blob = bucket.blob(object_path)
        kwargs = {
            "version": "v4",
            "expiration": timedelta(seconds=self._settings.gcs_signed_read_url_ttl_seconds),
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
            signer_email = self._settings.gcs_signed_url_service_account or getattr(
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

    def rasterio_open_uri(self, ref: str) -> str:
        """
        URI or path to pass to ``rasterio.open``.

        Local paths and absolute ``/`` paths are unchanged. ``gs://`` is rewritten to
        ``/vsicurl/<signed https URL>`` for cloud-efficient ranged reads.
        """
        if ref.startswith("gs://"):
            signed_url = self.mint_signed_get_url(ref)
            return f"/vsicurl/{signed_url}"
        return ref

    def raster_band_count(self, ref: str) -> int:
        """
        Number of raster bands (e.g. environmental COG), after :meth:`rasterio_open_uri` prep.

        ``ref`` may be a local path, ``gs://`` object path, or an already-prepared ``/vsicurl/...``
        URL (passed through unchanged by :meth:`rasterio_open_uri`).
        """
        import rasterio

        with rasterio.open(self.rasterio_open_uri(ref)) as src:
            return int(src.count)

    def read_opaque_bytes(self, uri: str) -> bytes:
        """Full object bytes (e.g. pickle); ``gs://`` uses Application Default Credentials."""
        if uri.startswith("gs://"):
            bucket_name, blob_name = split_gs_uri(uri)
            return (
                self._storage_client()
                .bucket(bucket_name)
                .blob(blob_name)
                .download_as_bytes()
            )
        with open(uri, "rb") as f:
            return f.read()

    def artifact_cache_fingerprint(self, path: str) -> float:
        """
        Stable cache key for local files (mtime) or ``gs://`` objects (generation).

        Matches the semantics previously used by the explainability LRU cache.
        """
        if path.startswith("gs://"):
            try:
                bucket_name, blob_name = split_gs_uri(path)
                blob = (
                    self._storage_client()
                    .bucket(bucket_name)
                    .blob(blob_name)
                )
                blob.reload()
                if blob.generation is not None:
                    return float(blob.generation)
            except Exception:
                logger.debug(
                    "artifact cache fingerprint failed for %s", path, exc_info=True
                )
            return -1.0
        try:
            return Path(path).stat().st_mtime
        except OSError:
            return -1.0

    def read_explainability_background_parquet(
        self,
        uri: str,
        **read_kwargs: Any,
    ) -> pd.DataFrame:
        """
        Load the explainability background Parquet as a DataFrame (v1: full read).

        For ``gs://``, uses pyarrow with a GCS filesystem (no eager Python-side download).
        For local paths, uses :func:`pandas.read_parquet`.

        ``**read_kwargs`` are forwarded to :func:`pyarrow.parquet.read_table` when ``uri`` is
        ``gs://``, and to :func:`pandas.read_parquet` when ``uri`` is a local path. Only pass
        keyword arguments that are valid for **both** APIs (e.g. ``columns=``) unless you know
        which branch runs; otherwise use separate call sites or extend this method with
        explicit ``pyarrow_kwargs`` / ``pandas_kwargs`` parameters.
        """
        if uri.startswith("gs://"):
            filesystem, path = pafs.FileSystem.from_uri(uri)
            table = pq.read_table(path, filesystem=filesystem, **read_kwargs)
            return table.to_pandas()
        return pd.read_parquet(uri, **read_kwargs)
