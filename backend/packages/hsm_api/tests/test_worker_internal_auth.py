"""Worker internal endpoint auth (dev / compose)."""

from unittest.mock import patch

from starlette.testclient import TestClient

from hsm_core.settings import Settings
from hsm_worker.main import create_app


def test_worker_requires_secret_when_configured():
    settings = Settings(
        google_cloud_project="p",
        worker_internal_secret="test-secret-32-bytes-long!!!!",
    )
    app = create_app(settings)
    with TestClient(app) as client:
        r = client.post("/internal/worker/run", json={"job_id": "j1"})
    assert r.status_code == 403


def test_worker_accepts_matching_secret():
    secret = "test-secret-32-bytes-long!!!!"
    settings = Settings(
        google_cloud_project="p",
        worker_internal_secret=secret,
    )
    with patch("hsm_worker.main._dispatch_after_claim") as mock_dispatch:
        app = create_app(settings)
        with TestClient(app) as client:
            r = client.post(
                "/internal/worker/run",
                json={"job_id": "j1", "kind": "explainability_background_sample"},
                headers={"X-HSM-Worker-Secret": secret},
            )
    assert r.status_code == 200
    assert r.json() == {"ok": True}
    mock_dispatch.assert_called_once()
