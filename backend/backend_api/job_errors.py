"""Errors for background job execution (worker / Cloud Tasks)."""

from __future__ import annotations

from typing import Any


class JobRetryableError(Exception):
    """
    Transient infrastructure failure while handling a job.

    The worker resets the job to ``queued`` and responds with HTTP 503 so Cloud Tasks
    retries according to queue policy. Use for likely-transient cases (e.g. storage
    flake); do not use for validation or business-rule failures.
    """

    def __init__(self, message: str, *, code: str = "TRANSIENT") -> None:
        super().__init__(message)
        self.code = code


def is_retryable_infra_error(exc: BaseException) -> bool:
    """
    Return True if ``exc`` is a likely-transient infrastructure error worth retrying.

    Does **not** classify validation, client, or business failures — those stay terminal.
    """
    if isinstance(exc, (TimeoutError, ConnectionError, OSError)):
        return True
    try:
        from google.api_core import exceptions as gexc

        if isinstance(
            exc,
            (
                gexc.ServiceUnavailable,
                gexc.DeadlineExceeded,
                gexc.Aborted,
                gexc.InternalServerError,
            ),
        ):
            return True
    except ImportError:
        pass
    try:
        from google.auth import exceptions as gauth_exc

        if isinstance(exc, (gauth_exc.TransportError,)):
            return True
    except ImportError:
        pass
    return False


def wrap_pipeline_infra_errors(exc: BaseException) -> Any:
    """
    If ``exc`` is retryable infra, raise :class:`JobRetryableError`; otherwise re-raise ``exc``.

    Handlers use this after ``except HTTPException: raise`` so validation stays terminal.
    """
    if is_retryable_infra_error(exc):
        raise JobRetryableError(str(exc)[:4000], code="INFRA_TRANSIENT") from exc
    raise exc
