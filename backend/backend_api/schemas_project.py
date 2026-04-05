"""Catalog project (issue #14) — shared driver stack; models link via ``project_id``."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class EnvironmentalBandDefinition(BaseModel):
    """One band in the project's shared multi-band environmental COG (0-based index)."""

    index: int = Field(..., ge=0, description="0-based band index in the GeoTIFF")
    name: str = Field(
        ...,
        min_length=1,
        description="Stable column name (matches training / model feature order)",
    )
    label: str | None = Field(
        default=None,
        description="Optional human-readable label for UI and raw value display",
    )


class RegenerateExplainabilityBackgroundBody(BaseModel):
    """Optional body for POST ``/projects/{id}/explainability-background-sample``."""

    sample_rows: int | None = Field(
        default=None,
        ge=8,
        le=50_000,
        description="Number of random pixels; omit to use the server default (ENV_BACKGROUND_SAMPLE_ROWS).",
    )


class CatalogProject(BaseModel):
    """
    Admin-defined grouping: optional shared environmental (multi-band) COG per project
    (upload on create or later via admin update); models reference ``project_id`` and a
    band subset on the model document.
    """

    id: str = Field(..., description="Stable opaque id (document id in Firestore)")
    name: str
    description: str | None = None
    status: Literal["active", "archived"] = "active"
    visibility: Literal["public", "private"] = "public"
    allowed_uids: list[str] = Field(
        default_factory=list,
        description="Firebase uids allowed when visibility is private",
    )
    driver_artifact_root: str | None = Field(
        default=None,
        description="Storage prefix for the project's shared environmental COG (set after upload).",
    )
    driver_cog_path: str | None = Field(
        default=None,
        description="Filename or path relative to driver_artifact_root",
    )
    environmental_band_definitions: list[EnvironmentalBandDefinition] | None = Field(
        default=None,
        description="Per-band names (and optional labels) for the environmental COG; set after upload.",
    )
    explainability_background_path: str | None = Field(
        default=None,
        description="Reference sample Parquet for SHAP (relative to driver_artifact_root); auto-generated when the COG is uploaded.",
    )
    explainability_background_sample_rows: int | None = Field(
        default=None,
        description="Row count of the last generated explainability background Parquet (random pixels).",
    )
    explainability_background_generated_at: str | None = Field(
        default=None,
        description="ISO 8601 timestamp when explainability_background.parquet was last written.",
    )
    created_at: str | None = None
    updated_at: str | None = None

    model_config = {"extra": "allow"}
