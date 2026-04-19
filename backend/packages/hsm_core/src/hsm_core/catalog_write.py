"""Firestore writes for catalog projects (shared API + worker)."""

from __future__ import annotations

from google.cloud import firestore

from hsm_core.catalog_collections import PROJECTS_COLLECTION_ID
from hsm_core.schemas_project import CatalogProject
from hsm_core.settings import Settings


def upsert_project(settings: Settings, project: CatalogProject) -> None:
    """Create or replace the ``projects/{project_id}`` document."""
    client = firestore.Client(project=settings.google_cloud_project)
    data = project.model_dump(exclude={"id", "band_inference_notes"}, exclude_none=True)
    client.collection(PROJECTS_COLLECTION_ID).document(project.id).set(data)
