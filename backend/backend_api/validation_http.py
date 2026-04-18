"""Shared :class:`HTTPException` factories for structured ``detail`` payloads."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from backend_api.api_errors import validation_error


def validation_http_exception(
    code: str,
    message: str,
    *,
    status_code: int = 422,
    context: dict[str, Any] | None = None,
) -> HTTPException:
    """422 (or other status) with ``validation_error`` detail shape."""
    return HTTPException(
        status_code=status_code,
        detail=validation_error(code, message, context=context),
    )


def service_unavailable_http(code: str, message: str) -> HTTPException:
    """503 with ``validation_error`` detail shape."""
    return HTTPException(
        status_code=503,
        detail=validation_error(code, message),
    )
