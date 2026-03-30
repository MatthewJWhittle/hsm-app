"""Catalog loaded from Firestore (production or emulator via FIRESTORE_EMULATOR_HOST)."""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Protocol

# Firestore emulator often accepts connections a few seconds after the process starts.
_FIRESTORE_EMULATOR_READ_RETRIES = 15
_FIRESTORE_EMULATOR_READ_DELAY_SEC = 0.5

from google.cloud import firestore
from google.cloud.firestore_v1 import DocumentSnapshot
from pydantic import ValidationError

from backend_api.schemas import Model
from backend_api.schemas_project import CatalogProject
from backend_api.settings import Settings

logger = logging.getLogger(__name__)

# Single collection for Model documents (document id = Model.id).
MODELS_COLLECTION_ID = "models"
PROJECTS_COLLECTION_ID = "projects"

CATALOG_VALIDATION_DETAIL = (
    "Catalog data does not match the Model schema; fix Firestore documents or see server logs."
)
PROJECT_CATALOG_VALIDATION_DETAIL = (
    "Catalog data does not match the CatalogProject schema; fix Firestore documents or see server logs."
)


class CatalogService(Protocol):
    """Contract for catalog data (Firestore-backed)."""

    validation_error: str | None
    load_error: str | None
    models: list[Model]
    projects: list[CatalogProject]

    def get_model(self, model_id: str) -> Model | None:
        """Return one model by id, or ``None`` if not found."""

    def get_project(self, project_id: str) -> CatalogProject | None:
        """Return one catalog project by id, or ``None`` if not found."""


class FirestoreCatalogService:
    """Load catalog from Firestore (production or emulator via FIRESTORE_EMULATOR_HOST)."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self.validation_error: str | None = None
        self.load_error: str | None = None
        self.models: list[Model] = []
        self.projects: list[CatalogProject] = []
        self._models_by_id: dict[str, Model] = {}
        self._projects_by_id: dict[str, CatalogProject] = {}
        self._load()

    def reload(self) -> None:
        """Re-read Firestore after admin writes (same process)."""
        self.validation_error = None
        self.load_error = None
        self.models = []
        self.projects = []
        self._models_by_id = {}
        self._projects_by_id = {}
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

        proj_coll = client.collection(PROJECTS_COLLECTION_ID)
        coll = client.collection(MODELS_COLLECTION_ID)
        models: list[Model] = []
        projects: list[CatalogProject] = []
        use_emulator = bool(os.environ.get("FIRESTORE_EMULATOR_HOST"))
        max_attempts = (
            _FIRESTORE_EMULATOR_READ_RETRIES if use_emulator else 1
        )
        for attempt in range(max_attempts):
            try:
                models = []
                projects = []
                for doc in proj_coll.stream():
                    try:
                        payload = _snapshot_to_model_dict(doc)
                        projects.append(CatalogProject.model_validate(payload))
                    except ValidationError:
                        logger.exception(
                            "Firestore document %s is not a valid CatalogProject; fix catalog data",
                            doc.id,
                        )
                        self.validation_error = PROJECT_CATALOG_VALIDATION_DETAIL
                        self.models = []
                        self.projects = []
                        self._models_by_id = {}
                        self._projects_by_id = {}
                        return
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
                        self.projects = []
                        self._models_by_id = {}
                        self._projects_by_id = {}
                        return
                break
            except Exception as e:
                if attempt == max_attempts - 1:
                    logger.exception("Failed to read Firestore catalog")
                    self.load_error = (
                        "Could not read catalog from Firestore; see server logs for details."
                    )
                    return
                logger.warning(
                    "Firestore catalog read failed (attempt %s/%s), retrying: %s",
                    attempt + 1,
                    max_attempts,
                    e,
                )
                time.sleep(_FIRESTORE_EMULATOR_READ_DELAY_SEC)

        models.sort(key=lambda m: m.id)
        projects.sort(key=lambda p: p.id)
        self.models = models
        self.projects = projects
        self._models_by_id = {m.id: m for m in models}
        self._projects_by_id = {p.id: p for p in projects}
        if self.load_error is None:
            logger.info(
                "Loaded %s project(s) from %r and %s model(s) from %r",
                len(self.projects),
                PROJECTS_COLLECTION_ID,
                len(self.models),
                MODELS_COLLECTION_ID,
            )

    def get_model(self, model_id: str) -> Model | None:
        return self._models_by_id.get(model_id)

    def get_project(self, project_id: str) -> CatalogProject | None:
        return self._projects_by_id.get(project_id)


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


def build_catalog_service(settings: Settings) -> CatalogService:
    return FirestoreCatalogService(settings)
