"""Coordinator's day in one call, for the mobile Coordinator screens.

GET /v1/coordinator/today answers the three things a coordinator checks
every morning:
  * has every section's attendance been taken, and how is it looking;
  * which teachers are away (marked absent / on approved leave);
  * which of their periods still need a substitute — with suggestions.

Assigning a substitute reuses POST /v1/school-admin/timetable/substitutions,
which already admits coordinators.
"""

from __future__ import annotations

from datetime import date as _date
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import require_roles
from app.core.tenant_session import tenant_scoped_session

_coordinator = require_roles("coordinator", "vice_principal", "principal", "hod", "school_admin")

router = APIRouter(prefix="/coordinator", tags=["coordinator"], dependencies=[Depends(_coordinator)])


@router.get("/today")
async def today(
    on: Optional[_date] = None,
    session: AsyncSession = Depends(tenant_scoped_session),
):
    from app.models.academic import ClassDef, Section, Subject
    from app.models.attendance import StudentAttendance, StudentAttendanceStatus
    from app.models.auth import User
    from app.models.parent import Student
    from app.models.staff_extras import StaffLeave, StaffLeaveStatus
    from app.models.teacher import AttendanceStatus, Teacher, TeacherAttendance
    from app.models.timetable import Substitution, SubstitutionStatus, TimetableEntry
    from app.schemas.timetable import SubstitutionSuggest
    from app.services.timetable import suggest_substitutes

    day = on or _date.today()

    # ---- Sections + today's attendance ----------------------------------
    sections = (
        await session.execute(
            select(Section, ClassDef)
            .join(ClassDef, ClassDef.id == Section.class_def_id)
            .order_by(ClassDef.sequence, ClassDef.name, Section.name)
        )
    ).all()
    labels = {s.id: f"{c.name}-{s.name}" for s, c in sections}

    strength = dict(
        (
            await session.execute(
                select(Student.section_id, func.count(Student.id))
                .where(Student.is_active.is_(True), Student.section_id.is_not(None))
                .group_by(Student.section_id)
            )
        ).all()
    )
    marks: dict[int, dict[str, int]] = {}
    present_statuses = {
        StudentAttendanceStatus.PRESENT.value,
        StudentAttendanceStatus.LATE.value,
        StudentAttendanceStatus.HALF_DAY.value,
    }
    for section_id, st, n in (
        await session.execute(
            select(StudentAttendance.section_id, StudentAttendance.status, func.count(StudentAttendance.id))
            .where(StudentAttendance.date == day, StudentAttendance.section_id.is_not(None))
            .group_by(StudentAttendance.section_id, StudentAttendance.status)
        )
    ).all():
        m = marks.setdefault(section_id, {"present": 0, "absent": 0})
        if st in present_statuses:
            m["present"] += int(n)
        elif st == StudentAttendanceStatus.ABSENT.value:
            m["absent"] += int(n)

    in_charge_ids = {s.in_charge_user_id for s, _ in sections if s.in_charge_user_id}

    # ---- Teachers away today ----------------------------------------------
    away: dict[int, str] = {}  # user_id -> why
    for user_id, st in (
        await session.execute(
            select(Teacher.user_id, TeacherAttendance.status)
            .join(Teacher, Teacher.id == TeacherAttendance.teacher_id)
            .where(TeacherAttendance.date == day, TeacherAttendance.status != AttendanceStatus.PRESENT.value)
        )
    ).all():
        away[user_id] = {"leave": "On leave", "half_day": "Half day"}.get(st, "Marked absent")
    teacher_user_ids = select(Teacher.user_id)
    for user_id, kind in (
        await session.execute(
            select(StaffLeave.user_id, StaffLeave.kind).where(
                StaffLeave.status == StaffLeaveStatus.APPROVED.value,
                StaffLeave.start_date <= day,
                StaffLeave.end_date >= day,
                StaffLeave.user_id.in_(teacher_user_ids),
            )
        )
    ).all():
        away.setdefault(user_id, f"On leave · {kind}")

    # ---- Their periods, cover status and suggestions ---------------------
    subs = {
        (s.section_id, s.period_number): s
        for s in (
            await session.execute(
                select(Substitution).where(
                    Substitution.date == day,
                    Substitution.status != SubstitutionStatus.CANCELLED.value,
                )
            )
        ).scalars().all()
    }
    absent_teachers: list[dict] = []
    needed = covered = 0
    suggestion_ids: dict[tuple[int, int], list[int]] = {}
    periods_by_teacher: dict[int, list[TimetableEntry]] = {}
    if away:
        for entry in (
            await session.execute(
                select(TimetableEntry)
                .where(
                    TimetableEntry.teacher_user_id.in_(list(away)),
                    TimetableEntry.day_of_week == day.weekday(),
                )
                .order_by(TimetableEntry.period_number)
            )
        ).scalars().all():
            periods_by_teacher.setdefault(entry.teacher_user_id, []).append(entry)
        for user_id in periods_by_teacher:
            suggestion = await suggest_substitutes(session, SubstitutionSuggest(date=day, teacher_user_id=user_id))
            for e in suggestion.entries:
                suggestion_ids[(e.section_id, e.period_number)] = e.suggested_substitutes[:5]

    people = set(away) | in_charge_ids | {
        s.substitute_teacher_user_id for s in subs.values() if s.substitute_teacher_user_id
    } | {uid for ids in suggestion_ids.values() for uid in ids}
    names = dict(
        (await session.execute(select(User.id, User.full_name).where(User.id.in_(people)))).all()
    ) if people else {}
    subject_ids = {e.subject_id for es in periods_by_teacher.values() for e in es if e.subject_id}
    subjects = dict(
        (await session.execute(select(Subject.id, Subject.name).where(Subject.id.in_(subject_ids)))).all()
    ) if subject_ids else {}

    for user_id, why in sorted(away.items(), key=lambda kv: names.get(kv[0], "")):
        periods = []
        for e in periods_by_teacher.get(user_id, []):
            sub = subs.get((e.section_id, e.period_number))
            needed += 1
            if sub is not None and sub.substitute_teacher_user_id:
                covered += 1
            periods.append({
                "section_id": e.section_id,
                "section_label": labels.get(e.section_id, f"Section {e.section_id}"),
                "period_number": e.period_number,
                "subject": subjects.get(e.subject_id),
                "substitution": None if sub is None else {
                    "id": sub.id,
                    "substitute_user_id": sub.substitute_teacher_user_id,
                    "substitute_name": names.get(sub.substitute_teacher_user_id),
                    "status": sub.status,
                },
                "suggestions": [
                    {"user_id": uid, "name": names.get(uid, f"Teacher #{uid}")}
                    for uid in suggestion_ids.get((e.section_id, e.period_number), [])
                ],
            })
        absent_teachers.append({
            "user_id": user_id,
            "name": names.get(user_id, f"Teacher #{user_id}"),
            "reason": why,
            "periods": periods,
        })

    section_rows = []
    for s, _c in sections:
        m = marks.get(s.id)
        section_rows.append({
            "section_id": s.id,
            "label": labels[s.id],
            "class_teacher": names.get(s.in_charge_user_id) if s.in_charge_user_id else None,
            "strength": int(strength.get(s.id, 0)),
            "marked": m is not None,
            "present": m["present"] if m else 0,
            "absent": m["absent"] if m else 0,
        })
    marked = [r for r in section_rows if r["marked"]]
    present = sum(r["present"] for r in marked)
    absent = sum(r["absent"] for r in marked)
    return {
        "date": day.isoformat(),
        "attendance": {
            "sections": len(section_rows),
            "marked_sections": len(marked),
            "present": present,
            "absent": absent,
            "percent": round(present / (present + absent) * 100, 1) if present + absent else None,
        },
        "sections": section_rows,
        "absent_teachers": absent_teachers,
        "cover": {"needed": needed, "covered": covered},
    }
