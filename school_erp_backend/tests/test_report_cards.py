"""Phase 16 report card system tests."""

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
async def graded_section(demo_admin_client):
    """Two-student class with two subjects, marks already entered, default
    grade scale set."""
    cls = (await demo_admin_client.post(
        "/v1/school-admin/classes",
        json={"code": "6", "name": "Class 6", "stage": "primary", "sequence": 6},
    )).json()
    sec = (await demo_admin_client.post(
        "/v1/school-admin/sections",
        json={"class_def_id": cls["id"], "name": "A"},
    )).json()
    math = (await demo_admin_client.post(
        "/v1/school-admin/subjects",
        json={"code": "MATH", "name": "Mathematics"},
    )).json()
    sci = (await demo_admin_client.post(
        "/v1/school-admin/subjects",
        json={"code": "SCI", "name": "Science"},
    )).json()
    students = []
    for name, phone in [("Diya", "+919900000050"), ("Eshan", "+919900000051")]:
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
        json={"name": "Term 1", "kind": "quarterly", "default_max_marks": 50},
    )).json()
    es_math = (await demo_admin_client.post(
        f"/v1/school-admin/exams/{exam['id']}/subjects",
        json={"class_def_id": cls["id"], "subject_id": math["id"],
              "max_marks": 50, "passing_marks": 18},
    )).json()
    es_sci = (await demo_admin_client.post(
        f"/v1/school-admin/exams/{exam['id']}/subjects",
        json={"class_def_id": cls["id"], "subject_id": sci["id"],
              "max_marks": 50, "passing_marks": 18},
    )).json()
    await demo_admin_client.put(
        "/v1/school-admin/grade-scales",
        json={
            "code": "default", "name": "Default", "is_default": True,
            "bands": [
                {"min_pct": 90, "grade": "A+"},
                {"min_pct": 75, "grade": "A"},
                {"min_pct": 50, "grade": "B"},
                {"min_pct": 33, "grade": "C"},
                {"min_pct": 0, "grade": "F"},
            ],
        },
    )
    # Diya: 45+45 = 90% A+; Eshan: 25+30 = 55% B
    await demo_admin_client.post(
        "/v1/school-admin/exams/marks/bulk",
        json={
            "exam_subject_id": es_math["id"],
            "entries": [
                {"student_id": students[0]["id"], "obtained_marks": 45},
                {"student_id": students[1]["id"], "obtained_marks": 25},
            ],
        },
    )
    await demo_admin_client.post(
        "/v1/school-admin/exams/marks/bulk",
        json={
            "exam_subject_id": es_sci["id"],
            "entries": [
                {"student_id": students[0]["id"], "obtained_marks": 45},
                {"student_id": students[1]["id"], "obtained_marks": 30},
            ],
        },
    )
    return {"cls": cls, "sec": sec, "exam": exam, "students": students}


@pytest.mark.asyncio
async def test_template_crud(demo_admin_client):
    upserted = await demo_admin_client.put(
        "/v1/school-admin/report-cards/templates",
        json={
            "code": "cbse-default", "name": "CBSE Default",
            "board": "cbse",
            "layout": {"show_co_curricular": True, "show_attendance": True},
            "is_default": True,
        },
    )
    assert upserted.status_code == 200, upserted.text
    body = upserted.json()
    assert body["is_default"] is True

    # Second default flips first off.
    second = await demo_admin_client.put(
        "/v1/school-admin/report-cards/templates",
        json={
            "code": "icse-default", "name": "ICSE Default",
            "board": "icse", "layout": {}, "is_default": True,
        },
    )
    assert second.status_code == 200
    listing = (await demo_admin_client.get("/v1/school-admin/report-cards/templates")).json()
    by_code = {t["code"]: t for t in listing}
    assert by_code["icse-default"]["is_default"] is True
    assert by_code["cbse-default"]["is_default"] is False


@pytest.mark.asyncio
async def test_co_curricular_and_remarks(demo_admin_client, graded_section):
    f = graded_section
    student_id = f["students"][0]["id"]

    cc = await demo_admin_client.post(
        f"/v1/school-admin/report-cards/{f['exam']['id']}/co-curricular",
        json={"student_id": student_id, "area": "Discipline", "grade": "A", "remarks": "Excellent"},
    )
    assert cc.status_code == 200
    # Upsert (same area) replaces.
    cc2 = await demo_admin_client.post(
        f"/v1/school-admin/report-cards/{f['exam']['id']}/co-curricular",
        json={"student_id": student_id, "area": "Discipline", "grade": "A+"},
    )
    assert cc2.json()["grade"] == "A+"

    rem = await demo_admin_client.post(
        f"/v1/school-admin/report-cards/{f['exam']['id']}/remarks",
        json={"student_id": student_id,
              "teacher_remark": "Diya is consistent.",
              "principal_remark": "Keep it up."},
    )
    assert rem.status_code == 200

    listing = await demo_admin_client.get(
        f"/v1/school-admin/report-cards/{f['exam']['id']}/co-curricular",
        params={"section_id": f["sec"]["id"]},
    )
    assert any(c["area"] == "Discipline" for c in listing.json())


@pytest.mark.asyncio
async def test_generate_bulk_and_pdf_download(demo_admin_client, graded_section):
    f = graded_section
    # Add a co-curricular entry + remark for the topper.
    await demo_admin_client.post(
        f"/v1/school-admin/report-cards/{f['exam']['id']}/co-curricular",
        json={"student_id": f["students"][0]["id"], "area": "Sports", "grade": "A"},
    )
    await demo_admin_client.post(
        f"/v1/school-admin/report-cards/{f['exam']['id']}/remarks",
        json={"student_id": f["students"][0]["id"], "teacher_remark": "Star pupil."},
    )

    gen = await demo_admin_client.post(
        "/v1/school-admin/report-cards/generate",
        json={"exam_id": f["exam"]["id"], "section_id": f["sec"]["id"], "publish": False},
    )
    assert gen.status_code == 200, gen.text
    body = gen.json()
    assert body["generated"] == 2
    assert body["skipped"] == 0

    listing = (await demo_admin_client.get(
        f"/v1/school-admin/report-cards/{f['exam']['id']}/sections/{f['sec']['id']}"
    )).json()
    assert len(listing) == 2
    by_student = {rc["student_id"]: rc for rc in listing}
    diya = by_student[f["students"][0]["id"]]
    assert diya["overall_grade"] == "A+"
    assert diya["rank_in_section"] == 1
    assert diya["status"] == "generated"
    assert diya["snapshot"]["co_curricular"]
    assert diya["snapshot"]["remarks"]["teacher_remark"] == "Star pupil."

    pdf = await demo_admin_client.get(
        f"/v1/school-admin/report-cards/{diya['id']}/pdf"
    )
    assert pdf.status_code == 200
    assert pdf.headers["content-type"].startswith("application/pdf")
    assert pdf.content[:4] == b"%PDF"

    # Re-generate is idempotent (same row updated).
    again = await demo_admin_client.post(
        "/v1/school-admin/report-cards/generate",
        json={"exam_id": f["exam"]["id"], "section_id": f["sec"]["id"], "publish": True},
    )
    assert again.json()["generated"] == 2
    listing2 = (await demo_admin_client.get(
        f"/v1/school-admin/report-cards/{f['exam']['id']}/sections/{f['sec']['id']}"
    )).json()
    assert len(listing2) == 2  # idempotent — same two rows
    assert all(r["status"] == "published" for r in listing2)


@pytest.mark.asyncio
async def test_publish_section_and_parent_download(demo_admin_client, graded_section):
    f = graded_section
    await demo_admin_client.post(
        "/v1/school-admin/report-cards/generate",
        json={"exam_id": f["exam"]["id"], "section_id": f["sec"]["id"]},
    )
    pub = await demo_admin_client.post(
        f"/v1/school-admin/report-cards/{f['exam']['id']}/sections/{f['sec']['id']}/publish"
    )
    assert pub.status_code == 200
    assert pub.json()["published"] == 2

    # Parent of Diya can access her card; cannot access Eshan's.
    await demo_admin_client.post(
        "/v1/auth/reset-password",
        json={"identifier": "diya@home.test", "subdomain": "demo",
              "otp": "1234", "new_password": "Parent@123"},
    )
    parent_token = await _login("demo", "diya@home.test", "Parent@123")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
        headers={"Authorization": f"Bearer {parent_token}", "X-Tenant-Subdomain": "demo"},
    ) as parent_ac:
        rows = await parent_ac.get(
            f"/v1/parent/children/{f['students'][0]['id']}/report-cards"
        )
        assert rows.status_code == 200
        body = rows.json()
        assert len(body["rows"]) == 1
        card = body["rows"][0]
        assert card["status"] == "published"
        assert card["overall_grade"] == "A+"

        pdf = await parent_ac.get(card["pdf_url"])
        assert pdf.status_code == 200
        assert pdf.content[:4] == b"%PDF"

        bad = await parent_ac.get(
            f"/v1/parent/children/{f['students'][1]['id']}/report-cards"
        )
        assert bad.status_code == 403


@pytest.mark.asyncio
async def test_generate_unknown_exam_404(demo_admin_client, graded_section):
    f = graded_section
    bad = await demo_admin_client.post(
        "/v1/school-admin/report-cards/generate",
        json={"exam_id": 99999, "section_id": f["sec"]["id"]},
    )
    assert bad.status_code == 404


@pytest.mark.asyncio
async def test_super_admin_blocked(super_admin_token):
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    ) as ac:
        r = await ac.get("/v1/school-admin/report-cards/templates")
        assert r.status_code == 403
