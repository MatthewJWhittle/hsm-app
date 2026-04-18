"""Run persisted background jobs (invoked from internal worker HTTP handler)."""

from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import HTTPException, Request

from backend_api.catalog_service import CatalogService
from backend_api.deps.catalog import get_object_storage
from backend_api.deps.settings_dep import get_settings
from backend_api.job_handlers import JobRunContext, get_job_handler, run_job_handler
from backend_api.jobs import (
    complete_job_failure,
    complete_job_success,
    get_job,
    try_claim_job,
)
from backend_api.schemas_job import JobError, JobKind, JobStatus
from backend_api.storage import ObjectStorage

logger = logging.getLogger(__name__)


def _job_error_from_http_exception(exc: HTTPException) -> JobError:
    detail: Any = exc.detail
    if isinstance(detail, dict) and "code" in detail:
        return JobError(
            code=str(detail["code"]),
            message=str(detail.get("message", ""))[:8000],
        )
    return JobError(code=f"HTTP_{exc.status_code}", message=str(detail)[:8000])


async def execute_job(request: Request, job_id: str) -> None:
    """
    Claim ``job_id`` and run the registered handler.

    Raises :class:`HTTPException` only for infrastructure issues (e.g. missing job).
    Business failures are recorded on the job document and the handler returns **200**
    so Cloud Tasks does not retry indefinitely.
    """
    settings = get_settings(request)
    job = get_job(settings, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")

    if job.status in (JobStatus.SUCCEEDED, JobStatus.FAILED):
        logger.info("execute_job skip terminal job_id=%s status=%s", job_id, job.status)
        return

    claimed = try_claim_job(settings, job_id)
    if claimed is None:
        latest = get_job(settings, job_id)
        if latest and latest.status in (JobStatus.SUCCEEDED, JobStatus.FAILED):
            return
        if latest and latest.status == JobStatus.RUNNING:
            return
        raise HTTPException(status_code=409, detail="job could not be claimed")

    storage: ObjectStorage = get_object_storage(request)
    catalog: CatalogService = request.app.state.catalog_service
    if getattr(catalog, "load_error", None) or getattr(catalog, "validation_error", None):
        complete_job_failure(
            settings,
            job_id,
            JobError(code="CATALOG_NOT_READY", message="catalog service not ready"),
        )
        return

    kind = claimed.kind
    handler = get_job_handler(kind)
    if handler is None:
        complete_job_failure(
            settings,
            job_id,
            JobError(code="UNSUPPORTED_JOB_KIND", message=str(kind)),
        )
        return

    ctx = JobRunContext(
        request=request,
        settings=settings,
        storage=storage,
        catalog=catalog,
        job_id=job_id,
    )

    t0 = time.perf_counter()
    try:
        logger.info("execute_job start job_id=%s kind=%s", job_id, kind)
        await run_job_handler(ctx, kind, claimed.input, handler)

        latest = get_job(settings, job_id)
        if latest is None:
            logger.warning("execute_job job missing after handler job_id=%s", job_id)
            return
        if latest.status == JobStatus.FAILED:
            duration_ms = int((time.perf_counter() - t0) * 1000)
            logger.info(
                "execute_job handler recorded failure job_id=%s kind=%s duration_ms=%s",
                job_id,
                kind,
                duration_ms,
            )
            return
        if latest.status == JobStatus.SUCCEEDED:
            return

        complete_job_success(settings, job_id)
        duration_ms = int((time.perf_counter() - t0) * 1000)
        logger.info(
            "execute_job succeeded job_id=%s kind=%s duration_ms=%s",
            job_id,
            kind,
            duration_ms,
        )
    except HTTPException as e:
        duration_ms = int((time.perf_counter() - t0) * 1000)
        logger.warning(
            "execute_job HTTP error job_id=%s status=%s duration_ms=%s detail=%s",
            job_id,
            e.status_code,
            duration_ms,
            e.detail,
        )
        complete_job_failure(settings, job_id, _job_error_from_http_exception(e))
    except Exception as e:
        duration_ms = int((time.perf_counter() - t0) * 1000)
        logger.exception(
            "execute_job failed job_id=%s duration_ms=%s",
            job_id,
            duration_ms,
        )
        complete_job_failure(
            settings,
            job_id,
            JobError(code="JOB_RUNTIME_ERROR", message=str(e)[:4000]),
        )
