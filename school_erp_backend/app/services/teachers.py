"""Teacher onboarding, subject + class assignment, workload, attendance."""

from __future__ import annotations

from datetime import date as _date
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import hash_password
from app.models.academic import ClassDef, Section, Subject
from app.models.auth import Role, User, UserRole
from app.models.curriculum import SectionSubject
from app.models.teacher import (
    AttendanceStatus,
    EmploymentStatus,
    Teacher,
    TeacherAttendance,
    TeacherSubject,
)
from app.schemas.teacher import (
    SubstitutionCandidate,
    TeacherAttendanceBulkWrite,
    TeacherAttendanceWrite,
    TeacherCreate,
    TeacherUpdate,
    TeacherWorkload,
    TeacherWorkloadEntry,
)


VALID_TEACHER_ROLES = {
    "principal", "vice_principal", "coordinator",
    "class_teacher", "subject_teacher",
}


# ---- Onboarding -------------------------------------------------------------


async def _next_employee_no(session: AsyncSession, tenant_id: int) -> str:
    yy = _date.today().strftime("%y")
    n = int(
        (
            await session.execute(select(func.count(Teacher.id)).where(Teacher.tenant_id == tenant_id))
        ).scalar_one()
    )
    return f"EMP-{yy}-{n + 1:04d}"


async def _ensure_user(
    session: AsyncSession,
    *,
    tenant_id: int,
    full_name: str,
    email: Optional[str],
    phone: Optional[str],
    password: str,
) -> User:
    if not email and not phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either email or phone is required to log the teacher in",
        )
    existing_q = select(User).where(User.tenant_id == tenant_id)
    if email:
        existing_q = existing_q.where(User.email == email)
    elif phone:
        existing_q = existing_q.where(User.phone == phone)
    existing = (await session.execute(existing_q)).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email/phone already exists in this tenant",
        )
    user = User(
        tenant_id=tenant_id,
        full_name=full_name,
        email=email,
        phone=phone,
        password_hash=hash_password(password),
        is_active=True,
        is_email_verified=False,
        is_phone_verified=False,
    )
    session.add(user)
    await session.flush()
    return user


async def _attach_roles(
    session: AsyncSession,
    *,
    tenant_id: int,
    user_id: int,
    role_codes: list[str],
) -> list[Role]:
    valid = {c for c in role_codes if c in VALID_TEACHER_ROLES}
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"role_codes must include at least one of {sorted(VALID_TEACHER_ROLES)}",
        )
    roles = list(
        (
            await session.execute(
                select(Role).where(Role.tenant_id == tenant_id, Role.code.in_(list(valid)))
            )
        ).scalars().all()
    )
    if not roles:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Tenant RBAC not seeded; run app.services.seed.seed_rbac_for_tenant first",
        )
    for r in roles:
        session.add(UserRole(tenant_id=tenant_id, user_id=user_id, role_id=r.id))
    return roles


async def onboard_teacher(
    session: AsyncSession, tenant_id: int, payload: TeacherCreate
) -> Teacher:
    user = await _ensure_user(
        session,
        tenant_id=tenant_id,
        full_name=payload.full_name,
        email=str(payload.email) if payload.email else None,
        phone=payload.phone,
        password=payload.password,
    )
    await _attach_roles(
        session, tenant_id=tenant_id, user_id=user.id, role_codes=payload.role_codes
    )

    employee_no = payload.employee_no or await _next_employee_no(session, tenant_id)
    teacher = Teacher(
        tenant_id=tenant_id,
        user_id=user.id,
        employee_no=employee_no,
        first_name=payload.first_name,
        last_name=payload.last_name,
        full_name=payload.full_name,
        photo_url=payload.photo_url,
        date_of_birth=payload.date_of_birth,
        gender=payload.gender,
        blood_group=payload.blood_group,
        phone=payload.phone,
        email=str(payload.email) if payload.email else None,
        address=payload.address,
        emergency_contact=payload.emergency_contact,
        emergency_phone=payload.emergency_phone,
        department_id=payload.department_id,
        designation=payload.designation,
        date_of_joining=payload.date_of_joining or _date.today(),
        qualifications=list(payload.qualifications),
        experience_years=payload.experience_years,
        is_class_teacher=payload.is_class_teacher,
        is_available_for_substitution=payload.is_available_for_substitution,
        notes=payload.notes,
        employment_status=EmploymentStatus.ACTIVE.value,
    )
    session.add(teacher)
    try:
        await session.commit()
    except Exception as exc:
        await session.rollback()
        if "uq_teachers_tenant_employee_no" in str(exc).lower() or "unique" in str(exc).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Employee number {employee_no} already in use",
            )
        raise
    await session.refresh(teacher)
    return teacher


async def update_teacher(
    session: AsyncSession, teacher: Teacher, payload: TeacherUpdate
) -> Teacher:
    data = payload.model_dump(exclude_unset=True)
    if "employment_status" in data and data["employment_status"] is not None:
        data["employment_status"] = payload.employment_status.value if payload.employment_status else None
    for k, v in data.items():
        setattr(teacher, k, v)
    await session.commit()
    await session.refresh(teacher)
    return teacher


async def search_teachers(
    session: AsyncSession,
    *,
    q: Optional[str] = None,
    department_id: Optional[int] = None,
    employment_status: Optional[EmploymentStatus] = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Teacher], int]:
    stmt = select(Teacher)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Teacher.full_name).like(like),
                func.lower(Teacher.employee_no).like(like),
                func.coalesce(Teacher.phone, "").like(like),
                func.coalesce(func.lower(Teacher.email), "").like(like),
            )
        )
    if department_id is not None:
        stmt = stmt.where(Teacher.department_id == department_id)
    if employment_status is not None:
        stmt = stmt.where(Teacher.employment_status == employment_status.value)
    total = int(
        (await session.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    )
    rows = (
        await session.execute(stmt.order_by(Teacher.full_name).offset(offset).limit(limit))
    ).scalars().all()
    return list(rows), total


# ---- Subject qualifications -------------------------------------------------


async def set_qualified_subjects(
    session: AsyncSession,
    tenant_id: int,
    teacher: Teacher,
    subject_ids: list[int],
) -> list[TeacherSubject]:
    valid_ids = set(
        (
            await session.execute(
                select(Subject.id).where(Subject.id.in_(subject_ids))
            )
        ).scalars().all()
    )
    # Reset.
    await session.execute(
        TeacherSubject.__table__.delete().where(TeacherSubject.teacher_id == teacher.id)
    )
    new_rows = [
        TeacherSubject(tenant_id=tenant_id, teacher_id=teacher.id, subject_id=sid)
        for sid in valid_ids
    ]
    session.add_all(new_rows)
    await session.commit()
    return list(
        (
            await session.execute(
                select(TeacherSubject).where(TeacherSubject.teacher_id == teacher.id)
            )
        ).scalars().all()
    )


# ---- Section assignments ----------------------------------------------------


async def assign_section_subject(
    session: AsyncSession, teacher: Teacher, section_subject_id: int
) -> SectionSubject:
    ss = (
        await session.execute(
            select(SectionSubject).where(SectionSubject.id == section_subject_id)
        )
    ).scalar_one_or_none()
    if ss is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Section-subject row not found"
        )
    ss.teacher_user_id = teacher.user_id
    await session.commit()
    await session.refresh(ss)
    return ss


async def clear_section_subject_teacher(
    session: AsyncSession, section_subject_id: int
) -> SectionSubject:
    ss = (
        await session.execute(
            select(SectionSubject).where(SectionSubject.id == section_subject_id)
        )
    ).scalar_one_or_none()
    if ss is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section-subject row not found")
    ss.teacher_user_id = None
    await session.commit()
    await session.refresh(ss)
    return ss


async def assign_class_teacher(
    session: AsyncSession, teacher: Teacher, section_id: int
) -> Section:
    section = (
        await session.execute(select(Section).where(Section.id == section_id))
    ).scalar_one_or_none()
    if section is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")
    section.in_charge_user_id = teacher.user_id
    teacher.is_class_teacher = True
    await session.commit()
    await session.refresh(section)
    return section


# ---- Workload ---------------------------------------------------------------


async def workload(session: AsyncSession, teacher: Teacher) -> TeacherWorkload:
    rows = (
        await session.execute(
            select(SectionSubject, Section, ClassDef, Subject)
            .join(Section, Section.id == SectionSubject.section_id)
            .join(ClassDef, ClassDef.id == Section.class_def_id)
            .join(Subject, Subject.id == SectionSubject.subject_id)
            .where(SectionSubject.teacher_user_id == teacher.user_id)
            .order_by(ClassDef.sequence, Section.name, Subject.code)
        )
    ).all()

    entries = [
        TeacherWorkloadEntry(
            section_subject_id=ss.id,
            section_id=sec.id,
            section_name=sec.name,
            class_def_id=cls.id,
            class_name=cls.name,
            subject_id=subj.id,
            subject_name=subj.name,
            weekly_periods=ss.weekly_periods,
        )
        for (ss, sec, cls, subj) in rows
    ]
    classes = {(e.class_def_id, e.section_id) for e in entries}
    subjects = {e.subject_id for e in entries}
    total = sum(e.weekly_periods for e in entries)

    is_class_teacher_of = (
        await session.execute(
            select(Section.id).where(Section.in_charge_user_id == teacher.user_id).limit(1)
        )
    ).scalar_one_or_none()

    return TeacherWorkload(
        teacher_id=teacher.id,
        user_id=teacher.user_id,
        full_name=teacher.full_name,
        weekly_periods_total=total,
        classes_handled=len(classes),
        subjects_taught=len(subjects),
        is_class_teacher_of_section=is_class_teacher_of,
        entries=entries,
    )


# ---- Attendance -------------------------------------------------------------


async def upsert_attendance(
    session: AsyncSession,
    tenant_id: int,
    teacher: Teacher,
    payload: TeacherAttendanceWrite,
) -> TeacherAttendance:
    existing = (
        await session.execute(
            select(TeacherAttendance).where(
                TeacherAttendance.teacher_id == teacher.id,
                TeacherAttendance.date == payload.date,
            )
        )
    ).scalar_one_or_none()
    if existing is None:
        existing = TeacherAttendance(
            tenant_id=tenant_id,
            teacher_id=teacher.id,
            date=payload.date,
            status=payload.status.value,
            remarks=payload.remarks,
        )
        session.add(existing)
    else:
        existing.status = payload.status.value
        existing.remarks = payload.remarks
    await session.commit()
    await session.refresh(existing)
    return existing


async def bulk_attendance(
    session: AsyncSession,
    tenant_id: int,
    payload: TeacherAttendanceBulkWrite,
) -> int:
    teacher_ids = [e.teacher_id for e in payload.entries]
    teachers_by_id = {
        t.id: t
        for t in (
            await session.execute(select(Teacher).where(Teacher.id.in_(teacher_ids)))
        ).scalars().all()
    }
    written = 0
    for entry in payload.entries:
        if entry.teacher_id not in teachers_by_id:
            continue
        existing = (
            await session.execute(
                select(TeacherAttendance).where(
                    TeacherAttendance.teacher_id == entry.teacher_id,
                    TeacherAttendance.date == payload.date,
                )
            )
        ).scalar_one_or_none()
        if existing is None:
            session.add(
                TeacherAttendance(
                    tenant_id=tenant_id,
                    teacher_id=entry.teacher_id,
                    date=payload.date,
                    status=entry.status.value,
                    remarks=entry.remarks,
                )
            )
        else:
            existing.status = entry.status.value
            existing.remarks = entry.remarks
        written += 1
    await session.commit()
    return written


async def attendance_for_teacher(
    session: AsyncSession,
    teacher: Teacher,
    *,
    start: Optional[_date] = None,
    end: Optional[_date] = None,
) -> list[TeacherAttendance]:
    stmt = select(TeacherAttendance).where(TeacherAttendance.teacher_id == teacher.id)
    if start:
        stmt = stmt.where(TeacherAttendance.date >= start)
    if end:
        stmt = stmt.where(TeacherAttendance.date <= end)
    return list((await session.execute(stmt.order_by(TeacherAttendance.date.desc()))).scalars().all())


# ---- Substitution pool ------------------------------------------------------


async def substitution_pool(
    session: AsyncSession,
    *,
    target_date: _date,
    subject_id: Optional[int] = None,
) -> list[SubstitutionCandidate]:
    stmt = select(Teacher).where(
        Teacher.employment_status == EmploymentStatus.ACTIVE.value,
        Teacher.is_available_for_substitution.is_(True),
    )
    if subject_id is not None:
        stmt = stmt.join(TeacherSubject, TeacherSubject.teacher_id == Teacher.id).where(
            TeacherSubject.subject_id == subject_id
        )
    teachers = list((await session.execute(stmt)).scalars().all())

    # Pull per-day attendance + workload in one shot.
    today_attendance = {
        a.teacher_id: a.status
        for a in (
            await session.execute(
                select(TeacherAttendance).where(TeacherAttendance.date == target_date)
            )
        ).scalars().all()
    }
    workloads = {
        row[0]: row[1]
        for row in (
            await session.execute(
                select(
                    Teacher.id,
                    func.coalesce(func.sum(SectionSubject.weekly_periods), 0),
                )
                .join(SectionSubject, SectionSubject.teacher_user_id == Teacher.user_id, isouter=True)
                .group_by(Teacher.id)
            )
        ).all()
    }

    candidates: list[SubstitutionCandidate] = []
    for t in teachers:
        is_present = today_attendance.get(t.id, AttendanceStatus.PRESENT.value) == AttendanceStatus.PRESENT.value
        candidates.append(
            SubstitutionCandidate(
                teacher_id=t.id,
                user_id=t.user_id,
                full_name=t.full_name,
                qualifications=list(t.qualifications or []),
                weekly_periods_total=int(workloads.get(t.id, 0) or 0),
                is_available_for_substitution=t.is_available_for_substitution,
                is_present=is_present,
            )
        )
    candidates.sort(key=lambda c: (not c.is_present, c.weekly_periods_total))
    return candidates
