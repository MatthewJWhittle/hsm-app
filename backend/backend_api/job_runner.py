"""Run persisted background jobs (invoked from internal worker HTTP handler)."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException, Request

from backend_api.catalog_service import CatalogService
from backend_api.deps.catalog import get_object_storage
from backend_api.deps.settings_dep import get_settings
from backend_api.env_cog_replace_pipeline import replace_project_environmental_cogs_pipeline
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

    try:
        if claimed.kind == JobKind.ENVIRONMENTAL_COG_REPLACE:
            inp = claimed.input
            await replace_project_environmental_cogs_pipeline(
                request,
                settings,
                storage,
                catalog,
                str(inp["project_id"]),
                None,
                str(inp["upload_session_id"]),
                inp.get("environmental_band_definitions"),
                inp.get("infer_band_definitions"),
            )
            complete_job_success(settings, job_id)
            logger.info("execute_job succeeded job_id=%s kind=%s", job_id, claimed.kind)
        else:
            complete_job_failure(
                settings,
                job_id,
                JobError(
                    code="UNSUPPORTED_JOB_KIND",
                    message=str(claimed.kind),
                ),
            )
    except HTTPException as e:
        logger.warning(
            "execute_job HTTP error job_id=%s status=%s detail=%s",
            job_id,
            e.status_code,
            e.detail,
        )
        complete_job_failure(settings, job_id, _job_error_from_http_exception(e))
    except Exception as e:
        logger.exception("execute_job failed job_id=%s", job_id)
        complete_job_failure(
            settings,
            job_id,
            JobError(code="JOB_RUNTIME_ERROR", message=str(e)[:4000]),
        )
