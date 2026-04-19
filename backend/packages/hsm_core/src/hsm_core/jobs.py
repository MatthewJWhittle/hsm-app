"""Firestore-backed background job documents (API + worker).

Writes are performed only from trusted server code. ``firestore.rules`` deny
client access to ``jobs/*``; API/worker use the Admin SDK.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from google.cloud import firestore
from pydantic import BaseModel, Field

from hsm_core.job_error_codes import JobErrorCode, job_error_code_str

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
    # Kind-specific parameters (prefer this for new fields; legacy top-level keys stay for compat)
    params: dict[str, Any] | None = None


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
    params: dict[str, Any] | None = (
        {"sample_rows": sample_rows} if sample_rows is not None else None
    )
    return JobDocument(
        job_id=new_job_id(),
        status="pending",
        kind=kind,
        project_id=project_id,
        created_by_uid=created_by_uid,
        created_at=now,
        updated_at=now,
        sample_rows=sample_rows,
        params=params,
    )


def explainability_sample_rows_for_job(job: JobDocument, *, settings_default: int) -> int:
    """Resolve row count for explainability sampling (``params`` then legacy ``sample_rows``)."""
    if job.params:
        raw = job.params.get("sample_rows")
        if isinstance(raw, int):
            return raw
    if job.sample_rows is not None:
        return job.sample_rows
    return settings_default


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


def try_abandon_stale_pending_job(
    client: firestore.Client,
    job: JobDocument,
    *,
    abandon_after_seconds: int | None,
) -> JobDocument:
    """If ``pending`` longer than ``abandon_after_seconds``, mark ``failed`` (NEVER_DISPATCHED).

    Uses a transaction so only one writer wins. Disabled when ``abandon_after_seconds`` is
    None or non-positive.
    """
    if not abandon_after_seconds or abandon_after_seconds <= 0:
        return job
    if job.status != "pending":
        return job
    created = _parse_firestore_datetime(job.created_at)
    if created is None:
        return job
    if (datetime.now(UTC) - created).total_seconds() < abandon_after_seconds:
        return job

    ref = client.collection(JOBS_COLLECTION_ID).document(job.job_id)

    @firestore.transactional
    def _abandon(
        transaction: firestore.Transaction,
        doc_ref: firestore.DocumentReference,
    ) -> JobDocument:
        snap = doc_ref.get(transaction=transaction)
        if not snap.exists:
            return job
        data = snap.to_dict() or {}
        if data.get("status") != "pending":
            return job_from_firestore(data, job.job_id)
        now = _now_iso()
        _pending_abandon_msg = (
            "job remained pending longer than the configured maximum window"
        )
        transaction.update(
            doc_ref,
            {
                "status": "failed",
                "error_code": JobErrorCode.NEVER_DISPATCHED,
                "error_message": _pending_abandon_msg,
                "updated_at": now,
            },
        )
        data["status"] = "failed"
        data["error_code"] = JobErrorCode.NEVER_DISPATCHED
        data["error_message"] = _pending_abandon_msg
        data["updated_at"] = now
        return job_from_firestore(data, job.job_id)

    return _abandon(client.transaction(), ref)


def _parse_firestore_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        try:
            s = str(value).replace("Z", "+00:00")
            dt = datetime.fromisoformat(s)
        except (ValueError, TypeError):
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


def running_lease_is_stale(
    updated_at_raw: Any,
    *,
    stale_after_seconds: int,
    now: datetime | None = None,
) -> bool:
    """True if ``updated_at`` is missing, unparseable, or older than ``stale_after_seconds``."""
    if stale_after_seconds <= 0:
        return True
    started = _parse_firestore_datetime(updated_at_raw)
    if started is None:
        return True
    now_dt = now if now is not None else datetime.now(UTC)
    if now_dt.tzinfo is None:
        now_dt = now_dt.replace(tzinfo=UTC)
    return (now_dt - started).total_seconds() >= stale_after_seconds


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


def fail_job(
    client: firestore.Client,
    job_id: str,
    *,
    code: JobErrorCode | str,
    message: str,
    max_message_len: int = 2000,
) -> None:
    """Set job to ``failed`` with a truncated, user-safe message."""
    c = job_error_code_str(code)
    msg = (message.strip() or c)[:max_message_len]
    update_job_status(client, job_id, status="failed", error_code=c, error_message=msg)


def try_claim_job_for_execution(
    client: firestore.Client,
    job_id: str,
    *,
    stale_running_after_seconds: int,
) -> JobDocument | None:
    """Claim a job for execution (pending -> running, or reclaim stale running).

    Cloud Tasks retries may arrive while status is still ``running`` if the worker
    died after the claim. When ``updated_at`` is older than ``stale_running_after_seconds``,
    refresh the lease (``updated_at``) and return the document so work can run again.
    Pass ``stale_running_after_seconds`` equal to ``WORKER_HTTP_DEADLINE_SECONDS`` (plus a
    small optional grace, often **0**) so the first retry after an HTTP timeout can reclaim.

    Returns ``None`` if the job is missing, terminal (succeeded/failed), or ``running``
    with a fresh lease.
    """
    ref = client.collection(JOBS_COLLECTION_ID).document(job_id)

    @firestore.transactional
    def _claim(
        transaction: firestore.Transaction,
        doc_ref: firestore.DocumentReference,
    ) -> JobDocument | None:
        snap = doc_ref.get(transaction=transaction)
        if not snap.exists:
            return None
        data = snap.to_dict() or {}
        status = data.get("status")
        now = _now_iso()
        if status in ("succeeded", "failed"):
            return None
        if status == "pending":
            transaction.update(
                doc_ref,
                {
                    "status": "running",
                    "updated_at": now,
                },
            )
            data["status"] = "running"
            data["updated_at"] = now
            return job_from_firestore(data, job_id)
        if status == "running":
            if not running_lease_is_stale(
                data.get("updated_at"),
                stale_after_seconds=stale_running_after_seconds,
            ):
                return None
            transaction.update(doc_ref, {"updated_at": now})
            data["updated_at"] = now
            return job_from_firestore(data, job_id)
        return None

    return _claim(client.transaction(), ref)
