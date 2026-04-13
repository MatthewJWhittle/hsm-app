"""Structured API error payloads for machine-readable 4xx responses."""

from __future__ import annotations

from typing import Any


def validation_error(
    code: str,
    message: str,
    *,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build a JSON-serializable ``detail`` object for :class:`fastapi.HTTPException`.

    Clients should branch on ``code``; ``message`` is human-readable; ``context`` holds
    optional structured fields (e.g. ``expected_epsg``, ``got_crs``).
    """
    out: dict[str, Any] = {"code": code, "message": message}
    if context:
        out["context"] = context
    return out
