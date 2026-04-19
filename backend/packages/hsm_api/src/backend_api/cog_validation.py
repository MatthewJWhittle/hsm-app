"""Validate suitability rasters before catalog commit (docs/data-models.md)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import rasterio
from rasterio.crs import CRS

from backend_api.point_sampling import EXPECTED_SUITABILITY_CRS

EXPECTED_EPSG = 3857


class CogValidationError(Exception):
    """Invalid file for suitability COG registration."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "COG_VALIDATION",
        context: dict | None = None,
    ) -> None:
        self.message = message
        self.code = code
        self.context = context or {}
        super().__init__(message)


def validate_suitability_cog_bytes(content: bytes) -> None:
    """Validate COG bytes: readable GeoTIFF, tiled, EPSG:3857."""
    if len(content) < 1024:
        raise CogValidationError(
            "file too small to be a valid GeoTIFF",
            code="COG_TOO_SMALL",
        )
    with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as tmp:
        tmp.write(content)
        path = Path(tmp.name)
    try:
        validate_suitability_cog_path(path)
    finally:
        path.unlink(missing_ok=True)


def validate_suitability_cog_path(path: Path) -> None:
    """Validate on-disk COG: tiled, EPSG:3857."""
    validate_suitability_cog_uri(str(path))


def validate_suitability_cog_uri(uri: str) -> None:
    """Validate COG from a rasterio-readable URI/path: tiled, EPSG:3857."""
    try:
        with rasterio.open(uri) as src:
            if src.crs is None:
                raise CogValidationError(
                    "raster has no CRS; expected EPSG:3857",
                    code="COG_NO_CRS",
                    context={"expected_epsg": EXPECTED_EPSG},
                )
            if src.crs != CRS.from_epsg(EXPECTED_EPSG):
                got = src.crs.to_string() if src.crs else "none"
                raise CogValidationError(
                    f"CRS must be EPSG:3857; got {got}",
                    code="COG_CRS_MISMATCH",
                    context={"expected_epsg": EXPECTED_EPSG, "got_crs": got},
                )
            if not src.is_tiled:
                raise CogValidationError(
                    "raster must be tiled (Cloud Optimized GeoTIFF); use COG creation tools",
                    code="COG_NOT_TILED",
                )
    except rasterio.errors.RasterioIOError as e:
        raise CogValidationError(
            f"cannot read raster: {e}",
            code="COG_READ_ERROR",
            context={"rasterio": str(e)},
        ) from e
