"""Non-teaching staff (accountant, librarian, bus staff, ...) self-service."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.seed import (
    DEFAULT_PARENT_PASSWORD,
    DEFAULT_SCHOOL_ADMIN_EMAIL,
    DEFAULT_SCHOOL_ADMIN_PASSWORD,
    DEMO_PARENT_EMAIL,
)


async def _client_for(email: str, password: str) -> AsyncClient:
    ac = AsyncClient(
        transport=ASGITransport(app=app), base_url="http://localhost", headers={"X-Tenant-Subdomain": "demo"}
    )
    r = await ac.post("/v1/auth/login", json={"identifier": email, "password": password, "subdomain": "demo"})
    assert r.status_code == 200, r.text
    ac.headers["Authorization"] = f"Bearer {r.json()['tokens']['access_token']}"
    return ac


async def _make_user(admin: AsyncClient, email: str, role: str) -> None:
    r = await admin.post(
        "/v1/school-admin/users",
        json={"full_name": f"Demo {role}", "email": email, "password": "Staff@123", "role_codes": [role]},
    )
    assert r.status_code == 201, r.text


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["accountant", "librarian", "hostel_warden", "bus_staff", "receptionist"])
async def test_staff_self_service(super_admin_token, role):
    admin = await _client_for(DEFAULT_SCHOOL_ADMIN_EMAIL, DEFAULT_SCHOOL_ADMIN_PASSWORD)
    email = f"{role}.self@demo.school"
    await _make_user(admin, email, role)
    staff = await _client_for(email, "Staff@123")
    try:
        assert (await staff.get("/v1/staff/holidays")).status_code == 200
        assert (await staff.get("/v1/staff/events")).status_code == 200
        r = await staff.post(
            "/v1/staff/my-leaves",
            json={"start_date": "2026-11-02", "end_date": "2026-11-03", "reason": f"Family function ({role})", "kind": "casual"},
        )
        assert r.status_code == 201, r.text
        # (The test DB keeps staff_leaves between tests, so match on this one.)
        mine = (await staff.get("/v1/staff/my-leaves")).json()
        assert f"Family function ({role})" in [l["reason"] for l in mine]
        assert (await staff.get("/v1/mobile/teacher/me/payslips")).status_code == 200
        # Staff notices / announcements reach them too.
        assert (await staff.get("/v1/mobile/notices")).status_code == 200
    finally:
        await admin.aclose()
        await staff.aclose()


@pytest.mark.asyncio
async def test_parent_cannot_use_staff_api(super_admin_token):
    parent = await _client_for(DEMO_PARENT_EMAIL, DEFAULT_PARENT_PASSWORD)
    try:
        assert (await parent.get("/v1/staff/my-leaves")).status_code == 403
    finally:
        await parent.aclose()


@pytest.mark.asyncio
async def test_bus_staff_can_drive(super_admin_token):
    admin = await _client_for(DEFAULT_SCHOOL_ADMIN_EMAIL, DEFAULT_SCHOOL_ADMIN_PASSWORD)
    await _make_user(admin, "driver.bus@demo.school", "bus_staff")
    bus = await _client_for("driver.bus@demo.school", "Staff@123")
    try:
        # Offered as a driver account on the admin Fleet form…
        cands = (await admin.get("/v1/school-admin/transport/drivers/candidates")).json()
        assert "driver.bus@demo.school" in [c.get("email") for c in cands], cands
        # …and allowed into the driver screens' data.
        assert (await bus.get("/v1/school-admin/transport/driver/routes")).status_code == 200
    finally:
        await admin.aclose()
        await bus.aclose()
