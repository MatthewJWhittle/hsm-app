"""Build Model[] from the on-disk catalog JSON (local dev; Firestore snapshot or legacy shapes)."""

from __future__ import annotations

import json
import os
import re
from typing import Any

from backend_api.schemas import Model

_SLUG_RE = re.compile(r"[^a-z0-9]+")


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
    """Convert loaded catalog JSON to Model list (Firestore snapshot, explicit models[], or legacy items[])."""
    if not raw:
        return []

    explicit = _explicit_models_list(raw)
    if explicit is not None:
        return _models_from_dicts(explicit)

    items = raw.get("items")
    if not isinstance(items, list):
        return []

    return _derive_models_from_items(items)


def load_index(path: str) -> dict[str, Any] | None:
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None
