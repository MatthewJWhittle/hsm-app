"""Tests for stratified block sampling into explainability background Parquet."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_bounds

from backend_api.env_background_sample import sample_background_parquet_to_tempfile
from backend_api.schemas_project import EnvironmentalBandDefinition


def _write_multiband_tif(path: Path, h: int, w: int, n_bands: int) -> None:
    transform = from_bounds(-180, -90, 180, 90, w, h)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=h,
        width=w,
        count=n_bands,
        dtype="float32",
        crs=CRS.from_epsg(4326),
        transform=transform,
        nodata=-9999.0,
    ) as dst:
        for b in range(n_bands):
            plane = np.full((h, w), float(b + 1), dtype=np.float32)
            dst.write(plane, b + 1)


def _defs(n_bands: int) -> list[EnvironmentalBandDefinition]:
    return [
        EnvironmentalBandDefinition(index=i, name=f"b{i}", label=None)
        for i in range(n_bands)
    ]


def test_sample_background_parquet_stratified_block_pass(tmp_path: Path) -> None:
    tif = tmp_path / "env.tif"
    _write_multiband_tif(tif, 32, 32, 2)
    out = sample_background_parquet_to_tempfile(
        str(tif), _defs(2), n_samples=48, seed=42
    )
    try:
        df = pd.read_parquet(out)
        assert df.shape == (48, 2)
        assert list(df.columns) == ["b0", "b1"]
        assert np.allclose(df["b0"].to_numpy(), 1.0)
        assert np.allclose(df["b1"].to_numpy(), 2.0)
    finally:
        out.unlink(missing_ok=True)


def test_sample_background_parquet_insufficient_valid_pixels(tmp_path: Path) -> None:
    tif = tmp_path / "nonfinite.tif"
    h, w = 4, 4
    transform = from_bounds(-180, -90, 180, 90, w, h)
    with rasterio.open(
        tif,
        "w",
        driver="GTiff",
        height=h,
        width=w,
        count=1,
        dtype="float32",
        crs=CRS.from_epsg(4326),
        transform=transform,
    ) as dst:
        # Non-finite values are skipped (metadata nodata alone does not mask ``read()``).
        dst.write(np.full((h, w), np.nan, dtype=np.float32), 1)

    with pytest.raises(ValueError, match="could only sample"):
        sample_background_parquet_to_tempfile(str(tif), _defs(1), n_samples=8, seed=0)
