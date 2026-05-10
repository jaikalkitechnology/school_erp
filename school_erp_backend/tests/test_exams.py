"""Phase 15 examination system tests."""

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
async def section_with_exam(demo_admin_client):
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
    eng = (await demo_admin_client.post(
        "/v1/school-admin/subjects",
        json={"code": "ENG", "name": "English"},
    )).json()
    students = []
    for name, phone in [
        ("Aarav", "+919900000040"),
        ("Bina", "+919900000041"),
        ("Chitra", "+919900000042"),
    ]:
        s = (await demo_admin_client.post(
            "/v1/school-admin/students",
            json={
                "full_name": name,
                "class_def_id": cls["id"], "section_id": sec["id"],
                "parent_phone": phone, "parent_email": f"{name.lower()}@home.test",
                "father_name": "Test Parent",
            },
        )).json()
        students.append(s)
    exam = (await demo_admin_client.post(
        "/v1/school-admin/exams",
        json={"name": "Unit Test 1", "kind": "unit_test", "default_max_marks": 50},
    )).json()
    es_math = (await demo_admin_client.post(
        f"/v1/school-admin/exams/{exam['id']}/subjects",
        json={
            "class_def_id": cls["id"], "subject_id": math["id"],
            "max_marks": 50, "passing_marks": 18,
        },
    )).json()
    es_eng = (await demo_admin_client.post(
        f"/v1/school-admin/exams/{exam['id']}/subjects",
        json={
            "class_def_id": cls["id"], "subject_id": eng["id"],
            "max_marks": 50, "passing_marks": 18,
        },
    )).json()
    return {
        "cls": cls, "sec": sec, "math": math, "eng": eng,
        "students": students, "exam": exam, "es_math": es_math, "es_eng": es_eng,
    }


@pytest.mark.asyncio
async def test_exam_and_subject_setup(demo_admin_client, section_with_exam):
    f = section_with_exam
    listing = await demo_admin_client.get("/v1/school-admin/exams")
    assert any(e["id"] == f["exam"]["id"] for e in listing.json())

    subjects = await demo_admin_client.get(f"/v1/school-admin/exams/{f['exam']['id']}/subjects")
    assert len(subjects.json()) == 2

    # Reject passing > max.
    bad = await demo_admin_client.post(
        f"/v1/school-admin/exams/{f['exam']['id']}/subjects",
        json={
            "class_def_id": f["cls"]["id"], "subject_id": f["math"]["id"],
            "max_marks": 50, "passing_marks": 60,
        },
    )
    # Even though duplicate would also fire, validation comes first.
    assert bad.status_code == 400


@pytest.mark.asyncio
async def test_marks_entry_valid_and_overflow(demo_admin_client, section_with_exam):
    f = section_with_exam
    students = f["students"]
    es_math = f["es_math"]
    bad = await demo_admin_client.post(
        "/v1/school-admin/exams/marks/bulk",
        json={
            "exam_subject_id": es_math["id"],
            "entries": [
                {"student_id": students[0]["id"], "obtained_marks": 60},
            ],
        },
    )
    assert bad.status_code == 400  # over max

    ok = await demo_admin_client.post(
        "/v1/school-admin/exams/marks/bulk",
        json={
            "exam_subject_id": es_math["id"],
            "entries": [
                {"student_id": students[0]["id"], "obtained_marks": 45},
                {"student_id": students[1]["id"], "obtained_marks": 15},  # < passing
                {"student_id": students[2]["id"], "obtained_marks": None,
                 "status": "absent"},
            ],
        },
    )
    assert ok.status_code == 200
    assert ok.json()["written"] == 3


@pytest.mark.asyncio
async def test_grade_scale_and_results_with_rank(demo_admin_client, section_with_exam):
    f = section_with_exam
    # Set up a default grade scale.
    await demo_admin_client.put(
        "/v1/school-admin/grade-scales",
        json={
            "code": "default",
            "name": "Default scale",
            "is_default": True,
            "bands": [
                {"min_pct": 90, "grade": "A+"},
                {"min_pct": 75, "grade": "A"},
                {"min_pct": 50, "grade": "B"},
                {"min_pct": 33, "grade": "C"},
                {"min_pct": 0, "grade": "F"},
            ],
        },
    )

    students = f["students"]
    es_math, es_eng = f["es_math"], f["es_eng"]
    # Aarav: 45+45=90/100 (A+)
    # Bina:  20+20=40/100 (C)
    # Chitra: absent in math, 30 in eng
    await demo_admin_client.post(
        "/v1/school-admin/exams/marks/bulk",
        json={
            "exam_subject_id": es_math["id"],
            "entries": [
                {"student_id": students[0]["id"], "obtained_marks": 45},
                {"student_id": students[1]["id"], "obtained_marks": 20},
                {"student_id": students[2]["id"], "status": "absent"},
            ],
        },
    )
    await demo_admin_client.post(
        "/v1/school-admin/exams/marks/bulk",
        json={
            "exam_subject_id": es_eng["id"],
            "entries": [
                {"student_id": students[0]["id"], "obtained_marks": 45},
                {"student_id": students[1]["id"], "obtained_marks": 20},
                {"student_id": students[2]["id"], "obtained_marks": 30},
            ],
        },
    )

    r = await demo_admin_client.get(
        f"/v1/school-admin/exams/{f['exam']['id']}/results",
        params={"section_id": f["sec"]["id"]},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    by_id = {row["student_id"]: row for row in body["students"]}
    aarav = by_id[students[0]["id"]]
    bina = by_id[students[1]["id"]]
    chitra = by_id[students[2]["id"]]

    assert aarav["percentage"] == 90.0
    assert aarav["overall_grade"] == "A+"
    assert aarav["overall_status"] == "pass"
    assert aarav["rank_in_section"] == 1

    assert bina["percentage"] == 40.0
    # Bina got 20 in math (passing 18) + 20 in eng (passing 18) = both pass
    # but overall grade for 40% is C.
    assert bina["overall_grade"] == "C"
    assert bina["overall_status"] == "pass"
    assert bina["rank_in_section"] == 2

    assert chitra["overall_status"] == "absent"
    assert chitra["rank_in_section"] == 3
    assert body["section_average_pct"] > 0


@pytest.mark.asyncio
async def test_publish_and_parent_results_scope(demo_admin_client, section_with_exam):
    f = section_with_exam
    students = f["students"]
    await demo_admin_client.post(
        "/v1/school-admin/exams/marks/bulk",
        json={
            "exam_subject_id": f["es_math"]["id"],
            "entries": [{"student_id": students[0]["id"], "obtained_marks": 40}],
        },
    )
    await demo_admin_client.post(
        "/v1/school-admin/exams/marks/bulk",
        json={
            "exam_subject_id": f["es_eng"]["id"],
            "entries": [{"student_id": students[0]["id"], "obtained_marks": 40}],
        },
    )
    pub = await demo_admin_client.post(
        f"/v1/school-admin/exams/{f['exam']['id']}/publish"
    )
    assert pub.json()["status"] == "published"

    # Parent of Aarav can see results.
    await demo_admin_client.post(
        "/v1/auth/reset-password",
        json={"identifier": "aarav@home.test", "subdomain": "demo", "otp": "1234", "new_password": "Parent@123"},
    )
    parent_token = await _login("demo", "aarav@home.test", "Parent@123")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
        headers={"Authorization": f"Bearer {parent_token}", "X-Tenant-Subdomain": "demo"},
    ) as parent_ac:
        ok = await parent_ac.get(f"/v1/parent/children/{students[0]['id']}/exam-results")
        assert ok.status_code == 200
        rows = ok.json()["rows"]
        assert any(r["exam_id"] == f["exam"]["id"] and r["published"] for r in rows)

        # Forbidden on another kid.
        bad = await parent_ac.get(f"/v1/parent/children/{students[1]['id']}/exam-results")
        assert bad.status_code == 403


@pytest.mark.asyncio
async def test_marks_invalid_student_400(demo_admin_client, section_with_exam):
    f = section_with_exam
    bad = await demo_admin_client.post(
        "/v1/school-admin/exams/marks/bulk",
        json={
            "exam_subject_id": f["es_math"]["id"],
            "entries": [{"student_id": 99999, "obtained_marks": 10}],
        },
    )
    assert bad.status_code == 400


@pytest.mark.asyncio
async def test_super_admin_blocked(super_admin_token):
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    ) as ac:
        r = await ac.get("/v1/school-admin/exams")
        assert r.status_code == 403
