"""Sample suitability COGs at WGS84 points (docs/data-models.md)."""

from __future__ import annotations

import math
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.transform import rowcol
from rasterio.warp import transform as transform_coords
from rasterio.windows import Window

from backend_api.schemas import DriverVariable, Model, PointInspection, RawEnvironmentalValue

if TYPE_CHECKING:
    from backend_api.catalog_service import CatalogService

EXPECTED_SUITABILITY_CRS = CRS.from_epsg(3857)


class PointSamplingError(Exception):
    """Expected failure (e.g. out of bounds, nodata); maps to HTTP 422."""

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class RasterNotFoundError(Exception):
    """Expected missing raster file on disk; maps to HTTP 503."""

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


def resolve_environmental_cog_path_for_model(
    model: Model, catalog: "CatalogService"
) -> str | None:
    """
    Absolute path to the multi-band environmental COG for driver sampling.

    Prefer the catalog project's shared stack; else ``driver_config.driver_cog_path``
    relative to ``artifact_root`` (see docs/data-models.md).
    """
    if model.project_id:
        proj = catalog.get_project(model.project_id)
        if proj and proj.driver_artifact_root and proj.driver_cog_path:
            root = proj.driver_artifact_root.rstrip("/")
            rel = proj.driver_cog_path.strip()
            if rel.startswith("/"):
                return rel
            return f"{root}/{rel}"

    dc = model.driver_config or {}
    rel = dc.get("driver_cog_path")
    if isinstance(rel, str) and rel.strip():
        rel = rel.strip()
        if rel.startswith("/"):
            return rel
        root = model.artifact_root.rstrip("/")
        return f"{root}/{rel}"
    return None


def validate_driver_band_indices_for_model(model: Model, catalog: "CatalogService") -> None:
    """
    If the model lists driver bands and an environmental COG path resolves and exists,
    ensure every index is in range for that file (0-based band index < band count).

    Raises:
        ValueError: indices out of range (use for HTTP 422).
    """
    indices = model.driver_band_indices
    if not indices:
        return
    path = resolve_environmental_cog_path_for_model(model, catalog)
    if not path:
        return
    p = Path(path)
    if not p.is_file():
        return
    mx = max(indices)
    if min(indices) < 0:
        raise ValueError("driver_band_indices must be non-negative")
    with rasterio.open(p) as src:
        if mx >= src.count:
            raise ValueError(
                f"driver_band_indices: maximum index {mx} is out of range for "
                f"environmental raster with {src.count} band(s) (0-based indices)"
            )


def sample_suitability(cog_path: str, lng: float, lat: float) -> float:
    """
    Read band 1 at (lng, lat) in WGS84.

    Raises:
        PointSamplingError: out of bounds, nodata, wrong CRS, unreadable pixel.
        RasterNotFoundError: path does not exist.
    """
    path = Path(cog_path)
    if not path.is_file():
        raise RasterNotFoundError("suitability raster not found on server")

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
        row_i = int(row_i)
        col_i = int(col_i)
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


def sample_environmental_bands_at_point(
    cog_path: str, lng: float, lat: float, band_indices_0based: list[int]
) -> list[float]:
    """
    Read each requested band at (lng, lat) in WGS84.

    ``band_indices_0based`` are **0-based** indices into the raster band list; rasterio
    uses 1-based band numbers, so band ``i`` is read as ``src.read(i + 1, ...)``.

    Raises:
        PointSamplingError: CRS, extent, nodata, or index out of range.
        RasterNotFoundError: file missing.
    """
    path = Path(cog_path)
    if not path.is_file():
        raise RasterNotFoundError("environmental raster not found on server")

    out: list[float] = []
    with rasterio.open(path) as src:
        if not src.crs:
            raise PointSamplingError(
                "environmental raster has no CRS; expected EPSG:3857 for point inspection"
            )
        if src.crs != EXPECTED_SUITABILITY_CRS:
            raise PointSamplingError(
                f"environmental raster CRS must be EPSG:3857 for point inspection; got {src.crs}"
            )

        xs, ys = transform_coords("EPSG:4326", src.crs, [lng], [lat])
        x, y = float(xs[0]), float(ys[0])
        if not all(math.isfinite(v) for v in (x, y)):
            raise PointSamplingError("could not project coordinates to raster CRS")

        row_i, col_i = rowcol(src.transform, x, y)
        row_i = int(row_i)
        col_i = int(col_i)
        if row_i < 0 or row_i >= src.height or col_i < 0 or col_i >= src.width:
            raise PointSamplingError("point is outside the environmental raster extent")

        window = Window(col_i, row_i, 1, 1)

        for bi in band_indices_0based:
            if bi < 0 or bi >= src.count:
                raise PointSamplingError(
                    f"environmental raster has no band index {bi} (0-based); "
                    f"file has {src.count} band(s)"
                )
            ri = bi + 1
            data = src.read(ri, window=window, masked=True)
            if np.ma.getmaskarray(data).any():
                raise PointSamplingError(
                    "no environmental value at this location (nodata) for one or more driver bands"
                )
            raw = float(data[0, 0])
            if not math.isfinite(raw):
                raise PointSamplingError(
                    "no environmental value at this location (nodata) for one or more driver bands"
                )
            out.append(raw)
    return out


def build_raw_environmental_values(
    model: Model, values: list[float]
) -> list[RawEnvironmentalValue]:
    """Labels for sampled bands; prefers ``band_labels`` / ``band_names``, else ``feature_names``."""
    indices = model.driver_band_indices or []
    dc = model.driver_config or {}
    names = dc.get("band_labels") or dc.get("band_names")
    if not (isinstance(names, list) and len(names) == len(values)):
        fn = dc.get("feature_names")
        if isinstance(fn, list) and len(fn) == len(values):
            names = [str(x) for x in fn]
        else:
            names = [f"band_{indices[i]}" for i in range(len(values))]
    else:
        names = [str(x) for x in names]
    units = dc.get("band_units")
    descs = dc.get("band_descriptions")
    out: list[RawEnvironmentalValue] = []
    for i, (name, val) in enumerate(zip(names, values)):
        unit = None
        if isinstance(units, list) and i < len(units):
            u = units[i]
            if isinstance(u, str) and u.strip():
                unit = u.strip()
        desc = None
        if isinstance(descs, list) and i < len(descs):
            di = descs[i]
            if isinstance(di, str) and di.strip():
                desc = di.strip()
        out.append(RawEnvironmentalValue(name=name, value=val, unit=unit, description=desc))
    return out


def inspect_point(
    model: Model,
    lng: float,
    lat: float,
    *,
    catalog: "CatalogService | None" = None,
) -> PointInspection:
    """Sample suitability; optional raw env values and SHAP influence when configured."""
    from backend_api.point_explainability import (
        compute_shap_driver_variables,
        explainability_configured,
    )

    path = resolve_cog_path(model)
    value = sample_suitability(path, lng, lat)

    drivers_out: list[DriverVariable] | None = None  # None → serialize as empty list
    raw_out: list[RawEnvironmentalValue] | None = None

    indices = model.driver_band_indices
    if catalog is not None and indices:
        env_path = resolve_environmental_cog_path_for_model(model, catalog)
        if env_path is not None:
            band_values = sample_environmental_bands_at_point(
                env_path, lng, lat, indices
            )
            raw_out = build_raw_environmental_values(model, band_values)
            if explainability_configured(model):
                dc = model.driver_config or {}
                fnames = dc.get("feature_names")
                if not (
                    isinstance(fnames, list)
                    and len(fnames) == len(band_values)
                    and len(fnames) > 0
                ):
                    raise PointSamplingError(
                        "explainability requires feature_names with the same length "
                        "and order as driver_band_indices"
                    )
                import pandas as pd

                feature_df = pd.DataFrame(
                    [band_values], columns=[str(x) for x in fnames]
                )
                drivers_out = compute_shap_driver_variables(model, feature_df)

    return PointInspection(
        value=value,
        unit="suitability (0–1)",
        drivers=drivers_out or [],
        raw_environmental_values=raw_out,
    )
