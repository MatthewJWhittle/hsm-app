"""Enqueue worker HTTP tasks via Cloud Tasks or local BackgroundTasks + httpx."""

from __future__ import annotations

import json
import logging
from urllib.parse import urlparse

import httpx
from fastapi import BackgroundTasks
from google.cloud import tasks_v2
from google.protobuf import duration_pb2

from hsm_core.settings import Settings

logger = logging.getLogger(__name__)


def _oidc_audience(task_url: str) -> str:
    p = urlparse(task_url)
    if not p.scheme or not p.netloc:
        raise ValueError(f"Invalid WORKER_TASK_URL for audience: {task_url!r}")
    return f"{p.scheme}://{p.netloc}"


def _enqueue_cloud_task(settings: Settings, body: dict) -> None:
    if (
        not settings.cloud_tasks_queue
        or not settings.cloud_tasks_location
        or not settings.cloud_tasks_oidc_service_account
        or not settings.worker_task_url
    ):
        raise RuntimeError("Cloud Tasks settings incomplete")

    client = tasks_v2.CloudTasksClient()
    parent = client.queue_path(
        settings.google_cloud_project,
        settings.cloud_tasks_location,
        settings.cloud_tasks_queue,
    )
    payload = json.dumps(body).encode()
    task: dict = {
        "http_request": {
            "http_method": tasks_v2.HttpMethod.POST,
            "url": settings.worker_task_url,
            "headers": {"Content-Type": "application/json"},
            "body": payload,
            "oidc_token": {
                "service_account_email": settings.cloud_tasks_oidc_service_account,
                "audience": _oidc_audience(settings.worker_task_url),
            },
        },
        "dispatch_deadline": duration_pb2.Duration(seconds=900),
    }
    client.create_task(tasks_v2.CreateTaskRequest(parent=parent, task=task))
    logger.info("cloud_tasks_enqueued job_id=%s kind=%s", body.get("job_id"), body.get("kind"))


def _post_local_worker(url: str, body: dict) -> None:
    try:
        httpx.post(url, json=body, timeout=httpx.Timeout(600.0, connect=30.0))
    except Exception:
        logger.exception("local_worker_post_failed url=%s job_id=%s", url, body.get("job_id"))


def schedule_background_http_task(
    *,
    settings: Settings,
    background_tasks: BackgroundTasks | None,
    body: dict,
) -> None:
    """Fire-and-forget: Cloud Tasks in cloud, or BackgroundTasks + HTTP in local."""
    if settings.use_cloud_tasks:
        _enqueue_cloud_task(settings, body)
        return
    if not settings.worker_base_url:
        raise RuntimeError("WORKER_BASE_URL required when USE_CLOUD_TASKS=false")
    if background_tasks is None:
        raise RuntimeError("BackgroundTasks required for local worker dispatch")
    url = f"{settings.worker_base_url.rstrip('/')}/internal/worker/run"
    background_tasks.add_task(_post_local_worker, url, body)
    logger.info("local_worker_scheduled job_id=%s kind=%s", body.get("job_id"), body.get("kind"))
