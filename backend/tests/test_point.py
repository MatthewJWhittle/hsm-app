"""Tests for GET /models/{id}/point (synthetic COG in tmp_path)."""

import importlib
from unittest.mock import patch

import numpy as np
import pytest
import rasterio
from fastapi.testclient import TestClient
from rasterio.crs import CRS
from rasterio.transform import from_bounds
from rasterio.warp import transform as transform_coords

from tests.helpers import mock_firestore_client_for_documents


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


def _write_test_cog_all_nodata(
    path,
    bounds_3857: tuple[float, float, float, float],
    nodata: float = -9999.0,
) -> None:
    """EPSG:3857 raster where every pixel equals nodata."""
    width, height = 8, 8
    transform = from_bounds(*bounds_3857, width, height)
    data = np.full((height, width), nodata, dtype=np.float32)
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
        nodata=nodata,
    ) as dst:
        dst.write(data, 1)


def _write_test_cog_epsg4326(
    path,
    bounds_wgs84: tuple[float, float, float, float],
    fill: float,
) -> None:
    """Small WGS84 GeoTIFF (wrong CRS for point inspection — expect EPSG:3857)."""
    width, height = 8, 8
    transform = from_bounds(*bounds_wgs84, width, height)
    data = np.full((height, width), fill, dtype=np.float32)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=1,
        dtype=data.dtype,
        crs=CRS.from_epsg(4326),
        transform=transform,
        nodata=-9999.0,
    ) as dst:
        dst.write(data, 1)


@pytest.fixture
def point_client(tmp_path):
    """Catalog with one model pointing at a synthetic COG."""
    cog = tmp_path / "suitability_cog.tif"
    bounds = (-200_000.0, 7_000_000.0, -199_000.0, 7_000_500.0)
    _write_test_cog(cog, bounds, fill=0.42)

    documents = [
        {
            "id": "test-bat--roosting",
            "species": "Test bat",
            "activity": "Roosting",
            "artifact_root": str(tmp_path),
            "suitability_cog_path": "suitability_cog.tif",
        }
    ]
    mock_client = mock_firestore_client_for_documents(documents)
    with patch("backend_api.catalog_service.firestore.Client", return_value=mock_client):
        import backend_api.main as main

        importlib.reload(main)
        with TestClient(main.app) as client:
            yield client, bounds


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


def test_point_missing_cog_503(tmp_path):
    """Catalog references a COG path that does not exist on disk."""
    documents = [
        {
            "id": "test-bat--roosting",
            "species": "Test bat",
            "activity": "Roosting",
            "artifact_root": str(tmp_path),
            "suitability_cog_path": "this_file_is_missing.tif",
        }
    ]
    mock_client = mock_firestore_client_for_documents(documents)
    with patch("backend_api.catalog_service.firestore.Client", return_value=mock_client):
        import backend_api.main as main

        importlib.reload(main)
        with TestClient(main.app) as client:
            r = client.get(
                "/models/test-bat--roosting/point",
                params={"lng": -2.5, "lat": 53.0},
            )
    assert r.status_code == 503
    assert r.json()["detail"] == "suitability raster not found on server"


def test_point_nodata_pixel_422(tmp_path):
    """Inside raster extent but pixel is nodata."""
    cog = tmp_path / "suitability_cog.tif"
    bounds = (-200_000.0, 7_000_000.0, -199_000.0, 7_000_500.0)
    _write_test_cog_all_nodata(cog, bounds)

    documents = [
        {
            "id": "test-bat--roosting",
            "species": "Test bat",
            "activity": "Roosting",
            "artifact_root": str(tmp_path),
            "suitability_cog_path": "suitability_cog.tif",
        }
    ]
    mock_client = mock_firestore_client_for_documents(documents)
    with patch("backend_api.catalog_service.firestore.Client", return_value=mock_client):
        import backend_api.main as main

        importlib.reload(main)
        with TestClient(main.app) as client:
            lng, lat = _center_wgs84(bounds)
            r = client.get(
                "/models/test-bat--roosting/point",
                params={"lng": lng, "lat": lat},
            )
    assert r.status_code == 422
    assert "nodata" in r.json()["detail"].lower()


def test_point_wrong_crs_422(tmp_path):
    """Raster must be EPSG:3857; WGS84 file is rejected."""
    cog = tmp_path / "suitability_cog.tif"
    bounds_wgs84 = (-4.0, 50.0, -3.0, 51.0)
    _write_test_cog_epsg4326(cog, bounds_wgs84, fill=0.5)

    documents = [
        {
            "id": "test-bat--roosting",
            "species": "Test bat",
            "activity": "Roosting",
            "artifact_root": str(tmp_path),
            "suitability_cog_path": "suitability_cog.tif",
        }
    ]
    mock_client = mock_firestore_client_for_documents(documents)
    with patch("backend_api.catalog_service.firestore.Client", return_value=mock_client):
        import backend_api.main as main

        importlib.reload(main)
        with TestClient(main.app) as client:
            minx, miny, maxx, maxy = bounds_wgs84
            lng = (minx + maxx) / 2.0
            lat = (miny + maxy) / 2.0
            r = client.get(
                "/models/test-bat--roosting/point",
                params={"lng": lng, "lat": lat},
            )
    assert r.status_code == 422
    detail = r.json()["detail"].lower()
    assert "3857" in detail or "crs" in detail
