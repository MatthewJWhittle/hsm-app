"""Handler: replace model suitability COG from upload session.

Canonical implementation: :func:`backend_api.model_suitability_pipeline.update_model_pipeline`.
"""

from __future__ import annotations

from fastapi import HTTPException

from backend_api.job_errors import wrap_pipeline_infra_errors
from backend_api.job_handlers.context import JobRunContext
from backend_api.model_suitability_pipeline import update_model_pipeline
from backend_api.schemas import ModelMetadata
from backend_api.schemas_job import JobError, JobInputModelReplaceSuitabilityCog
from backend_api.jobs import complete_job_failure


async def run(ctx: JobRunContext, inp: JobInputModelReplaceSuitabilityCog) -> None:
    existing = ctx.catalog.get_model(inp.model_id)
    if existing is None:
        complete_job_failure(
            ctx.settings,
            ctx.job_id,
            JobError(code="MODEL_NOT_FOUND", message=inp.model_id),
        )
        return
    md = ModelMetadata.model_validate_json(inp.metadata_json) if inp.metadata_json else existing.metadata
    try:
        await update_model_pipeline(
            ctx.request,
            ctx.settings,
            ctx.storage,
            ctx.catalog,
            existing,
            species=inp.species,
            activity=inp.activity,
            project_id=inp.project_id,
            metadata=md,
            file=None,
            upload_session_id=inp.upload_session_id,
            serialized_model_file=None,
        )
    except HTTPException:
        raise
    except Exception as e:
        wrap_pipeline_infra_errors(e)
