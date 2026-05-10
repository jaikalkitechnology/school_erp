"""Phase 2 auth + RBAC tests."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.seed import (
    DEFAULT_SCHOOL_ADMIN_EMAIL,
    DEFAULT_SCHOOL_ADMIN_PASSWORD,
    DEFAULT_SUPER_ADMIN_EMAIL,
    DEFAULT_SUPER_ADMIN_PASSWORD,
)


@pytest.mark.asyncio
async def test_super_admin_can_login(super_admin_token):
    """Fixture itself does the login call - if we got here it worked."""
    assert super_admin_token


@pytest.mark.asyncio
async def test_school_admin_login_via_subdomain_field(super_admin_token):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as ac:
        r = await ac.post(
            "/v1/auth/login",
            json={
                "identifier": DEFAULT_SCHOOL_ADMIN_EMAIL,
                "password": DEFAULT_SCHOOL_ADMIN_PASSWORD,
                "subdomain": "demo",
            },
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["user"]["roles"] == ["school_admin"]
        assert body["user"]["tenant_subdomain"] == "demo"
        assert body["tokens"]["access_token"]


@pytest.mark.asyncio
async def test_login_via_subdomain_header(super_admin_token):
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
        headers={"X-Tenant-Subdomain": "demo"},
    ) as ac:
        r = await ac.post(
            "/v1/auth/login",
            json={
                "identifier": DEFAULT_SCHOOL_ADMIN_EMAIL,
                "password": DEFAULT_SCHOOL_ADMIN_PASSWORD,
            },
        )
        assert r.status_code == 200


@pytest.mark.asyncio
async def test_wrong_password_returns_401(super_admin_token):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as ac:
        r = await ac.post(
            "/v1/auth/login",
            json={
                "identifier": DEFAULT_SUPER_ADMIN_EMAIL,
                "password": "wrong",
                "subdomain": "platform",
            },
        )
        assert r.status_code == 401


@pytest.mark.asyncio
async def test_unknown_user_returns_401(super_admin_token):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as ac:
        r = await ac.post(
            "/v1/auth/login",
            json={
                "identifier": "ghost@nowhere",
                "password": "Whatever@123",
                "subdomain": "demo",
            },
        )
        assert r.status_code == 401


@pytest.mark.asyncio
async def test_me_returns_user_with_roles_and_perms(auth_client):
    r = await auth_client.get("/v1/auth/me")
    assert r.status_code == 200
    body = r.json()
    assert body["roles"] == ["super_admin"]
    assert "platform.tenants.manage" in body["permissions"]
    assert body["primary_role"] == "super_admin"


@pytest.mark.asyncio
async def test_me_requires_token():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as ac:
        r = await ac.get("/v1/auth/me")
        assert r.status_code == 401


@pytest.mark.asyncio
async def test_refresh_rotates_tokens(super_admin_token):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as ac:
        login = await ac.post(
            "/v1/auth/login",
            json={
                "identifier": DEFAULT_SUPER_ADMIN_EMAIL,
                "password": DEFAULT_SUPER_ADMIN_PASSWORD,
                "subdomain": "platform",
            },
        )
        old_refresh = login.json()["tokens"]["refresh_token"]

        r = await ac.post("/v1/auth/refresh", json={"refresh_token": old_refresh})
        assert r.status_code == 200, r.text
        new_pair = r.json()
        assert new_pair["refresh_token"] != old_refresh

        # Old refresh token must now be invalid (rotation revokes it).
        replay = await ac.post("/v1/auth/refresh", json={"refresh_token": old_refresh})
        assert replay.status_code == 401


@pytest.mark.asyncio
async def test_logout_revokes_refresh_token(super_admin_token):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as ac:
        login = await ac.post(
            "/v1/auth/login",
            json={
                "identifier": DEFAULT_SUPER_ADMIN_EMAIL,
                "password": DEFAULT_SUPER_ADMIN_PASSWORD,
                "subdomain": "platform",
            },
        )
        access = login.json()["tokens"]["access_token"]
        refresh = login.json()["tokens"]["refresh_token"]

        r = await ac.post(
            "/v1/auth/logout",
            json={"refresh_token": refresh},
            headers={"Authorization": f"Bearer {access}"},
        )
        assert r.status_code == 204

        replay = await ac.post("/v1/auth/refresh", json={"refresh_token": refresh})
        assert replay.status_code == 401


@pytest.mark.asyncio
async def test_school_admin_token_blocked_from_super_admin_routes(super_admin_token):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as ac:
        login = await ac.post(
            "/v1/auth/login",
            json={
                "identifier": DEFAULT_SCHOOL_ADMIN_EMAIL,
                "password": DEFAULT_SCHOOL_ADMIN_PASSWORD,
                "subdomain": "demo",
            },
        )
        token = login.json()["tokens"]["access_token"]
        r = await ac.get(
            "/admin/tenants",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 403


@pytest.mark.asyncio
async def test_token_tenant_mismatch_blocked(super_admin_token):
    """Sending a token for tenant A but hitting tenant B's subdomain must 403."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as ac:
        login = await ac.post(
            "/v1/auth/login",
            json={
                "identifier": DEFAULT_SCHOOL_ADMIN_EMAIL,
                "password": DEFAULT_SCHOOL_ADMIN_PASSWORD,
                "subdomain": "demo",
            },
        )
        token = login.json()["tokens"]["access_token"]

        # Hit /v1/auth/me through the platform subdomain - tenant_id mismatches.
        r = await ac.get(
            "/v1/auth/me",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Tenant-Subdomain": "platform",
            },
        )
        assert r.status_code == 403


@pytest.mark.asyncio
async def test_parent_children_empty_for_non_parent(auth_client):
    """Super admin isn't a parent - children list is empty, not an error."""
    r = await auth_client.get("/v1/auth/parent/children")
    assert r.status_code == 200
    assert r.json() == []
