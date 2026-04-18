"""Shared preflight for explainability background sampling from the environmental COG."""

from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException

from backend_api.api_errors import validation_error
from backend_api.catalog_service import CatalogService
from backend_api.project_manifest import resolve_env_cog_path_from_parts
from backend_api.schemas_project import CatalogProject


def env_cog_path_readable_for_sampling(abs_path: str) -> bool:
    """Local files must exist on disk; ``gs://`` URIs are assumed present after upload."""
    if abs_path.startswith("gs://"):
        return True
    return Path(abs_path).is_file()


def require_catalog_project_env_cog_for_explainability(
    catalog: CatalogService, project_id: str
) -> tuple[CatalogProject, str]:
    existing = catalog.get_project(project_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="project not found")

    artifact_root = existing.driver_artifact_root
    cog_path = existing.driver_cog_path
    band_defs = existing.environmental_band_definitions

    if not artifact_root or not cog_path:
        raise HTTPException(
            status_code=422,
            detail=validation_error(
                "ENV_COG_REQUIRED",
                "project has no environmental COG; upload one first",
            ),
        )
    if not band_defs:
        raise HTTPException(
            status_code=422,
            detail=validation_error(
                "BAND_DEFINITIONS_MISSING",
                "project has no environmental band definitions; save band names first",
            ),
        )

    abs_path = resolve_env_cog_path_from_parts(artifact_root, cog_path)
    if not abs_path:
        raise HTTPException(
            status_code=422,
            detail=validation_error(
                "ENV_COG_PATH_INVALID",
                "cannot resolve environmental COG path",
            ),
        )
    if not env_cog_path_readable_for_sampling(abs_path):
        raise HTTPException(
            status_code=422,
            detail=validation_error(
                "ENV_COG_NOT_ON_DISK",
                "environmental COG not found on server",
            ),
        )

    return existing, abs_path
