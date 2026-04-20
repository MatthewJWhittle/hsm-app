"""Shared GeoTIFF builders for raster / ArtifactReadRuntime pipeline tests."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_bounds


def write_tiled_epsg3857_cog(path: Path | str, *, fill: float = 0.42) -> tuple[float, float, float, float]:
    """
    Small **tiled** EPSG:3857 GeoTIFF suitable for :func:`validate_suitability_cog_uri`.

    Uses internal blocks smaller than the raster extent so COG validation accepts the
    file as tiled (strip GeoTIFFs use full-width row blocks and fail validation).

    Returns bounds (minx, miny, maxx, maxy) in EPSG:3857 used for the transform.
    """
    path = Path(path)
    # Large enough that on-disk GeoTIFF exceeds validate_suitability_cog_bytes 1 KiB floor.
    width, height = 512, 512
    bounds_3857 = (-1000.0, -1000.0, 1000.0, 1000.0)
    transform = from_bounds(*bounds_3857, width, height)
    data = np.full((height, width), fill, dtype=np.float32)
    profile = {
        "driver": "GTiff",
        "width": width,
        "height": height,
        "count": 1,
        "dtype": "float32",
        "crs": CRS.from_epsg(3857),
        "transform": transform,
        "nodata": -9999.0,
        "tiled": True,
        "blockxsize": 128,
        "blockysize": 128,
        "compress": "deflate",
    }
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(data, 1)
    return bounds_3857


def write_untiled_epsg3857_gtiff(path: Path | str, *, fill: float = 0.1) -> None:
    """EPSG:3857 raster that is **not** tiled (expect COG validation ``COG_NOT_TILED``)."""
    path = Path(path)
    width, height = 32, 32
    transform = from_bounds(-500.0, -500.0, 500.0, 500.0, width, height)
    data = np.full((height, width), fill, dtype=np.float32)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=1,
        dtype="float32",
        crs=CRS.from_epsg(3857),
        transform=transform,
        nodata=-9999.0,
    ) as dst:
        dst.write(data, 1)


def write_multiband_env_cog(
    path: Path | str,
    *,
    n_bands: int,
    crs_epsg: int = 4326,
    descriptions: tuple[str | None, ...] | None = None,
) -> None:
    """Multi-band GeoTIFF (e.g. environmental stack) for band-definition inference tests."""
    path = Path(path)
    h, w = 16, 16
    transform = from_bounds(-180, -90, 180, 90, w, h)
    desc = descriptions or (None,) * n_bands
    if len(desc) != n_bands:
        raise ValueError("descriptions length must match n_bands")
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=h,
        width=w,
        count=n_bands,
        dtype="float32",
        crs=CRS.from_epsg(crs_epsg),
        transform=transform,
        nodata=-9999.0,
    ) as dst:
        for b in range(n_bands):
            plane = np.full((h, w), float(b + 1), dtype=np.float32)
            dst.write(plane, b + 1)
            if desc[b] is not None:
                dst.set_band_description(b + 1, desc[b])

