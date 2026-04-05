"""Pydantic models aligned with docs/data-models.md."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class Model(BaseModel):
    """One selectable catalog entry (species + activity + COG paths)."""

    id: str = Field(..., description="Stable identifier (slug-safe)")
    project_id: str | None = Field(
        None,
        description="Parent catalog project id; omit only for legacy rows pre-migration",
    )
    species: str
    activity: str
    artifact_root: str = Field(
        ...,
        description="Base path in storage for this model's artifacts",
    )
    suitability_cog_path: str = Field(
        ...,
        description="Path to suitability COG (absolute or relative to artifact_root)",
    )
    model_name: str | None = None
    model_version: str | None = None
    driver_band_indices: list[int] | None = Field(
        None,
        description="0-based band indices into the project's shared environmental COG",
    )
    driver_config: dict[str, Any] | None = None

    model_config = {"extra": "allow"}


class DriverVariable(BaseModel):
    """One variable’s contribution to suitability at this point (e.g. SHAP-style influence)."""

    name: str
    direction: Literal["increase", "decrease", "neutral"]
    label: str | None = None
    magnitude: float | None = None
    display_name: str | None = Field(
        default=None,
        description="Human-friendly name from catalog (when different from ``name``).",
    )


class RawEnvironmentalValue(BaseModel):
    """Sampled environmental input at the clicked location (secondary detail)."""

    name: str
    value: float
    unit: str | None = None
    description: str | None = Field(
        default=None,
        description="Optional catalog description for this variable.",
    )


class PointInspection(BaseModel):
    """Suitability value, optional influence drivers, and optional raw env values at a location."""

    value: float
    unit: str | None = None
    drivers: list[DriverVariable] = Field(
        default_factory=list,
        description="Ranked variable influence (e.g. SHAP); empty when explainability is not configured.",
    )
    raw_environmental_values: list[RawEnvironmentalValue] | None = Field(
        default=None,
        description="Raw raster values for configured bands at this point (same order as model inputs when aligned).",
    )


class AuthMeResponse(BaseModel):
    """Decoded Firebase ID token fields exposed to the client."""

    uid: str
    email: str | None = None
