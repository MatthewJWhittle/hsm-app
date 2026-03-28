"""Sample suitability COGs at WGS84 points (docs/data-models.md)."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.transform import rowcol
from rasterio.warp import transform as transform_coords
from rasterio.windows import Window

from backend_api.schemas import Model, PointInspection

EXPECTED_SUITABILITY_CRS = CRS.from_epsg(3857)


class PointSamplingError(Exception):
    """Expected failure (e.g. out of bounds, nodata); maps to HTTP 422."""

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


def resolve_cog_path(model: Model) -> str:
    """Absolute filesystem path to the suitability COG (matches frontend cogPath.ts)."""
    p = model.suitability_cog_path
    if p.startswith("/"):
        return p
    root = model.artifact_root.rstrip("/")
    return f"{root}/{p}"


def sample_suitability(cog_path: str, lng: float, lat: float) -> float:
    """
    Read band 1 at (lng, lat) in WGS84.

    Raises:
        PointSamplingError: out of bounds, nodata, wrong CRS, unreadable pixel.
        FileNotFoundError: path does not exist.
    """
    path = Path(cog_path)
    if not path.is_file():
        raise FileNotFoundError(cog_path)

    with rasterio.open(path) as src:
        if not src.crs:
            raise PointSamplingError("raster has no CRS; expected EPSG:3857")
        if src.crs != EXPECTED_SUITABILITY_CRS:
            raise PointSamplingError(
                f"raster CRS must be EPSG:3857 for point inspection; got {src.crs}"
            )

        xs, ys = transform_coords("EPSG:4326", src.crs, [lng], [lat])
        x, y = float(xs[0]), float(ys[0])
        if not all(math.isfinite(v) for v in (x, y)):
            raise PointSamplingError("could not project coordinates to raster CRS")

        row_i, col_i = rowcol(src.transform, x, y)
        if row_i < 0 or row_i >= src.height or col_i < 0 or col_i >= src.width:
            raise PointSamplingError("point is outside the raster extent")

        window = Window(col_i, row_i, 1, 1)
        data = src.read(1, window=window, masked=True)
        if np.ma.getmaskarray(data).any():
            raise PointSamplingError("no suitability value at this location (nodata)")
        raw = float(data[0, 0])
        if not math.isfinite(raw):
            raise PointSamplingError("no suitability value at this location (nodata)")
        return raw


def inspect_point(model: Model, lng: float, lat: float) -> PointInspection:
    """Sample suitability at WGS84; driver bands wired in a later iteration."""
    path = resolve_cog_path(model)
    value = sample_suitability(path, lng, lat)
    return PointInspection(
        value=value,
        unit="suitability (0–1)",
        drivers=[],
    )
