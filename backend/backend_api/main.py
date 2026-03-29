from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool

from backend_api.auth_deps import require_id_token_claims
from backend_api.catalog_service import CatalogService, build_catalog_service
from backend_api.firebase_admin_app import init_firebase_admin
from backend_api.point_sampling import PointSamplingError, inspect_point
from backend_api.schemas import AuthMeResponse, Model, PointInspection
from backend_api.settings import Settings


def _cors_allow_origins(settings: Settings) -> list[str]:
    return [x.strip() for x in settings.cors_origins.split(",") if x.strip()]


_settings = Settings()


def get_catalog_service(request: Request) -> CatalogService:
    return request.app.state.catalog_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.settings = _settings
    init_firebase_admin(_settings)
    app.state.catalog_service = build_catalog_service(_settings)
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
