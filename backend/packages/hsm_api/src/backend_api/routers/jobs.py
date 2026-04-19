"""Admin job status (poll after 202 enqueue)."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from google.cloud import firestore
from pydantic import ValidationError

from backend_api.auth_deps import require_admin_claims
from backend_api.deps.settings_dep import get_settings
from backend_api.schemas_jobs import JobPollResponse
from hsm_core.catalog_collections import PROJECTS_COLLECTION_ID
from hsm_core.firestore_io import snapshot_to_document_dict
from hsm_core.jobs import get_job
from hsm_core.schemas_project import CatalogProject
from hsm_core.settings import Settings

router = APIRouter()

logger = logging.getLogger(__name__)


def _load_project_from_firestore(settings: Settings, project_id: str) -> CatalogProject | None:
    client = firestore.Client(project=settings.google_cloud_project)
    snap = client.collection(PROJECTS_COLLECTION_ID).document(project_id).get()
    if not snap.exists:
        return None
    try:
        return CatalogProject.model_validate(snapshot_to_document_dict(snap))
    except ValidationError:
        logger.exception("invalid CatalogProject in Firestore for job poll project_id=%s", project_id)
        return None


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
