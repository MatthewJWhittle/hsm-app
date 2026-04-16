"""Environmental COG band count and manifest validation (project-level)."""

from __future__ import annotations

import json
import re
from pathlib import Path

import rasterio
from pydantic import ValidationError
from rasterio.io import DatasetReader, MemoryFile

from backend_api.schemas_project import BandLabelPatch, EnvironmentalBandDefinition


def count_bands_in_geotiff_bytes(content: bytes) -> int:
    """Return band count from in-memory GeoTIFF / COG bytes."""
    with MemoryFile(content) as mem:
        with mem.open() as src:
            return int(src.count)


def count_bands_in_path(path: str) -> int:
    """Return band count from a GeoTIFF / COG on disk."""
    with rasterio.open(path) as src:
        return int(src.count)


def _normalise_machine_band_name(raw: str | None, index: int) -> tuple[str, str | None]:
    """
    Build a stable machine name from GDAL band description, else ``band_{index}``.

    Returns (name, optional warning).
    """
    if raw is None or not str(raw).strip():
        return f"band_{index}", f"Band {index}: no GDAL description; using band_{index}."
    s = str(raw).strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    if not s:
        return f"band_{index}", (
            f"Band {index}: description {raw!r} could not be turned into a machine name; "
            f"using band_{index}."
        )
    if len(s) > 64:
        truncated = s[:64].rstrip("_")
        return truncated, f"Band {index}: machine name truncated from description {raw!r}."
    return s, None


def _uniquify_machine_names(
    defs: list[EnvironmentalBandDefinition],
) -> tuple[list[EnvironmentalBandDefinition], list[str]]:
    """Ensure machine ``name`` values are unique (case-insensitive); append _2, _3, … on collision."""
    warnings: list[str] = []
    used_lower: set[str] = set()
    out: list[EnvironmentalBandDefinition] = []
    for d in defs:
        base = d.name
        candidate = base
        n = 2
        while candidate.lower() in used_lower:
            candidate = f"{base}_{n}"
            n += 1
        if candidate != base:
            warnings.append(
                f"Band {d.index}: machine name {base!r} collided with another band; using {candidate!r}."
            )
        used_lower.add(candidate.lower())
        out.append(d.model_copy(update={"name": candidate}) if candidate != base else d)
    return out, warnings


def infer_band_definitions_from_dataset(
    src: DatasetReader,
) -> tuple[list[EnvironmentalBandDefinition], list[str]]:
    """
    Build one manifest row per raster band from GDAL descriptions (slugified) or ``band_i``.

    Raises:
        ValueError: zero bands or validation failure after inference.
    """
    warnings: list[str] = []
    count = int(src.count)
    if count == 0:
        raise ValueError("environmental raster has zero bands")
    defs: list[EnvironmentalBandDefinition] = []
    for i in range(count):
        raw = src.descriptions[i] if src.descriptions and i < len(src.descriptions) else None
        name, w = _normalise_machine_band_name(raw, i)
        if w:
            warnings.append(w)
        defs.append(EnvironmentalBandDefinition(index=i, name=name, label=None, description=None))
    defs, uw = _uniquify_machine_names(defs)
    warnings.extend(uw)
    validate_band_definitions_match_raster(count, defs)
    return defs, warnings


def infer_band_definitions_from_bytes(content: bytes) -> tuple[list[EnvironmentalBandDefinition], list[str]]:
    """Infer band manifest from in-memory GeoTIFF / COG bytes."""
    with MemoryFile(content) as mem:
        with mem.open() as src:
            return infer_band_definitions_from_dataset(src)


def definitions_from_rasterio_dataset(src: DatasetReader) -> list[EnvironmentalBandDefinition]:
    """
    Build one manifest row per band (legacy helper).

    Prefer :func:`infer_band_definitions_from_dataset` for slugified names and uniqueness.
    """
    defs, _ = infer_band_definitions_from_dataset(src)
    return defs


def default_band_definitions(count: int) -> list[EnvironmentalBandDefinition]:
    """``band_0`` … ``band_{count-1}`` placeholders (admin can rename via PUT)."""
    return [
        EnvironmentalBandDefinition(index=i, name=f"band_{i}", label=None, description=None)
        for i in range(count)
    ]


def default_band_definitions_from_path(path: str) -> list[EnvironmentalBandDefinition]:
    """Derive band definitions from an on-disk GeoTIFF/COG (same rules as upload inference)."""
    with rasterio.open(path) as src:
        defs, _ = infer_band_definitions_from_dataset(src)
    return defs


def band_definitions_for_upload_bytes(
    content: bytes,
    definitions_form: str | None,
    *,
    infer_band_definitions: bool = True,
) -> tuple[list[EnvironmentalBandDefinition], list[str]]:
    """
    Resolve band definitions for a new upload.

    If ``environmental_band_definitions`` JSON is present and non-empty after parse, validate
    against the raster and return (no inference notes).

    Otherwise, if ``infer_band_definitions`` is True, infer names from GDAL band descriptions
    (slugified, unique machine names) and return warnings for fallbacks/collisions.

    If inference is disabled and no definitions are supplied, raises ``ValueError``.
    """
    parsed = parse_band_definitions_json(definitions_form)
    if parsed is not None:
        with MemoryFile(content) as mem:
            with mem.open() as src:
                count = int(src.count)
                validate_band_definitions_match_raster(count, parsed)
        return parsed, []
    if not infer_band_definitions:
        raise ValueError(
            "environmental_band_definitions JSON is required when infer_band_definitions is false"
        )
    return infer_band_definitions_from_bytes(content)


def band_definitions_for_upload_path(
    path: str,
    definitions_form: str | None,
    *,
    infer_band_definitions: bool = True,
) -> tuple[list[EnvironmentalBandDefinition], list[str]]:
    """
    Resolve band definitions for a new upload from an on-disk raster path.
    """
    parsed = parse_band_definitions_json(definitions_form)
    with rasterio.open(path) as src:
        count = int(src.count)
        if parsed is not None:
            validate_band_definitions_match_raster(count, parsed)
            return parsed, []
        if not infer_band_definitions:
            raise ValueError(
                "environmental_band_definitions JSON is required when infer_band_definitions is false"
            )
        return infer_band_definitions_from_dataset(src)


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

    seen_lower: set[str] = set()
    for d in defs:
        k = d.name.lower()
        if k in seen_lower:
            raise ValueError(
                f"duplicate environmental band machine name {d.name!r} "
                "(names must be unique per project, case-insensitive)"
            )
        seen_lower.add(k)


def parse_band_definitions_json(raw: str | None) -> list[EnvironmentalBandDefinition] | None:
    """Parse optional JSON array from multipart form; raise ValueError on bad input."""
    if raw is None or not str(raw).strip():
        return None
    data = json.loads(raw.strip())
    if not isinstance(data, list):
        raise ValueError("environmental_band_definitions must be a JSON array")
    if len(data) == 0:
        return None
    try:
        return [EnvironmentalBandDefinition.model_validate(x) for x in data]
    except ValidationError as e:
        raise ValueError(str(e)) from e


def merge_band_label_patch(
    definition: EnvironmentalBandDefinition, patch: BandLabelPatch
) -> EnvironmentalBandDefinition:
    """Apply partial label/description; ``label`` overrides ``name`` when both are set."""
    fs = patch.model_fields_set
    new_label = definition.label
    new_desc = definition.description
    if "label" in fs:
        new_label = patch.label
    elif "name" in fs:
        new_label = patch.name
    if "description" in fs:
        new_desc = patch.description
    return definition.model_copy(update={"label": new_label, "description": new_desc})


def apply_band_label_updates(
    definitions: list[EnvironmentalBandDefinition],
    updates: dict[str, BandLabelPatch],
) -> list[EnvironmentalBandDefinition]:
    """
    Merge label patches keyed by machine ``name``. Raises ``ValueError`` if any key is unknown.
    """
    if not updates:
        raise ValueError("updates must be non-empty")
    by_name = {d.name for d in definitions}
    unknown = sorted(k for k in updates if k not in by_name)
    if unknown:
        raise ValueError(f"unknown band name(s): {unknown!r}")
    out: list[EnvironmentalBandDefinition] = []
    for d in definitions:
        p = updates.get(d.name)
        if p is None:
            out.append(d)
        else:
            out.append(merge_band_label_patch(d, p))
    return out
