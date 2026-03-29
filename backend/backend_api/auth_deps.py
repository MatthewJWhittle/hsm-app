"""FastAPI dependencies for Firebase ID token verification."""

from __future__ import annotations

from firebase_admin import auth
from fastapi import Depends, HTTPException, Request
from starlette.concurrency import run_in_threadpool


def _bearer_token(request: Request) -> str:
    header = request.headers.get("Authorization")
    if not header or not header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = header.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing bearer token")
    return token


async def require_id_token_claims(request: Request) -> dict:
    """Verify ``Authorization: Bearer <ID token>`` and return decoded claims."""
    token = _bearer_token(request)

    def _verify() -> dict:
        return auth.verify_id_token(token)

    try:
        return await run_in_threadpool(_verify)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from None


async def require_admin_claims(
    claims: dict = Depends(require_id_token_claims),
) -> dict:
    """Verified ID token with Firebase custom claim ``admin: true`` (else 403)."""
    if claims.get("admin") is not True:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return claims
