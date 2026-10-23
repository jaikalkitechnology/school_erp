"""Coordinator's day: attendance by section, teachers away, cover needed."""

from datetime import date

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.main import app
from app.services.seed import DEFAULT_SCHOOL_ADMIN_EMAIL, DEFAULT_SCHOOL_ADMIN_PASSWORD, DEFAULT_STAFF_PASSWORD


async def _client_for(email: str, password: str) -> AsyncClient:
    ac = AsyncClient(
        transport=ASGITransport(app=app), base_url="http://localhost", headers={"X-Tenant-Subdomain": "demo"}
    )
    r = await ac.post("/v1/auth/login", json={"identifier": email, "password": password, "subdomain": "demo"})
    assert r.status_code == 200, r.text
    ac.headers["Authorization"] = f"Bearer {r.json()['tokens']['access_token']}"
    return ac


async def _setup_absent_teacher() -> tuple[int, int, int]:
    """The seeded class + subject teachers; the first is marked absent today
    and has period 2 in a new section. Returns (absent_uid, other_uid, section_id)."""
    from app.database import AsyncSessionLocal
    from app.models.academic import ClassDef, Section
    from app.models.auth import User
    from app.models.teacher import Teacher, TeacherAttendance
    from app.models.tenant import Tenant
    from app.models.timetable import TimetableEntry

    async with AsyncSessionLocal() as s:
        tid = (await s.execute(select(Tenant.id).where(Tenant.subdomain == "demo"))).scalar_one()
        teachers = []
        for email in ("class.teacher@demo.school", "subject.teacher@demo.school"):
            user = (await s.execute(select(User).where(User.tenant_id == tid, User.email == email))).scalar_one()
            t = (await s.execute(select(Teacher).where(Teacher.user_id == user.id))).scalar_one_or_none()
            if t is None:
                t = Teacher(tenant_id=tid, user_id=user.id, employee_no=f"T{user.id}", full_name=user.full_name)
                s.add(t)
            teachers.append(t)
        cls = ClassDef(tenant_id=tid, code="C9", name="Class 9", stage="secondary", sequence=9)
        s.add(cls)
        await s.flush()
        sec = Section(tenant_id=tid, class_def_id=cls.id, name="A", capacity=40)
        s.add(sec)
        await s.flush()
        s.add(TimetableEntry(tenant_id=tid, section_id=sec.id, day_of_week=date.today().weekday(),
                             period_number=2, teacher_user_id=teachers[0].user_id))
        s.add(TeacherAttendance(tenant_id=tid, teacher_id=teachers[0].id, date=date.today(), status="absent"))
        await s.commit()
        return teachers[0].user_id, teachers[1].user_id, sec.id


@pytest.mark.asyncio
async def test_coordinator_sees_cover_needed_and_assigns(super_admin_token):
    admin = await _client_for(DEFAULT_SCHOOL_ADMIN_EMAIL, DEFAULT_SCHOOL_ADMIN_PASSWORD)
    r = await admin.post(
        "/v1/school-admin/users",
        json={"full_name": "Meera Coordinator", "email": "coord@demo.school", "password": "Coord@123",
              "role_codes": ["coordinator"]},
    )
    assert r.status_code == 201, r.text
    a_uid, b_uid, section_id = await _setup_absent_teacher()
    coord = await _client_for("coord@demo.school", "Coord@123")
    try:
        day = (await coord.get("/v1/coordinator/today")).json()
        assert any(s["label"] == "Class 9-A" and s["marked"] is False for s in day["sections"])
        away = {t["user_id"]: t for t in day["absent_teachers"]}
        assert a_uid in away and away[a_uid]["reason"] == "Marked absent"
        period = away[a_uid]["periods"][0]
        assert period["section_label"] == "Class 9-A" and period["period_number"] == 2
        assert period["substitution"] is None
        assert b_uid in [s["user_id"] for s in period["suggestions"]]
        assert day["cover"] == {"needed": 1, "covered": 0}

        # Assign the suggested teacher with the existing timetable endpoint.
        r = await coord.post(
            "/v1/school-admin/timetable/substitutions",
            json={"date": date.today().isoformat(), "section_id": section_id, "period_number": 2,
                  "substitute_teacher_user_id": b_uid, "reason": "Teacher absent"},
        )
        assert r.status_code == 201, r.text
        day = (await coord.get("/v1/coordinator/today")).json()
        assert day["cover"] == {"needed": 1, "covered": 1}
        sub = day["absent_teachers"][0]["periods"][0]["substitution"]
        assert sub["substitute_user_id"] == b_uid and sub["substitute_name"]
    finally:
        await admin.aclose()
        await coord.aclose()


@pytest.mark.asyncio
async def test_teacher_cannot_open_coordinator_view(super_admin_token):
    t = await _client_for("subject.teacher@demo.school", DEFAULT_STAFF_PASSWORD)
    try:
        assert (await t.get("/v1/coordinator/today")).status_code == 403
    finally:
        await t.aclose()
