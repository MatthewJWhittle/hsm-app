"""Point-level SHAP explainability — model + background from effective config (``metadata.analysis`` + project)."""

from __future__ import annotations

import logging
import pickle
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
import shap

from backend_api.feature_band_names import FeatureBandNamesValidationError
from backend_api.model_effective_config import get_effective_driver_config, get_feature_band_indices
from backend_api.point_sampling import PointSamplingError
from backend_api.schemas import DriverVariable, Model

if TYPE_CHECKING:
    from backend_api.catalog_service import CatalogService

logger = logging.getLogger(__name__)

TOP_INFLUENCE_DRIVERS = 8


def _background_storage_root(model: Model, dc: dict) -> str:
    """Project shared background vs legacy per-model folder."""
    r = dc.get("explainability_background_artifact_root")
    if isinstance(r, str) and r.strip():
        return r.strip()
    return model.artifact_root


def _resolve_artifact_file(artifact_root: str, rel: str) -> Path:
    """Resolve path under ``artifact_root``; reject path traversal."""
    rel = rel.strip()
    if not rel:
        raise ValueError("empty path")
    if rel.startswith("/"):
        p = Path(rel)
    else:
        parts = Path(rel).parts
        if ".." in parts:
            raise ValueError("path must not contain '..'")
        p = (Path(artifact_root).resolve() / rel).resolve()
    return p


def explainability_configured(model: Model, catalog: "CatalogService") -> bool:
    """True when serialized model + background + feature_names are available for SHAP."""
    dc = get_effective_driver_config(model, catalog)
    mp = dc.get("explainability_model_path")
    bp = dc.get("explainability_background_path")
    fn = dc.get("feature_names")
    return bool(
        isinstance(mp, str)
        and mp.strip()
        and isinstance(bp, str)
        and bp.strip()
        and isinstance(fn, list)
        and len(fn) > 0
        and all(isinstance(x, (str, int, float)) for x in fn)
    )


def compute_shap_driver_variables(
    model: Model,
    feature_row: pd.DataFrame,
    dc: dict,
) -> list[DriverVariable]:
    """
    Load sklearn pipeline + background from ``artifact_root``, run permutation SHAP
    for one row, return top drivers by |contribution|.

    ``feature_row`` columns must match training feature order (``feature_names``).
    """
    mp = dc.get("explainability_model_path")
    bp = dc.get("explainability_background_path")
    if not isinstance(mp, str) or not isinstance(bp, str):
        return []

    model_path = _resolve_artifact_file(model.artifact_root, mp)
    bg_path = _resolve_artifact_file(_background_storage_root(model, dc), bp)

    if not model_path.is_file():
        raise PointSamplingError("explainability model file not found on server")
    if not bg_path.is_file():
        raise PointSamplingError("explainability background file not found on server")

    try:
        with open(model_path, "rb") as f:
            clf = pickle.load(f)
    except Exception as e:
        logger.exception("Failed to load explainability model")
        raise PointSamplingError("explainability model could not be loaded") from e

    try:
        background = pd.read_parquet(bg_path)
    except Exception as e:
        logger.exception("Failed to read explainability background")
        raise PointSamplingError("explainability background could not be read") from e

    fnames = [str(x) for x in (dc.get("feature_names") or [])]
    if list(feature_row.columns) != fnames:
        feature_row = feature_row[fnames]

    missing_bg = [c for c in fnames if c not in background.columns]
    if missing_bg:
        raise PointSamplingError(
            f"background parquet missing columns: {missing_bg!r}"
        )

    background = background[fnames]
    pos = int(dc.get("explainability_positive_class", 1))

    def predict_fn(data: pd.DataFrame) -> np.ndarray:
        arr = np.asarray(data, dtype=np.float64)
        proba = clf.predict_proba(arr)
        if proba.shape[1] <= pos:
            raise PointSamplingError("model output does not support configured positive class index")
        return proba[:, pos]

    try:
        explainer = shap.Explainer(
            predict_fn,
            background,
            algorithm="permutation",
            model_output="probability",
        )
        shap_values = explainer(feature_row)
    except Exception as e:
        logger.exception("SHAP explain failed")
        raise PointSamplingError("could not compute variable influence at this location") from e

    vals = np.asarray(shap_values.values)
    if vals.ndim == 2:
        row = vals[0]
    else:
        row = vals.flatten()

    if row.shape[0] != len(fnames):
        raise PointSamplingError("SHAP output size does not match feature list")

    pairs = list(zip(fnames, row.tolist()))
    pairs.sort(key=lambda x: abs(float(x[1])), reverse=True)
    pairs = pairs[:TOP_INFLUENCE_DRIVERS]

    band_labels = dc.get("band_labels")
    name_to_display: dict[str, str] = {}
    if isinstance(band_labels, list) and len(band_labels) == len(fnames):
        for i, fname in enumerate(fnames):
            bl = band_labels[i]
            if isinstance(bl, str) and bl.strip():
                name_to_display[str(fname)] = bl.strip()

    drivers: list[DriverVariable] = []
    for name, phi in pairs:
        phi_f = float(phi)
        if phi_f > 0:
            direction = "increase"
        elif phi_f < 0:
            direction = "decrease"
        else:
            direction = "neutral"
        dn = name_to_display.get(str(name))
        drivers.append(
            DriverVariable(
                name=name,
                direction=direction,
                magnitude=phi_f,
                label=f"{phi_f:+.4g}",
                display_name=dn if dn and dn != str(name) else None,
            )
        )
    return drivers


def validate_explainability_artifacts_for_model(
    model: Model, catalog: "CatalogService"
) -> None:
    """
    When explainability is configured, ensure feature list aligns with bands and files exist.

    Raises:
        ValueError: for HTTP 422 on admin save.
    """
    if not explainability_configured(model, catalog):
        return
    try:
        indices = get_feature_band_indices(model, catalog)
    except FeatureBandNamesValidationError as e:
        raise ValueError(
            "feature_band_names do not match the project environmental manifest"
        ) from e
    dc = get_effective_driver_config(model, catalog)
    fnames = dc.get("feature_names")
    if not isinstance(fnames, list) or len(fnames) != len(indices):
        raise ValueError(
            "explainability requires feature_names with the same length as feature_band_names"
        )
    mp = dc.get("explainability_model_path")
    bp = dc.get("explainability_background_path")
    if not isinstance(mp, str) or not isinstance(bp, str):
        raise ValueError("serialized model path and explainability background path must be strings")
    mpath = _resolve_artifact_file(model.artifact_root, mp)
    bpath = _resolve_artifact_file(_background_storage_root(model, dc), bp)
    if not mpath.is_file():
        raise ValueError(f"serialized model file not found at {mp!r}")
    if not bpath.is_file():
        raise ValueError(f"explainability background file not found at {bp!r}")
