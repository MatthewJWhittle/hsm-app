"""Validate model feature band names against the catalog project's environmental manifest."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import HTTPException

from backend_api.feature_band_names import (
    FeatureBandNamesValidationError,
    resolve_feature_band_names_to_indices,
)
from backend_api.schemas import Model
from hsm_core.env_cog_paths import resolve_env_cog_path_from_parts

if TYPE_CHECKING:
    from backend_api.catalog_service import CatalogService


def resolve_project_env_cog_absolute_path(project) -> str | None:
    """Absolute path to project environmental COG, or None."""
    return resolve_env_cog_path_from_parts(
        project.driver_artifact_root, project.driver_cog_path
    )


def validate_model_feature_bands_for_admin(model: Model, catalog: "CatalogService") -> None:
    """
    When ``metadata.analysis.feature_band_names`` is set, ensure names resolve against the
    project manifest. Raises ``HTTPException`` 400 with structured detail when invalid.

    Raises:
        ValueError: for HTTP 422 on admin save (missing manifest when COG exists, etc.).
    """
    analysis = model.metadata.analysis if model.metadata else None
    names = analysis.feature_band_names if analysis else None
    if not names:
        return
    if not model.project_id:
        raise ValueError("feature_band_names requires project_id")
    proj = catalog.get_project(model.project_id)
    if proj is None:
        return
    if proj.driver_cog_path and not proj.environmental_band_definitions:
        raise ValueError(
            "This project has an environmental COG but no band definitions yet. "
            "Edit the project in Admin and save band names for each raster band."
        )
    if not proj.environmental_band_definitions:
        raise ValueError(
            "feature_band_names requires project environmental_band_definitions on the parent project"
        )
    try:
        resolve_feature_band_names_to_indices(names, proj.environmental_band_definitions)
    except FeatureBandNamesValidationError as e:
        raise HTTPException(status_code=400, detail=e.detail) from e
