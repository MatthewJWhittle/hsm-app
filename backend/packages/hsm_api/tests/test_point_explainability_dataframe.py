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

    drivers = compute_shap_driver_variables(
        model, feature_row, dc, max_background_rows=512
    )
    assert len(drivers) >= 1
    names = {d.name for d in drivers}
    assert names.issubset(set(cols))
