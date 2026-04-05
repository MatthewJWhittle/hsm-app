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
    created_at: str | None = None
    updated_at: str | None = None

    model_config = {"extra": "allow"}
