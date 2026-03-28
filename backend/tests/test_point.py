"""Tests for GET /models/{id}/point (synthetic COG in tmp_path)."""

import importlib
import json

import numpy as np
import pytest
import rasterio
from fastapi.testclient import TestClient
from rasterio.crs import CRS
from rasterio.transform import from_bounds
from rasterio.warp import transform as transform_coords


def _write_test_cog(path, bounds_3857: tuple[float, float, float, float], fill: float) -> None:
    """Small EPSG:3857 GeoTIFF with constant value."""
    width, height = 8, 8
    transform = from_bounds(*bounds_3857, width, height)
    data = np.full((height, width), fill, dtype=np.float32)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=1,
        dtype=data.dtype,
        crs=CRS.from_epsg(3857),
        transform=transform,
        nodata=-9999.0,
    ) as dst:
        dst.write(data, 1)


@pytest.fixture
def point_client(tmp_path, monkeypatch):
    """Catalog with one model pointing at a synthetic COG."""
    cog = tmp_path / "suitability_cog.tif"
    # ~UK area in Web Mercator (meters)
    bounds = (-200_000.0, 7_000_000.0, -199_000.0, 7_000_500.0)
    _write_test_cog(cog, bounds, fill=0.42)

    catalog = tmp_path / "firestore_models.json"
    catalog.write_text(
        json.dumps(
            {
                "collection_id": "models",
                "documents": [
                    {
                        "id": "test-bat--roosting",
                        "species": "Test bat",
                        "activity": "Roosting",
                        "artifact_root": str(tmp_path),
                        "suitability_cog_path": "suitability_cog.tif",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("CATALOG_PATH", str(catalog))
    import backend_api.main as main

    importlib.reload(main)
    with TestClient(main.app) as c:
        yield c, bounds


def _center_wgs84(bounds_3857: tuple[float, float, float, float]) -> tuple[float, float]:
    minx, miny, maxx, maxy = bounds_3857
    cx = (minx + maxx) / 2.0
    cy = (miny + maxy) / 2.0
    lngs, lats = transform_coords(CRS.from_epsg(3857), "EPSG:4326", [cx], [cy])
    return float(lngs[0]), float(lats[0])


def test_point_returns_value(point_client):
    client, bounds = point_client
    lng, lat = _center_wgs84(bounds)
    r = client.get(
        "/models/test-bat--roosting/point",
        params={"lng": lng, "lat": lat},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["value"] == pytest.approx(0.42)
    assert data["unit"] == "suitability (0–1)"
    assert data["drivers"] == []


def test_point_outside_raster_422(point_client):
    client, _bounds = point_client
    r = client.get(
        "/models/test-bat--roosting/point",
        params={"lng": 0.0, "lat": 0.0},
    )
    assert r.status_code == 422
    assert "outside" in r.json()["detail"].lower() or "extent" in r.json()["detail"].lower()


def test_point_unknown_model_404(point_client):
    client, bounds = point_client
    lng, lat = _center_wgs84(bounds)
    r = client.get(
        "/models/does-not-exist/point",
        params={"lng": lng, "lat": lat},
    )
    assert r.status_code == 404


def test_point_lat_out_of_range_422(point_client):
    client, bounds = point_client
    lng, lat = _center_wgs84(bounds)
    r = client.get(
        "/models/test-bat--roosting/point",
        params={"lng": lng, "lat": 100.0},
    )
    assert r.status_code == 422
