"""Firestore persistence and lifecycle helpers for generic background jobs."""

from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import UTC, datetime

from google.cloud import firestore

from backend_api.schemas_job import Job, JobError, JobKind, JobStatus, validate_job_input
from backend_api.settings import Settings

logger = logging.getLogger(__name__)

JOBS_COLLECTION_ID = "jobs"
JOB_IDEMPOTENCY_COLLECTION_ID = "job_idempotency"


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _idempotency_doc_id(idempotency_key: str) -> str:
    return hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()


def _persist_job(client: firestore.Client, job: Job) -> None:
    data = job.model_dump(
        exclude={"id"},
        exclude_none=True,
        mode="json",
    )
    client.collection(JOBS_COLLECTION_ID).document(job.id).set(data)


def _job_document_data(job: Job) -> dict:
    return job.model_dump(exclude={"id"}, exclude_none=True, mode="json")


def get_job(settings: Settings, job_id: str) -> Job | None:
    """Load ``jobs/{job_id}`` or return ``None``."""
    client = firestore.Client(project=settings.google_cloud_project)
    snap = client.collection(JOBS_COLLECTION_ID).document(job_id).get()
    if not snap.exists:
        return None
    payload = snap.to_dict() or {}
    payload["id"] = job_id
    return Job.model_validate(payload)


def _create_job_no_idempotency(
    client: firestore.Client,
    *,
    kind: JobKind,
    normalized: dict,
    idempotency_key: str | None,
    created_by_uid: str | None,
) -> Job:
    job_id = str(uuid.uuid4())
    now = _now_iso()
    job = Job(
        id=job_id,
        kind=kind,
        status=JobStatus.QUEUED,
        input=normalized,
        error=None,
        idempotency_key=idempotency_key,
        created_by_uid=created_by_uid,
        created_at=now,
        updated_at=now,
        started_at=None,
        completed_at=None,
    )
    _persist_job(client, job)
    return job


def _create_job_idempotency_transaction(
    transaction,
    *,
    client: firestore.Client,
    idem_ref,
    kind: JobKind,
    normalized: dict,
    idempotency_key: str,
    created_by_uid: str | None,
) -> Job:
    idem_snap = idem_ref.get(transaction=transaction)
    if idem_snap.exists:
        existing_job_id = (idem_snap.to_dict() or {}).get("job_id")
        if isinstance(existing_job_id, str) and existing_job_id:
            job_ref = client.collection(JOBS_COLLECTION_ID).document(existing_job_id)
            job_snap = job_ref.get(transaction=transaction)
            if job_snap.exists:
                payload = dict(job_snap.to_dict() or {})
                payload["id"] = existing_job_id
                return Job.model_validate(payload)

    job_id = str(uuid.uuid4())
    now = _now_iso()
    job = Job(
        id=job_id,
        kind=kind,
        status=JobStatus.QUEUED,
        input=normalized,
        error=None,
        idempotency_key=idempotency_key,
        created_by_uid=created_by_uid,
        created_at=now,
        updated_at=now,
        started_at=None,
        completed_at=None,
    )
    data = _job_document_data(job)
    job_ref = client.collection(JOBS_COLLECTION_ID).document(job_id)
    transaction.set(job_ref, data)
    transaction.set(
        idem_ref,
        {"job_id": job_id, "created_at": now},
    )
    return job


def create_job(
    settings: Settings,
    *,
    kind: JobKind,
    input: dict,
    created_by_uid: str | None = None,
    idempotency_key: str | None = None,
) -> Job:
    """
    Create a ``queued`` job. When ``idempotency_key`` is set and a mapping already exists,
    returns the existing job (duplicate-safe via a Firestore transaction).
    """
    normalized = validate_job_input(kind, input)
    client = firestore.Client(project=settings.google_cloud_project)

    if not idempotency_key:
        return _create_job_no_idempotency(
            client,
            kind=kind,
            normalized=normalized,
            idempotency_key=None,
            created_by_uid=created_by_uid,
        )

    idem_id = _idempotency_doc_id(idempotency_key)
    idem_ref = client.collection(JOB_IDEMPOTENCY_COLLECTION_ID).document(idem_id)
    txn_runner = firestore.transactional(_create_job_idempotency_transaction)
    return txn_runner(
        client.transaction(),
        client=client,
        idem_ref=idem_ref,
        kind=kind,
        normalized=normalized,
        idempotency_key=idempotency_key,
        created_by_uid=created_by_uid,
    )


def _claim_job_in_transaction(
    transaction,
    doc_ref,
    job_id: str,
) -> Job | None:
    """Core of :func:`try_claim_job` (use inside a Firestore transaction)."""
    snap = doc_ref.get(transaction=transaction)
    if not snap.exists:
        return None
    payload = dict(snap.to_dict() or {})
    if payload.get("status") != JobStatus.QUEUED.value:
        return None
    now = _now_iso()
    payload["status"] = JobStatus.RUNNING.value
    payload["started_at"] = now
    payload["updated_at"] = now
    transaction.update(
        doc_ref,
        {
            "status": JobStatus.RUNNING.value,
            "started_at": now,
            "updated_at": now,
        },
    )
    payload["id"] = job_id
    return Job.model_validate(payload)


def try_claim_job(settings: Settings, job_id: str) -> Job | None:
    """
    Atomically move ``queued`` → ``running`` (sets ``started_at``).

    Returns the updated :class:`Job` if claimed, or ``None`` if the document is missing
    or not in ``queued`` state (idempotent / concurrent worker safe).
    """
    client = firestore.Client(project=settings.google_cloud_project)
    ref = client.collection(JOBS_COLLECTION_ID).document(job_id)

    @firestore.transactional
    def _claim(transaction, doc_ref) -> Job | None:
        return _claim_job_in_transaction(transaction, doc_ref, job_id)

    try:
        return _claim(client.transaction(), ref)
    except Exception:
        logger.exception("try_claim_job failed job_id=%s", job_id)
        raise


def complete_job_success(settings: Settings, job_id: str) -> None:
    """Mark job ``succeeded`` and set ``completed_at``."""
    client = firestore.Client(project=settings.google_cloud_project)
    now = _now_iso()
    ref = client.collection(JOBS_COLLECTION_ID).document(job_id)
    ref.update(
        {
            "status": JobStatus.SUCCEEDED.value,
            "updated_at": now,
            "completed_at": now,
            "error": firestore.DELETE_FIELD,
        }
    )


def complete_job_failure(settings: Settings, job_id: str, error: JobError) -> None:
    """Mark job ``failed`` with structured error."""
    client = firestore.Client(project=settings.google_cloud_project)
    now = _now_iso()
    err_map = error.model_dump(exclude_none=True, mode="json")
    client.collection(JOBS_COLLECTION_ID).document(job_id).update(
        {
            "status": JobStatus.FAILED.value,
            "updated_at": now,
            "completed_at": now,
            "error": err_map,
        }
    )
