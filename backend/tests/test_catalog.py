"""Unit tests for catalog derivation from JSON index."""

import pytest

from backend_api.catalog import catalog_to_models, try_load_catalog_json


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


def test_catalog_to_models_missing_documents_returns_empty():
    assert catalog_to_models({"collection_id": "models"}) == []


def test_catalog_to_models_empty_documents():
    assert catalog_to_models({"documents": []}) == []


def test_catalog_to_models_documents_not_list_raises():
    with pytest.raises(ValueError, match="documents array"):
        catalog_to_models({"documents": "not-a-list"})


def test_try_load_catalog_json_missing_returns_none_none(tmp_path):
    assert try_load_catalog_json(str(tmp_path / "nope.json")) == (None, None)


def test_try_load_catalog_json_invalid_json_returns_error(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{ not json", encoding="utf-8")
    data, err = try_load_catalog_json(str(bad))
    assert data is None
    assert err == "Catalog file is not valid JSON."


def test_try_load_catalog_json_non_object_returns_error(tmp_path):
    f = tmp_path / "arr.json"
    f.write_text("[1,2]", encoding="utf-8")
    data, err = try_load_catalog_json(str(f))
    assert data is None
    assert err == "Catalog file must be a JSON object."
