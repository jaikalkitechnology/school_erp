"""Phase 20 reports & analytics tests."""

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
async def small_school(demo_admin_client):
    r_cls = await demo_admin_client.post(
        "/v1/school-admin/classes",
        json={"code": "9", "name": "Class 9", "stage": "secondary", "sequence": 9},
    )
    assert r_cls.status_code in (200, 201), r_cls.text
    cls = r_cls.json()
    sec = (await demo_admin_client.post(
        "/v1/school-admin/sections",
        json={"class_def_id": cls["id"], "name": "A"},
    )).json()
    students = []
    for n, p in [("Aria", "+919900000100"), ("Boman", "+919900000101"),
                 ("Cara", "+919900000102")]:
        students.append((await demo_admin_client.post(
            "/v1/school-admin/students",
            json={
                "full_name": n, "class_def_id": cls["id"], "section_id": sec["id"],
                "parent_phone": p, "parent_email": f"{n.lower()}@a.test",
                "father_name": "P",
            },
        )).json())
    return {"cls": cls, "sec": sec, "students": students}


@pytest.mark.asyncio
async def test_overview_and_class_strength(demo_admin_client, small_school):
    f = small_school
    body = (await demo_admin_client.get("/v1/school-admin/analytics/overview")).json()
    assert body["students"] >= 3
    assert body["classes"] >= 1
    labels = [p["label"] for p in body["by_class_strength"]]
    assert any(name == "Class 9" for name in labels)


@pytest.mark.asyncio
async def test_attendance_trend_with_data(demo_admin_client, small_school):
    f = small_school
    from datetime import date
    today = date.today().isoformat()
    r_mark = await demo_admin_client.post(
        "/v1/school-admin/attendance/mark",
        json={
            "section_id": f["sec"]["id"],
            "date": today,
            "default_status": "present",
            "entries": [
                {"student_id": f["students"][2]["id"], "status": "absent"},
            ],
        },
    )
    assert r_mark.status_code == 200, r_mark.text
    body = (await demo_admin_client.get(
        "/v1/school-admin/analytics/attendance-trend",
        params={"days": 7},
    )).json()
    assert len(body["points"]) == 7
    assert any(p["value"] > 0 for p in body["points"])


@pytest.mark.asyncio
async def test_fees_overview(demo_admin_client, small_school):
    f = small_school
    cat = (await demo_admin_client.post(
        "/v1/school-admin/fees/categories",
        json={"name": "Tuition", "code": "TUI"},
    )).json()
    struct = (await demo_admin_client.post(
        "/v1/school-admin/fees/structures",
        json={
            "category_id": cat["id"], "class_def_id": f["cls"]["id"],
            "amount": 500, "period": "monthly",
        },
    )).json()
    from datetime import date
    today = date.today()
    period_start = today.replace(day=1).isoformat()
    period_end = today.isoformat()
    due = today.isoformat()
    await demo_admin_client.post(
        f"/v1/school-admin/fees/structures/{struct['id']}/generate",
        json={
            "period_start": period_start, "period_end": period_end,
            "due_date": due,
        },
    )
    body = (await demo_admin_client.get("/v1/school-admin/analytics/fees")).json()
    assert float(body["total_billed"]) > 0
    assert float(body["pending"]) > 0


@pytest.mark.asyncio
async def test_library_transport_hostel_summaries(demo_admin_client, small_school):
    lib = (await demo_admin_client.get("/v1/school-admin/analytics/library")).json()
    assert "issued_today" in lib and "overdue" in lib

    tr = (await demo_admin_client.get("/v1/school-admin/analytics/transport")).json()
    assert tr["routes"] == 0

    ho = (await demo_admin_client.get("/v1/school-admin/analytics/hostel")).json()
    assert ho["occupied"] == 0


@pytest.mark.asyncio
async def test_students_report_json_and_csv(demo_admin_client, small_school):
    f = small_school
    rows = (await demo_admin_client.get(
        "/v1/school-admin/analytics/reports/students",
        params={"class_def_id": f["cls"]["id"]},
    )).json()["rows"]
    assert len(rows) == 3

    csv_resp = await demo_admin_client.get(
        "/v1/school-admin/analytics/reports/students.csv",
        params={"class_def_id": f["cls"]["id"]},
    )
    assert csv_resp.status_code == 200
    assert csv_resp.headers["content-type"].startswith("text/csv")
    body = csv_resp.text
    assert body.startswith("student_id,admission_number,")
    assert "Aria" in body and "Boman" in body and "Cara" in body


@pytest.mark.asyncio
async def test_super_admin_blocked(super_admin_token):
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    ) as ac:
        r = await ac.get("/v1/school-admin/analytics/overview")
        assert r.status_code == 403
