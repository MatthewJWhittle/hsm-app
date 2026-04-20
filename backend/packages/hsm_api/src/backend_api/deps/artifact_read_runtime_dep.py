"""Artifact read runtime (raster / columnar / opaque library-facing prep)."""

from __future__ import annotations

from fastapi import Request

from hsm_core.artifact_read_runtime import ArtifactReadRuntime


def get_artifact_read_runtime(request: Request) -> ArtifactReadRuntime:
    return request.app.state.artifact_read_runtime
