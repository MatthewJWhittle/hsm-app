"""FastAPI application factory and ASGI ``app`` (uvicorn: ``backend_api.main:app``)."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from backend_api.app_state import assert_hsm_app_state_attrs
from backend_api.routers import auth, jobs, models, projects, root, uploads
from backend_api.catalog_service import build_catalog_service
from hsm_core.firebase_admin_app import init_firebase_admin
from hsm_core.artifact_read_runtime import ArtifactReadRuntime
from hsm_core.settings import Settings
from hsm_core.storage import build_object_storage


def _cors_allow_origins(settings: Settings) -> list[str]:
    return [x.strip() for x in settings.cors_origins.split(",") if x.strip()]


def _cors_allow_origin_regex(settings: Settings) -> str | None:
    if settings.cors_origin_regex is None:
        return None
    value = settings.cors_origin_regex.strip()
    return value or None


def create_app(settings: Settings | None = None) -> FastAPI:
    """
    Build the FastAPI app.

    Blocking sync work in path operations uses :func:`starlette.concurrency.run_in_threadpool`
    or sync ``def`` routes per FastAPI concurrency guidance.
    """
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Populate ``app.state`` with the fields documented in ``backend_api.app_state.HsmAppState``."""
        app.state.settings = settings
        init_firebase_admin(settings)
        app.state.catalog_service = build_catalog_service(settings)
        app.state.object_storage = build_object_storage(settings)
        app.state.artifact_read_runtime = ArtifactReadRuntime(settings)
        assert_hsm_app_state_attrs(app)
        yield

    app_kwargs: dict = {
        "title": "HSM Visualiser API",
        "description": (
            "API for Habitat Suitability Model Visualisation.\n\n"
            "**Docs:** `GET /api/openapi.json`, Swagger UI at `/api/docs`, ReDoc at `/api/redoc` "
            "(unless `OPENAPI_ENABLED=false`).\n\n"
            "**Admin writes** (`POST`/`PUT` on `/api/models`, `/api/projects`, …): "
            "`Authorization: Bearer` with a Firebase **ID** token that includes the **`admin: true`** "
            "custom claim. Obtain tokens with **`POST /api/auth/token`** (JSON email/password); "
            "set **`admin_only: true`** when you need a token that is rejected unless the user is an admin.\n\n"
            "**Uploads:** environmental and suitability rasters must be **Cloud Optimized GeoTIFF** "
            "in **EPSG:3857**. Model **`metadata.analysis.feature_band_names`** must resolve against "
            "the parent project's **`environmental_band_definitions`** (see `ModelMetadata` in OpenAPI).\n\n"
            "**Explainability pickle** (`multipart` **`serialized_model_file`**): upload a **fitted scikit-learn–compatible** "
            "estimator only — the API runtime does **not** install arbitrary training-repo packages; pickles that "
            "import custom modules fail at **`GET …/point`** with **`EXPLAINABILITY_PICKLE_IMPORT`**. "
            "See repository **`docs/serialized-model-requirements.md`**.\n\n"
            "Long-form guide for modellers and scripts: repository **`docs/api-integration.md`**.\n\n"
            "Set `OPENAPI_ENABLED=false` in production to disable `/api/docs` and OpenAPI JSON."
        ),
        "version": "0.1.0",
        "lifespan": lifespan,
        "openapi_url": "/api/openapi.json",
        "docs_url": "/api/docs",
        "redoc_url": "/api/redoc",
    }
    if not settings.openapi_enabled:
        app_kwargs["openapi_url"] = None
        app_kwargs["docs_url"] = None
        app_kwargs["redoc_url"] = None

    app = FastAPI(**app_kwargs)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_allow_origins(settings),
        allow_origin_regex=_cors_allow_origin_regex(settings),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(root.router)
    app.include_router(auth.router, prefix="/api")
    app.include_router(projects.router, prefix="/api")
    app.include_router(models.router, prefix="/api")
    app.include_router(uploads.router, prefix="/api")
    app.include_router(jobs.router, prefix="/api")

    if settings.openapi_enabled:

        def custom_openapi() -> dict:
            if app.openapi_schema:
                return app.openapi_schema
            openapi_schema = get_openapi(
                title=app.title,
                version=app.version,
                openapi_version=app.openapi_version,
                description=str(app.description),
                routes=app.routes,
            )
            openapi_schema.setdefault("components", {}).setdefault("securitySchemes", {})[
                "HTTPBearer"
            ] = {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": (
                    "Firebase ID token in `Authorization: Bearer <token>`. "
                    "Required for routes tagged `admin` (must include custom claim `admin: true`). "
                    "Obtain via `POST /api/auth/token` with email/password; use `admin_only: true` "
                    "to require an admin-capable token. Optional on public catalog reads."
                ),
            }
            for path_item in openapi_schema.get("paths", {}).values():
                for op in path_item.values():
                    if isinstance(op, dict) and "admin" in op.get("tags", []):
                        op["security"] = [{"HTTPBearer": []}]
            app.openapi_schema = openapi_schema
            return app.openapi_schema

        app.openapi = custom_openapi  # type: ignore[method-assign]

    return app


_settings = Settings()
app = create_app(_settings)
