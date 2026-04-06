"""Resolve enriched runtime config from ``Model.metadata`` + catalog (replaces persisted ``driver_config``)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend_api.schemas import Model

if TYPE_CHECKING:
    from backend_api.catalog_service import CatalogService


def get_feature_band_indices(model: Model) -> list[int]:
    """0-based environmental COG band indices for this model (feature order)."""
    if model.metadata and model.metadata.analysis and model.metadata.analysis.feature_band_indices:
        return list(model.metadata.analysis.feature_band_indices)
    return []


def get_effective_driver_config(model: Model, catalog: "CatalogService") -> dict:
    """
    Build the same key shape the point pipeline used when ``driver_config`` was persisted:
    ``feature_names``, ``band_labels``, ``band_descriptions``, explainability paths, etc.
    """
    dc: dict = {}
    analysis = model.metadata.analysis if model.metadata else None
    indices = get_feature_band_indices(model)

    if analysis:
        if analysis.serialized_model_path and str(analysis.serialized_model_path).strip():
            dc["explainability_model_path"] = analysis.serialized_model_path.strip()
        if analysis.positive_class_index is not None:
            dc["explainability_positive_class"] = analysis.positive_class_index
        else:
            dc["explainability_positive_class"] = 1
        if analysis.driver_cog_path and str(analysis.driver_cog_path).strip():
            dc["driver_cog_path"] = analysis.driver_cog_path.strip()

    if not indices or not model.project_id:
        return dc

    proj = catalog.get_project(model.project_id)
    if not proj or not proj.environmental_band_definitions:
        return dc

    by_idx = {d.index: d for d in proj.environmental_band_definitions}
    names: list[str] = []
    labels: list[str] = []
    descriptions: list[str | None] = []
    for idx in indices:
        d = by_idx.get(idx)
        if d is None:
            continue
        names.append(d.name)
        labels.append(d.label.strip() if d.label else d.name)
        if d.description is not None and str(d.description).strip():
            descriptions.append(str(d.description).strip())
        else:
            descriptions.append(None)

    if len(names) != len(indices):
        return dc

    dc["feature_names"] = names
    dc["band_labels"] = labels
    if any(x is not None for x in descriptions):
        dc["band_descriptions"] = descriptions
    else:
        dc.pop("band_descriptions", None)

    if proj.explainability_background_path and proj.driver_artifact_root:
        dc["explainability_background_path"] = proj.explainability_background_path
        dc["explainability_background_artifact_root"] = proj.driver_artifact_root
    else:
        dc.pop("explainability_background_artifact_root", None)

    return dc
