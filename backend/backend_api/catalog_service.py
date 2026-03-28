"""Catalog backends: file snapshot (local dev) and Firestore (production)."""

from __future__ import annotations

import logging
from typing import Protocol

from pydantic import ValidationError

from backend_api.catalog import catalog_to_models, try_load_catalog_json
from backend_api.schemas import Model
from backend_api.settings import Settings

logger = logging.getLogger(__name__)

CATALOG_VALIDATION_DETAIL = (
    "Catalog file does not match the Model schema; fix the JSON or see server logs."
)


class CatalogService(Protocol):
    """Contract for catalog data (file snapshot, Firestore, tests, etc.)."""

    raw: dict | None
    validation_error: str | None
    load_error: str | None
    models: list[Model]

    def get_model(self, model_id: str) -> Model | None:
        """Return one model by id, or ``None`` if not found."""

    def is_missing_catalog_file(self) -> bool:
        """True when the file-backed catalog path has no file (404 for empty list)."""


class FileCatalogService:
    """Load catalog once from a Firestore-shaped JSON file on disk."""

    def __init__(self, catalog_path: str) -> None:
        self.path = catalog_path
        self.raw: dict | None = None
        self.load_error: str | None = None
        self.validation_error: str | None = None
        self.models: list[Model] = []
        self._models_by_id: dict[str, Model] = {}
        self._load()

    def _load(self) -> None:
        raw, err = try_load_catalog_json(self.path)
        self.raw = raw
        if err is not None:
            self.load_error = err
            return
        if raw is None:
            return
        try:
            self.models = catalog_to_models(raw)
        except ValidationError:
            logger.exception("Catalog JSON failed Model validation for %s", self.path)
            self.validation_error = CATALOG_VALIDATION_DETAIL
            self.models = []
            return
        # If multiple rows share the same `id`, the last one wins for lookup only; the
        # list from GET /models may still contain duplicates until ingestion enforces uniqueness.
        self._models_by_id = {m.id: m for m in self.models}

    def get_model(self, model_id: str) -> Model | None:
        return self._models_by_id.get(model_id)

    def is_missing_catalog_file(self) -> bool:
        return self.raw is None and self.load_error is None


class FirestoreCatalogService:
    """Firestore-backed catalog (production). Stub until Firestore is wired."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self.raw: dict | None = None
        self.validation_error: str | None = None
        self.load_error: str | None = (
            "Firestore catalog backend is not implemented yet; "
            "use CATALOG_BACKEND=file for local dev."
        )
        self.models: list[Model] = []
        logger.warning(
            "CATALOG_BACKEND=firestore is selected but FirestoreCatalogService is still a stub"
        )

    def get_model(self, model_id: str) -> Model | None:
        return None

    def is_missing_catalog_file(self) -> bool:
        return False


def build_catalog_service(settings: Settings) -> CatalogService:
    if settings.catalog_backend == "firestore":
        return FirestoreCatalogService(settings)
    return FileCatalogService(settings.catalog_path)
