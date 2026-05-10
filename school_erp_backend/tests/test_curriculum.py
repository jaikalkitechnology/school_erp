"""Phase 5 tests: houses, section subjects, calendar, syllabi + chapters."""

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
async def class_section_subject(demo_admin_client):
    """Create a class with a section and two subjects; return ids."""
    cls = (await demo_admin_client.post(
        "/v1/school-admin/classes",
        json={"code": "5", "name": "Class 5", "stage": "primary", "sequence": 5},
    )).json()
    sec = (await demo_admin_client.post(
        "/v1/school-admin/sections",
        json={"class_def_id": cls["id"], "name": "A", "capacity": 40},
    )).json()
    s1 = (await demo_admin_client.post(
        "/v1/school-admin/subjects",
        json={"code": "MATH", "name": "Mathematics"},
    )).json()
    s2 = (await demo_admin_client.post(
        "/v1/school-admin/subjects",
        json={"code": "ENG", "name": "English"},
    )).json()
    return {"class_id": cls["id"], "section_id": sec["id"], "subjects": [s1["id"], s2["id"]]}


@pytest.mark.asyncio
async def test_house_crud(demo_admin_client):
    create = await demo_admin_client.post(
        "/v1/school-admin/curriculum/houses",
        json={"name": "Saffron", "code": "S", "color": "#E85D2E"},
    )
    assert create.status_code == 201
    hid = create.json()["id"]

    listing = await demo_admin_client.get("/v1/school-admin/curriculum/houses")
    assert any(h["id"] == hid for h in listing.json())

    update = await demo_admin_client.patch(
        f"/v1/school-admin/curriculum/houses/{hid}",
        json={"name": "Saffron", "color": "#FFB800"},
    )
    assert update.status_code == 200
    assert update.json()["color"] == "#FFB800"

    rem = await demo_admin_client.delete(f"/v1/school-admin/curriculum/houses/{hid}")
    assert rem.status_code == 204


@pytest.mark.asyncio
async def test_section_subject_bulk_link_idempotent(demo_admin_client, class_section_subject):
    section_id = class_section_subject["section_id"]
    subjects = class_section_subject["subjects"]

    r1 = await demo_admin_client.post(
        "/v1/school-admin/curriculum/section-subjects/bulk",
        json={"section_id": section_id, "subject_ids": subjects, "weekly_periods": 5},
    )
    assert r1.status_code == 200
    assert len(r1.json()) == 2

    # Second call must be a no-op (idempotent), still returns the same set.
    r2 = await demo_admin_client.post(
        "/v1/school-admin/curriculum/section-subjects/bulk",
        json={"section_id": section_id, "subject_ids": subjects, "weekly_periods": 5},
    )
    assert r2.status_code == 200
    assert len(r2.json()) == 2


@pytest.mark.asyncio
async def test_calendar_event_crud(demo_admin_client):
    r = await demo_admin_client.post(
        "/v1/school-admin/curriculum/events",
        json={
            "title": "Sports day",
            "kind": "sports",
            "starts_at": "2025-12-15T08:00:00",
            "ends_at": "2025-12-15T17:00:00",
            "is_all_day": False,
        },
    )
    assert r.status_code == 201, r.text
    eid = r.json()["id"]

    upd = await demo_admin_client.patch(
        f"/v1/school-admin/curriculum/events/{eid}",
        json={
            "title": "Annual Sports Day",
            "kind": "sports",
            "starts_at": "2025-12-15T08:00:00",
        },
    )
    assert upd.status_code == 200
    assert upd.json()["title"] == "Annual Sports Day"

    listing = await demo_admin_client.get("/v1/school-admin/curriculum/events")
    assert any(e["id"] == eid for e in listing.json())


@pytest.mark.asyncio
async def test_syllabus_with_chapters_and_progress(demo_admin_client, class_section_subject):
    # Need an academic year for the syllabus FK.
    yr = (await demo_admin_client.post(
        "/v1/school-admin/academic-years",
        json={
            "code": "2025-26", "name": "AY 2025-26",
            "start_date": "2025-04-01", "end_date": "2026-03-31",
            "is_active": True,
        },
    )).json()

    syl = await demo_admin_client.post(
        "/v1/school-admin/curriculum/syllabi",
        json={
            "year_id": yr["id"],
            "class_def_id": class_section_subject["class_id"],
            "subject_id": class_section_subject["subjects"][0],
            "title": "Math Syllabus",
        },
    )
    assert syl.status_code == 201, syl.text
    sid = syl.json()["id"]
    assert syl.json()["overall_completion_pct"] == 0

    # Two chapters, weighted by expected_periods.
    c1 = await demo_admin_client.post(
        f"/v1/school-admin/curriculum/syllabi/{sid}/chapters",
        json={"sequence": 1, "title": "Numbers", "expected_periods": 6},
    )
    c2 = await demo_admin_client.post(
        f"/v1/school-admin/curriculum/syllabi/{sid}/chapters",
        json={"sequence": 2, "title": "Fractions", "expected_periods": 4},
    )
    assert c1.status_code == 201 and c2.status_code == 201

    # Mark chapter 1 100% done.
    p = await demo_admin_client.patch(
        f"/v1/school-admin/curriculum/chapters/{c1.json()['id']}/progress",
        json={"completion_pct": 100},
    )
    assert p.status_code == 200
    assert p.json()["completion_pct"] == 100
    assert p.json()["completed_on"] is not None

    # Mark chapter 2 50% done.
    p2 = await demo_admin_client.patch(
        f"/v1/school-admin/curriculum/chapters/{c2.json()['id']}/progress",
        json={"completion_pct": 50},
    )
    assert p2.status_code == 200

    listing = await demo_admin_client.get(
        "/v1/school-admin/curriculum/syllabi",
        params={"year_id": yr["id"]},
    )
    body = listing.json()[0]
    # 6*100 + 4*50 = 800; 800 / (6+4) = 80%
    assert body["overall_completion_pct"] == 80.0


@pytest.mark.asyncio
async def test_curriculum_routes_require_school_role(super_admin_token):
    """Super admin token must NOT be allowed (lacks school staff roles)."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    ) as ac:
        r = await ac.get("/v1/school-admin/curriculum/houses")
        assert r.status_code == 403
