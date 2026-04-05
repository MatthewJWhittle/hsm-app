"""Catalog project routes (read + admin write)."""

from __future__ import annotations

import json
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
from backend_api.cog_validation import CogValidationError
from backend_api.deps.catalog import get_object_storage, require_catalog_ready
from backend_api.env_background_sample import write_project_explainability_background_parquet
from backend_api.env_cog_bands import (
    band_definitions_for_upload_bytes,
    count_bands_in_path,
    default_band_definitions_from_path,
    parse_band_definitions_json,
    validate_band_definitions_match_raster,
)
from backend_api.project_manifest import resolve_env_cog_path_from_parts
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
from backend_api.schemas_project import CatalogProject, EnvironmentalBandDefinition
from backend_api.settings import Settings
from backend_api.storage import EXPLAINABILITY_BACKGROUND_FILENAME, ObjectStorage

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


@router.patch(
    "/projects/{project_id}/environmental-band-definitions",
    response_model=CatalogProject,
    tags=["admin"],
    responses=_ADMIN_RESPONSES,
    summary="Set environmental band definitions (names and display labels)",
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
    ``[{"index": 0, "name": "band_0", "label": "Elevation"}, ...]``.
    """
    existing = catalog.get_project(project_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="project not found")

    artifact_root = existing.driver_artifact_root
    cog_path = existing.driver_cog_path
    abs_path = resolve_env_cog_path_from_parts(artifact_root, cog_path)
    if not abs_path:
        raise HTTPException(
            status_code=422,
            detail="cannot set band definitions without an environmental COG uploaded",
        )
    if not Path(abs_path).is_file():
        raise HTTPException(
            status_code=422,
            detail="environmental COG not found on server; upload the file first",
        )

    def _count() -> int:
        return count_bands_in_path(abs_path)

    count = await run_in_threadpool(_count)
    try:
        validate_band_definitions_match_raster(count, definitions)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

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
        raise HTTPException(status_code=503, detail=f"could not save catalog: {e}") from e

    await reload_catalog_threaded(request)
    return project


@router.post(
    "/projects",
    response_model=CatalogProject,
    status_code=201,
    tags=["admin"],
    responses=_ADMIN_RESPONSES,
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
    environmental_band_definitions: Annotated[str | None, Form()] = None,
):
    """Create a project; environmental COG may be uploaded now or added via PUT (admin only)."""
    if not name.strip():
        raise HTTPException(status_code=422, detail="name is required")
    visibility_v = parse_visibility(visibility)
    try:
        uids = _parse_allowed_uids(allowed_uids)
    except (json.JSONDecodeError, ValueError) as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    project_id = str(uuid.uuid4())
    artifact_root: str | None = None
    cog_path: str | None = None
    band_defs: list[EnvironmentalBandDefinition] | None = None
    if file is not None:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=422, detail="empty file")
        if len(content) > settings.max_environmental_upload_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"file exceeds max size {settings.max_environmental_upload_bytes} bytes",
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

        try:

            def _defs() -> list[EnvironmentalBandDefinition]:
                return band_definitions_for_upload_bytes(
                    content, environmental_band_definitions
                )

            band_defs = await run_in_threadpool(_defs)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e

    explain_bg_path: str | None = None
    if band_defs and artifact_root and cog_path:
        try:

            def _bg() -> None:
                write_project_explainability_background_parquet(
                    storage,
                    project_id,
                    artifact_root,
                    cog_path,
                    band_defs,
                    settings.env_background_sample_rows,
                )

            await run_in_threadpool(_bg)
            explain_bg_path = EXPLAINABILITY_BACKGROUND_FILENAME
        except Exception as e:
            raise HTTPException(
                status_code=422,
                detail=f"could not build explainability background sample from COG: {e}",
            ) from e

    now = datetime.now(UTC).isoformat()

    project = CatalogProject(
        id=project_id,
        name=name.strip(),
        description=description.strip() if description else None,
        status="active",
        visibility=visibility_v,
        allowed_uids=uids,
        driver_artifact_root=artifact_root,
        driver_cog_path=cog_path,
        environmental_band_definitions=band_defs,
        explainability_background_path=explain_bg_path,
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
    environmental_band_definitions: Annotated[str | None, Form()] = None,
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
    new_band_defs: list[EnvironmentalBandDefinition] | None = (
        existing.environmental_band_definitions
    )

    if file is not None:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=422, detail="empty file")
        if len(content) > settings.max_environmental_upload_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"file exceeds max size {settings.max_environmental_upload_bytes} bytes",
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

        try:

            def _defs() -> list[EnvironmentalBandDefinition]:
                return band_definitions_for_upload_bytes(
                    content, environmental_band_definitions
                )

            new_band_defs = await run_in_threadpool(_defs)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e
    elif environmental_band_definitions is not None and environmental_band_definitions.strip():
        try:
            parsed = parse_band_definitions_json(environmental_band_definitions)
        except (json.JSONDecodeError, ValueError) as e:
            raise HTTPException(status_code=422, detail=str(e)) from e
        if parsed is None:
            new_band_defs = None
        else:
            abs_path = resolve_env_cog_path_from_parts(artifact_root, cog_path)
            if not abs_path:
                raise HTTPException(
                    status_code=422,
                    detail="cannot set band definitions without an environmental COG uploaded",
                )
            if not Path(abs_path).is_file():
                raise HTTPException(
                    status_code=422,
                    detail="environmental COG not found on server; upload the file first",
                )

            def _count() -> int:
                return count_bands_in_path(abs_path)

            count = await run_in_threadpool(_count)
            try:
                validate_band_definitions_match_raster(count, parsed)
            except ValueError as e:
                raise HTTPException(status_code=422, detail=str(e)) from e
            new_band_defs = parsed
    elif not existing.environmental_band_definitions:
        abs_path = resolve_env_cog_path_from_parts(artifact_root, cog_path)
        if abs_path and Path(abs_path).is_file():

            def _backfill() -> list[EnvironmentalBandDefinition]:
                return default_band_definitions_from_path(abs_path)

            try:
                new_band_defs = await run_in_threadpool(_backfill)
            except OSError:
                new_band_defs = None

    new_explain_bg_path = existing.explainability_background_path
    if (
        new_band_defs
        and artifact_root
        and cog_path
        and (file is not None or not existing.explainability_background_path)
    ):
        try:

            def _bg() -> None:
                write_project_explainability_background_parquet(
                    storage,
                    project_id,
                    artifact_root,
                    cog_path,
                    new_band_defs,
                    settings.env_background_sample_rows,
                )

            await run_in_threadpool(_bg)
            new_explain_bg_path = EXPLAINABILITY_BACKGROUND_FILENAME
        except Exception as e:
            raise HTTPException(
                status_code=422,
                detail=f"could not build explainability background sample from COG: {e}",
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
        driver_artifact_root=artifact_root,
        driver_cog_path=cog_path,
        environmental_band_definitions=new_band_defs,
        explainability_background_path=new_explain_bg_path,
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
