"""ASGI request timeout: short default, long worker route."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from backend_api.main import create_app
from backend_api.settings import Settings


def _mock_firestore():
    mock_coll = MagicMock()
    mock_coll.stream.return_value = iter([])
    mock_fs = MagicMock()
    mock_fs.collection.return_value = mock_coll
    return mock_fs


@patch("backend_api.catalog_service.firestore.Client")
def test_non_worker_route_hits_short_timeout_returns_504(mock_fs_cls):
    mock_fs_cls.return_value = _mock_firestore()
    settings = Settings(http_default_request_timeout_seconds=0.05)
    app = create_app(settings)

    @app.get("/_test_slow")
    async def _slow() -> dict[str, bool]:
        await asyncio.sleep(0.3)
        return {"ok": True}

    with TestClient(app) as client:
        r = client.get("/_test_slow")
    assert r.status_code == 504
    assert r.json().get("detail") == "gateway timeout"


@patch("backend_api.catalog_service.firestore.Client")
def test_health_ok_under_default_middleware(mock_fs_cls):
    mock_fs_cls.return_value = _mock_firestore()
    app = create_app(Settings())
    with TestClient(app) as client:
        r = client.get("/health")
    assert r.status_code == 200
