"""Pydantic models aligned with docs/data-models.md."""

from typing import Any

from pydantic import BaseModel, Field


class Model(BaseModel):
    """One selectable catalog entry (species + activity + COG paths)."""

    id: str = Field(..., description="Stable identifier (slug-safe)")
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
    driver_config: dict[str, Any] | None = None

    model_config = {"extra": "allow"}
