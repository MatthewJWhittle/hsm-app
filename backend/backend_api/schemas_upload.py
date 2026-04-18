"""Pydantic schemas for admin upload sessions."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

UploadSessionStatus = Literal[
    "pending",
    "complete",
    "failed",
]

UploadSessionStage = Literal[
    "init",
    "upload",
    "validate",
    "derive",
    "persist",
    "done",
]


class UploadInitBody(BaseModel):
    """Request body for creating an upload session."""

    project_id: str | None = Field(
        default=None,
        description="Optional project id this upload is for.",
    )
    filename: str = Field(
        ...,
        min_length=1,
        max_length=512,
        description="Original client filename.",
    )
    content_type: str | None = Field(
        default=None,
        max_length=128,
        description="Client MIME type.",
    )
    size_bytes: int | None = Field(
        default=None,
        ge=0,
        description="Optional expected file size in bytes.",
    )


class UploadCompleteBody(BaseModel):
    """Request body for marking an upload as complete."""

    size_bytes: int | None = Field(
        default=None,
        ge=0,
        description="Optional observed uploaded object size.",
    )
    checksum_sha256: str | None = Field(
        default=None,
        min_length=32,
        max_length=128,
        description="Optional client checksum for future verification.",
    )


class UploadSession(BaseModel):
    """Stored upload session state."""

    id: str
    project_id: str | None = None
    filename: str
    content_type: str | None = None
    requested_size_bytes: int | None = None
    uploaded_size_bytes: int | None = None
    checksum_sha256: str | None = None
    status: UploadSessionStatus
    stage: UploadSessionStage
    gcs_bucket: str
    object_path: str
    created_by_uid: str
    created_at: str
    updated_at: str
    error_code: str | None = None
    error_message: str | None = None
    error_stage: UploadSessionStage | None = None


class UploadSessionResponse(BaseModel):
    """API response for upload session lifecycle endpoints."""

    id: str
    status: UploadSessionStatus
    project_id: str | None = None
    filename: str
    content_type: str | None = None
    requested_size_bytes: int | None = None
    uploaded_size_bytes: int | None = None
    checksum_sha256: str | None = None
    stage: UploadSessionStage
    gcs_bucket: str
    object_path: str
    upload_url: str | None = None
    created_at: str
    updated_at: str
    error_code: str | None = None
    error_message: str | None = None
    error_stage: UploadSessionStage | None = None


def to_upload_session_response(
    session: UploadSession, *, upload_url: str | None = None
) -> UploadSessionResponse:
    """Map stored upload session to API response shape."""
    return UploadSessionResponse(
        id=session.id,
        status=session.status,
        project_id=session.project_id,
        filename=session.filename,
        content_type=session.content_type,
        requested_size_bytes=session.requested_size_bytes,
        uploaded_size_bytes=session.uploaded_size_bytes,
        checksum_sha256=session.checksum_sha256,
        stage=session.stage,
        gcs_bucket=session.gcs_bucket,
        object_path=session.object_path,
        upload_url=upload_url,
        created_at=session.created_at,
        updated_at=session.updated_at,
        error_code=session.error_code,
        error_message=session.error_message,
        error_stage=session.error_stage,
    )
