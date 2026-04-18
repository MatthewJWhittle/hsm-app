"""Handler: create project with environmental COG from upload session.

Canonical implementation: :func:`backend_api.project_create_pipeline.create_project_with_environmental_cog_pipeline`.
"""

from __future__ import annotations

from fastapi import HTTPException

from backend_api.job_errors import wrap_pipeline_infra_errors
from backend_api.job_handlers.context import JobRunContext
from backend_api.job_handlers.project_utils import allowed_uids_from_json
from backend_api.project_create_pipeline import create_project_with_environmental_cog_pipeline
from backend_api.schemas_job import JobInputProjectCreateWithEnvUpload


async def run(ctx: JobRunContext, inp: JobInputProjectCreateWithEnvUpload) -> None:
    uids = allowed_uids_from_json(inp.allowed_uids_json)
    try:
        await create_project_with_environmental_cog_pipeline(
            ctx.request,
            ctx.settings,
            ctx.storage,
            project_id=inp.project_id,
            name=inp.name,
            description=inp.description,
            visibility_v=inp.visibility,
            uids=uids,
            upload_session_id=inp.upload_session_id,
            file=None,
            environmental_band_definitions=inp.environmental_band_definitions,
            infer_band_definitions=inp.infer_band_definitions,
        )
    except HTTPException:
        raise
    except Exception as e:
        wrap_pipeline_infra_errors(e)
