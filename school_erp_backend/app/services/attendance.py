"""Student attendance service (Phase 9)."""

from __future__ import annotations

import calendar
from datetime import date as _date
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.academic import Section
from app.models.attendance import StudentAttendance, StudentAttendanceStatus
from app.models.parent import Student
from app.schemas.attendance import (
    AttendanceMarkRequest,
    DefaulterRow,
    SectionMonthlyReport,
    SectionRoll,
    StudentHistoryRow,
    StudentMonthlySummary,
    StudentRollEntry,
)


COUNTABLE_STATUSES = {
    StudentAttendanceStatus.PRESENT.value: "present",
    StudentAttendanceStatus.ABSENT.value: "absent",
    StudentAttendanceStatus.LATE.value: "late",
    StudentAttendanceStatus.LEAVE.value: "leave",
    StudentAttendanceStatus.HALF_DAY.value: "half_day",
}


# ---- Roll-call -------------------------------------------------------------


async def section_roll(
    session: AsyncSession,
    *,
    section_id: int,
    target_date: _date,
    period: str = "day",
) -> SectionRoll:
    section = (
        await session.execute(select(Section).where(Section.id == section_id))
    ).scalar_one_or_none()
    if section is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")

    students = list(
        (
            await session.execute(
                select(Student)
                .where(Student.section_id == section_id, Student.is_active.is_(True))
                .order_by(Student.roll_no.is_(None), Student.roll_no, Student.full_name)
            )
        ).scalars().all()
    )
    rows_by_student = {
        a.student_id: a
        for a in (
            await session.execute(
                select(StudentAttendance).where(
                    StudentAttendance.section_id == section_id,
                    StudentAttendance.date == target_date,
                    StudentAttendance.period == period,
                )
            )
        ).scalars().all()
    }

    entries = [
        StudentRollEntry(
            student_id=s.id,
            full_name=s.full_name,
            admission_number=s.admission_number,
            roll_no=s.roll_no,
            status=StudentAttendanceStatus(
                rows_by_student[s.id].status if s.id in rows_by_student else StudentAttendanceStatus.PRESENT.value
            ),
            remarks=(rows_by_student[s.id].remarks if s.id in rows_by_student else None),
        )
        for s in students
    ]
    counts: dict[str, int] = {label: 0 for label in COUNTABLE_STATUSES.values()}
    counts["unmarked"] = 0
    for s in students:
        if s.id in rows_by_student:
            counts[COUNTABLE_STATUSES[rows_by_student[s.id].status]] += 1
        else:
            counts["unmarked"] += 1

    return SectionRoll(
        section_id=section_id,
        date=target_date,
        period=period,
        students=entries,
        counts=counts,
    )


async def mark_section_attendance(
    session: AsyncSession,
    tenant_id: int,
    user_id: int,
    payload: AttendanceMarkRequest,
) -> SectionRoll:
    section = (
        await session.execute(select(Section).where(Section.id == payload.section_id))
    ).scalar_one_or_none()
    if section is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")

    students_in_section = list(
        (
            await session.execute(
                select(Student.id).where(
                    Student.section_id == payload.section_id, Student.is_active.is_(True)
                )
            )
        ).scalars().all()
    )
    students_set = set(students_in_section)
    by_student = {e.student_id: e for e in payload.entries}
    invalid = set(by_student) - students_set
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Students {sorted(invalid)} are not in this section",
        )

    existing = {
        a.student_id: a
        for a in (
            await session.execute(
                select(StudentAttendance).where(
                    StudentAttendance.section_id == payload.section_id,
                    StudentAttendance.date == payload.date,
                    StudentAttendance.period == payload.period,
                )
            )
        ).scalars().all()
    }

    for sid in students_in_section:
        entry = by_student.get(sid)
        status_value = (entry.status if entry else payload.default_status).value
        remarks = entry.remarks if entry else None
        existing_row = existing.get(sid)
        if existing_row is None:
            session.add(
                StudentAttendance(
                    tenant_id=tenant_id,
                    student_id=sid,
                    section_id=section.id,
                    class_def_id=section.class_def_id,
                    date=payload.date,
                    period=payload.period,
                    status=status_value,
                    marked_by_user_id=user_id,
                    remarks=remarks,
                )
            )
        else:
            existing_row.status = status_value
            existing_row.remarks = remarks
            existing_row.marked_by_user_id = user_id

    await session.commit()
    return await section_roll(
        session, section_id=payload.section_id, target_date=payload.date, period=payload.period
    )


# ---- Reports ---------------------------------------------------------------


def _date_range_for_month(year: int, month: int) -> tuple[_date, _date]:
    if not (1 <= month <= 12):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="month must be 1..12")
    start = _date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    end = _date(year, month, last_day)
    return start, end


async def section_monthly(
    session: AsyncSession,
    *,
    section_id: int,
    year: int,
    month: int,
) -> SectionMonthlyReport:
    start, end = _date_range_for_month(year, month)

    students = list(
        (
            await session.execute(
                select(Student)
                .where(Student.section_id == section_id, Student.is_active.is_(True))
                .order_by(Student.full_name)
            )
        ).scalars().all()
    )

    # Working days = unique dates with at least one row in the section over the range.
    working_days = int(
        (
            await session.execute(
                select(func.count(func.distinct(StudentAttendance.date))).where(
                    StudentAttendance.section_id == section_id,
                    StudentAttendance.date >= start,
                    StudentAttendance.date <= end,
                )
            )
        ).scalar_one()
    )

    summaries: list[StudentMonthlySummary] = []
    for s in students:
        rows = list(
            (
                await session.execute(
                    select(StudentAttendance.status).where(
                        StudentAttendance.student_id == s.id,
                        StudentAttendance.date >= start,
                        StudentAttendance.date <= end,
                    )
                )
            ).scalars().all()
        )
        counts = {v: 0 for v in COUNTABLE_STATUSES.values()}
        for r in rows:
            counts[COUNTABLE_STATUSES[r]] += 1
        total = len(rows)
        # Present + late + half-day count toward attendance.
        attended = counts["present"] + counts["late"] + counts["half_day"] * 0.5
        pct = round((attended / total) * 100, 2) if total else 0.0
        summaries.append(
            StudentMonthlySummary(
                student_id=s.id,
                full_name=s.full_name,
                admission_number=s.admission_number,
                total_days=total,
                present=counts["present"],
                absent=counts["absent"],
                late=counts["late"],
                leave=counts["leave"],
                half_day=counts["half_day"],
                attendance_pct=pct,
            )
        )

    return SectionMonthlyReport(
        section_id=section_id,
        year=year,
        month=month,
        working_days=working_days,
        students=summaries,
    )


async def defaulters(
    session: AsyncSession,
    *,
    threshold_pct: float,
    start: Optional[_date] = None,
    end: Optional[_date] = None,
    section_id: Optional[int] = None,
) -> list[DefaulterRow]:
    if start is None and end is None:
        today = _date.today()
        start = _date(today.year, today.month, 1)
        end = today

    stmt = select(StudentAttendance.student_id, StudentAttendance.status).where(
        StudentAttendance.date >= start,
        StudentAttendance.date <= end,
    )
    if section_id is not None:
        stmt = stmt.where(StudentAttendance.section_id == section_id)

    rows = list((await session.execute(stmt)).all())
    bucket: dict[int, dict[str, int]] = {}
    for sid, status_value in rows:
        b = bucket.setdefault(sid, {"total": 0, "present": 0})
        b["total"] += 1
        if status_value in {
            StudentAttendanceStatus.PRESENT.value,
            StudentAttendanceStatus.LATE.value,
        }:
            b["present"] += 1
        elif status_value == StudentAttendanceStatus.HALF_DAY.value:
            # Half-day counts as half a present.
            b["present"] += 0.5  # type: ignore[operator]

    if not bucket:
        return []

    students_q = select(Student).where(Student.id.in_(list(bucket.keys())))
    if section_id is not None:
        students_q = students_q.where(Student.section_id == section_id)
    students = list((await session.execute(students_q)).scalars().all())

    out: list[DefaulterRow] = []
    for s in students:
        b = bucket.get(s.id) or {"total": 0, "present": 0}
        total = b["total"]
        present = b["present"]
        pct = round((present / total) * 100, 2) if total else 0.0
        if total > 0 and pct < threshold_pct:
            out.append(
                DefaulterRow(
                    student_id=s.id,
                    full_name=s.full_name,
                    admission_number=s.admission_number,
                    section_id=s.section_id,
                    class_def_id=s.class_def_id,
                    total_days=total,
                    present_days=int(present),
                    attendance_pct=pct,
                )
            )
    out.sort(key=lambda r: r.attendance_pct)
    return out


async def student_history(
    session: AsyncSession,
    *,
    student_id: int,
    start: Optional[_date] = None,
    end: Optional[_date] = None,
    limit: int = 60,
) -> list[StudentHistoryRow]:
    stmt = select(StudentAttendance).where(StudentAttendance.student_id == student_id)
    if start:
        stmt = stmt.where(StudentAttendance.date >= start)
    if end:
        stmt = stmt.where(StudentAttendance.date <= end)
    stmt = stmt.order_by(StudentAttendance.date.desc()).limit(limit)
    rows = list((await session.execute(stmt)).scalars().all())
    return [
        StudentHistoryRow(
            date=r.date,
            period=r.period,
            status=StudentAttendanceStatus(r.status),
            remarks=r.remarks,
        )
        for r in rows
    ]


async def today_status_for_student(
    session: AsyncSession, student_id: int
) -> Optional[str]:
    today = _date.today()
    row = (
        await session.execute(
            select(StudentAttendance.status).where(
                StudentAttendance.student_id == student_id,
                StudentAttendance.date == today,
                StudentAttendance.period == "day",
            )
        )
    ).scalar_one_or_none()
    return row
