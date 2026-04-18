"""Worker auth: explicit secret vs OIDC modes."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from backend_api.job_worker_auth import verify_internal_job_caller
from backend_api.settings import Settings


def _req(headers: dict[str, str]) -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/internal/jobs/run",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
    }
    return Request(scope)


def test_secret_mode_good():
    s = Settings(
        job_worker_auth_mode="secret",
        internal_job_secret="s3cret",
    )
    verify_internal_job_caller(_req({"X-Internal-Job-Secret": "s3cret"}), s)


def test_secret_mode_bad():
    s = Settings(job_worker_auth_mode="secret", internal_job_secret="s3cret")
    with pytest.raises(HTTPException) as ei:
        verify_internal_job_caller(_req({"X-Internal-Job-Secret": "wrong"}), s)
    assert ei.value.status_code == 401


def test_secret_mode_missing_config():
    s = Settings(job_worker_auth_mode="secret", internal_job_secret=None)
    with pytest.raises(HTTPException) as ei:
        verify_internal_job_caller(_req({}), s)
    assert ei.value.status_code == 503


@patch("google.oauth2.id_token.verify_oauth2_token")
def test_oidc_mode_rejects_secret_header(mock_verify):
    s = Settings(
        job_worker_auth_mode="oidc",
        job_worker_url="https://example.run.app/api/internal/jobs/run",
        cloud_tasks_oidc_audience="https://example.run.app",
    )
    with pytest.raises(HTTPException) as ei:
        verify_internal_job_caller(
            _req({"X-Internal-Job-Secret": "x", "Authorization": "Bearer t"}),
            s,
        )
    assert ei.value.status_code == 401
    mock_verify.assert_not_called()


@patch("google.oauth2.id_token.verify_oauth2_token")
def test_oidc_mode_verifies_bearer(mock_verify):
    mock_verify.return_value = {"sub": "sa@x"}
    s = Settings(
        job_worker_auth_mode="oidc",
        job_worker_url="https://example.run.app/api/internal/jobs/run",
        cloud_tasks_oidc_audience="https://example.run.app",
    )
    verify_internal_job_caller(_req({"Authorization": "Bearer fakeoidc"}), s)
    mock_verify.assert_called_once()
