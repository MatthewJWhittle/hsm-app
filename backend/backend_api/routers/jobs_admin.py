"""Admin job status API."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from backend_api.auth_deps import require_admin_claims
from backend_api.deps.settings_dep import get_settings
from backend_api.jobs import get_job
from backend_api.schemas_job import Job
from backend_api.settings import Settings

router = APIRouter(tags=["admin"])


@router.get(
    "/jobs/{job_id}",
    response_model=Job,
    summary="Get background job status",
)
async def get_job_status(
    job_id: str,
    settings: Annotated[Settings, Depends(get_settings)],
    _claims: Annotated[dict, Depends(require_admin_claims)],
) -> Job:
    job = get_job(settings, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return job
