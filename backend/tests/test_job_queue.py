"""Tests for job queue dispatch."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from backend_api.job_queue import CloudTasksJobQueue, DisabledJobQueue, build_job_queue
from backend_api.settings import Settings

_JOB_ENV_KEYS = (
    "JOB_QUEUE_BACKEND",
    "JOB_WORKER_URL",
    "CLOUD_TASKS_LOCATION",
    "CLOUD_TASKS_QUEUE_ID",
    "CLOUD_TASKS_OIDC_SERVICE_ACCOUNT_EMAIL",
    "CLOUD_TASKS_OIDC_AUDIENCE",
    "INTERNAL_JOB_SECRET",
    "JOB_WORKER_AUTH_MODE",
)


@pytest.fixture(autouse=True)
def _clear_job_queue_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Avoid host env vars overriding explicit Settings(...) kwargs in tests."""
    for key in _JOB_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_disabled_queue_noop():
    q = DisabledJobQueue()
    q.enqueue_run_job("any-id")  # no exception


def test_build_job_queue_disabled_variants():
    for raw in ("disabled", "off", "none"):
        s = Settings(job_queue_backend=raw)
        q = build_job_queue(s)
        assert isinstance(q, DisabledJobQueue)
    s_default = Settings()
    assert isinstance(build_job_queue(s_default), DisabledJobQueue)


def test_build_job_queue_unknown():
    with pytest.raises(ValueError, match="unknown JOB_QUEUE_BACKEND"):
        build_job_queue(Settings(job_queue_backend="typo"))


def test_direct_backend_rejected():
    with pytest.raises(ValueError, match="unknown JOB_QUEUE_BACKEND"):
        build_job_queue(Settings(job_queue_backend="direct"))


@patch("backend_api.job_queue.tasks_v2.CloudTasksClient")
def test_cloud_tasks_queue_creates_task(mock_client_cls):
    mock_instance = MagicMock()
    mock_instance.queue_path.return_value = "projects/p/locations/us-central1/queues/q"
    mock_client_cls.return_value = mock_instance

    s = Settings(
        google_cloud_project="p",
        job_queue_backend="cloud_tasks",
        cloud_tasks_location="us-central1",
        cloud_tasks_queue_id="q",
        job_worker_url="https://run.example/internal/jobs/run",
        cloud_tasks_oidc_service_account_email="tasks-invoker@p.iam.gserviceaccount.com",
        cloud_tasks_oidc_audience="https://run.example",
    )
    q = CloudTasksJobQueue(s)
    q.enqueue_run_job("job-xyz")

    mock_instance.create_task.assert_called_once()
    call_kw = mock_instance.create_task.call_args.kwargs["request"]
    assert call_kw["parent"] == "projects/p/locations/us-central1/queues/q"
    task = call_kw["task"]
    assert task["http_request"]["url"] == "https://run.example/internal/jobs/run"
    assert task["http_request"]["body"] == b'{"job_id": "job-xyz"}'
    oidc = task["http_request"]["oidc_token"]
    assert oidc["service_account_email"] == "tasks-invoker@p.iam.gserviceaccount.com"
    assert oidc["audience"] == "https://run.example"


@patch("backend_api.job_queue.tasks_v2.CloudTasksClient")
def test_build_job_queue_cloud_tasks_alias(mock_client_cls):
    mock_client_cls.return_value.queue_path.return_value = "parent"
    s = Settings(
        google_cloud_project="p",
        job_queue_backend="cloud_tasks",
        job_worker_url="https://w/",
        cloud_tasks_oidc_service_account_email="sa@x",
    )
    q = build_job_queue(s)
    assert isinstance(q, CloudTasksJobQueue)


def test_cloud_tasks_requires_oidc_email():
    with patch("backend_api.job_queue.tasks_v2.CloudTasksClient", return_value=MagicMock()):
        q = CloudTasksJobQueue(
            Settings(
                google_cloud_project="p",
                job_worker_url="https://w/",
                cloud_tasks_oidc_service_account_email=None,
            )
        )
        with pytest.raises(RuntimeError, match="OIDC"):
            q.enqueue_run_job("j")
