"""Async eligibility helpers (upload-session + queue enabled)."""

from __future__ import annotations

import pytest

from backend_api.job_async_policy import (
    should_async_explainability_background,
    should_async_model_create_with_upload,
    should_async_project_create_with_env,
    should_async_replace_environmental_cogs,
)
from backend_api.settings import Settings


@pytest.fixture(autouse=True)
def _clear_job_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("JOB_QUEUE_BACKEND", raising=False)


def test_queue_disabled_never_async():
    s = Settings(job_queue_backend="disabled")
    assert not should_async_replace_environmental_cogs(
        s, has_multipart_file=False, upload_session_id="u1"
    )
    assert not should_async_project_create_with_env(
        s, has_multipart_file=False, upload_session_id="u1"
    )
    assert not should_async_explainability_background(s)
    assert not should_async_model_create_with_upload(
        s,
        upload_session_id="u1",
        has_multipart_file=False,
        has_serialized_pickle=False,
    )


def test_cloud_tasks_session_replace():
    s = Settings(job_queue_backend="cloud_tasks")
    assert should_async_replace_environmental_cogs(
        s, has_multipart_file=False, upload_session_id="u1"
    )
    assert not should_async_replace_environmental_cogs(
        s, has_multipart_file=True, upload_session_id="u1"
    )


def test_model_async_requires_no_multipart_file():
    s = Settings(job_queue_backend="cloud_tasks")
    assert should_async_model_create_with_upload(
        s,
        upload_session_id="u1",
        has_multipart_file=False,
        has_serialized_pickle=False,
    )
    assert not should_async_model_create_with_upload(
        s,
        upload_session_id="u1",
        has_multipart_file=True,
        has_serialized_pickle=False,
    )
