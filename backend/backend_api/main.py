"""FastAPI application factory and ASGI ``app`` (uvicorn: ``backend_api.main:app``)."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend_api.firebase_admin_app import init_firebase_admin
from backend_api.routers import auth, models, projects, root
from backend_api.catalog_service import build_catalog_service
from backend_api.settings import Settings
from backend_api.storage import build_object_storage


def _cors_allow_origins(settings: Settings) -> list[str]:
    return [x.strip() for x in settings.cors_origins.split(",") if x.strip()]


def create_app(settings: Settings | None = None) -> FastAPI:
    """
    Build the FastAPI app.

    Blocking sync work in path operations uses :func:`starlette.concurrency.run_in_threadpool`
    or sync ``def`` routes per FastAPI concurrency guidance.
    """
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.settings = settings
        init_firebase_admin(settings)
        app.state.catalog_service = build_catalog_service(settings)
        app.state.object_storage = build_object_storage(settings)
        yield

    app_kwargs: dict = {
        "title": "HSM Visualiser API",
        "description": (
            "API for Habitat Suitability Model Visualisation. "
            "Set OPENAPI_ENABLED=false in production to disable /docs and OpenAPI JSON."
        ),
        "version": "0.1.0",
        "lifespan": lifespan,
    }
    if not settings.openapi_enabled:
        app_kwargs["openapi_url"] = None
        app_kwargs["docs_url"] = None
        app_kwargs["redoc_url"] = None

    app = FastAPI(**app_kwargs)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_allow_origins(settings),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(root.router)
    app.include_router(auth.router)
    app.include_router(projects.router)
    app.include_router(models.router)
    return app


_settings = Settings()
app = create_app(_settings)
