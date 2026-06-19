"""Teacher-app facing service.

Single source of truth for "what does this teacher have access to" —
class teachers see their section, subject teachers see every section
they teach a subject in. Every write endpoint funnels through here so
we can enforce the same access check before delegating to existing
school-admin services (attendance, homework, leave decide).
"""

from __future__ import annotations

from datetime import date as _date
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.academic import ClassDef, Section, Subject
from app.models.curriculum import SectionSubject
from app.models.parent import Student
from app.models.teacher import Teacher
from app.models.timetable import TimetableEntry


# ---- Schemas --------------------------------------------------------------


class TeacherSectionAccess(BaseModel):
    section_id: int
    section_name: str
    class_label: Optional[str] = None
    is_class_teacher: bool
    subjects: list[str] = Field(default_factory=list)
    student_count: int = 0


class TeacherProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: int
    teacher_id: int
    employee_no: str
    full_name: str
    photo_url: Optional[str] = None
    designation: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    is_class_teacher: bool
    qualifications: list[str] = Field(default_factory=list)
    experience_years: int = 0
    # School-side context — surfaced here so the in-app ID card preview
    # doesn't need a second call to read the tenant block.
    school_name: Optional[str] = None
    school_address: Optional[str] = None
    school_phone: Optional[str] = None
    school_logo_url: Optional[str] = None


class TeacherMe(BaseModel):
    profile: TeacherProfile
    sections: list[TeacherSectionAccess]


class TodayPeriod(BaseModel):
    period_number: int
    section_id: int
    section_label: str
    subject_id: Optional[int]
    subject_name: Optional[str]
    room: Optional[str] = None


class WeekPeriod(BaseModel):
    day_of_week: int  # 0 Mon → 6 Sun
    period_number: int
    starts_at: Optional[str] = None  # "HH:MM"
    ends_at: Optional[str] = None
    section_id: Optional[int] = None
    section_label: Optional[str] = None
    subject_id: Optional[int] = None
    subject_name: Optional[str] = None
    room: Optional[str] = None
    is_break: bool = False


class TeacherTimetable(BaseModel):
    days: list[int]  # which days have any periods (0..6)
    rows: list[WeekPeriod]


class TeacherToday(BaseModel):
    date: _date
    day_of_week: int
    periods: list[TodayPeriod]
    pending_homework_count: int
    pending_leaves_count: int
    sections_to_mark_attendance: int


class StudentRosterRow(BaseModel):
    student_id: int
    full_name: str
    admission_number: str
    roll_no: Optional[str] = None
    photo_url: Optional[str] = None
    parent_phone: Optional[str] = None
    gender: Optional[str] = None


# ---- Helpers --------------------------------------------------------------


async def _teacher_for_user(
    session: AsyncSession, *, tenant_id: int, user_id: int
) -> Teacher:
    teacher = (
        await session.execute(
            select(Teacher).where(
                Teacher.tenant_id == tenant_id, Teacher.user_id == user_id,
            )
        )
    ).scalar_one_or_none()
    if teacher is None:
        # Roles like principal can have no Teacher row; we still want
        # them to see /me, but `attendance` writes still need to know
        # *which* sections they cover.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No teacher profile linked to this user. Ask the school admin.",
        )
    return teacher


async def _accessible_sections(
    session: AsyncSession, *, user_id: int
) -> list[int]:
    """Sections this user is allowed to touch — either as in-charge or
    as the subject teacher of any subject in that section."""
    in_charge_ids = list(
        (
            await session.execute(
                select(Section.id).where(Section.in_charge_user_id == user_id)
            )
        ).scalars().all()
    )
    teach_ids = list(
        (
            await session.execute(
                select(SectionSubject.section_id).where(
                    SectionSubject.teacher_user_id == user_id
                )
            )
        ).scalars().all()
    )
    return sorted({*in_charge_ids, *teach_ids})


async def assert_section_access(
    session: AsyncSession, *, user_id: int, section_id: int
) -> None:
    sections = await _accessible_sections(session, user_id=user_id)
    if section_id not in sections:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't teach this section",
        )


# ---- Profile + access map -------------------------------------------------


async def _load_tenant_block(session: AsyncSession, tenant_id: int) -> dict:
    from app.models.tenant import Tenant

    t = (
        await session.execute(select(Tenant).where(Tenant.id == tenant_id))
    ).scalar_one_or_none()
    if t is None:
        return {}
    return {
        "school_name": t.school_name,
        "school_address": t.address,
        "school_phone": t.phone,
        "school_logo_url": t.logo_url,
    }


async def teacher_me(
    session: AsyncSession, *, tenant_id: int, user_id: int
) -> TeacherMe:
    teacher = await _teacher_for_user(session, tenant_id=tenant_id, user_id=user_id)
    tenant_block = await _load_tenant_block(session, tenant_id)

    accessible_ids = await _accessible_sections(session, user_id=user_id)
    if not accessible_ids:
        profile = TeacherProfile(
            user_id=user_id,
            teacher_id=teacher.id,
            employee_no=teacher.employee_no,
            full_name=teacher.full_name,
            photo_url=teacher.photo_url,
            designation=teacher.designation,
            phone=teacher.phone,
            email=teacher.email,
            **tenant_block,
            is_class_teacher=teacher.is_class_teacher,
            qualifications=list(teacher.qualifications or []),
            experience_years=teacher.experience_years or 0,
        )
        return TeacherMe(profile=profile, sections=[])

    sections = list(
        (
            await session.execute(
                select(Section).where(Section.id.in_(accessible_ids))
                .options(selectinload(Section.class_def))
            )
        ).scalars().all()
    )
    subjects_in_section: dict[int, list[str]] = {}
    rows = (
        await session.execute(
            select(SectionSubject.section_id, Subject.name)
            .join(Subject, Subject.id == SectionSubject.subject_id)
            .where(
                SectionSubject.section_id.in_(accessible_ids),
                SectionSubject.teacher_user_id == user_id,
            )
        )
    ).all()
    for sid, sname in rows:
        subjects_in_section.setdefault(sid, []).append(sname)

    counts = {
        sid: cnt
        for sid, cnt in (
            await session.execute(
                select(Student.section_id, _count_id())
                .where(
                    Student.section_id.in_(accessible_ids),
                    Student.is_active.is_(True),
                )
                .group_by(Student.section_id)
            )
        ).all()
    }

    sec_access = [
        TeacherSectionAccess(
            section_id=s.id,
            section_name=s.name,
            class_label=s.class_def.name if s.class_def else None,
            is_class_teacher=(s.in_charge_user_id == user_id),
            subjects=subjects_in_section.get(s.id, []),
            student_count=int(counts.get(s.id, 0)),
        )
        for s in sections
    ]
    sec_access.sort(key=lambda a: (not a.is_class_teacher, a.class_label or "", a.section_name))

    profile = TeacherProfile(
        user_id=user_id,
        teacher_id=teacher.id,
        employee_no=teacher.employee_no,
        full_name=teacher.full_name,
        photo_url=teacher.photo_url,
        designation=teacher.designation,
        phone=teacher.phone,
        email=teacher.email,
        is_class_teacher=teacher.is_class_teacher,
        qualifications=list(teacher.qualifications or []),
        experience_years=teacher.experience_years or 0,
        **tenant_block,
    )
    return TeacherMe(profile=profile, sections=sec_access)


def _count_id():
    from sqlalchemy import func
    return func.count(Student.id)


# ---- Today --------------------------------------------------------------


async def teacher_today(
    session: AsyncSession, *, tenant_id: int, user_id: int
) -> TeacherToday:
    from sqlalchemy import func

    today = datetime.now(timezone.utc).date()
    dow = today.weekday()  # 0 Mon → 6 Sun

    entries = list(
        (
            await session.execute(
                select(TimetableEntry, Section, Subject, ClassDef)
                .join(Section, Section.id == TimetableEntry.section_id)
                .outerjoin(Subject, Subject.id == TimetableEntry.subject_id)
                .outerjoin(ClassDef, ClassDef.id == Section.class_def_id)
                .where(
                    TimetableEntry.teacher_user_id == user_id,
                    TimetableEntry.day_of_week == dow,
                )
                .order_by(TimetableEntry.period_number)
            )
        ).all()
    )
    periods = [
        TodayPeriod(
            period_number=e.period_number,
            section_id=sec.id,
            section_label=f"{cls.name if cls else ''} {sec.name}".strip() or sec.name,
            subject_id=sub.id if sub else None,
            subject_name=sub.name if sub else None,
            room=e.room,
        )
        for e, sec, sub, cls in entries
    ]

    # Pending homework: my own homework where due_date >= today and there
    # are submissions yet to grade. We use a coarse count to stay cheap.
    from app.models.homework import Homework, HomeworkSubmission, SubmissionStatus

    submitted_to_grade = int(
        (
            await session.execute(
                select(func.count(HomeworkSubmission.id))
                .join(Homework, Homework.id == HomeworkSubmission.homework_id)
                .where(
                    Homework.teacher_user_id == user_id,
                    HomeworkSubmission.status == SubmissionStatus.SUBMITTED.value,
                )
            )
        ).scalar_one()
    )

    # Pending leaves on this teacher's section(s).
    accessible_section_ids = await _accessible_sections(session, user_id=user_id)
    pending_leaves = 0
    if accessible_section_ids:
        from app.models.parent import LeaveApplication, LeaveStatus

        student_ids = list(
            (
                await session.execute(
                    select(Student.id).where(
                        Student.section_id.in_(accessible_section_ids)
                    )
                )
            ).scalars().all()
        )
        if student_ids:
            pending_leaves = int(
                (
                    await session.execute(
                        select(func.count(LeaveApplication.id)).where(
                            LeaveApplication.status == LeaveStatus.PENDING.value,
                            LeaveApplication.student_id.in_(student_ids),
                        )
                    )
                ).scalar_one()
            )

    sections_to_mark = len({p.section_id for p in periods})

    return TeacherToday(
        date=today,
        day_of_week=dow,
        periods=periods,
        pending_homework_count=submitted_to_grade,
        pending_leaves_count=pending_leaves,
        sections_to_mark_attendance=sections_to_mark,
    )


# ---- Roster -------------------------------------------------------------


async def section_roster(
    session: AsyncSession, *, user_id: int, section_id: int
) -> list[StudentRosterRow]:
    await assert_section_access(session, user_id=user_id, section_id=section_id)
    students = list(
        (
            await session.execute(
                select(Student)
                .where(Student.section_id == section_id, Student.is_active.is_(True))
                .order_by(Student.roll_no.is_(None), Student.roll_no, Student.full_name)
            )
        ).scalars().all()
    )
    return [
        StudentRosterRow(
            student_id=s.id,
            full_name=s.full_name,
            admission_number=s.admission_number,
            roll_no=s.roll_no,
            photo_url=s.photo_url,
            parent_phone=s.parent_phone,
            gender=s.gender,
        )
        for s in students
    ]


# ---- Weekly timetable for the logged-in teacher --------------------------


async def teacher_timetable(
    session: AsyncSession, *, tenant_id: int, user_id: int,
) -> TeacherTimetable:
    """Build the teacher's weekly grid. We pull every TimetableEntry
    assigned to this user, join in section + subject + class, and slot
    in PeriodDef start/end times where available so the mobile UI can
    render real clock times instead of bare period numbers."""
    from app.models.timetable import PeriodDef, TimetableEntry

    entries = list(
        (
            await session.execute(
                select(TimetableEntry, Section, Subject, ClassDef)
                .join(Section, Section.id == TimetableEntry.section_id)
                .outerjoin(Subject, Subject.id == TimetableEntry.subject_id)
                .outerjoin(ClassDef, ClassDef.id == Section.class_def_id)
                .where(TimetableEntry.teacher_user_id == user_id)
                .order_by(
                    TimetableEntry.day_of_week, TimetableEntry.period_number,
                )
            )
        ).all()
    )

    # Period defs are tenant-wide; load once and key by (dow, period).
    pdefs = {
        (p.day_of_week, p.period_number): p
        for p in (
            await session.execute(select(PeriodDef))
        ).scalars().all()
    }

    rows: list[WeekPeriod] = []
    days: set[int] = set()
    for e, sec, sub, cls in entries:
        pdef = pdefs.get((e.day_of_week, e.period_number))
        rows.append(WeekPeriod(
            day_of_week=e.day_of_week,
            period_number=e.period_number,
            starts_at=pdef.starts_at.strftime("%H:%M") if pdef and pdef.starts_at else None,
            ends_at=pdef.ends_at.strftime("%H:%M") if pdef and pdef.ends_at else None,
            section_id=sec.id,
            section_label=f"{cls.name if cls else ''} {sec.name}".strip() or sec.name,
            subject_id=sub.id if sub else None,
            subject_name=sub.name if sub else None,
            room=e.room,
            is_break=False,
        ))
        days.add(e.day_of_week)

    return TeacherTimetable(days=sorted(days), rows=rows)


# ---- Student drill-down -------------------------------------------------


class StudentDrill(BaseModel):
    student_id: int
    full_name: str
    admission_number: str
    roll_no: Optional[str] = None
    photo_url: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    blood_group: Optional[str] = None
    class_label: Optional[str] = None
    section_name: Optional[str] = None
    address: Optional[str] = None
    parent_phone: Optional[str] = None
    parent_email: Optional[str] = None
    father_name: Optional[str] = None
    mother_name: Optional[str] = None
    emergency_phone: Optional[str] = None
    medical_conditions: Optional[str] = None
    allergies: Optional[str] = None
    attendance_30d_pct: Optional[float] = None
    behaviour_notes: list[dict] = Field(default_factory=list)


async def student_drill(
    session: AsyncSession, *, user_id: int, student_id: int,
) -> StudentDrill:
    student = (
        await session.execute(select(Student).where(Student.id == student_id))
    ).scalar_one_or_none()
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    if student.section_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Student has no section",
        )
    await assert_section_access(
        session, user_id=user_id, section_id=student.section_id,
    )

    section = (
        await session.execute(select(Section).where(Section.id == student.section_id))
    ).scalar_one_or_none()
    class_label: Optional[str] = None
    if section is not None and section.class_def_id:
        cls = (
            await session.execute(
                select(ClassDef).where(ClassDef.id == section.class_def_id)
            )
        ).scalar_one_or_none()
        class_label = cls.name if cls else None

    # 30-day attendance %.
    from datetime import timedelta

    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=30)
    pct: Optional[float] = None
    try:
        from app.models.attendance import StudentAttendance

        rows = list(
            (
                await session.execute(
                    select(StudentAttendance).where(
                        StudentAttendance.student_id == student_id,
                        StudentAttendance.date >= start,
                        StudentAttendance.date <= today,
                    )
                )
            ).scalars().all()
        )
        if rows:
            present = sum(
                1 for r in rows if r.status in {"present", "late", "half_day"}
            )
            pct = round(100.0 * present / len(rows), 1)
    except Exception:
        # Missing column / table on a partially-migrated DB shouldn't
        # take the whole drill-down 500. Log it; surface profile +
        # behaviour notes only.
        import logging

        logging.getLogger(__name__).exception(
            "student_drill: attendance rollup failed for student %s", student_id,
        )

    # Behaviour notes (latest first).
    notes: list = []
    try:
        from app.models.staff_extras import BehaviourNote

        notes = list(
            (
                await session.execute(
                    select(BehaviourNote)
                    .where(BehaviourNote.student_id == student_id)
                    .order_by(
                        BehaviourNote.occurred_on.desc(),
                        BehaviourNote.id.desc(),
                    )
                    .limit(20)
                )
            ).scalars().all()
        )
    except Exception:
        # behaviour_notes table missing on a partially-migrated DB →
        # return [] so the screen still loads.
        import logging

        logging.getLogger(__name__).exception(
            "student_drill: behaviour notes load failed for student %s",
            student_id,
        )

    return StudentDrill(
        student_id=student.id,
        full_name=student.full_name,
        admission_number=student.admission_number,
        roll_no=student.roll_no,
        photo_url=student.photo_url,
        date_of_birth=student.date_of_birth.isoformat() if student.date_of_birth else None,
        gender=student.gender,
        blood_group=student.blood_group,
        class_label=class_label,
        section_name=section.name if section else None,
        address=student.address,
        parent_phone=student.parent_phone,
        parent_email=student.parent_email,
        father_name=student.father_name,
        mother_name=student.mother_name,
        emergency_phone=student.emergency_phone,
        medical_conditions=student.medical_conditions,
        allergies=student.allergies,
        attendance_30d_pct=pct,
        behaviour_notes=[{
            "id": n.id,
            "occurred_on": n.occurred_on.isoformat(),
            "kind": n.kind,
            "headline": n.headline,
            "detail": n.detail,
            "visible_to_parent": n.visible_to_parent,
        } for n in notes],
    )


# ---- Behaviour notes ----------------------------------------------------


class BehaviourNoteRead(BaseModel):
    id: int
    student_id: int
    occurred_on: str
    kind: str
    headline: str
    detail: Optional[str] = None
    visible_to_parent: bool


class BehaviourNoteWrite(BaseModel):
    student_id: int
    occurred_on: Optional[str] = None
    kind: str = Field(default="neutral")  # positive / concern / neutral
    headline: str = Field(min_length=1, max_length=180)
    detail: Optional[str] = None
    visible_to_parent: bool = True


async def add_behaviour_note(
    session: AsyncSession,
    *,
    tenant_id: int,
    teacher_user_id: int,
    payload: BehaviourNoteWrite,
) -> BehaviourNoteRead:
    from datetime import date as _date

    from app.models.staff_extras import BehaviourNote

    student = (
        await session.execute(
            select(Student).where(Student.id == payload.student_id)
        )
    ).scalar_one_or_none()
    if student is None or student.section_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    await assert_section_access(
        session, user_id=teacher_user_id, section_id=student.section_id,
    )

    occurred = (
        _date.fromisoformat(payload.occurred_on)
        if payload.occurred_on
        else datetime.now(timezone.utc).date()
    )
    obj = BehaviourNote(
        tenant_id=tenant_id,
        student_id=payload.student_id,
        teacher_user_id=teacher_user_id,
        occurred_on=occurred,
        kind=payload.kind,
        headline=payload.headline,
        detail=payload.detail,
        visible_to_parent=payload.visible_to_parent,
    )
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return BehaviourNoteRead(
        id=obj.id,
        student_id=obj.student_id,
        occurred_on=obj.occurred_on.isoformat(),
        kind=obj.kind,
        headline=obj.headline,
        detail=obj.detail,
        visible_to_parent=obj.visible_to_parent,
    )


# ---- Staff leave (my own) -----------------------------------------------


class StaffLeaveRead(BaseModel):
    id: int
    user_id: int
    start_date: str
    end_date: str
    reason: str
    kind: str
    status: str
    decision_remarks: Optional[str] = None
    decided_at: Optional[str] = None


class StaffLeaveWrite(BaseModel):
    start_date: str
    end_date: str
    reason: str = Field(min_length=3)
    kind: str = Field(default="casual")


class StaffLeaveDecide(BaseModel):
    status: str  # approved / rejected
    decision_remarks: Optional[str] = None


def _staff_leave_to_read(obj) -> StaffLeaveRead:
    return StaffLeaveRead(
        id=obj.id,
        user_id=obj.user_id,
        start_date=obj.start_date.isoformat() if obj.start_date else "",
        end_date=obj.end_date.isoformat() if obj.end_date else "",
        reason=obj.reason or "",
        kind=obj.kind or "casual",
        status=obj.status or "pending",
        decision_remarks=obj.decision_remarks,
        decided_at=obj.decided_at.isoformat() if obj.decided_at else None,
    )


async def apply_staff_leave(
    session: AsyncSession,
    *,
    tenant_id: int,
    user_id: int,
    payload: StaffLeaveWrite,
) -> StaffLeaveRead:
    from datetime import date as _date

    from app.models.staff_extras import StaffLeave

    try:
        start = _date.fromisoformat(payload.start_date)
        end = _date.fromisoformat(payload.end_date)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date: {e}",
        )
    if end < start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_date must be on or after start_date",
        )
    obj = StaffLeave(
        tenant_id=tenant_id,
        user_id=user_id,
        start_date=start,
        end_date=end,
        reason=payload.reason.strip(),
        kind=payload.kind,
        status="pending",
    )
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return _staff_leave_to_read(obj)


async def list_my_staff_leaves(
    session: AsyncSession, *, user_id: int, limit: int = 50,
) -> list[StaffLeaveRead]:
    from app.models.staff_extras import StaffLeave

    rows = list(
        (
            await session.execute(
                select(StaffLeave)
                .where(StaffLeave.user_id == user_id)
                .order_by(StaffLeave.id.desc())
                .limit(limit)
            )
        ).scalars().all()
    )
    return [_staff_leave_to_read(r) for r in rows]


async def list_pending_staff_leaves_for_principal(
    session: AsyncSession,
) -> list[StaffLeaveRead]:
    from app.models.staff_extras import StaffLeave

    rows = list(
        (
            await session.execute(
                select(StaffLeave)
                .where(StaffLeave.status == "pending")
                .order_by(StaffLeave.start_date)
            )
        ).scalars().all()
    )
    return [_staff_leave_to_read(r) for r in rows]


async def decide_staff_leave(
    session: AsyncSession,
    *,
    leave_id: int,
    decided_by_user_id: int,
    payload: StaffLeaveDecide,
) -> StaffLeaveRead:
    from app.models.staff_extras import StaffLeave

    if payload.status not in {"approved", "rejected"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="status must be 'approved' or 'rejected'",
        )
    obj = (
        await session.execute(
            select(StaffLeave).where(StaffLeave.id == leave_id)
        )
    ).scalar_one_or_none()
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Leave not found")
    if obj.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Leave already {obj.status}",
        )
    obj.status = payload.status
    obj.decision_remarks = payload.decision_remarks
    obj.decided_by_user_id = decided_by_user_id
    obj.decided_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await session.commit()
    await session.refresh(obj)
    return _staff_leave_to_read(obj)
