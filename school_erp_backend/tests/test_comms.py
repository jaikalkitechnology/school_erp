"""Phase 12 communication tests."""

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
async def class_with_parent(demo_admin_client):
    cls = (await demo_admin_client.post(
        "/v1/school-admin/classes",
        json={"code": "5", "name": "Class 5", "stage": "primary", "sequence": 5},
    )).json()
    sec = (await demo_admin_client.post(
        "/v1/school-admin/sections",
        json={"class_def_id": cls["id"], "name": "A"},
    )).json()
    student = (await demo_admin_client.post(
        "/v1/school-admin/students",
        json={
            "full_name": "Aarav", "class_def_id": cls["id"], "section_id": sec["id"],
            "parent_phone": "+919900000020", "parent_email": "parent@home.test",
            "father_name": "Ravi",
        },
    )).json()
    rp = await demo_admin_client.post(
        "/v1/auth/reset-password",
        json={
            "identifier": "parent@home.test", "subdomain": "demo",
            "otp": "1234", "new_password": "Parent@123",
        },
    )
    assert rp.status_code == 204
    return cls, sec, student


@pytest.mark.asyncio
async def test_default_templates_seeded(demo_admin_client):
    r = await demo_admin_client.get("/v1/school-admin/communication/templates")
    assert r.status_code == 200
    codes = {t["code"] for t in r.json()}
    assert {"leave.decided", "announcement.posted", "fee.collected"}.issubset(codes)


@pytest.mark.asyncio
async def test_announcement_publish_fans_out_to_parents(
    demo_admin_client, class_with_parent
):
    r = await demo_admin_client.post(
        "/v1/school-admin/communication/announcements",
        json={
            "title": "Sports day on Friday",
            "body": "All parents please send sports kit.",
            "audience": "parents",
            "publish": True,
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    # The auto-created parent counts as a recipient.
    assert body["fanned_out_to"] >= 1

    # Parent sees it in their notifications.
    parent_token = await _login("demo", "parent@home.test", "Parent@123")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
        headers={"Authorization": f"Bearer {parent_token}", "X-Tenant-Subdomain": "demo"},
    ) as ac:
        notifs = await ac.get("/v1/notifications")
        assert notifs.status_code == 200
        titles = [n["title"] for n in notifs.json()]
        assert "Sports day on Friday" in titles


@pytest.mark.asyncio
async def test_section_audience_only_targets_linked_parents(
    demo_admin_client, class_with_parent
):
    cls, sec, _ = class_with_parent
    # Add a second class + student NOT linked to parent@home.test.
    other_cls = (await demo_admin_client.post(
        "/v1/school-admin/classes",
        json={"code": "6", "name": "Class 6", "stage": "middle", "sequence": 6},
    )).json()
    other_sec = (await demo_admin_client.post(
        "/v1/school-admin/sections",
        json={"class_def_id": other_cls["id"], "name": "A"},
    )).json()
    await demo_admin_client.post(
        "/v1/school-admin/students",
        json={
            "full_name": "Stranger", "class_def_id": other_cls["id"], "section_id": other_sec["id"],
            "parent_phone": "+919900099999",
        },
    )

    # Announce only to the other section's audience.
    r = await demo_admin_client.post(
        "/v1/school-admin/communication/announcements",
        json={
            "title": "Class 6 only",
            "body": "Only Class 6 parents see this.",
            "audience": "section",
            "audience_id": other_sec["id"],
            "publish": True,
        },
    )
    assert r.status_code == 201

    parent_token = await _login("demo", "parent@home.test", "Parent@123")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
        headers={"Authorization": f"Bearer {parent_token}", "X-Tenant-Subdomain": "demo"},
    ) as ac:
        notifs = await ac.get("/v1/notifications")
        titles = [n["title"] for n in notifs.json()]
        assert "Class 6 only" not in titles


@pytest.mark.asyncio
async def test_leave_decision_notifies_parent(demo_admin_client, class_with_parent):
    _, _, student = class_with_parent
    parent_token = await _login("demo", "parent@home.test", "Parent@123")

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
        headers={"Authorization": f"Bearer {parent_token}", "X-Tenant-Subdomain": "demo"},
    ) as parent_ac:
        leave = await parent_ac.post(
            "/v1/parent/leave-applications",
            json={
                "student_id": student["id"],
                "start_date": "2025-09-01", "end_date": "2025-09-02",
                "reason": "Family event",
            },
        )
        assert leave.status_code == 201
        leave_id = leave.json()["id"]

    decide = await demo_admin_client.post(
        f"/v1/school-admin/leave-applications/{leave_id}/decide",
        json={"decision": "approved", "decision_remarks": "Granted"},
    )
    assert decide.status_code == 200

    # Parent receives the notification.
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
        headers={"Authorization": f"Bearer {parent_token}", "X-Tenant-Subdomain": "demo"},
    ) as parent_ac:
        notifs = await parent_ac.get("/v1/notifications")
        rows = notifs.json()
        leave_notif = next((n for n in rows if n["kind"] == "leave"), None)
        assert leave_notif is not None
        assert "approved" in leave_notif["title"].lower()
        assert leave_notif["read_at"] is None

        # Mark read.
        marked = await parent_ac.post(f"/v1/notifications/{leave_notif['id']}/read")
        assert marked.status_code == 200
        assert marked.json()["read_at"] is not None


@pytest.mark.asyncio
async def test_direct_message_round_trip(demo_admin_client, class_with_parent):
    # Find admin user id (the demo school admin).
    me = await demo_admin_client.get("/v1/auth/me")
    admin_user_id = me.json()["id"]
    # Find parent user_id.
    _, _, student = class_with_parent
    parents = await demo_admin_client.get(
        f"/v1/school-admin/students/{student['id']}/parents"
    )
    parent_user_id = parents.json()[0]["parent_user_id"]

    parent_token = await _login("demo", "parent@home.test", "Parent@123")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
        headers={"Authorization": f"Bearer {parent_token}", "X-Tenant-Subdomain": "demo"},
    ) as parent_ac:
        sent = await parent_ac.post(
            "/v1/messages",
            json={
                "recipient_user_id": admin_user_id,
                "subject": "Question about fee",
                "body": "Could you clarify the August invoice?",
            },
        )
        assert sent.status_code == 201

    inbox = await demo_admin_client.get("/v1/messages")
    bodies = [m["body"] for m in inbox.json()]
    assert any("August invoice" in b for b in bodies)


@pytest.mark.asyncio
async def test_outbox_records_external_channels(demo_admin_client, class_with_parent):
    # Tweak a template so the next event also queues SMS.
    await demo_admin_client.put(
        "/v1/school-admin/communication/templates/leave.decided",
        json={
            "code": "leave.decided",
            "subject_en": "Leave {{decision}}",
            "body_en": "{{student}} {{decision}}",
            "channels": ["in_app", "sms"],
        },
    )
    _, _, student = class_with_parent
    parent_token = await _login("demo", "parent@home.test", "Parent@123")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
        headers={"Authorization": f"Bearer {parent_token}", "X-Tenant-Subdomain": "demo"},
    ) as parent_ac:
        leave = await parent_ac.post(
            "/v1/parent/leave-applications",
            json={
                "student_id": student["id"],
                "start_date": "2025-09-15", "end_date": "2025-09-15",
                "reason": "Doctor",
            },
        )
        leave_id = leave.json()["id"]

    await demo_admin_client.post(
        f"/v1/school-admin/leave-applications/{leave_id}/decide",
        json={"decision": "rejected", "decision_remarks": "Critical school day"},
    )

    outbox = await demo_admin_client.get("/v1/school-admin/communication/outbox")
    sms_rows = [r for r in outbox.json() if r["channel"] == "sms"]
    assert sms_rows, "Expected at least one SMS row in the outbox"
    # Parent has a phone, so it should be queued (not skipped).
    assert any(r["status"] == "queued" for r in sms_rows)


@pytest.mark.asyncio
async def test_mark_all_notifications_read(demo_admin_client, class_with_parent):
    # Trigger a couple of notifications first.
    await demo_admin_client.post(
        "/v1/school-admin/communication/announcements",
        json={"title": "A1", "body": "x", "audience": "parents", "publish": True},
    )
    await demo_admin_client.post(
        "/v1/school-admin/communication/announcements",
        json={"title": "A2", "body": "x", "audience": "parents", "publish": True},
    )
    parent_token = await _login("demo", "parent@home.test", "Parent@123")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
        headers={"Authorization": f"Bearer {parent_token}", "X-Tenant-Subdomain": "demo"},
    ) as parent_ac:
        unread = await parent_ac.get("/v1/notifications", params={"only_unread": True})
        assert len(unread.json()) >= 2
        clear = await parent_ac.post("/v1/notifications/read-all")
        assert clear.status_code == 200
        assert clear.json()["marked"] >= 2
        leftover = await parent_ac.get("/v1/notifications", params={"only_unread": True})
        assert leftover.json() == []


@pytest.mark.asyncio
async def test_publish_reports_why_push_did_not_go_out(demo_admin_client):
    """With FCM off (no service-account JSON in tests) the publish result
    must say so, instead of looking like "no phones registered"."""
    status = await demo_admin_client.get("/v1/school-admin/communication/push-status")
    assert status.status_code == 200, status.text
    assert status.json()["available"] is False
    assert "not found" in status.json()["reason"]
    assert status.json()["active_devices"] == 0

    r = await demo_admin_client.post(
        "/v1/school-admin/communication/announcements",
        json={"title": "Push check", "body": "Hello", "audience": "parents", "publish": True, "send_push": True},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["push_sent"] == 0
    assert body["push_skipped"] >= 1
    assert body["push_unavailable_reason"]


@pytest.mark.asyncio
async def test_clear_and_delete_own_notifications(demo_admin_client):
    for i in range(3):
        r = await demo_admin_client.post(
            "/v1/school-admin/communication/announcements",
            json={"title": f"Note {i}", "body": "x", "audience": "staff", "publish": True, "send_push": False},
        )
        assert r.status_code == 201, r.text
    mine = (await demo_admin_client.get("/v1/notifications")).json()
    assert len(mine) >= 3

    # Delete one.
    r = await demo_admin_client.delete(f"/v1/notifications/{mine[0]['id']}")
    assert r.status_code == 204
    after = (await demo_admin_client.get("/v1/notifications")).json()
    assert mine[0]["id"] not in [n["id"] for n in after]
    assert (await demo_admin_client.delete(f"/v1/notifications/{mine[0]['id']}")).status_code == 404

    # Clear the rest.
    r = await demo_admin_client.delete("/v1/notifications")
    assert r.status_code == 200 and r.json()["cleared"] == len(after)
    assert (await demo_admin_client.get("/v1/notifications")).json() == []
