"""Pydantic models for generic background jobs (Cloud Tasks worker payloads)."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class JobStatus(StrEnum):
    """Lifecycle of a job record in Firestore."""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class JobKind(StrEnum):
    """Registered job types. Extend with new kinds as routes migrate to async jobs."""

    ENVIRONMENTAL_COG_REPLACE = "environmental_cog_replace"


class JobError(BaseModel):
    """Structured failure stored on the job document."""

    code: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)
    detail: str | None = None


class JobInputEnvironmentalCogReplace(BaseModel):
    """Input for :attr:`JobKind.ENVIRONMENTAL_COG_REPLACE`."""

    project_id: str = Field(..., min_length=1)
    upload_session_id: str = Field(..., min_length=1)
    environmental_band_definitions: str | None = Field(
        default=None,
        description="Optional JSON string of band definitions (same as multipart form field).",
    )
    infer_band_definitions: str | None = Field(
        default=None,
        description="Optional form flag for inferring band names (same as multipart form field).",
    )


class JobAcceptedResponse(BaseModel):
    """Returned with **202** when a background job is enqueued (e.g. large env COG replace)."""

    job_id: str
    status: str = "queued"


class Job(BaseModel):
    """Durable job row in Firestore ``jobs/{job_id}``."""

    id: str
    kind: JobKind
    status: JobStatus
    input: dict[str, Any]
    error: JobError | None = None
    idempotency_key: str | None = None
    created_by_uid: str | None = None
    created_at: str
    updated_at: str
    started_at: str | None = None
    completed_at: str | None = None


def validate_job_input(kind: JobKind, raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize and validate ``input`` for ``kind`` (raises ``ValueError`` if invalid)."""
    if kind == JobKind.ENVIRONMENTAL_COG_REPLACE:
        return JobInputEnvironmentalCogReplace.model_validate(raw).model_dump()
    raise ValueError(f"unsupported job kind: {kind!r}")
