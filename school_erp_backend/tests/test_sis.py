"""Phase 6 SIS tests: admit, search, sibling auto-link, promote, withdraw, isolation."""

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
async def class_section(demo_admin_client):
    cls = (await demo_admin_client.post(
        "/v1/school-admin/classes",
        json={"code": "5", "name": "Class 5", "stage": "primary", "sequence": 5},
    )).json()
    sec = (await demo_admin_client.post(
        "/v1/school-admin/sections",
        json={"class_def_id": cls["id"], "name": "A"},
    )).json()
    return cls, sec


@pytest.mark.asyncio
async def test_admit_with_auto_admission_number(demo_admin_client, class_section):
    cls, sec = class_section
    r = await demo_admin_client.post(
        "/v1/school-admin/students",
        json={
            "full_name": "Aarav Sharma",
            "first_name": "Aarav", "last_name": "Sharma",
            "date_of_birth": "2015-04-01",
            "gender": "male",
            "class_def_id": cls["id"],
            "section_id": sec["id"],
            "parent_phone": "+919876543210",
            "father_name": "Ravi Sharma",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["admission_number"].startswith("ADM-")
    assert body["status"] == "active"
    assert body["current_class_label"] == "Class 5 · A"


@pytest.mark.asyncio
async def test_section_must_match_class(demo_admin_client, class_section):
    cls_a = (await demo_admin_client.post(
        "/v1/school-admin/classes",
        json={"code": "6", "name": "Class 6", "stage": "middle", "sequence": 6},
    )).json()
    sec_b = (await demo_admin_client.post(
        "/v1/school-admin/sections",
        json={"class_def_id": cls_a["id"], "name": "A"},
    )).json()

    cls_other, _ = class_section  # class 5
    r = await demo_admin_client.post(
        "/v1/school-admin/students",
        json={
            "full_name": "Mismatched",
            "class_def_id": cls_other["id"],  # class 5
            "section_id": sec_b["id"],         # section of class 6
        },
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_sibling_auto_link_on_phone_match(demo_admin_client, class_section):
    cls, sec = class_section
    payload = {
        "class_def_id": cls["id"],
        "section_id": sec["id"],
        "parent_phone": "+919998887777",
    }
    a = (await demo_admin_client.post(
        "/v1/school-admin/students",
        json={**payload, "full_name": "Sibling One"},
    )).json()
    b = (await demo_admin_client.post(
        "/v1/school-admin/students",
        json={**payload, "full_name": "Sibling Two"},
    )).json()

    detail_a = (await demo_admin_client.get(f"/v1/school-admin/students/{a['id']}")).json()
    detail_b = (await demo_admin_client.get(f"/v1/school-admin/students/{b['id']}")).json()
    assert detail_a["sibling_group_id"] == detail_b["sibling_group_id"]
    assert b["id"] in detail_a["sibling_ids"]
    assert a["id"] in detail_b["sibling_ids"]


@pytest.mark.asyncio
async def test_search_by_admission_and_class_filter(demo_admin_client, class_section):
    cls, sec = class_section
    s1 = (await demo_admin_client.post(
        "/v1/school-admin/students",
        json={"full_name": "Riya Kapoor", "class_def_id": cls["id"], "section_id": sec["id"]},
    )).json()

    r = await demo_admin_client.get("/v1/school-admin/students", params={"q": "Riya"})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 1
    assert any(item["id"] == s1["id"] for item in body["items"])

    r2 = await demo_admin_client.get(
        "/v1/school-admin/students", params={"class_def_id": cls["id"]}
    )
    assert r2.status_code == 200
    assert any(item["id"] == s1["id"] for item in r2.json()["items"])


@pytest.mark.asyncio
async def test_promotion_skips_inactive(demo_admin_client, class_section):
    cls5, sec5 = class_section
    cls6 = (await demo_admin_client.post(
        "/v1/school-admin/classes",
        json={"code": "6", "name": "Class 6", "stage": "middle", "sequence": 6},
    )).json()
    sec6 = (await demo_admin_client.post(
        "/v1/school-admin/sections",
        json={"class_def_id": cls6["id"], "name": "A"},
    )).json()

    active = (await demo_admin_client.post(
        "/v1/school-admin/students",
        json={"full_name": "Promote Me", "class_def_id": cls5["id"], "section_id": sec5["id"]},
    )).json()
    other = (await demo_admin_client.post(
        "/v1/school-admin/students",
        json={"full_name": "Withdrawn Me", "class_def_id": cls5["id"], "section_id": sec5["id"]},
    )).json()
    await demo_admin_client.post(
        f"/v1/school-admin/students/{other['id']}/withdraw",
        json={"status": "transferred"},
    )

    r = await demo_admin_client.post(
        "/v1/school-admin/students/promote",
        json={
            "student_ids": [active["id"], other["id"]],
            "target_class_def_id": cls6["id"],
            "target_section_id": sec6["id"],
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert active["id"] in body["promoted"]
    assert other["id"] not in body["promoted"]
    assert any(s["id"] == other["id"] for s in body["skipped"])

    detail = (await demo_admin_client.get(f"/v1/school-admin/students/{active['id']}")).json()
    assert detail["class_def_id"] == cls6["id"]
    assert detail["section_id"] == sec6["id"]


@pytest.mark.asyncio
async def test_withdraw_and_transfer_certificate(demo_admin_client, class_section):
    cls, sec = class_section
    s = (await demo_admin_client.post(
        "/v1/school-admin/students",
        json={"full_name": "Bye Student", "class_def_id": cls["id"], "section_id": sec["id"]},
    )).json()

    w = await demo_admin_client.post(
        f"/v1/school-admin/students/{s['id']}/withdraw",
        json={"status": "transferred", "remarks": "Family relocated"},
    )
    assert w.status_code == 200
    assert w.json()["status"] == "transferred"
    assert w.json()["is_active"] is False

    tc = await demo_admin_client.get(f"/v1/school-admin/students/{s['id']}/transfer-certificate")
    assert tc.status_code == 200
    body = tc.json()
    assert body["school_name"]
    assert body["last_class_label"] == "Class 5 · A"


@pytest.mark.asyncio
async def test_admission_funnel_promotes_to_student(demo_admin_client):
    a = await demo_admin_client.post(
        "/v1/school-admin/admissions",
        json={"full_name": "Future Student", "parent_phone": "+919000000000"},
    )
    assert a.status_code == 201
    aid = a.json()["id"]

    s = await demo_admin_client.post(f"/v1/school-admin/admissions/{aid}/admit")
    assert s.status_code == 200, s.text
    assert s.json()["full_name"] == "Future Student"

    # Replay should 409 (already admitted).
    s2 = await demo_admin_client.post(f"/v1/school-admin/admissions/{aid}/admit")
    assert s2.status_code == 409


@pytest.mark.asyncio
async def test_documents_attach_and_verify(demo_admin_client, class_section):
    cls, sec = class_section
    s = (await demo_admin_client.post(
        "/v1/school-admin/students",
        json={"full_name": "Doc Student", "class_def_id": cls["id"], "section_id": sec["id"]},
    )).json()

    d = await demo_admin_client.post(
        f"/v1/school-admin/students/{s['id']}/documents",
        json={"kind": "birth_certificate", "label": "BC", "path": "tenant_2/students/documents/x.pdf"},
    )
    assert d.status_code == 201
    did = d.json()["id"]
    assert d.json()["is_verified"] is False

    v = await demo_admin_client.post(
        f"/v1/school-admin/students/{s['id']}/documents/{did}/verify"
    )
    assert v.status_code == 200
    assert v.json()["is_verified"] is True


@pytest.mark.asyncio
async def test_cross_tenant_isolation_on_students(super_admin_token):
    """Other tenant cannot see Demo's students."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    ) as super_ac:
        await super_ac.post(
            "/admin/tenants",
            json={"school_name": "Other", "school_code": "OTH-001", "subdomain": "othersis", "plan_code": "basic"},
        )
    from app.database import AsyncSessionLocal
    from app.services.seed import _ensure_user, seed_rbac_for_tenant
    from sqlalchemy import select
    from app.models.tenant import Tenant

    async with AsyncSessionLocal() as session:
        other_id = (
            await session.execute(select(Tenant.id).where(Tenant.subdomain == "othersis"))
        ).scalar_one()
        await seed_rbac_for_tenant(session, other_id)
        await _ensure_user(
            session,
            tenant_id=other_id,
            email="other@sis.com",
            full_name="Other Admin",
            password="Other@123",
            role_codes=["school_admin"],
        )

    demo_token = await _login("demo", DEFAULT_SCHOOL_ADMIN_EMAIL, DEFAULT_SCHOOL_ADMIN_PASSWORD)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
        headers={"Authorization": f"Bearer {demo_token}", "X-Tenant-Subdomain": "demo"},
    ) as ac:
        await ac.post("/v1/school-admin/students", json={"full_name": "Secret Student"})

    other_token = await _login("othersis", "other@sis.com", "Other@123")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
        headers={"Authorization": f"Bearer {other_token}", "X-Tenant-Subdomain": "othersis"},
    ) as ac:
        listing = await ac.get("/v1/school-admin/students")
        assert listing.status_code == 200
        assert all(item["full_name"] != "Secret Student" for item in listing.json()["items"])
