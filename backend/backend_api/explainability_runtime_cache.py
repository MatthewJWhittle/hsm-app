"""In-process LRU cache for permutation SHAP explainers (pickle + background → ``shap.Explainer``)."""

from __future__ import annotations

import logging
import threading
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)

_MAX_ENTRIES = 8


@dataclass(frozen=True)
class ShapExplainerBundle:
    """Reusable SHAP explainer plus display metadata (paths unchanged while this is valid)."""

    explainer: Any
    fnames: list[str]
    pos: int
    band_labels: list | None


_lock = threading.Lock()
_lru: "OrderedDict[str, ShapExplainerBundle]" = OrderedDict()
_meta: dict[str, tuple[float, float, int, str, str]] = {}
"""model_id → (model_mtime, bg_mtime, max_background_rows, model_path_str, bg_path_str)."""


def _touch(key: str, bundle: ShapExplainerBundle, meta: tuple[float, float, int, str, str]) -> None:
    _lru[key] = bundle
    _meta[key] = meta
    _lru.move_to_end(key)
    while len(_lru) > _MAX_ENTRIES:
        old_k, _ = _lru.popitem(last=False)
        _meta.pop(old_k, None)
        logger.debug("explainability cache evicted %s", old_k)


def get_or_build_shap_bundle(
    model_id: str,
    model_path: Path,
    bg_path: Path,
    max_background_rows: int,
    factory: Callable[[], ShapExplainerBundle],
) -> ShapExplainerBundle:
    """
    Return a cached :class:`ShapExplainerBundle` when pickle + parquet mtimes and row cap match.

    ``factory`` must load artifacts and build the explainer (no SHAP run for the query row).
    """
    try:
        mt_model = model_path.stat().st_mtime
        mt_bg = bg_path.stat().st_mtime
    except OSError:
        # Tests may mock ``is_file`` without a real file; treat as uncacheable miss.
        mt_model, mt_bg = -1.0, -1.0
    key = model_id
    mps, bgps = str(model_path), str(bg_path)
    meta = (mt_model, mt_bg, max_background_rows, mps, bgps)

    with _lock:
        prev = _meta.get(key)
        hit = _lru.get(key)
        if (
            hit is not None
            and prev is not None
            and prev == meta
        ):
            _lru.move_to_end(key)
            return hit

    bundle = factory()

    with _lock:
        cur = _meta.get(key)
        cur_hit = _lru.get(key)
        if cur_hit is not None and cur is not None and cur == meta:
            _lru.move_to_end(key)
            return cur_hit
        _touch(key, bundle, meta)
    return bundle


def clear_explainability_cache_for_tests() -> None:
    """Reset cache between tests."""
    with _lock:
        _lru.clear()
        _meta.clear()
