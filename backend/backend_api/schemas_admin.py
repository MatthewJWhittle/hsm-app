"""Pydantic helpers for admin multipart fields (non-file parts)."""

from __future__ import annotations

import json
from typing import Any

from pydantic import TypeAdapter, ValidationError

from backend_api.schemas import ModelMetadata

_driver_config_adapter = TypeAdapter(dict[str, Any])


def parse_driver_config_form(raw: str | None) -> dict[str, Any] | None:
    """
    Parse optional ``driver_config`` form field as JSON object.

    Raises ``ValueError`` with a message suitable for HTTP 422 when invalid.
    """
    if raw is None or raw.strip() == "":
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"driver_config must be valid JSON: {e}") from e
    if not isinstance(data, dict):
        raise ValueError("driver_config must be a JSON object")
    try:
        return _driver_config_adapter.validate_python(data)
    except ValidationError as e:
        raise ValueError(str(e)) from e


def parse_metadata_form(raw: str | None) -> ModelMetadata | None:
    """
    Parse optional ``metadata`` form field as JSON object (``ModelMetadata`` shape).

    Raises ``ValueError`` with a message suitable for HTTP 422 when invalid.
    """
    if raw is None or raw.strip() == "":
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"metadata must be valid JSON: {e}") from e
    if not isinstance(data, dict):
        raise ValueError("metadata must be a JSON object")
    try:
        return ModelMetadata.model_validate(data)
    except ValidationError as e:
        raise ValueError(str(e)) from e
