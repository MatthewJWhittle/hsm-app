"""Build Model[] from on-disk catalog JSON (local dev; Firestore snapshot or legacy)."""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from backend_api.schemas import Model

logger = logging.getLogger(__name__)

_SLUG_RE = re.compile(r"[^a-z0-9]+")

# Slug rules mirror `scripts/generate_hsm_index.py` for local dev only. That script will
# go away once COGs are uploaded via the API and written to the database; this module
# stays the single place for legacy `items[]` → Model derivation.


def slug_segment(name: str) -> str:
    s = name.lower().strip()
    s = _SLUG_RE.sub("-", s)
    return s.strip("-")


def stable_model_id(species: str, activity: str) -> str:
    """Structured slug: taxon--activity (double hyphen between major parts)."""
    return f"{slug_segment(species)}--{slug_segment(activity)}"


def _explicit_models_list(raw: dict[str, Any]) -> list[dict[str, Any]] | None:
    """Explicit Model rows: Firestore snapshot `documents[]`, or legacy `models[]`."""
    docs = raw.get("documents")
    if isinstance(docs, list) and docs:
        return docs
    models = raw.get("models")
    if isinstance(models, list) and models:
        return models
    return None


def _derive_models_from_items(items: list[dict[str, Any]]) -> list[Model]:
    seen_ids: dict[str, int] = {}
    out: list[Model] = []

    for item in items:
        species = item.get("species") or ""
        activity = item.get("activity") or ""
        cog_path = item.get("cog_path") or ""
        if not species or not activity or not cog_path:
            continue

        base_id = stable_model_id(species, activity)
        n = seen_ids.get(base_id, 0)
        if n:
            model_id = f"{base_id}--{n + 1}"
        else:
            model_id = base_id
        seen_ids[base_id] = n + 1

        # Normalize path: expect /data/... in Docker
        if not os.path.isabs(cog_path):
            cog_path = os.path.join("/data", cog_path.lstrip("/"))

        artifact_root = os.path.dirname(cog_path) or "/data"
        basename = os.path.basename(cog_path)
        out.append(
            Model(
                id=model_id,
                species=species,
                activity=activity,
                artifact_root=artifact_root,
                suitability_cog_path=basename,
            )
        )

    return out


def _models_from_dicts(mdicts: list[dict[str, Any]]) -> list[Model]:
    return [Model.model_validate(m) for m in mdicts]


def catalog_to_models(raw: dict[str, Any] | None) -> list[Model]:
    """Convert loaded catalog JSON to Model list (Firestore, models[], or legacy items[])."""
    if not raw:
        return []

    explicit = _explicit_models_list(raw)
    if explicit is not None:
        return _models_from_dicts(explicit)

    items = raw.get("items")
    if not isinstance(items, list):
        return []

    return _derive_models_from_items(items)


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
