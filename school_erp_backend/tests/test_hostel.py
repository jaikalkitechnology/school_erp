"""Phase 19 hostel system tests."""

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
async def demo_admin_client(super_admin_token):
    token = await _login("demo", DEFAULT_SCHOOL_ADMIN_EMAIL, DEFAULT_SCHOOL_ADMIN_PASSWORD)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-Subdomain": "demo"},
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def hostel_setup(demo_admin_client):
    h = (await demo_admin_client.post(
        "/v1/school-admin/hostel/hostels",
        json={"code": "BH1", "name": "Boys Hostel 1", "kind": "boys"},
    )).json()
    rooms = []
    for n, cap, fee in [("101", 2, 1500), ("102", 1, 2000)]:
        rooms.append((await demo_admin_client.post(
            f"/v1/school-admin/hostel/hostels/{h['id']}/rooms",
            json={"number": n, "capacity": cap, "monthly_fee": fee},
        )).json())
    return {"hostel": h, "rooms": rooms}


@pytest.mark.asyncio
async def test_hostel_room_setup_and_duplicates(demo_admin_client, hostel_setup):
    f = hostel_setup
    listing = (await demo_admin_client.get(
        f"/v1/school-admin/hostel/hostels/{f['hostel']['id']}/rooms"
    )).json()
    assert len(listing) == 2
    assert all(r["occupied"] == 0 for r in listing)

    dup = await demo_admin_client.post(
        f"/v1/school-admin/hostel/hostels/{f['hostel']['id']}/rooms",
        json={"number": "101", "capacity": 1},
    )
    assert dup.status_code == 409


@pytest.mark.asyncio
async def test_allocation_capacity_and_idempotent(demo_admin_client, hostel_setup):
    f = hostel_setup
    students = []
    for n, p in [("Aakash", "+919900000090"), ("Bhavik", "+919900000091"),
                 ("Chetan", "+919900000092")]:
        students.append((await demo_admin_client.post(
            "/v1/school-admin/students",
            json={"full_name": n, "parent_phone": p, "parent_email": f"{n.lower()}@gmail.com",
                  "father_name": "P"},
        )).json())

    room2cap = f["rooms"][0]  # 101 cap=2
    today = date.today().isoformat()
    a1 = await demo_admin_client.post(
        "/v1/school-admin/hostel/allocations",
        json={"student_id": students[0]["id"], "room_id": room2cap["id"],
              "occupied_from": today},
    )
    assert a1.status_code == 200
    a2 = await demo_admin_client.post(
        "/v1/school-admin/hostel/allocations",
        json={"student_id": students[1]["id"], "room_id": room2cap["id"],
              "occupied_from": today},
    )
    assert a2.status_code == 200

    # Third would exceed capacity.
    a3 = await demo_admin_client.post(
        "/v1/school-admin/hostel/allocations",
        json={"student_id": students[2]["id"], "room_id": room2cap["id"],
              "occupied_from": today},
    )
    assert a3.status_code == 400

    # Re-allocating student[0] to the same room is idempotent (not blocked by capacity).
    again = await demo_admin_client.post(
        "/v1/school-admin/hostel/allocations",
        json={"student_id": students[0]["id"], "room_id": room2cap["id"],
              "occupied_from": today, "monthly_fee": 1800},
    )
    assert again.status_code == 200
    assert float(again.json()["monthly_fee"]) == 1800.0

    detail = (await demo_admin_client.get(
        f"/v1/school-admin/hostel/rooms/{room2cap['id']}"
    )).json()
    assert detail["room"]["occupied"] == 2
    assert len(detail["occupants"]) == 2


@pytest.mark.asyncio
async def test_mess_visitor_disciplinary(demo_admin_client, hostel_setup):
    f = hostel_setup
    student = (await demo_admin_client.post(
        "/v1/school-admin/students",
        json={"full_name": "Dev", "parent_phone": "+919900000093",
              "parent_email": "dev@gmail.com", "father_name": "P"},
    )).json()
    today = date.today().isoformat()

    # Mess upsert.
    await demo_admin_client.put(
        f"/v1/school-admin/hostel/hostels/{f['hostel']['id']}/mess",
        json={"menu_date": today, "meal": "lunch", "items": "Dal, Rice, Paneer"},
    )
    second = await demo_admin_client.put(
        f"/v1/school-admin/hostel/hostels/{f['hostel']['id']}/mess",
        json={"menu_date": today, "meal": "lunch", "items": "Roti, Sabji"},
    )
    assert second.json()["items"] == "Roti, Sabji"

    # Visitor in/out.
    visitor = (await demo_admin_client.post(
        f"/v1/school-admin/hostel/hostels/{f['hostel']['id']}/visitors",
        json={"student_id": student["id"], "visitor_name": "Father",
              "relation": "father"},
    )).json()
    assert visitor["out_at"] is None
    out = await demo_admin_client.post(
        f"/v1/school-admin/hostel/visitors/{visitor['id']}/checkout"
    )
    assert out.status_code == 200
    again = await demo_admin_client.post(
        f"/v1/school-admin/hostel/visitors/{visitor['id']}/checkout"
    )
    assert again.status_code == 400  # already checked out

    # Disciplinary log.
    rec = await demo_admin_client.post(
        f"/v1/school-admin/hostel/hostels/{f['hostel']['id']}/disciplinary",
        json={"student_id": student["id"], "incident_on": today,
              "severity": "warning", "title": "Late return"},
    )
    assert rec.status_code == 201


@pytest.mark.asyncio
async def test_leave_lifecycle_and_parent(demo_admin_client, hostel_setup):
    f = hostel_setup
    student = (await demo_admin_client.post(
        "/v1/school-admin/students",
        json={"full_name": "Esha", "parent_phone": "+919900000094",
              "parent_email": "esha@gmail.com", "father_name": "P"},
    )).json()
    today = date.today()
    await demo_admin_client.post(
        "/v1/school-admin/hostel/allocations",
        json={"student_id": student["id"], "room_id": f["rooms"][1]["id"],
              "occupied_from": today.isoformat()},
    )

    bad = await demo_admin_client.post(
        f"/v1/school-admin/hostel/hostels/{f['hostel']['id']}/leaves",
        json={"student_id": student["id"],
              "from_date": today.isoformat(),
              "to_date": (today - timedelta(days=1)).isoformat(),
              "reason": "Trip"},
    )
    assert bad.status_code == 400

    leave = (await demo_admin_client.post(
        f"/v1/school-admin/hostel/hostels/{f['hostel']['id']}/leaves",
        json={"student_id": student["id"],
              "from_date": today.isoformat(),
              "to_date": (today + timedelta(days=2)).isoformat(),
              "reason": "Family wedding"},
    )).json()
    assert leave["status"] == "pending"

    decided = await demo_admin_client.post(
        f"/v1/school-admin/hostel/leaves/{leave['id']}/decide",
        json={"decision": "approved", "decision_notes": "OK"},
    )
    assert decided.json()["status"] == "approved"

    # Decide again is blocked.
    again = await demo_admin_client.post(
        f"/v1/school-admin/hostel/leaves/{leave['id']}/decide",
        json={"decision": "rejected"},
    )
    assert again.status_code == 400

    returned = await demo_admin_client.post(
        f"/v1/school-admin/hostel/leaves/{leave['id']}/return"
    )
    assert returned.json()["status"] == "returned"

    # Parent view.
    await demo_admin_client.post(
        "/v1/auth/reset-password",
        json={"identifier": "esha@gmail.com", "subdomain": "demo",
              "otp": "1234", "new_password": "Parent@123"},
    )
    parent_token = await _login("demo", "esha@gmail.com", "Parent@123")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
        headers={"Authorization": f"Bearer {parent_token}", "X-Tenant-Subdomain": "demo"},
    ) as parent_ac:
        ok = await parent_ac.get(f"/v1/parent/children/{student['id']}/hostel")
        assert ok.status_code == 200
        body = ok.json()
        assert body["hostel_name"] == "Boys Hostel 1"
        assert body["room_number"] == "102"
        assert any(l["status"] == "returned" for l in body["leaves"])


@pytest.mark.asyncio
async def test_reports_endpoint(demo_admin_client, hostel_setup):
    rep = (await demo_admin_client.get("/v1/school-admin/hostel/reports")).json()
    assert rep["total_hostels"] >= 1
    assert rep["total_capacity"] == 3  # 2 + 1
    assert rep["available_seats"] == 3


@pytest.mark.asyncio
async def test_super_admin_blocked(super_admin_token):
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    ) as ac:
        r = await ac.get("/v1/school-admin/hostel/hostels")
        assert r.status_code == 403


@pytest.mark.asyncio
async def test_edit_and_delete_hostels_and_rooms(demo_admin_client):
    c = demo_admin_client
    h = (await c.post("/v1/school-admin/hostel/hostels", json={"code": "TMP1", "name": "Temp Hostel", "kind": "boys"})).json()
    other = (await c.post("/v1/school-admin/hostel/hostels", json={"code": "TMP2", "name": "Other", "kind": "girls"})).json()

    # Edit hostel; a duplicate code is a clean 409, not a 500.
    r = await c.patch(f"/v1/school-admin/hostel/hostels/{h['id']}",
                      json={"code": "TMP1", "name": "Tagore House", "kind": "girls", "is_active": False})
    assert r.status_code == 200 and r.json()["name"] == "Tagore House" and r.json()["is_active"] is False
    r = await c.patch(f"/v1/school-admin/hostel/hostels/{h['id']}", json={"code": "TMP2", "name": "x", "kind": "boys"})
    assert r.status_code == 409

    # Rooms: edit, capacity floor, delete rules.
    room = (await c.post(f"/v1/school-admin/hostel/hostels/{h['id']}/rooms", json={"number": "101", "capacity": 2})).json()
    spare = (await c.post(f"/v1/school-admin/hostel/hostels/{h['id']}/rooms", json={"number": "102", "capacity": 1})).json()
    r = await c.patch(f"/v1/school-admin/hostel/rooms/{room['id']}",
                      json={"number": "101A", "floor": "1", "capacity": 3, "monthly_fee": 2500, "status": "available"})
    assert r.status_code == 200 and r.json()["number"] == "101A" and r.json()["capacity"] == 3
    r = await c.patch(f"/v1/school-admin/hostel/rooms/{spare['id']}", json={"number": "101A", "capacity": 1})
    assert r.status_code == 409

    for name, phone in (("Hari", "+919900000095"), ("Ravi", "+919900000096")):
        kid = (await c.post("/v1/school-admin/students", json={
            "full_name": name, "parent_phone": phone, "parent_email": f"{name.lower()}@gmail.com",
            "father_name": "P"})).json()
        r = await c.post("/v1/school-admin/hostel/allocations",
                         json={"student_id": kid["id"], "room_id": room["id"], "occupied_from": "2026-06-01"})
        assert r.status_code == 200, r.text
    # Two students live there: capacity can't go below 2.
    r = await c.patch(f"/v1/school-admin/hostel/rooms/{room['id']}", json={"number": "101A", "capacity": 1})
    assert r.status_code == 400 and "below 2" in r.json()["detail"]
    r = await c.delete(f"/v1/school-admin/hostel/rooms/{room['id']}")
    assert r.status_code == 409 and "Move them out" in r.json()["detail"]
    assert (await c.delete(f"/v1/school-admin/hostel/rooms/{spare['id']}")).status_code == 204

    # Hostel with a student stay can't be deleted; an empty one can.
    r = await c.delete(f"/v1/school-admin/hostel/hostels/{h['id']}")
    assert r.status_code == 409 and "inactive" in r.json()["detail"]
    assert (await c.delete(f"/v1/school-admin/hostel/hostels/{other['id']}")).status_code == 204
    names = [x["name"] for x in (await c.get("/v1/school-admin/hostel/hostels")).json()]
    assert "Other" not in names and "Tagore House" in names
