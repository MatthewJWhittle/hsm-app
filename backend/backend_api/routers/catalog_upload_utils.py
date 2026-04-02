"""Shared helpers for admin COG uploads and catalog reload (models + projects routers)."""

from __future__ import annotations

from fastapi import Request
from starlette.concurrency import run_in_threadpool

from backend_api.catalog_service import FirestoreCatalogService
from backend_api.cog_validation import validate_suitability_cog_bytes


async def validate_cog_bytes_threaded(content: bytes) -> None:
    """Run COG validation off the event loop."""

    def _run() -> None:
        validate_suitability_cog_bytes(content)

    await run_in_threadpool(_run)


async def reload_catalog_threaded(request: Request) -> None:
    """Reload in-process Firestore catalog after admin writes."""

    def _run() -> None:
        cat = request.app.state.catalog_service
        if isinstance(cat, FirestoreCatalogService):
            cat.reload()

    await run_in_threadpool(_run)
