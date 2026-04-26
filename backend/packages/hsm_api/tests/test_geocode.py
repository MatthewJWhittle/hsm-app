"""Tests for the MapTiler-backed place-search proxy."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
from fastapi.testclient import TestClient

from backend_api.main import create_app
from backend_api.routers.geocode import parse_maptiler_response
from backend_api.settings import Settings


def _client(settings: Settings):
    mock_coll = MagicMock()
    mock_coll.stream.return_value = iter([])
    mock_fs = MagicMock()
    mock_fs.collection.return_value = mock_coll
    with patch("backend_api.catalog_service.firestore.Client", return_value=mock_fs):
        app = create_app(settings)
        with TestClient(app) as c:
            yield c


class _FakeAsyncClient:
    response: httpx.Response | Exception
    requested_url: str | None = None
    requested_params: dict | None = None

    def __init__(self, *, timeout: float):
        self.timeout = timeout

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def get(self, url: str, params: dict):
        type(self).requested_url = url
        type(self).requested_params = params
        if isinstance(type(self).response, Exception):
            raise type(self).response
        return type(self).response


def test_parse_maptiler_response_maps_features():
    parsed = parse_maptiler_response(
        {
            "type": "FeatureCollection",
            "attribution": "MapTiler OpenStreetMap contributors",
            "features": [
                {
                    "id": "municipality.123",
                    "type": "Feature",
                    "place_name": "Guiseley, Leeds, England, United Kingdom",
                    "center": [-1.712, 53.875],
                    "bbox": [-1.75, 53.84, -1.66, 53.91],
                }
            ],
        }
    )

    assert len(parsed.results) == 1
    result = parsed.results[0]
    assert result.id == "municipality.123"
    assert result.label == "Guiseley, Leeds, England, United Kingdom"
    assert result.center.lng == -1.712
    assert result.center.lat == 53.875
    assert result.bbox == (-1.75, 53.84, -1.66, 53.91)
    assert result.source == "maptiler"


def test_parse_maptiler_response_returns_empty_for_empty_collection():
    assert parse_maptiler_response({"features": []}).results == []


def test_geocode_search_requires_api_key():
    for c in _client(Settings(maptiler_api_key=None)):
        r = c.get("/api/geocode/search", params={"q": "Guiseley"})

    assert r.status_code == 503
    assert r.json()["detail"] == "Place search is not configured."


def test_geocode_search_rejects_blank_query():
    for c in _client(Settings(maptiler_api_key="key")):
        r = c.get("/api/geocode/search", params={"q": "  "})

    assert r.status_code == 422


def test_geocode_search_calls_maptiler(monkeypatch):
    _FakeAsyncClient.response = httpx.Response(
        200,
        json={
            "features": [
                {
                    "id": "place.1",
                    "place_name": "Guiseley, Leeds",
                    "center": [-1.712, 53.875],
                }
            ]
        },
    )
    monkeypatch.setattr("backend_api.routers.geocode.httpx.AsyncClient", _FakeAsyncClient)

    for c in _client(
        Settings(
            maptiler_api_key="secret",
            geocode_country="gb",
            geocode_language="en",
        )
    ):
        r = c.get("/api/geocode/search", params={"q": "Guiseley", "limit": "3"})

    assert r.status_code == 200
    assert r.json()["results"][0]["label"] == "Guiseley, Leeds"
    assert _FakeAsyncClient.requested_url == "https://api.maptiler.com/geocoding/Guiseley.json"
    assert _FakeAsyncClient.requested_params == {
        "key": "secret",
        "limit": 3,
        "autocomplete": "true",
        "country": "gb",
        "language": "en",
    }


def test_geocode_search_maps_timeout_to_503(monkeypatch):
    _FakeAsyncClient.response = httpx.TimeoutException("timeout")
    monkeypatch.setattr("backend_api.routers.geocode.httpx.AsyncClient", _FakeAsyncClient)

    for c in _client(Settings(maptiler_api_key="secret")):
        r = c.get("/api/geocode/search", params={"q": "Guiseley"})

    assert r.status_code == 503
    assert r.json()["detail"] == "Place search timed out."
