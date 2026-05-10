"""Homework endpoints (Phase 14)."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import AuthPrincipal, require_roles
from app.core.tenant_session import platform_session, tenant_scoped_session
from app.models.homework import Homework
from app.models.parent import Parent, ParentChildMapping
from app.schemas.homework import (
    GradeWrite,
    HomeworkRead,
    HomeworkStatusReport,
    HomeworkUpdate,
    HomeworkWrite,
    StudentHomeworkRow,
    SubmissionRead,
    SubmissionWrite,
)
from app.services.homework import (
    create_homework,
    delete_homework,
    grade_submission,
    homework_status_report,
    list_for_section,
    list_for_student,
    list_for_teacher,
    list_submissions,
    submit_homework,
    update_homework,
)


_school_admin = require_roles("school_admin", "principal", "vice_principal")
_teacher = require_roles(
    "school_admin", "principal", "vice_principal", "coordinator",
    "class_teacher", "subject_teacher",
)
_parent = require_roles("parent")


router = APIRouter(
    prefix="/school-admin/homework",
    tags=["school-admin"],
    dependencies=[Depends(_teacher)],
)


@router.get("", response_model=list[HomeworkRead])
async def list_route(
    section_id: Optional[int] = None,
    teacher_user_id: Optional[int] = None,
    upcoming_only: bool = False,
    session: AsyncSession = Depends(tenant_scoped_session),
):
    if section_id is not None:
        return await list_for_section(session, section_id=section_id, upcoming_only=upcoming_only)
    if teacher_user_id is not None:
        return await list_for_teacher(session, teacher_user_id)
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Provide section_id or teacher_user_id",
    )


@router.post("", response_model=HomeworkRead, status_code=status.HTTP_201_CREATED)
async def create_route(
    payload: HomeworkWrite,
    principal: AuthPrincipal = Depends(_teacher),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await create_homework(
        session,
        tenant_id=principal.tenant_id,
        teacher_user_id=principal.user_id,
        payload=payload,
    )


@router.patch("/{homework_id}", response_model=HomeworkRead)
async def update_route(
    homework_id: int,
    payload: HomeworkUpdate,
    principal: AuthPrincipal = Depends(_teacher),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await update_homework(session, homework_id, payload)


@router.delete("/{homework_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_route(
    homework_id: int,
    principal: AuthPrincipal = Depends(_school_admin),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    await delete_homework(session, homework_id)


@router.get("/{homework_id}/submissions", response_model=list[SubmissionRead])
async def submissions_route(
    homework_id: int,
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await list_submissions(session, homework_id)


@router.get("/{homework_id}/report", response_model=HomeworkStatusReport)
async def report_route(
    homework_id: int,
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await homework_status_report(session, homework_id)


@router.post(
    "/submissions/{submission_id}/grade",
    response_model=SubmissionRead,
)
async def grade_route(
    submission_id: int,
    payload: GradeWrite,
    principal: AuthPrincipal = Depends(_teacher),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await grade_submission(
        session,
        submission_id=submission_id,
        teacher_user_id=principal.user_id,
        payload=payload,
    )


# ---- Parent-facing ---------------------------------------------------------


parent_router = APIRouter(prefix="/parent", tags=["parent"], dependencies=[Depends(_parent)])


async def _ensure_linked(
    session: AsyncSession, *, user_id: int, student_id: int
) -> None:
    parent = (
        await session.execute(
            select(Parent).where(Parent.user_id == user_id)
        )
    ).scalar_one_or_none()
    if parent is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a parent account")
    linked = (
        await session.execute(
            select(ParentChildMapping.id).where(
                ParentChildMapping.parent_id == parent.id,
                ParentChildMapping.student_id == student_id,
            )
        )
    ).scalar_one_or_none()
    if linked is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Child not linked")


@parent_router.get(
    "/children/{student_id}/homework", response_model=list[StudentHomeworkRow]
)
async def parent_child_homework(
    student_id: int,
    principal: AuthPrincipal = Depends(_parent),
    session: AsyncSession = Depends(platform_session),
):
    await _ensure_linked(session, user_id=principal.user_id, student_id=student_id)
    return await list_for_student(session, student_id)


@parent_router.post(
    "/children/{student_id}/homework/submit",
    response_model=SubmissionRead,
    status_code=status.HTTP_201_CREATED,
)
async def parent_submit(
    student_id: int,
    payload: SubmissionWrite,
    principal: AuthPrincipal = Depends(_parent),
    session: AsyncSession = Depends(platform_session),
):
    await _ensure_linked(session, user_id=principal.user_id, student_id=student_id)
    return await submit_homework(
        session,
        tenant_id=principal.tenant_id,
        student_id=student_id,
        submitted_by_user_id=principal.user_id,
        payload=payload,
    )
