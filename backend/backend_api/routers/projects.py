"""Catalog project routes (read + admin write)."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from datetime import UTC, datetime
from typing import Annotated

from google.cloud import storage
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
from backend_api.env_background_sample import write_project_explainability_background_parquet
from backend_api.env_cog_bands import (
    apply_band_label_updates,
    band_definitions_for_upload_bytes,
    count_bands_in_path,
    default_band_definitions_from_path,
    parse_band_definitions_json,
    validate_band_definitions_match_raster,
)
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
from backend_api.project_manifest import resolve_env_cog_path_from_parts
from backend_api.schemas_project import (
    BandLabelPatch,
    CatalogProject,
    EnvironmentalBandDefinition,
    RegenerateExplainabilityBackgroundBody,
)
from backend_api.settings import Settings
from backend_api.storage import EXPLAINABILITY_BACKGROUND_FILENAME, ObjectStorage
from backend_api.upload_sessions import get_upload_session, upsert_upload_session
from backend_api.schemas_upload import UploadSession

router = APIRouter()

_ADMIN_RESPONSES: dict[int | str, dict[str, str]] = {
    status.HTTP_401_UNAUTHORIZED: {"description": "Missing or invalid bearer token"},
    status.HTTP_403_FORBIDDEN: {"description": "Valid token but admin claim not set"},
    status.HTTP_413_REQUEST_ENTITY_TOO_LARGE: {"description": "Upload exceeds max size"},
    status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Invalid COG/CRS or form data"},
    status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Storage or Firestore failure"},
}


def _proj_422(
    code: str, message: str, *, context: dict | None = None
) -> HTTPException:
    """422 with the same structured ``detail`` shape as admin model routes."""
    return HTTPException(
        status_code=422, detail=validation_error(code, message, context=context)
    )


def _proj_503(code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=503, detail=validation_error(code, message)
    )


def _infer_band_definitions_from_form(raw: str | None) -> bool:
    """When omitted, infer band names from the raster. Use ``false``/``0``/``no`` to require JSON."""
    if raw is None or not str(raw).strip():
        return True
    v = str(raw).strip().lower()
    if v in ("0", "false", "no"):
        return False
    return True


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


def _download_upload_session_bytes(
    settings: Settings, upload_session_id: str
) -> tuple[bytes, UploadSession]:
    """Download uploaded object bytes from a completed upload session."""
    session = get_upload_session(settings, upload_session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="upload session not found")
    if session.status not in ("uploaded", "validating", "deriving", "ready"):
        raise HTTPException(
            status_code=409,
            detail=validation_error(
                "UPLOAD_NOT_READY",
                f"upload session status {session.status!r} is not ready for project create",
            ),
        )
    if not settings.gcs_bucket or session.gcs_bucket != settings.gcs_bucket:
        raise HTTPException(
            status_code=422,
            detail=validation_error(
                "UPLOAD_BUCKET_MISMATCH",
                "upload session bucket does not match configured API bucket",
            ),
        )
    client = storage.Client()
    bucket = client.bucket(session.gcs_bucket)
    blob = bucket.blob(session.object_path)
    if not blob.exists():
        raise HTTPException(
            status_code=422,
            detail=validation_error(
                "UPLOAD_OBJECT_MISSING",
                "upload object not found in storage",
            ),
        )
    return blob.download_as_bytes(), session


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
        raise _proj_422(
            "ENV_COG_REQUIRED",
            "cannot set band definitions without an environmental COG uploaded",
        )
    if not Path(abs_path).is_file():
        raise _proj_422(
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
        raise _proj_503("CATALOG_SAVE_FAILED", f"could not save catalog: {e}") from e

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
        raise _proj_422(
            "BAND_DEFINITIONS_MISSING",
            "project has no environmental band definitions; upload the environmental COG first",
        )

    artifact_root = existing.driver_artifact_root
    cog_path = existing.driver_cog_path
    abs_path = resolve_env_cog_path_from_parts(artifact_root, cog_path)
    if not abs_path:
        raise _proj_422(
            "ENV_COG_REQUIRED",
            "cannot patch band labels without an environmental COG on the project",
        )
    if not Path(abs_path).is_file():
        raise _proj_422(
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
        raise _proj_503("CATALOG_SAVE_FAILED", f"could not save catalog: {e}") from e

    await reload_catalog_threaded(request)
    return project


def _environmental_cog_readable_for_sampling(abs_path: str) -> bool:
    """Local files must exist on disk; ``gs://`` URIs are assumed present after upload."""
    if abs_path.startswith("gs://"):
        return True
    return Path(abs_path).is_file()


@router.post(
    "/projects/{project_id}/explainability-background-sample",
    response_model=CatalogProject,
    tags=["admin"],
    responses=_ADMIN_RESPONSES,
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
    existing = catalog.get_project(project_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="project not found")

    artifact_root = existing.driver_artifact_root
    cog_path = existing.driver_cog_path
    band_defs = existing.environmental_band_definitions

    if not artifact_root or not cog_path:
        raise _proj_422(
            "ENV_COG_REQUIRED",
            "project has no environmental COG; upload one first",
        )
    if not band_defs:
        raise _proj_422(
            "BAND_DEFINITIONS_MISSING",
            "project has no environmental band definitions; save band names first",
        )

    abs_path = resolve_env_cog_path_from_parts(artifact_root, cog_path)
    if not abs_path:
        raise _proj_422(
            "ENV_COG_PATH_INVALID",
            "cannot resolve environmental COG path",
        )
    if not _environmental_cog_readable_for_sampling(abs_path):
        raise _proj_422(
            "ENV_COG_NOT_ON_DISK",
            "environmental COG not found on server",
        )

    n_samples = (
        body.sample_rows
        if body.sample_rows is not None
        else settings.env_background_sample_rows
    )

    def _bg() -> None:
        write_project_explainability_background_parquet(
            storage,
            project_id,
            artifact_root,
            cog_path,
            band_defs,
            n_samples,
        )

    try:
        await run_in_threadpool(_bg)
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=validation_error(
                "EXPLAINABILITY_BACKGROUND_FAILED",
                "could not build explainability background sample from COG",
                context={"cause": str(e)},
            ),
        ) from e

    now = datetime.now(UTC).isoformat()
    project = existing.model_copy(
        update={
            "explainability_background_path": EXPLAINABILITY_BACKGROUND_FILENAME,
            "explainability_background_sample_rows": n_samples,
            "explainability_background_generated_at": now,
            "updated_at": now,
        }
    )

    def _persist() -> None:
        upsert_project(settings, project)

    try:
        await run_in_threadpool(_persist)
    except Exception as e:
        raise _proj_503("CATALOG_SAVE_FAILED", f"could not save catalog: {e}") from e

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
        raise _proj_422("MISSING_FIELD", "name is required")
    visibility_v = parse_visibility(visibility)
    try:
        uids = _parse_allowed_uids(allowed_uids)
    except (json.JSONDecodeError, ValueError) as e:
        raise HTTPException(
            status_code=422,
            detail=validation_error("ALLOWED_UIDS_INVALID", str(e)),
        ) from e

    project_id = str(uuid.uuid4())
    artifact_root: str | None = None
    cog_path: str | None = None
    band_defs: list[EnvironmentalBandDefinition] | None = None
    inference_notes: list[str] | None = None
    if file is not None and upload_session_id:
        raise _proj_422(
            "UPLOAD_CONFLICT",
            "provide either multipart file or upload_session_id, not both",
        )
    uploaded_session = None
    if upload_session_id:
        content, uploaded_session = await run_in_threadpool(
            _download_upload_session_bytes,
            settings,
            upload_session_id,
        )
    elif file is not None:
        content = await file.read()
    else:
        content = None

    if content is not None:
        if not content:
            raise _proj_422("EMPTY_FILE", "empty file")
        if len(content) > settings.max_environmental_upload_bytes:
            raise HTTPException(
                status_code=413,
                detail=validation_error(
                    "UPLOAD_TOO_LARGE",
                    f"file exceeds max size {settings.max_environmental_upload_bytes} bytes",
                    context={"max_bytes": settings.max_environmental_upload_bytes},
                ),
            )
        try:
            await validate_cog_bytes_threaded(content)
        except CogValidationError as e:
            raise HTTPException(
                status_code=422,
                detail=validation_error(e.code, e.message, context=e.context or None),
            ) from e

        def _write() -> tuple[str, str]:
            return storage.write_project_driver_cog(project_id, content)

        try:
            artifact_root, cog_path = await run_in_threadpool(_write)
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=validation_error("STORAGE_LAYOUT_INVALID", str(e)),
            ) from e
        except Exception as e:
            raise _proj_503("STORAGE_WRITE_FAILED", f"could not store file: {e}") from e

        try:

            def _defs() -> tuple[list[EnvironmentalBandDefinition], list[str]]:
                return band_definitions_for_upload_bytes(
                    content,
                    environmental_band_definitions,
                    infer_band_definitions=_infer_band_definitions_from_form(
                        infer_band_definitions
                    ),
                )

            band_defs, infer_notes = await run_in_threadpool(_defs)
            inference_notes = infer_notes if infer_notes else None
        except ValueError as e:
            raise HTTPException(
                status_code=422,
                detail=validation_error("BAND_DEFINITIONS", str(e)),
            ) from e
        if uploaded_session is not None and uploaded_session.status != "ready":
            completed = uploaded_session.model_copy(
                update={
                    "status": "ready",
                    "stage": "done",
                    "updated_at": datetime.now(UTC).isoformat(),
                    "error_code": None,
                    "error_message": None,
                    "error_stage": None,
                }
            )
            try:
                await run_in_threadpool(upsert_upload_session, settings, completed)
            except Exception:
                # Project create succeeded; keep request successful even if session metadata lags.
                pass

    explain_bg_path: str | None = None
    explain_bg_rows: int | None = None
    explain_bg_at: str | None = None
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
            explain_bg_rows = settings.env_background_sample_rows
        except Exception as e:
            raise HTTPException(
                status_code=422,
                detail=validation_error(
                    "EXPLAINABILITY_BACKGROUND_FAILED",
                    "could not build explainability background sample from COG",
                    context={"cause": str(e)},
                ),
            ) from e

    now = datetime.now(UTC).isoformat()
    if explain_bg_path:
        explain_bg_at = now

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
        band_inference_notes=inference_notes,
        explainability_background_path=explain_bg_path,
        explainability_background_sample_rows=explain_bg_rows,
        explainability_background_generated_at=explain_bg_at,
        created_at=now,
        updated_at=now,
    )

    def _persist() -> None:
        upsert_project(settings, project)

    try:
        await run_in_threadpool(_persist)
    except Exception as e:
        raise _proj_503("CATALOG_SAVE_FAILED", f"could not save catalog: {e}") from e

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
    infer_band_definitions: Annotated[str | None, Form()] = None,
):
    """Update project (admin only).

    When replacing the environmental COG, band definitions can be omitted to infer from the
    file (see ``infer_band_definitions`` on ``POST /projects``).
    """
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
        raise HTTPException(
            status_code=422,
            detail=validation_error("ALLOWED_UIDS_INVALID", str(e)),
        ) from e

    artifact_root = existing.driver_artifact_root
    cog_path = existing.driver_cog_path
    new_band_defs: list[EnvironmentalBandDefinition] | None = (
        existing.environmental_band_definitions
    )
    inference_notes: list[str] | None = None

    if file is not None:
        content = await file.read()
        if not content:
            raise _proj_422("EMPTY_FILE", "empty file")
        if len(content) > settings.max_environmental_upload_bytes:
            raise HTTPException(
                status_code=413,
                detail=validation_error(
                    "UPLOAD_TOO_LARGE",
                    f"file exceeds max size {settings.max_environmental_upload_bytes} bytes",
                    context={"max_bytes": settings.max_environmental_upload_bytes},
                ),
            )
        try:
            await validate_cog_bytes_threaded(content)
        except CogValidationError as e:
            raise HTTPException(
                status_code=422,
                detail=validation_error(e.code, e.message, context=e.context or None),
            ) from e

        def _write() -> tuple[str, str]:
            return storage.write_project_driver_cog(project_id, content)

        try:
            artifact_root, cog_path = await run_in_threadpool(_write)
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=validation_error("STORAGE_LAYOUT_INVALID", str(e)),
            ) from e
        except Exception as e:
            raise _proj_503("STORAGE_WRITE_FAILED", f"could not store file: {e}") from e

        try:

            def _defs() -> tuple[list[EnvironmentalBandDefinition], list[str]]:
                return band_definitions_for_upload_bytes(
                    content,
                    environmental_band_definitions,
                    infer_band_definitions=_infer_band_definitions_from_form(
                        infer_band_definitions
                    ),
                )

            new_band_defs, infer_notes = await run_in_threadpool(_defs)
            inference_notes = infer_notes if infer_notes else None
        except ValueError as e:
            raise HTTPException(
                status_code=422,
                detail=validation_error("BAND_DEFINITIONS", str(e)),
            ) from e
    elif environmental_band_definitions is not None and environmental_band_definitions.strip():
        try:
            parsed = parse_band_definitions_json(environmental_band_definitions)
        except (json.JSONDecodeError, ValueError) as e:
            raise HTTPException(
                status_code=422,
                detail=validation_error("BAND_DEFINITION_JSON_INVALID", str(e)),
            ) from e
        if parsed is None:
            new_band_defs = None
        else:
            abs_path = resolve_env_cog_path_from_parts(artifact_root, cog_path)
            if not abs_path:
                raise _proj_422(
                    "ENV_COG_REQUIRED",
                    "cannot set band definitions without an environmental COG uploaded",
                )
            if not Path(abs_path).is_file():
                raise _proj_422(
                    "ENV_COG_NOT_ON_DISK",
                    "environmental COG not found on server; upload the file first",
                )

            def _count() -> int:
                return count_bands_in_path(abs_path)

            count = await run_in_threadpool(_count)
            try:
                validate_band_definitions_match_raster(count, parsed)
            except ValueError as e:
                raise HTTPException(
                    status_code=422,
                    detail=validation_error("BAND_DEFINITION_INVALID", str(e)),
                ) from e
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
    new_explain_bg_rows = existing.explainability_background_sample_rows
    new_explain_bg_at = existing.explainability_background_generated_at
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
            new_explain_bg_rows = settings.env_background_sample_rows
            new_explain_bg_at = datetime.now(UTC).isoformat()
        except Exception as e:
            raise HTTPException(
                status_code=422,
                detail=validation_error(
                    "EXPLAINABILITY_BACKGROUND_FAILED",
                    "could not build explainability background sample from COG",
                    context={"cause": str(e)},
                ),
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
        band_inference_notes=inference_notes,
        explainability_background_path=new_explain_bg_path,
        explainability_background_sample_rows=new_explain_bg_rows,
        explainability_background_generated_at=new_explain_bg_at,
        created_at=existing.created_at,
        updated_at=now,
    )

    def _persist() -> None:
        upsert_project(settings, project)

    try:
        await run_in_threadpool(_persist)
    except Exception as e:
        raise _proj_503("CATALOG_SAVE_FAILED", f"could not save catalog: {e}") from e

    await reload_catalog_threaded(request)
    return project
