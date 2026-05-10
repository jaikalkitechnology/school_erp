"""Phase 17 library system tests."""

from datetime import date, timedelta

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
async def book_with_copies(demo_admin_client):
    book = (await demo_admin_client.post(
        "/v1/school-admin/library/books",
        json={
            "title": "Wings of Fire", "author": "A. P. J. Abdul Kalam",
            "isbn": "9788173711466", "category": "biography",
            "default_fine_per_day": 5, "default_loan_days": 7,
        },
    )).json()
    copies = (await demo_admin_client.post(
        f"/v1/school-admin/library/books/{book['id']}/copies/bulk",
        json={"count": 3},
    )).json()
    return {"book": book, "copies": copies}


@pytest.mark.asyncio
async def test_book_create_search_and_duplicate_isbn(demo_admin_client):
    a = await demo_admin_client.post(
        "/v1/school-admin/library/books",
        json={"title": "Sapiens", "isbn": "9780062316097", "category": "non-fiction"},
    )
    assert a.status_code == 201
    dup = await demo_admin_client.post(
        "/v1/school-admin/library/books",
        json={"title": "Sapiens dup", "isbn": "9780062316097"},
    )
    assert dup.status_code == 409

    listing = await demo_admin_client.get(
        "/v1/school-admin/library/books", params={"q": "Sapi"}
    )
    assert any(b["title"] == "Sapiens" for b in listing.json())


@pytest.mark.asyncio
async def test_issue_return_with_fine(demo_admin_client, book_with_copies):
    f = book_with_copies
    student = (await demo_admin_client.post(
        "/v1/school-admin/students",
        json={
            "full_name": "Farah",
            "parent_phone": "+919900000060", "parent_email": "farah@home.test",
            "father_name": "Test Parent",
        },
    )).json()
    copy = f["copies"][0]
    loan = (await demo_admin_client.post(
        "/v1/school-admin/library/issue",
        json={"copy_id": copy["id"], "borrower_kind": "student", "borrower_id": student["id"]},
    )).json()
    assert loan["status"] == "active"

    # Issuing the same copy twice fails (now ISSUED).
    bad = await demo_admin_client.post(
        "/v1/school-admin/library/issue",
        json={"copy_id": copy["id"], "borrower_kind": "student", "borrower_id": student["id"]},
    )
    assert bad.status_code == 400

    # Return 3 days late (5/day -> 15 fine).
    late_return = (date.today() + timedelta(days=10)).isoformat()
    res = await demo_admin_client.post(
        "/v1/school-admin/library/return",
        json={"loan_id": loan["id"], "on_date": late_return, "fine_paid": 15},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] == "returned"
    assert float(body["fine_amount"]) == 15.0
    assert float(body["fine_paid"]) == 15.0


@pytest.mark.asyncio
async def test_overdue_sweep(demo_admin_client, book_with_copies):
    f = book_with_copies
    student = (await demo_admin_client.post(
        "/v1/school-admin/students",
        json={
            "full_name": "Gita", "parent_phone": "+919900000061",
            "parent_email": "gita@home.test", "father_name": "Test Parent",
        },
    )).json()
    loan = (await demo_admin_client.post(
        "/v1/school-admin/library/issue",
        json={
            "copy_id": f["copies"][0]["id"],
            "borrower_kind": "student",
            "borrower_id": student["id"],
            "loan_days": 7,
        },
    )).json()
    # Manually back-date the due_on so the sweep flips it.
    from sqlalchemy import update
    from app.database import AsyncSessionLocal
    from app.models.library import Loan
    async with AsyncSessionLocal() as s:
        await s.execute(update(Loan).where(Loan.id == loan["id"]).values(
            due_on=date.today() - timedelta(days=2)
        ))
        await s.commit()
    sweep = await demo_admin_client.post("/v1/school-admin/library/sweep-overdue")
    assert sweep.json()["marked_overdue"] >= 1

    overdue_list = await demo_admin_client.get(
        "/v1/school-admin/library/loans", params={"status_filter": "overdue"}
    )
    assert any(l["id"] == loan["id"] for l in overdue_list.json())


@pytest.mark.asyncio
async def test_reservations_promote_after_return(demo_admin_client, book_with_copies):
    f = book_with_copies
    book_id = f["book"]["id"]
    s1 = (await demo_admin_client.post(
        "/v1/school-admin/students",
        json={"full_name": "Hari", "parent_phone": "+919900000062",
              "parent_email": "hari@home.test", "father_name": "P"},
    )).json()
    s2 = (await demo_admin_client.post(
        "/v1/school-admin/students",
        json={"full_name": "Ila", "parent_phone": "+919900000063",
              "parent_email": "ila@home.test", "father_name": "P"},
    )).json()

    # Issue out all 3 copies so the next reservation is forced PENDING.
    loans = []
    for c, stu in zip(f["copies"], [s1, s1, s2]):
        loans.append((await demo_admin_client.post(
            "/v1/school-admin/library/issue",
            json={"copy_id": c["id"], "borrower_kind": "student", "borrower_id": stu["id"]},
        )).json())

    res = await demo_admin_client.post(
        "/v1/school-admin/library/reservations",
        json={"book_id": book_id, "borrower_kind": "student", "borrower_id": s2["id"]},
    )
    assert res.status_code == 201
    assert res.json()["status"] == "pending"

    dup = await demo_admin_client.post(
        "/v1/school-admin/library/reservations",
        json={"book_id": book_id, "borrower_kind": "student", "borrower_id": s2["id"]},
    )
    assert dup.status_code == 409

    # Return a copy → first PENDING reservation flips to READY.
    await demo_admin_client.post(
        "/v1/school-admin/library/return",
        json={"loan_id": loans[0]["id"]},
    )
    listing = (await demo_admin_client.get(
        "/v1/school-admin/library/reservations",
        params={"status_filter": "ready"},
    )).json()
    assert any(r["id"] == res.json()["id"] for r in listing)


@pytest.mark.asyncio
async def test_reports_and_parent_view(demo_admin_client, book_with_copies):
    f = book_with_copies
    student = (await demo_admin_client.post(
        "/v1/school-admin/students",
        json={"full_name": "Jaya", "parent_phone": "+919900000064",
              "parent_email": "jaya@home.test", "father_name": "P"},
    )).json()
    await demo_admin_client.post(
        "/v1/school-admin/library/issue",
        json={"copy_id": f["copies"][0]["id"], "borrower_kind": "student",
              "borrower_id": student["id"]},
    )

    rep = (await demo_admin_client.get("/v1/school-admin/library/reports")).json()
    assert rep["total_books"] >= 1
    assert rep["issued"] >= 1
    assert rep["available"] >= 1

    # Parent of Jaya can see her book; not other kids.
    await demo_admin_client.post(
        "/v1/auth/reset-password",
        json={"identifier": "jaya@home.test", "subdomain": "demo",
              "otp": "1234", "new_password": "Parent@123"},
    )
    parent_token = await _login("demo", "jaya@home.test", "Parent@123")
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
        headers={"Authorization": f"Bearer {parent_token}", "X-Tenant-Subdomain": "demo"},
    ) as parent_ac:
        ok = await parent_ac.get(f"/v1/parent/children/{student['id']}/library")
        assert ok.status_code == 200
        rows = ok.json()["rows"]
        assert any(r["book_title"] == "Wings of Fire" for r in rows)


@pytest.mark.asyncio
async def test_super_admin_blocked(super_admin_token):
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    ) as ac:
        r = await ac.get("/v1/school-admin/library/books")
        assert r.status_code == 403
