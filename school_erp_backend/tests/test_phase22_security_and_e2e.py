"""Phase 22 final-prep tests.

Two flavours bundled here so the whole production-readiness story shows up
together:

1. **Cross-tenant pen tests** — confirm that a token issued for tenant A
   cannot reach tenant B's data through any of the headers / claims we
   accept. These are not "happy-path" tests; they're paranoid attacks
   against the multi-tenant boundary.
2. **End-to-end happy path** — admit a student, mark her present, generate
   a fee invoice, collect cash, and verify the parent dashboard reflects
   every step.
"""

from datetime import date

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


def _headers(token: str, subdomain: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "X-Tenant-Subdomain": subdomain}


@pytest_asyncio.fixture
async def two_tenants(super_admin_token):
    """Provision a second tenant ("other") with its own school admin so we
    have two independent schools to isolate."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    ) as super_ac:
        r = await super_ac.post(
            "/admin/tenants",
            json={
                "school_name": "Other School",
                "school_code": "OTHER-002",
                "subdomain": "other",
                "plan_code": "basic",
            },
        )
        assert r.status_code == 201, r.text
        other_tid = r.json()["id"]

    from app.database import AsyncSessionLocal
    from app.services.seed import _ensure_user, seed_rbac_for_tenant

    async with AsyncSessionLocal() as session:
        await seed_rbac_for_tenant(session, other_tid)
        await _ensure_user(
            session,
            tenant_id=other_tid,
            email="admin@other.school",
            full_name="Other Admin",
            password="Other@123",
            role_codes=["school_admin"],
        )

    demo_token = await _login("demo", DEFAULT_SCHOOL_ADMIN_EMAIL, DEFAULT_SCHOOL_ADMIN_PASSWORD)
    other_token = await _login("other", "admin@other.school", "Other@123")
    return {"demo_token": demo_token, "other_token": other_token, "other_tid": other_tid}


# =============================================================================
# Cross-tenant pen tests
# =============================================================================


@pytest.mark.asyncio
async def test_demo_token_with_other_subdomain_is_403(two_tenants):
    """Sending a demo token with X-Tenant-Subdomain: other must 403, not
    leak data from `other`. Defense-in-depth: even if middleware resolved
    `other`, the JWT carries `tenant_id=demo_id` and the principal check
    rejects the mismatch."""
    demo_token = two_tenants["demo_token"]
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
        headers=_headers(demo_token, "other"),
    ) as ac:
        r = await ac.get("/v1/school-admin/dashboard")
        assert r.status_code == 403


@pytest.mark.asyncio
async def test_demo_admin_cannot_see_other_tenants_students(two_tenants):
    """Each tenant creates a student; queries with the other token return
    only their own."""
    demo = two_tenants["demo_token"]
    other = two_tenants["other_token"]

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
        headers=_headers(demo, "demo"),
    ) as demo_ac:
        await demo_ac.post(
            "/v1/school-admin/students",
            json={
                "full_name": "Demo Pupil",
                "parent_phone": "+919900000200",
                "parent_email": "demo.pupil@h.test",
                "father_name": "Demo P",
            },
        )
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
        headers=_headers(other, "other"),
    ) as other_ac:
        await other_ac.post(
            "/v1/school-admin/students",
            json={
                "full_name": "Other Pupil",
                "parent_phone": "+919900000201",
                "parent_email": "other.pupil@h.test",
                "father_name": "Other P",
            },
        )
        listing = (await other_ac.get("/v1/school-admin/students")).json()
    names = [s["full_name"] for s in listing["items"]]
    assert "Other Pupil" in names
    assert "Demo Pupil" not in names


@pytest.mark.asyncio
async def test_super_admin_token_blocked_from_school_admin_routes(super_admin_token):
    """Super-admin token must NOT pass the school-admin RBAC gate.
    This catches the regression where someone mistakenly grants the
    super_admin role both scopes."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    ) as ac:
        # All three sample paths should refuse super-admin tokens.
        for path in (
            "/v1/school-admin/dashboard",
            "/v1/school-admin/students",
            "/v1/school-admin/fees/categories",
        ):
            r = await ac.get(path)
            assert r.status_code == 403, f"{path}: expected 403, got {r.status_code}"


@pytest.mark.asyncio
async def test_unknown_subdomain_404_at_middleware(super_admin_token):
    """Unknown tenant subdomains never reach the RBAC layer."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
        headers={"X-Tenant-Subdomain": "nope"},
    ) as ac:
        r = await ac.get("/v1/health")
        assert r.status_code == 404


@pytest.mark.asyncio
async def test_school_admin_cannot_call_super_admin_billing(two_tenants):
    """A school admin token for `demo` must not be able to read
    /admin/billing/* (which is super-admin only)."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
        headers=_headers(two_tenants["demo_token"], "demo"),
    ) as ac:
        r = await ac.get("/admin/billing/invoices")
        assert r.status_code == 403


# =============================================================================
# End-to-end happy path
# =============================================================================


@pytest_asyncio.fixture
async def demo_admin(super_admin_token):
    token = await _login("demo", DEFAULT_SCHOOL_ADMIN_EMAIL, DEFAULT_SCHOOL_ADMIN_PASSWORD)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
        headers=_headers(token, "demo"),
    ) as ac:
        yield ac


@pytest.mark.asyncio
async def test_e2e_admit_attendance_fee_then_parent_view(demo_admin):
    """Walks every Phase 4 → 11 module a typical school touches on day one:

    1. Set up a class + section.
    2. Admit a student (auto-creates the parent + role).
    3. Mark her present today.
    4. Create a fee category + structure, generate the invoice, collect
       half of it in cash.
    5. Log in as the parent and check the dashboard reflects the
       attendance, the half-paid invoice, and the linked child.
    """
    cls = (await demo_admin.post(
        "/v1/school-admin/classes",
        json={"code": "10", "name": "Class 10", "stage": "secondary", "sequence": 10},
    )).json()
    sec = (await demo_admin.post(
        "/v1/school-admin/sections",
        json={"class_def_id": cls["id"], "name": "A"},
    )).json()
    student = (await demo_admin.post(
        "/v1/school-admin/students",
        json={
            "full_name": "Nisha",
            "class_def_id": cls["id"], "section_id": sec["id"],
            "parent_phone": "+919900000300",
            "parent_email": "nisha.parent@h.test",
            "father_name": "Test Parent",
        },
    )).json()

    today = date.today().isoformat()
    await demo_admin.post(
        "/v1/school-admin/attendance/mark",
        json={
            "section_id": sec["id"],
            "date": today,
            "default_status": "present",
        },
    )

    cat = (await demo_admin.post(
        "/v1/school-admin/fees/categories",
        json={"name": "Tuition", "code": "TUI"},
    )).json()
    structure = (await demo_admin.post(
        "/v1/school-admin/fees/structures",
        json={
            "category_id": cat["id"], "class_def_id": cls["id"],
            "amount": 1000, "period": "monthly",
        },
    )).json()
    today_d = date.today()
    period_start = today_d.replace(day=1).isoformat()
    period_end = today_d.isoformat()
    gen = await demo_admin.post(
        f"/v1/school-admin/fees/structures/{structure['id']}/generate",
        json={
            "period_start": period_start, "period_end": period_end,
            "due_date": today,
        },
    )
    assert gen.status_code == 200, gen.text

    fee_view = (await demo_admin.get(
        f"/v1/school-admin/fees/students/{student['id']}"
    )).json()
    assert fee_view["invoices"], "expected at least one invoice"
    invoice_id = fee_view["invoices"][0]["id"]
    invoice_total = float(fee_view["invoices"][0]["total_amount"])

    paid = await demo_admin.post(
        "/v1/school-admin/fees/collect",
        json={
            "invoice_id": invoice_id,
            "amount": invoice_total / 2,
            "method": "cash",
        },
    )
    assert paid.status_code in (200, 201), paid.text

    # Parent flow: reset password to a known value, log in.
    await demo_admin.post(
        "/v1/auth/reset-password",
        json={
            "identifier": "nisha.parent@h.test", "subdomain": "demo",
            "otp": "1234", "new_password": "Parent@123",
        },
    )
    parent_token = await _login("demo", "nisha.parent@h.test", "Parent@123")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
        headers=_headers(parent_token, "demo"),
    ) as parent_ac:
        children = (await parent_ac.get("/v1/parent/children")).json()
        assert any(c["student_id"] == student["id"] for c in children)

        dashboard = (await parent_ac.get(
            f"/v1/parent/dashboard/{student['id']}"
        )).json()
        # Today's roll was 'present' → today_attendance must be set.
        assert dashboard["today_attendance"] in {"present", "late", "half_day"}
        # Half-paid invoice → fee_due_amount is half of total.
        assert float(dashboard["fee_due_amount"]) == pytest.approx(invoice_total / 2, rel=1e-2)

        fees = (await parent_ac.get(
            f"/v1/parent/children/{student['id']}/fees"
        )).json()
        assert any(i["id"] == invoice_id for i in fees["invoices"])
