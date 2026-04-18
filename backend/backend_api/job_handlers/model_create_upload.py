"""Handler: create model with suitability COG from upload session.

Canonical implementation: :func:`backend_api.model_suitability_pipeline.create_model_with_suitability_upload_pipeline`.
"""

from __future__ import annotations

from fastapi import HTTPException

from backend_api.job_errors import wrap_pipeline_infra_errors
from backend_api.job_handlers.context import JobRunContext
from backend_api.model_suitability_pipeline import create_model_with_suitability_upload_pipeline
from backend_api.schemas import ModelMetadata
from backend_api.schemas_job import JobInputModelCreateWithUpload


async def run(ctx: JobRunContext, inp: JobInputModelCreateWithUpload) -> None:
    meta = ModelMetadata.model_validate_json(inp.metadata_json) if inp.metadata_json else None
    try:
        await create_model_with_suitability_upload_pipeline(
            ctx.request,
            ctx.settings,
            ctx.storage,
            ctx.catalog,
            model_id=inp.model_id,
            project_id=inp.project_id,
            species=inp.species,
            activity=inp.activity,
            upload_session_id=inp.upload_session_id,
            file=None,
            metadata=meta,
            serialized_model_file=None,
        )
    except HTTPException:
        raise
    except Exception as e:
        wrap_pipeline_infra_errors(e)
