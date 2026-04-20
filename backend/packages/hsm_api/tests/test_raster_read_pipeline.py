"""
Integration and contract tests for the ArtifactReadRuntime → rasterio pipeline.

These tests use **real rasterio** on temp files where possible, and reserve mocks for
signing / ``gs://`` so CI does not need GCS or GDAL ``gs://`` credentials.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_bounds

from backend_api.cog_validation import (
    CogValidationError,
    validate_suitability_cog_bytes,
    validate_suitability_cog_uri,
)
from backend_api.env_cog_bands import band_definitions_for_upload_path, band_definitions_for_upload_uri
from backend_api.point_sampling import sample_environmental_bands_at_point, sample_suitability
from hsm_core.artifact_read_runtime import ArtifactReadRuntime
from hsm_core.settings import WorkerSettings

from tests.raster_test_utils import (
    write_multiband_env_cog,
    write_tiled_epsg3857_cog,
    write_untiled_epsg3857_gtiff,
)
from tests.test_point import _center_wgs84, _write_test_cog


@pytest.fixture
def rt() -> ArtifactReadRuntime:
    return ArtifactReadRuntime(WorkerSettings())


def test_validate_suitability_cog_bytes_roundtrip(tmp_path: Path, rt: ArtifactReadRuntime) -> None:
    p = tmp_path / "bytes.tif"
    write_tiled_epsg3857_cog(p)
    raw = p.read_bytes()
    validate_suitability_cog_bytes(raw, rt)


def test_validate_suitability_cog_uri_accepts_tiled_epsg3857(tmp_path: Path, rt: ArtifactReadRuntime) -> None:
    p = tmp_path / "ok.tif"
    write_tiled_epsg3857_cog(p)
    validate_suitability_cog_uri(rt, str(p))


def test_validate_suitability_cog_uri_rejects_untiled(tmp_path: Path, rt: ArtifactReadRuntime) -> None:
    p = tmp_path / "strip.tif"
    write_untiled_epsg3857_gtiff(p)
    with pytest.raises(CogValidationError) as exc:
        validate_suitability_cog_uri(rt, str(p))
    assert exc.value.code == "COG_NOT_TILED"


def test_validate_suitability_cog_uri_rejects_wrong_crs(tmp_path: Path, rt: ArtifactReadRuntime) -> None:
    p = tmp_path / "wgs84.tif"
    h, w = 32, 32
    transform = from_bounds(-1, -1, 1, 1, w, h)
    with rasterio.open(
        p,
        "w",
        driver="GTiff",
        height=h,
        width=w,
        count=1,
        dtype="float32",
        crs=CRS.from_epsg(4326),
        transform=transform,
        tiled=True,
        blockxsize=16,
        blockysize=16,
    ) as dst:
        dst.write(np.zeros((h, w), dtype=np.float32), 1)
    with pytest.raises(CogValidationError) as exc:
        validate_suitability_cog_uri(rt, str(p))
    assert exc.value.code == "COG_CRS_MISMATCH"


def test_validate_suitability_cog_uri_gs_ref_routes_through_rasterio_open_uri(
    tmp_path: Path, rt: ArtifactReadRuntime
) -> None:
    """``validate_suitability_cog_uri`` must ask the runtime to rewrite ``gs://`` before open."""
    p = tmp_path / "signed.tif"
    write_tiled_epsg3857_cog(p)
    gs = "gs://fake-bucket/path/cog.tif"
    seen: list[str] = []

    def fake_open_uri(ref: str) -> str:
        seen.append(ref)
        return str(p)

    with patch.object(rt, "rasterio_open_uri", side_effect=fake_open_uri):
        validate_suitability_cog_uri(rt, gs)
    assert seen == [gs]


def test_validate_suitability_cog_uri_gs_ref_never_passes_raw_gs_to_rasterio_open(
    tmp_path: Path, rt: ArtifactReadRuntime
) -> None:
    p = tmp_path / "via_signed.tif"
    write_tiled_epsg3857_cog(p)

    real_open = rasterio.open

    def guard(*args: object, **kwargs: object):
        first = args[0] if args else kwargs.get("path") or kwargs.get("datasetname")
        if isinstance(first, str) and first.startswith("gs://"):
            raise AssertionError("rasterio.open received raw gs:// — must use /vsicurl/ or local path")
        return real_open(*args, **kwargs)

    with patch.object(rt, "rasterio_open_uri", return_value=str(p)):
        with patch("rasterio.open", side_effect=guard):
            validate_suitability_cog_uri(rt, "gs://b/o.tif")


def test_raster_band_count_matches_rasterio_open(tmp_path: Path, rt: ArtifactReadRuntime) -> None:
    p = tmp_path / "bands.tif"
    write_multiband_env_cog(p, n_bands=4, descriptions=("a", "b", None, "d"))
    n = rt.raster_band_count(str(p))
    with rasterio.open(p) as src:
        assert n == int(src.count)


def test_band_definitions_for_upload_uri_gs_ref_uses_runtime_open_uri(
    tmp_path: Path, rt: ArtifactReadRuntime
) -> None:
    p = tmp_path / "remote.tif"
    write_multiband_env_cog(p, n_bands=1)
    seen: list[str] = []

    def fake_open_uri(ref: str) -> str:
        seen.append(ref)
        return str(p)

    with patch.object(rt, "rasterio_open_uri", side_effect=fake_open_uri):
        band_definitions_for_upload_uri(rt, "gs://b/k/x.tif", None, infer_band_definitions=True)
    assert seen == ["gs://b/k/x.tif"]


def test_band_definitions_for_upload_uri_infer_local(tmp_path: Path, rt: ArtifactReadRuntime) -> None:
    p = tmp_path / "env.tif"
    write_multiband_env_cog(
        p, n_bands=2, descriptions=("Elevation band", "Land cover")
    )
    defs, notes = band_definitions_for_upload_uri(
        rt, str(p), None, infer_band_definitions=True
    )
    assert len(defs) == 2
    assert defs[0].index == 0
    assert defs[1].index == 1
    assert all(d.name for d in defs)
    assert isinstance(notes, list)


def test_band_definitions_for_upload_path_explicit_json(tmp_path: Path, rt: ArtifactReadRuntime) -> None:
    p = tmp_path / "e.tif"
    write_multiband_env_cog(p, n_bands=2)
    import json

    raw = json.dumps(
        [
            {"index": 0, "name": "x0", "label": None, "description": None},
            {"index": 1, "name": "x1", "label": None, "description": None},
        ]
    )
    defs, notes = band_definitions_for_upload_path(rt, str(p), raw, infer_band_definitions=False)
    assert [d.name for d in defs] == ["x0", "x1"]
    assert notes == []


def test_sample_suitability_reads_constant_value(tmp_path: Path, rt: ArtifactReadRuntime) -> None:
    p = tmp_path / "suit.tif"
    bounds = (-200_000.0, 7_000_000.0, -199_000.0, 7_000_500.0)
    _write_test_cog(p, bounds, fill=0.77)
    lng, lat = _center_wgs84(bounds)
    v = sample_suitability(rt, str(p), lng, lat)
    assert v == pytest.approx(0.77)


def test_sample_environmental_bands_multiband(tmp_path: Path, rt: ArtifactReadRuntime) -> None:
    p = tmp_path / "env.tif"
    bounds = (-200_000.0, 7_000_000.0, -199_000.0, 7_000_500.0)
    width, height = 8, 8
    transform = from_bounds(*bounds, width, height)
    with rasterio.open(
        p,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=3,
        dtype="float32",
        crs=CRS.from_epsg(3857),
        transform=transform,
        nodata=-9999.0,
    ) as dst:
        for b in range(3):
            dst.write(np.full((height, width), float(b + 1), dtype=np.float32), b + 1)
    lng, lat = _center_wgs84(bounds)
    vals = sample_environmental_bands_at_point(rt, str(p), lng, lat, [0, 2])
    assert vals == [pytest.approx(1.0), pytest.approx(3.0)]


def test_rasterio_open_uri_idempotent_for_vsicurl(rt: ArtifactReadRuntime) -> None:
    vsicurl = "/vsicurl/https://example.com/x.tif"
    assert rt.rasterio_open_uri(vsicurl) == vsicurl
