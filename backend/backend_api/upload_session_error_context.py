"""Structured ``context`` for upload-session-related validation errors."""

from __future__ import annotations

from backend_api.schemas_upload import UploadSession


def upload_error_context(
    *,
    project_id: str,
    phase: str,
    uploaded_session: UploadSession | None,
    extra: dict | None = None,
) -> dict:
    ctx: dict = {
        "project_id": project_id,
        "phase": phase,
        "upload_session_id": uploaded_session.id if uploaded_session is not None else None,
    }
    if extra:
        ctx.update(extra)
    return ctx
