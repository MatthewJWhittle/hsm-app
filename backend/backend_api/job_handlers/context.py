"""Shared context passed to every background job handler."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request

from backend_api.catalog_service import CatalogService
from backend_api.settings import Settings
from backend_api.storage import ObjectStorage


@dataclass(frozen=True, slots=True)
class JobRunContext:
    """Dependencies and identifiers for one job execution (after claim)."""

    request: Request
    settings: Settings
    storage: ObjectStorage
    catalog: CatalogService
    job_id: str
