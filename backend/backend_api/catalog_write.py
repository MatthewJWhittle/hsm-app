"""Firestore writes for catalog (admin)."""

from __future__ import annotations

from google.cloud import firestore

from backend_api.catalog_service import MODELS_COLLECTION_ID, PROJECTS_COLLECTION_ID
from backend_api.schemas import Model
from backend_api.schemas_project import CatalogProject
from backend_api.settings import Settings


def upsert_model(settings: Settings, model: Model) -> None:
    """Create or replace the ``models/{model_id}`` document."""
    client = firestore.Client(project=settings.google_cloud_project)
    data = model.model_dump(exclude={"id"}, exclude_none=True)
    client.collection(MODELS_COLLECTION_ID).document(model.id).set(data)


def upsert_project(settings: Settings, project: CatalogProject) -> None:
    """Create or replace the ``projects/{project_id}`` document."""
    client = firestore.Client(project=settings.google_cloud_project)
    data = project.model_dump(exclude={"id"}, exclude_none=True)
    client.collection(PROJECTS_COLLECTION_ID).document(project.id).set(data)
