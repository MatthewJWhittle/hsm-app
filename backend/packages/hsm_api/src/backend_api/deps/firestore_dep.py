"""Firestore Admin client scoped to the API's GCP project."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from google.cloud import firestore

from backend_api.deps.settings_dep import get_settings
from hsm_core.settings import Settings


def get_firestore_client(
    settings: Annotated[Settings, Depends(get_settings)],
) -> firestore.Client:
    return firestore.Client(project=settings.google_cloud_project)
