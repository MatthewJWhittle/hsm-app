"""Infer environmental band definitions from GeoTIFF metadata (project uploads)."""

from io import BytesIO

import numpy as np
import pytest
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_bounds

from backend_api.env_cog_bands import (
    band_definitions_for_upload_bytes,
    infer_band_definitions_from_bytes,
)


def _minimal_geotiff_bytes(
    *,
    band_descriptions: tuple[str | None, ...],
) -> bytes:
    """Small EPSG:3857 multi-band GeoTIFF; band descriptions set when provided."""
    h, w = 4, 4
    data = np.zeros((len(band_descriptions), h, w), dtype=np.float32)
    transform = from_bounds(0.0, 0.0, 100.0, 100.0, w, h)
    buf = BytesIO()
    profile = {
        "driver": "GTiff",
        "width": w,
        "height": h,
        "count": len(band_descriptions),
        "dtype": "float32",
        "crs": CRS.from_epsg(3857),
        "transform": transform,
    }
    with rasterio.open(buf, "w", **profile) as dst:
        for i, desc in enumerate(band_descriptions):
            dst.write(data[i], i + 1)
            if desc is not None:
                dst.set_band_description(i + 1, desc)
    buf.seek(0)
    return buf.getvalue()


def test_infer_slugifies_and_warns_on_missing_description() -> None:
    raw = _minimal_geotiff_bytes(band_descriptions=(None, "My Elevation!"))
    defs, notes = infer_band_definitions_from_bytes(raw)
    assert [d.name for d in defs] == ["band_0", "my_elevation"]
    assert any("no GDAL description" in n for n in notes)
    assert any("band_0" in n for n in notes)


def test_infer_uniquifies_duplicate_normalised_names() -> None:
    raw = _minimal_geotiff_bytes(band_descriptions=("Same Name", "Same Name"))
    defs, notes = infer_band_definitions_from_bytes(raw)
    assert [d.name for d in defs] == ["same_name", "same_name_2"]
    assert any("collided" in n.lower() for n in notes)


def test_band_definitions_for_upload_infer_false_requires_json() -> None:
    raw = _minimal_geotiff_bytes(band_descriptions=("a",))
    with pytest.raises(ValueError, match="infer_band_definitions is false"):
        band_definitions_for_upload_bytes(raw, None, infer_band_definitions=False)


def test_band_definitions_for_upload_explicit_json_no_notes() -> None:
    raw = _minimal_geotiff_bytes(band_descriptions=("ignored", "ignored"))
    json_form = (
        '[{"index":0,"name":"foo","label":null},{"index":1,"name":"bar","label":null}]'
    )
    defs, notes = band_definitions_for_upload_bytes(raw, json_form)
    assert [d.name for d in defs] == ["foo", "bar"]
    assert notes == []
