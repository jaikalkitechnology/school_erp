"""Student-facing endpoints (self-service).

A student logs in and sees *their own* academic data: profile, dashboard,
attendance, timetable, homework (view + submit) and published report
cards. Every route resolves the caller's own Student row via
``Student.user_id`` under a tenant-scoped session, so a student can only
ever read their own records.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import AuthPrincipal, require_roles
from app.core.tenant_session import tenant_scoped_session
from app.schemas.homework import StudentHomeworkRow, SubmissionWrite, SubmissionRead
from app.schemas.parent import ChildDashboard, StudentProfileView
from app.schemas.report_cards import (
    ParentReportCardRow,
    ParentReportCards,
    ReportCardStatus,
)
from app.services.parents import build_student_profile
from app.services.student_self import dashboard_for_self, resolve_self_student


_student_role = require_roles("student")


router = APIRouter(
    prefix="/student",
    tags=["student"],
    dependencies=[Depends(_student_role)],
)


@router.get("/me", response_model=StudentProfileView)
async def student_me(
    principal: AuthPrincipal = Depends(_student_role),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    student = await resolve_self_student(session, principal.user_id)
    return await build_student_profile(
        session, student_id=student.id, tenant_id=principal.tenant_id,
    )


@router.get("/dashboard", response_model=ChildDashboard)
async def student_dashboard(
    principal: AuthPrincipal = Depends(_student_role),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    student = await resolve_self_student(session, principal.user_id)
    return await dashboard_for_self(session, student)


@router.get("/attendance")
async def student_attendance(
    limit: int = Query(default=60, ge=1, le=365),
    principal: AuthPrincipal = Depends(_student_role),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    from app.services.attendance import student_history

    student = await resolve_self_student(session, principal.user_id)
    return await student_history(session, student_id=student.id, limit=limit)


@router.get("/attendance/by-subject")
async def student_attendance_by_subject_route(
    window_days: int = Query(default=90, ge=7, le=365),
    principal: AuthPrincipal = Depends(_student_role),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    from app.services.attendance import student_attendance_by_subject

    student = await resolve_self_student(session, principal.user_id)
    return await student_attendance_by_subject(
        session, student_id=student.id, window_days=window_days,
    )


@router.get("/timetable")
async def student_timetable(
    principal: AuthPrincipal = Depends(_student_role),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    from app.services.attendance import student_timetable_view

    student = await resolve_self_student(session, principal.user_id)
    return await student_timetable_view(session, student_id=student.id)


@router.get("/homework", response_model=list[StudentHomeworkRow])
async def student_homework(
    principal: AuthPrincipal = Depends(_student_role),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    from app.services.homework import list_for_student

    student = await resolve_self_student(session, principal.user_id)
    return await list_for_student(session, student.id)


@router.post(
    "/homework/submit",
    response_model=SubmissionRead,
    status_code=status.HTTP_201_CREATED,
)
async def student_submit_homework(
    payload: SubmissionWrite,
    principal: AuthPrincipal = Depends(_student_role),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    from app.services.homework import submit_homework

    student = await resolve_self_student(session, principal.user_id)
    return await submit_homework(
        session,
        tenant_id=principal.tenant_id,
        student_id=student.id,
        submitted_by_user_id=principal.user_id,
        payload=payload,
    )


@router.get("/report-cards", response_model=ParentReportCards)
async def student_report_cards(
    principal: AuthPrincipal = Depends(_student_role),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    from app.services.report_cards import parent_child_cards

    student = await resolve_self_student(session, principal.user_id)
    cards = await parent_child_cards(session, student.id)
    rows: list[ParentReportCardRow] = []
    for rc in cards:
        snap = rc.snapshot or {}
        rows.append(
            ParentReportCardRow(
                report_card_id=rc.id,
                exam_id=rc.exam_id,
                exam_name=snap.get("exam_name", ""),
                status=ReportCardStatus(rc.status),
                percentage=rc.percentage,
                overall_grade=rc.overall_grade,
                rank_in_section=rc.rank_in_section,
                pdf_url=f"/v1/parent/report-cards/{rc.id}/pdf",
                published_at=rc.published_at,
            )
        )
    return ParentReportCards(student_id=student.id, rows=rows)
