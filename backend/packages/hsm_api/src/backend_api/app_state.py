"""Types for FastAPI/Starlette ``app.state`` populated in ``lifespan`` (see ``main.create_app``)."""

from __future__ import annotations

from typing import Protocol

from backend_api.catalog_service import CatalogService
from hsm_core.artifact_read_runtime import ArtifactReadRuntime
from hsm_core.settings import Settings
from hsm_core.storage import ObjectStorage


class HsmAppState(Protocol):
    """Structural type for attributes assigned on ``app.state`` during startup."""

    settings: Settings
    catalog_service: CatalogService
    object_storage: ObjectStorage
    artifact_read_runtime: ArtifactReadRuntime
