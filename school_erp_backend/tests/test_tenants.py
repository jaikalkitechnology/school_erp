"""Phase 1: Multi-tenant isolation + Super Admin tenant API tests.

These tests are the core acceptance criteria for Phase 1: a tenant must NEVER
see another tenant's data, and the super admin endpoints must work end-to-end.
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
from app.services.seed import seed_plans
from app.services.tenants import create_tenant


# ---- Plumbing ----------------------------------------------------------------


async def _truncate_tenants() -> None:
    """Wipe tenant-scoped state so each test gets a clean slate."""
    from sqlalchemy import delete

    from app.models.tenant import (
        Subscription,
        SubscriptionPlan,
        Tenant,
        TenantSettings,
        TenantUsageSnapshot,
    )

    async with AsyncSessionLocal() as session:
        for model in (TenantUsageSnapshot, TenantSettings, Subscription, Tenant, SubscriptionPlan):
            await session.execute(delete(model))
        await session.commit()


@pytest_asyncio.fixture
async def two_tenants():
    """Create two committed tenants (alpha, beta) for cross-tenant tests."""
    await _truncate_tenants()
    async with AsyncSessionLocal() as session:
        await seed_plans(session)
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

    # Tenant A's filtered session must only see Alpha rows.
    async with AsyncSessionLocal() as session:
        _install_filter(session.sync_session, a.id)
        rows = (await session.execute(select(TenantSettings))).scalars().all()
        assert len(rows) == 1
        assert rows[0].value == "Alpha rises"

    # And Tenant B's only sees Beta.
    async with AsyncSessionLocal() as session:
        _install_filter(session.sync_session, b.id)
        rows = (await session.execute(select(TenantSettings))).scalars().all()
        assert len(rows) == 1
        assert rows[0].value == "Beta blooms"


@pytest.mark.asyncio
async def test_unfiltered_session_sees_all_tenants(two_tenants):
    """The platform_session escape hatch is intentional - super admin needs it."""
    from app.models.tenant import Tenant

    async with AsyncSessionLocal() as session:
        rows = (await session.execute(select(Tenant))).scalars().all()
        assert len(rows) >= 2


@pytest.mark.asyncio
async def test_unsafe_cross_tenant_execution_option(two_tenants):
    """Explicit opt-out via execution_options must bypass the filter."""
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
async def test_super_admin_list_tenants(two_tenants):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as ac:
        r = await ac.get("/admin/tenants")
        assert r.status_code == 200
        subs = {t["subdomain"] for t in r.json()}
        assert {"alpha", "beta"}.issubset(subs)


@pytest.mark.asyncio
async def test_super_admin_create_and_get_tenant(seeded_plans):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as ac:
        r = await ac.post(
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

        r2 = await ac.get(f"/admin/tenants/{tenant['id']}")
        assert r2.status_code == 200
        assert r2.json()["subdomain"] == "gamma"


@pytest.mark.asyncio
async def test_super_admin_suspend_then_activate(two_tenants):
    a, _ = two_tenants
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as ac:
        r = await ac.post(f"/admin/tenants/{a.id}/suspend")
        assert r.status_code == 200
        assert r.json()["status"] == TenantStatus.SUSPENDED.value

        r = await ac.post(f"/admin/tenants/{a.id}/activate")
        assert r.status_code == 200
        assert r.json()["status"] == TenantStatus.ACTIVE.value


@pytest.mark.asyncio
async def test_suspended_tenant_blocked_at_middleware(two_tenants):
    a, _ = two_tenants
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as ac:
        await ac.post(f"/admin/tenants/{a.id}/suspend")
        # Attempt a tenant-scoped request: must 403 from the middleware.
        r = await ac.get("/v1/health", headers={"X-Tenant-Id": str(a.id)})
        assert r.status_code == 403


@pytest.mark.asyncio
async def test_tenant_health_endpoint(two_tenants):
    a, _ = two_tenants
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as ac:
        r = await ac.get(f"/admin/tenants/{a.id}/health")
        assert r.status_code == 200
        body = r.json()
        assert body["tenant_id"] == a.id
        assert body["storage_limit_mb"] > 0
        assert body["storage_used_mb"] >= 0
        assert body["storage_used_pct"] >= 0


@pytest.mark.asyncio
async def test_impersonation_token_carries_tenant(two_tenants):
    a, _ = two_tenants
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as ac:
        # Reactivate first (test ordering safety)
        await ac.post(f"/admin/tenants/{a.id}/activate")
        r = await ac.post(f"/admin/tenants/{a.id}/impersonate")
        assert r.status_code == 200
        body = r.json()
        assert body["tenant_id"] == a.id
        assert body["subdomain"] == "alpha"
        assert body["expires_in_seconds"] > 0
        from app.core.security import decode_token

        decoded = decode_token(body["token"])
        assert decoded["tenant_id"] == a.id
        assert decoded["impersonation"] is True


@pytest.mark.asyncio
async def test_duplicate_subdomain_rejected(seeded_plans):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as ac:
        payload = {
            "school_name": "Dup School",
            "school_code": "DUP-001",
            "subdomain": "duplicate",
            "plan_code": "basic",
        }
        r1 = await ac.post("/admin/tenants", json=payload)
        assert r1.status_code == 201, r1.text
        r2 = await ac.post(
            "/admin/tenants",
            json={**payload, "school_code": "DUP-002"},  # same subdomain, different code
        )
        assert r2.status_code == 409


@pytest.mark.asyncio
async def test_subdomain_resolution_via_header(two_tenants):
    """Sending X-Tenant-Subdomain attaches the right tenant_id to request.state."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as ac:
        r = await ac.get("/v1/health", headers={"X-Tenant-Subdomain": "alpha"})
        assert r.status_code == 200


@pytest.mark.asyncio
async def test_unknown_subdomain_returns_404(seeded_plans):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as ac:
        r = await ac.get("/v1/health", headers={"X-Tenant-Subdomain": "ghost"})
        assert r.status_code == 404
