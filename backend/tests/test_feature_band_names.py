"""Unit tests for feature_band_names resolution."""

import pytest

from backend_api.feature_band_names import (
    FeatureBandNamesValidationError,
    resolve_feature_band_names_to_indices,
)
from backend_api.schemas_project import EnvironmentalBandDefinition


def _defs() -> list[EnvironmentalBandDefinition]:
    return [
        EnvironmentalBandDefinition(index=0, name="a", label=None),
        EnvironmentalBandDefinition(index=1, name="B", label=None),
    ]


def test_resolve_order_and_case_insensitive() -> None:
    assert resolve_feature_band_names_to_indices(["B", "a"], _defs()) == [1, 0]


def test_unknown_raises() -> None:
    with pytest.raises(FeatureBandNamesValidationError) as ei:
        resolve_feature_band_names_to_indices(["a", "missing"], _defs())
    assert "unknown_feature_band_names" in ei.value.detail  # type: ignore[attr-defined]


def test_duplicate_in_list_raises() -> None:
    with pytest.raises(FeatureBandNamesValidationError) as ei:
        resolve_feature_band_names_to_indices(["a", "a"], _defs())
    assert "duplicate_feature_band_names" in ei.value.detail  # type: ignore[union-attr]


def test_manifest_duplicate_names_rejected() -> None:
    from backend_api.env_cog_bands import validate_band_definitions_match_raster

    defs = [
        EnvironmentalBandDefinition(index=0, name="a", label=None),
        EnvironmentalBandDefinition(index=1, name="A", label=None),
    ]
    with pytest.raises(ValueError, match="duplicate"):
        validate_band_definitions_match_raster(2, defs)
