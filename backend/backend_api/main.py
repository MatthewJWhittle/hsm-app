import json
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool

from backend_api.auth_deps import require_admin_claims, require_id_token_claims
from backend_api.catalog_service import CatalogService, FirestoreCatalogService, build_catalog_service
from backend_api.catalog_write import upsert_model
from backend_api.cog_validation import CogValidationError, validate_suitability_cog_bytes
from backend_api.firebase_admin_app import init_firebase_admin
from backend_api.point_sampling import PointSamplingError, inspect_point
from backend_api.schemas import AuthMeResponse, Model, PointInspection
from backend_api.settings import Settings
from backend_api.storage import ObjectStorage, build_object_storage


def _cors_allow_origins(settings: Settings) -> list[str]:
    return [x.strip() for x in settings.cors_origins.split(",") if x.strip()]


_settings = Settings()


def get_catalog_service(request: Request) -> CatalogService:
    return request.app.state.catalog_service


def get_object_storage(request: Request) -> ObjectStorage:
    return request.app.state.object_storage


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.settings = _settings
    init_firebase_admin(_settings)
    app.state.catalog_service = build_catalog_service(_settings)
    app.state.object_storage = build_object_storage(_settings)
    yield


app = FastAPI(
    title="HSM Visualiser API",
    description="API for Habitat Suitability Model Visualisation",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_allow_origins(_settings),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Welcome to HSM Visualiser API"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/auth/me", response_model=AuthMeResponse)
async def auth_me(claims: dict = Depends(require_id_token_claims)):
    """Return uid/email from a verified Firebase ID token (Bearer)."""
    uid = claims.get("uid")
    if not uid or not isinstance(uid, str):
        raise HTTPException(status_code=401, detail="Invalid token payload")
    email = claims.get("email")
    email_out = email if isinstance(email, str) else None
    return AuthMeResponse(uid=uid, email=email_out)


def _raise_catalog_http_errors(catalog: CatalogService) -> None:
    if catalog.validation_error:
        raise HTTPException(status_code=503, detail=catalog.validation_error)
    if catalog.load_error:
        raise HTTPException(status_code=503, detail=catalog.load_error)


@app.get("/models", response_model=list[Model])
async def list_models(catalog: CatalogService = Depends(get_catalog_service)):
    """List all suitability models (catalog). Aligns with docs/data-models.md."""
    _raise_catalog_http_errors(catalog)
    return catalog.models


@app.get("/models/{model_id}", response_model=Model)
async def get_model(
    model_id: str,
    catalog: CatalogService = Depends(get_catalog_service),
):
    _raise_catalog_http_errors(catalog)
    m = catalog.get_model(model_id)
    if m is not None:
        return m
    raise HTTPException(status_code=404, detail="model not found")


@app.get("/models/{model_id}/point", response_model=PointInspection)
async def get_model_point(
    model_id: str,
    lng: float = Query(..., ge=-180.0, le=180.0, description="Longitude (WGS84)"),
    lat: float = Query(..., ge=-90.0, le=90.0, description="Latitude (WGS84)"),
    catalog: CatalogService = Depends(get_catalog_service),
):
    """
    Suitability value at a WGS84 point (band 1 of the model COG).

    Returns 422 if the point is outside the raster, nodata, or the file CRS is not EPSG:3857.
    """
    _raise_catalog_http_errors(catalog)
    m = catalog.get_model(model_id)
    if m is None:
        raise HTTPException(status_code=404, detail="model not found")

    def _run() -> PointInspection:
        return inspect_point(m, lng, lat)

    try:
        return await run_in_threadpool(_run)
    except PointSamplingError as e:
        raise HTTPException(status_code=422, detail=e.detail) from e
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=503,
            detail="suitability raster not found on server",
        ) from e


def _reload_catalog(request: Request) -> None:
    cat = request.app.state.catalog_service
    if isinstance(cat, FirestoreCatalogService):
        cat.reload()


def _parse_driver_config(raw: str | None) -> dict | None:
    if raw is None or (isinstance(raw, str) and raw.strip() == ""):
        return None
    try:
        out = json.loads(raw)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=422,
            detail=f"driver_config must be valid JSON: {e}",
        ) from e
    if not isinstance(out, dict):
        raise HTTPException(status_code=422, detail="driver_config must be a JSON object")
    return out


@app.post("/models", response_model=Model, status_code=201)
async def create_model(
    request: Request,
    species: str = Form(...),
    activity: str = Form(...),
    file: UploadFile = File(...),
    model_name: str | None = Form(None),
    model_version: str | None = Form(None),
    driver_config: str | None = Form(None),
    _claims: dict = Depends(require_admin_claims),
    storage: ObjectStorage = Depends(get_object_storage),
):
    """Create a catalog entry and store the suitability COG (admin only)."""
    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail="empty file")
    try:
        validate_suitability_cog_bytes(content)
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

    dc = _parse_driver_config(driver_config)
    model = Model(
        id=model_id,
        species=species.strip(),
        activity=activity.strip(),
        artifact_root=artifact_root,
        suitability_cog_path=suitability_cog_path,
        model_name=model_name.strip() if model_name else None,
        model_version=model_version.strip() if model_version else None,
        driver_config=dc,
    )

    def _persist() -> None:
        upsert_model(_settings, model)

    try:
        await run_in_threadpool(_persist)
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"could not save catalog: {e}",
        ) from e

    _reload_catalog(request)
    return model


@app.put("/models/{model_id}", response_model=Model)
async def update_model(
    request: Request,
    model_id: str,
    species: str | None = Form(None),
    activity: str | None = Form(None),
    file: UploadFile | None = File(None),
    model_name: str | None = Form(None),
    model_version: str | None = Form(None),
    driver_config: str | None = Form(None),
    _claims: dict = Depends(require_admin_claims),
    catalog: CatalogService = Depends(get_catalog_service),
    storage: ObjectStorage = Depends(get_object_storage),
):
    """Update metadata and/or replace the suitability COG (admin only)."""
    _raise_catalog_http_errors(catalog)
    existing = catalog.get_model(model_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="model not found")

    artifact_root = existing.artifact_root
    suitability_cog_path = existing.suitability_cog_path

    if file is not None:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=422, detail="empty file")
        try:
            validate_suitability_cog_bytes(content)
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
        new_driver = _parse_driver_config(driver_config)
    else:
        new_driver = existing.driver_config

    model = Model(
        id=model_id,
        species=new_species,
        activity=new_activity,
        artifact_root=artifact_root,
        suitability_cog_path=suitability_cog_path,
        model_name=new_name,
        model_version=new_ver,
        driver_config=new_driver,
    )

    def _persist() -> None:
        upsert_model(_settings, model)

    try:
        await run_in_threadpool(_persist)
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"could not save catalog: {e}",
        ) from e

    _reload_catalog(request)
    return model
