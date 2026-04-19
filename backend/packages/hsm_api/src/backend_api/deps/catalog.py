"""Catalog and storage dependencies."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request

from backend_api.catalog_service import CatalogService
from backend_api.schemas import Model
from backend_api.storage import ObjectStorage


def get_catalog_service(request: Request) -> CatalogService:
    return request.app.state.catalog_service


def get_object_storage(request: Request) -> ObjectStorage:
    return request.app.state.object_storage


def _raise_catalog_http_errors(catalog: CatalogService) -> None:
    if catalog.validation_error:
        raise HTTPException(status_code=503, detail=catalog.validation_error)
    if catalog.load_error:
        raise HTTPException(status_code=503, detail=catalog.load_error)


def require_catalog_ready(catalog: CatalogService = Depends(get_catalog_service)) -> CatalogService:
    """503 if Firestore catalog failed validation or could not load."""
    _raise_catalog_http_errors(catalog)
    return catalog


def get_model_or_404(
    model_id: str,
    catalog: CatalogService = Depends(require_catalog_ready),
) -> Model:
    """Resolve ``model_id`` to a :class:`Model` or 404."""
    m = catalog.get_model(model_id)
    if m is None:
        raise HTTPException(status_code=404, detail="model not found")
    return m
