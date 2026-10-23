"""Day-to-day summaries for the mobile Accountant / Librarian / Hostel
Warden tabs.

The admin routes return ids (student_id, book_id, borrower_id, ...) for
the website's tables; a phone screen needs names on the first load, so
each role gets one call that bundles today's numbers and lists with
names filled in. Actions reuse the existing routes (hostel leave
decide, visitor checkout), except returning a book by its barcode,
which is what a librarian has in hand.
"""

from __future__ import annotations

from datetime import date as _date, datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import AuthPrincipal, require_roles
from app.core.tenant_session import tenant_scoped_session

_accountant = require_roles("accountant", "school_admin", "principal", "vice_principal")
_librarian = require_roles("librarian", "school_admin", "principal", "vice_principal")
_warden = require_roles("hostel_warden", "school_admin", "principal", "vice_principal")

router = APIRouter(prefix="/staff", tags=["staff"])


def _money(v) -> str:
    return str(Decimal(v or 0).quantize(Decimal("0.01")))


async def _student_names(session: AsyncSession, ids: set[int]) -> dict[int, tuple[str, str]]:
    """student_id -> (name, class label)."""
    from app.models.parent import Student

    if not ids:
        return {}
    rows = (
        await session.execute(
            select(Student.id, Student.full_name, Student.current_class_label).where(Student.id.in_(ids))
        )
    ).all()
    return {sid: (name, label or "") for sid, name, label in rows}


# ---- Accountant -------------------------------------------------------------


@router.get("/fees/today")
async def fees_today(
    principal: AuthPrincipal = Depends(_accountant),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    """Collected today / this month, what's outstanding, and who owes most."""
    from app.models.parent import Parent, ParentChildMapping
    from app.services.fees import collection_summary, defaulters

    today = _date.today()
    day = await collection_summary(session, start=today, end=today)
    month = await collection_summary(session, start=today.replace(day=1), end=today)
    owing = sorted(await defaulters(session), key=lambda r: r.amount_overdue, reverse=True)[:30]

    names = await _student_names(session, {r.student_id for r in owing})
    phones: dict[int, str] = {}
    if owing:
        for student_id, phone in (
            await session.execute(
                select(ParentChildMapping.student_id, Parent.phone)
                .join(Parent, Parent.id == ParentChildMapping.parent_id)
                .where(ParentChildMapping.student_id.in_([r.student_id for r in owing]), Parent.phone.is_not(None))
                .order_by(ParentChildMapping.is_primary.desc())
            )
        ).all():
            phones.setdefault(student_id, phone)

    return {
        "date": today.isoformat(),
        "collected_today": _money(day.total_collected),
        "collected_month": _money(month.total_collected),
        "pending": _money(month.total_pending),
        "overdue": _money(month.overdue_amount),
        "by_method_today": {k: _money(v) for k, v in day.by_method.items()},
        "defaulters": [
            {
                "student_id": r.student_id,
                "name": r.full_name,
                "admission_number": r.admission_number,
                "class_label": names.get(r.student_id, ("", ""))[1],
                "invoices_overdue": r.invoices_overdue,
                "amount_overdue": _money(r.amount_overdue),
                "parent_phone": phones.get(r.student_id),
            }
            for r in owing
        ],
    }


# ---- Librarian --------------------------------------------------------------


async def _borrower_names(session: AsyncSession, rows) -> dict[tuple[str, int], str]:
    from app.models.auth import User

    students = {r.borrower_id for r in rows if r.borrower_kind == "student"}
    staff = {r.borrower_id for r in rows if r.borrower_kind != "student"}
    out: dict[tuple[str, int], str] = {}
    for sid, (name, label) in (await _student_names(session, students)).items():
        out[("student", sid)] = f"{name} ({label})" if label else name
    if staff:
        for uid, name in (await session.execute(select(User.id, User.full_name).where(User.id.in_(staff)))).all():
            out[("teacher", uid)] = name
    return out


@router.get("/library/today")
async def library_today(
    principal: AuthPrincipal = Depends(_librarian),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    """Today's issues / returns, books overdue and reservations waiting."""
    from app.models.library import Book, BookCopy, Loan, LoanStatus, Reservation, ReservationStatus

    today = _date.today()
    issued_today = (await session.execute(select(func.count(Loan.id)).where(Loan.issued_on == today))).scalar() or 0
    returned_today = (
        await session.execute(select(func.count(Loan.id)).where(Loan.returned_on == today))
    ).scalar() or 0
    on_loan = (
        await session.execute(
            select(func.count(Loan.id)).where(
                Loan.status.in_([LoanStatus.ACTIVE.value, LoanStatus.OVERDUE.value])
            )
        )
    ).scalar() or 0

    overdue = (
        await session.execute(
            select(Loan, Book.title, BookCopy.barcode)
            .join(Book, Book.id == Loan.book_id)
            .join(BookCopy, BookCopy.id == Loan.copy_id)
            .where(
                Loan.status.in_([LoanStatus.ACTIVE.value, LoanStatus.OVERDUE.value]),
                Loan.due_on < today,
            )
            .order_by(Loan.due_on)
            .limit(50)
        )
    ).all()
    waiting = (
        await session.execute(
            select(Reservation, Book.title)
            .join(Book, Book.id == Reservation.book_id)
            .where(Reservation.status.in_([ReservationStatus.PENDING.value, ReservationStatus.READY.value]))
            .order_by(Reservation.requested_at)
            .limit(50)
        )
    ).all()
    who = await _borrower_names(session, [l for l, _, _ in overdue] + [r for r, _ in waiting])

    return {
        "date": today.isoformat(),
        "issued_today": issued_today,
        "returned_today": returned_today,
        "on_loan": on_loan,
        "overdue": [
            {
                "loan_id": loan.id,
                "title": title,
                "barcode": barcode,
                "borrower": who.get((loan.borrower_kind, loan.borrower_id), f"#{loan.borrower_id}"),
                "borrower_kind": loan.borrower_kind,
                "due_on": loan.due_on.isoformat(),
                "days_overdue": (today - loan.due_on).days,
            }
            for loan, title, barcode in overdue
        ],
        "reservations": [
            {
                "id": res.id,
                "title": title,
                "borrower": who.get((res.borrower_kind, res.borrower_id), f"#{res.borrower_id}"),
                "status": res.status,
                "requested_at": res.requested_at.isoformat(),
            }
            for res, title in waiting
        ],
    }


class ReturnByBarcode(BaseModel):
    barcode: str = Field(min_length=1, max_length=60)


@router.post("/library/return-by-barcode")
async def return_by_barcode(
    payload: ReturnByBarcode,
    principal: AuthPrincipal = Depends(_librarian),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    """Return the copy with this barcode (the book in the librarian's hand)."""
    from app.models.library import Book, BookCopy, Loan, LoanStatus
    from app.schemas.library import ReturnRequest
    from app.services.library import return_loan

    row = (
        await session.execute(
            select(Loan, Book.title)
            .join(BookCopy, BookCopy.id == Loan.copy_id)
            .join(Book, Book.id == Loan.book_id)
            .where(
                BookCopy.barcode == payload.barcode.strip(),
                Loan.status.in_([LoanStatus.ACTIVE.value, LoanStatus.OVERDUE.value]),
            )
            .order_by(Loan.id.desc())
            .limit(1)
        )
    ).first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No book on loan with that barcode")
    loan, title = row
    returned = await return_loan(session, principal.user_id, ReturnRequest(loan_id=loan.id))
    return {"loan_id": returned.id, "title": title, "fine_amount": _money(returned.fine_amount)}


# ---- Hostel warden ----------------------------------------------------------


@router.get("/hostel/today")
async def hostel_today(
    principal: AuthPrincipal = Depends(_warden),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    """Occupancy, leave requests waiting for a decision, students away on
    leave now, and visitors still checked in."""
    from app.models.hostel import HostelLeave, HostelLeaveStatus, VisitorLog
    from app.services.hostel import reports

    today = _date.today()
    summary = await reports(session)
    pending = (
        await session.execute(
            select(HostelLeave)
            .where(HostelLeave.status == HostelLeaveStatus.PENDING.value)
            .order_by(HostelLeave.from_date)
            .limit(50)
        )
    ).scalars().all()
    away = (
        await session.execute(
            select(func.count(HostelLeave.id)).where(
                HostelLeave.status == HostelLeaveStatus.APPROVED.value,
                HostelLeave.from_date <= today,
                HostelLeave.to_date >= today,
            )
        )
    ).scalar() or 0
    visitors = (
        await session.execute(
            select(VisitorLog).where(VisitorLog.out_at.is_(None)).order_by(VisitorLog.in_at).limit(50)
        )
    ).scalars().all()
    names = await _student_names(session, {l.student_id for l in pending} | {v.student_id for v in visitors})

    def student(sid: int) -> dict:
        name, label = names.get(sid, (f"Student #{sid}", ""))
        return {"student_id": sid, "student_name": name, "class_label": label}

    return {
        "date": today.isoformat(),
        "total_capacity": summary.total_capacity,
        "occupied": summary.occupied,
        "available_seats": summary.available_seats,
        "away_on_leave": away,
        "pending_leaves": [
            {
                "id": l.id,
                **student(l.student_id),
                "from_date": l.from_date.isoformat(),
                "to_date": l.to_date.isoformat(),
                "reason": l.reason,
                "contact_phone": l.contact_phone,
            }
            for l in pending
        ],
        "visitors_in": [
            {
                "id": v.id,
                **student(v.student_id),
                "visitor_name": v.visitor_name,
                "relation": v.relation,
                "in_at": v.in_at.isoformat(),
            }
            for v in visitors
        ],
    }
