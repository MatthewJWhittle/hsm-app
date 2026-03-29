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

