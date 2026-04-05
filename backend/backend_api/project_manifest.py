"""Align model ``driver_config`` with catalog project environmental band definitions."""

from __future__ import annotations

from typing import TYPE_CHECKING

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
    indices = model.driver_band_indices
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


def enrich_model_driver_config_from_project(model: Model, catalog: "CatalogService") -> Model:
    """
    Set ``driver_config.feature_names`` and ``driver_config.band_labels`` from the project
    manifest in the same order as ``driver_band_indices``.
    """
    indices = model.driver_band_indices
    if not indices or not model.project_id:
        return model
    proj = catalog.get_project(model.project_id)
    if not proj or not proj.environmental_band_definitions:
        return model
    by_idx = {d.index: d for d in proj.environmental_band_definitions}
    names: list[str] = []
    labels: list[str] = []
    for idx in indices:
        d = by_idx.get(idx)
        if d is None:
            continue
        names.append(d.name)
        labels.append(d.label.strip() if d.label else d.name)
    if len(names) != len(indices):
        return model
    dc = dict(model.driver_config or {})
    dc["feature_names"] = names
    dc["band_labels"] = labels
    return model.model_copy(update={"driver_config": dc})
