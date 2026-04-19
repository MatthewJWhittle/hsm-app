"""Normalize Firebase / Identity Toolkit claims across routes."""

from __future__ import annotations

from typing import Any


def subject_uid_from_claims(claims: dict[str, Any] | None) -> str | None:
    """Stable uid for job ownership: ``uid``, then ``sub``, then ``user_id``."""
    if not claims:
        return None
    for key in ("uid", "sub", "user_id"):
        raw = claims.get(key)
        if raw is None:
            continue
        s = str(raw).strip()
        if s:
            return s
    return None
