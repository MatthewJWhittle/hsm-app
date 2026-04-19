"""Explainability pickle load errors (custom training modules missing on server)."""

from unittest.mock import mock_open, patch

import pandas as pd
import pytest

from backend_api.point_explainability import compute_shap_driver_variables
from backend_api.point_sampling import PointSamplingError
from backend_api.schemas import Model, ModelAnalysis, ModelMetadata


def _minimal_model() -> Model:
    return Model(
        id="m1",
        project_id="p1",
        species="Bat",
        activity="Roost",
        artifact_root="/artifacts",
        suitability_cog_path="s.tif",
        metadata=ModelMetadata(
            analysis=ModelAnalysis(serialized_model_path="model.pkl"),
        ),
    )


def test_pickle_module_not_found_clear_error() -> None:
    model = _minimal_model()
    dc = {
        "explainability_model_path": "model.pkl",
        "explainability_background_path": "bg.parquet",
        "explainability_background_artifact_root": "/artifacts",
        "feature_names": ["a"],
        "band_labels": ["A"],
    }
    feature_row = pd.DataFrame([[0.5]], columns=["a"])
    e = ModuleNotFoundError("No module named 'sdm'")
    e.name = "sdm"  # type: ignore[attr-defined]

    with (
        patch(
            "backend_api.point_explainability.resolve_artifact_uri",
            side_effect=["/artifacts/model.pkl", "/artifacts/bg.parquet"],
        ),
        patch("backend_api.point_explainability.artifact_uri_exists", return_value=True),
        patch("builtins.open", mock_open(read_data=b"")),
        patch("pickle.loads", side_effect=e),
    ):
        with pytest.raises(PointSamplingError) as ei:
            compute_shap_driver_variables(model, feature_row, dc, max_background_rows=512)
    assert ei.value.code == "EXPLAINABILITY_PICKLE_IMPORT"
    assert "sdm" in ei.value.detail.lower() or "missing import" in ei.value.detail.lower()
