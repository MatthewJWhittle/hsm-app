"""Pytest hooks: env so Firebase Admin can init without GCP credentials."""

import os

import pytest

# Tests run without GCP ADC; Auth emulator host lets Admin SDK initialize for verify_id_token mocks.
os.environ.setdefault("FIREBASE_AUTH_EMULATOR_HOST", "127.0.0.1:9099")


@pytest.fixture(autouse=True)
def _clear_explainability_runtime_cache() -> None:
    """SHAP explainer cache is process-global; reset between tests for isolation."""
    from backend_api.explainability_runtime_cache import clear_explainability_cache_for_tests

    clear_explainability_cache_for_tests()
    yield
    clear_explainability_cache_for_tests()
