"""Async HTTP client smoke test (httpx ASGI transport)."""

from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from backend_api.main import create_app
from backend_api.settings import Settings


@pytest.mark.asyncio
async def test_health_async():
    mock_coll = MagicMock()
    mock_coll.stream.return_value = iter([])
    mock_fs = MagicMock()
    mock_fs.collection.return_value = mock_coll
    with patch("backend_api.catalog_service.firestore.Client", return_value=mock_fs):
        app = create_app(Settings())
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"
