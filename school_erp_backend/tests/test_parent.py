"""Phase 8 Parent Module tests."""

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


async def _admit_two_children(client) -> tuple[dict, dict]:
    """Use the same parent contact so siblings + parent both auto-link."""
    cls = (await client.post(
        "/v1/school-admin/classes",
        json={"code": "5", "name": "Class 5", "stage": "primary", "sequence": 5},
    )).json()
    sec = (await client.post(
        "/v1/school-admin/sections",
        json={"class_def_id": cls["id"], "name": "A"},
    )).json()
    common = {
        "class_def_id": cls["id"],
        "section_id": sec["id"],
        "parent_phone": "+919999000111",
        "parent_email": "ravi@home.test",
        "father_name": "Ravi Sharma",
    }
    a = (await client.post(
        "/v1/school-admin/students",
        json={**common, "full_name": "Aarav Sharma"},
    )).json()
    b = (await client.post(
        "/v1/school-admin/students",
        json={**common, "full_name": "Aanya Sharma"},
    )).json()
    return a, b


@pytest.mark.asyncio
async def test_admit_auto_creates_parent_user_and_link(demo_admin_client):
    a, b = await _admit_two_children(demo_admin_client)

    parents = (
        await demo_admin_client.get(f"/v1/school-admin/students/{a['id']}/parents")
    ).json()
    assert len(parents) == 1
    assert parents[0]["parent_phone"] == "+919999000111"
    assert parents[0]["is_primary"] is True
    # Same parent should also be linked to the second child.
    parents_b = (
        await demo_admin_client.get(f"/v1/school-admin/students/{b['id']}/parents")
    ).json()
    assert parents_b[0]["parent_id"] == parents[0]["parent_id"]


@pytest.mark.asyncio
async def test_create_parent_user_and_login(demo_admin_client):
    r = await demo_admin_client.post(
        "/v1/school-admin/parents",
        json={
            "full_name": "Suman Kapoor",
            "email": "suman@home.test",
            "phone": "+919800000001",
            "password": "Parent@123",
            "relation": "mother",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["full_name"] == "Suman Kapoor"

    # Parent can log in.
    token = await _login("demo", "suman@home.test", "Parent@123")
    assert token


@pytest.mark.asyncio
async def test_parent_endpoints_for_admitted_parent(demo_admin_client):
    a, b = await _admit_two_children(demo_admin_client)

    # The auto-created parent has no password (OTP-only). Set one via the
    # school admin's "create parent" endpoint by re-using the same email
    # would 409, so simulate the OTP flow with the reset-password endpoint.
    rp = await demo_admin_client.post(
        "/v1/auth/reset-password",
        json={"identifier": "ravi@home.test", "subdomain": "demo", "otp": "1234", "new_password": "Parent@123"},
    )
    assert rp.status_code == 204, rp.text

    parent_token = await _login("demo", "ravi@home.test", "Parent@123")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
        headers={"Authorization": f"Bearer {parent_token}", "X-Tenant-Subdomain": "demo"},
    ) as ac:
        me = await ac.get("/v1/parent/me")
        assert me.status_code == 200
        assert me.json()["relation"] in {"father", "guardian", "mother"}

        kids = await ac.get("/v1/parent/children")
        assert kids.status_code == 200
        assert {k["student_id"] for k in kids.json()} == {a["id"], b["id"]}

        switch = await ac.post("/v1/parent/select-child", json={"student_id": b["id"]})
        assert switch.status_code == 200
        assert switch.json()["current_child_id"] == b["id"]

        dash = await ac.get(f"/v1/parent/dashboard/{a['id']}")
        assert dash.status_code == 200
        body = dash.json()
        assert body["full_name"] == a["full_name"]
        assert body["pending_leaves"] == 0
        assert body["sibling_ids"] == [b["id"]]


@pytest.mark.asyncio
async def test_leave_application_full_cycle(demo_admin_client):
    a, _ = await _admit_two_children(demo_admin_client)
    await demo_admin_client.post(
        "/v1/auth/reset-password",
        json={"identifier": "ravi@home.test", "subdomain": "demo", "otp": "1234", "new_password": "Parent@123"},
    )

    parent_token = await _login("demo", "ravi@home.test", "Parent@123")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
        headers={"Authorization": f"Bearer {parent_token}", "X-Tenant-Subdomain": "demo"},
    ) as parent_ac:
        bad = await parent_ac.post(
            "/v1/parent/leave-applications",
            json={"student_id": a["id"], "start_date": "2025-08-10", "end_date": "2025-08-05", "reason": "Test"},
        )
        assert bad.status_code == 400  # end_date < start_date

        ok = await parent_ac.post(
            "/v1/parent/leave-applications",
            json={
                "student_id": a["id"],
                "start_date": "2025-08-10",
                "end_date": "2025-08-12",
                "reason": "Family wedding",
            },
        )
        assert ok.status_code == 201
        leave_id = ok.json()["id"]
        assert ok.json()["status"] == "pending"

        my_list = await parent_ac.get("/v1/parent/leave-applications")
        assert any(item["id"] == leave_id for item in my_list.json())

    # School admin sees it in queue and approves.
    queue = await demo_admin_client.get(
        "/v1/school-admin/leave-applications", params={"status": "pending"}
    )
    assert queue.status_code == 200
    assert any(item["id"] == leave_id for item in queue.json())

    decide = await demo_admin_client.post(
        f"/v1/school-admin/leave-applications/{leave_id}/decide",
        json={"decision": "approved", "decision_remarks": "Granted"},
    )
    assert decide.status_code == 200
    assert decide.json()["status"] == "approved"


@pytest.mark.asyncio
async def test_parent_cannot_access_other_childs_data(demo_admin_client):
    a, _ = await _admit_two_children(demo_admin_client)
    # Add a third student NOT linked to ravi@home.test (different parent contact).
    cls = (await demo_admin_client.post(
        "/v1/school-admin/classes",
        json={"code": "6", "name": "Class 6", "stage": "middle", "sequence": 6},
    )).json()
    other = (await demo_admin_client.post(
        "/v1/school-admin/students",
        json={
            "full_name": "Other Kid",
            "class_def_id": cls["id"],
            "parent_phone": "+919800100200",  # different parent
        },
    )).json()

    await demo_admin_client.post(
        "/v1/auth/reset-password",
        json={"identifier": "ravi@home.test", "subdomain": "demo", "otp": "1234", "new_password": "Parent@123"},
    )
    parent_token = await _login("demo", "ravi@home.test", "Parent@123")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
        headers={"Authorization": f"Bearer {parent_token}", "X-Tenant-Subdomain": "demo"},
    ) as ac:
        forbidden = await ac.get(f"/v1/parent/dashboard/{other['id']}")
        assert forbidden.status_code == 403


@pytest.mark.asyncio
async def test_school_admin_can_link_unlink_parent(demo_admin_client):
    a, _ = await _admit_two_children(demo_admin_client)
    # Manually create another parent.
    p = await demo_admin_client.post(
        "/v1/school-admin/parents",
        json={
            "full_name": "Step-mother",
            "email": "step@home.test",
            "password": "Step@123",
            "relation": "guardian",
        },
    )
    assert p.status_code == 201
    parent_user_id = p.json()["user_id"]

    link = await demo_admin_client.post(
        f"/v1/school-admin/students/{a['id']}/parents",
        json={
            "parent_user_id": parent_user_id,
            "relation": "guardian",
            "access_level": "secondary",
            "is_primary": False,
            "can_pay_fee": False,
            "can_receive_notifications": True,
        },
    )
    assert link.status_code == 200, link.text
    mapping_id = link.json()["mapping_id"]
    assert link.json()["access_level"] == "secondary"
    assert link.json()["can_pay_fee"] is False

    # List shows both parents now.
    parents = (
        await demo_admin_client.get(f"/v1/school-admin/students/{a['id']}/parents")
    ).json()
    assert len(parents) == 2

    # Unlink.
    rm = await demo_admin_client.delete(
        f"/v1/school-admin/students/{a['id']}/parents/{mapping_id}"
    )
    assert rm.status_code == 204
    assert len((
        await demo_admin_client.get(f"/v1/school-admin/students/{a['id']}/parents")
    ).json()) == 1


@pytest.mark.asyncio
async def test_super_admin_token_blocked_from_parent_routes(super_admin_token):
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    ) as ac:
        r = await ac.get("/v1/parent/me")
        assert r.status_code == 403
