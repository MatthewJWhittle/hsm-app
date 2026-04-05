"""Environmental COG band count and manifest validation (project-level)."""

from __future__ import annotations

from pathlib import Path

import rasterio
from rasterio.io import DatasetReader, MemoryFile

from backend_api.schemas_project import EnvironmentalBandDefinition


def count_bands_in_geotiff_bytes(content: bytes) -> int:
    """Return band count from in-memory GeoTIFF / COG bytes."""
    with MemoryFile(content) as mem:
        with mem.open() as src:
            return int(src.count)


def count_bands_in_path(path: str) -> int:
    """Return band count from a GeoTIFF / COG on disk."""
    with rasterio.open(path) as src:
        return int(src.count)


def definitions_from_rasterio_dataset(src: DatasetReader) -> list[EnvironmentalBandDefinition]:
    """
    Build one manifest row per band. Uses GDAL/rasterio per-band ``descriptions``
    as ``name`` when set; otherwise ``band_0`` … ``band_{n-1}``.
    """
    count = int(src.count)
    out: list[EnvironmentalBandDefinition] = []
    for i in range(count):
        raw = src.descriptions[i] if src.descriptions and i < len(src.descriptions) else None
        name = (
            str(raw).strip()
            if raw is not None and str(raw).strip()
            else f"band_{i}"
        )
        out.append(EnvironmentalBandDefinition(index=i, name=name, label=None, description=None))
    return out


def default_band_definitions(count: int) -> list[EnvironmentalBandDefinition]:
    """``band_0`` … ``band_{count-1}`` placeholders (admin can rename via PUT)."""
    return [
        EnvironmentalBandDefinition(index=i, name=f"band_{i}", label=None, description=None)
        for i in range(count)
    ]


def default_band_definitions_from_path(path: str) -> list[EnvironmentalBandDefinition]:
    """Same as :func:`definitions_from_rasterio_dataset` for an on-disk GeoTIFF/COG."""
    with rasterio.open(path) as src:
        return definitions_from_rasterio_dataset(src)


def band_definitions_for_upload_bytes(
    content: bytes, definitions_form: str | None
) -> list[EnvironmentalBandDefinition]:
    """
    Resolve band definitions for a new upload: validate client JSON if present,
    otherwise derive names from the file (band descriptions when set, else ``band_i``).
    """
    parsed = parse_band_definitions_json(definitions_form)
    with MemoryFile(content) as mem:
        with mem.open() as src:
            count = int(src.count)
            if parsed is not None:
                validate_band_definitions_match_raster(count, parsed)
                return parsed
            return definitions_from_rasterio_dataset(src)


def validate_band_definitions_match_raster(
    count: int, defs: list[EnvironmentalBandDefinition]
) -> None:
    """
    Ensure definitions cover exactly ``0 .. count-1`` with unique indices.

    Raises:
        ValueError: mismatch or invalid indices.
    """
    if count < 0:
        raise ValueError("invalid band count")
    if len(defs) != count:
        raise ValueError(
            f"environmental_band_definitions must have {count} entries (one per raster band)"
        )
    seen: set[int] = set()
    for d in defs:
        if d.index in seen:
            raise ValueError(f"duplicate band index {d.index} in definitions")
        seen.add(d.index)
    expected = set(range(count))
    if seen != expected:
        missing = sorted(expected - seen)
        extra = sorted(seen - expected)
        msg = "environmental_band_definitions indices must be exactly 0..n-1"
        if missing:
            msg += f"; missing indices: {missing!r}"
        if extra:
            msg += f"; unexpected indices: {extra!r}"
        raise ValueError(msg)


def parse_band_definitions_json(raw: str | None) -> list[EnvironmentalBandDefinition] | None:
    """Parse optional JSON array from multipart form; raise ValueError on bad input."""
    if raw is None or not str(raw).strip():
        return None
    import json

    from pydantic import ValidationError

    data = json.loads(raw.strip())
    if not isinstance(data, list):
        raise ValueError("environmental_band_definitions must be a JSON array")
    if len(data) == 0:
        return None
    try:
        return [EnvironmentalBandDefinition.model_validate(x) for x in data]
    except ValidationError as e:
        raise ValueError(str(e)) from e
