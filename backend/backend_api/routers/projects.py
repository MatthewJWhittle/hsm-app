"""Catalog project routes (read + admin write)."""

from __future__ import annotations

import json
import logging
import os
import uuid
from pathlib import Path
from datetime import UTC, datetime
from typing import Annotated

from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from starlette.concurrency import run_in_threadpool

from backend_api.auth_deps import optional_id_token_claims, require_admin_claims
from backend_api.catalog_service import CatalogService
from backend_api.catalog_write import upsert_project
from backend_api.api_errors import validation_error
from backend_api.cog_validation import CogValidationError
from backend_api.deps.catalog import get_object_storage, require_catalog_ready
from backend_api.env_cog_bands import (
    apply_band_label_updates,
    band_definitions_for_upload_path,
    count_bands_in_path,
    default_band_definitions_from_path,
    infer_band_definitions_from_form,
    parse_band_definitions_json,
    validate_band_definitions_match_raster,
)
from backend_api.env_cog_replace_pipeline import replace_project_environmental_cogs_pipeline
from backend_api.project_create_pipeline import create_project_with_environmental_cog_pipeline
from backend_api.env_cog_explainability_preflight import (
    require_catalog_project_env_cog_for_explainability,
)
from backend_api.explainability_background_pipeline import (
    regenerate_explainability_background_pipeline,
)
from backend_api.job_async_policy import (
    should_async_explainability_background,
    should_async_project_create_with_env,
    should_async_replace_environmental_cogs,
)
from backend_api.job_http import (
    accepted_job_202_response,
    admin_created_by_uid,
    enqueue_and_schedule_job,
)
from backend_api.deps.settings_dep import get_settings
from backend_api.deps.visibility_models import (
    filter_projects_for_viewer,
    get_project_visible_or_404,
)
from backend_api.routers.catalog_upload_utils import (
    reload_catalog_threaded,
    validate_cog_path_threaded,
)
from backend_api.routers.project_visibility_parse import (
    parse_status_optional,
    parse_visibility,
    parse_visibility_optional,
)
from backend_api.project_manifest import resolve_env_cog_path_from_parts
from backend_api.schemas_job import JobKind
from backend_api.schemas_project import (
    BandLabelPatch,
    CatalogProject,
    EnvironmentalBandDefinition,
    RegenerateExplainabilityBackgroundBody,
)
from backend_api.settings import Settings
from backend_api.storage import ObjectStorage
from backend_api.schemas_upload import UploadSession
from backend_api.upload_session_error_context import upload_error_context
from backend_api.upload_session_ingest import (
    best_effort_fail,
    best_effort_mark,
    download_upload_session_to_tempfile,
    write_upload_file_to_tempfile,
)
from backend_api.validation_http import service_unavailable_http, validation_http_exception

router = APIRouter()
logger = logging.getLogger(__name__)

_ADMIN_RESPONSES: dict[int | str, dict[str, str]] = {
    status.HTTP_401_UNAUTHORIZED: {"description": "Missing or invalid bearer token"},
    status.HTTP_403_FORBIDDEN: {"description": "Valid token but admin claim not set"},
    status.HTTP_413_REQUEST_ENTITY_TOO_LARGE: {"description": "Upload exceeds max size"},
    status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Invalid COG/CRS or form data"},
    status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Storage or Firestore failure"},
}

_ADMIN_POST_PROJECTS_RESPONSES: dict[int | str, dict[str, str]] = {
    **_ADMIN_RESPONSES,
    status.HTTP_202_ACCEPTED: {
        "description": "Background job enqueued (upload session + job queue enabled)",
    },
}


def _parse_allowed_uids(raw: str | None) -> list[str]:
    if not raw or not raw.strip():
        return []
    raw = raw.strip()
    if raw.startswith("["):
        data = json.loads(raw)
        if not isinstance(data, list):
            raise ValueError("allowed_uids must be a JSON array of strings")
        return [str(x) for x in data]
    return [s.strip() for s in raw.split(",") if s.strip()]


@router.get("/projects", response_model=list[CatalogProject], tags=["catalog"])
async def list_projects(
    catalog: Annotated[CatalogService, Depends(require_catalog_ready)],
    claims: Annotated[dict | None, Depends(optional_id_token_claims)],
):
    """List catalog projects visible to the caller (public + private if allowed)."""
    return filter_projects_for_viewer(catalog, claims)


@router.get("/projects/{project_id}", response_model=CatalogProject, tags=["catalog"])
async def get_project(
    project: Annotated[CatalogProject, Depends(get_project_visible_or_404)],
):
    """Return one catalog project if visible to the caller."""
    return project


@router.patch(
    "/projects/{project_id}/environmental-band-definitions",
    response_model=CatalogProject,
    tags=["admin"],
    responses=_ADMIN_RESPONSES,
    summary="Set environmental band definitions (name, display label, description)",
)
async def patch_environmental_band_definitions(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    _claims: Annotated[dict, Depends(require_admin_claims)],
    catalog: Annotated[CatalogService, Depends(require_catalog_ready)],
    project_id: str,
    definitions: Annotated[list[EnvironmentalBandDefinition], Body(...)],
):
    """
    Replace the project's band manifest. Must list every band index ``0 .. n-1`` matching
    the on-disk environmental COG. Send JSON array, e.g.
    ``[{"index": 0, "name": "band_0", "label": "Elevation", "description": "..."}, ...]``.
    """
    existing = catalog.get_project(project_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="project not found")

    artifact_root = existing.driver_artifact_root
    cog_path = existing.driver_cog_path
    abs_path = resolve_env_cog_path_from_parts(artifact_root, cog_path)
    if not abs_path:
        raise validation_http_exception(
            "ENV_COG_REQUIRED",
            "cannot set band definitions without an environmental COG uploaded",
        )
    if not Path(abs_path).is_file():
        raise validation_http_exception(
            "ENV_COG_NOT_ON_DISK",
            "environmental COG not found on server; upload the file first",
        )

    def _count() -> int:
        return count_bands_in_path(abs_path)

    count = await run_in_threadpool(_count)
    try:
        validate_band_definitions_match_raster(count, definitions)
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail=validation_error("BAND_DEFINITION_INVALID", str(e)),
        ) from e

    now = datetime.now(UTC).isoformat()
    project = existing.model_copy(
        update={
            "environmental_band_definitions": definitions,
            "updated_at": now,
        }
    )

    def _persist() -> None:
        upsert_project(settings, project)

    try:
        await run_in_threadpool(_persist)
    except Exception as e:
        raise service_unavailable_http("CATALOG_SAVE_FAILED", f"could not save catalog: {e}") from e

    await reload_catalog_threaded(request)
    return project


@router.patch(
    "/projects/{project_id}/environmental-band-definitions/labels",
    response_model=CatalogProject,
    tags=["admin"],
    responses=_ADMIN_RESPONSES,
    summary="Patch display labels and descriptions for one or more bands (by machine name)",
)
async def patch_environmental_band_definition_labels(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    _claims: Annotated[dict, Depends(require_admin_claims)],
    catalog: Annotated[CatalogService, Depends(require_catalog_ready)],
    project_id: str,
    updates: Annotated[dict[str, BandLabelPatch], Body(...)],
):
    """
    Partial update: request body is a JSON object mapping each band's machine ``name`` to fields to set.

    Example::

        {
          "ceh_landcover_arable": {
            "name": "Arable",
            "description": "CEH Land Cover Map; arable agriculture."
          },
          "terrain_dtm": { "label": "Ground elevation", "description": "..." }
        }

    Use ``label`` or ``name`` for the display title (``label`` wins if both are present).
    Omitted bands are unchanged. Unknown band names return **422**.
    """
    existing = catalog.get_project(project_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="project not found")

    defs = existing.environmental_band_definitions
    if not defs:
        raise validation_http_exception(
            "BAND_DEFINITIONS_MISSING",
            "project has no environmental band definitions; upload the environmental COG first",
        )

    artifact_root = existing.driver_artifact_root
    cog_path = existing.driver_cog_path
    abs_path = resolve_env_cog_path_from_parts(artifact_root, cog_path)
    if not abs_path:
        raise validation_http_exception(
            "ENV_COG_REQUIRED",
            "cannot patch band labels without an environmental COG on the project",
        )
    if not Path(abs_path).is_file():
        raise validation_http_exception(
            "ENV_COG_NOT_ON_DISK",
            "environmental COG not found on server; upload the file first",
        )

    try:
        merged = apply_band_label_updates(defs, updates)
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail=validation_error("BAND_LABEL_PATCH_INVALID", str(e)),
        ) from e

    count = await run_in_threadpool(lambda: count_bands_in_path(abs_path))
    try:
        validate_band_definitions_match_raster(count, merged)
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail=validation_error("BAND_DEFINITION_INVALID", str(e)),
        ) from e

    now = datetime.now(UTC).isoformat()
    project = existing.model_copy(
        update={
            "environmental_band_definitions": merged,
            "updated_at": now,
        }
    )

    def _persist() -> None:
        upsert_project(settings, project)

    try:
        await run_in_threadpool(_persist)
    except Exception as e:
        raise service_unavailable_http("CATALOG_SAVE_FAILED", f"could not save catalog: {e}") from e

    await reload_catalog_threaded(request)
    return project


_ADMIN_EXPLAINABILITY_BG_RESPONSES: dict[int | str, dict[str, str]] = {
    **_ADMIN_RESPONSES,
    status.HTTP_202_ACCEPTED: {
        "description": "Background job enqueued when job queue is enabled",
    },
}


@router.post(
    "/projects/{project_id}/explainability-background-sample",
    response_model=CatalogProject,
    tags=["admin"],
    responses=_ADMIN_EXPLAINABILITY_BG_RESPONSES,
    summary="Regenerate SHAP explainability background Parquet from the environmental COG",
)
async def post_explainability_background_sample(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    _claims: Annotated[dict, Depends(require_admin_claims)],
    storage: Annotated[ObjectStorage, Depends(get_object_storage)],
    catalog: Annotated[CatalogService, Depends(require_catalog_ready)],
    project_id: str,
    body: Annotated[
        RegenerateExplainabilityBackgroundBody,
        Body(),
    ] = RegenerateExplainabilityBackgroundBody(),
):
    """
    Re-sample random pixels from the project's environmental COG into
    ``explainability_background.parquet`` (same path as on upload).

    Does not require re-uploading the COG. Omit ``sample_rows`` to use
    ``ENV_BACKGROUND_SAMPLE_ROWS``.
    """
    if should_async_explainability_background(settings):
        require_catalog_project_env_cog_for_explainability(catalog, project_id)
        job = enqueue_and_schedule_job(
            settings,
            kind=JobKind.EXPLAINABILITY_BACKGROUND_REGENERATE,
            input={
                "project_id": project_id,
                "sample_rows": body.sample_rows,
            },
            created_by_uid=admin_created_by_uid(_claims),
        )
        return accepted_job_202_response(job, project_id=project_id)

    return await regenerate_explainability_background_pipeline(
        request,
        settings,
        storage,
        catalog,
        project_id,
        body.sample_rows,
    )


@router.post(
    "/projects",
    response_model=CatalogProject,
    status_code=201,
    tags=["admin"],
    responses=_ADMIN_POST_PROJECTS_RESPONSES,
    summary="Create catalog project (optional shared environmental COG upload)",
)
async def create_project(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    _claims: Annotated[dict, Depends(require_admin_claims)],
    storage: Annotated[ObjectStorage, Depends(get_object_storage)],
    name: Annotated[str, Form()],
    file: Annotated[UploadFile | None, File()] = None,
    description: Annotated[str | None, Form()] = None,
    visibility: Annotated[str, Form()] = "public",
    allowed_uids: Annotated[str | None, Form()] = None,
    upload_session_id: Annotated[str | None, Form()] = None,
    environmental_band_definitions: Annotated[str | None, Form()] = None,
    infer_band_definitions: Annotated[str | None, Form()] = None,
):
    """Create a project; environmental COG may be uploaded now or added via PUT (admin only).

    When uploading an environmental COG, omit ``environmental_band_definitions`` to infer
    machine names from GDAL band descriptions (slugified; collisions resolved). Set form field
    ``infer_band_definitions`` to ``false`` to require an explicit JSON array instead.
    """
    if not name.strip():
        raise validation_http_exception("MISSING_FIELD", "name is required")
    visibility_v = parse_visibility(visibility)
    try:
        uids = _parse_allowed_uids(allowed_uids)
    except (json.JSONDecodeError, ValueError) as e:
        raise HTTPException(
            status_code=422,
            detail=validation_error("ALLOWED_UIDS_INVALID", str(e)),
        ) from e

    project_id = str(uuid.uuid4())
    logger.info(
        "project_create_start project_id=%s has_multipart=%s has_session=%s",
        project_id,
        file is not None,
        bool(upload_session_id),
    )
    if file is not None and upload_session_id:
        raise validation_http_exception(
            "UPLOAD_CONFLICT",
            "provide either multipart file or upload_session_id, not both",
        )

    if file is None and upload_session_id is None:
        now = datetime.now(UTC).isoformat()
        project = CatalogProject(
            id=project_id,
            name=name.strip(),
            description=description.strip() if description else None,
            status="active",
            visibility=visibility_v,
            allowed_uids=uids,
            created_at=now,
            updated_at=now,
        )

        def _persist_empty() -> None:
            upsert_project(settings, project)

        try:
            await run_in_threadpool(_persist_empty)
            logger.info("project_create_catalog_save_ok project_id=%s", project_id)
        except Exception as e:
            raise service_unavailable_http("CATALOG_SAVE_FAILED", f"could not save catalog: {e}") from e
        await reload_catalog_threaded(request)
        return project

    if should_async_project_create_with_env(
        settings,
        has_multipart_file=file is not None,
        upload_session_id=upload_session_id,
    ):
        job = enqueue_and_schedule_job(
            settings,
            kind=JobKind.PROJECT_CREATE_WITH_ENV_UPLOAD,
            input={
                "project_id": project_id,
                "name": name.strip(),
                "description": description.strip() if description else None,
                "visibility": visibility_v,
                "allowed_uids_json": json.dumps(uids),
                "upload_session_id": upload_session_id,
                "environmental_band_definitions": environmental_band_definitions,
                "infer_band_definitions": infer_band_definitions,
            },
            created_by_uid=admin_created_by_uid(_claims),
        )
        return accepted_job_202_response(job, project_id=project_id)

    return await create_project_with_environmental_cog_pipeline(
        request,
        settings,
        storage,
        project_id=project_id,
        name=name.strip(),
        description=description.strip() if description else None,
        visibility_v=visibility_v,
        uids=uids,
        upload_session_id=upload_session_id,
        file=file,
        environmental_band_definitions=environmental_band_definitions,
        infer_band_definitions=infer_band_definitions,
    )


@router.patch(
    "/projects/{project_id}",
    response_model=CatalogProject,
    tags=["admin"],
    responses=_ADMIN_RESPONSES,
    summary="Update catalog project metadata only",
)
async def update_project(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    _claims: Annotated[dict, Depends(require_admin_claims)],
    storage: Annotated[ObjectStorage, Depends(get_object_storage)],
    catalog: Annotated[CatalogService, Depends(require_catalog_ready)],
    project_id: str,
    name: Annotated[str | None, Form()] = None,
    description: Annotated[str | None, Form()] = None,
    status: Annotated[str | None, Form()] = None,
    visibility: Annotated[str | None, Form()] = None,
    allowed_uids: Annotated[str | None, Form()] = None,
    file: Annotated[UploadFile | None, File()] = None,
    upload_session_id: Annotated[str | None, Form()] = None,
    environmental_band_definitions: Annotated[str | None, Form()] = None,
    infer_band_definitions: Annotated[str | None, Form()] = None,
):
    """Update project metadata only (admin only)."""
    existing = catalog.get_project(project_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="project not found")
    if (
        file is not None
        or upload_session_id is not None
        or environmental_band_definitions is not None
        or infer_band_definitions is not None
    ):
        raise validation_http_exception(
            "ENV_COG_REPLACE_ROUTE_REQUIRED",
            "metadata updates do not accept environmental COG upload fields; use POST /projects/{project_id}/environmental-cogs",
        )

    new_status = (
        parse_status_optional(status) if status is not None else existing.status
    )
    new_visibility = (
        parse_visibility_optional(visibility)
        if visibility is not None
        else existing.visibility
    )

    try:
        new_uids = (
            _parse_allowed_uids(allowed_uids) if allowed_uids is not None else None
        )
    except (json.JSONDecodeError, ValueError) as e:
        raise HTTPException(
            status_code=422,
            detail=validation_error("ALLOWED_UIDS_INVALID", str(e)),
        ) from e

    now = datetime.now(UTC).isoformat()
    project = CatalogProject(
        id=project_id,
        name=name.strip() if name is not None else existing.name,
        description=(
            description.strip() if description is not None else existing.description
        ),
        status=new_status,
        visibility=new_visibility,
        allowed_uids=new_uids if new_uids is not None else existing.allowed_uids,
        driver_artifact_root=existing.driver_artifact_root,
        driver_cog_path=existing.driver_cog_path,
        environmental_band_definitions=existing.environmental_band_definitions,
        band_inference_notes=existing.band_inference_notes,
        explainability_background_path=existing.explainability_background_path,
        explainability_background_sample_rows=existing.explainability_background_sample_rows,
        explainability_background_generated_at=existing.explainability_background_generated_at,
        created_at=existing.created_at,
        updated_at=now,
    )

    def _persist() -> None:
        upsert_project(settings, project)

    try:
        await run_in_threadpool(_persist)
    except Exception as e:
        raise service_unavailable_http("CATALOG_SAVE_FAILED", f"could not save catalog: {e}") from e

    await reload_catalog_threaded(request)
    return project


@router.post(
    "/projects/{project_id}/environmental-cogs",
    tags=["admin"],
    responses={
        **_ADMIN_RESPONSES,
        202: {"description": "Background job enqueued (upload session + job queue enabled)"},
    },
    summary="Replace project environmental COG via multipart file or upload session",
)
async def replace_project_environmental_cogs(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    _claims: Annotated[dict, Depends(require_admin_claims)],
    storage: Annotated[ObjectStorage, Depends(get_object_storage)],
    catalog: Annotated[CatalogService, Depends(require_catalog_ready)],
    project_id: str,
    file: Annotated[UploadFile | None, File()] = None,
    upload_session_id: Annotated[str | None, Form()] = None,
    environmental_band_definitions: Annotated[str | None, Form()] = None,
    infer_band_definitions: Annotated[str | None, Form()] = None,
):
    """Create/replace a project's active environmental COG (admin only).

    When ``JOB_QUEUE_BACKEND`` is not ``disabled`` and the client sends only
    ``upload_session_id`` (no multipart file), the API returns **202** and processes
    the replace in a background worker (Cloud Tasks).
    """
    existing = catalog.get_project(project_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="project not found")

    if file is not None and upload_session_id:
        raise validation_http_exception(
            "UPLOAD_CONFLICT",
            "provide either multipart file or upload_session_id, not both",
        )
    if file is None and upload_session_id is None:
        raise validation_http_exception(
            "MISSING_UPLOAD",
            "provide multipart file or upload_session_id",
        )

    if should_async_replace_environmental_cogs(
        settings,
        has_multipart_file=file is not None,
        upload_session_id=upload_session_id,
    ):
        job = enqueue_and_schedule_job(
            settings,
            kind=JobKind.ENVIRONMENTAL_COG_REPLACE,
            input={
                "project_id": project_id,
                "upload_session_id": upload_session_id,
                "environmental_band_definitions": environmental_band_definitions,
                "infer_band_definitions": infer_band_definitions,
            },
            created_by_uid=admin_created_by_uid(_claims),
        )
        return accepted_job_202_response(job)

    return await replace_project_environmental_cogs_pipeline(
        request,
        settings,
        storage,
        catalog,
        project_id,
        file,
        upload_session_id,
        environmental_band_definitions,
        infer_band_definitions,
    )
