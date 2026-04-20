"""Unit tests for hsm_core ArtifactReadRuntime seam (raster URI, opaque bytes, Parquet)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from hsm_core.artifact_read_runtime import ArtifactReadRuntime
from hsm_core.env_cog_paths import raster_storage_uri_readable, reject_raw_gs_uri_for_rasterio
from hsm_core.settings import WorkerSettings


def test_reject_raw_gs_uri_for_rasterio_raises() -> None:
    with pytest.raises(ValueError, match="rasterio cannot open raw gs://"):
        reject_raw_gs_uri_for_rasterio("gs://bucket/object.tif")


def test_raster_storage_uri_readable_gs_vsicurl_and_local(tmp_path: Path) -> None:
    assert raster_storage_uri_readable("gs://b/o.tif")
    assert raster_storage_uri_readable("/vsicurl/https://example.com/x.tif")
    p = tmp_path / "f.tif"
    p.write_bytes(b"")
    assert raster_storage_uri_readable(str(p))


def test_rasterio_open_uri_local_passthrough(tmp_path: Path) -> None:
    p = tmp_path / "x.tif"
    p.write_bytes(b"")
    rt = ArtifactReadRuntime(WorkerSettings())
    assert rt.rasterio_open_uri(str(p)) == str(p)


def test_rasterio_open_uri_gs_uses_vsicurl() -> None:
    settings = WorkerSettings()
    rt = ArtifactReadRuntime(settings)
    with patch.object(rt, "mint_signed_get_url", return_value="https://signed.example/o?token=1"):
        out = rt.rasterio_open_uri("gs://b/k/o.tif")
    assert out.startswith("/vsicurl/https://signed.example/o?token=1")


def test_read_opaque_bytes_local(tmp_path: Path) -> None:
    f = tmp_path / "m.pkl"
    f.write_bytes(b"hello")
    rt = ArtifactReadRuntime(WorkerSettings())
    assert rt.read_opaque_bytes(str(f)) == b"hello"


def test_read_opaque_bytes_gcs() -> None:
    rt = ArtifactReadRuntime(WorkerSettings())
    mock_blob = MagicMock()
    mock_blob.download_as_bytes.return_value = b"xyz"
    with patch("hsm_core.artifact_read_runtime.storage.Client") as mock_client:
        mock_client.return_value.bucket.return_value.blob.return_value = mock_blob
        assert rt.read_opaque_bytes("gs://mybucket/path/file.pkl") == b"xyz"


def test_artifact_cache_fingerprint_local_mtime(tmp_path: Path) -> None:
    f = tmp_path / "x.bin"
    f.write_bytes(b"0")
    rt = ArtifactReadRuntime(WorkerSettings())
    fp = rt.artifact_cache_fingerprint(str(f))
    assert fp == f.stat().st_mtime


def test_read_explainability_background_parquet_local(tmp_path: Path) -> None:
    df = pd.DataFrame({"a": [1.0, 2.0]})
    path = tmp_path / "bg.parquet"
    df.to_parquet(path)
    rt = ArtifactReadRuntime(WorkerSettings())
    out = rt.read_explainability_background_parquet(str(path))
    assert list(out.columns) == ["a"]
    assert len(out) == 2
