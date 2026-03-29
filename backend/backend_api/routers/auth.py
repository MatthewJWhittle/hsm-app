"""Auth-related routes."""

from fastapi import APIRouter, Depends, HTTPException

from backend_api.auth_deps import require_id_token_claims
from backend_api.schemas import AuthMeResponse

router = APIRouter(tags=["auth"])


@router.get("/auth/me", response_model=AuthMeResponse)
async def auth_me(claims: dict = Depends(require_id_token_claims)):
    """Return uid/email from a verified Firebase ID token (Bearer)."""
    uid = claims.get("uid")
    if not uid or not isinstance(uid, str):
        raise HTTPException(status_code=401, detail="Invalid token payload")
    email = claims.get("email")
    email_out = email if isinstance(email, str) else None
    return AuthMeResponse(uid=uid, email=email_out)
