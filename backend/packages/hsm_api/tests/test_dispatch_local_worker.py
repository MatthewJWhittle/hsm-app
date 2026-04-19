"""Local BackgroundTasks worker HTTP dispatch."""

from unittest.mock import patch

import httpx

from backend_api.jobs.dispatch import WORKER_INTERNAL_SECRET_HEADER, _post_local_worker
from backend_api.settings import Settings


def test_post_local_worker_marks_job_failed_when_http_raises():
    settings = Settings(
        google_cloud_project="test-proj",
        worker_http_deadline_seconds=120,
        worker_internal_secret=None,
    )
    with (
        patch("backend_api.jobs.dispatch.httpx.post") as mock_post,
        patch("backend_api.jobs.dispatch.firestore.Client") as mock_fs,
        patch("backend_api.jobs.dispatch.update_job_status") as mock_update,
    ):
        mock_post.side_effect = httpx.ConnectError("connection refused")
        mock_fs.return_value = object()
        _post_local_worker(
            settings,
            "http://worker/run",
            {"job_id": "jid-1", "kind": "explainability_background_sample"},
        )
    mock_update.assert_called_once()
    assert mock_update.call_args[0][1] == "jid-1"
    assert mock_update.call_args[1]["status"] == "failed"
    assert mock_update.call_args[1]["error_code"] == "LOCAL_WORKER_DISPATCH_FAILED"


def test_post_local_worker_sends_secret_and_read_timeout():
    settings = Settings(
        google_cloud_project="p",
        worker_http_deadline_seconds=90,
        worker_internal_secret="s3cr3t",
    )
    with patch("backend_api.jobs.dispatch.httpx.post") as mock_post:
        mock_post.return_value = httpx.Response(200)
        _post_local_worker(settings, "http://w/x", {"job_id": "j"})
    mock_post.assert_called_once()
    _args, kw = mock_post.call_args
    assert kw["headers"][WORKER_INTERNAL_SECRET_HEADER] == "s3cr3t"
    assert kw["timeout"].read == 90.0
