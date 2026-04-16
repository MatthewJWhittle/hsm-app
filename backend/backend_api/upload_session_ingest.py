"""Shared helpers for session-backed upload ingestion flows."""

from __future__ import annotations

import logging

from fastapi import HTTPException
from google.cloud import storage

from backend_api.api_errors import validation_error
from backend_api.schemas_upload import (
    UploadSession,
    UploadSessionStage,
    UploadSessionStatus,
)
from backend_api.settings import Settings
from backend_api.upload_session_runtime import fail_upload_session, mark_upload_session
from backend_api.upload_sessions import get_upload_session

logger = logging.getLogger(__name__)


def download_upload_session_bytes(
    settings: Settings, upload_session_id: str, *, purpose: str
) -> tuple[bytes, UploadSession]:
    """Resolve a ready upload session and download its bytes."""
    session = get_upload_session(settings, upload_session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="upload session not found")
    if session.status not in ("uploaded", "validating", "deriving", "ready"):
        raise HTTPException(
            status_code=409,
            detail=validation_error(
                "UPLOAD_NOT_READY",
                f"upload session status {session.status!r} is not ready for {purpose}",
            ),
        )
    if not settings.gcs_bucket or session.gcs_bucket != settings.gcs_bucket:
        raise HTTPException(
            status_code=422,
            detail=validation_error(
                "UPLOAD_BUCKET_MISMATCH",
                "upload session bucket does not match configured API bucket",
            ),
        )
    client = storage.Client()
    bucket = client.bucket(session.gcs_bucket)
    blob = bucket.blob(session.object_path)
    if not blob.exists():
        raise HTTPException(
            status_code=422,
            detail=validation_error(
                "UPLOAD_OBJECT_MISSING",
                "upload object not found in storage",
            ),
        )
    return blob.download_as_bytes(), session


def best_effort_mark(
    settings: Settings,
    session: UploadSession | None,
    *,
    status: UploadSessionStatus,
    stage: UploadSessionStage,
    context: str,
) -> UploadSession | None:
    """Attempt non-terminal transition and log on failure."""
    if session is None:
        return None
    try:
        return mark_upload_session(settings, session, status=status, stage=stage)
    except Exception:
        logger.warning(
            "Upload session mark failed (%s): id=%s status=%s stage=%s",
            context,
            session.id,
            status,
            stage,
            exc_info=True,
        )
        return session


def best_effort_fail(
    settings: Settings,
    session: UploadSession | None,
    *,
    stage: UploadSessionStage,
    error_code: str,
    error_message: str,
    context: str,
) -> UploadSession | None:
    """Attempt terminal failure transition and log on failure."""
    if session is None:
        return None
    try:
        return fail_upload_session(
            settings,
            session,
            stage=stage,
            error_code=error_code,
            error_message=error_message,
        )
    except Exception:
        logger.warning(
            "Upload session fail-mark failed (%s): id=%s stage=%s error_code=%s",
            context,
            session.id,
            stage,
            error_code,
            exc_info=True,
        )
        return session
