"""Phase 13 timetable + substitution tests."""

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


async def _onboard_teacher(client, full_name: str, email: str, phone: str) -> dict:
    return (await client.post(
        "/v1/school-admin/teachers",
        json={
            "full_name": full_name,
            "email": email,
            "phone": phone,
            "password": "Teacher@123",
            "qualifications": ["B.Ed"],
            "experience_years": 3,
            "role_codes": ["subject_teacher"],
        },
    )).json()


@pytest_asyncio.fixture
async def two_sections_two_teachers_two_subjects(demo_admin_client):
    cls5 = (await demo_admin_client.post(
        "/v1/school-admin/classes",
        json={"code": "5", "name": "Class 5", "stage": "primary", "sequence": 5},
    )).json()
    sec5a = (await demo_admin_client.post(
        "/v1/school-admin/sections",
        json={"class_def_id": cls5["id"], "name": "A"},
    )).json()
    cls6 = (await demo_admin_client.post(
        "/v1/school-admin/classes",
        json={"code": "6", "name": "Class 6", "stage": "middle", "sequence": 6},
    )).json()
    sec6a = (await demo_admin_client.post(
        "/v1/school-admin/sections",
        json={"class_def_id": cls6["id"], "name": "A"},
    )).json()
    math = (await demo_admin_client.post(
        "/v1/school-admin/subjects",
        json={"code": "MATH", "name": "Mathematics"},
    )).json()
    eng = (await demo_admin_client.post(
        "/v1/school-admin/subjects",
        json={"code": "ENG", "name": "English"},
    )).json()
    asha = await _onboard_teacher(demo_admin_client, "Asha", "asha@demo.school", "+919800000010")
    bina = await _onboard_teacher(demo_admin_client, "Bina", "bina@demo.school", "+919800000011")
    return {
        "cls5": cls5, "sec5a": sec5a,
        "cls6": cls6, "sec6a": sec6a,
        "math": math, "eng": eng,
        "asha": asha, "bina": bina,
    }


@pytest.mark.asyncio
async def test_period_defs_crud(demo_admin_client):
    r = await demo_admin_client.put(
        "/v1/school-admin/timetable/periods",
        json={
            "day_of_week": 0, "period_number": 1,
            "label": "P1", "starts_at": "08:30:00", "ends_at": "09:15:00",
        },
    )
    assert r.status_code == 200, r.text
    listing = await demo_admin_client.get("/v1/school-admin/timetable/periods")
    assert any(p["period_number"] == 1 for p in listing.json())

    bad = await demo_admin_client.put(
        "/v1/school-admin/timetable/periods",
        json={
            "day_of_week": 0, "period_number": 2,
            "starts_at": "10:00:00", "ends_at": "09:00:00",
        },
    )
    assert bad.status_code == 400


@pytest.mark.asyncio
async def test_section_grid_save_and_conflict(demo_admin_client, two_sections_two_teachers_two_subjects):
    f = two_sections_two_teachers_two_subjects
    asha_user = f["asha"]["user_id"]

    # Save section 5A: Asha takes Mon period 1.
    save = await demo_admin_client.put(
        f"/v1/school-admin/timetable/sections/{f['sec5a']['id']}",
        json={
            "cells": [
                {
                    "day_of_week": 0, "period_number": 1,
                    "subject_id": f["math"]["id"], "teacher_user_id": asha_user, "room": "R-1",
                },
                {
                    "day_of_week": 0, "period_number": 2,
                    "subject_id": f["eng"]["id"], "teacher_user_id": asha_user, "room": "R-1",
                },
            ]
        },
    )
    assert save.status_code == 200
    assert save.json() == {"saved": 2, "conflicts": []}

    # Now try to give Asha Mon P1 in section 6A too -> conflict.
    clash = await demo_admin_client.put(
        f"/v1/school-admin/timetable/sections/{f['sec6a']['id']}",
        json={
            "cells": [
                {
                    "day_of_week": 0, "period_number": 1,
                    "subject_id": f["math"]["id"], "teacher_user_id": asha_user,
                },
            ]
        },
    )
    assert clash.status_code == 200
    body = clash.json()
    assert body["saved"] == 0
    assert len(body["conflicts"]) == 1
    assert body["conflicts"][0]["other_section_id"] == f["sec5a"]["id"]


@pytest.mark.asyncio
async def test_duplicate_cell_in_payload_400(demo_admin_client, two_sections_two_teachers_two_subjects):
    f = two_sections_two_teachers_two_subjects
    bad = await demo_admin_client.put(
        f"/v1/school-admin/timetable/sections/{f['sec5a']['id']}",
        json={
            "cells": [
                {"day_of_week": 0, "period_number": 1},
                {"day_of_week": 0, "period_number": 1},
            ]
        },
    )
    assert bad.status_code == 400


@pytest.mark.asyncio
async def test_teacher_view_lists_their_periods(demo_admin_client, two_sections_two_teachers_two_subjects):
    f = two_sections_two_teachers_two_subjects
    asha_user = f["asha"]["user_id"]
    await demo_admin_client.put(
        f"/v1/school-admin/timetable/sections/{f['sec5a']['id']}",
        json={
            "cells": [
                {"day_of_week": 0, "period_number": 1, "subject_id": f["math"]["id"], "teacher_user_id": asha_user},
                {"day_of_week": 1, "period_number": 1, "subject_id": f["eng"]["id"], "teacher_user_id": asha_user},
            ]
        },
    )
    r = await demo_admin_client.get(f"/v1/school-admin/timetable/teachers/{asha_user}")
    assert r.status_code == 200
    cells = r.json()["cells"]
    days = {c["day_of_week"] for c in cells}
    assert days == {0, 1}


@pytest.mark.asyncio
async def test_substitution_suggest_picks_free_qualified_teacher(
    demo_admin_client, two_sections_two_teachers_two_subjects
):
    f = two_sections_two_teachers_two_subjects
    asha_user = f["asha"]["user_id"]
    bina = f["bina"]
    bina_user = bina["user_id"]

    # Make Bina qualified for Math.
    await demo_admin_client.put(
        f"/v1/school-admin/teachers/{bina['id']}/qualified-subjects",
        json={"subject_ids": [f["math"]["id"]]},
    )

    # Mon = 2024-08-05 (a Monday). Asha takes Math at 5A Mon P1.
    await demo_admin_client.put(
        f"/v1/school-admin/timetable/sections/{f['sec5a']['id']}",
        json={
            "cells": [
                {"day_of_week": 0, "period_number": 1, "subject_id": f["math"]["id"], "teacher_user_id": asha_user},
            ]
        },
    )

    r = await demo_admin_client.post(
        "/v1/school-admin/timetable/substitutions/suggest",
        json={"date": "2024-08-05", "teacher_user_id": asha_user},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["entries"]
    e = body["entries"][0]
    assert e["section_id"] == f["sec5a"]["id"]
    assert e["period_number"] == 1
    assert bina_user in e["suggested_substitutes"]


@pytest.mark.asyncio
async def test_substitution_blocks_busy_teacher(
    demo_admin_client, two_sections_two_teachers_two_subjects
):
    f = two_sections_two_teachers_two_subjects
    asha_user = f["asha"]["user_id"]
    bina_user = f["bina"]["user_id"]

    # Asha = Math at 5A Mon P1; Bina = English at 6A Mon P1 (busy at the same slot).
    await demo_admin_client.put(
        f"/v1/school-admin/timetable/sections/{f['sec5a']['id']}",
        json={
            "cells": [
                {"day_of_week": 0, "period_number": 1, "subject_id": f["math"]["id"], "teacher_user_id": asha_user},
            ]
        },
    )
    await demo_admin_client.put(
        f"/v1/school-admin/timetable/sections/{f['sec6a']['id']}",
        json={
            "cells": [
                {"day_of_week": 0, "period_number": 1, "subject_id": f["eng"]["id"], "teacher_user_id": bina_user},
            ]
        },
    )

    bad = await demo_admin_client.post(
        "/v1/school-admin/timetable/substitutions",
        json={
            "date": "2024-08-05",
            "section_id": f["sec5a"]["id"],
            "period_number": 1,
            "substitute_teacher_user_id": bina_user,
            "reason": "Asha sick",
        },
    )
    assert bad.status_code == 409


@pytest.mark.asyncio
async def test_substitution_assign_complete_cancel(
    demo_admin_client, two_sections_two_teachers_two_subjects
):
    f = two_sections_two_teachers_two_subjects
    asha_user = f["asha"]["user_id"]
    bina_user = f["bina"]["user_id"]
    await demo_admin_client.put(
        f"/v1/school-admin/timetable/sections/{f['sec5a']['id']}",
        json={
            "cells": [
                {"day_of_week": 0, "period_number": 1, "subject_id": f["math"]["id"], "teacher_user_id": asha_user},
            ]
        },
    )
    create = await demo_admin_client.post(
        "/v1/school-admin/timetable/substitutions",
        json={
            "date": "2024-08-05",
            "section_id": f["sec5a"]["id"],
            "period_number": 1,
            "substitute_teacher_user_id": bina_user,
        },
    )
    assert create.status_code == 201
    sub_id = create.json()["id"]
    assert create.json()["status"] == "assigned"

    listing = await demo_admin_client.get(
        "/v1/school-admin/timetable/substitutions",
        params={"target_date": "2024-08-05"},
    )
    assert any(s["id"] == sub_id for s in listing.json())

    done = await demo_admin_client.post(
        f"/v1/school-admin/timetable/substitutions/{sub_id}/complete"
    )
    assert done.json()["status"] == "completed"

    cancel = await demo_admin_client.post(
        f"/v1/school-admin/timetable/substitutions/{sub_id}/cancel"
    )
    assert cancel.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_super_admin_blocked(super_admin_token):
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    ) as ac:
        r = await ac.get("/v1/school-admin/timetable/periods")
        assert r.status_code == 403
