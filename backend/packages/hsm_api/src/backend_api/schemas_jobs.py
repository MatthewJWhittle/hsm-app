"""API schemas for background jobs."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from backend_api.schemas_project import CatalogProject


class JobAcceptedResponse(BaseModel):
    job_id: str
    status: Literal["pending"] = "pending"


class JobPollResponse(BaseModel):
    job_id: str
    status: str
    kind: str
    project_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    project: CatalogProject | None = Field(
        default=None,
        description="When status is succeeded, loaded from Firestore for admin UI.",
    )
