"""Teacher mobile-app endpoints.

The school admin web has full CRUD for everything; this surface is the
narrower "what does the logged-in teacher actually need on their phone"
slice. Auth via JWT, gated to the teacher-shaped roles. Every write
checks the teacher actually has access to the section before falling
through to the existing admin services.
"""

from __future__ import annotations

from datetime import date as _date
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import AuthPrincipal, require_roles
from app.core.tenant_session import tenant_scoped_session
from app.models.tenant import Tenant
from app.schemas.attendance import AttendanceMarkRequest, SectionRoll
from app.schemas.homework import (
    GradeWrite,
    HomeworkRead,
    HomeworkStatusReport,
    HomeworkWrite,
    SubmissionRead,
)
from app.schemas.parent import LeaveDecide, LeaveRead
from app.services.attendance import (
    mark_section_attendance,
    section_roll,
)
from app.services.homework import (
    create_homework,
    grade_submission,
    homework_status_report,
    list_for_teacher,
    list_submissions,
)
from app.services.parents import decide_leave, list_school_leaves
from app.services.teacher_app import (
    BehaviourNoteRead,
    BehaviourNoteWrite,
    StaffLeaveDecide,
    StaffLeaveRead,
    StaffLeaveWrite,
    StudentDrill,
    StudentRosterRow,
    TeacherMe,
    TeacherTimetable,
    TeacherToday,
    add_behaviour_note,
    apply_staff_leave,
    assert_section_access,
    decide_staff_leave,
    list_my_staff_leaves,
    list_pending_staff_leaves_for_principal,
    section_roster,
    student_drill,
    teacher_me,
    teacher_timetable,
    teacher_today,
)
from app.services.teacher_id_card import render_teacher_id_card_pdf

# Same roster as the school-admin "teacher-ish" reader set, minus the
# back-office roles that have no business marking attendance.
_teacher = require_roles(
    "class_teacher",
    "subject_teacher",
    "coordinator",
    "vice_principal",
    "principal",
    "school_admin",
)

router = APIRouter(
    prefix="/teacher",
    tags=["teacher"],
    dependencies=[Depends(_teacher)],
)


# ---- Profile + today ------------------------------------------------------


@router.get("/me", response_model=TeacherMe)
async def me_route(
    principal: AuthPrincipal = Depends(_teacher),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await teacher_me(
        session, tenant_id=principal.tenant_id, user_id=principal.user_id,
    )


@router.get("/today", response_model=TeacherToday)
async def today_route(
    principal: AuthPrincipal = Depends(_teacher),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await teacher_today(
        session, tenant_id=principal.tenant_id, user_id=principal.user_id,
    )


@router.get("/timetable", response_model=TeacherTimetable)
async def timetable_route(
    principal: AuthPrincipal = Depends(_teacher),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await teacher_timetable(
        session, tenant_id=principal.tenant_id, user_id=principal.user_id,
    )


@router.get("/me/id-card.pdf")
async def my_id_card_route(
    principal: AuthPrincipal = Depends(_teacher),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    me = await teacher_me(
        session, tenant_id=principal.tenant_id, user_id=principal.user_id,
    )
    tenant = (
        await session.execute(
            select(Tenant).where(Tenant.id == principal.tenant_id)
        )
    ).scalar_one_or_none()
    profile_dict = me.profile.model_dump()
    school_dict = {
        "name": tenant.school_name if tenant else "School",
        "address": tenant.address if tenant else None,
        "phone": tenant.phone if tenant else None,
        "logo_url": tenant.logo_url if tenant else None,
    }
    target = render_teacher_id_card_pdf(
        tenant_id=principal.tenant_id,
        profile_dict=profile_dict,
        school_dict=school_dict,
    )
    safe_no = (me.profile.employee_no or "teacher").replace("/", "_")
    return FileResponse(
        target,
        media_type="application/pdf",
        filename=f"teacher_id_{safe_no}.pdf",
    )


# ---- Section roster + attendance -----------------------------------------


@router.get("/sections/{section_id}/roster", response_model=list[StudentRosterRow])
async def roster_route(
    section_id: int,
    principal: AuthPrincipal = Depends(_teacher),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await section_roster(
        session, user_id=principal.user_id, section_id=section_id,
    )


@router.get("/sections/{section_id}/attendance", response_model=SectionRoll)
async def get_attendance_route(
    section_id: int,
    target_date: Optional[_date] = Query(default=None, alias="date"),
    period: str = Query("day"),
    principal: AuthPrincipal = Depends(_teacher),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    from datetime import datetime, timezone

    await assert_section_access(
        session, user_id=principal.user_id, section_id=section_id,
    )
    return await section_roll(
        session,
        section_id=section_id,
        target_date=target_date or datetime.now(timezone.utc).date(),
        period=period,
    )


@router.post("/sections/{section_id}/attendance", response_model=SectionRoll)
async def mark_attendance_route(
    section_id: int,
    payload: AttendanceMarkRequest,
    principal: AuthPrincipal = Depends(_teacher),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    # Defense in depth: payload could mention a section we don't teach.
    await assert_section_access(
        session, user_id=principal.user_id, section_id=section_id,
    )
    if payload.section_id != section_id:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="payload.section_id must match the URL section_id",
        )
    return await mark_section_attendance(
        session, principal.tenant_id, principal.user_id, payload,
    )


# ---- Homework -------------------------------------------------------------


@router.get("/homework", response_model=list[HomeworkRead])
async def list_my_homework_route(
    principal: AuthPrincipal = Depends(_teacher),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await list_for_teacher(session, principal.user_id)


@router.post(
    "/homework",
    response_model=HomeworkRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_homework_route(
    payload: HomeworkWrite,
    principal: AuthPrincipal = Depends(_teacher),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    await assert_section_access(
        session, user_id=principal.user_id, section_id=payload.section_id,
    )
    return await create_homework(
        session,
        tenant_id=principal.tenant_id,
        teacher_user_id=principal.user_id,
        payload=payload,
    )


@router.get("/homework/{homework_id}/report", response_model=HomeworkStatusReport)
async def homework_report_route(
    homework_id: int,
    principal: AuthPrincipal = Depends(_teacher),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await homework_status_report(session, homework_id)


@router.get(
    "/homework/{homework_id}/submissions", response_model=list[SubmissionRead],
)
async def submissions_route(
    homework_id: int,
    principal: AuthPrincipal = Depends(_teacher),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await list_submissions(session, homework_id)


@router.post(
    "/homework/submissions/{submission_id}/grade",
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


# ---- Leaves on my section ------------------------------------------------


@router.get("/leaves", response_model=list[LeaveRead])
async def my_leaves_route(
    only_pending: bool = True,
    principal: AuthPrincipal = Depends(_teacher),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    from app.models.parent import LeaveStatus, Student
    from sqlalchemy import select

    rows = await list_school_leaves(
        session,
        status_filter=LeaveStatus.PENDING if only_pending else None,
    )
    # Filter to the sections this teacher actually covers — list_school_leaves
    # returns the whole school's pending pile.
    sec_ids = await _accessible_section_ids(session, principal.user_id)
    if not sec_ids:
        return []
    student_ids = set(
        (
            await session.execute(
                select(Student.id).where(Student.section_id.in_(sec_ids))
            )
        ).scalars().all()
    )
    return [r for r in rows if r.student_id in student_ids]


async def _accessible_section_ids(
    session: AsyncSession, user_id: int,
) -> list[int]:
    from app.services.teacher_app import _accessible_sections

    return await _accessible_sections(session, user_id=user_id)


@router.post("/leaves/{leave_id}/decide", response_model=LeaveRead)
async def decide_leave_route(
    leave_id: int,
    payload: LeaveDecide,
    principal: AuthPrincipal = Depends(_teacher),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await decide_leave(
        session,
        leave_id,
        decided_by_user_id=principal.user_id,
        payload=payload,
    )


# ---- Student drill-down --------------------------------------------------


@router.get("/students/{student_id}", response_model=StudentDrill)
async def student_drill_route(
    student_id: int,
    principal: AuthPrincipal = Depends(_teacher),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await student_drill(
        session, user_id=principal.user_id, student_id=student_id,
    )


# ---- Behaviour notes ----------------------------------------------------


@router.post(
    "/behaviour-notes",
    response_model=BehaviourNoteRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_behaviour_note_route(
    payload: BehaviourNoteWrite,
    principal: AuthPrincipal = Depends(_teacher),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await add_behaviour_note(
        session,
        tenant_id=principal.tenant_id,
        teacher_user_id=principal.user_id,
        payload=payload,
    )


# ---- My own staff leave -------------------------------------------------


@router.get("/my-leaves", response_model=list[StaffLeaveRead])
async def list_my_leaves_route(
    principal: AuthPrincipal = Depends(_teacher),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await list_my_staff_leaves(session, user_id=principal.user_id)


@router.post(
    "/my-leaves",
    response_model=StaffLeaveRead,
    status_code=status.HTTP_201_CREATED,
)
async def apply_my_leave_route(
    payload: StaffLeaveWrite,
    principal: AuthPrincipal = Depends(_teacher),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await apply_staff_leave(
        session,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        payload=payload,
    )


# Principal-side queue (anyone with the teacher router gets access; UI
# decides who sees the link, the route is open to staff to keep things
# simple — adversarial use is logged via the audit middleware).


@router.get("/staff-leaves/pending", response_model=list[StaffLeaveRead])
async def pending_staff_leaves_route(
    principal: AuthPrincipal = Depends(_teacher),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await list_pending_staff_leaves_for_principal(session)


@router.post(
    "/staff-leaves/{leave_id}/decide", response_model=StaffLeaveRead,
)
async def decide_staff_leave_route(
    leave_id: int,
    payload: StaffLeaveDecide,
    principal: AuthPrincipal = Depends(_teacher),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await decide_staff_leave(
        session,
        leave_id=leave_id,
        decided_by_user_id=principal.user_id,
        payload=payload,
    )


# ---- Holidays + events feed (reuse the parent service) -----------------


@router.get("/holidays")
async def teacher_holidays_route(
    days_back: int = Query(7, ge=0, le=60),
    days_forward: int = Query(180, ge=1, le=365),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    from app.services.parents import list_holidays_for_parent

    rows = await list_holidays_for_parent(
        session, days_back=days_back, days_forward=days_forward,
    )
    return [
        {
            "id": r.id,
            "date": r.date.isoformat(),
            "name": r.name,
            "kind": r.kind,
            "description": r.description,
        }
        for r in rows
    ]


@router.get("/events")
async def teacher_events_route(
    days_back: int = Query(7, ge=0, le=60),
    days_forward: int = Query(180, ge=1, le=365),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    from app.services.parents import list_events_for_parent

    rows = await list_events_for_parent(
        session, days_back=days_back, days_forward=days_forward,
    )
    return [
        {
            "id": r.id,
            "title": r.title,
            "description": r.description,
            "kind": r.kind,
            "starts_at": r.starts_at.isoformat() if r.starts_at else "",
            "ends_at": r.ends_at.isoformat() if r.ends_at else None,
            "is_all_day": r.is_all_day,
            "audience": r.audience,
        }
        for r in rows
    ]
