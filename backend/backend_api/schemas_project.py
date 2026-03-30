"""Catalog project (issue #14) — shared driver stack; models link via ``project_id``."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class CatalogProject(BaseModel):
    """
    Admin-defined grouping: one shared environmental (multi-band) COG per project;
    models reference ``project_id`` and a band subset on the model document.
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
    driver_artifact_root: str = Field(
        ...,
        description="Storage prefix for the project's shared environmental COG",
    )
    driver_cog_path: str = Field(
        ...,
        description="Filename or path relative to driver_artifact_root",
    )
    created_at: str | None = None
    updated_at: str | None = None

    model_config = {"extra": "allow"}
