"""Runtime helpers for updating upload session stage/status."""

from __future__ import annotations

from datetime import UTC, datetime

from backend_api.schemas_upload import UploadSession, UploadSessionStage, UploadSessionStatus
from backend_api.settings import Settings
from backend_api.upload_session_transitions import can_transition_status
from backend_api.upload_sessions import upsert_upload_session


def _assert_status_transition(session: UploadSession, target_status: UploadSessionStatus) -> None:
    if target_status == session.status:
        return
    if not can_transition_status(session.status, target_status):
        raise ValueError(
            f"invalid upload session status transition: {session.status!r} -> {target_status!r}"
        )


def mark_upload_session(
    settings: Settings,
    session: UploadSession,
    *,
    status: UploadSessionStatus,
    stage: UploadSessionStage,
) -> UploadSession:
    """Persist a non-error lifecycle update and return the updated session."""
    _assert_status_transition(session, status)
    updated = session.model_copy(
        update={
            "status": status,
            "stage": stage,
            "updated_at": datetime.now(UTC).isoformat(),
            "error_code": None,
            "error_message": None,
            "error_stage": None,
        }
    )
    upsert_upload_session(settings, updated)
    return updated


def fail_upload_session(
    settings: Settings,
    session: UploadSession,
    *,
    stage: UploadSessionStage,
    error_code: str,
    error_message: str,
) -> UploadSession:
    """Persist a terminal failed state and return the updated session."""
    _assert_status_transition(session, "failed")
    updated = session.model_copy(
        update={
            "status": "failed",
            "stage": stage,
            "updated_at": datetime.now(UTC).isoformat(),
            "error_code": error_code,
            "error_message": error_message,
            "error_stage": stage,
        }
    )
    upsert_upload_session(settings, updated)
    return updated
