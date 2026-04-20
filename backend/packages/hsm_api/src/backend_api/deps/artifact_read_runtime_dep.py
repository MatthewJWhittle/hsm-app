"""Artifact read runtime (raster / columnar / opaque library-facing prep)."""

from __future__ import annotations

from typing import cast

from fastapi import Request

from backend_api.app_state import HsmAppState
from hsm_core.artifact_read_runtime import ArtifactReadRuntime


def get_artifact_read_runtime(request: Request) -> ArtifactReadRuntime:
    """Resolve runtime from ``app.state`` (set in ``main.create_app`` lifespan)."""
    return cast(HsmAppState, request.app.state).artifact_read_runtime
