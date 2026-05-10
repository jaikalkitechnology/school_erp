"""Time table + substitution service (Phase 13)."""

from __future__ import annotations

from datetime import date as _date
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.academic import Section, Subject
from app.models.curriculum import SectionSubject
from app.models.teacher import (
    AttendanceStatus,
    EmploymentStatus,
    Teacher,
    TeacherAttendance,
    TeacherSubject,
)
from app.models.timetable import (
    PeriodDef,
    Substitution,
    SubstitutionStatus,
    TimetableEntry,
)
from app.schemas.timetable import (
    CellConflict,
    CellWrite,
    PeriodDefWrite,
    SaveResult,
    SectionTimetable,
    SectionTimetableWrite,
    SubSuggestionEntry,
    SubstitutionSuggest,
    SubstitutionSuggestion,
    SubstitutionWrite,
    TeacherCell,
    TeacherTimetable,
)


# ---- Period definitions ----------------------------------------------------


async def list_periods(session: AsyncSession) -> list[PeriodDef]:
    return list(
        (
            await session.execute(
                select(PeriodDef).order_by(PeriodDef.day_of_week, PeriodDef.period_number)
            )
        ).scalars().all()
    )


async def upsert_period(
    session: AsyncSession, tenant_id: int, payload: PeriodDefWrite
) -> PeriodDef:
    if payload.starts_at and payload.ends_at and payload.ends_at <= payload.starts_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ends_at must be after starts_at",
        )
    existing = (
        await session.execute(
            select(PeriodDef).where(
                PeriodDef.day_of_week == payload.day_of_week,
                PeriodDef.period_number == payload.period_number,
            )
        )
    ).scalar_one_or_none()
    if existing is None:
        existing = PeriodDef(tenant_id=tenant_id, **payload.model_dump())
        session.add(existing)
    else:
        for k, v in payload.model_dump().items():
            setattr(existing, k, v)
    await session.commit()
    await session.refresh(existing)
    return existing


async def delete_period(session: AsyncSession, period_id: int) -> None:
    obj = (
        await session.execute(select(PeriodDef).where(PeriodDef.id == period_id))
    ).scalar_one_or_none()
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Period not found")
    await session.delete(obj)
    await session.commit()


# ---- Section grid ----------------------------------------------------------


async def section_timetable(
    session: AsyncSession, section_id: int
) -> SectionTimetable:
    rows = list(
        (
            await session.execute(
                select(TimetableEntry)
                .where(TimetableEntry.section_id == section_id)
                .order_by(TimetableEntry.day_of_week, TimetableEntry.period_number)
            )
        ).scalars().all()
    )
    cells = [
        {
            "id": r.id,
            "day_of_week": r.day_of_week,
            "period_number": r.period_number,
            "subject_id": r.subject_id,
            "teacher_user_id": r.teacher_user_id,
            "room": r.room,
            "notes": r.notes,
        }
        for r in rows
    ]
    return SectionTimetable(section_id=section_id, cells=cells)


async def _conflicts_for_cells(
    session: AsyncSession, *, section_id: int, cells: list[CellWrite]
) -> list[CellConflict]:
    """Return cells that would put a teacher in two sections at the same slot."""
    out: list[CellConflict] = []
    for cell in cells:
        if cell.teacher_user_id is None:
            continue
        clash = (
            await session.execute(
                select(TimetableEntry).where(
                    TimetableEntry.teacher_user_id == cell.teacher_user_id,
                    TimetableEntry.day_of_week == cell.day_of_week,
                    TimetableEntry.period_number == cell.period_number,
                    TimetableEntry.section_id != section_id,
                )
            )
        ).scalar_one_or_none()
        if clash is not None:
            out.append(
                CellConflict(
                    day_of_week=cell.day_of_week,
                    period_number=cell.period_number,
                    teacher_user_id=cell.teacher_user_id,
                    other_section_id=clash.section_id,
                )
            )
    return out


async def replace_section_timetable(
    session: AsyncSession,
    tenant_id: int,
    section_id: int,
    payload: SectionTimetableWrite,
) -> SaveResult:
    # 1) Validate the section exists.
    if (
        await session.execute(select(Section).where(Section.id == section_id))
    ).scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")

    # 2) Reject duplicate (day, period) within the same payload.
    seen: set[tuple[int, int]] = set()
    for c in payload.cells:
        key = (c.day_of_week, c.period_number)
        if key in seen:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Duplicate cell day={c.day_of_week} period={c.period_number} in payload",
            )
        seen.add(key)

    # 3) Detect cross-section teacher conflicts.
    conflicts = await _conflicts_for_cells(session, section_id=section_id, cells=payload.cells)
    if conflicts:
        return SaveResult(saved=0, conflicts=conflicts)

    # 4) Replace the section's grid.
    await session.execute(
        TimetableEntry.__table__.delete().where(TimetableEntry.section_id == section_id)
    )
    for c in payload.cells:
        session.add(
            TimetableEntry(
                tenant_id=tenant_id,
                section_id=section_id,
                day_of_week=c.day_of_week,
                period_number=c.period_number,
                subject_id=c.subject_id,
                teacher_user_id=c.teacher_user_id,
                room=c.room,
                notes=c.notes,
            )
        )
    await session.commit()
    return SaveResult(saved=len(payload.cells), conflicts=[])


# ---- Teacher view ----------------------------------------------------------


async def teacher_timetable(
    session: AsyncSession, teacher_user_id: int
) -> TeacherTimetable:
    rows = list(
        (
            await session.execute(
                select(TimetableEntry)
                .where(TimetableEntry.teacher_user_id == teacher_user_id)
                .order_by(TimetableEntry.day_of_week, TimetableEntry.period_number)
            )
        ).scalars().all()
    )
    cells = [
        TeacherCell(
            day_of_week=r.day_of_week,
            period_number=r.period_number,
            section_id=r.section_id,
            subject_id=r.subject_id,
            room=r.room,
        )
        for r in rows
    ]
    return TeacherTimetable(teacher_user_id=teacher_user_id, cells=cells)


# ---- Substitutions ---------------------------------------------------------


async def suggest_substitutes(
    session: AsyncSession, payload: SubstitutionSuggest
) -> SubstitutionSuggestion:
    day_of_week = payload.date.weekday()  # 0=Mon..6=Sun

    # Periods this teacher would normally take that day.
    rows = list(
        (
            await session.execute(
                select(TimetableEntry).where(
                    TimetableEntry.teacher_user_id == payload.teacher_user_id,
                    TimetableEntry.day_of_week == day_of_week,
                )
            )
        ).scalars().all()
    )
    if not rows:
        return SubstitutionSuggestion(
            date=payload.date,
            absent_teacher_user_id=payload.teacher_user_id,
            entries=[],
        )

    # All teachers active + available + present that day.
    teachers = list(
        (
            await session.execute(
                select(Teacher).where(
                    Teacher.employment_status == EmploymentStatus.ACTIVE.value,
                    Teacher.is_available_for_substitution.is_(True),
                    Teacher.user_id != payload.teacher_user_id,
                )
            )
        ).scalars().all()
    )
    if not teachers:
        return SubstitutionSuggestion(
            date=payload.date,
            absent_teacher_user_id=payload.teacher_user_id,
            entries=[],
        )

    teacher_user_ids = [t.user_id for t in teachers]
    teachers_by_user = {t.user_id: t for t in teachers}

    # Skip teachers who are absent / on leave that day.
    absent_today = {
        a.teacher_id
        for a in (
            await session.execute(
                select(TeacherAttendance).where(
                    TeacherAttendance.date == payload.date,
                    TeacherAttendance.status != AttendanceStatus.PRESENT.value,
                )
            )
        ).scalars().all()
    }

    # Pre-fetch each teacher's busy slots that day.
    busy_rows = (
        await session.execute(
            select(
                TimetableEntry.teacher_user_id,
                TimetableEntry.period_number,
            ).where(
                TimetableEntry.teacher_user_id.in_(teacher_user_ids),
                TimetableEntry.day_of_week == day_of_week,
            )
        )
    ).all()
    busy: dict[int, set[int]] = {}
    for uid, period in busy_rows:
        busy.setdefault(uid, set()).add(period)

    # Already-assigned subs for the date.
    assigned = {
        (s.section_id, s.period_number): s
        for s in (
            await session.execute(
                select(Substitution).where(Substitution.date == payload.date)
            )
        ).scalars().all()
    }

    # Qualified-subject preference: subject_id -> set of user_ids qualified.
    teacher_id_to_user = {t.id: t.user_id for t in teachers}
    qualified_subject_to_teachers: dict[int, set[int]] = {}
    for ts in (
        await session.execute(
            select(TeacherSubject).where(
                TeacherSubject.teacher_id.in_(list(teacher_id_to_user.keys()))
            )
        )
    ).scalars().all():
        uid = teacher_id_to_user.get(ts.teacher_id)
        if uid is None:
            continue
        qualified_subject_to_teachers.setdefault(ts.subject_id, set()).add(uid)

    entries: list[SubSuggestionEntry] = []
    for entry in rows:
        candidates: list[int] = []
        # Prefer teachers qualified for the subject.
        preferred = (
            qualified_subject_to_teachers.get(entry.subject_id, set())
            if entry.subject_id is not None
            else set()
        )
        for uid in teacher_user_ids:
            t = teachers_by_user.get(uid)
            if t is None or t.id in absent_today:
                continue
            if entry.period_number in busy.get(uid, set()):
                continue
            # Already taken by another sub the same period? skip.
            existing = assigned.get((entry.section_id, entry.period_number))
            if existing and existing.substitute_teacher_user_id == uid:
                continue
            candidates.append(uid)
        candidates.sort(key=lambda uid: (uid not in preferred, uid))
        entries.append(
            SubSuggestionEntry(
                section_id=entry.section_id,
                period_number=entry.period_number,
                subject_id=entry.subject_id,
                suggested_substitutes=candidates[:5],
            )
        )

    return SubstitutionSuggestion(
        date=payload.date,
        absent_teacher_user_id=payload.teacher_user_id,
        entries=entries,
    )


async def list_substitutions_for_date(
    session: AsyncSession, day: _date
) -> list[Substitution]:
    return list(
        (
            await session.execute(
                select(Substitution)
                .where(Substitution.date == day)
                .order_by(Substitution.section_id, Substitution.period_number)
            )
        ).scalars().all()
    )


async def assign_substitution(
    session: AsyncSession,
    tenant_id: int,
    payload: SubstitutionWrite,
) -> Substitution:
    day_of_week = payload.date.weekday()
    cell = (
        await session.execute(
            select(TimetableEntry).where(
                TimetableEntry.section_id == payload.section_id,
                TimetableEntry.day_of_week == day_of_week,
                TimetableEntry.period_number == payload.period_number,
            )
        )
    ).scalar_one_or_none()
    if cell is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No timetable entry for that section + period on that weekday",
        )

    # Block: substitute already busy at the same slot in another section.
    busy = (
        await session.execute(
            select(TimetableEntry).where(
                TimetableEntry.teacher_user_id == payload.substitute_teacher_user_id,
                TimetableEntry.day_of_week == day_of_week,
                TimetableEntry.period_number == payload.period_number,
                TimetableEntry.section_id != payload.section_id,
            )
        )
    ).scalar_one_or_none()
    if busy is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Substitute is already teaching section {busy.section_id} at this slot",
        )

    existing = (
        await session.execute(
            select(Substitution).where(
                Substitution.date == payload.date,
                Substitution.section_id == payload.section_id,
                Substitution.period_number == payload.period_number,
            )
        )
    ).scalar_one_or_none()
    if existing is None:
        existing = Substitution(
            tenant_id=tenant_id,
            date=payload.date,
            section_id=payload.section_id,
            period_number=payload.period_number,
            subject_id=cell.subject_id,
            original_teacher_user_id=cell.teacher_user_id,
            substitute_teacher_user_id=payload.substitute_teacher_user_id,
            status=SubstitutionStatus.ASSIGNED.value,
            reason=payload.reason,
        )
        session.add(existing)
    else:
        existing.substitute_teacher_user_id = payload.substitute_teacher_user_id
        existing.status = SubstitutionStatus.ASSIGNED.value
        existing.reason = payload.reason
    await session.commit()
    await session.refresh(existing)
    return existing


async def complete_substitution(session: AsyncSession, sub_id: int) -> Substitution:
    obj = (
        await session.execute(select(Substitution).where(Substitution.id == sub_id))
    ).scalar_one_or_none()
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Substitution not found")
    obj.status = SubstitutionStatus.COMPLETED.value
    await session.commit()
    await session.refresh(obj)
    return obj


async def cancel_substitution(session: AsyncSession, sub_id: int) -> Substitution:
    obj = (
        await session.execute(select(Substitution).where(Substitution.id == sub_id))
    ).scalar_one_or_none()
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Substitution not found")
    obj.status = SubstitutionStatus.CANCELLED.value
    await session.commit()
    await session.refresh(obj)
    return obj
