"""OpenAPI / docs toggles."""

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from backend_api.main import create_app
from backend_api.settings import Settings


def test_openapi_disabled_without_touching_global_app():
    mock_coll = MagicMock()
    mock_coll.stream.return_value = iter([])
    mock_fs = MagicMock()
    mock_fs.collection.return_value = mock_coll
    with patch("backend_api.catalog_service.firestore.Client", return_value=mock_fs):
        app = create_app(Settings(openapi_enabled=False))
        with TestClient(app) as c:
            assert c.get("/openapi.json").status_code == 404
            assert c.get("/docs").status_code == 404
            assert c.get("/health").status_code == 200
