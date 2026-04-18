"""Handler: regenerate explainability background Parquet.

Canonical implementation: :func:`backend_api.explainability_background_pipeline.regenerate_explainability_background_pipeline`.
"""

from __future__ import annotations

from fastapi import HTTPException

from backend_api.explainability_background_pipeline import (
    regenerate_explainability_background_pipeline,
)
from backend_api.job_errors import wrap_pipeline_infra_errors
from backend_api.job_handlers.context import JobRunContext
from backend_api.schemas_job import JobInputExplainabilityBackgroundRegenerate


async def run(ctx: JobRunContext, inp: JobInputExplainabilityBackgroundRegenerate) -> None:
    try:
        await regenerate_explainability_background_pipeline(
            ctx.request,
            ctx.settings,
            ctx.storage,
            ctx.catalog,
            inp.project_id,
            inp.sample_rows,
        )
    except HTTPException:
        raise
    except Exception as e:
        wrap_pipeline_infra_errors(e)
