import json
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    hsm_index_path: str = "/data/hsm_index.json"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load configuration and index at startup
    settings = Settings()  # loads from env if present
    index_path = settings.hsm_index_path
    app.state.settings = settings
    app.state.hsm_index_path = index_path
    try:
        if os.path.exists(index_path):
            with open(index_path, 'r', encoding='utf-8') as f:
                app.state.hsm_index = json.load(f)
        else:
            app.state.hsm_index = None
    except Exception:
        app.state.hsm_index = None
    yield
    # No shutdown actions required


app = FastAPI(
    title="HSM Visualiser API",
    description="API for Habitat Suitability Model Visualisation",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
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


def _parse_filename(filename: str):
    # expects ..._cog.tif
    lower = filename.lower()
    if not lower.endswith("_cog.tif"):
        return None, None
    stem = filename[:-8]  # remove _cog.tif
    if "_" not in stem:
        return None, None
    species, activity = stem.rsplit("_", 1)
    return species, activity


@app.get("/hsm/options")
async def list_options(request: Request):
    data = getattr(request.app.state, 'hsm_index', None)
    if not data:
        return JSONResponse(status_code=404, content={"error": "index not found"})
    # Return species, activities, and the list of (species, activity, cog_path)
    items = data.get("items", [])
    return JSONResponse(content={
        "species": data.get("species", []),
        "activities": data.get("activities", []),
        "items": items,
    })


@app.get("/hsm/url")
async def get_cog_url(request: Request, species: str = Query(...), activity: str = Query(...)):
    data = getattr(request.app.state, 'hsm_index', None)
    if not data:
        return JSONResponse(status_code=404, content={"error": "index not found"})
    by_species = data.get("by_species", {})
    cog_path = by_species.get(species, {}).get(activity)
    if not cog_path:
        return JSONResponse(
            status_code=404,
            content={
                "error": "not found",
                "species": species,
                "activity": activity,
            },
        )
    return JSONResponse(content={"cog_path": cog_path})