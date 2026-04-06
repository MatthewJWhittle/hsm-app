"""Pydantic models aligned with docs/data-models.md."""

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class ModelCard(BaseModel):
    """Human-facing model card (Hugging Face–style metadata)."""

    title: str | None = None
    summary: str | None = None
    metrics: dict[str, Any] | None = Field(
        default=None,
        description="Optional metric map (e.g. accuracy, F1); values are scalars or short strings.",
    )
    spatial_resolution_m: float | None = None
    training_period: str | None = None
    evaluation_notes: str | None = None
    license: str | None = None
    citation: str | None = None


class ModelAnalysis(BaseModel):
    """Training / inference inputs: band subset, serialized estimator, optional overrides."""

    feature_band_indices: list[int] | None = Field(
        default=None,
        description="0-based indices into the project environmental COG (feature order).",
    )
    serialized_model_path: str | None = Field(
        default=None,
        description="Path to pickled sklearn estimator relative to artifact_root (e.g. serialized_model.pkl).",
    )
    positive_class_index: int | None = Field(
        default=None,
        ge=0,
        description="Index for predict_proba positive class (default 1 at runtime).",
    )
    driver_cog_path: str | None = Field(
        default=None,
        description="Optional per-model environmental COG override (relative to artifact_root).",
    )


class ModelMetadata(BaseModel):
    """All non-artifact model description: card, custom extras, and analysis inputs."""

    card: ModelCard | None = None
    extras: dict[str, str] | None = None
    analysis: ModelAnalysis | None = None


class Model(BaseModel):
    """One selectable catalog entry (species + activity + COG paths + optional metadata)."""

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
    metadata: ModelMetadata | None = None

    model_config = {"extra": "allow"}

    @model_validator(mode="before")
    @classmethod
    def _migrate_legacy_driver_fields(cls, data: Any) -> Any:
        """Map legacy ``driver_band_indices`` / ``driver_config`` into ``metadata.analysis``."""
        if not isinstance(data, dict):
            return data
        if data.get("metadata") is not None:
            data.pop("driver_band_indices", None)
            data.pop("driver_config", None)
            return data

        analysis: dict[str, Any] = {}
        if data.get("driver_band_indices") is not None:
            analysis["feature_band_indices"] = data["driver_band_indices"]
        dc = data.get("driver_config")
        if isinstance(dc, dict):
            mp = dc.get("explainability_model_path")
            if isinstance(mp, str) and mp.strip():
                analysis["serialized_model_path"] = mp.strip()
            pc = dc.get("explainability_positive_class")
            if pc is not None:
                try:
                    analysis["positive_class_index"] = int(pc)
                except (TypeError, ValueError):
                    pass
            dcp = dc.get("driver_cog_path")
            if isinstance(dcp, str) and dcp.strip():
                analysis["driver_cog_path"] = dcp.strip()

        meta: dict[str, Any] = {}
        if analysis:
            meta["analysis"] = analysis
        if meta:
            data["metadata"] = meta
        data.pop("driver_band_indices", None)
        data.pop("driver_config", None)
        return data


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
