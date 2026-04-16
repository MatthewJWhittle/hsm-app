"""Shared helpers for admin COG uploads and catalog reload (models + projects routers)."""

from __future__ import annotations

from pathlib import Path

from fastapi import Request
from starlette.concurrency import run_in_threadpool

from backend_api.catalog_service import FirestoreCatalogService
from backend_api.cog_validation import validate_suitability_cog_bytes, validate_suitability_cog_path


async def validate_cog_bytes_threaded(content: bytes) -> None:
    """Run COG validation off the event loop."""

    def _run() -> None:
        validate_suitability_cog_bytes(content)

    await run_in_threadpool(_run)


async def validate_cog_path_threaded(path: str) -> None:
    """Run COG validation for an on-disk path off the event loop."""

    def _run() -> None:
        validate_suitability_cog_path(path=Path(path))

    await run_in_threadpool(_run)


async def reload_catalog_threaded(request: Request) -> None:
    """Reload in-process Firestore catalog after admin writes."""

    def _run() -> None:
        cat = request.app.state.catalog_service
        if isinstance(cat, FirestoreCatalogService):
            cat.reload()

    await run_in_threadpool(_run)
