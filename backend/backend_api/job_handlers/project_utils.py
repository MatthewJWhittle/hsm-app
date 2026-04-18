"""Shared helpers for project-related job handlers."""

from __future__ import annotations

import json


def allowed_uids_from_json(raw: str | None) -> list[str]:
    if raw is None or not str(raw).strip():
        return []
    data = json.loads(raw)
    if not isinstance(data, list):
        raise ValueError("allowed_uids_json must be a JSON array")
    out: list[str] = []
    for x in data:
        if not isinstance(x, str):
            raise ValueError("allowed_uids_json must be an array of strings")
        out.append(x)
    return out
