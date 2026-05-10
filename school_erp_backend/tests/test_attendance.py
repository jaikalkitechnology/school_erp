"""Phase 9 attendance tests."""

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


async def _setup_class_with_two_students(client) -> tuple[dict, dict, dict, dict]:
    cls = (await client.post(
        "/v1/school-admin/classes",
        json={"code": "5", "name": "Class 5", "stage": "primary", "sequence": 5},
    )).json()
    sec = (await client.post(
        "/v1/school-admin/sections",
        json={"class_def_id": cls["id"], "name": "A"},
    )).json()
    a = (await client.post(
        "/v1/school-admin/students",
        json={"full_name": "Aarav", "class_def_id": cls["id"], "section_id": sec["id"], "parent_phone": "+919900000001"},
    )).json()
    b = (await client.post(
        "/v1/school-admin/students",
        json={"full_name": "Riya", "class_def_id": cls["id"], "section_id": sec["id"], "parent_phone": "+919900000002"},
    )).json()
    return cls, sec, a, b


@pytest.mark.asyncio
async def test_default_roll_treats_unmarked_as_present_only_after_save(demo_admin_client):
    _, sec, a, b = await _setup_class_with_two_students(demo_admin_client)
    roll = await demo_admin_client.get(
        f"/v1/school-admin/attendance/section/{sec['id']}",
        params={"date": "2025-08-01"},
    )
    assert roll.status_code == 200
    body = roll.json()
    # Nothing saved yet -> counts['unmarked'] is the entire roster.
    assert body["counts"]["unmarked"] == 2
    assert body["counts"]["present"] == 0


@pytest.mark.asyncio
async def test_mark_section_attendance_with_per_student_overrides(demo_admin_client):
    _, sec, a, b = await _setup_class_with_two_students(demo_admin_client)
    r = await demo_admin_client.post(
        "/v1/school-admin/attendance/mark",
        json={
            "section_id": sec["id"],
            "date": "2025-08-01",
            "default_status": "present",
            "entries": [
                {"student_id": a["id"], "status": "absent", "remarks": "Fever"},
            ],
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    statuses = {s["student_id"]: s["status"] for s in body["students"]}
    assert statuses[a["id"]] == "absent"
    assert statuses[b["id"]] == "present"
    assert body["counts"]["present"] == 1
    assert body["counts"]["absent"] == 1


@pytest.mark.asyncio
async def test_mark_idempotent_updates(demo_admin_client):
    _, sec, a, _ = await _setup_class_with_two_students(demo_admin_client)
    payload = {
        "section_id": sec["id"], "date": "2025-08-01",
        "entries": [{"student_id": a["id"], "status": "absent"}],
        "default_status": "present",
    }
    await demo_admin_client.post("/v1/school-admin/attendance/mark", json=payload)
    payload["entries"] = [{"student_id": a["id"], "status": "late", "remarks": "Bus delay"}]
    r = await demo_admin_client.post("/v1/school-admin/attendance/mark", json=payload)
    body = r.json()
    statuses = {s["student_id"]: s["status"] for s in body["students"]}
    assert statuses[a["id"]] == "late"


@pytest.mark.asyncio
async def test_invalid_student_in_section_400(demo_admin_client):
    _, sec, a, _ = await _setup_class_with_two_students(demo_admin_client)
    r = await demo_admin_client.post(
        "/v1/school-admin/attendance/mark",
        json={
            "section_id": sec["id"], "date": "2025-08-01",
            "entries": [{"student_id": 99999, "status": "absent"}],
        },
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_monthly_report_attendance_pct(demo_admin_client):
    _, sec, a, b = await _setup_class_with_two_students(demo_admin_client)
    # Two days: 2025-08-01 a=present b=absent; 2025-08-02 both present.
    await demo_admin_client.post("/v1/school-admin/attendance/mark", json={
        "section_id": sec["id"], "date": "2025-08-01", "default_status": "present",
        "entries": [{"student_id": b["id"], "status": "absent"}],
    })
    await demo_admin_client.post("/v1/school-admin/attendance/mark", json={
        "section_id": sec["id"], "date": "2025-08-02", "default_status": "present",
        "entries": [],
    })
    r = await demo_admin_client.get(
        f"/v1/school-admin/attendance/section/{sec['id']}/monthly",
        params={"year": 2025, "month": 8},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["working_days"] == 2
    by_id = {s["student_id"]: s for s in body["students"]}
    assert by_id[a["id"]]["attendance_pct"] == 100.0
    assert by_id[b["id"]]["attendance_pct"] == 50.0


@pytest.mark.asyncio
async def test_defaulter_list_picks_low_attendance(demo_admin_client):
    _, sec, a, b = await _setup_class_with_two_students(demo_admin_client)
    # b absent twice in a row.
    for d in ("2025-08-01", "2025-08-02"):
        await demo_admin_client.post("/v1/school-admin/attendance/mark", json={
            "section_id": sec["id"], "date": d, "default_status": "present",
            "entries": [{"student_id": b["id"], "status": "absent"}],
        })
    r = await demo_admin_client.get(
        "/v1/school-admin/attendance/defaulters",
        params={"threshold_pct": 75, "section_id": sec["id"], "start": "2025-08-01", "end": "2025-08-31"},
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["student_id"] == b["id"]
    assert body[0]["attendance_pct"] < 75


@pytest.mark.asyncio
async def test_student_history_returns_recent_marks(demo_admin_client):
    _, sec, a, _ = await _setup_class_with_two_students(demo_admin_client)
    await demo_admin_client.post("/v1/school-admin/attendance/mark", json={
        "section_id": sec["id"], "date": "2025-08-01", "default_status": "present",
        "entries": [{"student_id": a["id"], "status": "late", "remarks": "Bus"}],
    })
    r = await demo_admin_client.get(
        f"/v1/school-admin/attendance/student/{a['id']}",
        params={"start": "2025-08-01", "end": "2025-08-31"},
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["status"] == "late"
    assert body[0]["remarks"] == "Bus"


@pytest.mark.asyncio
async def test_parent_can_see_only_linked_attendance(demo_admin_client):
    _, sec, a, _ = await _setup_class_with_two_students(demo_admin_client)
    cls2 = (await demo_admin_client.post(
        "/v1/school-admin/classes",
        json={"code": "6", "name": "Class 6", "stage": "middle", "sequence": 6},
    )).json()
    other = (await demo_admin_client.post(
        "/v1/school-admin/students",
        json={"full_name": "Other", "class_def_id": cls2["id"], "parent_phone": "+919999999998"},
    )).json()

    # Mark some attendance for `a`.
    await demo_admin_client.post("/v1/school-admin/attendance/mark", json={
        "section_id": sec["id"], "date": "2025-08-01", "default_status": "present",
    })

    # Reset password for `a`'s parent (auto-created via parent_phone).
    await demo_admin_client.post(
        "/v1/auth/reset-password",
        json={
            "identifier": "+919900000001", "subdomain": "demo",
            "otp": "1234", "new_password": "Parent@123",
        },
    )

    parent_token = await _login("demo", "+919900000001", "Parent@123")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
        headers={"Authorization": f"Bearer {parent_token}", "X-Tenant-Subdomain": "demo"},
    ) as ac:
        # Allowed: own child.
        ok = await ac.get(f"/v1/parent/children/{a['id']}/attendance")
        assert ok.status_code == 200
        assert isinstance(ok.json(), list)
        # Forbidden: not linked.
        bad = await ac.get(f"/v1/parent/children/{other['id']}/attendance")
        assert bad.status_code == 403
