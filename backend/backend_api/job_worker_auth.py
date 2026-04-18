"""Authenticate calls to internal job worker endpoints (explicit secret vs OIDC modes)."""

from __future__ import annotations

import hmac

from fastapi import HTTPException, Request

from backend_api.settings import Settings


def verify_internal_job_caller(request: Request, settings: Settings) -> None:
    """
    Auth is explicit (JOB_WORKER_AUTH_MODE), not inferred from whether a secret is set:

    - **secret** — require ``X-Internal-Job-Secret`` matching :attr:`Settings.internal_job_secret`.
    - **oidc** — require ``Authorization: Bearer`` Google OIDC token; reject ``X-Internal-Job-Secret``.
    """
    mode = (settings.job_worker_auth_mode or "oidc").strip().lower()
    if mode not in ("secret", "oidc"):
        raise HTTPException(status_code=503, detail="invalid JOB_WORKER_AUTH_MODE")

    if mode == "secret":
        secret = (settings.internal_job_secret or "").strip()
        if not secret:
            raise HTTPException(
                status_code=503,
                detail="JOB_WORKER_AUTH_MODE=secret requires INTERNAL_JOB_SECRET",
            )
        got = request.headers.get("X-Internal-Job-Secret") or ""
        if not hmac.compare_digest(got.encode("utf-8"), secret.encode("utf-8")):
            raise HTTPException(status_code=401, detail="invalid internal job secret")
        return

    # OIDC mode: never accept secret-only auth (production footgun if secret leaked).
    if (request.headers.get("X-Internal-Job-Secret") or "").strip():
        raise HTTPException(
            status_code=401,
            detail="worker auth is OIDC-only; remove X-Internal-Job-Secret",
        )
    auth = request.headers.get("Authorization") or ""
    if not auth.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="missing bearer OIDC token (set JOB_WORKER_AUTH_MODE=secret for local secret auth)",
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
