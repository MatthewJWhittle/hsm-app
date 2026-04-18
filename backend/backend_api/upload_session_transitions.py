"""Centralized upload session lifecycle transitions."""

from __future__ import annotations

from backend_api.schemas_upload import UploadSession

_ALLOWED_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"complete", "failed"},
    "complete": {"failed"},
    "failed": set(),
}


def can_transition_status(current: str, target: str) -> bool:
    """Return whether the upload status transition is allowed."""
    return target in _ALLOWED_STATUS_TRANSITIONS.get(current, set())


def complete_upload_transition(
    session: UploadSession, *, size_bytes: int | None, checksum_sha256: str | None, now_iso: str
) -> UploadSession:
    """
    Transition a session for ``POST /uploads/{id}/complete``.

    Rules:
    - pending -> complete (stage upload -> done)
    - complete is idempotent
    - failed rejects transition
    """
    if session.status == "failed":
        raise ValueError(f"cannot complete upload in status {session.status!r}")

    next_status = "complete" if session.status == "pending" else session.status
    next_stage = "done" if session.status == "pending" else session.stage

    return session.model_copy(
        update={
            "status": next_status,
            "stage": next_stage,
            "uploaded_size_bytes": (
                size_bytes if size_bytes is not None else session.uploaded_size_bytes
            ),
            "checksum_sha256": (
                checksum_sha256
                if checksum_sha256 is not None
                else session.checksum_sha256
            ),
            "updated_at": now_iso,
        }
    )
