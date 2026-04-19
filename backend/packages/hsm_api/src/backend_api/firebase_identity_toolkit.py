"""Server-side calls to Firebase Identity Toolkit (email/password sign-in).

Used by :func:`POST /auth/token` so clients can obtain ID tokens via this API only,
without calling Identity Toolkit URLs directly.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request


class IdentityToolkitError(Exception):
    """Identity Toolkit returned an error payload or unexpected response."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def sign_in_with_password(
    *,
    web_api_key: str,
    email: str,
    password: str,
    auth_emulator_host: str | None,
) -> dict:
    """
    POST accounts:signInWithPassword; returns Identity Toolkit JSON (idToken, refreshToken, …).

    ``auth_emulator_host`` is ``host:port`` (e.g. ``firebase-emulators:9099``). When set,
    requests use ``http`` to that host; otherwise ``https`` to Google.
    """
    key_q = urllib.parse.quote(web_api_key, safe="")
    path = f"/identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={key_q}"
    if auth_emulator_host:
        url = f"http://{auth_emulator_host}{path}"
    else:
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={key_q}"

    body = json.dumps(
        {
            "email": email,
            "password": password,
            "returnSecureToken": True,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        try:
            err_json = json.loads(err_body)
            msg = err_json.get("error", {}).get("message", err_body)
        except json.JSONDecodeError:
            msg = err_body or str(e.reason)
        raise IdentityToolkitError(msg, status_code=e.code) from e
    except urllib.error.URLError as e:
        raise IdentityToolkitError(str(e.reason or e)) from e

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise IdentityToolkitError("Invalid JSON from Identity Toolkit") from e

    if "error" in data:
        err = data["error"]
        msg = err.get("message", "Identity Toolkit error") if isinstance(err, dict) else str(err)
        raise IdentityToolkitError(msg)

    return data
