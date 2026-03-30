"""Catalog project routes (read + admin write)."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import (
    APIRouter,
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
from backend_api.cog_validation import CogValidationError
from backend_api.deps.catalog import get_object_storage, require_catalog_ready
from backend_api.deps.settings_dep import get_settings
from backend_api.deps.visibility_models import (
    filter_projects_for_viewer,
    get_project_visible_or_404,
)
from backend_api.routers.catalog_upload_utils import (
    reload_catalog_threaded,
    validate_cog_bytes_threaded,
)
from backend_api.routers.project_visibility_parse import (
    parse_status_optional,
    parse_visibility,
    parse_visibility_optional,
)
from backend_api.schemas_project import CatalogProject
from backend_api.settings import Settings
from backend_api.storage import ObjectStorage

router = APIRouter()

_ADMIN_RESPONSES: dict[int | str, dict[str, str]] = {
    status.HTTP_401_UNAUTHORIZED: {"description": "Missing or invalid bearer token"},
    status.HTTP_403_FORBIDDEN: {"description": "Valid token but admin claim not set"},
    status.HTTP_413_REQUEST_ENTITY_TOO_LARGE: {"description": "Upload exceeds max size"},
    status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Invalid COG/CRS or form data"},
    status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Storage or Firestore failure"},
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


@router.post(
    "/projects",
    response_model=CatalogProject,
    status_code=201,
    tags=["admin"],
    responses=_ADMIN_RESPONSES,
    summary="Create catalog project and upload shared environmental COG",
)
async def create_project(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    _claims: Annotated[dict, Depends(require_admin_claims)],
    storage: Annotated[ObjectStorage, Depends(get_object_storage)],
    name: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
    description: Annotated[str | None, Form()] = None,
    visibility: Annotated[str, Form()] = "public",
    allowed_uids: Annotated[str | None, Form()] = None,
):
    """Create a project and store the shared environmental COG (admin only)."""
    visibility_v = parse_visibility(visibility)
    try:
        uids = _parse_allowed_uids(allowed_uids)
    except (json.JSONDecodeError, ValueError) as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail="empty file")
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"file exceeds max size {settings.max_upload_bytes} bytes",
        )
    try:
        await validate_cog_bytes_threaded(content)
    except CogValidationError as e:
        raise HTTPException(status_code=422, detail=e.message) from e

    project_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()

    def _write() -> tuple[str, str]:
        return storage.write_project_driver_cog(project_id, content)

    try:
        artifact_root, cog_path = await run_in_threadpool(_write)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"could not store file: {e}") from e

    project = CatalogProject(
        id=project_id,
        name=name.strip(),
        description=description.strip() if description else None,
        status="active",
        visibility=visibility_v,
        allowed_uids=uids,
        driver_artifact_root=artifact_root,
        driver_cog_path=cog_path,
        created_at=now,
        updated_at=now,
    )

    def _persist() -> None:
        upsert_project(settings, project)

    try:
        await run_in_threadpool(_persist)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"could not save catalog: {e}") from e

    await reload_catalog_threaded(request)
    return project


@router.put(
    "/projects/{project_id}",
    response_model=CatalogProject,
    tags=["admin"],
    responses=_ADMIN_RESPONSES,
    summary="Update catalog project metadata and/or replace environmental COG",
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
):
    """Update project (admin only)."""
    existing = catalog.get_project(project_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="project not found")

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
        raise HTTPException(status_code=422, detail=str(e)) from e

    artifact_root = existing.driver_artifact_root
    cog_path = existing.driver_cog_path

    if file is not None:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=422, detail="empty file")
        if len(content) > settings.max_upload_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"file exceeds max size {settings.max_upload_bytes} bytes",
            )
        try:
            await validate_cog_bytes_threaded(content)
        except CogValidationError as e:
            raise HTTPException(status_code=422, detail=e.message) from e

        def _write() -> tuple[str, str]:
            return storage.write_project_driver_cog(project_id, content)

        try:
            artifact_root, cog_path = await run_in_threadpool(_write)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"could not store file: {e}") from e

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
        driver_artifact_root=artifact_root,
        driver_cog_path=cog_path,
        created_at=existing.created_at,
        updated_at=now,
    )

    def _persist() -> None:
        upsert_project(settings, project)

    try:
        await run_in_threadpool(_persist)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"could not save catalog: {e}") from e

    await reload_catalog_threaded(request)
    return project
