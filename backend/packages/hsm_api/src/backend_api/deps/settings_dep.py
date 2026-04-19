"""Access app settings from request state."""

from __future__ import annotations

from fastapi import Request

from hsm_core.settings import Settings


def get_settings(request: Request) -> Settings:
    return request.app.state.settings
