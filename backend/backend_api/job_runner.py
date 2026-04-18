"""Run persisted background jobs (invoked from internal worker HTTP handler)."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from fastapi import HTTPException, Request

from backend_api.catalog_service import CatalogService
from backend_api.deps.catalog import get_object_storage
from backend_api.deps.settings_dep import get_settings
from backend_api.env_cog_replace_pipeline import replace_project_environmental_cogs_pipeline
from backend_api.explainability_background_pipeline import (
    regenerate_explainability_background_pipeline,
)
from backend_api.jobs import (
    complete_job_failure,
    complete_job_success,
    get_job,
    try_claim_job,
)
from backend_api.model_suitability_pipeline import (
    create_model_with_suitability_upload_pipeline,
    update_model_pipeline,
)
from backend_api.project_create_pipeline import create_project_with_environmental_cog_pipeline
from backend_api.schemas import ModelMetadata
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


def _allowed_uids_from_json(raw: str | None) -> list[str]:
    if raw is None or not str(raw).strip():
        return []
    data = json.loads(raw)
    if not isinstance(data, list):
        raise ValueError("allowed_uids_json must be a JSON array")
    out: list[str] = []
    for x in data:
        if not isinstance(x, str):
            raise ValueError("allowed_uids_json must be an array of strings")
        out.append(x)
    return out


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

    t0 = time.perf_counter()
    try:
        kind = claimed.kind
        inp = claimed.input
        logger.info("execute_job start job_id=%s kind=%s", job_id, kind)

        if kind == JobKind.ENVIRONMENTAL_COG_REPLACE:
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
        elif kind == JobKind.PROJECT_CREATE_WITH_ENV_UPLOAD:
            uids = _allowed_uids_from_json(inp.get("allowed_uids_json"))
            await create_project_with_environmental_cog_pipeline(
                request,
                settings,
                storage,
                project_id=str(inp["project_id"]),
                name=str(inp["name"]),
                description=inp.get("description"),
                visibility_v=str(inp["visibility"]),
                uids=uids,
                upload_session_id=str(inp["upload_session_id"]),
                file=None,
                environmental_band_definitions=inp.get("environmental_band_definitions"),
                infer_band_definitions=inp.get("infer_band_definitions"),
            )
        elif kind == JobKind.MODEL_CREATE_WITH_UPLOAD:
            mj = inp.get("metadata_json")
            meta = ModelMetadata.model_validate_json(mj) if mj else None
            await create_model_with_suitability_upload_pipeline(
                request,
                settings,
                storage,
                catalog,
                model_id=str(inp["model_id"]),
                project_id=str(inp["project_id"]),
                species=str(inp["species"]),
                activity=str(inp["activity"]),
                upload_session_id=str(inp["upload_session_id"]),
                file=None,
                metadata=meta,
                serialized_model_file=None,
            )
        elif kind == JobKind.MODEL_REPLACE_SUITABILITY_COG:
            existing = catalog.get_model(str(inp["model_id"]))
            if existing is None:
                complete_job_failure(
                    settings,
                    job_id,
                    JobError(code="MODEL_NOT_FOUND", message=str(inp["model_id"])),
                )
                return
            mj = inp.get("metadata_json")
            md = ModelMetadata.model_validate_json(mj) if mj else existing.metadata
            await update_model_pipeline(
                request,
                settings,
                storage,
                catalog,
                existing,
                species=str(inp["species"]),
                activity=str(inp["activity"]),
                project_id=str(inp["project_id"]),
                metadata=md,
                file=None,
                upload_session_id=str(inp["upload_session_id"]),
                serialized_model_file=None,
            )
        elif kind == JobKind.EXPLAINABILITY_BACKGROUND_REGENERATE:
            await regenerate_explainability_background_pipeline(
                request,
                settings,
                storage,
                catalog,
                str(inp["project_id"]),
                inp.get("sample_rows"),
            )
        else:
            complete_job_failure(
                settings,
                job_id,
                JobError(
                    code="UNSUPPORTED_JOB_KIND",
                    message=str(kind),
                ),
            )
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
