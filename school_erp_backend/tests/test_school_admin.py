"""Phase 4 tests: school admin academic CRUD + multi-tenant isolation."""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.seed import (
    DEFAULT_SCHOOL_ADMIN_EMAIL,
    DEFAULT_SCHOOL_ADMIN_PASSWORD,
)


async def _login_school_admin(subdomain: str, email: str, password: str) -> str:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as ac:
        r = await ac.post(
            "/v1/auth/login",
            json={"identifier": email, "password": password, "subdomain": subdomain},
        )
        assert r.status_code == 200, r.text
        return r.json()["tokens"]["access_token"]


@pytest_asyncio.fixture
async def demo_admin_client(super_admin_token):
    """A pre-authenticated client for the demo school's admin."""
    token = await _login_school_admin("demo", DEFAULT_SCHOOL_ADMIN_EMAIL, DEFAULT_SCHOOL_ADMIN_PASSWORD)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Tenant-Subdomain": "demo",
        },
    ) as ac:
        yield ac


@pytest.mark.asyncio
async def test_dashboard_endpoint(demo_admin_client):
    r = await demo_admin_client.get("/v1/school-admin/dashboard")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["subdomain"] == "demo"
    assert body["students_count"] >= 0
    assert body["storage_limit_mb"] > 0


@pytest.mark.asyncio
async def test_settings_get_and_patch(demo_admin_client):
    get = await demo_admin_client.get("/v1/school-admin/settings")
    assert get.status_code == 200
    assert get.json()["primary_color"]

    patch = await demo_admin_client.patch(
        "/v1/school-admin/settings",
        json={"primary_color": "#0F766E", "phone": "+919999999999"},
    )
    assert patch.status_code == 200, patch.text
    assert patch.json()["primary_color"] == "#0F766E"
    assert patch.json()["phone"] == "+919999999999"


@pytest.mark.asyncio
async def test_department_class_section_subject_holiday_crud(demo_admin_client):
    # Department
    dept = await demo_admin_client.post(
        "/v1/school-admin/departments",
        json={"name": "Primary", "code": "PRI"},
    )
    assert dept.status_code == 201, dept.text
    dept_id = dept.json()["id"]

    # Class
    cls = await demo_admin_client.post(
        "/v1/school-admin/classes",
        json={"code": "1", "name": "Class 1", "stage": "primary", "sequence": 1, "department_id": dept_id},
    )
    assert cls.status_code == 201, cls.text
    cls_id = cls.json()["id"]

    # Section
    sec = await demo_admin_client.post(
        "/v1/school-admin/sections",
        json={"class_def_id": cls_id, "name": "A", "capacity": 35},
    )
    assert sec.status_code == 201, sec.text

    # Subject
    sub = await demo_admin_client.post(
        "/v1/school-admin/subjects",
        json={"code": "MATH", "name": "Mathematics", "is_core": True},
    )
    assert sub.status_code == 201, sub.text

    # Academic year (active)
    yr = await demo_admin_client.post(
        "/v1/school-admin/academic-years",
        json={
            "code": "2025-26",
            "name": "Academic Year 2025-26",
            "start_date": "2025-04-01",
            "end_date": "2026-03-31",
            "is_active": True,
        },
    )
    assert yr.status_code == 201, yr.text
    yr_id = yr.json()["id"]
    assert yr.json()["is_active"] is True

    # Term
    term = await demo_admin_client.post(
        f"/v1/school-admin/academic-years/{yr_id}/terms",
        json={"name": "Term 1", "start_date": "2025-04-01", "end_date": "2025-09-30"},
    )
    assert term.status_code == 201, term.text

    # Holiday
    hol = await demo_admin_client.post(
        "/v1/school-admin/holidays",
        json={"date": "2025-08-15", "name": "Independence Day", "kind": "public", "year_id": yr_id},
    )
    assert hol.status_code == 201, hol.text

    # Lists return what we just created
    listing = await demo_admin_client.get("/v1/school-admin/classes")
    assert any(c["id"] == cls_id for c in listing.json())
    sec_list = await demo_admin_client.get(f"/v1/school-admin/sections?class_def_id={cls_id}")
    assert sec_list.status_code == 200
    assert len(sec_list.json()) == 1


@pytest.mark.asyncio
async def test_only_one_active_academic_year(demo_admin_client):
    a = await demo_admin_client.post(
        "/v1/school-admin/academic-years",
        json={
            "code": "year-a",
            "name": "Year A",
            "start_date": "2024-04-01",
            "end_date": "2025-03-31",
            "is_active": True,
        },
    )
    assert a.status_code == 201
    b = await demo_admin_client.post(
        "/v1/school-admin/academic-years",
        json={
            "code": "year-b",
            "name": "Year B",
            "start_date": "2025-04-01",
            "end_date": "2026-03-31",
            "is_active": True,
        },
    )
    assert b.status_code == 201

    listing = await demo_admin_client.get("/v1/school-admin/academic-years")
    actives = [y for y in listing.json() if y["is_active"]]
    assert len(actives) == 1
    assert actives[0]["code"] == "year-b"


@pytest.mark.asyncio
async def test_tenant_isolation_on_school_admin_endpoints(super_admin_token):
    """Spin up a second tenant; its admin must not see the demo tenant's rows."""
    # Bootstrap a second tenant + school admin via the super admin API.
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    ) as super_ac:
        create = await super_ac.post(
            "/admin/tenants",
            json={
                "school_name": "Other School",
                "school_code": "OTHER-001",
                "subdomain": "other",
                "plan_code": "basic",
            },
        )
        assert create.status_code == 201

    # Manually seed RBAC + a school-admin user for the new tenant.
    from app.database import AsyncSessionLocal
    from app.services.seed import _ensure_user, seed_rbac_for_tenant

    async with AsyncSessionLocal() as session:
        await seed_rbac_for_tenant(session, create.json()["id"])
        await _ensure_user(
            session,
            tenant_id=create.json()["id"],
            email="other@school.com",
            full_name="Other Admin",
            password="Other@123",
            role_codes=["school_admin"],
        )

    # Demo admin creates a department.
    demo_token = await _login_school_admin("demo", DEFAULT_SCHOOL_ADMIN_EMAIL, DEFAULT_SCHOOL_ADMIN_PASSWORD)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
        headers={"Authorization": f"Bearer {demo_token}", "X-Tenant-Subdomain": "demo"},
    ) as ac:
        r = await ac.post("/v1/school-admin/departments", json={"name": "DemoDept"})
        assert r.status_code == 201

    # Other admin must NOT see DemoDept.
    other_token = await _login_school_admin("other", "other@school.com", "Other@123")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
        headers={"Authorization": f"Bearer {other_token}", "X-Tenant-Subdomain": "other"},
    ) as ac:
        listing = await ac.get("/v1/school-admin/departments")
        assert listing.status_code == 200
        assert all(d["name"] != "DemoDept" for d in listing.json())


@pytest.mark.asyncio
async def test_super_admin_cannot_call_school_admin_endpoints(auth_client):
    """Super admin lacks the school staff roles, so 403."""
    r = await auth_client.get("/v1/school-admin/dashboard")
    assert r.status_code == 403
