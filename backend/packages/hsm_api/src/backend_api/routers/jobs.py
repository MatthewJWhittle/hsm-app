"""Admin job status (poll after 202 enqueue)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from google.cloud import firestore

from backend_api.auth_deps import require_admin_claims
from backend_api.deps.settings_dep import get_settings
from backend_api.schemas_jobs import JobPollResponse
from backend_api.schemas_project import CatalogProject
from backend_api.settings import Settings
from hsm_core.jobs import get_job

router = APIRouter()


def _load_project_from_firestore(settings: Settings, project_id: str) -> CatalogProject | None:
    from backend_api.catalog_service import PROJECTS_COLLECTION_ID

    client = firestore.Client(project=settings.google_cloud_project)
    snap = client.collection(PROJECTS_COLLECTION_ID).document(project_id).get()
    if not snap.exists:
        return None
    return CatalogProject.model_validate(snap.to_dict())


@router.get(
    "/admin/jobs/{job_id}",
    response_model=JobPollResponse,
    tags=["admin"],
    summary="Poll background job status (admin)",
)
async def get_job_status(
    settings: Annotated[Settings, Depends(get_settings)],
    claims: Annotated[dict, Depends(require_admin_claims)],
    job_id: str,
):
    client = firestore.Client(project=settings.google_cloud_project)
    job = get_job(client, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")

    uid = claims.get("uid") or claims.get("user_id") or claims.get("sub")
    if job.created_by_uid and uid and job.created_by_uid != uid:
        raise HTTPException(status_code=403, detail="not allowed to view this job")

    project = None
    if (
        job.status == "succeeded"
        and job.project_id
        and job.kind == "explainability_background_sample"
    ):
        project = _load_project_from_firestore(settings, job.project_id)

    return JobPollResponse(
        job_id=job.job_id,
        status=job.status,
        kind=job.kind,
        project_id=job.project_id,
        error_code=job.error_code,
        error_message=job.error_message,
        project=project,
    )
