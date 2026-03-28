"""Application settings (env / .env)."""

from __future__ import annotations

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App configuration.

    Environment variables use the ``CATALOG_*`` prefix as field names in uppercase
    (Pydantic Settings), e.g. ``CATALOG_BACKEND``, ``CATALOG_PATH``.

    **Catalog backend:** omit ``CATALOG_BACKEND`` in production to use ``firestore``.
    Set ``CATALOG_BACKEND=file`` in local Docker Compose (or ``.env``) for the JSON snapshot.
    """

    model_config = SettingsConfigDict(extra="ignore")

    catalog_backend: Literal["file", "firestore"] = "firestore"
    catalog_path: str = "/data/catalog/firestore_models.json"
