"""Pluggable background job handlers (registry dispatch from :mod:`backend_api.job_runner`)."""

from __future__ import annotations

from backend_api.job_handlers.context import JobRunContext
from backend_api.job_handlers.registry import get_job_handler, run_job_handler

__all__ = ["JobRunContext", "get_job_handler", "run_job_handler"]
