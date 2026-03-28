"""Shared pytest configuration."""

import pytest


@pytest.fixture(autouse=True)
def default_catalog_backend_file(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests assume the JSON file backend unless they override CATALOG_BACKEND."""
    monkeypatch.setenv("CATALOG_BACKEND", "file")
