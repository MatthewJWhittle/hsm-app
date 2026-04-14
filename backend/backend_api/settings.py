"""Application settings (env / .env)."""

from __future__ import annotations

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App configuration.

    **Firestore:** set ``GOOGLE_CLOUD_PROJECT`` (or ``GCLOUD_PROJECT``).
    For the emulator, set ``FIRESTORE_EMULATOR_HOST`` (e.g. ``127.0.0.1:8085``).
    From Docker Desktop, use ``host.docker.internal:8085`` when emulators run on the
    host.

    **Auth (Admin SDK):** set ``FIREBASE_AUTH_EMULATOR_HOST`` in dev (e.g.
    ``firebase-emulators:9099`` from Docker) so ``verify_id_token`` uses the Auth
    emulator. Omit in production (use Application Default Credentials). Use
    ``FIREBASE_PROJECT_ID`` when Firebase Auth lives in a different project than
    ``GOOGLE_CLOUD_PROJECT`` (Firestore/storage project).

    **CORS:** ``CORS_ORIGINS`` is a comma-separated list of allowed browser origins.
    Defaults include local dev and Firebase Hosting URLs for this project.

    Catalog documents use collection id ``models`` (``MODELS_COLLECTION_ID`` in
    ``catalog_service``).

    **Storage (admin uploads):** ``STORAGE_BACKEND`` is ``local`` (default) or ``gcs``.
    Local writes use ``LOCAL_STORAGE_ROOT``. GCS uses ``GCS_BUCKET`` and optional
    ``GCS_OBJECT_PREFIX``.

    **OpenAPI / docs:** set ``OPENAPI_ENABLED=false`` in production to disable ``/docs``,
    ``/redoc``, and ``/openapi.json``.

    **Uploads:** ``MAX_UPLOAD_BYTES`` caps admin suitability COG uploads (default ~100 MB).
    ``MAX_ENVIRONMENTAL_UPLOAD_BYTES`` caps project environmental (driver) COG uploads
    (default 1 GiB). Enforce in-process; also configure a reverse proxy or Cloud Run
    request size limits in production.
    """

    model_config = SettingsConfigDict(extra="ignore")

    cors_origins: str = Field(
        default=(
            "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,"
            "https://hsm-dashboard.web.app,https://hsm-dashboard.firebaseapp.com"
        ),
        description="Comma-separated origins for CORS (browser → API cross-origin).",
        validation_alias=AliasChoices("CORS_ORIGINS"),
    )
    cors_origin_regex: str | None = Field(
        default=None,
        description=(
            "Optional regex for dynamic CORS origins (for example Firebase PR previews). "
            "Applied in addition to CORS_ORIGINS."
        ),
        validation_alias=AliasChoices("CORS_ORIGIN_REGEX"),
    )

    google_cloud_project: str = Field(
        default="hsm-dashboard",
        description="GCP / Firebase project id used by the Firestore client.",
        validation_alias=AliasChoices("GOOGLE_CLOUD_PROJECT", "GCLOUD_PROJECT"),
    )

    firebase_project_id: str | None = Field(
        default=None,
        description=(
            "Firebase project id used by Firebase Admin token verification. "
            "If unset, falls back to GOOGLE_CLOUD_PROJECT."
        ),
        validation_alias=AliasChoices("FIREBASE_PROJECT_ID"),
    )

    firebase_auth_emulator_host: str | None = Field(
        default=None,
        description="Auth emulator host:port (set before Admin SDK init in dev).",
        validation_alias=AliasChoices("FIREBASE_AUTH_EMULATOR_HOST"),
    )

    firebase_web_api_key: str | None = Field(
        default=None,
        description=(
            "Firebase Web API key (Identity Toolkit). Required for POST /auth/token "
            "against production Auth; optional in dev when using the Auth emulator "
            "(defaults to a placeholder if unset)."
        ),
        validation_alias=AliasChoices("FIREBASE_WEB_API_KEY", "VITE_FIREBASE_API_KEY"),
    )

    storage_backend: str = Field(
        default="local",
        description="Object storage for admin uploads: 'local' or 'gcs'.",
        validation_alias=AliasChoices("STORAGE_BACKEND"),
    )

    local_storage_root: str = Field(
        default="/data",
        description="Filesystem root for suitability COGs when STORAGE_BACKEND=local.",
        validation_alias=AliasChoices("LOCAL_STORAGE_ROOT"),
    )

    gcs_bucket: str | None = Field(
        default=None,
        description="GCS bucket when STORAGE_BACKEND=gcs.",
        validation_alias=AliasChoices("GCS_BUCKET"),
    )

    gcs_object_prefix: str = Field(
        default="",
        description="Optional prefix inside the bucket (e.g. 'hsm/'); trailing slash optional.",
        validation_alias=AliasChoices("GCS_OBJECT_PREFIX"),
    )

    openapi_enabled: bool = Field(
        default=True,
        description="If false, disable OpenAPI schema and Swagger/ReDoc UIs.",
        # Include field name so Settings(openapi_enabled=False) and tests work; env OPENAPI_ENABLED still matches.
        validation_alias=AliasChoices("openapi_enabled", "OPENAPI_ENABLED"),
    )

    max_upload_bytes: int = Field(
        default=100 * 1024 * 1024,
        description="Maximum admin suitability COG upload size in bytes.",
        validation_alias=AliasChoices("MAX_UPLOAD_BYTES"),
        ge=1024,
    )

    max_environmental_upload_bytes: int = Field(
        default=1024 * 1024 * 1024,
        description="Maximum admin environmental (project driver) COG upload size in bytes.",
        validation_alias=AliasChoices("MAX_ENVIRONMENTAL_UPLOAD_BYTES"),
        ge=1024,
    )

    env_background_sample_rows: int = Field(
        default=256,
        description="Number of random pixels sampled from the environmental COG into the shared explainability background Parquet.",
        validation_alias=AliasChoices("ENV_BACKGROUND_SAMPLE_ROWS"),
        ge=8,
        le=50_000,
    )

    shap_background_max_rows: int = Field(
        default=512,
        description=(
            "Max rows read from explainability_background.parquet when running permutation SHAP "
            "on GET /models/{id}/point (deterministic head slice). Limits request-time CPU; "
            "raise for larger training backgrounds only if you accept longer point requests."
        ),
        validation_alias=AliasChoices("SHAP_BACKGROUND_MAX_ROWS"),
        ge=8,
        le=50_000,
    )

    point_inspect_timeout_seconds: float = Field(
        default=45.0,
        description=(
            "Wall-clock limit for synchronous GET /models/{id}/point work (suitability + env + SHAP). "
            "Returns 504 when exceeded; the worker thread may still finish briefly after the client disconnects."
        ),
        validation_alias=AliasChoices("POINT_INSPECT_TIMEOUT_SECONDS"),
        ge=5.0,
        le=300.0,
    )

