"""Internal routes for background job workers (not in OpenAPI)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from backend_api.deps.settings_dep import get_settings
from backend_api.job_runner import execute_job
from backend_api.job_worker_auth import verify_internal_job_caller
from backend_api.settings import Settings

router = APIRouter(prefix="/internal", include_in_schema=False)


class RunJobBody(BaseModel):
    job_id: str = Field(..., min_length=1)


@router.post("/jobs/run")
async def post_internal_run_job(
    request: Request,
    body: RunJobBody,
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, bool]:
    verify_internal_job_caller(request, settings)
    await execute_job(request, body.job_id)
    return {"ok": True}
