"""ASGI request timeouts: short default for user-facing routes, long for Cloud Tasks worker only.

Cloud Run exposes a single per-service timeout; this middleware adds path-aware ceilings in the app
so normal traffic cannot hold connections for as long as the worker route.
"""

from __future__ import annotations

import asyncio

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from backend_api.settings import Settings

# Must match internal_jobs.router: prefix /internal + POST /jobs/run under /api.
_WORKER_PATH = "/api/internal/jobs/run"


class RequestTimeoutMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, settings: Settings):
        super().__init__(app)
        self._settings = settings

    async def dispatch(self, request: Request, call_next):
        path = request.scope.get("path") or ""
        if path == _WORKER_PATH:
            limit = self._settings.internal_job_http_timeout_seconds
        else:
            limit = self._settings.http_default_request_timeout_seconds
        try:
            return await asyncio.wait_for(call_next(request), timeout=limit)
        except asyncio.TimeoutError:
            return JSONResponse(
                status_code=504,
                content={"detail": "gateway timeout"},
            )
