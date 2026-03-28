"""Build Model[] from Firestore-shaped catalog JSON (``documents[]`` only)."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from backend_api.schemas import Model

logger = logging.getLogger(__name__)


def _models_from_dicts(mdicts: list[dict[str, Any]]) -> list[Model]:
    return [Model.model_validate(m) for m in mdicts]


def catalog_to_models(raw: dict[str, Any] | None) -> list[Model]:
    """Convert loaded catalog JSON to Model list. Expects a ``documents`` array."""
    if not raw:
        return []
    if "documents" not in raw:
        return []
    docs = raw["documents"]
    if not isinstance(docs, list):
        raise ValueError("catalog must contain a documents array")
    return _models_from_dicts(docs)


def try_load_catalog_json(path: str) -> tuple[dict[str, Any] | None, str | None]:
    """Load catalog JSON from disk with explicit outcomes (no silent failures).

    Returns:
        ``(data, None)`` — Parsed object (usually a dict).
        ``(None, None)`` — Path does not exist (catalog not configured; not an error).
        ``(None, detail)`` — File exists but could not be read or parsed; ``detail`` is
        safe for HTTP responses; see server logs for the underlying exception.
    """
    if not os.path.exists(path):
        logger.info("Catalog file not found at %s (CATALOG_PATH)", path)
        return None, None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        logger.warning("Catalog file at %s is not valid JSON: %s", path, e)
        return None, "Catalog file is not valid JSON."
    except OSError as e:
        logger.warning("Catalog file at %s cannot be read: %s", path, e, exc_info=True)
        return None, "Catalog file could not be read."
    if not isinstance(data, dict):
        logger.warning(
            "Catalog file at %s must be a JSON object, got %s",
            path,
            type(data).__name__,
        )
        return None, "Catalog file must be a JSON object."
    return data, None
