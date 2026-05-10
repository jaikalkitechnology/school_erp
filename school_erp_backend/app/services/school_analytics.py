"""Phase 20 school-admin analytics service.

Cross-module aggregations for the school admin reports dashboard. Built on
top of every phase that landed before, so the queries deliberately stay at
the level of `select / func.count / func.sum` per module.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.academic import ClassDef, Section
from app.models.attendance import StudentAttendance, StudentAttendanceStatus
from app.models.exams import Exam, ExamMarks, ExamSubject, GradeScale, MarkStatus
from app.models.fees import FeeCategory, FeeInvoice, FeeInvoiceStatus, FeePayment, PaymentStatus
from app.models.hostel import HostelAllocation, HostelLeave, HostelLeaveStatus, Room
from app.models.library import Book, Loan, LoanStatus
from app.models.parent import Student
from app.models.teacher import Teacher
from app.models.transport import (
    Bus,
    Driver,
    Route,
    StudentTransport,
    Trip,
    TripPhase,
)


def _D(v) -> Decimal:
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v or "0"))


# ---- Overview ------------------------------------------------------------


async def overview(session: AsyncSession) -> dict:
    students = (
        await session.execute(
            select(func.count(Student.id)).where(Student.is_active.is_(True))
        )
    ).scalar_one()
    teachers = (await session.execute(select(func.count(Teacher.id)))).scalar_one()
    classes = (await session.execute(select(func.count(ClassDef.id)))).scalar_one()
    sections = (await session.execute(select(func.count(Section.id)))).scalar_one()

    today = date.today()
    today_rows = list(
        (
            await session.execute(
                select(StudentAttendance.status, func.count(StudentAttendance.id))
                .where(StudentAttendance.date == today)
                .group_by(StudentAttendance.status)
            )
        ).all()
    )
    counts = {s: int(n) for s, n in today_rows}
    present = counts.get(StudentAttendanceStatus.PRESENT.value, 0)
    late = counts.get(StudentAttendanceStatus.LATE.value, 0)
    half = counts.get(StudentAttendanceStatus.HALF_DAY.value, 0)
    total_marked = sum(counts.values())
    attendance_pct = (
        round((present + late + 0.5 * half) / total_marked * 100, 2)
        if total_marked else 0.0
    )

    first = today.replace(day=1)
    fees_collected_month = (
        await session.execute(
            select(func.coalesce(func.sum(FeePayment.amount), 0)).where(
                FeePayment.paid_at >= datetime.combine(first, datetime.min.time()),
                FeePayment.status == PaymentStatus.SUCCESS.value,
            )
        )
    ).scalar_one() or 0
    fees_pending = (
        await session.execute(
            select(
                func.coalesce(
                    func.sum(FeeInvoice.total_amount - FeeInvoice.paid_amount), 0
                )
            ).where(
                FeeInvoice.status.in_(
                    [
                        FeeInvoiceStatus.PENDING.value,
                        FeeInvoiceStatus.PARTIAL.value,
                        FeeInvoiceStatus.OVERDUE.value,
                    ]
                )
            )
        )
    ).scalar_one() or 0

    overdue_loans = (
        await session.execute(
            select(func.count(Loan.id)).where(
                Loan.due_on < today,
                Loan.status.in_([LoanStatus.ACTIVE.value, LoanStatus.OVERDUE.value]),
            )
        )
    ).scalar_one()

    cls_rows = list(
        (
            await session.execute(
                select(ClassDef.id, ClassDef.name).order_by(ClassDef.sequence)
            )
        ).all()
    )
    student_counts = dict(
        (
            await session.execute(
                select(Student.class_def_id, func.count(Student.id))
                .where(Student.is_active.is_(True))
                .group_by(Student.class_def_id)
            )
        ).all()
    )
    by_class = [
        {"label": name, "value": float(student_counts.get(cid, 0))}
        for cid, name in cls_rows
    ]

    return {
        "students": students,
        "teachers": teachers,
        "classes": classes,
        "sections": sections,
        "attendance_today_pct": attendance_pct,
        "fee_collected_this_month": _D(fees_collected_month),
        "fee_pending": _D(fees_pending),
        "overdue_loans": int(overdue_loans),
        "by_class_strength": by_class,
    }


# ---- Attendance trend ----------------------------------------------------


async def attendance_trend(session: AsyncSession, days: int = 14) -> dict:
    today = date.today()
    start = today - timedelta(days=days - 1)
    rows = list(
        (
            await session.execute(
                select(
                    StudentAttendance.date,
                    StudentAttendance.status,
                    func.count(StudentAttendance.id),
                ).where(StudentAttendance.date >= start)
                .group_by(StudentAttendance.date, StudentAttendance.status)
                .order_by(StudentAttendance.date)
            )
        ).all()
    )
    by_day: dict[date, dict[str, int]] = {}
    for d, st, n in rows:
        by_day.setdefault(d, {})[st] = int(n)
    points = []
    totals: list[float] = []
    for i in range(days):
        d = start + timedelta(days=i)
        bucket = by_day.get(d, {})
        total = sum(bucket.values())
        present = bucket.get(StudentAttendanceStatus.PRESENT.value, 0)
        late = bucket.get(StudentAttendanceStatus.LATE.value, 0)
        half = bucket.get(StudentAttendanceStatus.HALF_DAY.value, 0)
        pct = (present + late + 0.5 * half) / total * 100 if total else 0.0
        points.append({"label": d.isoformat(), "value": round(pct, 2)})
        if total:
            totals.append(pct)
    avg = round(sum(totals) / len(totals), 2) if totals else 0.0
    return {"points": points, "average_pct": avg}


# ---- Fees ----------------------------------------------------------------


async def fees(session: AsyncSession) -> dict:
    total_billed = (
        await session.execute(select(func.coalesce(func.sum(FeeInvoice.total_amount), 0)))
    ).scalar_one() or 0
    total_collected = (
        await session.execute(
            select(func.coalesce(func.sum(FeePayment.amount), 0)).where(
                FeePayment.status == PaymentStatus.SUCCESS.value
            )
        )
    ).scalar_one() or 0
    pending = (
        await session.execute(
            select(
                func.coalesce(func.sum(FeeInvoice.total_amount - FeeInvoice.paid_amount), 0)
            ).where(
                FeeInvoice.status.in_(
                    [
                        FeeInvoiceStatus.PENDING.value,
                        FeeInvoiceStatus.PARTIAL.value,
                        FeeInvoiceStatus.OVERDUE.value,
                    ]
                )
            )
        )
    ).scalar_one() or 0
    overdue_count = (
        await session.execute(
            select(func.count(FeeInvoice.id)).where(
                FeeInvoice.status == FeeInvoiceStatus.OVERDUE.value
            )
        )
    ).scalar_one()

    by_method = list(
        (
            await session.execute(
                select(FeePayment.method, func.coalesce(func.sum(FeePayment.amount), 0))
                .where(FeePayment.status == PaymentStatus.SUCCESS.value)
                .group_by(FeePayment.method)
            )
        ).all()
    )
    by_method_points = [
        {"label": m, "value": float(amt or 0)} for m, amt in by_method
    ]

    cat_rows = list(
        (
            await session.execute(
                select(
                    FeeCategory.name,
                    func.coalesce(func.sum(FeeInvoice.paid_amount), 0),
                ).join(FeeInvoice, FeeInvoice.category_id == FeeCategory.id)
                .group_by(FeeCategory.name)
            )
        ).all()
    )
    by_category_points = [
        {"label": name, "value": float(amt or 0)} for name, amt in cat_rows
    ]

    return {
        "total_billed": _D(total_billed),
        "total_collected": _D(total_collected),
        "pending": _D(pending),
        "overdue_count": int(overdue_count),
        "by_method": by_method_points,
        "by_category": by_category_points,
    }


# ---- Exams ---------------------------------------------------------------


async def exam_analytics(session: AsyncSession, *, exam_id: Optional[int] = None) -> dict:
    exams_q = select(Exam)
    if exam_id is not None:
        exams_q = exams_q.where(Exam.id == exam_id)
    exams_q = exams_q.order_by(Exam.id.desc()).limit(5)
    exams = list((await session.execute(exams_q)).scalars().all())

    rows: list[dict] = []
    grade_dist: dict[str, int] = {}

    scale = (
        await session.execute(
            select(GradeScale).where(GradeScale.is_default.is_(True)).limit(1)
        )
    ).scalar_one_or_none()
    bands = sorted(scale.bands or [], key=lambda b: -float(b["min_pct"])) if scale else []

    def _grade(pct: float) -> Optional[str]:
        for b in bands:
            if pct >= float(b["min_pct"]):
                return str(b["grade"])
        return None

    section_class = dict(
        (await session.execute(select(Section.id, Section.class_def_id))).all()
    )

    for exam in exams:
        es_rows = list(
            (
                await session.execute(
                    select(ExamSubject).where(ExamSubject.exam_id == exam.id)
                )
            ).scalars().all()
        )
        if not es_rows:
            continue
        es_ids = [e.id for e in es_rows]
        es_max = {e.id: _D(e.max_marks) for e in es_rows}
        es_class = {e.id: e.class_def_id for e in es_rows}

        marks = list(
            (
                await session.execute(
                    select(ExamMarks).where(ExamMarks.exam_subject_id.in_(es_ids))
                )
            ).scalars().all()
        )
        if not marks:
            continue
        students = dict(
            (
                await session.execute(
                    select(Student.id, Student.section_id).where(
                        Student.id.in_({m.student_id for m in marks})
                    )
                )
            ).all()
        )
        per_section: dict[int, list[tuple[float, bool]]] = {}
        for m in marks:
            sec_id = students.get(m.student_id)
            if sec_id is None:
                continue
            cls_id = section_class.get(sec_id)
            sub_max = es_max.get(m.exam_subject_id, _D("0"))
            if cls_id != es_class.get(m.exam_subject_id) or sub_max <= 0:
                continue
            if m.obtained_marks is None or m.status == MarkStatus.ABSENT.value:
                pct = 0.0
                ok = False
            else:
                pct = float((_D(m.obtained_marks) / sub_max) * 100)
                ok = m.status != MarkStatus.FAIL.value
            per_section.setdefault(sec_id, []).append((pct, ok))

        sec_ids = list(per_section.keys())
        sec_names = (
            dict(
                (
                    await session.execute(
                        select(Section.id, Section.name).where(Section.id.in_(sec_ids))
                    )
                ).all()
            )
            if sec_ids else {}
        )

        for sec_id, pairs in per_section.items():
            if not pairs:
                continue
            avg = sum(p for p, _ in pairs) / len(pairs)
            pass_pct = sum(1 for _, ok in pairs if ok) / len(pairs) * 100
            rows.append(
                {
                    "exam_id": exam.id,
                    "exam_name": exam.name,
                    "section_id": sec_id,
                    "section_name": sec_names.get(sec_id),
                    "average_pct": round(avg, 2),
                    "pass_pct": round(pass_pct, 2),
                    "student_count": len(pairs),
                }
            )
            if bands:
                for pct, _ in pairs:
                    g = _grade(pct) or "—"
                    grade_dist[g] = grade_dist.get(g, 0) + 1

    return {
        "rows": rows,
        "grade_distribution": [
            {"label": k, "value": float(v)} for k, v in sorted(grade_dist.items())
        ],
    }


# ---- Library / transport / hostel ----------------------------------------


async def library_usage(session: AsyncSession) -> dict:
    today = date.today()
    issued_today = (
        await session.execute(
            select(func.count(Loan.id)).where(Loan.issued_on == today)
        )
    ).scalar_one()
    overdue = (
        await session.execute(
            select(func.count(Loan.id)).where(
                Loan.due_on < today,
                Loan.status.in_([LoanStatus.ACTIVE.value, LoanStatus.OVERDUE.value]),
            )
        )
    ).scalar_one()
    rows = list(
        (
            await session.execute(
                select(Loan.book_id, func.count(Loan.id))
                .group_by(Loan.book_id)
                .order_by(func.count(Loan.id).desc())
                .limit(5)
            )
        ).all()
    )
    titles: dict[int, str] = {}
    if rows:
        bids = [bid for bid, _ in rows]
        titles = dict(
            (
                await session.execute(select(Book.id, Book.title).where(Book.id.in_(bids)))
            ).all()
        )
    return {
        "issued_today": int(issued_today),
        "overdue": int(overdue),
        "most_loaned": [
            {"label": titles.get(bid, str(bid)), "value": float(cnt)}
            for bid, cnt in rows
        ],
    }


async def transport_summary(session: AsyncSession) -> dict:
    today = date.today()
    routes = (await session.execute(select(func.count(Route.id)))).scalar_one()
    buses = (await session.execute(select(func.count(Bus.id)))).scalar_one()
    drivers = (await session.execute(select(func.count(Driver.id)))).scalar_one()
    students_allocated = (
        await session.execute(select(func.count(StudentTransport.id)))
    ).scalar_one()
    active_trips = (
        await session.execute(
            select(func.count(Trip.id)).where(
                Trip.trip_date == today,
                Trip.phase == TripPhase.IN_PROGRESS.value,
            )
        )
    ).scalar_one()
    return {
        "routes": int(routes),
        "buses": int(buses),
        "drivers": int(drivers),
        "students_allocated": int(students_allocated),
        "active_trips_today": int(active_trips),
    }


async def hostel_summary(session: AsyncSession) -> dict:
    rooms = list((await session.execute(select(Room))).scalars().all())
    capacity = sum(r.capacity for r in rooms)
    occupied = (
        await session.execute(
            select(func.count(HostelAllocation.id)).where(HostelAllocation.is_active.is_(True))
        )
    ).scalar_one()
    pending_leaves = (
        await session.execute(
            select(func.count(HostelLeave.id)).where(
                HostelLeave.status == HostelLeaveStatus.PENDING.value
            )
        )
    ).scalar_one()
    return {
        "occupied": int(occupied),
        "available_seats": int(max(0, capacity - occupied)),
        "pending_leaves": int(pending_leaves),
    }


# ---- Standard reports ----------------------------------------------------


async def student_report(
    session: AsyncSession,
    *,
    class_def_id: Optional[int] = None,
    section_id: Optional[int] = None,
    only_active: bool = True,
) -> list[dict]:
    stmt = select(Student)
    if class_def_id is not None:
        stmt = stmt.where(Student.class_def_id == class_def_id)
    if section_id is not None:
        stmt = stmt.where(Student.section_id == section_id)
    if only_active:
        stmt = stmt.where(Student.is_active.is_(True))
    stmt = stmt.order_by(Student.full_name)
    students = list((await session.execute(stmt)).scalars().all())
    if not students:
        return []
    cls_names = dict(
        (await session.execute(select(ClassDef.id, ClassDef.name))).all()
    )
    sec_names = dict(
        (await session.execute(select(Section.id, Section.name))).all()
    )
    rows = []
    for s in students:
        rows.append(
            {
                "student_id": s.id,
                "admission_number": s.admission_number,
                "full_name": s.full_name,
                "class_label": cls_names.get(s.class_def_id),
                "section_name": sec_names.get(s.section_id) if s.section_id else None,
                "parent_phone": s.parent_phone,
                "status": s.status,
            }
        )
    return rows
