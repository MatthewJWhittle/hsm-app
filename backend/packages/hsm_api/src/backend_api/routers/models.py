"""Catalog and model routes (read + admin write)."""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    status,
)
from starlette.concurrency import run_in_threadpool
from starlette.responses import Response

from backend_api.api_errors import validation_error
from backend_api.auth_deps import optional_id_token_claims, require_admin_claims
from backend_api.catalog_service import CatalogService
from backend_api.catalog_write import upsert_model
from backend_api.cog_validation import CogValidationError
from backend_api.deps.artifact_read_runtime_dep import get_artifact_read_runtime
from backend_api.deps.catalog import (
    get_model_or_404,
    get_object_storage,
    require_catalog_ready,
)
from backend_api.deps.visibility_models import (
    filter_models_for_viewer,
    get_model_visible_or_404,
)
from backend_api.deps.settings_dep import get_settings
from backend_api.point_explainability import (
    validate_explainability_artifacts_for_model,
    warm_explainability_cache,
)
from backend_api.point_sampling import (
    PointSamplingError,
    RasterNotFoundError,
    inspect_point,
    validate_driver_band_indices_for_model,
)
from backend_api.env_background_sample import resolve_env_cog_uri_for_sampling
from backend_api.project_manifest import validate_model_feature_bands_for_admin
from backend_api.schemas import Model, ModelAnalysis, ModelMetadata, PointInspection
from backend_api.schemas_admin import parse_metadata_multipart_part
from backend_api.routers.catalog_upload_utils import (
    reload_catalog_threaded,
    validate_cog_path_threaded,
    validate_cog_uri_threaded,
)
from backend_api.routers.models_openapi import OPENAPI_POST_MODELS, OPENAPI_PUT_MODEL
from backend_api.settings import Settings
from hsm_core.artifact_read_runtime import ArtifactReadRuntime
from backend_api.schemas_upload import UploadSession
from backend_api.schemas_upload import UploadSessionResponse, to_upload_session_response
from backend_api.storage import (
    GcsObjectStorage,
    SERIALIZED_MODEL_FILENAME,
    ObjectStorage,
)
from backend_api.upload_session_ingest import (
    best_effort_fail,
    best_effort_mark,
    upload_session_gcs_uri,
    write_upload_file_to_tempfile,
)
from starlette.datastructures import FormData, UploadFile as StarletteUploadFile

router = APIRouter()
logger = logging.getLogger(__name__)


def _find_model_by_triplet(
    catalog: CatalogService,
    project_id: str,
    species: str,
    activity: str,
) -> Model | None:
    """Return an existing model with the same project, species, and activity (if any)."""
    for m in catalog.models:
        if m.project_id == project_id and m.species == species and m.activity == activity:
            return m
    return None


def _cog_validation_422(exc: CogValidationError) -> HTTPException:
    return HTTPException(
        status_code=422,
        detail=validation_error(exc.code, exc.message, context=exc.context or None),
    )


def _form_str(form: FormData, key: str) -> str | None:
    """Return a text form field, or None if missing/blank. Rejects accidental file parts."""
    v = form.get(key)
    if v is None:
        return None
    if isinstance(v, StarletteUploadFile):
        raise HTTPException(
            status_code=422,
            detail=validation_error(
                "FORM_FIELD_TYPE",
                f"Field {key!r} must be plain text. "
                "For metadata JSON, append a Blob with Content-Type application/json.",
                context={"field": key},
            ),
        )
    s = str(v)
    return s if s.strip() else None


def _form_require_str(form: FormData, key: str) -> str:
    s = _form_str(form, key)
    if not s:
        raise HTTPException(
            status_code=422,
            detail=validation_error("MISSING_FIELD", f"Missing form field {key!r}.", context={"field": key}),
        )
    return s.strip()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


_ADMIN_WRITE_RESPONSES: dict[int | str, dict[str, str]] = {
    status.HTTP_401_UNAUTHORIZED: {"description": "Missing or invalid bearer token"},
    status.HTTP_403_FORBIDDEN: {"description": "Valid token but admin claim not set"},
    status.HTTP_413_REQUEST_ENTITY_TOO_LARGE: {"description": "Upload exceeds MAX_UPLOAD_BYTES"},
    status.HTTP_422_UNPROCESSABLE_ENTITY: {
        "description": (
            "Validation failed. Response detail is a JSON object with "
            "`code`, `message`, and optional `context` (e.g. COG_CRS_MISMATCH, MISSING_FIELD)."
        ),
    },
    status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Storage or Firestore failure"},
}

_ADMIN_POST_MODELS_RESPONSES: dict[int | str, dict[str, str]] = {
    **_ADMIN_WRITE_RESPONSES,
    status.HTTP_409_CONFLICT: {
        "description": "Another model already exists for the same project_id + species + activity",
    },
}


async def _merge_serialized_model_upload(
    *,
    storage: ObjectStorage,
    settings: Settings,
    model_id: str,
    metadata: ModelMetadata | None,
    serialized_model_file: StarletteUploadFile | None,
) -> ModelMetadata | None:
    """Write optional sklearn upload and set ``metadata.analysis.serialized_model_path``."""
    if serialized_model_file is None:
        return metadata
    upload_temp_path = await write_upload_file_to_tempfile(
        serialized_model_file,
        max_bytes=settings.max_upload_bytes,
        suffix=".pkl",
    )
    logger.info("model_serialized_upload_ingest model_id=%s", model_id)
    try:
        upload_size = upload_temp_path.stat().st_size
        logger.info(
            "model_serialized_upload_size model_id=%s upload_bytes=%s",
            model_id,
            upload_size,
        )
        if upload_size <= 0:
            raise HTTPException(
                status_code=422,
                detail=validation_error(
                    "EMPTY_FILE",
                    "serialized_model_file is empty.",
                    context={"field": "serialized_model_file"},
                ),
            )

        def _write_m() -> None:
            storage.write_model_artifact_from_path(
                model_id, SERIALIZED_MODEL_FILENAME, str(upload_temp_path)
            )

        await run_in_threadpool(_write_m)
        logger.info("model_serialized_upload_persist_ok model_id=%s", model_id)
    finally:
        upload_temp_path.unlink(missing_ok=True)
    analysis = (metadata.analysis if metadata else None) or ModelAnalysis()
    analysis = analysis.model_copy(update={"serialized_model_path": SERIALIZED_MODEL_FILENAME})
    base = metadata or ModelMetadata()
    return base.model_copy(update={"analysis": analysis})


@router.get("/models", response_model=list[Model], tags=["catalog"])
async def list_models(
    catalog: Annotated[CatalogService, Depends(require_catalog_ready)],
    claims: Annotated[dict | None, Depends(optional_id_token_claims)],
    project_id: Annotated[str | None, Query()] = None,
):
    """List suitability models visible to the caller (optionally filter by ``project_id``)."""
    return filter_models_for_viewer(catalog, claims, project_id=project_id)


@router.get("/models/{model_id}", response_model=Model, tags=["catalog"])
async def get_model(m: Annotated[Model, Depends(get_model_visible_or_404)]):
    """Return one model by id if visible to the caller."""
    return m


@router.get("/models/{model_id}/point", response_model=PointInspection, tags=["catalog"])
async def get_model_point(
    lng: Annotated[
        float,
        Query(..., ge=-180.0, le=180.0, description="Longitude (WGS84)"),
    ],
    lat: Annotated[
        float,
        Query(..., ge=-90.0, le=90.0, description="Latitude (WGS84)"),
    ],
    m: Annotated[Model, Depends(get_model_visible_or_404)],
    catalog: Annotated[CatalogService, Depends(require_catalog_ready)],
    settings: Annotated[Settings, Depends(get_settings)],
    artifact_read: Annotated[ArtifactReadRuntime, Depends(get_artifact_read_runtime)],
):
    """
    Suitability value at a WGS84 point (band 1 of the model COG).

    **Always returned:** ``value`` (and ``capabilities.suitability_available``).

    **Conditionally returned:** ``raw_environmental_values`` when ``feature_band_names`` match the
    project manifest and an environmental COG path resolves. ``drivers`` (SHAP-style) only when
    explainability is fully configured (serialized model, background Parquet, aligned
    ``feature_names``). Use ``capabilities.notes`` to tell “not configured” from a hard error.

    Empty ``drivers`` with a numeric ``value`` usually means explainability is incomplete, not
    that the endpoint failed.

    **Pickle compatibility:** if the serialized estimator fails to load on the server (Python /
    scikit-learn / dependency mismatch with the training environment), influence may be unavailable
    even when other capabilities succeed; check ``capabilities.notes`` and server logs.

    **SHAP cost:** background Parquet rows are capped at ``SHAP_BACKGROUND_MAX_ROWS`` (see app settings)
    for each point request; larger files are truncated deterministically to the first N rows.

    **Timeout:** synchronous work is limited by ``POINT_INSPECT_TIMEOUT_SECONDS`` (default 45s); **504** on overrun.
    """

    def _run() -> PointInspection:
        return inspect_point(
            m,
            lng,
            lat,
            artifact_read=artifact_read,
            catalog=catalog,
            shap_background_max_rows=settings.shap_background_max_rows,
        )

    try:
        return await asyncio.wait_for(
            run_in_threadpool(_run),
            timeout=settings.point_inspect_timeout_seconds,
        )
    except TimeoutError:
        raise HTTPException(
            status_code=504,
            detail=validation_error(
                "POINT_INSPECT_TIMEOUT",
                "Point inspection exceeded the server time limit; try again or reduce explainability background size.",
            ),
        ) from None
    except PointSamplingError as e:
        raise HTTPException(
            status_code=422,
            detail=validation_error(e.code, e.detail),
        ) from e
    except RasterNotFoundError as e:
        raise HTTPException(
            status_code=503,
            detail=validation_error("RASTER_NOT_FOUND", e.detail),
        ) from e


@router.post(
    "/models/{model_id}/explainability-warmup",
    status_code=204,
    tags=["catalog"],
    summary="Prefetch SHAP explainer for a model (optional client optimization)",
)
async def post_explainability_warmup(
    m: Annotated[Model, Depends(get_model_visible_or_404)],
    catalog: Annotated[CatalogService, Depends(require_catalog_ready)],
    settings: Annotated[Settings, Depends(get_settings)],
    artifact_read: Annotated[ArtifactReadRuntime, Depends(get_artifact_read_runtime)],
):
    """
    Load serialized estimator + explainability background and build the permutation SHAP explainer
    into an in-memory cache when explainability is configured. Safe to call repeatedly; no-op when
    not configured. Does not run SHAP for a map click — use ``GET …/point`` for that.
    """

    def _warm() -> None:
        warm_explainability_cache(
            m,
            catalog,
            max_background_rows=settings.shap_background_max_rows,
            artifact_read=artifact_read,
        )

    await run_in_threadpool(_warm)
    return Response(status_code=204)


@router.post(
    "/models",
    response_model=Model | UploadSessionResponse,
    status_code=201,
    tags=["admin"],
    responses=_ADMIN_POST_MODELS_RESPONSES,
    summary="Create catalog entry and upload suitability COG",
    openapi_extra=OPENAPI_POST_MODELS,
)
async def create_model(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    _claims: Annotated[dict, Depends(require_admin_claims)],
    storage: Annotated[ObjectStorage, Depends(get_object_storage)],
    catalog: Annotated[CatalogService, Depends(require_catalog_ready)],
    artifact_read: Annotated[ArtifactReadRuntime, Depends(get_artifact_read_runtime)],
):
    """Create a catalog entry and store the suitability COG (admin only).

    Suitability rasters must be **EPSG:3857** tiled COGs. **409** if a model with the same
    ``project_id``, ``species``, and ``activity`` already exists (use ``PUT /models/{id}`` to update).
    """
    form = await request.form()
    project_id = _form_require_str(form, "project_id")
    species = _form_require_str(form, "species")
    activity = _form_require_str(form, "activity")
    if catalog.get_project(project_id) is None:
        raise HTTPException(
            status_code=422,
            detail=validation_error(
                "UNKNOWN_PROJECT",
                "project_id does not match a catalog project.",
                context={"project_id": project_id},
            ),
        )
    dup = _find_model_by_triplet(catalog, project_id, species, activity)
    if dup is not None:
        raise HTTPException(
            status_code=409,
            detail=validation_error(
                "MODEL_DUPLICATE",
                "A model with this project_id, species, and activity already exists.",
                context={"existing_model_id": dup.id},
            ),
        )
    upload_session_s = _form_str(form, "upload_session_id")
    file_part = form.get("file")
    if isinstance(file_part, str):
        raise HTTPException(
            status_code=422,
            detail=validation_error(
                "FORM_FIELD_TYPE",
                "file must be a file upload, not a text field.",
                context={"field": "file"},
            ),
        )
    if upload_session_s and isinstance(file_part, StarletteUploadFile):
        raise HTTPException(
            status_code=422,
            detail=validation_error(
                "UPLOAD_CONFLICT",
                "provide either multipart file or upload_session_id, not both",
            ),
        )
    if upload_session_s and settings.storage_backend.strip().lower() != "gcs":
        raise HTTPException(
            status_code=503,
            detail=validation_error(
                "STORAGE_BACKEND_UNSUPPORTED",
                "upload_session_id model create currently requires STORAGE_BACKEND=gcs",
            ),
        )
    upload_session: UploadSession | None = None
    upload_temp_path = None
    upload_uri: str | None = None
    upload_size: int | None = None
    rasterio_uri: str | None = None
    model_id = str(uuid.uuid4())
    logger.info(
        "model_create_start model_id=%s has_multipart=%s has_session=%s",
        model_id,
        isinstance(file_part, StarletteUploadFile),
        bool(upload_session_s),
    )
    if upload_session_s:
        upload_uri, upload_session, upload_size = await run_in_threadpool(
            upload_session_gcs_uri,
            settings,
            upload_session_s,
            purpose="model create",
        )
        if upload_session is not None:
            rasterio_uri = await run_in_threadpool(
                resolve_env_cog_uri_for_sampling,
                settings,
                f"gs://{upload_session.gcs_bucket}",
                upload_session.object_path,
            )
        logger.info(
            "model_create_ingest_session model_id=%s upload_session_id=%s",
            model_id,
            upload_session_s,
        )
    elif isinstance(file_part, StarletteUploadFile):
        upload_temp_path = await write_upload_file_to_tempfile(
            file_part,
            max_bytes=settings.max_upload_bytes,
        )
        logger.info("model_create_ingest_multipart model_id=%s", model_id)
    else:
        raise HTTPException(
            status_code=422,
            detail=validation_error(
                "MISSING_FIELD",
                "file or upload_session_id is required.",
                context={"field": "file"},
            ),
        )
    try:
        if upload_temp_path is not None:
            upload_size = os.path.getsize(str(upload_temp_path))
        logger.info(
            "model_create_upload_size model_id=%s upload_bytes=%s upload_session_id=%s",
            model_id,
            upload_size,
            upload_session.id if upload_session else None,
        )
        if upload_size is None:
            raise HTTPException(
                status_code=422,
                detail=validation_error(
                    "UPLOAD_SIZE_UNKNOWN",
                    "could not determine uploaded object size",
                    context={"field": "file"},
                ),
            )
        if upload_size <= 0:
            raise HTTPException(
                status_code=422,
                detail=validation_error(
                    "EMPTY_FILE",
                    "file is empty.",
                    context={"field": "file"},
                ),
            )
        if upload_size > settings.max_upload_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"file exceeds max size {settings.max_upload_bytes} bytes",
            )

        upload_session = await run_in_threadpool(
            best_effort_mark,
            settings,
            upload_session,
            status="complete",
            stage="validate",
            context="model-create-validate",
        )
        try:
            logger.info("model_create_validate_start model_id=%s", model_id)
            if upload_uri is not None:
                await validate_cog_uri_threaded(
                    rasterio_uri if rasterio_uri is not None else upload_uri
                )
            elif upload_temp_path is not None:
                await validate_cog_path_threaded(str(upload_temp_path))
            else:
                raise HTTPException(
                    status_code=422,
                    detail=validation_error(
                        "MISSING_FIELD",
                        "file or upload_session_id is required.",
                        context={"field": "file"},
                    ),
                )
            logger.info("model_create_validate_ok model_id=%s", model_id)
        except CogValidationError as e:
            await run_in_threadpool(
                best_effort_fail,
                settings,
                upload_session,
                stage="validate",
                error_code=e.code,
                error_message=e.message,
                context="model-create-cog-validate-failed",
            )
            raise _cog_validation_422(e) from e

        def _write() -> tuple[str, str]:
            if upload_uri is not None:
                if upload_session is None:
                    raise ValueError("upload session missing for session-based model create")
                return storage.promote_upload_session_suitability_cog(
                    model_id=model_id,
                    source_bucket=upload_session.gcs_bucket,
                    source_object_path=upload_session.object_path,
                )
            if upload_temp_path is None:
                raise ValueError("missing upload source path")
            return storage.write_suitability_cog_from_path(model_id, str(upload_temp_path))

        try:
            artifact_root, suitability_cog_path = await run_in_threadpool(_write)
            logger.info(
                "model_create_persist_cog_ok model_id=%s artifact_root=%s",
                model_id,
                artifact_root,
            )
        except ValueError as e:
            await run_in_threadpool(
                best_effort_fail,
                settings,
                upload_session,
                stage="persist",
                error_code="STORAGE_LAYOUT_INVALID",
                error_message=str(e),
                context="model-create-storage-layout-invalid",
            )
            raise HTTPException(
                status_code=400,
                detail=validation_error("STORAGE_LAYOUT_INVALID", str(e)),
            ) from e
        except Exception as e:
            await run_in_threadpool(
                best_effort_fail,
                settings,
                upload_session,
                stage="persist",
                error_code="STORAGE_WRITE_FAILED",
                error_message=str(e),
                context="model-create-storage-write-failed",
            )
            raise HTTPException(
                status_code=503,
                detail=validation_error(
                    "STORAGE_WRITE_FAILED",
                    f"could not store file: {e}",
                ),
            ) from e
    finally:
        if upload_temp_path is not None:
            upload_temp_path.unlink(missing_ok=True)

    try:
        meta_in = await parse_metadata_multipart_part(form.get("metadata"))
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail=validation_error("METADATA_INVALID", str(e)),
        ) from e
    sm_part = form.get("serialized_model_file")
    serialized_model_file = sm_part if isinstance(sm_part, StarletteUploadFile) else None
    meta_in = await _merge_serialized_model_upload(
        storage=storage,
        settings=settings,
        model_id=model_id,
        metadata=meta_in,
        serialized_model_file=serialized_model_file,
    )

    ts = _utc_now_iso()
    model = Model(
        id=model_id,
        project_id=project_id,
        species=species,
        activity=activity,
        artifact_root=artifact_root,
        suitability_cog_path=suitability_cog_path,
        created_at=ts,
        updated_at=ts,
        metadata=meta_in,
    )

    validate_model_feature_bands_for_admin(model, catalog)

    def _validate_and_enrich() -> Model:
        validate_driver_band_indices_for_model(model, catalog, artifact_read)
        validate_explainability_artifacts_for_model(model, catalog)
        return model

    upload_session = await run_in_threadpool(
        best_effort_mark,
        settings,
        upload_session,
        status="complete",
        stage="derive",
        context="model-create-derive",
    )
    try:
        model = await run_in_threadpool(_validate_and_enrich)
    except ValueError as e:
        await run_in_threadpool(
            best_effort_fail,
            settings,
            upload_session,
            stage="derive",
            error_code="MODEL_VALIDATION",
            error_message=str(e),
            context="model-create-validation-failed",
        )
        raise HTTPException(
            status_code=422,
            detail=validation_error("MODEL_VALIDATION", str(e)),
        ) from e

    def _persist() -> None:
        upsert_model(settings, model)

    upload_session = await run_in_threadpool(
        best_effort_mark,
        settings,
        upload_session,
        status="complete",
        stage="persist",
        context="model-create-persist",
    )
    try:
        await run_in_threadpool(_persist)
        logger.info("model_create_catalog_save_ok model_id=%s", model_id)
    except Exception as e:
        await run_in_threadpool(
            best_effort_fail,
            settings,
            upload_session,
            stage="persist",
            error_code="CATALOG_SAVE_FAILED",
            error_message=str(e),
            context="model-create-catalog-save",
        )
        raise HTTPException(
            status_code=503,
            detail=f"could not save catalog: {e}",
        ) from e

    upload_session = await run_in_threadpool(
        best_effort_mark,
        settings,
        upload_session,
        status="complete",
        stage="done",
        context="model-create-done",
    )

    await reload_catalog_threaded(request)
    return model


@router.put(
    "/models/{model_id}",
    response_model=Model,
    tags=["admin"],
    responses=_ADMIN_WRITE_RESPONSES,
    summary="Update model metadata and/or replace COG",
    openapi_extra=OPENAPI_PUT_MODEL,
)
async def update_model(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    _claims: Annotated[dict, Depends(require_admin_claims)],
    storage: Annotated[ObjectStorage, Depends(get_object_storage)],
    catalog: Annotated[CatalogService, Depends(require_catalog_ready)],
    existing: Annotated[Model, Depends(get_model_or_404)],
    artifact_read: Annotated[ArtifactReadRuntime, Depends(get_artifact_read_runtime)],
):
    """Update metadata and/or replace the suitability COG (admin only).

    Replacement COGs must be **EPSG:3857** tiled GeoTIFFs (same as POST).
    """
    form = await request.form()
    model_id = existing.id
    artifact_root = existing.artifact_root
    suitability_cog_path = existing.suitability_cog_path
    logger.info(
        "model_update_start model_id=%s has_multipart=%s",
        model_id,
        isinstance(form.get("file"), StarletteUploadFile),
    )

    file_part = form.get("file")
    if file_part is not None and not isinstance(file_part, StarletteUploadFile):
        raise HTTPException(
            status_code=422,
            detail=validation_error(
                "FORM_FIELD_TYPE",
                "file must be a file upload.",
                context={"field": "file"},
            ),
        )
    if isinstance(file_part, StarletteUploadFile):
        upload_temp_path = await write_upload_file_to_tempfile(
            file_part,
            max_bytes=settings.max_upload_bytes,
        )
        logger.info("model_update_ingest_multipart model_id=%s", model_id)
        try:
            upload_size = upload_temp_path.stat().st_size
            logger.info(
                "model_update_upload_size model_id=%s upload_bytes=%s",
                model_id,
                upload_size,
            )
            if upload_size <= 0:
                raise HTTPException(
                    status_code=422,
                    detail=validation_error(
                        "EMPTY_FILE",
                        "file is empty.",
                        context={"field": "file"},
                    ),
                )
            try:
                logger.info("model_update_validate_start model_id=%s", model_id)
                await validate_cog_path_threaded(str(upload_temp_path))
                logger.info("model_update_validate_ok model_id=%s", model_id)
            except CogValidationError as e:
                raise _cog_validation_422(e) from e

            def _write() -> tuple[str, str]:
                return storage.write_suitability_cog_from_path(
                    model_id, str(upload_temp_path)
                )

            try:
                artifact_root, suitability_cog_path = await run_in_threadpool(_write)
                logger.info(
                    "model_update_persist_cog_ok model_id=%s artifact_root=%s",
                    model_id,
                    artifact_root,
                )
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e)) from e
            except Exception as e:
                raise HTTPException(
                    status_code=503,
                    detail=f"could not store file: {e}",
                ) from e
        finally:
            upload_temp_path.unlink(missing_ok=True)

    species_s = _form_str(form, "species")
    activity_s = _form_str(form, "activity")
    new_species = species_s if species_s is not None else existing.species
    new_activity = activity_s if activity_s is not None else existing.activity
    new_project_id = existing.project_id
    project_id_f = _form_str(form, "project_id")
    if project_id_f is not None:
        if catalog.get_project(project_id_f) is None:
            raise HTTPException(
                status_code=422,
                detail=validation_error(
                    "UNKNOWN_PROJECT",
                    "project_id does not match a catalog project.",
                    context={"project_id": project_id_f},
                ),
            )
        new_project_id = project_id_f

    if "metadata" in form:
        try:
            new_metadata = await parse_metadata_multipart_part(form.get("metadata"))
        except ValueError as e:
            raise HTTPException(
                status_code=422,
                detail=validation_error("METADATA_INVALID", str(e)),
            ) from e
    else:
        new_metadata = existing.metadata

    sm_part = form.get("serialized_model_file")
    serialized_model_file = sm_part if isinstance(sm_part, StarletteUploadFile) else None

    new_metadata = await _merge_serialized_model_upload(
        storage=storage,
        settings=settings,
        model_id=model_id,
        metadata=new_metadata,
        serialized_model_file=serialized_model_file,
    )

    ts = _utc_now_iso()
    created_prev = existing.created_at or ts
    model = Model(
        id=model_id,
        project_id=new_project_id,
        species=new_species,
        activity=new_activity,
        artifact_root=artifact_root,
        suitability_cog_path=suitability_cog_path,
        created_at=created_prev,
        updated_at=ts,
        metadata=new_metadata,
    )

    validate_model_feature_bands_for_admin(model, catalog)

    def _validate_and_enrich() -> Model:
        validate_driver_band_indices_for_model(model, catalog, artifact_read)
        validate_explainability_artifacts_for_model(model, catalog)
        return model

    try:
        model = await run_in_threadpool(_validate_and_enrich)
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail=validation_error("MODEL_VALIDATION", str(e)),
        ) from e

    def _persist() -> None:
        upsert_model(settings, model)

    try:
        await run_in_threadpool(_persist)
        logger.info("model_update_catalog_save_ok model_id=%s", model_id)
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"could not save catalog: {e}",
        ) from e

    await reload_catalog_threaded(request)
    return model
