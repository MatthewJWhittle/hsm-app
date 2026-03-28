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

    Catalog documents use collection id ``models`` (``MODELS_COLLECTION_ID`` in
    ``catalog_service``).
    """

    model_config = SettingsConfigDict(extra="ignore")

    google_cloud_project: str = Field(
        default="hsm-dashboard",
        description="GCP / Firebase project id used by the Firestore client.",
        validation_alias=AliasChoices("GOOGLE_CLOUD_PROJECT", "GCLOUD_PROJECT"),
    )

