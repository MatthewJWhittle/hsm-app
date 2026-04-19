"""Firestore-backed background job documents (API + worker).

Writes are performed only from trusted server code. Client-facing
``firestore.rules`` should be tightened for ``jobs/*`` when convenient
(GitHub #67 follow-up).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from google.cloud import firestore
from pydantic import BaseModel, Field

JOBS_COLLECTION_ID = "jobs"

JobStatus = Literal["pending", "running", "succeeded", "failed"]


class JobDocument(BaseModel):
    """Stored at ``jobs/{job_id}``."""

    job_id: str
    status: JobStatus
    kind: str
    project_id: str | None = None
    created_by_uid: str | None = None
    created_at: str
    updated_at: str
    error_code: str | None = None
    error_message: str | None = None
    # Snapshot for explainability_background_sample
    sample_rows: int | None = None


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def new_job_id() -> str:
    return str(uuid.uuid4())


def create_job_document(
    *,
    kind: str,
    project_id: str | None,
    created_by_uid: str | None,
    sample_rows: int | None = None,
) -> JobDocument:
    now = _now_iso()
    return JobDocument(
        job_id=new_job_id(),
        status="pending",
        kind=kind,
        project_id=project_id,
        created_by_uid=created_by_uid,
        created_at=now,
        updated_at=now,
        sample_rows=sample_rows,
    )


def job_to_firestore(doc: JobDocument) -> dict[str, Any]:
    return doc.model_dump()


def job_from_firestore(data: dict[str, Any], job_id: str) -> JobDocument:
    payload = dict(data)
    payload["job_id"] = job_id
    return JobDocument.model_validate(payload)


def write_job(client: firestore.Client, doc: JobDocument) -> None:
    ref = client.collection(JOBS_COLLECTION_ID).document(doc.job_id)
    ref.set(job_to_firestore(doc))


def get_job(client: firestore.Client, job_id: str) -> JobDocument | None:
    ref = client.collection(JOBS_COLLECTION_ID).document(job_id)
    snap = ref.get()
    if not snap.exists:
        return None
    return job_from_firestore(snap.to_dict() or {}, job_id)


def update_job_status(
    client: firestore.Client,
    job_id: str,
    *,
    status: JobStatus,
    error_code: str | None = None,
    error_message: str | None = None,
) -> None:
    ref = client.collection(JOBS_COLLECTION_ID).document(job_id)
    payload: dict[str, Any] = {
        "status": status,
        "updated_at": _now_iso(),
    }
    if error_code is not None:
        payload["error_code"] = error_code
    if error_message is not None:
        payload["error_message"] = error_message
    if status == "succeeded":
        payload["error_code"] = None
        payload["error_message"] = None
    ref.update(payload)


def try_claim_pending_job(
    client: firestore.Client,
    job_id: str,
) -> JobDocument | None:
    """Atomically transition pending -> running. Returns doc if claim won."""
    ref = client.collection(JOBS_COLLECTION_ID).document(job_id)

    @firestore.transactional
    def _claim(transaction: firestore.Transaction, doc_ref: firestore.DocumentReference) -> JobDocument | None:
        snap = doc_ref.get(transaction=transaction)
        if not snap.exists:
            return None
        data = snap.to_dict() or {}
        if data.get("status") != "pending":
            return None
        transaction.update(
            doc_ref,
            {
                "status": "running",
                "updated_at": _now_iso(),
            },
        )
        data["status"] = "running"
        data["updated_at"] = _now_iso()
        return job_from_firestore(data, job_id)

    return _claim(client.transaction(), ref)
