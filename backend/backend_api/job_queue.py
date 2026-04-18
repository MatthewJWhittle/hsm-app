"""Background job dispatch: disabled (inline dev) or Cloud Tasks (deployed async)."""

from __future__ import annotations

import json
import logging
from typing import Protocol, runtime_checkable

from google.cloud import tasks_v2

from backend_api.settings import Settings

logger = logging.getLogger(__name__)


def _job_queue_backend_token(settings: Settings) -> str:
    return (settings.job_queue_backend or "disabled").strip().lower()


@runtime_checkable
class JobQueue(Protocol):
    """Enqueue execution of a persisted job (worker loads ``job_id`` from Firestore)."""

    def enqueue_run_job(self, job_id: str) -> None:
        """Schedule or trigger the worker for ``job_id``."""
        ...


class DisabledJobQueue:
    """No-op queue: use with local/test sync pipelines (no Cloud Tasks)."""

    def enqueue_run_job(self, job_id: str) -> None:
        logger.debug("job queue disabled; skip enqueue job_id=%s", job_id)


class CloudTasksJobQueue:
    """Enqueue an HTTP task to the worker URL with OIDC (production pattern)."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = tasks_v2.CloudTasksClient()

    def enqueue_run_job(self, job_id: str) -> None:
        url = (self._settings.job_worker_url or "").strip()
        if not url:
            raise RuntimeError("JOB_WORKER_URL is required when JOB_QUEUE_BACKEND=cloud_tasks")
        sa = (self._settings.cloud_tasks_oidc_service_account_email or "").strip()
        if not sa:
            raise RuntimeError(
                "CLOUD_TASKS_OIDC_SERVICE_ACCOUNT_EMAIL is required when JOB_QUEUE_BACKEND=cloud_tasks"
            )
        audience = (self._settings.cloud_tasks_oidc_audience or url).strip()
        parent = self._client.queue_path(
            self._settings.google_cloud_project,
            self._settings.cloud_tasks_location,
            self._settings.cloud_tasks_queue_id,
        )
        body = json.dumps({"job_id": job_id}).encode("utf-8")
        task = {
            "http_request": {
                "http_method": tasks_v2.HttpMethod.POST,
                "url": url,
                "headers": {"Content-Type": "application/json"},
                "body": body,
                "oidc_token": {
                    "service_account_email": sa,
                    "audience": audience,
                },
            }
        }
        self._client.create_task(request={"parent": parent, "task": task})


def build_job_queue(settings: Settings) -> JobQueue:
    """Factory for :class:`JobQueue` from settings."""
    raw = _job_queue_backend_token(settings)
    if raw in ("", "disabled", "off", "none"):
        return DisabledJobQueue()
    if raw in ("cloud_tasks", "cloudtasks", "tasks"):
        return CloudTasksJobQueue(settings)
    raise ValueError(f"unknown JOB_QUEUE_BACKEND: {settings.job_queue_backend!r}")


def job_queue_enabled(settings: Settings) -> bool:
    """True when Cloud Tasks dispatch is configured (not the default disabled backend)."""
    raw = _job_queue_backend_token(settings)
    return raw not in ("", "disabled", "off", "none")
