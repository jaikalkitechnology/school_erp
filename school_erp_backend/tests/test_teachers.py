"""Phase 7 Teacher Management tests."""

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
async def class_section_subjects(demo_admin_client):
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
    ss = await demo_admin_client.post(
        "/v1/school-admin/curriculum/section-subjects/bulk",
        json={"section_id": sec["id"], "subject_ids": [math["id"], eng["id"]], "weekly_periods": 5},
    )
    section_subjects = ss.json()
    return cls, sec, math, eng, section_subjects


def _teacher_payload(**overrides):
    base = {
        "full_name": "Asha Mehta",
        "first_name": "Asha",
        "last_name": "Mehta",
        "email": "asha@demo.school",
        "phone": "+919811112222",
        "password": "Teacher@123",
        "qualifications": ["B.Ed", "M.Sc Math"],
        "experience_years": 5,
        "designation": "Senior Teacher",
        "role_codes": ["class_teacher", "subject_teacher"],
    }
    base.update(overrides)
    return base


@pytest.mark.asyncio
async def test_onboard_creates_user_and_role(demo_admin_client):
    r = await demo_admin_client.post("/v1/school-admin/teachers", json=_teacher_payload())
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["employee_no"].startswith("EMP-")
    assert body["employment_status"] == "active"

    # Newly created teacher can log in.
    token = await _login("demo", "asha@demo.school", "Teacher@123")
    assert token


@pytest.mark.asyncio
async def test_duplicate_email_409(demo_admin_client):
    await demo_admin_client.post(
        "/v1/school-admin/teachers", json=_teacher_payload()
    )
    r = await demo_admin_client.post(
        "/v1/school-admin/teachers",
        json=_teacher_payload(employee_no="EMP-X-0002"),
    )
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_workload_sums_weekly_periods(demo_admin_client, class_section_subjects):
    _, sec, math, eng, section_subjects = class_section_subjects
    t = (await demo_admin_client.post("/v1/school-admin/teachers", json=_teacher_payload())).json()

    # Assign teacher to both section-subject rows.
    for ss in section_subjects:
        r = await demo_admin_client.post(
            f"/v1/school-admin/teachers/{t['id']}/assign-section-subject",
            json={"section_subject_id": ss["id"]},
        )
        assert r.status_code == 200

    wl = await demo_admin_client.get(f"/v1/school-admin/teachers/{t['id']}/workload")
    assert wl.status_code == 200
    body = wl.json()
    assert body["weekly_periods_total"] == 10  # 5 + 5
    assert body["classes_handled"] == 1
    assert body["subjects_taught"] == 2

    # Clear one assignment - workload halves.
    cl = await demo_admin_client.delete(
        f"/v1/school-admin/teachers/section-subjects/{section_subjects[0]['id']}/teacher"
    )
    assert cl.status_code == 200
    wl2 = (await demo_admin_client.get(f"/v1/school-admin/teachers/{t['id']}/workload")).json()
    assert wl2["weekly_periods_total"] == 5


@pytest.mark.asyncio
async def test_class_teacher_assignment_writes_section(demo_admin_client, class_section_subjects):
    _, sec, _, _, _ = class_section_subjects
    t = (await demo_admin_client.post("/v1/school-admin/teachers", json=_teacher_payload())).json()
    r = await demo_admin_client.post(
        f"/v1/school-admin/teachers/{t['id']}/assign-class-teacher",
        json={"section_id": sec["id"]},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["section_id"] == sec["id"]
    assert body["in_charge_user_id"] == t["user_id"]


@pytest.mark.asyncio
async def test_qualified_subjects_replace_set(demo_admin_client, class_section_subjects):
    _, _, math, eng, _ = class_section_subjects
    t = (await demo_admin_client.post("/v1/school-admin/teachers", json=_teacher_payload())).json()

    r = await demo_admin_client.put(
        f"/v1/school-admin/teachers/{t['id']}/qualified-subjects",
        json={"subject_ids": [math["id"], eng["id"]]},
    )
    assert r.status_code == 200
    assert {row["subject_id"] for row in r.json()} == {math["id"], eng["id"]}

    # Replace with just math.
    r2 = await demo_admin_client.put(
        f"/v1/school-admin/teachers/{t['id']}/qualified-subjects",
        json={"subject_ids": [math["id"]]},
    )
    assert {row["subject_id"] for row in r2.json()} == {math["id"]}


@pytest.mark.asyncio
async def test_attendance_idempotent_upsert(demo_admin_client):
    t = (await demo_admin_client.post("/v1/school-admin/teachers", json=_teacher_payload())).json()
    r1 = await demo_admin_client.post(
        f"/v1/school-admin/teachers/{t['id']}/attendance",
        json={"date": "2025-08-01", "status": "present"},
    )
    assert r1.status_code == 200
    r2 = await demo_admin_client.post(
        f"/v1/school-admin/teachers/{t['id']}/attendance",
        json={"date": "2025-08-01", "status": "leave", "remarks": "Personal"},
    )
    assert r2.status_code == 200
    assert r2.json()["status"] == "leave"

    listing = await demo_admin_client.get(
        f"/v1/school-admin/teachers/{t['id']}/attendance",
        params={"start": "2025-08-01", "end": "2025-08-01"},
    )
    assert len(listing.json()) == 1


@pytest.mark.asyncio
async def test_substitution_pool_orders_by_present_then_workload(
    demo_admin_client, class_section_subjects
):
    _, _, math, _, section_subjects = class_section_subjects
    busy = (await demo_admin_client.post(
        "/v1/school-admin/teachers",
        json=_teacher_payload(full_name="Busy Teacher", email="busy@demo.school", phone="+91900"),
    )).json()
    free = (await demo_admin_client.post(
        "/v1/school-admin/teachers",
        json=_teacher_payload(full_name="Free Teacher", email="free@demo.school", phone="+91901"),
    )).json()

    # Busy gets both section-subjects (10 periods total); Free has 0.
    for ss in section_subjects:
        await demo_admin_client.post(
            f"/v1/school-admin/teachers/{busy['id']}/assign-section-subject",
            json={"section_subject_id": ss["id"]},
        )
    await demo_admin_client.post(
        f"/v1/school-admin/teachers/{busy['id']}/attendance",
        json={"date": "2025-08-01", "status": "absent"},
    )

    pool = await demo_admin_client.get(
        "/v1/school-admin/teachers/substitution-pool",
        params={"target_date": "2025-08-01"},
    )
    assert pool.status_code == 200
    rows = pool.json()
    # Free is present + 0 workload; should appear before absent busy teacher.
    free_idx = next(i for i, r in enumerate(rows) if r["teacher_id"] == free["id"])
    busy_idx = next(i for i, r in enumerate(rows) if r["teacher_id"] == busy["id"])
    assert free_idx < busy_idx


@pytest.mark.asyncio
async def test_super_admin_token_blocked(super_admin_token):
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    ) as ac:
        r = await ac.get("/v1/school-admin/teachers")
        assert r.status_code == 403


@pytest.mark.asyncio
async def test_cross_tenant_isolation(super_admin_token):
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    ) as super_ac:
        await super_ac.post(
            "/admin/tenants",
            json={
                "school_name": "OtherT", "school_code": "OT-001",
                "subdomain": "otherteach", "plan_code": "basic",
            },
        )
    from sqlalchemy import select

    from app.database import AsyncSessionLocal
    from app.models.tenant import Tenant
    from app.services.seed import _ensure_user, seed_rbac_for_tenant

    async with AsyncSessionLocal() as session:
        other_id = (
            await session.execute(select(Tenant.id).where(Tenant.subdomain == "otherteach"))
        ).scalar_one()
        await seed_rbac_for_tenant(session, other_id)
        await _ensure_user(
            session, tenant_id=other_id, email="ot@x.com", full_name="OT Admin",
            password="OT@123", role_codes=["school_admin"],
        )

    demo_token = await _login("demo", DEFAULT_SCHOOL_ADMIN_EMAIL, DEFAULT_SCHOOL_ADMIN_PASSWORD)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
        headers={"Authorization": f"Bearer {demo_token}", "X-Tenant-Subdomain": "demo"},
    ) as ac:
        await ac.post("/v1/school-admin/teachers", json=_teacher_payload(email="x@demo.school", phone="+9192"))

    other_token = await _login("otherteach", "ot@x.com", "OT@123")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
        headers={"Authorization": f"Bearer {other_token}", "X-Tenant-Subdomain": "otherteach"},
    ) as ac:
        listing = await ac.get("/v1/school-admin/teachers")
        assert listing.json()["total"] == 0
