"""Unit tests for hsm_core ArtifactReadRuntime seam (raster URI, opaque bytes, Parquet)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from hsm_core.artifact_read_runtime import ArtifactReadRuntime
from hsm_core.settings import WorkerSettings


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


def test_read_explainability_background_parquet_local(tmp_path: Path) -> None:
    df = pd.DataFrame({"a": [1.0, 2.0]})
    path = tmp_path / "bg.parquet"
    df.to_parquet(path)
    rt = ArtifactReadRuntime(WorkerSettings())
    out = rt.read_explainability_background_parquet(str(path))
    assert list(out.columns) == ["a"]
    assert len(out) == 2
