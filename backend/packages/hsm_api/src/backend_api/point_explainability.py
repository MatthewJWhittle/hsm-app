"""Point-level SHAP explainability — model + background from effective config (``metadata.analysis`` + project)."""

from __future__ import annotations

import logging
import pickle
import threading
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
import shap

from backend_api.explainability_runtime_cache import ShapExplainerBundle, get_or_build_shap_bundle
from backend_api.feature_band_names import FeatureBandNamesValidationError
from backend_api.model_effective_config import get_effective_driver_config, get_feature_band_indices
from backend_api.point_sampling import PointSamplingError
from backend_api.schemas import DriverVariable, Model
from hsm_core.artifact_read_runtime import ArtifactReadRuntime
from hsm_core.env_cog_paths import artifact_uri_exists, resolve_artifact_uri

if TYPE_CHECKING:
    from backend_api.catalog_service import CatalogService

logger = logging.getLogger(__name__)

_MAX_CONCURRENT_SHAP_COMPUTES = 2
_shap_compute_semaphore = threading.BoundedSemaphore(_MAX_CONCURRENT_SHAP_COMPUTES)


def cap_shap_background_rows(background: pd.DataFrame, max_rows: int) -> pd.DataFrame:
    """
    Deterministically limit background size for permutation SHAP (first ``max_rows`` rows).

    Parquet row order is stable for a given file; this bounds request-time work without
    changing smaller backgrounds.
    """
    if max_rows < 1:
        return background
    n = len(background)
    if n <= max_rows:
        return background
    logger.info(
        "SHAP explainability background truncated from %s to %s rows (SHAP_BACKGROUND_MAX_ROWS)",
        n,
        max_rows,
    )
    return background.iloc[:max_rows].copy()


def _background_storage_root(model: Model, dc: dict) -> str:
    """Project shared background vs legacy per-model folder."""
    r = dc.get("explainability_background_artifact_root")
    if isinstance(r, str) and r.strip():
        return r.strip()
    return model.artifact_root


def _load_classifier_or_raise(model_path: str, artifact_read: ArtifactReadRuntime) -> object:
    try:
        raw = artifact_read.read_opaque_bytes(model_path)
        return pickle.loads(raw)
    except ModuleNotFoundError as e:
        mod = getattr(e, "name", None) or str(e)
        logger.warning(
            "Explainability pickle import failed (missing module %s)",
            mod,
            exc_info=False,
        )
        raise PointSamplingError(
            "Serialized estimator references Python code not available on this server "
            f"(missing import {mod!r}). Train with in-container packages only, or export a "
            "pipeline using standard sklearn / dependencies present in the API image.",
            code="EXPLAINABILITY_PICKLE_IMPORT",
        ) from None
    except Exception:
        logger.exception("Failed to load explainability model")
        raise PointSamplingError(
            "explainability model could not be loaded",
            code="EXPLAINABILITY_PICKLE_LOAD",
        ) from None


def _materialize_shap_explainer_bundle(
    model: Model,
    dc: dict,
    model_path: str,
    bg_path: str,
    max_background_rows: int,
    artifact_read: ArtifactReadRuntime,
) -> ShapExplainerBundle:
    """Load pickle + capped background and build ``shap.Explainer`` (no query row yet)."""
    clf = _load_classifier_or_raise(model_path, artifact_read)

    try:
        background = artifact_read.read_explainability_background_parquet(bg_path)
    except Exception:
        logger.exception("Failed to read explainability background")
        raise PointSamplingError("explainability background could not be read") from None

    fnames = [str(x) for x in (dc.get("feature_names") or [])]
    missing_bg = [c for c in fnames if c not in background.columns]
    if missing_bg:
        raise PointSamplingError(f"background parquet missing columns: {missing_bg!r}")

    background = background[fnames]
    background = cap_shap_background_rows(background, max_background_rows)
    pos = int(dc.get("explainability_positive_class", 1))

    def predict_fn(data: object) -> np.ndarray:
        if isinstance(data, pd.DataFrame):
            X = data.reindex(columns=fnames)
        else:
            arr = np.asarray(data, dtype=np.float64)
            if arr.ndim == 1:
                arr = arr.reshape(1, -1)
            if arr.shape[1] != len(fnames):
                raise PointSamplingError(
                    "explainability model input width "
                    f"({arr.shape[1]}) does not match configured feature count ({len(fnames)})"
                )
            X = pd.DataFrame(arr, columns=fnames)
        proba = clf.predict_proba(X)
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
    except Exception:
        logger.exception("Failed to construct SHAP explainer")
        raise PointSamplingError("could not build variable influence explainer") from None

    bl = dc.get("band_labels")
    band_labels: list | None = bl if isinstance(bl, list) else None
    return ShapExplainerBundle(
        explainer=explainer,
        fnames=fnames,
        pos=pos,
        band_labels=band_labels,
    )


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
    *,
    max_background_rows: int,
    artifact_read: ArtifactReadRuntime,
) -> list[DriverVariable]:
    """
    Load sklearn pipeline + background from ``artifact_root``, run permutation SHAP
    for one row, return all configured feature contributions ranked by |contribution|.

    ``feature_row`` columns must match training feature order (``feature_names``).

    ``max_background_rows`` caps rows loaded from the background Parquet for SHAP (see Settings).
    Explainer construction is cached per model when artifact mtimes are unchanged.
    """
    mp = dc.get("explainability_model_path")
    bp = dc.get("explainability_background_path")
    if not isinstance(mp, str) or not isinstance(bp, str):
        return []

    model_path = resolve_artifact_uri(model.artifact_root, mp)
    bg_path = resolve_artifact_uri(_background_storage_root(model, dc), bp)

    if not artifact_uri_exists(model_path):
        raise PointSamplingError("explainability model file not found on server")
    if not artifact_uri_exists(bg_path):
        raise PointSamplingError("explainability background file not found on server")

    acquired = _shap_compute_semaphore.acquire(blocking=False)
    if not acquired:
        raise PointSamplingError(
            "explainability is temporarily busy; retry shortly",
            code="EXPLAINABILITY_BUSY",
        )
    try:
        bundle = get_or_build_shap_bundle(
            model.id,
            model_path,
            bg_path,
            max_background_rows,
            artifact_read,
            lambda: _materialize_shap_explainer_bundle(
                model, dc, model_path, bg_path, max_background_rows, artifact_read
            ),
        )
        fnames = bundle.fnames
        feature_row = feature_row.reindex(columns=fnames)

        try:
            shap_values = bundle.explainer(feature_row)
        except Exception:
            logger.exception("SHAP explain failed")
            raise PointSamplingError(
                "could not compute variable influence at this location"
            ) from None
    finally:
        _shap_compute_semaphore.release()
    vals = np.asarray(shap_values.values)
    if vals.ndim == 2:
        row = vals[0]
    else:
        row = vals.flatten()

    if row.shape[0] != len(fnames):
        raise PointSamplingError("SHAP output size does not match feature list")

    pairs = list(zip(fnames, row.tolist()))
    pairs.sort(key=lambda x: abs(float(x[1])), reverse=True)

    band_labels = bundle.band_labels
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


def warm_explainability_cache(
    model: Model,
    catalog: "CatalogService",
    *,
    max_background_rows: int,
    artifact_read: ArtifactReadRuntime,
) -> None:
    """
    Load and cache SHAP explainer artifacts for a model (no query row).

    No-op when explainability is not configured or files are missing (does not raise).
    """
    if not explainability_configured(model, catalog):
        return
    try:
        dc = get_effective_driver_config(model, catalog)
    except FeatureBandNamesValidationError:
        return
    mp = dc.get("explainability_model_path")
    bp = dc.get("explainability_background_path")
    if not isinstance(mp, str) or not isinstance(bp, str):
        return
    model_path = resolve_artifact_uri(model.artifact_root, mp)
    bg_path = resolve_artifact_uri(_background_storage_root(model, dc), bp)
    if not artifact_uri_exists(model_path) or not artifact_uri_exists(bg_path):
        return
    try:
        get_or_build_shap_bundle(
            model.id,
            model_path,
            bg_path,
            max_background_rows,
            artifact_read,
            lambda: _materialize_shap_explainer_bundle(
                model, dc, model_path, bg_path, max_background_rows, artifact_read
            ),
        )
    except PointSamplingError:
        logger.debug("explainability warm skipped for model %s", model.id, exc_info=True)


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
    mpath = resolve_artifact_uri(model.artifact_root, mp)
    bpath = resolve_artifact_uri(_background_storage_root(model, dc), bp)
    if not artifact_uri_exists(mpath):
        raise ValueError(f"serialized model file not found at {mp!r}")
    if not artifact_uri_exists(bpath):
        raise ValueError(f"explainability background file not found at {bp!r}")
