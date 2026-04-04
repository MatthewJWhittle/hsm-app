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


def _write_test_cog_multiband(
    path,
    bounds_3857: tuple[float, float, float, float],
    fills: list[float],
) -> None:
    """Small EPSG:3857 GeoTIFF with ``len(fills)`` bands (constant per band)."""
    width, height = 8, 8
    transform = from_bounds(*bounds_3857, width, height)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=len(fills),
        dtype="float32",
        crs=CRS.from_epsg(3857),
        transform=transform,
        nodata=-9999.0,
    ) as dst:
        for i, fill in enumerate(fills):
            data = np.full((height, width), fill, dtype=np.float32)
            dst.write(data, i + 1)


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


def test_point_returns_environmental_drivers(tmp_path):
    """Model with project env COG and driver_band_indices returns raw driver values."""
    bounds = (-200_000.0, 7_000_000.0, -199_000.0, 7_000_500.0)
    cog = tmp_path / "suitability_cog.tif"
    _write_test_cog(cog, bounds, fill=0.42)
    env_cog = tmp_path / "projects" / "proj-a" / "environmental_cog.tif"
    env_cog.parent.mkdir(parents=True)
    _write_test_cog_multiband(env_cog, bounds, fills=[0.11, 0.22, 0.33])

    project_id = "proj-a"
    project_documents = [
        {
            "id": project_id,
            "name": "Test project",
            "driver_artifact_root": str(env_cog.parent),
            "driver_cog_path": "environmental_cog.tif",
        }
    ]
    documents = [
        {
            "id": "m-with-drivers",
            "species": "Test bat",
            "activity": "Roosting",
            "artifact_root": str(tmp_path),
            "suitability_cog_path": "suitability_cog.tif",
            "project_id": project_id,
            "driver_band_indices": [0, 2],
            "driver_config": {"band_labels": ["forest", "water"]},
        }
    ]
    mock_client = mock_firestore_client_for_documents(documents, project_documents=project_documents)
    with patch("backend_api.catalog_service.firestore.Client", return_value=mock_client):
        import backend_api.main as main

        importlib.reload(main)
        with TestClient(main.app) as client:
            lng, lat = _center_wgs84(bounds)
            r = client.get(
                "/models/m-with-drivers/point",
                params={"lng": lng, "lat": lat},
            )
    assert r.status_code == 200
    data = r.json()
    assert data["value"] == pytest.approx(0.42)
    assert len(data["drivers"]) == 2
    assert data["drivers"][0]["name"] == "forest"
    assert data["drivers"][0]["direction"] == "neutral"
    assert data["drivers"][0]["magnitude"] == pytest.approx(0.11)
    assert data["drivers"][1]["name"] == "water"
    assert data["drivers"][1]["magnitude"] == pytest.approx(0.33)


def test_point_drivers_empty_when_not_configured(point_client):
    """No driver_band_indices → drivers empty (existing behaviour)."""
    client, bounds = point_client
    lng, lat = _center_wgs84(bounds)
    r = client.get(
        "/models/test-bat--roosting/point",
        params={"lng": lng, "lat": lat},
    )
    assert r.status_code == 200
    assert r.json()["drivers"] == []


def test_point_env_raster_missing_503_when_drivers_configured(tmp_path):
    """driver_band_indices set but environmental file missing → 503 after suitability OK."""
    bounds = (-200_000.0, 7_000_000.0, -199_000.0, 7_000_500.0)
    cog = tmp_path / "suitability_cog.tif"
    _write_test_cog(cog, bounds, fill=0.5)
    project_id = "proj-x"
    project_documents = [
        {
            "id": project_id,
            "name": "P",
            "driver_artifact_root": str(tmp_path / "missing"),
            "driver_cog_path": "environmental_cog.tif",
        }
    ]
    documents = [
        {
            "id": "m-broken-env",
            "species": "Bat",
            "activity": "Fly",
            "artifact_root": str(tmp_path),
            "suitability_cog_path": "suitability_cog.tif",
            "project_id": project_id,
            "driver_band_indices": [0],
        }
    ]
    mock_client = mock_firestore_client_for_documents(documents, project_documents=project_documents)
    with patch("backend_api.catalog_service.firestore.Client", return_value=mock_client):
        import backend_api.main as main

        importlib.reload(main)
        with TestClient(main.app) as client:
            lng, lat = _center_wgs84(bounds)
            r = client.get(
                "/models/m-broken-env/point",
                params={"lng": lng, "lat": lat},
            )
    assert r.status_code == 503
    assert "environmental" in r.json()["detail"].lower()


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
