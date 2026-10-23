"""Mobile work tabs: accountant fees, librarian desk, hostel warden."""

from datetime import date, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import update

from app.main import app
from app.services.seed import DEFAULT_SCHOOL_ADMIN_EMAIL, DEFAULT_SCHOOL_ADMIN_PASSWORD


async def _client_for(email: str, password: str) -> AsyncClient:
    ac = AsyncClient(
        transport=ASGITransport(app=app), base_url="http://localhost", headers={"X-Tenant-Subdomain": "demo"}
    )
    r = await ac.post("/v1/auth/login", json={"identifier": email, "password": password, "subdomain": "demo"})
    assert r.status_code == 200, r.text
    ac.headers["Authorization"] = f"Bearer {r.json()['tokens']['access_token']}"
    return ac


async def _staff(admin: AsyncClient, role: str) -> AsyncClient:
    email = f"{role}.work@demo.school"
    r = await admin.post(
        "/v1/school-admin/users",
        json={"full_name": f"Demo {role}", "email": email, "password": "Staff@123", "role_codes": [role]},
    )
    assert r.status_code == 201, r.text
    return await _client_for(email, "Staff@123")


async def _student(admin: AsyncClient, name: str, phone: str) -> dict:
    r = await admin.post(
        "/v1/school-admin/students",
        json={"full_name": name, "parent_phone": phone, "parent_email": f"{name.lower()}@gmail.com",
              "father_name": "Parent"},
    )
    assert r.status_code == 201, r.text
    return r.json()


@pytest.mark.asyncio
async def test_librarian_desk_overdue_and_return_by_barcode(super_admin_token):
    from app.database import AsyncSessionLocal
    from app.models.library import Loan

    admin = await _client_for(DEFAULT_SCHOOL_ADMIN_EMAIL, DEFAULT_SCHOOL_ADMIN_PASSWORD)
    lib = await _staff(admin, "librarian")
    try:
        book = (await admin.post(
            "/v1/school-admin/library/books",
            json={"title": "Wings of Fire", "author": "A. P. J. Abdul Kalam", "default_loan_days": 7},
        )).json()
        copy = (await admin.post(f"/v1/school-admin/library/books/{book['id']}/copies/bulk", json={"count": 1})).json()[0]
        kid = await _student(admin, "Farah", "+919900000160")
        loan = (await lib.post(
            "/v1/school-admin/library/issue",
            json={"copy_id": copy["id"], "borrower_kind": "student", "borrower_id": kid["id"]},
        )).json()
        # Make it 3 days overdue.
        async with AsyncSessionLocal() as s:
            await s.execute(update(Loan).where(Loan.id == loan["id"]).values(due_on=date.today() - timedelta(days=3)))
            await s.commit()

        day = (await lib.get("/v1/staff/library/today")).json()
        assert day["issued_today"] >= 1 and day["on_loan"] >= 1
        late = next(o for o in day["overdue"] if o["loan_id"] == loan["id"])
        assert late["title"] == "Wings of Fire" and late["days_overdue"] == 3
        assert late["borrower"].startswith("Farah") and late["barcode"] == copy["barcode"]

        assert (await lib.post("/v1/staff/library/return-by-barcode", json={"barcode": "NOPE-1"})).status_code == 404
        r = await lib.post("/v1/staff/library/return-by-barcode", json={"barcode": copy["barcode"]})
        assert r.status_code == 200, r.text
        assert r.json()["title"] == "Wings of Fire"
        day = (await lib.get("/v1/staff/library/today")).json()
        assert loan["id"] not in [o["loan_id"] for o in day["overdue"]]
        assert day["returned_today"] >= 1
    finally:
        await admin.aclose()
        await lib.aclose()


@pytest.mark.asyncio
async def test_warden_sees_pending_leave_and_visitors(super_admin_token):
    admin = await _client_for(DEFAULT_SCHOOL_ADMIN_EMAIL, DEFAULT_SCHOOL_ADMIN_PASSWORD)
    warden = await _staff(admin, "hostel_warden")
    try:
        h = (await admin.post("/v1/school-admin/hostel/hostels", json={"code": "GH1", "name": "Girls Hostel", "kind": "girls"})).json()
        room = (await admin.post(f"/v1/school-admin/hostel/hostels/{h['id']}/rooms", json={"number": "1", "capacity": 2})).json()
        kid = await _student(admin, "Esha", "+919900000161")
        today = date.today()
        await admin.post("/v1/school-admin/hostel/allocations",
                         json={"student_id": kid["id"], "room_id": room["id"], "occupied_from": today.isoformat()})
        leave = (await admin.post(
            f"/v1/school-admin/hostel/hostels/{h['id']}/leaves",
            json={"student_id": kid["id"], "from_date": today.isoformat(),
                  "to_date": (today + timedelta(days=2)).isoformat(), "reason": "Family wedding"},
        )).json()
        await admin.post(f"/v1/school-admin/hostel/hostels/{h['id']}/visitors",
                         json={"student_id": kid["id"], "visitor_name": "Mother", "relation": "mother"})

        day = (await warden.get("/v1/staff/hostel/today")).json()
        assert day["occupied"] >= 1
        pending = next(l for l in day["pending_leaves"] if l["id"] == leave["id"])
        assert pending["student_name"] == "Esha" and pending["reason"] == "Family wedding"
        assert any(v["visitor_name"] == "Mother" and v["student_name"] == "Esha" for v in day["visitors_in"])

        # Approve with the existing route; it moves to "away on leave".
        r = await warden.post(f"/v1/school-admin/hostel/leaves/{leave['id']}/decide", json={"decision": "approved"})
        assert r.status_code == 200, r.text
        day = (await warden.get("/v1/staff/hostel/today")).json()
        assert leave["id"] not in [l["id"] for l in day["pending_leaves"]]
        assert day["away_on_leave"] >= 1
    finally:
        await admin.aclose()
        await warden.aclose()


@pytest.mark.asyncio
async def test_accountant_fees_today_and_role_checks(super_admin_token):
    admin = await _client_for(DEFAULT_SCHOOL_ADMIN_EMAIL, DEFAULT_SCHOOL_ADMIN_PASSWORD)
    acc = await _staff(admin, "accountant")
    try:
        r = await acc.get("/v1/staff/fees/today")
        assert r.status_code == 200, r.text
        assert {"collected_today", "collected_month", "pending", "overdue", "defaulters"} <= set(r.json())
        # Each tab is for its own role.
        assert (await acc.get("/v1/staff/library/today")).status_code == 403
        assert (await acc.get("/v1/staff/hostel/today")).status_code == 403
    finally:
        await admin.aclose()
        await acc.aclose()
