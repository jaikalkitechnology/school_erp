"""Exam endpoints (Phase 15)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import AuthPrincipal, require_roles
from app.core.tenant_session import platform_session, tenant_scoped_session
from app.models.parent import Parent, ParentChildMapping
from app.schemas.exams import (
    ExamRead,
    ExamResults,
    ExamSubjectRead,
    ExamSubjectWrite,
    ExamWrite,
    GradeScaleRead,
    GradeScaleWrite,
    MarkBulkRequest,
    ParentChildExams,
    SectionRoster,
)
from app.services.exams import (
    create_exam,
    list_exam_subjects,
    list_exams,
    list_grade_scales,
    parent_child_results,
    publish_exam,
    schedule_subject,
    section_results,
    section_roster,
    upsert_grade_scale,
    upsert_marks,
)


_school_admin = require_roles("school_admin", "principal", "vice_principal")
_teacher = require_roles(
    "school_admin", "principal", "vice_principal", "coordinator",
    "class_teacher", "subject_teacher",
)
_parent = require_roles("parent")


router = APIRouter(
    prefix="/school-admin/exams",
    tags=["school-admin"],
    dependencies=[Depends(_teacher)],
)


@router.get("", response_model=list[ExamRead])
async def list_exams_route(session: AsyncSession = Depends(tenant_scoped_session)):
    return await list_exams(session)


@router.post("", response_model=ExamRead, status_code=status.HTTP_201_CREATED)
async def create_exam_route(
    payload: ExamWrite,
    principal: AuthPrincipal = Depends(_school_admin),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await create_exam(session, principal.tenant_id, payload)


@router.post("/{exam_id}/publish", response_model=ExamRead)
async def publish_exam_route(
    exam_id: int,
    principal: AuthPrincipal = Depends(_school_admin),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await publish_exam(session, exam_id)


@router.get("/{exam_id}/subjects", response_model=list[ExamSubjectRead])
async def list_subjects_route(
    exam_id: int, session: AsyncSession = Depends(tenant_scoped_session)
):
    return await list_exam_subjects(session, exam_id)


@router.post(
    "/{exam_id}/subjects",
    response_model=ExamSubjectRead,
    status_code=status.HTTP_201_CREATED,
)
async def schedule_subject_route(
    exam_id: int,
    payload: ExamSubjectWrite,
    principal: AuthPrincipal = Depends(_school_admin),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await schedule_subject(session, principal.tenant_id, exam_id, payload)


@router.get("/exam-subjects/{exam_subject_id}/roster", response_model=SectionRoster)
async def roster_route(
    exam_subject_id: int,
    section_id: int,
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await section_roster(session, exam_subject_id, section_id)


@router.post("/marks/bulk")
async def bulk_marks_route(
    payload: MarkBulkRequest,
    principal: AuthPrincipal = Depends(_teacher),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    written = await upsert_marks(session, principal.tenant_id, principal.user_id, payload)
    return {"written": written}


@router.get("/{exam_id}/results", response_model=ExamResults)
async def results_route(
    exam_id: int,
    section_id: int,
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await section_results(session, exam_id=exam_id, section_id=section_id)


# ---- Grade scale -----------------------------------------------------------


grade_router = APIRouter(
    prefix="/school-admin/grade-scales",
    tags=["school-admin"],
    dependencies=[Depends(_teacher)],
)


@grade_router.get("", response_model=list[GradeScaleRead])
async def list_grade_scales_route(session: AsyncSession = Depends(tenant_scoped_session)):
    return await list_grade_scales(session)


@grade_router.put("", response_model=GradeScaleRead)
async def upsert_grade_scale_route(
    payload: GradeScaleWrite,
    principal: AuthPrincipal = Depends(_school_admin),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await upsert_grade_scale(session, principal.tenant_id, payload)


# ---- Parent view -----------------------------------------------------------


parent_router = APIRouter(
    prefix="/parent", tags=["parent"], dependencies=[Depends(_parent)]
)


@parent_router.get(
    "/children/{student_id}/exam-results",
    response_model=ParentChildExams,
)
async def parent_results_route(
    student_id: int,
    principal: AuthPrincipal = Depends(_parent),
    session: AsyncSession = Depends(platform_session),
):
    parent = (
        await session.execute(select(Parent).where(Parent.user_id == principal.user_id))
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
    return await parent_child_results(session, student_id)
