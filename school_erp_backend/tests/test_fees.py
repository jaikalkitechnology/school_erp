"""Phase 11 fee management tests."""

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
async def class_with_two_students(demo_admin_client):
    cls = (await demo_admin_client.post(
        "/v1/school-admin/classes",
        json={"code": "5", "name": "Class 5", "stage": "primary", "sequence": 5},
    )).json()
    sec = (await demo_admin_client.post(
        "/v1/school-admin/sections",
        json={"class_def_id": cls["id"], "name": "A"},
    )).json()
    a = (await demo_admin_client.post(
        "/v1/school-admin/students",
        json={
            "full_name": "Aarav", "class_def_id": cls["id"], "section_id": sec["id"],
            "parent_phone": "+919900000010", "parent_email": "ravi@home.test",
            "father_name": "Ravi",
        },
    )).json()
    b = (await demo_admin_client.post(
        "/v1/school-admin/students",
        json={
            "full_name": "Aanya", "class_def_id": cls["id"], "section_id": sec["id"],
            "parent_phone": "+919900000010", "parent_email": "ravi@home.test",
            "father_name": "Ravi",
        },
    )).json()
    return cls, sec, a, b


async def _make_tuition_structure(client, class_def_id: int, amount: int = 1000) -> tuple[int, int]:
    cat = (await client.post(
        "/v1/school-admin/fees/categories",
        json={"code": "TUI", "name": "Tuition", "is_recurring": True},
    )).json()
    structure = (await client.post(
        "/v1/school-admin/fees/structures",
        json={
            "class_def_id": class_def_id, "category_id": cat["id"],
            "period": "monthly", "amount": amount, "due_day_of_month": 10,
            "late_fee_per_day": 0, "grace_days": 5,
        },
    )).json()
    return cat["id"], structure["id"]


@pytest.mark.asyncio
async def test_category_and_structure_crud(demo_admin_client, class_with_two_students):
    cls, *_ = class_with_two_students
    cat_id, struct_id = await _make_tuition_structure(demo_admin_client, cls["id"])
    listing = await demo_admin_client.get("/v1/school-admin/fees/categories")
    assert any(c["id"] == cat_id for c in listing.json())

    # Duplicate (class, category, period) is rejected.
    dup = await demo_admin_client.post(
        "/v1/school-admin/fees/structures",
        json={
            "class_def_id": cls["id"], "category_id": cat_id,
            "period": "monthly", "amount": 2000,
        },
    )
    assert dup.status_code == 409


@pytest.mark.asyncio
async def test_generate_invoices_applies_sibling_discount(
    demo_admin_client, class_with_two_students
):
    cls, _, a, b = class_with_two_students
    _, struct_id = await _make_tuition_structure(demo_admin_client, cls["id"], amount=1000)

    r = await demo_admin_client.post(
        f"/v1/school-admin/fees/structures/{struct_id}/generate",
        json={
            "period_start": "2025-08-01",
            "period_end": "2025-08-31",
            "sibling_discount_pct": 10,
            "apply_sibling_discount": True,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["created"] == 2
    assert body["skipped"] == 0

    # Replay is idempotent.
    again = await demo_admin_client.post(
        f"/v1/school-admin/fees/structures/{struct_id}/generate",
        json={
            "period_start": "2025-08-01", "period_end": "2025-08-31",
            "sibling_discount_pct": 10,
        },
    )
    assert again.json() == {"created": 0, "skipped": 2, "structure_id": struct_id}

    # Sibling discount: 10% of 1000 = 100, total 900.
    a_view = await demo_admin_client.get(f"/v1/school-admin/fees/students/{a['id']}")
    assert a_view.status_code == 200
    inv = a_view.json()["invoices"][0]
    assert float(inv["discount_amount"]) == 100.0
    assert float(inv["total_amount"]) == 900.0


@pytest.mark.asyncio
async def test_collect_payment_marks_invoice_paid(demo_admin_client, class_with_two_students):
    cls, _, a, _ = class_with_two_students
    _, struct_id = await _make_tuition_structure(demo_admin_client, cls["id"], amount=500)
    await demo_admin_client.post(
        f"/v1/school-admin/fees/structures/{struct_id}/generate",
        json={
            "period_start": "2025-08-01", "period_end": "2025-08-31",
            "apply_sibling_discount": False,
        },
    )
    fees = (await demo_admin_client.get(f"/v1/school-admin/fees/students/{a['id']}")).json()
    invoice_id = fees["invoices"][0]["id"]

    r = await demo_admin_client.post(
        "/v1/school-admin/fees/collect",
        json={"invoice_id": invoice_id, "amount": 500, "method": "cash"},
    )
    assert r.status_code == 201, r.text

    fees_after = (await demo_admin_client.get(f"/v1/school-admin/fees/students/{a['id']}")).json()
    assert fees_after["invoices"][0]["status"] == "paid"
    assert float(fees_after["total_due"]) == 0


@pytest.mark.asyncio
async def test_partial_payment_then_final(demo_admin_client, class_with_two_students):
    cls, _, a, _ = class_with_two_students
    _, struct_id = await _make_tuition_structure(demo_admin_client, cls["id"], amount=1000)
    await demo_admin_client.post(
        f"/v1/school-admin/fees/structures/{struct_id}/generate",
        json={
            "period_start": "2025-08-01", "period_end": "2025-08-31",
            "apply_sibling_discount": False,
        },
    )
    invoice_id = (await demo_admin_client.get(
        f"/v1/school-admin/fees/students/{a['id']}"
    )).json()["invoices"][0]["id"]

    # Partial.
    await demo_admin_client.post(
        "/v1/school-admin/fees/collect",
        json={"invoice_id": invoice_id, "amount": 400, "method": "cash"},
    )
    p1 = (await demo_admin_client.get(f"/v1/school-admin/fees/students/{a['id']}")).json()
    assert p1["invoices"][0]["status"] == "partial"

    # Overpay rejected.
    over = await demo_admin_client.post(
        "/v1/school-admin/fees/collect",
        json={"invoice_id": invoice_id, "amount": 1000, "method": "cash"},
    )
    assert over.status_code == 400

    # Settle the rest.
    await demo_admin_client.post(
        "/v1/school-admin/fees/collect",
        json={"invoice_id": invoice_id, "amount": 600, "method": "upi"},
    )
    p2 = (await demo_admin_client.get(f"/v1/school-admin/fees/students/{a['id']}")).json()
    assert p2["invoices"][0]["status"] == "paid"


@pytest.mark.asyncio
async def test_online_payment_signature_check(demo_admin_client, class_with_two_students):
    """Initiate + confirm with proper Razorpay-style HMAC."""
    import hashlib
    import hmac

    cls, _, a, _ = class_with_two_students
    _, struct_id = await _make_tuition_structure(demo_admin_client, cls["id"], amount=300)
    await demo_admin_client.post(
        f"/v1/school-admin/fees/structures/{struct_id}/generate",
        json={
            "period_start": "2025-08-01", "period_end": "2025-08-31",
            "apply_sibling_discount": False,
        },
    )
    invoice_id = (await demo_admin_client.get(
        f"/v1/school-admin/fees/students/{a['id']}"
    )).json()["invoices"][0]["id"]

    # Auto-link parent on admit + reset their password.
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
        init = await ac.post(
            "/v1/parent/payments/initiate",
            json={"invoice_id": invoice_id},
        )
        assert init.status_code == 200, init.text
        order_id = init.json()["order_id"]

        bad = await ac.post(
            "/v1/parent/payments/confirm",
            json={
                "order_id": order_id,
                "razorpay_payment_id": "pay_abc",
                "razorpay_signature": "deadbeef",
            },
        )
        assert bad.status_code == 400

        from app.config import settings

        secret = settings.RAZORPAY_KEY_SECRET or "phase11-stub-secret"
        sig = hmac.new(
            secret.encode(), f"{order_id}|pay_abc".encode(), hashlib.sha256
        ).hexdigest()
        ok = await ac.post(
            "/v1/parent/payments/confirm",
            json={
                "order_id": order_id,
                "razorpay_payment_id": "pay_abc",
                "razorpay_signature": sig,
            },
        )
        assert ok.status_code == 200
        assert ok.json()["status"] == "success"

    # Invoice now reflects paid amount.
    after = (await demo_admin_client.get(f"/v1/school-admin/fees/students/{a['id']}")).json()
    assert after["invoices"][0]["status"] == "paid"


@pytest.mark.asyncio
async def test_collection_summary_and_defaulters(demo_admin_client, class_with_two_students):
    cls, _, a, b = class_with_two_students
    _, struct_id = await _make_tuition_structure(demo_admin_client, cls["id"], amount=500)
    # Past due: period_start 2024-01-01, due 10th Jan 2024.
    await demo_admin_client.post(
        f"/v1/school-admin/fees/structures/{struct_id}/generate",
        json={
            "period_start": "2024-01-01", "period_end": "2024-01-31",
            "apply_sibling_discount": False,
        },
    )
    fees_a = (await demo_admin_client.get(f"/v1/school-admin/fees/students/{a['id']}")).json()
    invoice_id = fees_a["invoices"][0]["id"]
    # Pay only Aarav's, leave Aanya as defaulter.
    await demo_admin_client.post(
        "/v1/school-admin/fees/collect",
        json={"invoice_id": invoice_id, "amount": 500, "method": "cash"},
    )

    today = "2099-01-01"  # any future date covers the payment range.
    summary = await demo_admin_client.get(
        "/v1/school-admin/fees/reports/collection",
        params={"start": "2020-01-01", "end": today},
    )
    assert summary.status_code == 200
    body = summary.json()
    assert float(body["total_collected"]) == 500.0

    defaulters = await demo_admin_client.get("/v1/school-admin/fees/reports/defaulters")
    assert defaulters.status_code == 200
    assert any(d["student_id"] == b["id"] for d in defaulters.json())


@pytest.mark.asyncio
async def test_parent_dashboard_includes_fee_due(demo_admin_client, class_with_two_students):
    cls, _, a, _ = class_with_two_students
    _, struct_id = await _make_tuition_structure(demo_admin_client, cls["id"], amount=750)
    await demo_admin_client.post(
        f"/v1/school-admin/fees/structures/{struct_id}/generate",
        json={
            "period_start": "2025-08-01", "period_end": "2025-08-31",
            "apply_sibling_discount": True, "sibling_discount_pct": 10,
        },
    )
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
        dash = await ac.get(f"/v1/parent/dashboard/{a['id']}")
        assert dash.status_code == 200
        # 10% sibling discount on 750 = 75, total due 675.
        assert dash.json()["fee_due_amount"] == 675.0


@pytest.mark.asyncio
async def test_parent_cannot_view_other_kid_fees(demo_admin_client, class_with_two_students):
    cls, _, _, _ = class_with_two_students
    other_cls = (await demo_admin_client.post(
        "/v1/school-admin/classes",
        json={"code": "6", "name": "Class 6", "stage": "middle", "sequence": 6},
    )).json()
    other = (await demo_admin_client.post(
        "/v1/school-admin/students",
        json={
            "full_name": "Stranger", "class_def_id": other_cls["id"],
            "parent_phone": "+919900099999",
        },
    )).json()
    _, struct_id = await _make_tuition_structure(demo_admin_client, other_cls["id"])
    await demo_admin_client.post(
        f"/v1/school-admin/fees/structures/{struct_id}/generate",
        json={
            "period_start": "2025-08-01", "period_end": "2025-08-31",
            "apply_sibling_discount": False,
        },
    )
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
        forbidden = await ac.get(f"/v1/parent/children/{other['id']}/fees")
        assert forbidden.status_code == 403
