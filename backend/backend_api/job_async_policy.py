"""
When admin routes use **async** (202 + Cloud Tasks) vs **inline** pipelines.

Only two queue modes exist: ``JOB_QUEUE_BACKEND=disabled`` (always inline) and
``cloud_tasks``. Local dev uses **disabled** and runs the same pipelines in-process — no fake HTTP self-call.

**Async-eligible (long-running upload-session flows)** — return 202 when ``job_queue_enabled(settings)`` and the request uses an upload session without multipart file where applicable:

- Replace project environmental COG (session only)
- Create project with environmental COG (session only)
- Create / replace model suitability COG (session only; not when serialized pickle multipart is present)
- Regenerate explainability background Parquet (always long-running; async when queue enabled)

**Stay synchronous (not async-eligible)** — small metadata PATCHes, band label patches, multipart uploads where we intentionally process in the request, or any route not listed above.

Future contributors: add async only for operations that can exceed HTTP timeout; keep eligibility obvious in :func:`should_async_*` helpers below.
"""

from __future__ import annotations

from backend_api.job_queue import job_queue_enabled
from backend_api.settings import Settings


def should_async_replace_environmental_cogs(
    settings: Settings,
    *,
    has_multipart_file: bool,
    upload_session_id: str | None,
) -> bool:
    """Upload-session replace only (no multipart file in the same request)."""
    return (
        job_queue_enabled(settings)
        and bool(upload_session_id)
        and not has_multipart_file
    )


def should_async_project_create_with_env(
    settings: Settings,
    *,
    has_multipart_file: bool,
    upload_session_id: str | None,
) -> bool:
    """Session-based env COG on create (not multipart)."""
    return (
        job_queue_enabled(settings)
        and bool(upload_session_id)
        and not has_multipart_file
    )


def should_async_explainability_background(settings: Settings) -> bool:
    """Long-running raster sampling; async whenever the queue is enabled."""
    return job_queue_enabled(settings)


def should_async_model_create_with_upload(
    settings: Settings,
    *,
    upload_session_id: str | None,
    has_multipart_file: bool,
    has_serialized_pickle: bool,
) -> bool:
    """Session suitability upload without multipart file or explainability pickle in the same request."""
    return (
        job_queue_enabled(settings)
        and bool(upload_session_id)
        and not has_multipart_file
        and not has_serialized_pickle
    )


def should_async_model_replace_suitability(
    settings: Settings,
    *,
    upload_session_id: str | None,
    has_multipart_file: bool,
    has_serialized_pickle: bool,
) -> bool:
    """Same eligibility rule as create."""
    return should_async_model_create_with_upload(
        settings,
        upload_session_id=upload_session_id,
        has_multipart_file=has_multipart_file,
        has_serialized_pickle=has_serialized_pickle,
    )
