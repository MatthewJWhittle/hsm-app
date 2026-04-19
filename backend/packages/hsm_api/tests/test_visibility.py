"""Unit tests for catalog project visibility helpers."""

from backend_api.schemas_project import CatalogProject
from backend_api.visibility import user_can_view_project


def _project(**kwargs: object) -> CatalogProject:
    base = {
        "id": "p1",
        "name": "P",
        "status": "active",
        "visibility": "public",
        "allowed_uids": [],
        "driver_artifact_root": "/a",
        "driver_cog_path": "x.tif",
    }
    base.update(kwargs)
    return CatalogProject.model_validate(base)


def test_public_visible_without_uid():
    p = _project(visibility="public")
    assert user_can_view_project(p, uid=None, is_admin=False)


def test_private_requires_uid_or_admin():
    p = _project(visibility="private", allowed_uids=["u1"])
    assert not user_can_view_project(p, uid=None, is_admin=False)
    assert user_can_view_project(p, uid="u1", is_admin=False)
    assert user_can_view_project(p, uid="u2", is_admin=True)


def test_archived_hidden_for_non_admin():
    p = _project(status="archived", visibility="public")
    assert not user_can_view_project(p, uid=None, is_admin=False)
    assert user_can_view_project(p, uid=None, is_admin=True)
