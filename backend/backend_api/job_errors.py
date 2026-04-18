"""Errors for background job execution (worker / Cloud Tasks)."""


class JobRetryableError(Exception):
    """
    Transient infrastructure failure while handling a job.

    The worker resets the job to ``queued`` and responds with HTTP 503 so Cloud Tasks
    retries according to queue policy. Use for likely-transient cases (e.g. storage
    flake); do not use for validation or business-rule failures.
    """
