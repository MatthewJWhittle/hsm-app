"""Catalog and model routes (read + admin write)."""

from __future__ import annotations

import json
import uuid
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from starlette.concurrency import run_in_threadpool

from backend_api.auth_deps import optional_id_token_claims, require_admin_claims
from backend_api.catalog_service import CatalogService
from backend_api.catalog_write import upsert_model
from backend_api.cog_validation import CogValidationError
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
from backend_api.point_explainability import validate_explainability_artifacts_for_model
from backend_api.point_sampling import (
    PointSamplingError,
    RasterNotFoundError,
    inspect_point,
    validate_driver_band_indices_for_model,
)
from backend_api.project_manifest import (
    enrich_model_driver_config_from_project,
    validate_model_bands_against_project_manifest,
)
from backend_api.schemas import Model, PointInspection
from backend_api.schemas_admin import parse_driver_config_form
from backend_api.routers.catalog_upload_utils import (
    reload_catalog_threaded,
    validate_cog_bytes_threaded,
)
from backend_api.settings import Settings
from backend_api.storage import EXPLAINABILITY_MODEL_FILENAME, ObjectStorage

router = APIRouter()

_ADMIN_WRITE_RESPONSES: dict[int | str, dict[str, str]] = {
    status.HTTP_401_UNAUTHORIZED: {"description": "Missing or invalid bearer token"},
    status.HTTP_403_FORBIDDEN: {"description": "Valid token but admin claim not set"},
    status.HTTP_413_REQUEST_ENTITY_TOO_LARGE: {"description": "Upload exceeds MAX_UPLOAD_BYTES"},
    status.HTTP_422_UNPROCESSABLE_ENTITY: {
        "description": "Empty file, invalid COG/CRS, or bad driver_config JSON",
    },
    status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Storage or Firestore failure"},
}


def _parse_driver_config_http(raw: str | None) -> dict | None:
    try:
        return parse_driver_config_form(raw)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


async def _merge_explainability_model_upload(
    *,
    storage: ObjectStorage,
    settings: Settings,
    model_id: str,
    dc: dict | None,
    explainability_model_file: UploadFile | None,
) -> dict | None:
    """Write optional sklearn upload and set fixed ``driver_config`` path (background is project-level)."""
    if explainability_model_file is None:
        return dc
    out = dict(dc) if dc else {}
    content = await explainability_model_file.read()
    if not content:
        raise HTTPException(
            status_code=422, detail="explainability_model_file is empty"
        )
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"explainability_model_file exceeds max size {settings.max_upload_bytes} bytes",
        )

    def _write_m() -> None:
        storage.write_model_artifact(model_id, EXPLAINABILITY_MODEL_FILENAME, content)

    await run_in_threadpool(_write_m)
    out["explainability_model_path"] = EXPLAINABILITY_MODEL_FILENAME
    return out


def _parse_driver_band_indices(raw: str | None) -> list[int] | None:
    if raw is None or not str(raw).strip():
        return None
    try:
        data = json.loads(raw.strip())
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=422, detail=f"driver_band_indices: {e}") from e
    if not isinstance(data, list):
        raise HTTPException(
            status_code=422, detail="driver_band_indices must be a JSON array of integers"
        )
    try:
        return [int(x) for x in data]
    except (TypeError, ValueError) as e:
        raise HTTPException(
            status_code=422, detail="driver_band_indices must be integers"
        ) from e


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
):
    """
    Suitability value at a WGS84 point (band 1 of the model COG).

    When the model has ``driver_band_indices`` and a resolvable environmental COG,
    returns ``raw_environmental_values`` at the point. When ``driver_config`` includes
    explainability artefacts (trained model under the layer + project reference sample + ``feature_names``), returns
    SHAP-style influence in ``drivers``. Configuration is read from the catalog model only.

    Returns 422 if the point is outside the raster, nodata, or the file CRS is not EPSG:3857.
    """

    def _run() -> PointInspection:
        return inspect_point(m, lng, lat, catalog=catalog)

    try:
        return await run_in_threadpool(_run)
    except PointSamplingError as e:
        raise HTTPException(status_code=422, detail=e.detail) from e
    except RasterNotFoundError as e:
        raise HTTPException(status_code=503, detail=e.detail) from e


@router.post(
    "/models",
    response_model=Model,
    status_code=201,
    tags=["admin"],
    responses=_ADMIN_WRITE_RESPONSES,
    summary="Create catalog entry and upload suitability COG",
)
async def create_model(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    _claims: Annotated[dict, Depends(require_admin_claims)],
    storage: Annotated[ObjectStorage, Depends(get_object_storage)],
    catalog: Annotated[CatalogService, Depends(require_catalog_ready)],
    project_id: Annotated[str, Form()],
    species: Annotated[str, Form()],
    activity: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
    model_name: Annotated[str | None, Form()] = None,
    model_version: Annotated[str | None, Form()] = None,
    driver_band_indices: Annotated[str | None, Form()] = None,
    driver_config: Annotated[str | None, Form()] = None,
    explainability_model_file: Annotated[UploadFile | None, File()] = None,
):
    """Create a catalog entry and store the suitability COG (admin only)."""
    if catalog.get_project(project_id.strip()) is None:
        raise HTTPException(status_code=422, detail="unknown project_id")
    band_indices = _parse_driver_band_indices(driver_band_indices)
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

    model_id = str(uuid.uuid4())

    def _write() -> tuple[str, str]:
        return storage.write_suitability_cog(model_id, content)

    try:
        artifact_root, suitability_cog_path = await run_in_threadpool(_write)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"could not store file: {e}",
        ) from e

    dc = _parse_driver_config_http(driver_config)
    dc = await _merge_explainability_model_upload(
        storage=storage,
        settings=settings,
        model_id=model_id,
        dc=dc,
        explainability_model_file=explainability_model_file,
    )
    model = Model(
        id=model_id,
        project_id=project_id.strip(),
        species=species.strip(),
        activity=activity.strip(),
        artifact_root=artifact_root,
        suitability_cog_path=suitability_cog_path,
        model_name=model_name.strip() if model_name else None,
        model_version=model_version.strip() if model_version else None,
        driver_band_indices=band_indices,
        driver_config=dc,
    )

    def _validate_and_enrich() -> Model:
        validate_model_bands_against_project_manifest(model, catalog)
        m = enrich_model_driver_config_from_project(model, catalog)
        validate_driver_band_indices_for_model(m, catalog)
        validate_explainability_artifacts_for_model(m)
        return m

    try:
        model = await run_in_threadpool(_validate_and_enrich)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    def _persist() -> None:
        upsert_model(settings, model)

    try:
        await run_in_threadpool(_persist)
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"could not save catalog: {e}",
        ) from e

    await reload_catalog_threaded(request)
    return model


@router.put(
    "/models/{model_id}",
    response_model=Model,
    tags=["admin"],
    responses=_ADMIN_WRITE_RESPONSES,
    summary="Update model metadata and/or replace COG",
)
async def update_model(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    _claims: Annotated[dict, Depends(require_admin_claims)],
    storage: Annotated[ObjectStorage, Depends(get_object_storage)],
    catalog: Annotated[CatalogService, Depends(require_catalog_ready)],
    existing: Annotated[Model, Depends(get_model_or_404)],
    species: Annotated[str | None, Form()] = None,
    activity: Annotated[str | None, Form()] = None,
    file: Annotated[UploadFile | None, File()] = None,
    model_name: Annotated[str | None, Form()] = None,
    model_version: Annotated[str | None, Form()] = None,
    project_id: Annotated[str | None, Form()] = None,
    driver_band_indices: Annotated[str | None, Form()] = None,
    driver_config: Annotated[str | None, Form()] = None,
    explainability_model_file: Annotated[UploadFile | None, File()] = None,
):
    """Update metadata and/or replace the suitability COG (admin only)."""
    model_id = existing.id
    artifact_root = existing.artifact_root
    suitability_cog_path = existing.suitability_cog_path

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
            return storage.write_suitability_cog(model_id, content)

        try:
            artifact_root, suitability_cog_path = await run_in_threadpool(_write)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        except Exception as e:
            raise HTTPException(
                status_code=503,
                detail=f"could not store file: {e}",
            ) from e

    new_species = species.strip() if species is not None else existing.species
    new_activity = activity.strip() if activity is not None else existing.activity
    if model_name is not None:
        stripped = model_name.strip()
        new_name = stripped if stripped else None
    else:
        new_name = existing.model_name
    if model_version is not None:
        stripped_v = model_version.strip()
        new_ver = stripped_v if stripped_v else None
    else:
        new_ver = existing.model_version
    if driver_config is not None:
        new_driver = _parse_driver_config_http(driver_config)
    else:
        new_driver = existing.driver_config

    merged_driver = await _merge_explainability_model_upload(
        storage=storage,
        settings=settings,
        model_id=model_id,
        dc=new_driver,
        explainability_model_file=explainability_model_file,
    )
    new_driver = merged_driver

    new_project_id = existing.project_id
    if project_id is not None:
        pid = project_id.strip()
        if catalog.get_project(pid) is None:
            raise HTTPException(status_code=422, detail="unknown project_id")
        new_project_id = pid

    new_band_indices = existing.driver_band_indices
    if driver_band_indices is not None:
        new_band_indices = _parse_driver_band_indices(driver_band_indices)

    model = Model(
        id=model_id,
        project_id=new_project_id,
        species=new_species,
        activity=new_activity,
        artifact_root=artifact_root,
        suitability_cog_path=suitability_cog_path,
        model_name=new_name,
        model_version=new_ver,
        driver_band_indices=new_band_indices,
        driver_config=new_driver,
    )

    def _validate_and_enrich() -> Model:
        validate_model_bands_against_project_manifest(model, catalog)
        m = enrich_model_driver_config_from_project(model, catalog)
        validate_driver_band_indices_for_model(m, catalog)
        validate_explainability_artifacts_for_model(m)
        return m

    try:
        model = await run_in_threadpool(_validate_and_enrich)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    def _persist() -> None:
        upsert_model(settings, model)

    try:
        await run_in_threadpool(_persist)
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"could not save catalog: {e}",
        ) from e

    await reload_catalog_threaded(request)
    return model
