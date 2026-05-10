"""Phase 1: Multi-tenant isolation + Super Admin tenant API tests.

Phase 2 added auth gating on /admin/*, so these tests now go through
``auth_client`` (which logs in as the seeded super admin).
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.tenant_session import _install_filter
from app.database import AsyncSessionLocal
from app.main import app
from app.models.tenant import TenantSettings, TenantStatus
from app.schemas.tenant import TenantCreate
from app.services.tenants import create_tenant


@pytest_asyncio.fixture
async def two_tenants(super_admin_token):
    """Seed runs as part of super_admin_token. We just add alpha+beta on top."""
    async with AsyncSessionLocal() as session:
        a = await create_tenant(
            session,
            TenantCreate(
                school_name="Alpha School",
                school_code="ALPHA-001",
                subdomain="alpha",
                plan_code="basic",
            ),
        )
        b = await create_tenant(
            session,
            TenantCreate(
                school_name="Beta School",
                school_code="BETA-001",
                subdomain="beta",
                plan_code="standard",
            ),
        )
    return a, b


# ---- Cross-tenant isolation --------------------------------------------------


@pytest.mark.asyncio
async def test_tenant_scoped_session_blocks_cross_tenant_reads(two_tenants):
    a, b = two_tenants

    async with AsyncSessionLocal() as raw:
        raw.add_all(
            [
                TenantSettings(tenant_id=a.id, category="brand", key="motto", value="Alpha rises"),
                TenantSettings(tenant_id=b.id, category="brand", key="motto", value="Beta blooms"),
            ]
        )
        await raw.commit()

    async with AsyncSessionLocal() as session:
        _install_filter(session.sync_session, a.id)
        rows = (await session.execute(select(TenantSettings))).scalars().all()
        assert {r.value for r in rows} == {"Alpha rises"}

    async with AsyncSessionLocal() as session:
        _install_filter(session.sync_session, b.id)
        rows = (await session.execute(select(TenantSettings))).scalars().all()
        assert {r.value for r in rows} == {"Beta blooms"}


@pytest.mark.asyncio
async def test_unfiltered_session_sees_all_tenants(two_tenants):
    from app.models.tenant import Tenant

    async with AsyncSessionLocal() as session:
        rows = (await session.execute(select(Tenant))).scalars().all()
        # Platform + demo + alpha + beta
        assert len(rows) >= 4


@pytest.mark.asyncio
async def test_unsafe_cross_tenant_execution_option(two_tenants):
    a, b = two_tenants
    async with AsyncSessionLocal() as raw:
        raw.add_all(
            [
                TenantSettings(tenant_id=a.id, category="brand", key="motto", value="A"),
                TenantSettings(tenant_id=b.id, category="brand", key="motto", value="B"),
            ]
        )
        await raw.commit()

    async with AsyncSessionLocal() as session:
        _install_filter(session.sync_session, a.id)
        rows = (
            await session.execute(
                select(TenantSettings).execution_options(unsafe_cross_tenant=True)
            )
        ).scalars().all()
        assert len(rows) >= 2


# ---- Super Admin HTTP API ---------------------------------------------------


@pytest.mark.asyncio
async def test_super_admin_routes_require_auth():
    """Without a token, /admin/* must 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as ac:
        r = await ac.get("/admin/tenants")
        assert r.status_code == 401


@pytest.mark.asyncio
async def test_super_admin_list_tenants(auth_client, two_tenants):
    r = await auth_client.get("/admin/tenants")
    assert r.status_code == 200, r.text
    subs = {t["subdomain"] for t in r.json()}
    assert {"alpha", "beta"}.issubset(subs)


@pytest.mark.asyncio
async def test_super_admin_create_and_get_tenant(auth_client):
    r = await auth_client.post(
        "/admin/tenants",
        json={
            "school_name": "Gamma School",
            "school_code": "GAMMA-001",
            "subdomain": "gamma",
            "plan_code": "premium",
        },
    )
    assert r.status_code == 201, r.text
    tenant = r.json()
    assert tenant["subdomain"] == "gamma"
    assert tenant["status"] == "trial"

    r2 = await auth_client.get(f"/admin/tenants/{tenant['id']}")
    assert r2.status_code == 200
    assert r2.json()["subdomain"] == "gamma"


@pytest.mark.asyncio
async def test_super_admin_suspend_then_activate(auth_client, two_tenants):
    a, _ = two_tenants
    r = await auth_client.post(f"/admin/tenants/{a.id}/suspend")
    assert r.status_code == 200
    assert r.json()["status"] == TenantStatus.SUSPENDED.value

    r = await auth_client.post(f"/admin/tenants/{a.id}/activate")
    assert r.status_code == 200
    assert r.json()["status"] == TenantStatus.ACTIVE.value


@pytest.mark.asyncio
async def test_suspended_tenant_blocked_at_middleware(auth_client, two_tenants):
    a, _ = two_tenants
    await auth_client.post(f"/admin/tenants/{a.id}/suspend")
    # A *separate* unauthenticated client hits a tenant route; middleware must 403.
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as ac:
        r = await ac.get("/v1/health", headers={"X-Tenant-Id": str(a.id)})
        assert r.status_code == 403


@pytest.mark.asyncio
async def test_tenant_health_endpoint(auth_client, two_tenants):
    a, _ = two_tenants
    r = await auth_client.get(f"/admin/tenants/{a.id}/health")
    assert r.status_code == 200
    body = r.json()
    assert body["tenant_id"] == a.id
    assert body["storage_limit_mb"] > 0
    assert body["storage_used_mb"] >= 0
    assert body["storage_used_pct"] >= 0


@pytest.mark.asyncio
async def test_impersonation_token_carries_tenant(auth_client, two_tenants):
    a, _ = two_tenants
    await auth_client.post(f"/admin/tenants/{a.id}/activate")
    r = await auth_client.post(f"/admin/tenants/{a.id}/impersonate")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["tenant_id"] == a.id
    assert body["subdomain"] == "alpha"
    assert body["expires_in_seconds"] > 0

    from app.core.security import decode_token

    decoded = decode_token(body["token"])
    assert decoded["tenant_id"] == a.id
    assert decoded["impersonation"] is True


@pytest.mark.asyncio
async def test_duplicate_subdomain_rejected(auth_client):
    payload = {
        "school_name": "Dup School",
        "school_code": "DUP-001",
        "subdomain": "duplicate",
        "plan_code": "basic",
    }
    r1 = await auth_client.post("/admin/tenants", json=payload)
    assert r1.status_code == 201, r1.text
    r2 = await auth_client.post("/admin/tenants", json={**payload, "school_code": "DUP-002"})
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_subdomain_resolution_via_header(two_tenants):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as ac:
        r = await ac.get("/v1/health", headers={"X-Tenant-Subdomain": "alpha"})
        assert r.status_code == 200


@pytest.mark.asyncio
async def test_unknown_subdomain_returns_404(super_admin_token):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as ac:
        r = await ac.get("/v1/health", headers={"X-Tenant-Subdomain": "ghost"})
        assert r.status_code == 404
