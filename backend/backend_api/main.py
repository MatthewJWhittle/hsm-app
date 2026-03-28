from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool

from backend_api.catalog_service import CatalogService, build_catalog_service
from backend_api.point_sampling import PointSamplingError, inspect_point
from backend_api.schemas import Model, PointInspection
from backend_api.settings import Settings


def get_catalog_service(request: Request) -> CatalogService:
    return request.app.state.catalog_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings()
    app.state.settings = settings
    app.state.catalog_service = build_catalog_service(settings)
    yield


app = FastAPI(
    title="HSM Visualiser API",
    description="API for Habitat Suitability Model Visualisation",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ],
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


def _raise_catalog_http_errors(catalog: CatalogService) -> None:
    if catalog.validation_error:
        raise HTTPException(status_code=503, detail=catalog.validation_error)
    if catalog.load_error:
        raise HTTPException(status_code=503, detail=catalog.load_error)


@app.get("/models", response_model=list[Model])
async def list_models(catalog: CatalogService = Depends(get_catalog_service)):
    """List all suitability models (catalog). Aligns with docs/data-models.md."""
    _raise_catalog_http_errors(catalog)
    if not catalog.models and catalog.is_missing_catalog_file():
        raise HTTPException(
            status_code=404,
            detail="Catalog not found; set CATALOG_PATH or add data/catalog/firestore_models.json",
        )
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
