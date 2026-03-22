"""Unit tests for catalog derivation from JSON index."""

from backend_api.catalog import catalog_to_models, load_index, stable_model_id


def test_stable_model_id_double_hyphen_between_parts():
    assert stable_model_id("Myotis daubentonii", "In flight") == "myotis-daubentonii--in-flight"


def test_index_to_models_from_items():
    raw = {
        "items": [
            {
                "species": "Myotis daubentonii",
                "activity": "In flight",
                "cog_path": "/data/hsm-predictions/cog/Myotis daubentonii_In flight_cog.tif",
            }
        ]
    }
    models = catalog_to_models(raw)
    assert len(models) == 1
    m = models[0]
    assert m.id == "myotis-daubentonii--in-flight"
    assert m.artifact_root == "/data/hsm-predictions/cog"
    assert m.suitability_cog_path == "Myotis daubentonii_In flight_cog.tif"


def test_index_to_models_duplicate_ids_get_suffix():
    raw = {
        "items": [
            {
                "species": "A",
                "activity": "B",
                "cog_path": "/data/cog/one_cog.tif",
            },
            {
                "species": "A",
                "activity": "B",
                "cog_path": "/data/cog/two_cog.tif",
            },
        ]
    }
    models = catalog_to_models(raw)
    assert len(models) == 2
    assert models[0].id == "a--b"
    assert models[1].id == "a--b--2"


def test_catalog_to_models_firestore_documents():
    raw = {
        "collection_id": "models",
        "documents": [
            {
                "id": "a--b",
                "species": "X",
                "activity": "Y",
                "artifact_root": "/data/models/a--b",
                "suitability_cog_path": "suitability_cog.tif",
            }
        ],
    }
    models = catalog_to_models(raw)
    assert len(models) == 1
    assert models[0].id == "a--b"
    assert models[0].suitability_cog_path == "suitability_cog.tif"


def test_catalog_to_models_explicit_models_array_legacy():
    raw = {
        "models": [
            {
                "id": "custom-id",
                "species": "X",
                "activity": "Y",
                "artifact_root": "/data/models/custom-id",
                "suitability_cog_path": "suitability_cog.tif",
            }
        ]
    }
    models = catalog_to_models(raw)
    assert len(models) == 1
    assert models[0].id == "custom-id"


def test_load_index_missing_returns_none(tmp_path):
    assert load_index(str(tmp_path / "nope.json")) is None
