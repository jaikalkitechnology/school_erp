"""Phase 21 subscription billing tests."""

from datetime import date, timedelta

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.seed import (
    DEFAULT_SCHOOL_ADMIN_EMAIL,
    DEFAULT_SCHOOL_ADMIN_PASSWORD,
)


async def _login(subdomain: str, email: str, password: str) -> str:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as ac:
        r = await ac.post(
            "/v1/auth/login",
            json={"identifier": email, "password": password, "subdomain": subdomain},
        )
        assert r.status_code == 200, r.text
        return r.json()["tokens"]["access_token"]


@pytest_asyncio.fixture
async def super_client(super_admin_token):
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    ) as ac:
        yield ac


async def _demo_tenant_id(super_client) -> int:
    listing = (await super_client.get("/admin/tenants")).json()
    for t in listing:
        if t["subdomain"] == "demo":
            return t["id"]
    raise AssertionError("demo tenant not seeded")


@pytest.mark.asyncio
async def test_generate_invoice_with_intra_gst(super_client):
    tid = await _demo_tenant_id(super_client)
    today = date.today()
    inv = (await super_client.post(
        "/admin/billing/invoices",
        json={
            "tenant_id": tid,
            "period_start": today.isoformat(),
            "period_end": (today + timedelta(days=29)).isoformat(),
            "gst_rate_pct": 18,
            "gst_treatment": "intra",
            "place_of_supply": "Maharashtra",
        },
    )).json()
    assert inv["status"] == "pending"
    # 30 days = 1 month exactly. Default plan (basic) monthly_price varies by seed.
    # Check that subtotal+tax math is consistent.
    assert float(inv["subtotal"]) > 0
    assert float(inv["cgst_amount"]) == float(inv["sgst_amount"])
    assert float(inv["igst_amount"]) == 0
    assert abs(
        float(inv["total_amount"])
        - (float(inv["subtotal"]) - float(inv["discount_amount"]) + float(inv["tax_amount"]))
    ) < 0.02


@pytest.mark.asyncio
async def test_generate_invoice_inter_state_uses_igst(super_client):
    tid = await _demo_tenant_id(super_client)
    today = date.today()
    inv = (await super_client.post(
        "/admin/billing/invoices",
        json={
            "tenant_id": tid,
            "period_start": today.isoformat(),
            "period_end": (today + timedelta(days=29)).isoformat(),
            "gst_rate_pct": 18,
            "gst_treatment": "inter",
            "place_of_supply": "Karnataka",
        },
    )).json()
    assert float(inv["cgst_amount"]) == 0
    assert float(inv["sgst_amount"]) == 0
    assert float(inv["igst_amount"]) > 0
    assert abs(float(inv["tax_amount"]) - float(inv["igst_amount"])) < 0.01


@pytest.mark.asyncio
async def test_payment_partial_overpay_and_status_progression(super_client):
    tid = await _demo_tenant_id(super_client)
    today = date.today()
    inv = (await super_client.post(
        "/admin/billing/invoices",
        json={
            "tenant_id": tid,
            "period_start": today.isoformat(),
            "period_end": (today + timedelta(days=29)).isoformat(),
            "gst_treatment": "intra",
        },
    )).json()
    total = float(inv["total_amount"])

    # Half-pay -> partial.
    a = await super_client.post(
        "/admin/billing/payments",
        json={"invoice_id": inv["id"], "amount": round(total / 2, 2), "method": "bank_transfer"},
    )
    assert a.status_code == 201
    detail = (await super_client.get(f"/admin/billing/invoices/{inv['id']}")).json()
    assert detail["status"] == "partial"

    # Pay rest -> paid.
    remainder = round(total - float(detail["paid_amount"]), 2)
    b = await super_client.post(
        "/admin/billing/payments",
        json={"invoice_id": inv["id"], "amount": remainder, "method": "upi"},
    )
    assert b.status_code == 201
    paid = (await super_client.get(f"/admin/billing/invoices/{inv['id']}")).json()
    assert paid["status"] == "paid"

    # Overpay rejected.
    bad = await super_client.post(
        "/admin/billing/payments",
        json={"invoice_id": inv["id"], "amount": 1, "method": "upi"},
    )
    assert bad.status_code == 400


@pytest.mark.asyncio
async def test_refund_caps_at_paid_amount(super_client):
    tid = await _demo_tenant_id(super_client)
    today = date.today()
    inv = (await super_client.post(
        "/admin/billing/invoices",
        json={
            "tenant_id": tid,
            "period_start": today.isoformat(),
            "period_end": (today + timedelta(days=29)).isoformat(),
            "gst_treatment": "intra",
        },
    )).json()
    total = float(inv["total_amount"])
    await super_client.post(
        "/admin/billing/payments",
        json={"invoice_id": inv["id"], "amount": total, "method": "razorpay"},
    )
    # Over-refund.
    bad = await super_client.post(
        "/admin/billing/refunds",
        json={"invoice_id": inv["id"], "amount": total + 100},
    )
    assert bad.status_code == 400
    # Full refund flips status.
    ok = await super_client.post(
        "/admin/billing/refunds",
        json={"invoice_id": inv["id"], "amount": total, "reason": "Service downtime"},
    )
    assert ok.status_code == 201
    final = (await super_client.get(f"/admin/billing/invoices/{inv['id']}")).json()
    assert final["status"] == "refunded"


@pytest.mark.asyncio
async def test_void_paid_invoice_blocked(super_client):
    tid = await _demo_tenant_id(super_client)
    today = date.today()
    inv = (await super_client.post(
        "/admin/billing/invoices",
        json={
            "tenant_id": tid,
            "period_start": today.isoformat(),
            "period_end": (today + timedelta(days=29)).isoformat(),
            "gst_treatment": "intra",
        },
    )).json()
    await super_client.post(
        "/admin/billing/payments",
        json={"invoice_id": inv["id"], "amount": float(inv["total_amount"])},
    )
    bad = await super_client.post(f"/admin/billing/invoices/{inv['id']}/void")
    assert bad.status_code == 400


@pytest.mark.asyncio
async def test_plan_change_with_proration(super_client):
    tid = await _demo_tenant_id(super_client)
    plans = (await super_client.get("/admin/plans")).json()
    cheaper = min(plans, key=lambda p: float(p["monthly_price"]))
    pricier = max(plans, key=lambda p: float(p["monthly_price"]))
    # Set tenant to the cheaper plan first.
    await super_client.post(
        f"/admin/tenants/{tid}/change-plan",
        json={"plan_id": cheaper["id"]},
    )
    # Ensure subscription_end is at least 30 days out.
    from datetime import datetime as _dt

    from sqlalchemy import update

    from app.database import AsyncSessionLocal
    from app.models.tenant import Tenant

    today = date.today()
    end_dt = _dt.combine(today + timedelta(days=30), _dt.min.time())
    async with AsyncSessionLocal() as s:
        await s.execute(update(Tenant).where(Tenant.id == tid).values(subscription_end=end_dt))
        await s.commit()
    res = await super_client.post(
        "/admin/billing/plan-change",
        json={
            "tenant_id": tid,
            "new_plan_id": pricier["id"],
            "effective_on": today.isoformat(),
            "pro_rate": True,
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["new_plan_id"] == pricier["id"]
    if float(pricier["monthly_price"]) > float(cheaper["monthly_price"]):
        assert float(body["pro_rated_charge"]) > 0
        assert body["invoice_id"] is not None


@pytest.mark.asyncio
async def test_auto_renew_skips_existing(super_client):
    tid = await _demo_tenant_id(super_client)
    # Wind subscription_end to 5 days in the future so auto-renew picks it up.
    from datetime import datetime as _dt

    from sqlalchemy import update

    from app.database import AsyncSessionLocal
    from app.models.tenant import Tenant

    today = date.today()
    new_end = _dt.combine(today + timedelta(days=5), _dt.min.time())
    async with AsyncSessionLocal() as s:
        await s.execute(
            update(Tenant)
            .where(Tenant.id == tid)
            .values(subscription_end=new_end, status="active")
        )
        await s.commit()

    first = (await super_client.post(
        "/admin/billing/auto-renew",
        json={"period_months": 1, "due_in_days": 14},
    )).json()
    assert first["generated"] >= 1
    second = (await super_client.post(
        "/admin/billing/auto-renew",
        json={"period_months": 1, "due_in_days": 14},
    )).json()
    assert second["generated"] == 0
    assert second["skipped"] >= 1


@pytest.mark.asyncio
async def test_reports_endpoint(super_client):
    tid = await _demo_tenant_id(super_client)
    today = date.today()
    await super_client.post(
        "/admin/billing/invoices",
        json={
            "tenant_id": tid,
            "period_start": today.isoformat(),
            "period_end": (today + timedelta(days=29)).isoformat(),
            "gst_treatment": "intra",
        },
    )
    body = (await super_client.get("/admin/billing/reports")).json()
    assert float(body["total_billed"]) > 0
    assert float(body["mrr"]) >= 0


@pytest.mark.asyncio
async def test_school_admin_can_view_own_subscription():
    token = await _login("demo", DEFAULT_SCHOOL_ADMIN_EMAIL, DEFAULT_SCHOOL_ADMIN_PASSWORD)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-Subdomain": "demo"},
    ) as ac:
        r = await ac.get("/v1/school-admin/subscription")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["plan_code"] is not None


@pytest.mark.asyncio
async def test_super_admin_token_required_for_billing(super_admin_token):
    # School admin token cannot read /admin/billing.
    token = await _login("demo", DEFAULT_SCHOOL_ADMIN_EMAIL, DEFAULT_SCHOOL_ADMIN_PASSWORD)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-Subdomain": "demo"},
    ) as ac:
        r = await ac.get("/admin/billing/invoices")
        assert r.status_code == 403
