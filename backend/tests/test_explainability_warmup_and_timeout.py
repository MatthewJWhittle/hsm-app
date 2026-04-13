"""Explainability warmup route and point inspection timeout."""

import importlib
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from tests.helpers import mock_firestore_client_for_documents


async def _raise_timeout(*_a, **_kw):
    raise TimeoutError()


@pytest.mark.filterwarnings("ignore:coroutine .* was never awaited:RuntimeWarning")
def test_point_inspect_timeout_returns_504():
    """GET /models/{id}/point returns 504 when asyncio.wait_for fires TimeoutError."""
    documents = [
        {
            "id": "m1",
            "species": "Bat",
            "activity": "Roost",
            "artifact_root": "/tmp",
            "suitability_cog_path": "s.tif",
        }
    ]
    mock_client = mock_firestore_client_for_documents(documents)
    with patch("backend_api.catalog_service.firestore.Client", return_value=mock_client):
        import backend_api.main as main

        importlib.reload(main)
        with (
            patch("backend_api.routers.models.asyncio.wait_for", _raise_timeout),
            TestClient(main.app) as client,
        ):
            r = client.get("/models/m1/point", params={"lng": -2.0, "lat": 53.0})
    assert r.status_code == 504
    detail = r.json().get("detail")
    assert isinstance(detail, dict)
    assert detail.get("code") == "POINT_INSPECT_TIMEOUT"


def test_explainability_warmup_returns_204():
    """Warmup is a no-op for models without explainability; still 204."""
    documents = [
        {
            "id": "m1",
            "species": "Bat",
            "activity": "Roost",
            "artifact_root": "/tmp",
            "suitability_cog_path": "s.tif",
        }
    ]
    mock_client = mock_firestore_client_for_documents(documents)
    with patch("backend_api.catalog_service.firestore.Client", return_value=mock_client):
        import backend_api.main as main

        importlib.reload(main)
        with TestClient(main.app) as client:
            r = client.post("/models/m1/explainability-warmup")
    assert r.status_code == 204
