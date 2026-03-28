"""Catalog backends: file snapshot (local dev) and Firestore (production)."""

from __future__ import annotations

import logging
from typing import Any, Protocol

from google.cloud import firestore
from google.cloud.firestore_v1 import DocumentSnapshot
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
        except ValueError as e:
            logger.exception("Catalog JSON has invalid shape for %s", self.path)
            self.validation_error = str(e)
            self.models = []
            return
        # If multiple rows share the same `id`, the last one wins for lookup only; the
        # list from GET /models may still contain duplicates until ingestion enforces uniqueness.
        self._models_by_id = {m.id: m for m in self.models}

    def get_model(self, model_id: str) -> Model | None:
        return self._models_by_id.get(model_id)

    def is_missing_catalog_file(self) -> bool:
        return self.raw is None and self.load_error is None


def _snapshot_to_model_dict(doc: DocumentSnapshot) -> dict[str, Any]:
    """Merge Firestore document data with document id (Model.id)."""
    data = doc.to_dict()
    if not data:
        payload: dict[str, Any] = {"id": doc.id}
    else:
        payload = {k: _sanitize_firestore_value(v) for k, v in data.items()}
        payload["id"] = doc.id
    return payload


def _sanitize_firestore_value(value: Any) -> Any:
    """Avoid passing Firestore-only types into Pydantic where possible."""
    if hasattr(value, "isoformat") and callable(value.isoformat):
        try:
            return value.isoformat()
        except (TypeError, ValueError):
            return str(value)
    if isinstance(value, dict):
        return {k: _sanitize_firestore_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize_firestore_value(v) for v in value]
    return value


class FirestoreCatalogService:
    """Load catalog from Firestore (production or emulator via FIRESTORE_EMULATOR_HOST)."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self.raw: dict | None = None
        self.validation_error: str | None = None
        self.load_error: str | None = None
        self.models: list[Model] = []
        self._models_by_id: dict[str, Model] = {}
        self._load()

    def _load(self) -> None:
        try:
            client = firestore.Client(project=self._settings.google_cloud_project)
        except Exception:
            logger.exception("Failed to create Firestore client")
            self.load_error = (
                "Could not connect to Firestore; check GOOGLE_CLOUD_PROJECT / GCLOUD_PROJECT "
                "and credentials (or FIRESTORE_EMULATOR_HOST for local emulator)."
            )
            return

        coll = client.collection(self._settings.firestore_models_collection)
        models: list[Model] = []
        try:
            for doc in coll.stream():
                try:
                    payload = _snapshot_to_model_dict(doc)
                    models.append(Model.model_validate(payload))
                except ValidationError:
                    logger.exception(
                        "Firestore document %s is not a valid Model; fix catalog data",
                        doc.id,
                    )
                    self.validation_error = CATALOG_VALIDATION_DETAIL
                    self.models = []
                    self._models_by_id = {}
                    return
        except Exception:
            logger.exception("Failed to read Firestore catalog")
            self.load_error = (
                "Could not read catalog from Firestore; see server logs for details."
            )
            return

        models.sort(key=lambda m: m.id)
        self.models = models
        self._models_by_id = {m.id: m for m in models}
        if self.load_error is None:
            logger.info(
                "Loaded %s model(s) from Firestore collection %r",
                len(self.models),
                self._settings.firestore_models_collection,
            )

    def get_model(self, model_id: str) -> Model | None:
        return self._models_by_id.get(model_id)

    def is_missing_catalog_file(self) -> bool:
        return False


def build_catalog_service(settings: Settings) -> CatalogService:
    if settings.catalog_backend == "firestore":
        return FirestoreCatalogService(settings)
    return FileCatalogService(settings.catalog_path)
