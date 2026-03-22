from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from backend_api.catalog import catalog_to_models, load_index
from backend_api.schemas import Model
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Path to local JSON catalog (Firestore snapshot shape; see docs/data-models.md)."""

    catalog_path: str = "/data/catalog/firestore_models.json"


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings()
    app.state.settings = settings
    app.state.catalog_path = settings.catalog_path
    raw = load_index(settings.catalog_path)
    app.state.catalog_raw = raw
    models_list = catalog_to_models(raw)
    app.state.models = models_list
    app.state.models_by_id = {m.id: m for m in models_list}
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


def _models(request: Request) -> list[Model]:
    return getattr(request.app.state, "models", []) or []


@app.get("/models", response_model=list[Model])
async def list_models(request: Request):
    """List all suitability models (catalog). Aligns with docs/data-models.md."""
    if not _models(request) and not getattr(request.app.state, "catalog_raw", None):
        raise HTTPException(
            status_code=404,
            detail="Catalog not found; set CATALOG_PATH or add data/catalog/firestore_models.json",
        )
    return _models(request)


@app.get("/models/{model_id}", response_model=Model)
async def get_model(model_id: str, request: Request):
    m = getattr(request.app.state, "models_by_id", {}).get(model_id)
    if m is not None:
        return m
    raise HTTPException(status_code=404, detail="model not found")
