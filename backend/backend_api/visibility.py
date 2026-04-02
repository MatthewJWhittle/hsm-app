"""Who may read a catalog project (public vs private + allow-list)."""

from __future__ import annotations

from backend_api.schemas_project import CatalogProject


def user_can_view_project(
    project: CatalogProject,
    *,
    uid: str | None,
    is_admin: bool,
) -> bool:
    """Return True if the caller may list/read this project and its models."""
    if is_admin:
        return True
    if project.status == "archived":
        return False
    if project.visibility == "public":
        return True
    if uid is None:
        return False
    return uid in project.allowed_uids
