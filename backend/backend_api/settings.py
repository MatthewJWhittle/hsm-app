"""Application settings (env / .env)."""

from __future__ import annotations

from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App configuration.

    Environment variables use the ``CATALOG_*`` prefix as field names in uppercase
    (Pydantic Settings), e.g. ``CATALOG_BACKEND``, ``CATALOG_PATH``.

    **Catalog backend:** omit ``CATALOG_BACKEND`` in production to use ``firestore``.
    Set ``CATALOG_BACKEND=file`` in local Docker Compose (or ``.env``) for the JSON snapshot.

    **Firestore:** set ``GOOGLE_CLOUD_PROJECT`` (or ``GCLOUD_PROJECT``) to your Firebase/GCP project id.
    For the **Firestore emulator**, set ``FIRESTORE_EMULATOR_HOST`` (e.g. ``127.0.0.1:8085``);
    the client uses it automatically. From Docker Desktop, use ``host.docker.internal:8085`` when
    emulators run on the host.
    """

    model_config = SettingsConfigDict(extra="ignore")

    catalog_backend: Literal["file", "firestore"] = "firestore"
    catalog_path: str = "/data/catalog/firestore_models.json"

    google_cloud_project: str = Field(
        default="hsm-dashboard",
        description="GCP / Firebase project id used by the Firestore client.",
        validation_alias=AliasChoices("GOOGLE_CLOUD_PROJECT", "GCLOUD_PROJECT"),
    )
    firestore_models_collection: str = Field(
        default="models",
        description="Firestore collection id for catalog Model documents (document id = Model.id).",
        validation_alias="FIRESTORE_MODELS_COLLECTION",
    )
