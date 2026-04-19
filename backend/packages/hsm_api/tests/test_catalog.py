"""Unit tests for catalog JSON → Model list (offline / tests)."""

import pytest

from backend_api.catalog import catalog_to_models


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
