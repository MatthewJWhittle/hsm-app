"""Auth-related routes."""

from fastapi import APIRouter, Depends, HTTPException, Request
from firebase_admin import auth
from firebase_admin import exceptions as firebase_exceptions
from starlette.concurrency import run_in_threadpool

from backend_api.auth_deps import require_id_token_claims
from backend_api.firebase_identity_toolkit import IdentityToolkitError, sign_in_with_password
from backend_api.schemas import AuthMeResponse, AuthTokenRequest, AuthTokenResponse
from backend_api.settings import Settings

router = APIRouter(tags=["auth"])


def _resolve_firebase_web_api_key(settings: Settings) -> str:
    if settings.firebase_web_api_key:
        return settings.firebase_web_api_key.strip()
    if settings.firebase_auth_emulator_host:
        return "demo"
    raise HTTPException(
        status_code=503,
        detail=(
            "FIREBASE_WEB_API_KEY is not configured. Set it to your Firebase Web API key "
            "so the API can complete email/password sign-in against production Auth."
        ),
    )


@router.get("/auth/me", response_model=AuthMeResponse)
async def auth_me(claims: dict = Depends(require_id_token_claims)):
    """Return uid/email from a verified Firebase ID token (Bearer)."""
    uid = claims.get("uid")
    if not uid or not isinstance(uid, str):
        raise HTTPException(status_code=401, detail="Invalid token payload")
    email = claims.get("email")
    email_out = email if isinstance(email, str) else None
    return AuthMeResponse(uid=uid, email=email_out)


@router.post("/auth/token", response_model=AuthTokenResponse)
async def post_auth_token(body: AuthTokenRequest, request: Request):
    """
    Exchange email/password for Firebase ID and refresh tokens via this API (no direct
    Identity Toolkit calls from the client). Use ``id_token`` as
    ``Authorization: Bearer`` for admin routes.

    **Lifetime:** Firebase ID tokens expire after roughly one hour; the response includes
    ``expires_in`` (seconds) and ``refresh_token`` for Firebase's token refresh flow, or
    call this endpoint again for long-running scripts.

    **Security:** Invalid credentials receive a generic **401** (no account enumeration).
    Do not log raw request bodies in production; enforce rate limits at the proxy.

    Set ``admin_only`` to require the ``admin: true`` custom claim (403 otherwise).
    """
    settings: Settings = request.app.state.settings
    web_api_key = _resolve_firebase_web_api_key(settings)

    def _sign_in() -> dict:
        return sign_in_with_password(
            web_api_key=web_api_key,
            email=body.email,
            password=body.password,
            auth_emulator_host=settings.firebase_auth_emulator_host,
        )

    try:
        data = await run_in_threadpool(_sign_in)
    except IdentityToolkitError as e:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        ) from e

    id_token = data.get("idToken")
    refresh_token = data.get("refreshToken")
    expires_in = data.get("expiresIn")
    if not id_token or not isinstance(id_token, str):
        raise HTTPException(
            status_code=502,
            detail="Unexpected response from identity provider",
        )
    refresh_out = refresh_token if isinstance(refresh_token, str) else ""
    expires_out = str(expires_in) if expires_in is not None else "3600"

    if body.admin_only:

        def _verify() -> dict:
            return auth.verify_id_token(id_token)

        try:
            claims = await run_in_threadpool(_verify)
        except (ValueError, firebase_exceptions.FirebaseError) as e:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired token",
            ) from e
        if claims.get("admin") is not True:
            raise HTTPException(status_code=403, detail="Admin privileges required")

    return AuthTokenResponse(
        id_token=id_token,
        refresh_token=refresh_out,
        expires_in=expires_out,
    )
