"""Regression: SHAP passes ndarrays; ColumnTransformer pipelines need DataFrame column names."""

from pathlib import Path

import numpy as np
import pandas as pd
import pickle
import pytest
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from backend_api.point_explainability import compute_shap_driver_variables
from backend_api.schemas import Model, ModelAnalysis, ModelMetadata
from hsm_core.artifact_read_runtime import ArtifactReadRuntime
from hsm_core.settings import Settings


def test_shap_column_transformer_pipeline_receives_dataframe(tmp_path: Path) -> None:
    """Permutation SHAP calls predict_fn with numpy arrays; server must wrap with feature columns."""
    cols = ["band_x", "band_y"]
    rng = np.random.default_rng(42)
    X_train = pd.DataFrame(rng.normal(size=(40, 2)), columns=cols)
    y_train = rng.integers(0, 2, size=40)

    pre = ColumnTransformer([("s", StandardScaler(), cols)], remainder="drop")
    pipe = Pipeline([("pre", pre), ("clf", LogisticRegression(max_iter=500))])
    pipe.fit(X_train, y_train)

    model_path = tmp_path / "serialized_model.pkl"
    with open(model_path, "wb") as f:
        pickle.dump(pipe, f)

    bg = pd.DataFrame(rng.normal(size=(16, 2)), columns=cols)
    bg_path = tmp_path / "explainability_background.parquet"
    bg.to_parquet(bg_path)

    model = Model(
        id="m1",
        project_id="p1",
        species="Bat",
        activity="Roost",
        artifact_root=str(tmp_path),
        suitability_cog_path="s.tif",
        metadata=ModelMetadata(
            analysis=ModelAnalysis(serialized_model_path="serialized_model.pkl"),
        ),
    )
    dc = {
        "explainability_model_path": "serialized_model.pkl",
        "explainability_background_path": "explainability_background.parquet",
        "explainability_background_artifact_root": str(tmp_path),
        "feature_names": cols,
        "explainability_positive_class": 1,
        "band_labels": ["X", "Y"],
    }
    feature_row = pd.DataFrame([[0.12, -0.34]], columns=cols)

    artifact_read = ArtifactReadRuntime(Settings())
    drivers = compute_shap_driver_variables(
        model, feature_row, dc, max_background_rows=512, artifact_read=artifact_read
    )
    assert len(drivers) >= 1
    names = {d.name for d in drivers}
    assert names.issubset(set(cols))


def test_shap_returns_all_feature_rows_without_top_k_cap(tmp_path: Path) -> None:
    """API should return influence for every configured feature, not just top-k."""
    cols = [f"band_{i}" for i in range(10)]
    rng = np.random.default_rng(7)
    X_train = pd.DataFrame(rng.normal(size=(120, len(cols))), columns=cols)
    y_train = rng.integers(0, 2, size=120)
    clf = LogisticRegression(max_iter=700).fit(X_train, y_train)

    model_path = tmp_path / "serialized_model.pkl"
    with open(model_path, "wb") as f:
        pickle.dump(clf, f)

    bg = pd.DataFrame(rng.normal(size=(64, len(cols))), columns=cols)
    bg_path = tmp_path / "explainability_background.parquet"
    bg.to_parquet(bg_path)

    model = Model(
        id="m-all-features",
        project_id="p1",
        species="Bat",
        activity="Roost",
        artifact_root=str(tmp_path),
        suitability_cog_path="s.tif",
        metadata=ModelMetadata(
            analysis=ModelAnalysis(serialized_model_path="serialized_model.pkl"),
        ),
    )
    dc = {
        "explainability_model_path": "serialized_model.pkl",
        "explainability_background_path": "explainability_background.parquet",
        "explainability_background_artifact_root": str(tmp_path),
        "feature_names": cols,
        "explainability_positive_class": 1,
        "band_labels": [f"Band {i}" for i in range(len(cols))],
    }
    feature_row = pd.DataFrame([rng.normal(size=len(cols))], columns=cols)

    artifact_read = ArtifactReadRuntime(Settings())
    drivers = compute_shap_driver_variables(
        model, feature_row, dc, max_background_rows=512, artifact_read=artifact_read
    )

    assert len(drivers) == len(cols)
    assert {d.name for d in drivers} == set(cols)
