"""Build Model[] from Firestore-shaped catalog JSON (``documents[]`` only).

Used by tests and offline tooling; the API loads models from Firestore only.
"""

from __future__ import annotations

from typing import Any

from backend_api.schemas import Model


def _models_from_dicts(mdicts: list[dict[str, Any]]) -> list[Model]:
    return [Model.model_validate(m) for m in mdicts]


def catalog_to_models(raw: dict[str, Any] | None) -> list[Model]:
    """Convert catalog JSON to Model list. Expects a ``documents`` array."""
    if not raw:
        return []
    if "documents" not in raw:
        return []
    docs = raw["documents"]
    if not isinstance(docs, list):
        raise ValueError("catalog must contain a documents array")
    return _models_from_dicts(docs)
