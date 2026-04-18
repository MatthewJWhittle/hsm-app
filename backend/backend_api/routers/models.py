"""Catalog and model routes (read + admin write)."""

from __future__ import annotations

import asyncio
import logging
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
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from starlette.responses import Response

from backend_api.api_errors import validation_error
from backend_api.auth_deps import optional_id_token_claims, require_admin_claims
from backend_api.catalog_service import CatalogService
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
from backend_api.job_queue import build_job_queue, job_queue_enabled
from backend_api.jobs import create_job
from backend_api.point_explainability import warm_explainability_cache
from backend_api.point_sampling import (
    PointSamplingError,
    RasterNotFoundError,
    inspect_point,
)
from backend_api.schemas import Model, ModelMetadata, PointInspection
from backend_api.schemas_job import JobAcceptedResponse, JobKind
from backend_api.model_suitability_pipeline import (
    create_model_with_suitability_upload_pipeline,
    update_model_pipeline,
)
from backend_api.schemas_admin import parse_metadata_multipart_part
from backend_api.routers.catalog_upload_utils import reload_catalog_threaded
from backend_api.routers.models_openapi import OPENAPI_POST_MODELS, OPENAPI_PUT_MODEL
from backend_api.settings import Settings
from backend_api.storage import ObjectStorage
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

_ADMIN_PUT_MODEL_RESPONSES: dict[int | str, dict[str, str]] = {
    **_ADMIN_WRITE_RESPONSES,
    status.HTTP_202_ACCEPTED: {
        "description": "Background job enqueued (upload session + job queue enabled, no pickle upload)",
    },
}

_ADMIN_POST_MODELS_RESPONSES: dict[int | str, dict[str, str]] = {
    **_ADMIN_WRITE_RESPONSES,
    status.HTTP_202_ACCEPTED: {
        "description": "Background job enqueued (upload session + job queue enabled, no pickle upload)",
    },
    status.HTTP_409_CONFLICT: {
        "description": "Another model already exists for the same project_id + species + activity",
    },
}


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
        )

    await run_in_threadpool(_warm)
    return Response(status_code=204)


@router.post(
    "/models",
    response_model=Model,
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
    if not upload_session_s and not isinstance(file_part, StarletteUploadFile):
        raise HTTPException(
            status_code=422,
            detail=validation_error(
                "MISSING_FIELD",
                "file or upload_session_id is required.",
                context={"field": "file"},
            ),
        )

    sm_part = form.get("serialized_model_file")
    has_serialized = isinstance(sm_part, StarletteUploadFile)
    try:
        meta_in = await parse_metadata_multipart_part(form.get("metadata"))
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail=validation_error("METADATA_INVALID", str(e)),
        ) from e

    if (
        job_queue_enabled(settings)
        and upload_session_s
        and not isinstance(file_part, StarletteUploadFile)
        and not has_serialized
    ):
        model_id = str(uuid.uuid4())
        metadata_json = meta_in.model_dump_json() if meta_in is not None else None
        job = create_job(
            settings,
            kind=JobKind.MODEL_CREATE_WITH_UPLOAD,
            input={
                "model_id": model_id,
                "project_id": project_id,
                "species": species,
                "activity": activity,
                "upload_session_id": upload_session_s,
                "metadata_json": metadata_json,
            },
            created_by_uid=str(_claims.get("uid") or "") or None,
        )
        build_job_queue(settings).enqueue_run_job(job.id)
        body = JobAcceptedResponse(
            job_id=job.id,
            status=job.status.value,
            model_id=model_id,
            project_id=project_id,
        )
        return JSONResponse(
            status_code=202,
            content=body.model_dump(mode="json"),
            headers={"Location": f"/api/jobs/{job.id}"},
        )

    model_id = str(uuid.uuid4())
    logger.info(
        "model_create_start model_id=%s has_multipart=%s has_session=%s",
        model_id,
        isinstance(file_part, StarletteUploadFile),
        bool(upload_session_s),
    )
    serialized_model_file = sm_part if has_serialized else None
    return await create_model_with_suitability_upload_pipeline(
        request,
        settings,
        storage,
        catalog,
        model_id=model_id,
        project_id=project_id,
        species=species,
        activity=activity,
        upload_session_id=upload_session_s,
        file=file_part if isinstance(file_part, StarletteUploadFile) else None,
        metadata=meta_in,
        serialized_model_file=serialized_model_file,
    )


@router.put(
    "/models/{model_id}",
    response_model=Model,
    tags=["admin"],
    responses=_ADMIN_PUT_MODEL_RESPONSES,
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
):
    """Update metadata and/or replace the suitability COG (admin only).

    Replacement COGs must be **EPSG:3857** tiled GeoTIFFs (same as POST).
    """
    form = await request.form()
    model_id = existing.id
    upload_session_s = _form_str(form, "upload_session_id")
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
    if upload_session_s and isinstance(file_part, StarletteUploadFile):
        raise HTTPException(
            status_code=422,
            detail=validation_error(
                "UPLOAD_CONFLICT",
                "provide either multipart file or upload_session_id, not both",
            ),
        )
    sm_part = form.get("serialized_model_file")
    has_serialized = isinstance(sm_part, StarletteUploadFile)
    logger.info(
        "model_update_start model_id=%s has_multipart=%s has_session=%s",
        model_id,
        isinstance(file_part, StarletteUploadFile),
        bool(upload_session_s),
    )

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

    if (
        job_queue_enabled(settings)
        and upload_session_s
        and not isinstance(file_part, StarletteUploadFile)
        and not has_serialized
    ):
        metadata_json = (
            new_metadata.model_dump_json() if new_metadata is not None else None
        )
        job = create_job(
            settings,
            kind=JobKind.MODEL_REPLACE_SUITABILITY_COG,
            input={
                "model_id": model_id,
                "upload_session_id": upload_session_s,
                "species": new_species,
                "activity": new_activity,
                "project_id": new_project_id,
                "metadata_json": metadata_json,
            },
            created_by_uid=str(_claims.get("uid") or "") or None,
        )
        build_job_queue(settings).enqueue_run_job(job.id)
        body = JobAcceptedResponse(
            job_id=job.id,
            status=job.status.value,
            model_id=model_id,
            project_id=new_project_id,
        )
        return JSONResponse(
            status_code=202,
            content=body.model_dump(mode="json"),
            headers={"Location": f"/api/jobs/{job.id}"},
        )

    serialized_model_file = sm_part if has_serialized else None
    return await update_model_pipeline(
        request,
        settings,
        storage,
        catalog,
        existing,
        species=new_species,
        activity=new_activity,
        project_id=new_project_id,
        metadata=new_metadata,
        file=file_part if isinstance(file_part, StarletteUploadFile) else None,
        upload_session_id=upload_session_s,
        serialized_model_file=serialized_model_file,
    )
