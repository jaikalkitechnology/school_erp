"""Library endpoints (Phase 17)."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import AuthPrincipal, require_roles
from app.core.tenant_session import platform_session, tenant_scoped_session
from app.models.library import BorrowerKind
from app.models.parent import Parent, ParentChildMapping
from app.schemas.library import (
    BookRead,
    BookWithStock,
    BookWrite,
    CopyBulkAdd,
    CopyRead,
    CopyWrite,
    IssueRequest,
    LibraryReports,
    LoanRead,
    ParentLibrary,
    ParentLibraryRow,
    ReservationRead,
    ReservationWrite,
    ReturnRequest,
)
from app.services.library import (
    add_copies_bulk,
    add_copy,
    book_stock,
    cancel_reservation,
    create_book,
    create_reservation,
    delete_book,
    issue_loan,
    list_books,
    list_copies,
    list_loans,
    list_reservations,
    mark_overdue,
    parent_child_loans,
    reports,
    return_loan,
    update_book,
)


_school_admin = require_roles("school_admin", "principal", "vice_principal")
_librarian = require_roles(
    "school_admin", "principal", "vice_principal", "librarian", "coordinator",
)
_reader = require_roles(
    "school_admin", "principal", "vice_principal", "librarian", "coordinator",
    "class_teacher", "subject_teacher",
)
_parent = require_roles("parent")


router = APIRouter(
    prefix="/school-admin/library",
    tags=["school-admin"],
    dependencies=[Depends(_reader)],
)


# ---- Books -----------------------------------------------------------------


@router.get("/books", response_model=list[BookWithStock])
async def list_books_route(
    q: Optional[str] = None,
    category: Optional[str] = None,
    session: AsyncSession = Depends(tenant_scoped_session),
):
    books = await list_books(session, q=q, category=category)
    stocks = await book_stock(session, [b.id for b in books])
    return [
        {
            **{c.name: getattr(b, c.name) for c in b.__table__.columns},
            "total_copies": stocks.get(b.id, {}).get("total", 0),
            "available_copies": stocks.get(b.id, {}).get("available", 0),
        }
        for b in books
    ]


@router.post("/books", response_model=BookRead, status_code=status.HTTP_201_CREATED)
async def create_book_route(
    payload: BookWrite,
    principal: AuthPrincipal = Depends(_librarian),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await create_book(session, principal.tenant_id, payload)


@router.patch("/books/{book_id}", response_model=BookRead)
async def update_book_route(
    book_id: int,
    payload: BookWrite,
    principal: AuthPrincipal = Depends(_librarian),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await update_book(session, book_id, payload)


@router.delete("/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_book_route(
    book_id: int,
    principal: AuthPrincipal = Depends(_librarian),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    """Delete a book from the catalogue. The service blocks the
    delete if any copy is still on active loan — so no data-loss
    risk when the librarian mis-clicks. School admins used to be
    required; librarians run the day-to-day catalogue so they now
    own it too."""
    await delete_book(session, book_id)


# ---- Categories (free-text on Book.category) -------------------------------


@router.post("/categories/rename")
async def rename_category_route(
    payload: dict,
    principal: AuthPrincipal = Depends(_librarian),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    """Rename a category across every book that currently carries
    it. Payload: ``{"from": "Sci-Fi", "to": "Science Fiction"}``.

    Categories aren't a first-class table — they're a free-text
    string on ``Book.category``. Rename = bulk UPDATE. The response
    reports how many books were touched so the librarian sees the
    scope of the change."""
    from app.models.library import Book

    source = (payload.get("from") or "").strip()
    target = (payload.get("to") or "").strip()
    if not source or not target:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Both 'from' and 'to' are required",
        )
    if source == target:
        return {"updated": 0}

    books = list(
        (
            await session.execute(
                select(Book).where(Book.category == source)
            )
        ).scalars().all()
    )
    for b in books:
        b.category = target
    await session.commit()
    return {"updated": len(books), "from": source, "to": target}


@router.delete("/categories/{name}", status_code=status.HTTP_200_OK)
async def delete_category_route(
    name: str,
    principal: AuthPrincipal = Depends(_librarian),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    """Delete a category by clearing it off every book that carries
    it (books survive; they just become "Uncategorised"). Returns
    the count of books touched."""
    from app.models.library import Book

    name = (name or "").strip()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category name required",
        )
    books = list(
        (
            await session.execute(
                select(Book).where(Book.category == name)
            )
        ).scalars().all()
    )
    for b in books:
        b.category = None
    await session.commit()
    return {"cleared": len(books), "category": name}


# ---- Authors + Publishers (free-text on Book) ----------------------------


@router.get("/authors")
async def list_authors_route(
    session: AsyncSession = Depends(tenant_scoped_session),
):
    """Distinct set of authors used across every book. Same pattern
    as ``/reports.by_category`` — we treat free-text authors as
    first-class entities in the UI."""
    from app.models.library import Book

    from sqlalchemy import func as _func

    rows = (
        await session.execute(
            select(Book.author, _func.count(Book.id))
            .where(Book.author.isnot(None))
            .group_by(Book.author)
            .order_by(Book.author)
        )
    ).all()
    return [{"author": name, "books": int(count)} for name, count in rows]


@router.post("/authors/rename")
async def rename_author_route(
    payload: dict,
    principal: AuthPrincipal = Depends(_librarian),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    from app.models.library import Book

    src = (payload.get("from") or "").strip()
    tgt = (payload.get("to") or "").strip()
    if not src or not tgt:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Both 'from' and 'to' are required")
    if src == tgt:
        return {"updated": 0}
    books = list(
        (await session.execute(select(Book).where(Book.author == src)))
        .scalars().all()
    )
    for b in books:
        b.author = tgt
    await session.commit()
    return {"updated": len(books), "from": src, "to": tgt}


@router.delete("/authors/{name}")
async def delete_author_route(
    name: str,
    principal: AuthPrincipal = Depends(_librarian),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    from app.models.library import Book

    name = (name or "").strip()
    books = list(
        (await session.execute(select(Book).where(Book.author == name)))
        .scalars().all()
    )
    for b in books:
        b.author = None
    await session.commit()
    return {"cleared": len(books), "author": name}


@router.get("/publishers")
async def list_publishers_route(
    session: AsyncSession = Depends(tenant_scoped_session),
):
    """Distinct set of publishers used across every book."""
    from app.models.library import Book

    from sqlalchemy import func as _func

    rows = (
        await session.execute(
            select(Book.publisher, _func.count(Book.id))
            .where(Book.publisher.isnot(None))
            .group_by(Book.publisher)
            .order_by(Book.publisher)
        )
    ).all()
    return [{"publisher": name, "books": int(count)} for name, count in rows]


@router.post("/publishers/rename")
async def rename_publisher_route(
    payload: dict,
    principal: AuthPrincipal = Depends(_librarian),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    from app.models.library import Book

    src = (payload.get("from") or "").strip()
    tgt = (payload.get("to") or "").strip()
    if not src or not tgt:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Both 'from' and 'to' are required")
    if src == tgt:
        return {"updated": 0}
    books = list(
        (await session.execute(select(Book).where(Book.publisher == src)))
        .scalars().all()
    )
    for b in books:
        b.publisher = tgt
    await session.commit()
    return {"updated": len(books), "from": src, "to": tgt}


@router.delete("/publishers/{name}")
async def delete_publisher_route(
    name: str,
    principal: AuthPrincipal = Depends(_librarian),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    from app.models.library import Book

    name = (name or "").strip()
    books = list(
        (await session.execute(select(Book).where(Book.publisher == name)))
        .scalars().all()
    )
    for b in books:
        b.publisher = None
    await session.commit()
    return {"cleared": len(books), "publisher": name}


# ---- Notification templates (library.* only) -----------------------------


@router.get("/notification-templates")
async def list_library_templates_route(
    session: AsyncSession = Depends(tenant_scoped_session),
):
    """List every library.* NotificationTemplate for the tenant so
    the LibraryNotificationsPage can render + edit them. Rows are
    seeded at boot by ``seed_library_templates`` so this endpoint
    always returns the full set."""
    from app.models.comms import NotificationTemplate
    from app.services.library_notifications import LIBRARY_TEMPLATES

    codes = [t["code"] for t in LIBRARY_TEMPLATES]
    rows = list(
        (
            await session.execute(
                select(NotificationTemplate)
                .where(NotificationTemplate.code.in_(codes))
                .order_by(NotificationTemplate.code)
            )
        ).scalars().all()
    )
    order = {c: i for i, c in enumerate(codes)}
    rows.sort(key=lambda r: order.get(r.code, 99))
    return [
        {
            "code": r.code,
            "subject_en": r.subject_en,
            "body_en": r.body_en,
            "channels": list(r.channels or []),
            "is_active": r.is_active,
        }
        for r in rows
    ]


@router.get("/notifications/diagnostics")
async def notification_diagnostics_route(
    borrower_kind: Optional[str] = None,
    borrower_id: Optional[int] = None,
    principal: AuthPrincipal = Depends(_librarian),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    """One-shot health check for the library notification pipeline.

    Answers, in a single request:
      1. Are all 5 library.* templates seeded for this tenant?
      2. If a borrower is given, which User rows would be notified?
      3. How many active FCM tokens (user_devices rows) do they have?
      4. What's in the notification_outbox for those users in the
         last 15 minutes?

    Pass ``?borrower_kind=student&borrower_id=<id>`` to include the
    per-recipient breakdown. Without params you still get the
    template-seed status."""
    from datetime import datetime, timedelta

    from app.models.auth_extras import UserDevice
    from app.models.comms import NotificationOutbox, NotificationTemplate
    from app.services.library_notifications import (
        LIBRARY_TEMPLATES, borrower_users,
    )

    known_codes = [t["code"] for t in LIBRARY_TEMPLATES]
    rows = list(
        (
            await session.execute(
                select(NotificationTemplate)
                .where(NotificationTemplate.code.in_(known_codes))
            )
        ).scalars().all()
    )
    template_status = {
        t["code"]: {"seeded": False, "active": False, "channels": []}
        for t in LIBRARY_TEMPLATES
    }
    for r in rows:
        template_status[r.code] = {
            "seeded": True,
            "active": bool(r.is_active),
            "channels": list(r.channels or []),
        }

    result: dict = {
        "tenant_id": principal.tenant_id,
        "templates_seeded": len(rows),
        "templates_expected": len(known_codes),
        "templates": template_status,
    }

    if borrower_kind and borrower_id:
        recipients = await borrower_users(session, borrower_kind, int(borrower_id))
        recipient_ids = [u.id for u in recipients]
        recipient_summary = [
            {
                "user_id": u.id,
                "name": u.full_name,
                "email": u.email,
                "phone": u.phone,
                "is_active": bool(u.is_active),
            }
            for u in recipients
        ]

        device_counts: dict[int, int] = {}
        if recipient_ids:
            device_rows = list(
                (
                    await session.execute(
                        select(UserDevice.user_id).where(
                            UserDevice.user_id.in_(recipient_ids),
                            UserDevice.is_active.is_(True),
                        )
                    )
                ).all()
            )
            for (uid,) in device_rows:
                device_counts[uid] = device_counts.get(uid, 0) + 1
        for r in recipient_summary:
            r["active_devices"] = device_counts.get(r["user_id"], 0)

        since = datetime.utcnow() - timedelta(minutes=15)
        outbox_rows: list[dict] = []
        if recipient_ids:
            rows_ob = list(
                (
                    await session.execute(
                        select(NotificationOutbox)
                        .where(
                            NotificationOutbox.recipient_user_id.in_(recipient_ids),
                            NotificationOutbox.created_at >= since,
                        )
                        .order_by(NotificationOutbox.id.desc())
                        .limit(30)
                    )
                ).scalars().all()
            )
            outbox_rows = [
                {
                    "id": r.id,
                    "recipient_user_id": r.recipient_user_id,
                    "channel": r.channel,
                    "status": r.status,
                    "subject": r.subject,
                    "error": r.error,
                    "created_at": (
                        r.created_at.isoformat() if r.created_at else None
                    ),
                }
                for r in rows_ob
            ]

        result["borrower"] = {
            "kind": borrower_kind,
            "id": int(borrower_id),
            "recipient_count": len(recipient_summary),
            "recipients": recipient_summary,
            "recent_outbox_rows": outbox_rows,
        }
    return result


@router.post("/notifications/test-send")
async def notification_test_send_route(
    payload: dict,
    principal: AuthPrincipal = Depends(_librarian),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    """Fire the ``library.issued`` template at a specified borrower
    without actually issuing a book. Use this to prove the whole
    pipeline works end-to-end from the browser: pick a real
    borrower, click send, watch their phone (and check
    notification_outbox afterwards).

    Payload: ``{"borrower_kind": "student", "borrower_id": 42}``.
    """
    from app.services.library_notifications import (
        _borrower_name, borrower_users,
    )
    from app.services.comms import notify
    from app.services.push_dispatch import drain_pending_push_outbox_ids

    borrower_kind = str(payload.get("borrower_kind") or "").strip()
    try:
        borrower_id = int(payload.get("borrower_id"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="borrower_id required")
    if borrower_kind not in {"student", "teacher"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="borrower_kind must be 'student' or 'teacher'")

    recipients = await borrower_users(session, borrower_kind, borrower_id)
    if not recipients:
        return {
            "ok": False,
            "reason": "No linked user accounts for this borrower — "
                      "neither the student's own login nor any parent login "
                      "is on record. Nothing to send.",
            "recipient_count": 0,
        }

    borrower_name = await _borrower_name(session, borrower_kind, borrower_id)
    n_created, push_outbox_ids = await notify(
        session,
        tenant_id=principal.tenant_id,
        template_code="library.issued",
        recipients=recipients,
        context={
            "borrower": borrower_name,
            "title": "TEST BOOK (diagnostic)",
            "due": "2099-01-01",
            "fine": "0",
            "fine_per_day": "0",
        },
        deeplink="/library",
        source_type="library_test",
        source_id=0,
        kind="library",
    )
    push_result = None
    if push_outbox_ids:
        r = await drain_pending_push_outbox_ids(session, push_outbox_ids)
        push_result = {"sent": r.sent, "failed": r.failed}
    return {
        "ok": True,
        "recipient_count": len(recipients),
        "recipients": [
            {"user_id": u.id, "name": u.full_name} for u in recipients
        ],
        "in_app_created": n_created,
        "push_outbox_queued": len(push_outbox_ids),
        "push_result": push_result,
    }


@router.put("/notification-templates/{code}")
async def update_library_template_route(
    code: str,
    payload: dict,
    principal: AuthPrincipal = Depends(_librarian),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    """Update a library.* template's subject / body / channels /
    active flag. Only the four editable fields are honoured; the
    code itself is immutable so triggers keep firing."""
    from app.models.comms import NotificationTemplate
    from app.services.library_notifications import LIBRARY_TEMPLATES

    known_codes = {t["code"] for t in LIBRARY_TEMPLATES}
    if code not in known_codes:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Not a library template")
    row = (
        await session.execute(
            select(NotificationTemplate)
            .where(NotificationTemplate.code == code)
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Template not found")

    if "subject_en" in payload:
        row.subject_en = str(payload["subject_en"])[:255]
    if "body_en" in payload:
        row.body_en = str(payload["body_en"])
    if "channels" in payload:
        valid = {"in_app", "push", "sms", "email", "whatsapp"}
        row.channels = [c for c in payload["channels"] if c in valid]
    if "is_active" in payload:
        row.is_active = bool(payload["is_active"])
    await session.commit()
    return {
        "code": row.code,
        "subject_en": row.subject_en,
        "body_en": row.body_en,
        "channels": list(row.channels or []),
        "is_active": row.is_active,
    }


# ---- Renew a loan ---------------------------------------------------------


@router.post("/loans/{loan_id}/renew")
async def renew_loan_route(
    loan_id: int,
    payload: dict,
    principal: AuthPrincipal = Depends(_librarian),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    """Extend the due date on an active loan. Payload:
    ``{"extra_days": 7}``. Blocks the renewal if the loan is already
    returned or lost, or if someone else has an outstanding
    reservation for the book."""
    from datetime import timedelta

    from app.models.library import (
        Loan, LoanStatus, Reservation, ReservationStatus,
    )

    extra_days = int(payload.get("extra_days") or 0)
    if extra_days <= 0 or extra_days > 60:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="extra_days must be between 1 and 60")
    loan = (
        await session.execute(select(Loan).where(Loan.id == loan_id))
    ).scalar_one_or_none()
    if loan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Loan not found")
    if loan.status not in {LoanStatus.ACTIVE.value, LoanStatus.OVERDUE.value}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Cannot renew a loan in status {loan.status}")

    pending_reservation = (
        await session.execute(
            select(Reservation).where(
                Reservation.book_id == loan.book_id,
                Reservation.status.in_([
                    ReservationStatus.PENDING.value,
                    ReservationStatus.READY.value,
                ]),
            )
        )
    ).scalar_one_or_none()
    if pending_reservation is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Another borrower has this book reserved. Renewal blocked.",
        )

    loan.due_on = loan.due_on + timedelta(days=extra_days)
    if loan.status == LoanStatus.OVERDUE.value:
        loan.status = LoanStatus.ACTIVE.value
    await session.commit()
    await session.refresh(loan)
    return {"loan_id": loan.id, "new_due_on": loan.due_on.isoformat()}


# ---- Recent activity (audit-lite) ----------------------------------------


@router.get("/activity")
async def recent_activity_route(
    limit: int = 50,
    session: AsyncSession = Depends(tenant_scoped_session),
):
    """Chronological feed of the most recent library actions —
    without a dedicated audit table, we synthesise this from the
    ``loans`` table (issue + return timestamps) and ``books`` /
    ``book_copies`` created_at columns."""
    from app.models.library import Book, BookCopy, Loan

    limit = max(1, min(limit, 200))

    loans = list(
        (
            await session.execute(
                select(Loan).order_by(Loan.id.desc()).limit(limit)
            )
        ).scalars().all()
    )
    books = list(
        (
            await session.execute(
                select(Book).order_by(Book.created_at.desc()).limit(limit)
            )
        ).scalars().all()
    )
    copies = list(
        (
            await session.execute(
                select(BookCopy).order_by(BookCopy.created_at.desc()).limit(limit)
            )
        ).scalars().all()
    )

    events: list[dict] = []
    for l in loans:
        events.append({
            "kind": "issue",
            "when": l.created_at.isoformat() if l.created_at else None,
            "loan_id": l.id,
            "copy_id": l.copy_id,
            "book_id": l.book_id,
            "borrower_kind": l.borrower_kind,
            "borrower_id": l.borrower_id,
        })
        if l.returned_on is not None:
            events.append({
                "kind": "return",
                "when": l.returned_on.isoformat(),
                "loan_id": l.id,
                "copy_id": l.copy_id,
                "book_id": l.book_id,
                "borrower_kind": l.borrower_kind,
                "borrower_id": l.borrower_id,
                "fine_paid": float(l.fine_paid or 0),
            })
    for b in books:
        events.append({
            "kind": "book_created",
            "when": b.created_at.isoformat() if b.created_at else None,
            "book_id": b.id,
            "title": b.title,
        })
    for c in copies:
        events.append({
            "kind": "copy_created",
            "when": c.created_at.isoformat() if c.created_at else None,
            "copy_id": c.id,
            "book_id": c.book_id,
            "barcode": c.barcode,
        })

    events.sort(key=lambda e: (e["when"] or ""), reverse=True)
    return events[:limit]


# ---- Copies ----------------------------------------------------------------


@router.get("/books/{book_id}/copies", response_model=list[CopyRead])
async def list_copies_route(
    book_id: int, session: AsyncSession = Depends(tenant_scoped_session)
):
    return await list_copies(session, book_id)


@router.post(
    "/books/{book_id}/copies",
    response_model=CopyRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_copy_route(
    book_id: int,
    payload: CopyWrite,
    principal: AuthPrincipal = Depends(_librarian),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await add_copy(session, principal.tenant_id, book_id, payload)


@router.post("/books/{book_id}/copies/bulk", response_model=list[CopyRead])
async def add_copies_bulk_route(
    book_id: int,
    payload: CopyBulkAdd,
    principal: AuthPrincipal = Depends(_librarian),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await add_copies_bulk(session, principal.tenant_id, book_id, payload)


# ---- Circulation ----------------------------------------------------------


@router.post("/issue", response_model=LoanRead, status_code=status.HTTP_201_CREATED)
async def issue_route(
    payload: IssueRequest,
    principal: AuthPrincipal = Depends(_librarian),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await issue_loan(session, principal.tenant_id, principal.user_id, payload)


@router.post("/return", response_model=LoanRead)
async def return_route(
    payload: ReturnRequest,
    principal: AuthPrincipal = Depends(_librarian),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await return_loan(session, principal.user_id, payload)


@router.get("/loans", response_model=list[LoanRead])
async def list_loans_route(
    status_filter: Optional[str] = None,
    borrower_kind: Optional[BorrowerKind] = None,
    borrower_id: Optional[int] = None,
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await list_loans(
        session,
        status_filter=status_filter,
        borrower_kind=borrower_kind,
        borrower_id=borrower_id,
    )


@router.post("/sweep-overdue")
async def sweep_overdue_route(
    principal: AuthPrincipal = Depends(_librarian),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    n = await mark_overdue(session)
    return {"marked_overdue": n}


# ---- Reservations ---------------------------------------------------------


@router.get("/reservations", response_model=list[ReservationRead])
async def list_reservations_route(
    status_filter: Optional[str] = None,
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await list_reservations(session, status_filter=status_filter)


@router.post(
    "/reservations",
    response_model=ReservationRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_reservation_route(
    payload: ReservationWrite,
    principal: AuthPrincipal = Depends(_librarian),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await create_reservation(session, principal.tenant_id, payload)


@router.post("/reservations/{reservation_id}/cancel", response_model=ReservationRead)
async def cancel_reservation_route(
    reservation_id: int,
    principal: AuthPrincipal = Depends(_librarian),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await cancel_reservation(session, reservation_id)


# ---- Reports ---------------------------------------------------------------


@router.get("/reports", response_model=LibraryReports)
async def reports_route(session: AsyncSession = Depends(tenant_scoped_session)):
    return await reports(session)


# ---- Parent view -----------------------------------------------------------


parent_router = APIRouter(
    prefix="/parent", tags=["parent"], dependencies=[Depends(_parent)]
)


@parent_router.get(
    "/children/{student_id}/library", response_model=ParentLibrary
)
async def parent_library_route(
    student_id: int,
    principal: AuthPrincipal = Depends(_parent),
    session: AsyncSession = Depends(platform_session),
):
    parent = (
        await session.execute(select(Parent).where(Parent.user_id == principal.user_id))
    ).scalar_one_or_none()
    if parent is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a parent account")
    linked = (
        await session.execute(
            select(ParentChildMapping.id).where(
                ParentChildMapping.parent_id == parent.id,
                ParentChildMapping.student_id == student_id,
            )
        )
    ).scalar_one_or_none()
    if linked is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Child not linked")
    rows = await parent_child_loans(session, student_id)
    return ParentLibrary(
        student_id=student_id,
        rows=[ParentLibraryRow(**r) for r in rows],
    )


@parent_router.get("/library/catalog", response_model=list[BookWithStock])
async def parent_library_catalog(
    q: Optional[str] = None,
    category: Optional[str] = None,
    session: AsyncSession = Depends(tenant_scoped_session),
):
    """Read-only book search for parents. Same search/filter shape as the
    librarian endpoint but without write actions — parents shouldn't be
    able to add/edit/delete books, and circulation still flows through
    the librarian-only POST /issue route."""
    books = await list_books(session, q=q, category=category)
    stocks = await book_stock(session, [b.id for b in books])
    return [
        {
            **{c.name: getattr(b, c.name) for c in b.__table__.columns},
            "total_copies": stocks.get(b.id, {}).get("total", 0),
            "available_copies": stocks.get(b.id, {}).get("available", 0),
        }
        for b in books
    ]
