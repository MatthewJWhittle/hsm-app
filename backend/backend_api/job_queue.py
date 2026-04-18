"""Pluggable dispatch for background jobs (Cloud Tasks vs direct HTTP vs disabled)."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Protocol, runtime_checkable

from google.cloud import tasks_v2

from backend_api.settings import Settings

logger = logging.getLogger(__name__)


@runtime_checkable
class JobQueue(Protocol):
    """Enqueue execution of a persisted job (worker loads ``job_id`` from Firestore)."""

    def enqueue_run_job(self, job_id: str) -> None:
        """Schedule or trigger the worker for ``job_id``."""
        ...


class DisabledJobQueue:
    """No-op queue (default until infra wires Cloud Tasks or direct worker)."""

    def enqueue_run_job(self, job_id: str) -> None:
        logger.debug("job queue disabled; skip enqueue job_id=%s", job_id)


class DirectJobQueue:
    """
    POST ``{\"job_id\": ...}`` to :attr:`Settings.job_worker_url`.

    **Semantics:** This call waits for the worker HTTP response. The worker runs ``execute_job`` to completion
    before returning, so the **API handler that enqueues also blocks** until the job finishes (unlike
    :class:`CloudTasksJobQueue`, which returns after the task is queued). Use for local/dev; production async
    enqueue should use ``cloud_tasks``.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def enqueue_run_job(self, job_id: str) -> None:
        url = (self._settings.job_worker_url or "").strip()
        if not url:
            raise RuntimeError("JOB_WORKER_URL is required when JOB_QUEUE_BACKEND=direct")
        payload = json.dumps({"job_id": job_id}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        secret = self._settings.internal_job_secret
        if secret:
            req.add_header("X-Internal-Job-Secret", secret)
        try:
            with urllib.request.urlopen(
                req, timeout=self._settings.job_direct_http_timeout_seconds
            ) as resp:
                if resp.status < 200 or resp.status >= 300:
                    body = resp.read(512).decode("utf-8", errors="replace")
                    raise RuntimeError(
                        f"direct job worker returned HTTP {resp.status}: {body[:200]}"
                    )
        except urllib.error.HTTPError as e:
            body = e.read(512).decode("utf-8", errors="replace") if e.fp else ""
            raise RuntimeError(
                f"direct job worker HTTP {e.code}: {body[:200]}"
            ) from e
        except urllib.error.URLError as e:
            raise RuntimeError(f"direct job worker request failed: {e}") from e


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
    raw = (settings.job_queue_backend or "disabled").strip().lower()
    if raw in ("", "disabled", "off", "none"):
        return DisabledJobQueue()
    if raw == "direct":
        return DirectJobQueue(settings)
    if raw in ("cloud_tasks", "cloudtasks", "tasks"):
        return CloudTasksJobQueue(settings)
    raise ValueError(f"unknown JOB_QUEUE_BACKEND: {settings.job_queue_backend!r}")


def job_queue_enabled(settings: Settings) -> bool:
    """True when background job dispatch is configured (not the default disabled backend)."""
    raw = (settings.job_queue_backend or "disabled").strip().lower()
    return raw not in ("", "disabled", "off", "none")
