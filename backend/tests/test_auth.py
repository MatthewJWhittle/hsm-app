"""Tests for GET /auth/me (Firebase ID token verification)."""

import importlib
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    documents = [
        {
            "id": "test-bat--roosting",
            "species": "Test bat",
            "activity": "Roosting",
            "artifact_root": "/data/cog",
            "suitability_cog_path": "test_cog.tif",
        }
    ]
    from tests.helpers import mock_firestore_client_for_documents

    mock_client = mock_firestore_client_for_documents(documents)
    with (
        patch("backend_api.catalog_service.firestore.Client", return_value=mock_client),
        patch(
            "backend_api.auth_deps.auth.verify_id_token",
            return_value={"uid": "user-1", "email": "dev@example.com"},
        ),
    ):
        import backend_api.main as main

        importlib.reload(main)
        with TestClient(main.app) as c:
            yield c


def test_auth_me_requires_bearer(client):
    r = client.get("/auth/me")
    assert r.status_code == 401


def test_auth_me_returns_uid_and_email(client):
    r = client.get("/auth/me", headers={"Authorization": "Bearer fake.jwt.token"})
    assert r.status_code == 200
    data = r.json()
    assert data["uid"] == "user-1"
    assert data["email"] == "dev@example.com"


def test_auth_token_returns_id_token(client):
    with patch("backend_api.routers.auth.sign_in_with_password") as m:
        m.return_value = {
            "idToken": "fake.id.token",
            "refreshToken": "rt",
            "expiresIn": "3600",
        }
        r = client.post(
            "/auth/token",
            json={"email": "dev@example.com", "password": "secret"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["id_token"] == "fake.id.token"
        assert data["refresh_token"] == "rt"
        assert data["token_type"] == "Bearer"
        m.assert_called_once()


def test_auth_token_invalid_password_401(client):
    from backend_api.firebase_identity_toolkit import IdentityToolkitError

    with patch(
        "backend_api.routers.auth.sign_in_with_password",
        side_effect=IdentityToolkitError("INVALID_PASSWORD"),
    ):
        r = client.post(
            "/auth/token",
            json={"email": "dev@example.com", "password": "wrong"},
        )
    assert r.status_code == 401
    assert r.json()["detail"] == "Invalid email or password"


def test_auth_token_admin_only_requires_admin_claim(client):
    with (
        patch(
            "backend_api.routers.auth.sign_in_with_password",
            return_value={
                "idToken": "fake.id.token",
                "refreshToken": "rt",
                "expiresIn": "3600",
            },
        ),
        patch(
            "backend_api.routers.auth.auth.verify_id_token",
            return_value={"uid": "u1", "admin": False},
        ),
    ):
        r = client.post(
            "/auth/token",
            json={
                "email": "dev@example.com",
                "password": "secret",
                "admin_only": True,
            },
        )
    assert r.status_code == 403


def test_auth_token_admin_only_ok_when_admin(client):
    with (
        patch(
            "backend_api.routers.auth.sign_in_with_password",
            return_value={
                "idToken": "fake.id.token",
                "refreshToken": "rt",
                "expiresIn": "3600",
            },
        ),
        patch(
            "backend_api.routers.auth.auth.verify_id_token",
            return_value={"uid": "u1", "admin": True},
        ),
    ):
        r = client.post(
            "/auth/token",
            json={
                "email": "dev@example.com",
                "password": "secret",
                "admin_only": True,
            },
        )
    assert r.status_code == 200
    assert r.json()["id_token"] == "fake.id.token"


def test_auth_me_invalid_token_401():
    documents = [
        {
            "id": "test-bat--roosting",
            "species": "Test bat",
            "activity": "Roosting",
            "artifact_root": "/data/cog",
            "suitability_cog_path": "test_cog.tif",
        }
    ]
    from tests.helpers import mock_firestore_client_for_documents

    mock_client = mock_firestore_client_for_documents(documents)
    mock_verify = MagicMock(side_effect=ValueError("bad token"))
    with (
        patch("backend_api.catalog_service.firestore.Client", return_value=mock_client),
        patch("backend_api.auth_deps.auth.verify_id_token", mock_verify),
    ):
        import backend_api.main as main

        importlib.reload(main)
        with TestClient(main.app) as c:
            r = c.get("/auth/me", headers={"Authorization": "Bearer x"})
    assert r.status_code == 401
