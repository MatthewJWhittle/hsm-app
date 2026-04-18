"""Shared HTTP helpers for admin routes that enqueue background jobs (202 + Location)."""

from __future__ import annotations

from fastapi.responses import JSONResponse

from backend_api.job_queue import build_job_queue
from backend_api.jobs import create_job
from backend_api.schemas_job import Job, JobAcceptedResponse, JobKind
from backend_api.settings import Settings


def admin_created_by_uid(claims: dict) -> str | None:
    """Firebase uid from ID-token claims for ``created_by_uid`` on job rows."""
    return str(claims.get("uid") or "") or None


def enqueue_and_schedule_job(
    settings: Settings,
    *,
    kind: JobKind,
    input: dict,
    created_by_uid: str | None,
) -> Job:
    """Persist a queued job and dispatch it to the configured :class:`~backend_api.job_queue.JobQueue`."""
    job = create_job(
        settings,
        kind=kind,
        input=input,
        created_by_uid=created_by_uid,
    )
    build_job_queue(settings).enqueue_run_job(job.id)
    return job


def accepted_job_202_response(
    job: Job,
    *,
    project_id: str | None = None,
    model_id: str | None = None,
) -> JSONResponse:
    """``202 Accepted`` with ``Location: /api/jobs/{id}`` for async job flows."""
    body = JobAcceptedResponse(
        job_id=job.id,
        status=job.status.value,
        project_id=project_id,
        model_id=model_id,
    )
    return JSONResponse(
        status_code=202,
        content=body.model_dump(mode="json"),
        headers={"Location": f"/api/jobs/{job.id}"},
    )
