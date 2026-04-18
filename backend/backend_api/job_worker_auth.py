"""Authenticate calls to internal job worker endpoints (dev secret or Cloud Tasks OIDC)."""

from __future__ import annotations

import hmac

from fastapi import HTTPException, Request

from backend_api.settings import Settings


def verify_internal_job_caller(request: Request, settings: Settings) -> None:
    """
    Allow either:

    - ``X-Internal-Job-Secret`` matching :attr:`Settings.internal_job_secret` (development / direct queue), or
    - ``Authorization: Bearer`` Google OIDC token with audience
      :attr:`Settings.cloud_tasks_oidc_audience` (or ``JOB_WORKER_URL`` fallback).

    If ``internal_job_secret`` is non-empty, only the header is checked (OIDC is skipped). Production
    Cloud Tasks setups should leave the secret unset and rely on OIDC.
    """
    secret = (settings.internal_job_secret or "").strip()
    if secret:
        got = request.headers.get("X-Internal-Job-Secret") or ""
        if not hmac.compare_digest(got.encode("utf-8"), secret.encode("utf-8")):
            raise HTTPException(status_code=401, detail="invalid internal job secret")
        return

    auth = request.headers.get("Authorization") or ""
    if not auth.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="missing bearer token (set INTERNAL_JOB_SECRET for local direct dispatch)",
        )
    token = auth.removeprefix("Bearer ").strip()
    audience = (settings.cloud_tasks_oidc_audience or settings.job_worker_url or "").strip()
    if not audience:
        raise HTTPException(
            status_code=503,
            detail="worker OIDC audience not configured (CLOUD_TASKS_OIDC_AUDIENCE or JOB_WORKER_URL)",
        )
    try:
        from google.auth.transport import requests as google_requests
        from google.oauth2 import id_token as google_id_token

        google_id_token.verify_oauth2_token(
            token, google_requests.Request(), audience=audience
        )
    except Exception:
        raise HTTPException(status_code=401, detail="invalid OIDC token") from None
