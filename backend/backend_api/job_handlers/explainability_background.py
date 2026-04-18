"""Handler: regenerate explainability background Parquet."""

from __future__ import annotations

from backend_api.explainability_background_pipeline import (
    regenerate_explainability_background_pipeline,
)
from backend_api.job_handlers.context import JobRunContext
from backend_api.schemas_job import JobInputExplainabilityBackgroundRegenerate


async def run(ctx: JobRunContext, inp: JobInputExplainabilityBackgroundRegenerate) -> None:
    await regenerate_explainability_background_pipeline(
        ctx.request,
        ctx.settings,
        ctx.storage,
        ctx.catalog,
        inp.project_id,
        inp.sample_rows,
    )
