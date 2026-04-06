"""Validate model band indices against the catalog project's environmental manifest."""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend_api.model_effective_config import get_feature_band_indices
from backend_api.schemas import Model

if TYPE_CHECKING:
    from backend_api.catalog_service import CatalogService


def resolve_project_env_cog_absolute_path(project) -> str | None:
    """Absolute path to project environmental COG, or None."""
    return resolve_env_cog_path_from_parts(
        project.driver_artifact_root, project.driver_cog_path
    )


def resolve_env_cog_path_from_parts(
    artifact_root: str | None, driver_cog_path: str | None
) -> str | None:
    """Absolute path from storage root + relative COG path."""
    if not artifact_root or not driver_cog_path:
        return None
    root = artifact_root.rstrip("/")
    rel = driver_cog_path.strip()
    if rel.startswith("/"):
        return rel
    return f"{root}/{rel}"


def validate_model_bands_against_project_manifest(model: Model, catalog: "CatalogService") -> None:
    """
    If the model uses a project environmental stack and lists driver bands, require a
    project band manifest and indices that exist in it.

    Raises:
        ValueError: for HTTP 422 on admin save.
    """
    indices = get_feature_band_indices(model)
    if not indices or not model.project_id:
        return
    proj = catalog.get_project(model.project_id)
    if proj is None:
        return
    if not proj.driver_cog_path:
        return
    if not proj.environmental_band_definitions:
        raise ValueError(
            "This project has an environmental COG but no band definitions yet. "
            "Edit the project in Admin and save band names for each raster band."
        )
    by_idx = {d.index: d for d in proj.environmental_band_definitions}
    for idx in indices:
        if idx not in by_idx:
            raise ValueError(
                f"driver_band_index {idx} is not in the project's environmental band definitions"
            )
