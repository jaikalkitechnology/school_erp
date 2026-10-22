"""Super admin sets each school's own admin login (onboarding + reset)."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


async def _login(subdomain: str, email: str, password: str):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as ac:
        return await ac.post(
            "/v1/auth/login",
            json={"identifier": email, "password": password, "subdomain": subdomain},
        )


@pytest.mark.asyncio
async def test_onboard_with_admin_then_login(auth_client):
    r = await auth_client.post(
        "/admin/tenants",
        json={
            "school_name": "Green Valley School",
            "school_code": "GVS-001",
            "subdomain": "greenvalley",
            "plan_code": "basic",
            "admin": {
                "full_name": "Asha Rao",
                "email": "Principal@GreenValley.edu",
                "password": "Valley2026",
            },
        },
    )
    assert r.status_code == 201, r.text
    tid = r.json()["id"]

    admins = (await auth_client.get(f"/admin/tenants/{tid}/admins")).json()
    assert [a["email"] for a in admins] == ["principal@greenvalley.edu"]

    login = await _login("greenvalley", "principal@greenvalley.edu", "Valley2026")
    assert login.status_code == 200, login.text
    # school_admin sees every admin page through its role (no per-page grants).
    assert "school_admin" in login.json()["user"]["roles"]

    # The demo school's seeded admin can't get into this school.
    other = await _login("greenvalley", "admin@demo.school", "School@123")
    assert other.status_code == 401


@pytest.mark.asyncio
async def test_reset_and_add_admin_for_existing_school(auth_client):
    r = await auth_client.post(
        "/admin/tenants",
        json={"school_name": "Old School", "school_code": "OLD-001", "subdomain": "oldschool", "plan_code": "basic"},
    )
    tid = r.json()["id"]
    assert (await auth_client.get(f"/admin/tenants/{tid}/admins")).json() == []

    body = {"full_name": "Ravi K", "email": "office@old.school", "password": "First1234"}
    assert (await auth_client.put(f"/admin/tenants/{tid}/admin", json=body)).status_code == 200
    assert (await _login("oldschool", "office@old.school", "First1234")).status_code == 200

    # Same email again = password reset, not a second account.
    body["password"] = "Second5678"
    assert (await auth_client.put(f"/admin/tenants/{tid}/admin", json=body)).status_code == 200
    assert len((await auth_client.get(f"/admin/tenants/{tid}/admins")).json()) == 1
    assert (await _login("oldschool", "office@old.school", "First1234")).status_code == 401
    assert (await _login("oldschool", "office@old.school", "Second5678")).status_code == 200


@pytest.mark.asyncio
@pytest.mark.parametrize("password", ["short1", "lettersonly", "12345678"])
async def test_weak_admin_password_rejected(auth_client, password):
    r = await auth_client.post(
        "/admin/tenants",
        json={
            "school_name": "Weak School",
            "school_code": "WEAK-001",
            "subdomain": "weakschool",
            "plan_code": "basic",
            "admin": {"full_name": "A B", "email": "a@weak.school", "password": password},
        },
    )
    assert r.status_code == 422, r.text
    if password != "short1":
        assert "letter and one number" in r.text
