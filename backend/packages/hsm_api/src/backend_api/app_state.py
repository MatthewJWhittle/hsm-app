"""Types for FastAPI/Starlette ``app.state`` populated in ``lifespan`` (see ``main.create_app``)."""

from __future__ import annotations

from typing import Protocol

from fastapi import FastAPI

from backend_api.catalog_service import CatalogService
from hsm_core.artifact_read_runtime import ArtifactReadRuntime
from hsm_core.settings import Settings
from hsm_core.storage import ObjectStorage

_HSM_APP_STATE_ATTRS = (
    "settings",
    "catalog_service",
    "object_storage",
    "artifact_read_runtime",
)


def assert_hsm_app_state_attrs(app: FastAPI) -> None:
    """Fail fast at startup if ``lifespan`` did not assign every required ``app.state`` field."""
    for name in _HSM_APP_STATE_ATTRS:
        if not hasattr(app.state, name):
            raise RuntimeError(
                f"app.state missing {name!r} after lifespan startup (expected HsmAppState)"
            )


class HsmAppState(Protocol):
    """Structural type for attributes assigned on ``app.state`` during startup."""

    settings: Settings
    catalog_service: CatalogService
    object_storage: ObjectStorage
    artifact_read_runtime: ArtifactReadRuntime
