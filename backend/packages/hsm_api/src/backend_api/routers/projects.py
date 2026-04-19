"""Catalog project routes (read + admin write)."""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Body,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from google.cloud import firestore
from starlette.concurrency import run_in_threadpool

from backend_api.auth_claims import subject_uid_from_claims
from backend_api.auth_deps import optional_id_token_claims, require_admin_claims
from backend_api.catalog_service import CatalogService
from backend_api.catalog_write import upsert_project
from backend_api.api_errors import validation_error
from backend_api.cog_validation import CogValidationError
from backend_api.deps.catalog import get_object_storage, require_catalog_ready
from backend_api.deps.firestore_dep import get_firestore_client
from backend_api.env_background_sample import (
    resolve_env_cog_uri_for_sampling,
    sanitize_exception_for_client,
    write_project_explainability_background_parquet,
)
from backend_api.jobs.dispatch import schedule_background_http_task
from backend_api.env_cog_bands import (
    apply_band_label_updates,
    band_definitions_for_upload_path,
    band_definitions_for_upload_uri,
    count_bands_in_path,
    validate_band_definitions_match_raster,
)
from backend_api.deps.settings_dep import get_settings
from backend_api.deps.visibility_models import (
    filter_projects_for_viewer,
    get_project_visible_or_404,
)
from backend_api.routers.catalog_upload_utils import (
    reload_catalog_threaded,
    validate_cog_path_threaded,
    validate_cog_uri_threaded,
)
from backend_api.routers.project_visibility_parse import (
    parse_status_optional,
    parse_visibility,
    parse_visibility_optional,
)
from backend_api.project_manifest import resolve_env_cog_path_from_parts
from backend_api.schemas_jobs import JobAcceptedResponse
from backend_api.schemas_project import (
    BandLabelPatch,
    CatalogProject,
    EnvironmentalBandDefinition,
    RegenerateExplainabilityBackgroundBody,
)
from backend_api.settings import Settings
from backend_api.storage import (
    EXPLAINABILITY_BACKGROUND_FILENAME,
    ObjectStorage,
)
from backend_api.schemas_upload import UploadSession
from backend_api.upload_session_ingest import (
    best_effort_fail,
    best_effort_mark,
    upload_session_gcs_uri,
    write_upload_file_to_tempfile,
)
from hsm_core.env_cog_paths import environmental_cog_readable_for_sampling
from hsm_core.explainability_job_preflight import (
    ExplainabilityJobPreflightError,
    validate_catalog_project_for_explainability_sample,
)
from hsm_core.job_error_codes import JobErrorCode
from hsm_core.jobs import create_job_document, fail_job, write_job

router = APIRouter()
logger = logging.getLogger(__name__)

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


def _upload_error_context(
    *,
    project_id: str,
    phase: str,
    uploaded_session: UploadSession | None,
    extra: dict | None = None,
) -> dict:
    ctx: dict = {
        "project_id": project_id,
        "phase": phase,
        "upload_session_id": uploaded_session.id if uploaded_session is not None else None,
    }
    if extra:
        ctx.update(extra)
    return ctx


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
    if not environmental_cog_readable_for_sampling(abs_path):
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
    if not environmental_cog_readable_for_sampling(abs_path):
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


@router.post(
    "/projects/{project_id}/explainability-background-sample",
    response_model=JobAcceptedResponse,
    status_code=202,
    tags=["admin"],
    responses={
        **_ADMIN_RESPONSES,
        202: {"description": "Background job enqueued; poll GET /api/admin/jobs/{job_id}"},
    },
    summary="Regenerate SHAP explainability background Parquet from the environmental COG",
)
async def post_explainability_background_sample(
    background_tasks: BackgroundTasks,
    settings: Annotated[Settings, Depends(get_settings)],
    fs_client: Annotated[firestore.Client, Depends(get_firestore_client)],
    _claims: Annotated[dict, Depends(require_admin_claims)],
    catalog: Annotated[CatalogService, Depends(require_catalog_ready)],
    project_id: str,
    body: Annotated[
        RegenerateExplainabilityBackgroundBody,
        Body(),
    ] = RegenerateExplainabilityBackgroundBody(),
):
    """
    Enqueue re-sampling of random pixels from the project's environmental COG into
    ``explainability_background.parquet`` (same path as on upload).

    Returns **202** with ``job_id``; poll ``GET /api/admin/jobs/{job_id}`` until
    ``status`` is ``succeeded`` or ``failed``. Does not require re-uploading the COG.
    Omit ``sample_rows`` to use ``ENV_BACKGROUND_SAMPLE_ROWS``.
    """
    existing = catalog.get_project(project_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="project not found")

    try:
        validate_catalog_project_for_explainability_sample(existing)
    except ExplainabilityJobPreflightError as e:
        raise _proj_422(e.code, e.message) from e

    n_samples = (
        body.sample_rows
        if body.sample_rows is not None
        else settings.env_background_sample_rows
    )

    job = create_job_document(
        kind="explainability_background_sample",
        project_id=project_id,
        created_by_uid=subject_uid_from_claims(_claims),
        sample_rows=n_samples,
    )

    def _persist_job() -> None:
        write_job(fs_client, job)

    await run_in_threadpool(_persist_job)
    try:
        schedule_background_http_task(
            settings=settings,
            background_tasks=background_tasks,
            body={"job_id": job.job_id, "kind": job.kind},
        )
    except Exception as exc:
        err_text = (str(exc).strip() or type(exc).__name__)[:2000]

        def _mark_enqueue_failed() -> None:
            fail_job(
                fs_client,
                job.job_id,
                code=JobErrorCode.ENQUEUE_FAILED,
                message=err_text,
            )

        try:
            await run_in_threadpool(_mark_enqueue_failed)
        except Exception:
            logger.exception(
                "enqueue_failed_and_could_not_update_job job_id=%s",
                job.job_id,
            )
        else:
            logger.warning(
                "enqueue_failed_marked_job_failed job_id=%s error=%s",
                job.job_id,
                err_text,
            )
        raise HTTPException(
            status_code=503,
            detail=validation_error(
                "ENQUEUE_FAILED",
                "could not enqueue background worker task",
                context={"job_id": job.job_id},
            ),
        ) from exc

    return JobAcceptedResponse(job_id=job.job_id)


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
    if upload_session_id and settings.storage_backend.strip().lower() != "gcs":
        raise _proj_503(
            "STORAGE_BACKEND_UNSUPPORTED",
            "upload_session_id project create currently requires STORAGE_BACKEND=gcs",
        )
    visibility_v = parse_visibility(visibility)
    try:
        uids = _parse_allowed_uids(allowed_uids)
    except (json.JSONDecodeError, ValueError) as e:
        raise HTTPException(
            status_code=422,
            detail=validation_error("ALLOWED_UIDS_INVALID", str(e)),
        ) from e

    project_id = str(uuid.uuid4())
    logger.info("project_create_start project_id=%s has_multipart=%s has_session=%s", project_id, file is not None, bool(upload_session_id))
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
    upload_temp_path: Path | None = None
    upload_uri: str | None = None
    upload_size: int | None = None
    rasterio_uri: str | None = None
    if upload_session_id:
        upload_uri, uploaded_session, upload_size = await run_in_threadpool(
            upload_session_gcs_uri,
            settings,
            upload_session_id,
            purpose="project create",
        )
        if uploaded_session is not None:
            rasterio_uri = await run_in_threadpool(
                resolve_env_cog_uri_for_sampling,
                settings,
                f"gs://{uploaded_session.gcs_bucket}",
                uploaded_session.object_path,
            )
        logger.info(
            "project_create_ingest_session project_id=%s upload_session_id=%s",
            project_id,
            upload_session_id,
        )
    elif file is not None:
        upload_temp_path = await write_upload_file_to_tempfile(
            file,
            max_bytes=settings.max_environmental_upload_bytes,
        )
        logger.info("project_create_ingest_multipart project_id=%s", project_id)

    try:
        if upload_temp_path is not None or upload_uri is not None:
            if upload_temp_path is not None:
                upload_size = os.path.getsize(str(upload_temp_path))
            logger.info("project_create_upload_size project_id=%s upload_bytes=%s upload_session_id=%s", project_id, upload_size, uploaded_session.id if uploaded_session else None)
            if upload_size is None:
                raise HTTPException(
                    status_code=422,
                    detail=validation_error(
                        "UPLOAD_SIZE_UNKNOWN",
                        "could not determine uploaded object size",
                    ),
                )
            if upload_size <= 0:
                raise _proj_422("EMPTY_FILE", "empty file")
            if upload_size > settings.max_environmental_upload_bytes:
                raise HTTPException(
                    status_code=413,
                    detail=validation_error(
                        "UPLOAD_TOO_LARGE",
                        f"file exceeds max size {settings.max_environmental_upload_bytes} bytes",
                        context={"max_bytes": settings.max_environmental_upload_bytes},
                    ),
                )
            uploaded_session = await run_in_threadpool(
                best_effort_mark,
                settings,
                uploaded_session,
                status="complete",
                stage="validate",
                context="project-create-validate",
            )
            try:
                logger.info("project_create_validate_start project_id=%s", project_id)
                if upload_uri is not None:
                    await validate_cog_uri_threaded(
                        rasterio_uri if rasterio_uri is not None else upload_uri
                    )
                elif upload_temp_path is not None:
                    await validate_cog_path_threaded(str(upload_temp_path))
                logger.info("project_create_validate_ok project_id=%s", project_id)
            except CogValidationError as e:
                await run_in_threadpool(
                    best_effort_fail,
                    settings,
                    uploaded_session,
                    stage="validate",
                    error_code=e.code,
                    error_message=e.message,
                    context="project-create-cog-validate-failed",
                )
                raise HTTPException(
                    status_code=422,
                    detail=validation_error(e.code, e.message, context=e.context or None),
                ) from e

            def _write() -> tuple[str, str]:
                if upload_uri is not None:
                    if uploaded_session is None:
                        raise ValueError("upload session missing for session-based project create")
                    return storage.promote_upload_session_driver_cog(
                        project_id=project_id,
                        source_bucket=uploaded_session.gcs_bucket,
                        source_object_path=uploaded_session.object_path,
                    )
                if upload_temp_path is None:
                    raise ValueError("missing upload source path")
                return storage.write_project_driver_cog_from_path(
                    project_id, str(upload_temp_path)
                )

            try:
                artifact_root, cog_path = await run_in_threadpool(_write)
                logger.info("project_create_persist_cog_ok project_id=%s artifact_root=%s", project_id, artifact_root)
            except ValueError as e:
                await run_in_threadpool(
                    best_effort_fail,
                    settings,
                    uploaded_session,
                    stage="persist",
                    error_code="STORAGE_LAYOUT_INVALID",
                    error_message=str(e),
                    context="project-create-storage-layout-invalid",
                )
                raise HTTPException(
                    status_code=400,
                    detail=validation_error("STORAGE_LAYOUT_INVALID", str(e)),
                ) from e
            except Exception as e:
                await run_in_threadpool(
                    best_effort_fail,
                    settings,
                    uploaded_session,
                    stage="persist",
                    error_code="STORAGE_WRITE_FAILED",
                    error_message=str(e),
                    context="project-create-storage-write-failed",
                )
                raise _proj_503("STORAGE_WRITE_FAILED", f"could not store file: {e}") from e

            uploaded_session = await run_in_threadpool(
                best_effort_mark,
                settings,
                uploaded_session,
                status="complete",
                stage="derive",
                context="project-create-derive",
            )
            try:
                logger.info("project_create_derive_bands_start project_id=%s", project_id)

                def _defs() -> tuple[list[EnvironmentalBandDefinition], list[str]]:
                    if upload_uri is not None:
                        return band_definitions_for_upload_uri(
                            rasterio_uri if rasterio_uri is not None else upload_uri,
                            environmental_band_definitions,
                            infer_band_definitions=_infer_band_definitions_from_form(
                                infer_band_definitions
                            ),
                        )
                    if upload_temp_path is not None:
                        return band_definitions_for_upload_path(
                            str(upload_temp_path),
                            environmental_band_definitions,
                            infer_band_definitions=_infer_band_definitions_from_form(
                                infer_band_definitions
                            ),
                        )
                    raise ValueError("missing upload source for band definition inference")

                band_defs, infer_notes = await run_in_threadpool(_defs)
                inference_notes = infer_notes if infer_notes else None
                logger.info("project_create_derive_bands_ok project_id=%s band_count=%s", project_id, len(band_defs) if band_defs else 0)
            except ValueError as e:
                await run_in_threadpool(
                    best_effort_fail,
                    settings,
                    uploaded_session,
                    stage="derive",
                    error_code="BAND_DEFINITIONS",
                    error_message=str(e),
                    context="project-create-band-definitions",
                )
                raise HTTPException(
                    status_code=422,
                    detail=validation_error("BAND_DEFINITIONS", str(e)),
                ) from e
    finally:
        if upload_temp_path is not None:
            upload_temp_path.unlink(missing_ok=True)

    explain_bg_path: str | None = None
    explain_bg_rows: int | None = None
    explain_bg_at: str | None = None
    if band_defs and artifact_root and cog_path:
        try:
            logger.info("project_create_background_start project_id=%s sample_rows=%s", project_id, settings.env_background_sample_rows)

            def _bg() -> None:
                write_project_explainability_background_parquet(
                    storage,
                    settings,
                    project_id,
                    artifact_root,
                    cog_path,
                    band_defs,
                    settings.env_background_sample_rows,
                )

            await run_in_threadpool(_bg)
            explain_bg_path = EXPLAINABILITY_BACKGROUND_FILENAME
            explain_bg_rows = settings.env_background_sample_rows
            logger.info("project_create_background_ok project_id=%s sample_rows=%s", project_id, explain_bg_rows)
        except Exception as e:
            await run_in_threadpool(
                best_effort_fail,
                settings,
                uploaded_session,
                stage="derive",
                error_code="EXPLAINABILITY_BACKGROUND_FAILED",
                error_message=str(e),
                context="project-create-explainability-background",
            )
            raise HTTPException(
                status_code=422,
                detail=validation_error(
                    "EXPLAINABILITY_BACKGROUND_FAILED",
                    "could not build explainability background sample from COG",
                    context={"cause": sanitize_exception_for_client(e)},
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

    uploaded_session = await run_in_threadpool(
        best_effort_mark,
        settings,
        uploaded_session,
        status="complete",
        stage="persist",
        context="project-create-persist",
    )
    try:
        await run_in_threadpool(_persist)
        logger.info("project_create_catalog_save_ok project_id=%s", project_id)
    except Exception as e:
        await run_in_threadpool(
            best_effort_fail,
            settings,
            uploaded_session,
            stage="persist",
            error_code="CATALOG_SAVE_FAILED",
            error_message=str(e),
            context="project-create-catalog-save",
        )
        raise _proj_503("CATALOG_SAVE_FAILED", f"could not save catalog: {e}") from e

    await reload_catalog_threaded(request)
    if uploaded_session is not None and uploaded_session.stage != "done":
        await run_in_threadpool(
            best_effort_mark,
            settings,
            uploaded_session,
            status="complete",
            stage="done",
            context="project-create-done",
        )
    return project


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
        raise _proj_422(
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
        raise _proj_503("CATALOG_SAVE_FAILED", f"could not save catalog: {e}") from e

    await reload_catalog_threaded(request)
    return project


@router.post(
    "/projects/{project_id}/environmental-cogs",
    response_model=CatalogProject,
    tags=["admin"],
    responses=_ADMIN_RESPONSES,
    summary="Replace project environmental COG from upload session",
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
    """Create/replace a project's active environmental COG (admin only)."""
    existing = catalog.get_project(project_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="project not found")
    if upload_session_id and settings.storage_backend.strip().lower() != "gcs":
        raise _proj_503(
            "STORAGE_BACKEND_UNSUPPORTED",
            "upload_session_id project replace currently requires STORAGE_BACKEND=gcs",
        )

    if file is not None and upload_session_id:
        raise _proj_422(
            "UPLOAD_CONFLICT",
            "provide either multipart file or upload_session_id, not both",
        )
    if file is not None:
        raise _proj_422(
            "UPLOAD_MODE_UNSUPPORTED",
            "direct multipart replace is not supported; use upload_session_id",
        )
    if upload_session_id is None:
        raise _proj_422(
            "MISSING_UPLOAD",
            "provide upload_session_id",
        )

    overall_started = perf_counter()
    upload_uri: str | None = None
    uploaded_session: UploadSession | None = None
    rasterio_uri: str | None = None

    try:
        ingest_started = perf_counter()
        upload_uri, uploaded_session, upload_size = await run_in_threadpool(
            upload_session_gcs_uri,
            settings,
            upload_session_id,
            purpose="project update",
        )
        logger.info(
            "project_replace_env_cog_ingest_done project_id=%s source=session-uri upload_session_id=%s duration_ms=%s",
            project_id,
            upload_session_id,
            int((perf_counter() - ingest_started) * 1000),
        )

        logger.info(
            "project_replace_env_cog_upload_size project_id=%s upload_bytes=%s upload_session_id=%s",
            project_id,
            upload_size,
            uploaded_session.id if uploaded_session else None,
        )
        if upload_size is None:
            raise HTTPException(
                status_code=422,
                detail=validation_error(
                    "UPLOAD_SIZE_UNKNOWN",
                    "could not determine uploaded object size",
                    context=_upload_error_context(
                        project_id=project_id,
                        phase="ingest",
                        uploaded_session=uploaded_session,
                    ),
                ),
            )
        if upload_size <= 0:
            raise _proj_422(
                "EMPTY_FILE",
                "empty file",
                context=_upload_error_context(
                    project_id=project_id,
                    phase="ingest",
                    uploaded_session=uploaded_session,
                ),
            )
        if upload_size > settings.max_environmental_upload_bytes:
            raise HTTPException(
                status_code=413,
                detail=validation_error(
                    "UPLOAD_TOO_LARGE",
                    f"file exceeds max size {settings.max_environmental_upload_bytes} bytes",
                    context=_upload_error_context(
                        project_id=project_id,
                        phase="ingest",
                        uploaded_session=uploaded_session,
                        extra={"max_bytes": settings.max_environmental_upload_bytes},
                    ),
                ),
            )

        if uploaded_session is None:
            raise _proj_503(
                "UPLOAD_SESSION_MISSING",
                "upload session could not be resolved for processing",
            )

        if uploaded_session.project_id is not None and uploaded_session.project_id != project_id:
            raise _proj_422(
                "UPLOAD_PROJECT_MISMATCH",
                "upload session project does not match route project",
            )
        if uploaded_session.status == "pending":
            raise HTTPException(
                status_code=409,
                detail="upload session is not complete; call POST /uploads/{id}/complete first",
            )
        if uploaded_session.status == "failed":
            raise HTTPException(
                status_code=409,
                detail="upload session is in failed state; create a new upload session",
            )

        rasterio_uri = await run_in_threadpool(
            resolve_env_cog_uri_for_sampling,
            settings,
            f"gs://{uploaded_session.gcs_bucket}",
            uploaded_session.object_path,
        )

        uploaded_session = await run_in_threadpool(
            best_effort_mark,
            settings,
            uploaded_session,
            status="complete",
            stage="validate",
            context="project-update-validate",
        )
        validate_started = perf_counter()
        try:
            logger.info(
                "project_replace_env_cog_validate_start project_id=%s",
                project_id,
            )
            await validate_cog_uri_threaded(
                rasterio_uri if rasterio_uri is not None else upload_uri
            )
            logger.info(
                "project_replace_env_cog_validate_ok project_id=%s duration_ms=%s",
                project_id,
                int((perf_counter() - validate_started) * 1000),
            )
        except CogValidationError as e:
            logger.info(
                "project_replace_env_cog_validate_failed project_id=%s duration_ms=%s",
                project_id,
                int((perf_counter() - validate_started) * 1000),
            )
            await run_in_threadpool(
                best_effort_fail,
                settings,
                uploaded_session,
                stage="validate",
                error_code=e.code,
                error_message=e.message,
                context="project-update-cog-validate-failed",
            )
            raise HTTPException(
                status_code=422,
                detail=validation_error(
                    e.code,
                    e.message,
                    context=_upload_error_context(
                        project_id=project_id,
                        phase="validate",
                        uploaded_session=uploaded_session,
                        extra=e.context or None,
                    ),
                ),
            ) from e

        def _write() -> tuple[str, str]:
            return storage.promote_upload_session_driver_cog(
                project_id=project_id,
                source_bucket=uploaded_session.gcs_bucket if uploaded_session else "",
                source_object_path=(
                    uploaded_session.object_path if uploaded_session else ""
                ),
            )

        persist_started = perf_counter()
        try:
            artifact_root, cog_path = await run_in_threadpool(_write)
            logger.info(
                "project_replace_env_cog_persist_cog_ok project_id=%s artifact_root=%s duration_ms=%s",
                project_id,
                artifact_root,
                int((perf_counter() - persist_started) * 1000),
            )
        except ValueError as e:
            await run_in_threadpool(
                best_effort_fail,
                settings,
                uploaded_session,
                stage="persist",
                error_code="STORAGE_LAYOUT_INVALID",
                error_message=str(e),
                context="project-update-storage-layout-invalid",
            )
            raise HTTPException(
                status_code=400,
                detail=validation_error(
                    "STORAGE_LAYOUT_INVALID",
                    str(e),
                    context=_upload_error_context(
                        project_id=project_id,
                        phase="persist",
                        uploaded_session=uploaded_session,
                    ),
                ),
            ) from e
        except Exception as e:
            await run_in_threadpool(
                best_effort_fail,
                settings,
                uploaded_session,
                stage="persist",
                error_code="STORAGE_WRITE_FAILED",
                error_message=str(e),
                context="project-update-storage-write-failed",
            )
            raise HTTPException(
                status_code=503,
                detail=validation_error(
                    "STORAGE_WRITE_FAILED",
                    f"could not store file: {e}",
                    context=_upload_error_context(
                        project_id=project_id,
                        phase="persist",
                        uploaded_session=uploaded_session,
                    ),
                ),
            ) from e

        uploaded_session = await run_in_threadpool(
            best_effort_mark,
            settings,
            uploaded_session,
            status="complete",
            stage="derive",
            context="project-update-derive",
        )
        derive_started = perf_counter()
        try:
            logger.info(
                "project_replace_env_cog_derive_bands_start project_id=%s",
                project_id,
            )

            def _defs() -> tuple[list[EnvironmentalBandDefinition], list[str]]:
                return band_definitions_for_upload_uri(
                    rasterio_uri if rasterio_uri is not None else upload_uri,
                    environmental_band_definitions,
                    infer_band_definitions=_infer_band_definitions_from_form(
                        infer_band_definitions
                    ),
                )

            new_band_defs, infer_notes = await run_in_threadpool(_defs)
            inference_notes = infer_notes if infer_notes else None
            logger.info(
                "project_replace_env_cog_derive_bands_ok project_id=%s band_count=%s duration_ms=%s",
                project_id,
                len(new_band_defs) if new_band_defs else 0,
                int((perf_counter() - derive_started) * 1000),
            )
        except ValueError as e:
            logger.info(
                "project_replace_env_cog_derive_bands_failed project_id=%s duration_ms=%s",
                project_id,
                int((perf_counter() - derive_started) * 1000),
            )
            await run_in_threadpool(
                best_effort_fail,
                settings,
                uploaded_session,
                stage="derive",
                error_code="BAND_DEFINITIONS",
                error_message=str(e),
                context="project-update-band-definitions",
            )
            raise HTTPException(
                status_code=422,
                detail=validation_error(
                    "BAND_DEFINITIONS",
                    str(e),
                    context=_upload_error_context(
                        project_id=project_id,
                        phase="derive",
                        uploaded_session=uploaded_session,
                    ),
                ),
            ) from e

        now = datetime.now(UTC).isoformat()
        project = existing.model_copy(
            update={
                "driver_artifact_root": artifact_root,
                "driver_cog_path": cog_path,
                "environmental_band_definitions": new_band_defs,
                "band_inference_notes": inference_notes,
                "explainability_background_path": None,
                "explainability_background_sample_rows": None,
                "explainability_background_generated_at": None,
                "updated_at": now,
            }
        )

        def _persist() -> None:
            upsert_project(settings, project)

        uploaded_session = await run_in_threadpool(
            best_effort_mark,
            settings,
            uploaded_session,
            status="complete",
            stage="persist",
            context="project-update-persist",
        )
        catalog_save_started = perf_counter()
        try:
            await run_in_threadpool(_persist)
            logger.info(
                "project_replace_env_cog_catalog_save_ok project_id=%s duration_ms=%s",
                project_id,
                int((perf_counter() - catalog_save_started) * 1000),
            )
        except Exception as e:
            await run_in_threadpool(
                best_effort_fail,
                settings,
                uploaded_session,
                stage="persist",
                error_code="CATALOG_SAVE_FAILED",
                error_message=str(e),
                context="project-update-catalog-save",
            )
            raise HTTPException(
                status_code=503,
                detail=validation_error(
                    "CATALOG_SAVE_FAILED",
                    f"could not save catalog: {e}",
                    context=_upload_error_context(
                        project_id=project_id,
                        phase="persist",
                        uploaded_session=uploaded_session,
                    ),
                ),
            ) from e

        reload_started = perf_counter()
        await reload_catalog_threaded(request)
        logger.info(
            "project_replace_env_cog_catalog_reload_ok project_id=%s duration_ms=%s",
            project_id,
            int((perf_counter() - reload_started) * 1000),
        )
        if uploaded_session is not None and uploaded_session.stage != "done":
            await run_in_threadpool(
                best_effort_mark,
                settings,
                uploaded_session,
                status="complete",
                stage="done",
                context="project-update-done",
            )
        logger.info(
            "project_replace_env_cog_done project_id=%s total_duration_ms=%s",
            project_id,
            int((perf_counter() - overall_started) * 1000),
        )
        return project
    except HTTPException:
        raise

