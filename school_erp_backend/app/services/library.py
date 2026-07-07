"""Library service (Phase 17)."""

from __future__ import annotations

import secrets
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.library import (
    Book,
    BookCopy,
    BorrowerKind,
    CopyStatus,
    Loan,
    LoanStatus,
    Reservation,
    ReservationStatus,
)
from app.models.parent import Student
from app.schemas.library import (
    BookWrite,
    CopyBulkAdd,
    CopyWrite,
    IssueRequest,
    LibraryReports,
    ReservationWrite,
    ReturnRequest,
)


def _today() -> date:
    return date.today()


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _D(v) -> Decimal:
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v or "0"))


# ---- Books -----------------------------------------------------------------


async def list_books(
    session: AsyncSession,
    *,
    q: Optional[str] = None,
    category: Optional[str] = None,
) -> list[Book]:
    stmt = select(Book)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Book.title.ilike(like), Book.author.ilike(like), Book.isbn.ilike(like)))
    if category:
        stmt = stmt.where(Book.category == category)
    stmt = stmt.order_by(Book.title)
    return list((await session.execute(stmt)).scalars().all())


async def book_stock(session: AsyncSession, book_ids: list[int]) -> dict[int, dict[str, int]]:
    if not book_ids:
        return {}
    rows = (
        await session.execute(
            select(BookCopy.book_id, BookCopy.status, func.count(BookCopy.id))
            .where(BookCopy.book_id.in_(book_ids))
            .group_by(BookCopy.book_id, BookCopy.status)
        )
    ).all()
    out: dict[int, dict[str, int]] = {bid: {"total": 0, "available": 0} for bid in book_ids}
    for bid, st, n in rows:
        out[bid]["total"] += n
        if st == CopyStatus.AVAILABLE.value:
            out[bid]["available"] += n
    return out


async def create_book(session: AsyncSession, tenant_id: int, payload: BookWrite) -> Book:
    obj = Book(tenant_id=tenant_id, **payload.model_dump())
    session.add(obj)
    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A book with this ISBN already exists",
        )
    await session.refresh(obj)
    return obj


async def update_book(
    session: AsyncSession, book_id: int, payload: BookWrite
) -> Book:
    obj = (
        await session.execute(select(Book).where(Book.id == book_id))
    ).scalar_one_or_none()
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    for k, v in payload.model_dump().items():
        setattr(obj, k, v)
    await session.commit()
    await session.refresh(obj)
    return obj


async def delete_book(session: AsyncSession, book_id: int) -> None:
    obj = (
        await session.execute(select(Book).where(Book.id == book_id))
    ).scalar_one_or_none()
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    has_active = (
        await session.execute(
            select(func.count(Loan.id)).where(
                Loan.book_id == book_id,
                Loan.status == LoanStatus.ACTIVE.value,
            )
        )
    ).scalar_one()
    if has_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Book has active loans; return them first",
        )
    await session.delete(obj)
    await session.commit()


# ---- Copies ----------------------------------------------------------------


async def list_copies(session: AsyncSession, book_id: int) -> list[BookCopy]:
    return list(
        (
            await session.execute(
                select(BookCopy).where(BookCopy.book_id == book_id).order_by(BookCopy.id)
            )
        ).scalars().all()
    )


async def add_copy(
    session: AsyncSession, tenant_id: int, book_id: int, payload: CopyWrite
) -> BookCopy:
    if (await session.execute(select(Book).where(Book.id == book_id))).scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    obj = BookCopy(
        tenant_id=tenant_id,
        book_id=book_id,
        barcode=payload.barcode,
        accession_number=payload.accession_number,
        notes=payload.notes,
    )
    session.add(obj)
    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A copy with this barcode already exists",
        )
    await session.refresh(obj)
    return obj


async def add_copies_bulk(
    session: AsyncSession, tenant_id: int, book_id: int, payload: CopyBulkAdd
) -> list[BookCopy]:
    if (await session.execute(select(Book).where(Book.id == book_id))).scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    out: list[BookCopy] = []
    bar_prefix = payload.barcode_prefix or f"BK{book_id:04d}"
    acc_prefix = payload.accession_prefix
    for _ in range(payload.count):
        barcode = f"{bar_prefix}-{secrets.token_hex(3).upper()}"
        accession = f"{acc_prefix}-{secrets.token_hex(2).upper()}" if acc_prefix else None
        obj = BookCopy(
            tenant_id=tenant_id,
            book_id=book_id,
            barcode=barcode,
            accession_number=accession,
        )
        session.add(obj)
        out.append(obj)
    await session.commit()
    for o in out:
        await session.refresh(o)
    return out


# ---- Loans / circulation --------------------------------------------------


async def _validate_borrower(
    session: AsyncSession, kind: BorrowerKind, borrower_id: int
) -> None:
    if kind == BorrowerKind.STUDENT:
        ok = (
            await session.execute(
                select(Student.id).where(
                    Student.id == borrower_id,
                    Student.is_active.is_(True),
                )
            )
        ).scalar_one_or_none()
        if ok is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Borrower student not found or inactive",
            )
    # For teachers we trust the staff user_id; no extra check.


async def issue_loan(
    session: AsyncSession,
    tenant_id: int,
    user_id: int,
    payload: IssueRequest,
) -> Loan:
    copy = (
        await session.execute(select(BookCopy).where(BookCopy.id == payload.copy_id))
    ).scalar_one_or_none()
    if copy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Copy not found")
    if copy.status != CopyStatus.AVAILABLE.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Copy is {copy.status} and cannot be issued",
        )
    book = (
        await session.execute(select(Book).where(Book.id == copy.book_id))
    ).scalar_one()

    await _validate_borrower(session, payload.borrower_kind, payload.borrower_id)

    loan_days = payload.loan_days or book.default_loan_days
    today = _today()
    loan = Loan(
        tenant_id=tenant_id,
        copy_id=copy.id,
        book_id=copy.book_id,
        borrower_kind=payload.borrower_kind.value,
        borrower_id=payload.borrower_id,
        issued_on=today,
        due_on=today + timedelta(days=loan_days),
        status=LoanStatus.ACTIVE.value,
        issued_by_user_id=user_id,
    )
    copy.status = CopyStatus.ISSUED.value
    session.add(loan)
    await session.commit()
    await session.refresh(loan)

    # Fire the "you've borrowed this" notification. Best-effort —
    # a template lookup failure or a broken FCM must not roll back
    # the issue we just committed.
    from app.services.library_notifications import fanout_for_loan
    await fanout_for_loan(
        session,
        tenant_id=tenant_id,
        template_code="library.issued",
        loan=loan,
    )
    return loan


async def return_loan(
    session: AsyncSession,
    user_id: int,
    payload: ReturnRequest,
) -> Loan:
    loan = (
        await session.execute(select(Loan).where(Loan.id == payload.loan_id))
    ).scalar_one_or_none()
    if loan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found")
    if loan.status not in {LoanStatus.ACTIVE.value, LoanStatus.OVERDUE.value}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Loan is already {loan.status}",
        )
    book = (
        await session.execute(select(Book).where(Book.id == loan.book_id))
    ).scalar_one()
    copy = (
        await session.execute(select(BookCopy).where(BookCopy.id == loan.copy_id))
    ).scalar_one()

    return_date = payload.on_date or _today()
    loan.returned_on = return_date
    loan.returned_by_user_id = user_id
    if payload.mark_lost:
        loan.status = LoanStatus.LOST.value
        copy.status = CopyStatus.LOST.value
    else:
        late_days = max(0, (return_date - loan.due_on).days)
        if late_days > 0:
            loan.fine_amount = _D(book.default_fine_per_day) * late_days
        loan.status = LoanStatus.RETURNED.value
        copy.status = CopyStatus.AVAILABLE.value

    if payload.fine_paid is not None:
        if payload.fine_paid < 0 or payload.fine_paid > _D(loan.fine_amount):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="fine_paid out of range",
            )
        loan.fine_paid = payload.fine_paid

    await session.commit()
    await session.refresh(loan)

    # Auto-promote first PENDING reservation for this book to READY.
    res = (
        await session.execute(
            select(Reservation)
            .where(
                Reservation.book_id == loan.book_id,
                Reservation.status == ReservationStatus.PENDING.value,
            )
            .order_by(Reservation.id)
            .limit(1)
        )
    ).scalar_one_or_none()
    if res is not None and not payload.mark_lost:
        res.status = ReservationStatus.READY.value
        res.ready_at = _now()
        copy.status = CopyStatus.RESERVED.value
        await session.commit()
        # Tell the reserving borrower a copy is ready for pickup.
        from app.services.library_notifications import (
            fanout_for_reservation_ready,
        )
        await fanout_for_reservation_ready(
            session,
            tenant_id=loan.tenant_id,
            book=book,
            borrower_kind=res.borrower_kind,
            borrower_id=res.borrower_id,
            reservation_id=res.id,
        )
    return loan


async def list_loans(
    session: AsyncSession,
    *,
    status_filter: Optional[str] = None,
    borrower_kind: Optional[BorrowerKind] = None,
    borrower_id: Optional[int] = None,
) -> list[Loan]:
    stmt = select(Loan)
    if status_filter:
        stmt = stmt.where(Loan.status == status_filter)
    if borrower_kind is not None:
        stmt = stmt.where(Loan.borrower_kind == borrower_kind.value)
    if borrower_id is not None:
        stmt = stmt.where(Loan.borrower_id == borrower_id)
    stmt = stmt.order_by(Loan.id.desc())
    return list((await session.execute(stmt)).scalars().all())


async def mark_overdue(session: AsyncSession) -> int:
    """Sweep ACTIVE loans whose due_on < today and flag them OVERDUE."""
    today = _today()
    rows = list(
        (
            await session.execute(
                select(Loan).where(
                    Loan.status == LoanStatus.ACTIVE.value,
                    Loan.due_on < today,
                )
            )
        ).scalars().all()
    )
    book_cache: dict[int, Book] = {}
    newly_overdue: list[Loan] = []
    for r in rows:
        if r.book_id not in book_cache:
            book_cache[r.book_id] = (
                await session.execute(select(Book).where(Book.id == r.book_id))
            ).scalar_one()
        late_days = (today - r.due_on).days
        r.status = LoanStatus.OVERDUE.value
        r.fine_amount = _D(book_cache[r.book_id].default_fine_per_day) * late_days
        newly_overdue.append(r)
    await session.commit()

    # Day-1 "you're overdue" fanout for each loan we just flipped.
    if newly_overdue:
        from app.services.library_notifications import fanout_for_loan
        for r in newly_overdue:
            await fanout_for_loan(
                session,
                tenant_id=r.tenant_id,
                template_code="library.overdue_day1",
                loan=r,
            )
    return len(rows)


# ---- Reservations ----------------------------------------------------------


async def list_reservations(
    session: AsyncSession, *, status_filter: Optional[str] = None
) -> list[Reservation]:
    stmt = select(Reservation)
    if status_filter:
        stmt = stmt.where(Reservation.status == status_filter)
    return list((await session.execute(stmt.order_by(Reservation.id.desc()))).scalars().all())


async def create_reservation(
    session: AsyncSession, tenant_id: int, payload: ReservationWrite
) -> Reservation:
    if (
        await session.execute(select(Book).where(Book.id == payload.book_id))
    ).scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    await _validate_borrower(session, payload.borrower_kind, payload.borrower_id)

    # Block duplicate active reservations.
    existing = (
        await session.execute(
            select(Reservation).where(
                Reservation.book_id == payload.book_id,
                Reservation.borrower_kind == payload.borrower_kind.value,
                Reservation.borrower_id == payload.borrower_id,
                Reservation.status.in_(
                    [ReservationStatus.PENDING.value, ReservationStatus.READY.value]
                ),
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Borrower already has an active reservation for this book",
        )

    obj = Reservation(
        tenant_id=tenant_id,
        book_id=payload.book_id,
        borrower_kind=payload.borrower_kind.value,
        borrower_id=payload.borrower_id,
        requested_at=_now(),
        status=ReservationStatus.PENDING.value,
    )

    # If a copy is available right now, jump straight to READY.
    avail = (
        await session.execute(
            select(BookCopy).where(
                BookCopy.book_id == payload.book_id,
                BookCopy.status == CopyStatus.AVAILABLE.value,
            ).limit(1)
        )
    ).scalar_one_or_none()
    if avail is not None:
        obj.status = ReservationStatus.READY.value
        obj.ready_at = _now()
        avail.status = CopyStatus.RESERVED.value

    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return obj


async def cancel_reservation(session: AsyncSession, reservation_id: int) -> Reservation:
    res = (
        await session.execute(select(Reservation).where(Reservation.id == reservation_id))
    ).scalar_one_or_none()
    if res is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")
    if res.status not in {ReservationStatus.PENDING.value, ReservationStatus.READY.value}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Reservation already {res.status}",
        )
    if res.status == ReservationStatus.READY.value:
        # Free a reserved copy back.
        copy = (
            await session.execute(
                select(BookCopy).where(
                    BookCopy.book_id == res.book_id,
                    BookCopy.status == CopyStatus.RESERVED.value,
                ).limit(1)
            )
        ).scalar_one_or_none()
        if copy:
            copy.status = CopyStatus.AVAILABLE.value
    res.status = ReservationStatus.CANCELLED.value
    res.cancelled_at = _now()
    await session.commit()
    await session.refresh(res)
    return res


# ---- Reports ---------------------------------------------------------------


async def reports(session: AsyncSession) -> LibraryReports:
    total_books = (
        await session.execute(select(func.count(Book.id)))
    ).scalar_one()
    total_copies = (await session.execute(select(func.count(BookCopy.id)))).scalar_one()
    issued = (
        await session.execute(
            select(func.count(BookCopy.id)).where(BookCopy.status == CopyStatus.ISSUED.value)
        )
    ).scalar_one()
    available = (
        await session.execute(
            select(func.count(BookCopy.id)).where(BookCopy.status == CopyStatus.AVAILABLE.value)
        )
    ).scalar_one()

    # Compute overdue on-the-fly so the dashboard is always current.
    today = _today()
    overdue = (
        await session.execute(
            select(func.count(Loan.id)).where(
                Loan.due_on < today,
                Loan.status.in_([LoanStatus.ACTIVE.value, LoanStatus.OVERDUE.value]),
            )
        )
    ).scalar_one()

    fines = (
        await session.execute(
            select(func.coalesce(func.sum(Loan.fine_amount - Loan.fine_paid), 0))
        )
    ).scalar_one() or 0

    book_rows = (await session.execute(select(Book.id, Book.category))).all()
    by_book_category = {bid: cat for bid, cat in book_rows}
    copy_counts = (
        await session.execute(
            select(BookCopy.book_id, func.count(BookCopy.id)).group_by(BookCopy.book_id)
        )
    ).all()
    cat_books: dict[Optional[str], int] = {}
    cat_copies: dict[Optional[str], int] = {}
    for bid, cat in book_rows:
        cat_books[cat] = cat_books.get(cat, 0) + 1
    copy_count_map = {bid: int(n) for bid, n in copy_counts}
    for bid, n in copy_count_map.items():
        cat = by_book_category.get(bid)
        cat_copies[cat] = cat_copies.get(cat, 0) + n
    by_category = [
        {"category": cat, "books": cat_books[cat], "copies": cat_copies.get(cat, 0)}
        for cat in cat_books
    ]

    return LibraryReports(
        total_books=total_books,
        total_copies=total_copies,
        issued=issued,
        overdue=overdue,
        available=available,
        fines_outstanding=_D(fines),
        by_category=by_category,  # type: ignore[arg-type]
    )


# ---- Parent view -----------------------------------------------------------


async def parent_child_loans(
    session: AsyncSession, student_id: int
) -> list[dict]:
    rows = list(
        (
            await session.execute(
                select(Loan).where(
                    Loan.borrower_kind == BorrowerKind.STUDENT.value,
                    Loan.borrower_id == student_id,
                ).order_by(Loan.id.desc())
            )
        ).scalars().all()
    )
    if not rows:
        return []
    book_ids = list({l.book_id for l in rows})
    titles = {
        b.id: b.title
        for b in (
            await session.execute(select(Book).where(Book.id.in_(book_ids)))
        ).scalars().all()
    }
    out = []
    for l in rows:
        out.append(
            {
                "loan_id": l.id,
                "book_id": l.book_id,
                "book_title": titles.get(l.book_id, ""),
                "issued_on": l.issued_on,
                "due_on": l.due_on,
                "returned_on": l.returned_on,
                "status": LoanStatus(l.status),
                "fine_amount": l.fine_amount,
            }
        )
    return out
