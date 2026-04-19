"""Legacy Firestore model document migration (driver_config → metadata.analysis)."""

from backend_api.schemas import Model


def test_legacy_driver_config_merged_when_metadata_exists_without_analysis_path():
    raw = {
        "id": "m1",
        "species": "S",
        "activity": "A",
        "artifact_root": "/models/m1",
        "suitability_cog_path": "s.tif",
        "metadata": {"card": {"title": "T"}},
        "driver_config": {
            "explainability_model_path": "serialized_model.pkl",
            "explainability_positive_class": 1,
        },
    }
    m = Model.model_validate(raw)
    assert m.metadata is not None
    assert m.metadata.analysis is not None
    assert m.metadata.analysis.serialized_model_path == "serialized_model.pkl"
    assert m.metadata.analysis.positive_class_index == 1
    assert m.metadata.card is not None
    assert m.metadata.card.title == "T"


def test_legacy_driver_config_does_not_overwrite_existing_analysis():
    raw = {
        "id": "m1",
        "species": "S",
        "activity": "A",
        "artifact_root": "/models/m1",
        "suitability_cog_path": "s.tif",
        "metadata": {
            "analysis": {"serialized_model_path": "current.pkl", "feature_band_names": ["a"]}
        },
        "driver_config": {"explainability_model_path": "stale.pkl"},
    }
    m = Model.model_validate(raw)
    assert m.metadata and m.metadata.analysis
    assert m.metadata.analysis.serialized_model_path == "current.pkl"
    assert m.metadata.analysis.feature_band_names == ["a"]
