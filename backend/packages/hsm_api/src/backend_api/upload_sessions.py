"""Firestore persistence helpers for admin upload sessions."""

from __future__ import annotations

from google.cloud import firestore

from backend_api.schemas_upload import UploadSession
from backend_api.settings import Settings

UPLOADS_COLLECTION_ID = "upload_sessions"


def upsert_upload_session(settings: Settings, session: UploadSession) -> None:
    """Create or replace ``upload_sessions/{upload_id}``."""
    client = firestore.Client(project=settings.google_cloud_project)
    data = session.model_dump(exclude={"id"}, exclude_none=True)
    client.collection(UPLOADS_COLLECTION_ID).document(session.id).set(data)


def get_upload_session(settings: Settings, upload_id: str) -> UploadSession | None:
    """Read one upload session from Firestore."""
    client = firestore.Client(project=settings.google_cloud_project)
    snap = client.collection(UPLOADS_COLLECTION_ID).document(upload_id).get()
    if not snap.exists:
        return None
    payload = snap.to_dict() or {}
    payload["id"] = upload_id
    return UploadSession.model_validate(payload)
