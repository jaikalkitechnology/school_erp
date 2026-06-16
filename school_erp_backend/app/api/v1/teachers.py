"""Teacher Management endpoints (Phase 7)."""

from __future__ import annotations

from datetime import date as _date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import AuthPrincipal, require_roles
from app.core.tenant_session import tenant_scoped_session
from app.models.teacher import EmploymentStatus, Teacher, TeacherSubject
from app.schemas.teacher import (
    AssignClassTeacher,
    AssignSectionSubject,
    SubstitutionCandidate,
    TeacherAttendanceBulkWrite,
    TeacherAttendanceRead,
    TeacherAttendanceWrite,
    TeacherCreate,
    TeacherListPage,
    TeacherRead,
    TeacherSubjectRead,
    TeacherSubjectsBulk,
    TeacherUpdate,
    TeacherWorkload,
)
from app.services.teachers import (
    assign_class_teacher,
    assign_section_subject,
    attendance_for_teacher,
    bulk_attendance,
    clear_section_subject_teacher,
    onboard_teacher,
    search_teachers,
    set_qualified_subjects,
    substitution_pool,
    update_teacher,
    upsert_attendance,
    workload,
)


_school_staff_read = require_roles(
    "school_admin", "principal", "vice_principal", "coordinator",
    "class_teacher", "subject_teacher", "office_staff",
)
_school_admin = require_roles("school_admin", "principal", "vice_principal")


router = APIRouter(
    prefix="/school-admin/teachers",
    tags=["school-admin"],
    dependencies=[Depends(_school_staff_read)],
)


async def _get_teacher(session: AsyncSession, teacher_id: int) -> Teacher:
    t = (await session.execute(select(Teacher).where(Teacher.id == teacher_id))).scalar_one_or_none()
    if t is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teacher not found")
    return t


# ---- List + detail ----------------------------------------------------------


@router.get("", response_model=TeacherListPage)
async def list_teachers(
    q: Optional[str] = Query(default=None, max_length=100),
    department_id: Optional[int] = None,
    status_filter: Optional[EmploymentStatus] = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    rows, total = await search_teachers(
        session, q=q, department_id=department_id, employment_status=status_filter, limit=limit, offset=offset
    )
    return TeacherListPage(
        items=[TeacherRead.model_validate(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/substitution-pool", response_model=list[SubstitutionCandidate])
async def substitution_pool_route(
    target_date: _date = Query(default_factory=_date.today),
    subject_id: Optional[int] = None,
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await substitution_pool(session, target_date=target_date, subject_id=subject_id)


@router.get("/{teacher_id}", response_model=TeacherRead)
async def get_teacher(teacher_id: int, session: AsyncSession = Depends(tenant_scoped_session)):
    return await _get_teacher(session, teacher_id)


@router.post("", response_model=TeacherRead, status_code=status.HTTP_201_CREATED)
async def create_teacher(
    payload: TeacherCreate,
    principal: AuthPrincipal = Depends(_school_admin),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await onboard_teacher(session, principal.tenant_id, payload)


@router.patch("/{teacher_id}", response_model=TeacherRead)
async def patch_teacher(
    teacher_id: int,
    payload: TeacherUpdate,
    principal: AuthPrincipal = Depends(_school_admin),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    teacher = await _get_teacher(session, teacher_id)
    return await update_teacher(session, teacher, payload)


@router.delete("/{teacher_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_teacher_route(
    teacher_id: int,
    principal: AuthPrincipal = Depends(_school_admin),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    """Hard-delete a teacher row + the linked User login.

    Cascading FKs handle TeacherSubject + TeacherAttendance. SectionSubject
    + Section.in_charge_user_id are SET NULL, so any sections this teacher
    was covering become "unassigned" rather than getting orphaned. For
    teachers with history you actually care about (attendance, marks
    entered), set employment_status='resigned' via PATCH instead — this
    DELETE is for data-entry mistakes."""
    from app.models.auth import User

    teacher = await _get_teacher(session, teacher_id)
    user_id = teacher.user_id
    await session.delete(teacher)
    if user_id:
        user = (
            await session.execute(select(User).where(User.id == user_id))
        ).scalar_one_or_none()
        if user is not None:
            await session.delete(user)
    await session.commit()


# ---- Subject qualifications -------------------------------------------------


@router.get("/{teacher_id}/qualified-subjects", response_model=list[TeacherSubjectRead])
async def list_qualified(teacher_id: int, session: AsyncSession = Depends(tenant_scoped_session)):
    await _get_teacher(session, teacher_id)
    return list(
        (
            await session.execute(
                select(TeacherSubject).where(TeacherSubject.teacher_id == teacher_id)
            )
        ).scalars().all()
    )


@router.put("/{teacher_id}/qualified-subjects", response_model=list[TeacherSubjectRead])
async def replace_qualified(
    teacher_id: int,
    payload: TeacherSubjectsBulk,
    principal: AuthPrincipal = Depends(_school_admin),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    teacher = await _get_teacher(session, teacher_id)
    return await set_qualified_subjects(session, principal.tenant_id, teacher, payload.subject_ids)


# ---- Section assignment -----------------------------------------------------


@router.post("/{teacher_id}/assign-section-subject")
async def assign_section_subject_route(
    teacher_id: int,
    payload: AssignSectionSubject,
    principal: AuthPrincipal = Depends(_school_admin),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    teacher = await _get_teacher(session, teacher_id)
    ss = await assign_section_subject(session, teacher, payload.section_subject_id)
    return {"id": ss.id, "teacher_user_id": ss.teacher_user_id}


@router.delete("/section-subjects/{section_subject_id}/teacher")
async def clear_section_subject_route(
    section_subject_id: int,
    principal: AuthPrincipal = Depends(_school_admin),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    ss = await clear_section_subject_teacher(session, section_subject_id)
    return {"id": ss.id, "teacher_user_id": ss.teacher_user_id}


@router.post("/{teacher_id}/assign-class-teacher")
async def assign_class_teacher_route(
    teacher_id: int,
    payload: AssignClassTeacher,
    principal: AuthPrincipal = Depends(_school_admin),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    teacher = await _get_teacher(session, teacher_id)
    section = await assign_class_teacher(session, teacher, payload.section_id)
    return {"section_id": section.id, "in_charge_user_id": section.in_charge_user_id}


# ---- Workload ---------------------------------------------------------------


@router.get("/{teacher_id}/workload", response_model=TeacherWorkload)
async def get_workload(teacher_id: int, session: AsyncSession = Depends(tenant_scoped_session)):
    teacher = await _get_teacher(session, teacher_id)
    return await workload(session, teacher)


# ---- Attendance -------------------------------------------------------------


@router.post("/{teacher_id}/attendance", response_model=TeacherAttendanceRead)
async def upsert_attendance_route(
    teacher_id: int,
    payload: TeacherAttendanceWrite,
    principal: AuthPrincipal = Depends(_school_admin),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    teacher = await _get_teacher(session, teacher_id)
    return await upsert_attendance(session, principal.tenant_id, teacher, payload)


@router.get("/{teacher_id}/attendance", response_model=list[TeacherAttendanceRead])
async def list_attendance(
    teacher_id: int,
    start: Optional[_date] = None,
    end: Optional[_date] = None,
    session: AsyncSession = Depends(tenant_scoped_session),
):
    teacher = await _get_teacher(session, teacher_id)
    return await attendance_for_teacher(session, teacher, start=start, end=end)


@router.post("/attendance/bulk")
async def bulk_attendance_route(
    payload: TeacherAttendanceBulkWrite,
    principal: AuthPrincipal = Depends(_school_admin),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    written = await bulk_attendance(session, principal.tenant_id, payload)
    return {"written": written}


# ---- Substitution pool route is declared at the top of the file so it
# matches before /{teacher_id}.
