"""Handler: replace project environmental COG (upload session)."""

from __future__ import annotations

from backend_api.env_cog_replace_pipeline import replace_project_environmental_cogs_pipeline
from backend_api.job_handlers.context import JobRunContext
from backend_api.schemas_job import JobInputEnvironmentalCogReplace


async def run(ctx: JobRunContext, inp: JobInputEnvironmentalCogReplace) -> None:
    await replace_project_environmental_cogs_pipeline(
        ctx.request,
        ctx.settings,
        ctx.storage,
        ctx.catalog,
        inp.project_id,
        None,
        inp.upload_session_id,
        inp.environmental_band_definitions,
        inp.infer_band_definitions,
    )
