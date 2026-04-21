"""Validate suitability rasters before catalog commit (docs/data-models.md)."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from hsm_core.artifact_read_runtime import ArtifactReadRuntime

if TYPE_CHECKING:
    from rasterio.io import DatasetReader

EXPECTED_EPSG = 3857


def _raster_uses_internal_tiling(src: "DatasetReader") -> bool:
    """
    True when the GeoTIFF uses a tiled storage layout (not row/strip).

    Replaces rasterio's deprecated ``DatasetReader.is_tiled`` (rasterio 1.4+): strip
    layouts use full-width row blocks; tiled COGs use blocks that do not span the full
    width; a single block covering the whole raster is treated as non-tiled layout.
    """
    blocks = src.block_shapes
    if not blocks:
        return False
    bh, bw = blocks[0]
    height, width = src.shape
    if bw == width and bh < height:
        return False
    if bh >= height and bw >= width:
        return False
    return True


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


def _validate_suitability_cog_rasterio_uri(uri: str) -> None:
    """Validate opened raster (CRS, tiling). ``uri`` must be passable to ``rasterio.open``."""
    import rasterio
    from rasterio.crs import CRS

    expected = CRS.from_epsg(EXPECTED_EPSG)

    try:
        with rasterio.open(uri) as src:
            if src.crs is None:
                raise CogValidationError(
                    "raster has no CRS; expected EPSG:3857",
                    code="COG_NO_CRS",
                    context={"expected_epsg": EXPECTED_EPSG},
                )
            if src.crs != expected:
                got = src.crs.to_string() if src.crs else "none"
                raise CogValidationError(
                    f"CRS must be EPSG:3857; got {got}",
                    code="COG_CRS_MISMATCH",
                    context={"expected_epsg": EXPECTED_EPSG, "got_crs": got},
                )
            if not _raster_uses_internal_tiling(src):
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


def validate_suitability_cog_bytes(
    content: bytes, artifact_read: ArtifactReadRuntime
) -> None:
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
        validate_suitability_cog_uri(artifact_read, str(path))
    finally:
        path.unlink(missing_ok=True)


def validate_suitability_cog_path(
    path: Path, artifact_read: ArtifactReadRuntime
) -> None:
    """Validate on-disk COG: tiled, EPSG:3857."""
    validate_suitability_cog_uri(artifact_read, str(path))


def validate_suitability_cog_uri(
    artifact_read: ArtifactReadRuntime, ref: str
) -> None:
    """
    Validate COG from a catalog/storage ref (local path, ``gs://``, or ``/vsicurl/...``).

    All opens go through ``artifact_read.rasterio_open_uri`` so ``gs://`` is never passed
    raw to GDAL in Cloud Run.
    """
    uri = artifact_read.rasterio_open_uri(ref)
    _validate_suitability_cog_rasterio_uri(uri)
