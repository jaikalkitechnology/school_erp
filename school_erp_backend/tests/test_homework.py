"""Phase 14 homework tests."""

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
async def section_with_two_students(demo_admin_client):
    cls = (await demo_admin_client.post(
        "/v1/school-admin/classes",
        json={"code": "5", "name": "Class 5", "stage": "primary", "sequence": 5},
    )).json()
    sec = (await demo_admin_client.post(
        "/v1/school-admin/sections",
        json={"class_def_id": cls["id"], "name": "A"},
    )).json()
    math = (await demo_admin_client.post(
        "/v1/school-admin/subjects",
        json={"code": "MATH", "name": "Mathematics"},
    )).json()
    a = (await demo_admin_client.post(
        "/v1/school-admin/students",
        json={
            "full_name": "Aarav",
            "class_def_id": cls["id"], "section_id": sec["id"],
            "parent_phone": "+919900000030", "parent_email": "ravi@home.test",
            "father_name": "Ravi",
        },
    )).json()
    b = (await demo_admin_client.post(
        "/v1/school-admin/students",
        json={
            "full_name": "Aanya",
            "class_def_id": cls["id"], "section_id": sec["id"],
            "parent_phone": "+919900000030", "parent_email": "ravi@home.test",
            "father_name": "Ravi",
        },
    )).json()
    rp = await demo_admin_client.post(
        "/v1/auth/reset-password",
        json={"identifier": "ravi@home.test", "subdomain": "demo", "otp": "1234", "new_password": "Parent@123"},
    )
    assert rp.status_code == 204
    return cls, sec, math, a, b


@pytest.mark.asyncio
async def test_teacher_create_and_list(demo_admin_client, section_with_two_students):
    _, sec, math, _, _ = section_with_two_students
    today = date.today()
    r = await demo_admin_client.post(
        "/v1/school-admin/homework",
        json={
            "section_id": sec["id"],
            "subject_id": math["id"],
            "title": "Long division",
            "description": "Pages 12-14",
            "due_date": (today + timedelta(days=3)).isoformat(),
            "max_marks": 10,
        },
    )
    assert r.status_code == 201, r.text
    hw_id = r.json()["id"]

    listing = await demo_admin_client.get(
        "/v1/school-admin/homework", params={"section_id": sec["id"]}
    )
    assert any(h["id"] == hw_id for h in listing.json())

    bad = await demo_admin_client.post(
        "/v1/school-admin/homework",
        json={
            "section_id": sec["id"],
            "title": "Bad",
            "due_date": (today - timedelta(days=2)).isoformat(),
        },
    )
    # default assigned_on is today; due_date in past triggers 400.
    assert bad.status_code == 400


@pytest.mark.asyncio
async def test_parent_submit_and_teacher_grade(demo_admin_client, section_with_two_students):
    _, sec, math, a, _ = section_with_two_students
    today = date.today()
    hw = (await demo_admin_client.post(
        "/v1/school-admin/homework",
        json={
            "section_id": sec["id"],
            "subject_id": math["id"],
            "title": "Worksheet",
            "due_date": (today + timedelta(days=2)).isoformat(),
            "max_marks": 20,
        },
    )).json()

    parent_token = await _login("demo", "ravi@home.test", "Parent@123")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
        headers={"Authorization": f"Bearer {parent_token}", "X-Tenant-Subdomain": "demo"},
    ) as parent_ac:
        sub = await parent_ac.post(
            f"/v1/parent/children/{a['id']}/homework/submit",
            json={"homework_id": hw["id"], "content": "Done"},
        )
        assert sub.status_code == 201, sub.text
        submission_id = sub.json()["id"]
        assert sub.json()["status"] == "submitted"

    # Teacher grades.
    grade = await demo_admin_client.post(
        f"/v1/school-admin/homework/submissions/{submission_id}/grade",
        json={"marks": 18, "feedback": "Nicely done"},
    )
    assert grade.status_code == 200
    assert grade.json()["status"] == "graded"
    assert float(grade.json()["marks"]) == 18.0

    # Over-mark rejected.
    over = await demo_admin_client.post(
        f"/v1/school-admin/homework/submissions/{submission_id}/grade",
        json={"marks": 25},
    )
    assert over.status_code == 400


@pytest.mark.asyncio
async def test_late_submission_flagged(demo_admin_client, section_with_two_students):
    _, sec, _, a, _ = section_with_two_students
    yesterday = date.today() - timedelta(days=1)

    # Backdate the due date by inserting via SQL: the API rejects past due_date,
    # so post one for today, then PATCH the due_date.
    hw = (await demo_admin_client.post(
        "/v1/school-admin/homework",
        json={
            "section_id": sec["id"],
            "title": "Old worksheet",
            "due_date": date.today().isoformat(),
            "max_marks": 5,
        },
    )).json()
    upd = await demo_admin_client.patch(
        f"/v1/school-admin/homework/{hw['id']}",
        json={"due_date": yesterday.isoformat()},
    )
    assert upd.status_code == 200

    parent_token = await _login("demo", "ravi@home.test", "Parent@123")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
        headers={"Authorization": f"Bearer {parent_token}", "X-Tenant-Subdomain": "demo"},
    ) as parent_ac:
        sub = await parent_ac.post(
            f"/v1/parent/children/{a['id']}/homework/submit",
            json={"homework_id": hw["id"], "content": "Late"},
        )
        assert sub.status_code == 201
        assert sub.json()["status"] == "late"


@pytest.mark.asyncio
async def test_status_report_counts_submitted(demo_admin_client, section_with_two_students):
    _, sec, _, a, b = section_with_two_students
    hw = (await demo_admin_client.post(
        "/v1/school-admin/homework",
        json={
            "section_id": sec["id"],
            "title": "Reading",
            "due_date": (date.today() + timedelta(days=5)).isoformat(),
            "max_marks": 10,
        },
    )).json()

    # Aarav submits, Aanya doesn't.
    parent_token = await _login("demo", "ravi@home.test", "Parent@123")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
        headers={"Authorization": f"Bearer {parent_token}", "X-Tenant-Subdomain": "demo"},
    ) as parent_ac:
        await parent_ac.post(
            f"/v1/parent/children/{a['id']}/homework/submit",
            json={"homework_id": hw["id"], "content": "x"},
        )

    rep = await demo_admin_client.get(f"/v1/school-admin/homework/{hw['id']}/report")
    assert rep.status_code == 200
    body = rep.json()
    assert body["submitted_count"] == 1
    assert body["total_students"] == 2


@pytest.mark.asyncio
async def test_dashboard_includes_pending_homework(demo_admin_client, section_with_two_students):
    _, sec, _, a, _ = section_with_two_students
    today = date.today()
    # Two homework pending for the section.
    await demo_admin_client.post(
        "/v1/school-admin/homework",
        json={"section_id": sec["id"], "title": "HW1", "due_date": (today + timedelta(days=2)).isoformat(), "max_marks": 10},
    )
    await demo_admin_client.post(
        "/v1/school-admin/homework",
        json={"section_id": sec["id"], "title": "HW2", "due_date": (today + timedelta(days=3)).isoformat(), "max_marks": 10},
    )

    parent_token = await _login("demo", "ravi@home.test", "Parent@123")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
        headers={"Authorization": f"Bearer {parent_token}", "X-Tenant-Subdomain": "demo"},
    ) as parent_ac:
        dash = await parent_ac.get(f"/v1/parent/dashboard/{a['id']}")
        assert dash.status_code == 200
        assert dash.json()["pending_homework"] == 2


@pytest.mark.asyncio
async def test_parent_cannot_view_other_kids_homework(demo_admin_client, section_with_two_students):
    cls = (await demo_admin_client.post(
        "/v1/school-admin/classes",
        json={"code": "6", "name": "Class 6", "stage": "middle", "sequence": 6},
    )).json()
    other = (await demo_admin_client.post(
        "/v1/school-admin/students",
        json={"full_name": "Other", "class_def_id": cls["id"], "parent_phone": "+919900099000"},
    )).json()
    parent_token = await _login("demo", "ravi@home.test", "Parent@123")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
        headers={"Authorization": f"Bearer {parent_token}", "X-Tenant-Subdomain": "demo"},
    ) as parent_ac:
        forbidden = await parent_ac.get(f"/v1/parent/children/{other['id']}/homework")
        assert forbidden.status_code == 403


@pytest.mark.asyncio
async def test_grading_rejects_after_done(demo_admin_client, section_with_two_students):
    _, sec, _, a, _ = section_with_two_students
    hw = (await demo_admin_client.post(
        "/v1/school-admin/homework",
        json={"section_id": sec["id"], "title": "X", "due_date": (date.today() + timedelta(days=2)).isoformat(), "max_marks": 5},
    )).json()
    parent_token = await _login("demo", "ravi@home.test", "Parent@123")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
        headers={"Authorization": f"Bearer {parent_token}", "X-Tenant-Subdomain": "demo"},
    ) as parent_ac:
        sub = await parent_ac.post(
            f"/v1/parent/children/{a['id']}/homework/submit",
            json={"homework_id": hw["id"], "content": "v1"},
        )
    submission_id = sub.json()["id"]
    await demo_admin_client.post(
        f"/v1/school-admin/homework/submissions/{submission_id}/grade",
        json={"marks": 4},
    )
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
        headers={"Authorization": f"Bearer {parent_token}", "X-Tenant-Subdomain": "demo"},
    ) as parent_ac:
        retry = await parent_ac.post(
            f"/v1/parent/children/{a['id']}/homework/submit",
            json={"homework_id": hw["id"], "content": "v2"},
        )
        assert retry.status_code == 409
