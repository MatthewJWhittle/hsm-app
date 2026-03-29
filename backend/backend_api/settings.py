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
    emulator. Omit in production (use Application Default Credentials).

    **CORS:** ``CORS_ORIGINS`` is a comma-separated list of allowed browser origins.
    Defaults include local dev and Firebase Hosting URLs for this project.

    Catalog documents use collection id ``models`` (``MODELS_COLLECTION_ID`` in
    ``catalog_service``).

    **Storage (admin uploads):** ``STORAGE_BACKEND`` is ``local`` (default) or ``gcs``.
    Local writes use ``LOCAL_STORAGE_ROOT``. GCS uses ``GCS_BUCKET`` and optional
    ``GCS_OBJECT_PREFIX``.
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

    google_cloud_project: str = Field(
        default="hsm-dashboard",
        description="GCP / Firebase project id used by the Firestore client.",
        validation_alias=AliasChoices("GOOGLE_CLOUD_PROJECT", "GCLOUD_PROJECT"),
    )

    firebase_auth_emulator_host: str | None = Field(
        default=None,
        description="Auth emulator host:port (set before Admin SDK init in dev).",
        validation_alias=AliasChoices("FIREBASE_AUTH_EMULATOR_HOST"),
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

