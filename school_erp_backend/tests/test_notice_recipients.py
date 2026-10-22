"""Notices sent to particular people inside an audience."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.seed import (
    DEFAULT_PARENT_PASSWORD,
    DEFAULT_SCHOOL_ADMIN_EMAIL,
    DEFAULT_SCHOOL_ADMIN_PASSWORD,
    DEMO_PARENT_EMAIL,
)


async def _client_for(email: str, password: str) -> AsyncClient:
    ac = AsyncClient(
        transport=ASGITransport(app=app), base_url="http://localhost", headers={"X-Tenant-Subdomain": "demo"}
    )
    r = await ac.post("/v1/auth/login", json={"identifier": email, "password": password, "subdomain": "demo"})
    assert r.status_code == 200, r.text
    ac.headers["Authorization"] = f"Bearer {r.json()['tokens']['access_token']}"
    return ac


@pytest.mark.asyncio
async def test_notice_to_particular_parents(super_admin_token):
    admin = await _client_for(DEFAULT_SCHOOL_ADMIN_EMAIL, DEFAULT_SCHOOL_ADMIN_PASSWORD)
    parent = await _client_for(DEMO_PARENT_EMAIL, DEFAULT_PARENT_PASSWORD)
    try:
        # The picker lists the demo parent (with an app login).
        r = await admin.get("/v1/operations/notices/recipients", params={"audience": "parents"})
        assert r.status_code == 200, r.text
        people = r.json()
        parent_uid = (await parent.get("/v1/auth/me")).json()["id"]
        assert parent_uid in [p["user_id"] for p in people]

        mk = lambda title, ids: admin.post(  # noqa: E731
            "/v1/operations/notices",
            json={"title": title, "body": "b", "audience": "parents", "recipient_user_ids": ids},
        )
        assert (await mk("For everyone", None)).status_code == 201
        assert (await mk("Just this parent", [parent_uid, parent_uid])).status_code == 201
        other = await mk("Someone else", [parent_uid + 100000])
        assert other.status_code == 201
        assert other.json()["recipient_user_ids"] == [parent_uid + 100000]

        feed = (await parent.get("/v1/mobile/notices")).json()
        titles = {n["title"] for n in feed}
        assert {"For everyone", "Just this parent"} <= titles
        assert "Someone else" not in titles

        bad = await admin.post(
            "/v1/operations/notices",
            json={"title": "x", "body": "b", "audience": "parents", "recipient_user_ids": ["abc"]},
        )
        assert bad.status_code == 400
    finally:
        await admin.aclose()
        await parent.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize("audience", ["staff", "students"])
async def test_recipient_picker_lists_people(super_admin_token, audience):
    admin = await _client_for(DEFAULT_SCHOOL_ADMIN_EMAIL, DEFAULT_SCHOOL_ADMIN_PASSWORD)
    try:
        r = await admin.get("/v1/operations/notices/recipients", params={"audience": audience})
        assert r.status_code == 200, r.text
        assert len(r.json()) >= 1
        assert all({"user_id", "name", "detail"} <= set(p) for p in r.json())
    finally:
        await admin.aclose()


@pytest.mark.asyncio
async def test_announcement_to_particular_parents(super_admin_token):
    admin = await _client_for(DEFAULT_SCHOOL_ADMIN_EMAIL, DEFAULT_SCHOOL_ADMIN_PASSWORD)
    parent = await _client_for(DEMO_PARENT_EMAIL, DEFAULT_PARENT_PASSWORD)
    try:
        parent_uid = (await parent.get("/v1/auth/me")).json()["id"]
        post = lambda title, audience, ids: admin.post(  # noqa: E731
            "/v1/school-admin/communication/announcements",
            json={"title": title, "body": "b", "audience": audience, "publish": True,
                  "send_push": False, "recipient_user_ids": ids},
        )

        mine = await post("Just this parent", "parents", [parent_uid])
        assert mine.status_code == 201, mine.text
        assert mine.json()["fanned_out_to"] == 1

        other = await post("Someone else", "parents", [parent_uid + 100000])
        assert other.json()["fanned_out_to"] == 0

        # Everyone: a recipient list makes no sense and is ignored.
        everyone = await post("Everyone", "all", [parent_uid + 100000])
        assert everyone.json()["fanned_out_to"] >= 1

        feed = {a["title"] for a in (await parent.get("/v1/announcements")).json()}
        assert {"Just this parent", "Everyone"} <= feed
        assert "Someone else" not in feed

        inbox = {n["title"] for n in (await parent.get("/v1/notifications")).json()}
        assert "Someone else" not in " ".join(inbox)

        listed = {a["title"]: a for a in (await admin.get("/v1/school-admin/communication/announcements")).json()}
        assert listed["Just this parent"]["recipient_user_ids"] == [parent_uid]
        assert listed["Everyone"]["recipient_user_ids"] is None
    finally:
        await admin.aclose()
        await parent.aclose()
