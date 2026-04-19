"""Normalize Firestore snapshots for Pydantic catalog models."""

from __future__ import annotations

from typing import Any

from google.cloud.firestore_v1 import DocumentSnapshot


def sanitize_firestore_value(value: Any) -> Any:
    """Avoid passing Firestore-only types into Pydantic where possible."""
    if hasattr(value, "isoformat") and callable(value.isoformat):
        try:
            return value.isoformat()
        except (TypeError, ValueError):
            return str(value)
    if isinstance(value, dict):
        return {k: sanitize_firestore_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize_firestore_value(v) for v in value]
    return value


def snapshot_to_document_dict(doc: DocumentSnapshot) -> dict[str, Any]:
    """Merge Firestore document data with document id (same shape as catalog loader)."""
    data = doc.to_dict()
    if not data:
        return {"id": doc.id}
    payload = {k: sanitize_firestore_value(v) for k, v in data.items()}
    payload["id"] = doc.id
    return payload
