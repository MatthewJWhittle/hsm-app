"""Parse and narrow catalog project form fields to Literal types (no type: ignore)."""

from __future__ import annotations

from typing import Literal

from fastapi import HTTPException


def parse_visibility(s: str) -> Literal["public", "private"]:
    if s == "public":
        return "public"
    if s == "private":
        return "private"
    raise HTTPException(status_code=422, detail="visibility must be public or private")


def parse_status_optional(s: str | None) -> Literal["active", "archived"] | None:
    if s is None:
        return None
    if s == "active":
        return "active"
    if s == "archived":
        return "archived"
    raise HTTPException(status_code=422, detail="status must be active or archived")


def parse_visibility_optional(s: str | None) -> Literal["public", "private"] | None:
    if s is None:
        return None
    return parse_visibility(s)
