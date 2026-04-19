"""Resolve catalog models with project visibility (issue #14)."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException

from backend_api.auth_deps import optional_id_token_claims
from backend_api.catalog_service import CatalogService
from backend_api.deps.catalog import require_catalog_ready
from backend_api.schemas import Model
from backend_api.schemas_project import CatalogProject
from backend_api.visibility import user_can_view_project


async def get_project_visible_or_404(
    project_id: str,
    catalog: Annotated[CatalogService, Depends(require_catalog_ready)],
    claims: Annotated[dict | None, Depends(optional_id_token_claims)],
) -> CatalogProject:
    """404 if unknown or not visible to caller."""
    p = catalog.get_project(project_id)
    if p is None:
        raise HTTPException(status_code=404, detail="project not found")
    uid = claims.get("uid") if claims else None
    is_admin = claims.get("admin") is True if claims else False
    if not user_can_view_project(p, uid=uid, is_admin=is_admin):
        raise HTTPException(status_code=404, detail="project not found")
    return p


async def get_model_visible_or_404(
    model_id: str,
    catalog: Annotated[CatalogService, Depends(require_catalog_ready)],
    claims: Annotated[dict | None, Depends(optional_id_token_claims)],
) -> Model:
    """404 if unknown or not visible to caller (private project / archived)."""
    m = catalog.get_model(model_id)
    if m is None:
        raise HTTPException(status_code=404, detail="model not found")
    uid = claims.get("uid") if claims else None
    is_admin = claims.get("admin") is True if claims else False
    if is_admin:
        return m
    if m.project_id is None:
        return m
    p = catalog.get_project(m.project_id)
    if p is None:
        raise HTTPException(status_code=404, detail="model not found")
    if not user_can_view_project(p, uid=uid, is_admin=False):
        raise HTTPException(status_code=404, detail="model not found")
    return m


def filter_models_for_viewer(
    catalog: CatalogService,
    claims: dict | None,
    *,
    project_id: str | None = None,
) -> list[Model]:
    """Models visible to the caller; admins see all."""
    uid = claims.get("uid") if claims else None
    is_admin = claims.get("admin") is True if claims else False

    def model_visible(m: Model) -> bool:
        if is_admin:
            return True
        if m.project_id is None:
            return True
        p = catalog.get_project(m.project_id)
        if p is None:
            return False
        return user_can_view_project(p, uid=uid, is_admin=False)

    out = [m for m in catalog.models if model_visible(m)]
    if project_id is not None:
        out = [m for m in out if m.project_id == project_id]
    out.sort(key=lambda x: x.id)
    return out


def filter_projects_for_viewer(
    catalog: CatalogService,
    claims: dict | None,
) -> list[CatalogProject]:
    """Catalog projects visible to the caller."""
    uid = claims.get("uid") if claims else None
    is_admin = claims.get("admin") is True if claims else False
    if is_admin:
        return sorted(catalog.projects, key=lambda p: p.id)
    return sorted(
        [
            p
            for p in catalog.projects
            if user_can_view_project(p, uid=uid, is_admin=False)
        ],
        key=lambda p: p.id,
    )
