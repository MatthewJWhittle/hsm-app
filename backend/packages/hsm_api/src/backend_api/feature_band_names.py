"""Resolve ``feature_band_names`` to raster band indices using the project manifest."""

from __future__ import annotations

from backend_api.schemas_project import EnvironmentalBandDefinition


class FeatureBandNamesValidationError(Exception):
    """Invalid feature band names for a project (maps to HTTP 400 with structured ``detail``)."""

    def __init__(self, *, unknown: list[str], duplicate: list[str]) -> None:
        self.unknown = unknown
        self.duplicate = duplicate
        detail: dict = {
            "error": "invalid_feature_band_names",
            "message": "Feature band names must match the project environmental manifest exactly once each.",
        }
        if unknown:
            detail["unknown_feature_band_names"] = unknown
        if duplicate:
            detail["duplicate_feature_band_names"] = duplicate
        self.detail = detail
        super().__init__(detail["message"])


def _manifest_by_lower_name(
    defs: list[EnvironmentalBandDefinition],
) -> dict[str, EnvironmentalBandDefinition]:
    by_lower: dict[str, EnvironmentalBandDefinition] = {}
    for d in defs:
        k = d.name.lower()
        if k in by_lower:
            raise ValueError(
                "environmental_band_definitions has duplicate machine names (case-insensitive); "
                "each band name must be unique per project"
            )
        by_lower[k] = d
    return by_lower


def resolve_feature_band_names_to_indices(
    names: list[str] | None,
    defs: list[EnvironmentalBandDefinition],
) -> list[int]:
    """
    Map ordered machine names to 0-based band indices.

    Matching is case-insensitive on ``EnvironmentalBandDefinition.name``; whitespace is stripped
    on each input name.

    Raises:
        FeatureBandNamesValidationError: unknown or duplicate names in ``names``.
    """
    if not names:
        return []
    by_lower = _manifest_by_lower_name(defs)
    seen_lower: set[str] = set()
    duplicate: list[str] = []
    unknown: list[str] = []
    indices: list[int] = []
    for raw in names:
        n = raw.strip()
        if not n:
            unknown.append("(empty)")
            continue
        k = n.lower()
        if k in seen_lower:
            duplicate.append(n)
            continue
        seen_lower.add(k)
        d = by_lower.get(k)
        if d is None:
            unknown.append(n)
        else:
            indices.append(d.index)
    if unknown or duplicate:
        raise FeatureBandNamesValidationError(
            unknown=sorted(set(unknown)),
            duplicate=sorted(set(duplicate)),
        )
    return indices
