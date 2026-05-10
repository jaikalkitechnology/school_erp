"""Student admission, promotion, withdrawal, sibling linking."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.academic import ClassDef, Section
from app.models.parent import Student
from app.models.sis import Admission, AdmissionStage, StudentDocument, StudentStatus
from app.schemas.sis import (
    AdmissionWrite,
    PromotionRequest,
    PromotionResult,
    StudentCreate,
    StudentUpdate,
    WithdrawRequest,
)


def _today() -> date:
    return datetime.now(timezone.utc).date()


def _format_class_label(cls: Optional[ClassDef], section: Optional[Section]) -> Optional[str]:
    if cls is None and section is None:
        return None
    if cls and section:
        return f"{cls.name} · {section.name}"
    if cls:
        return cls.name
    return None


# ---- Admission number generator -------------------------------------------


async def next_admission_number(session: AsyncSession, tenant_id: int) -> str:
    """ADM-YY-NNNN where NNNN is the count of students in the tenant + 1."""
    yy = _today().strftime("%y")
    count = int(
        (
            await session.execute(
                select(func.count(Student.id)).where(Student.tenant_id == tenant_id)
            )
        ).scalar_one()
    )
    return f"ADM-{yy}-{count + 1:04d}"


# ---- Sibling auto-linking --------------------------------------------------


def _has_parent_match(a: Student, b: Student) -> bool:
    keys_a = {x for x in (a.parent_phone, a.parent_email) if x}
    keys_b = {x for x in (b.parent_phone, b.parent_email) if x}
    return bool(keys_a & keys_b)


async def _auto_link_siblings(session: AsyncSession, tenant_id: int, new_student: Student) -> Optional[int]:
    """If the new student shares parent_phone or parent_email with any existing
    student in the tenant, slot them all into the same ``sibling_group_id``.
    Returns the assigned group id or None."""
    if not new_student.parent_phone and not new_student.parent_email:
        return None

    candidates = (
        await session.execute(
            select(Student).where(
                Student.tenant_id == tenant_id,
                Student.id != new_student.id,
                or_(
                    and_(Student.parent_phone.isnot(None), Student.parent_phone == new_student.parent_phone),
                    and_(Student.parent_email.isnot(None), Student.parent_email == new_student.parent_email),
                ),
            )
        )
    ).scalars().all()

    if not candidates:
        return None

    # Reuse an existing group if any sibling already has one.
    existing_group = next((c.sibling_group_id for c in candidates if c.sibling_group_id), None)
    if existing_group is None:
        # Pick the smallest student id in the cluster as a stable group id.
        existing_group = min((c.id for c in candidates), default=new_student.id)

    new_student.sibling_group_id = existing_group
    for c in candidates:
        if c.sibling_group_id != existing_group:
            c.sibling_group_id = existing_group
    await session.commit()
    return existing_group


# ---- Student CRUD ----------------------------------------------------------


async def admit_student(
    session: AsyncSession,
    tenant_id: int,
    payload: StudentCreate,
) -> Student:
    cls = (
        await session.execute(select(ClassDef).where(ClassDef.id == payload.class_def_id))
    ).scalar_one_or_none() if payload.class_def_id else None
    section = (
        await session.execute(select(Section).where(Section.id == payload.section_id))
    ).scalar_one_or_none() if payload.section_id else None
    if payload.section_id and not section:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Section not found")
    if section and cls and section.class_def_id != cls.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Section does not belong to the supplied class",
        )

    admission_number = payload.admission_number
    if not admission_number:
        admission_number = await next_admission_number(session, tenant_id)

    student = Student(
        tenant_id=tenant_id,
        admission_number=admission_number,
        full_name=payload.full_name,
        first_name=payload.first_name,
        last_name=payload.last_name,
        date_of_birth=payload.date_of_birth,
        gender=(payload.gender.value if payload.gender else None),
        blood_group=payload.blood_group,
        photo_url=payload.photo_url,
        class_def_id=payload.class_def_id,
        section_id=payload.section_id,
        house_id=payload.house_id,
        admission_date=payload.admission_date or _today(),
        previous_school=payload.previous_school,
        current_class_label=_format_class_label(cls, section),
        address=payload.address,
        phone=payload.phone,
        email=payload.email,
        aadhaar=payload.aadhaar,
        religion=payload.religion,
        caste=payload.caste,
        category=(payload.category.value if payload.category else None),
        father_name=payload.father_name,
        mother_name=payload.mother_name,
        guardian_name=payload.guardian_name,
        parent_phone=payload.parent_phone,
        parent_email=payload.parent_email,
        parent_occupation=payload.parent_occupation,
        allergies=payload.allergies,
        medical_conditions=payload.medical_conditions,
        emergency_contact_name=payload.emergency_contact_name,
        emergency_phone=payload.emergency_phone,
        roll_no=payload.roll_no,
        remarks=payload.remarks,
        is_active=True,
        status=StudentStatus.ACTIVE.value,
    )
    session.add(student)
    try:
        await session.commit()
    except Exception as exc:
        await session.rollback()
        if "uq_students_tenant_admission" in str(exc).lower() or "unique" in str(exc).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Admission number {admission_number} already in use",
            )
        raise
    await session.refresh(student)
    await _auto_link_siblings(session, tenant_id, student)
    # Phase 8: auto-link parent if contact info was supplied. Local import to
    # avoid a circular dependency between sis and parents services.
    from app.services.parents import autolink_parent_for_student

    await autolink_parent_for_student(session, tenant_id, student)
    await session.refresh(student)
    return student


async def update_student(session: AsyncSession, student: Student, payload: StudentUpdate) -> Student:
    data = payload.model_dump(exclude_unset=True)
    if "gender" in data and data["gender"] is not None:
        data["gender"] = payload.gender.value if payload.gender else None
    if "category" in data and data["category"] is not None:
        data["category"] = payload.category.value if payload.category else None
    if "status" in data and data["status"] is not None:
        data["status"] = payload.status.value if payload.status else None

    for k, v in data.items():
        setattr(student, k, v)

    # Refresh derived class label if placement changed.
    if "class_def_id" in data or "section_id" in data:
        cls = (
            await session.execute(select(ClassDef).where(ClassDef.id == student.class_def_id))
        ).scalar_one_or_none() if student.class_def_id else None
        section = (
            await session.execute(select(Section).where(Section.id == student.section_id))
        ).scalar_one_or_none() if student.section_id else None
        student.current_class_label = _format_class_label(cls, section)

    await session.commit()
    await session.refresh(student)
    return student


# ---- Search + listing ------------------------------------------------------


async def search_students(
    session: AsyncSession,
    *,
    q: Optional[str] = None,
    class_def_id: Optional[int] = None,
    section_id: Optional[int] = None,
    status_filter: Optional[StudentStatus] = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Student], int]:
    stmt = select(Student)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Student.full_name).like(like),
                func.lower(Student.admission_number).like(like),
                func.coalesce(Student.parent_phone, "").like(like),
                func.coalesce(func.lower(Student.parent_email), "").like(like),
            )
        )
    if class_def_id is not None:
        stmt = stmt.where(Student.class_def_id == class_def_id)
    if section_id is not None:
        stmt = stmt.where(Student.section_id == section_id)
    if status_filter is not None:
        stmt = stmt.where(Student.status == status_filter.value)

    total = int(
        (
            await session.execute(select(func.count()).select_from(stmt.subquery()))
        ).scalar_one()
    )
    stmt = stmt.order_by(Student.full_name).offset(offset).limit(limit)
    rows = (await session.execute(stmt)).scalars().all()
    return list(rows), total


# ---- Promotion + withdrawal ------------------------------------------------


async def promote(
    session: AsyncSession,
    payload: PromotionRequest,
) -> PromotionResult:
    target_cls = (
        await session.execute(select(ClassDef).where(ClassDef.id == payload.target_class_def_id))
    ).scalar_one_or_none()
    if target_cls is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Target class not found")
    target_section = None
    if payload.target_section_id is not None:
        target_section = (
            await session.execute(select(Section).where(Section.id == payload.target_section_id))
        ).scalar_one_or_none()
        if target_section is None or target_section.class_def_id != target_cls.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Target section does not belong to target class",
            )

    promoted: list[int] = []
    skipped: list[dict] = []
    for sid in payload.student_ids:
        student = (await session.execute(select(Student).where(Student.id == sid))).scalar_one_or_none()
        if student is None:
            skipped.append({"id": sid, "reason": "not_found"})
            continue
        if student.status != StudentStatus.ACTIVE.value:
            skipped.append({"id": sid, "reason": f"status={student.status}"})
            continue
        student.class_def_id = target_cls.id
        student.section_id = target_section.id if target_section else None
        student.current_class_label = _format_class_label(target_cls, target_section)
        promoted.append(sid)
    await session.commit()
    return PromotionResult(promoted=promoted, skipped=skipped)


async def withdraw(session: AsyncSession, student: Student, payload: WithdrawRequest) -> Student:
    student.status = payload.status.value
    student.is_active = False
    student.exit_date = payload.exit_date or _today()
    if payload.remarks:
        student.remarks = payload.remarks
    await session.commit()
    await session.refresh(student)
    return student


# ---- Sibling helpers -------------------------------------------------------


async def list_siblings(session: AsyncSession, student: Student) -> list[Student]:
    if student.sibling_group_id is None:
        return []
    rows = (
        await session.execute(
            select(Student).where(
                Student.sibling_group_id == student.sibling_group_id,
                Student.id != student.id,
            )
        )
    ).scalars().all()
    return list(rows)


async def link_siblings(session: AsyncSession, tenant_id: int, student_ids: list[int]) -> int:
    rows = (
        await session.execute(
            select(Student).where(Student.tenant_id == tenant_id, Student.id.in_(student_ids))
        )
    ).scalars().all()
    if len(rows) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Need at least 2 valid students in the same tenant",
        )
    existing = next((s.sibling_group_id for s in rows if s.sibling_group_id), None)
    group = existing or min(s.id for s in rows)
    for s in rows:
        s.sibling_group_id = group
    await session.commit()
    return group


# ---- Admission funnel ------------------------------------------------------


async def list_admissions(
    session: AsyncSession,
    *,
    stage: Optional[AdmissionStage] = None,
) -> list[Admission]:
    stmt = select(Admission).order_by(Admission.created_at.desc())
    if stage is not None:
        stmt = stmt.where(Admission.stage == stage.value)
    return list((await session.execute(stmt)).scalars().all())


async def create_admission(
    session: AsyncSession, tenant_id: int, payload: AdmissionWrite
) -> Admission:
    obj = Admission(
        tenant_id=tenant_id,
        full_name=payload.full_name,
        date_of_birth=payload.date_of_birth,
        gender=(payload.gender.value if payload.gender else None),
        parent_name=payload.parent_name,
        parent_phone=payload.parent_phone,
        parent_email=payload.parent_email,
        desired_class_id=payload.desired_class_id,
        previous_school=payload.previous_school,
        notes=payload.notes,
        stage=payload.stage.value,
    )
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return obj


async def admit_from_admission(
    session: AsyncSession,
    tenant_id: int,
    admission: Admission,
) -> Student:
    """Promote an admission row to a real Student row."""
    payload = StudentCreate(
        full_name=admission.full_name,
        date_of_birth=admission.date_of_birth,
        gender=admission.gender,  # type: ignore[arg-type]
        class_def_id=admission.desired_class_id,
        previous_school=admission.previous_school,
        parent_phone=admission.parent_phone,
        parent_email=admission.parent_email,
        father_name=admission.parent_name,  # best-effort
    )
    student = await admit_student(session, tenant_id, payload)
    admission.stage = AdmissionStage.ADMITTED.value
    admission.student_id = student.id
    await session.commit()
    return student
