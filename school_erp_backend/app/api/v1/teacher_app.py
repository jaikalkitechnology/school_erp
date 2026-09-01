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

from fastapi import APIRouter, Depends, HTTPException, Query, status
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
from app.schemas.exams import MarkBulkRequest
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


@router.get("/me/attendance/today")
async def my_today_attendance_route(
    principal: AuthPrincipal = Depends(_teacher),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    """Today's attendance row for the logged-in teacher, or null if
    they haven't been marked yet. Powers the "Mark me present" tile
    on the Today screen."""
    from datetime import datetime, timezone

    from sqlalchemy import select

    from app.models.teacher import Teacher, TeacherAttendance

    today = datetime.now(timezone.utc).date()
    teacher = (
        await session.execute(
            select(Teacher).where(
                Teacher.tenant_id == principal.tenant_id,
                Teacher.user_id == principal.user_id,
            )
        )
    ).scalar_one_or_none()
    if teacher is None:
        return {"date": today.isoformat(), "status": None, "teacher_id": None}
    row = (
        await session.execute(
            select(TeacherAttendance).where(
                TeacherAttendance.teacher_id == teacher.id,
                TeacherAttendance.date == today,
            )
        )
    ).scalar_one_or_none()
    return {
        "date": today.isoformat(),
        "teacher_id": teacher.id,
        "status": row.status if row else None,
        "remarks": row.remarks if row else None,
    }


@router.post("/me/attendance/mark")
async def mark_my_attendance_route(
    principal: AuthPrincipal = Depends(_teacher),
    session: AsyncSession = Depends(tenant_scoped_session),
    payload: dict | None = None,
):
    """One-tap "mark me present" from the teacher Today screen.

    Mirrors the admin's Staff attendance roll → the same row shows up
    on /v1/school-admin/teachers/attendance/roll the moment this lands.
    Defaults status to 'present'; pass {"status": "..."} to choose
    something else (handy if the teacher is leaving early)."""
    from datetime import datetime, timezone

    from sqlalchemy import select

    from app.models.teacher import Teacher, TeacherAttendance

    payload = payload or {}
    status_value = (payload.get("status") or "present").lower()
    if status_value not in {"present", "absent", "leave", "half_day"}:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="status must be present / absent / leave / half_day",
        )

    today = datetime.now(timezone.utc).date()
    teacher = (
        await session.execute(
            select(Teacher).where(
                Teacher.tenant_id == principal.tenant_id,
                Teacher.user_id == principal.user_id,
            )
        )
    ).scalar_one_or_none()
    if teacher is None:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No teacher profile linked to this user.",
        )

    existing = (
        await session.execute(
            select(TeacherAttendance).where(
                TeacherAttendance.teacher_id == teacher.id,
                TeacherAttendance.date == today,
            )
        )
    ).scalar_one_or_none()
    if existing is None:
        existing = TeacherAttendance(
            tenant_id=principal.tenant_id,
            teacher_id=teacher.id,
            date=today,
            status=status_value,
            remarks=payload.get("remarks"),
        )
        session.add(existing)
    else:
        existing.status = status_value
        if payload.get("remarks") is not None:
            existing.remarks = payload.get("remarks")
    await session.commit()
    await session.refresh(existing)
    return {
        "date": today.isoformat(),
        "teacher_id": teacher.id,
        "status": existing.status,
        "remarks": existing.remarks,
    }


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


@router.get("/students/{student_id}/marks")
async def student_marks_route(
    student_id: int,
    principal: AuthPrincipal = Depends(_teacher),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    """All exam results for a student the teacher has access to.

    Reuses the parent_child_results aggregator (same shape as the
    parent app's "exam results" tab). Teacher access is gated by
    section: if the student's section isn't on this teacher's roster,
    we 403."""
    from sqlalchemy import select

    from app.models.parent import Student
    from app.services.exams import parent_child_results

    student = (
        await session.execute(select(Student).where(Student.id == student_id))
    ).scalar_one_or_none()
    if student is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Student not found",
        )
    if student.section_id is None:
        return {"student_id": student_id, "exams": []}
    await assert_section_access(
        session, user_id=principal.user_id, section_id=student.section_id,
    )
    return await parent_child_results(session, student_id=student_id)


# ---- Chat (1-on-1 messages) ---------------------------------------------


@router.get("/messages/inbox")
async def my_inbox_route(
    principal: AuthPrincipal = Depends(_teacher),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    """Wrapper around comms.inbox_for so the teacher app doesn't need
    to know the platform-level /v1/messages route exists."""
    from app.services.comms import inbox_for

    rows = await inbox_for(session, principal.user_id)
    return [
        {
            "id": r.id,
            "sender_user_id": r.sender_user_id,
            "recipient_user_id": r.recipient_user_id,
            "subject": r.subject,
            "body": r.body,
            "read_at": r.read_at.isoformat() if r.read_at else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.get("/messages/sent")
async def my_sent_route(
    principal: AuthPrincipal = Depends(_teacher),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    from app.services.comms import sent_for

    rows = await sent_for(session, principal.user_id)
    return [
        {
            "id": r.id,
            "sender_user_id": r.sender_user_id,
            "recipient_user_id": r.recipient_user_id,
            "subject": r.subject,
            "body": r.body,
            "read_at": r.read_at.isoformat() if r.read_at else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.post("/messages/send", status_code=status.HTTP_201_CREATED)
async def send_message_route(
    payload: dict,
    principal: AuthPrincipal = Depends(_teacher),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    """Send a 1-on-1 message to a parent / admin / student. Payload
    must include recipient_user_id + body; subject is optional."""
    from app.schemas.comms import MessageSend
    from app.services.comms import send_message

    msg = await send_message(
        session,
        principal.tenant_id,
        principal.user_id,
        MessageSend(
            recipient_user_id=int(payload.get("recipient_user_id") or 0),
            subject=payload.get("subject"),
            body=str(payload.get("body") or "").strip(),
        ),
    )
    return {
        "id": msg.id,
        "sender_user_id": msg.sender_user_id,
        "recipient_user_id": msg.recipient_user_id,
        "subject": msg.subject,
        "body": msg.body,
        "created_at": msg.created_at.isoformat() if msg.created_at else None,
    }


@router.post("/messages/{message_id}/read")
async def mark_msg_read_route(
    message_id: int,
    principal: AuthPrincipal = Depends(_teacher),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    from app.services.comms import mark_message_read

    msg = await mark_message_read(session, message_id, principal.user_id)
    return {
        "id": msg.id,
        "read_at": msg.read_at.isoformat() if msg.read_at else None,
    }


@router.get("/messages/contacts")
async def chat_contacts_route(
    principal: AuthPrincipal = Depends(_teacher),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    """Suggested chat targets for the teacher: school admins +
    principals (admin chat), and parents of students in any section
    the teacher covers (parent chat). Students don't get an entry —
    they don't have logins on this app surface."""
    from sqlalchemy import select

    from app.models.auth import Role, User, UserRole
    from app.models.parent import Parent, ParentChildMapping, Student

    # Admins + principals.
    admins = list(
        (
            await session.execute(
                select(User)
                .join(UserRole, UserRole.user_id == User.id)
                .join(Role, Role.id == UserRole.role_id)
                .where(
                    User.tenant_id == principal.tenant_id,
                    User.is_active.is_(True),
                    Role.code.in_(["school_admin", "principal", "vice_principal"]),
                )
            )
        ).unique().scalars().all()
    )

    # Parents of accessible students.
    accessible = await _accessible_section_ids(session, principal.user_id)
    parent_rows: list[User] = []
    if accessible:
        students_in_my_sections = list(
            (
                await session.execute(
                    select(Student.id).where(Student.section_id.in_(accessible))
                )
            ).scalars().all()
        )
        if students_in_my_sections:
            parent_rows = list(
                (
                    await session.execute(
                        select(User)
                        .join(Parent, Parent.user_id == User.id)
                        .join(
                            ParentChildMapping,
                            ParentChildMapping.parent_id == Parent.id,
                        )
                        .where(
                            ParentChildMapping.student_id.in_(students_in_my_sections),
                            User.is_active.is_(True),
                        )
                    )
                ).unique().scalars().all()
            )

    def _u(u: User, kind: str) -> dict:
        return {
            "user_id": u.id,
            "full_name": u.full_name,
            "kind": kind,
            "email": u.email,
            "phone": u.phone,
        }

    seen: set[int] = set()
    out: list[dict] = []
    for u in admins:
        if u.id in seen:
            continue
        seen.add(u.id)
        out.append(_u(u, "admin"))
    for u in parent_rows:
        if u.id in seen:
            continue
        seen.add(u.id)
        out.append(_u(u, "parent"))
    return out


@router.get("/students/{student_id}", response_model=StudentDrill)
async def student_drill_route(
    student_id: int,
    principal: AuthPrincipal = Depends(_teacher),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    """The service already wraps the optional bits (attendance,
    behaviour notes) in try/except so a partially-migrated DB doesn't
    take the response 500. Anything we still see here is a real bug —
    wrap once more so the FastAPI default 500 page gets replaced with
    a JSON detail the mobile app can render in its error card."""
    import logging

    try:
        return await student_drill(
            session, user_id=principal.user_id, student_id=student_id,
        )
    except HTTPException:
        raise
    except Exception as e:
        logging.getLogger(__name__).exception(
            "student_drill_route failed (user=%s student=%s)",
            principal.user_id, student_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not load student profile: {type(e).__name__}: {e}",
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
    """Wrap the service call so a partially-migrated DB (missing the
    behaviour_notes table) returns 503 with an actionable message
    instead of FastAPI's default 500 stack."""
    import logging

    from sqlalchemy.exc import OperationalError, ProgrammingError

    try:
        return await add_behaviour_note(
            session,
            tenant_id=principal.tenant_id,
            teacher_user_id=principal.user_id,
            payload=payload,
        )
    except HTTPException:
        raise
    except (OperationalError, ProgrammingError) as exc:
        # MySQL: "Table 'X.behaviour_notes' doesn't exist" (1146).
        # Postgres: "relation behaviour_notes does not exist" (42P01).
        msg = str(exc.orig if hasattr(exc, "orig") else exc)
        if "behaviour_notes" in msg or "doesn't exist" in msg or "does not exist" in msg:
            logging.getLogger(__name__).warning(
                "behaviour_notes table missing: run `alembic upgrade head`. %s", msg,
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "Behaviour notes are not yet enabled on this database. "
                    "Ask the admin to run the latest migration "
                    "(alembic upgrade head)."
                ),
            )
        logging.getLogger(__name__).exception(
            "add_behaviour_note_route DB error", exc_info=exc,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {msg[:200]}",
        )
    except Exception as exc:  # noqa: BLE001
        logging.getLogger(__name__).exception(
            "add_behaviour_note_route failed (user=%s student=%s)",
            principal.user_id, payload.student_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not save the note: {type(exc).__name__}: {exc}",
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


@router.get("/exams")
async def teacher_exams_route(
    days_back: int = Query(30, ge=0, le=180),
    days_forward: int = Query(180, ge=1, le=365),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    """Published exams in a date window — surfaced on the teacher
    Calendar's third tab so the dashboard's "upcoming exams" counter
    has a corresponding feed."""
    from datetime import date, timedelta

    from sqlalchemy import or_

    try:
        from app.models.exams import Exam
    except Exception:
        return []

    today = date.today()
    start = today - timedelta(days=days_back)
    end = today + timedelta(days=days_forward)

    rows = list(
        (
            await session.execute(
                select(Exam)
                .where(
                    Exam.published_at.isnot(None),
                    or_(
                        Exam.start_date.is_(None),
                        Exam.start_date.between(start, end),
                    ),
                )
                .order_by(Exam.start_date.is_(None), Exam.start_date.asc())
            )
        ).scalars().all()
    )
    return [
        {
            "id": e.id,
            "name": e.name,
            "kind": e.kind,
            "start_date": e.start_date.isoformat() if e.start_date else None,
            "end_date": e.end_date.isoformat() if e.end_date else None,
            "status": e.status,
            "notes": e.notes,
        }
        for e in rows
    ]


@router.get("/exams/{exam_id}/timetable")
async def teacher_exam_timetable_route(
    exam_id: int,
    session: AsyncSession = Depends(tenant_scoped_session),
):
    """Per-subject schedule for the exam: which paper is on which
    date / time, what's the max + passing marks, which class it's for.

    Returns one row per ExamSubject, ordered by (date, start time).
    Rows with no date sink to the bottom — the UI shows them under a
    "Date TBD" group so unscheduled papers are still visible.
    """
    from sqlalchemy.orm import aliased

    try:
        from app.models.academic import ClassDef, Subject
        from app.models.exams import Exam, ExamSubject
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Exams module is not enabled on this database",
        )

    exam = (
        await session.execute(select(Exam).where(Exam.id == exam_id))
    ).scalar_one_or_none()
    if exam is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found",
        )

    subj_alias = aliased(Subject)
    cls_alias = aliased(ClassDef)
    rows = list(
        (
            await session.execute(
                select(ExamSubject, subj_alias, cls_alias)
                .join(subj_alias, ExamSubject.subject_id == subj_alias.id)
                .join(cls_alias, ExamSubject.class_def_id == cls_alias.id)
                .where(ExamSubject.exam_id == exam_id)
                .order_by(
                    ExamSubject.exam_date.is_(None),
                    ExamSubject.exam_date.asc(),
                    ExamSubject.starts_at.asc(),
                )
            )
        ).all()
    )
    return {
        "exam_id": exam.id,
        "exam_name": exam.name,
        "exam_kind": exam.kind,
        "start_date": exam.start_date.isoformat() if exam.start_date else None,
        "end_date": exam.end_date.isoformat() if exam.end_date else None,
        "default_max_marks": float(exam.default_max_marks)
        if exam.default_max_marks is not None
        else None,
        "papers": [
            {
                "id": es.id,
                "subject_id": es.subject_id,
                "subject_name": subj.name,
                "class_id": es.class_def_id,
                "class_name": cls.name,
                "exam_date": es.exam_date.isoformat() if es.exam_date else None,
                "starts_at": es.starts_at.isoformat() if es.starts_at else None,
                "ends_at": es.ends_at.isoformat() if es.ends_at else None,
                "max_marks": float(es.max_marks) if es.max_marks is not None else None,
                "passing_marks": float(es.passing_marks)
                if es.passing_marks is not None
                else None,
            }
            for (es, subj, cls) in rows
        ],
    }


# ---- Exam mark entry ------------------------------------------------------


@router.get("/exams/{exam_id}/mark-entry")
async def teacher_mark_entry_targets_route(
    exam_id: int,
    principal: AuthPrincipal = Depends(_teacher),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    """Every {section × exam-subject} the logged-in teacher can enter
    marks for, with all names + ids the mobile screen needs. Each target
    is an ExamSubject (a paper for a class) paired with a section the
    teacher teaches that belongs to that class."""
    from app.models.academic import ClassDef, Section, Subject
    from app.models.exams import Exam, ExamSubject
    from app.schemas.exams import TeacherMarkEntryTarget, TeacherMarkEntryTargets
    from app.services.teacher_app import _accessible_sections

    exam = (
        await session.execute(select(Exam).where(Exam.id == exam_id))
    ).scalar_one_or_none()
    if exam is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found"
        )

    section_ids = await _accessible_sections(session, user_id=principal.user_id)
    if not section_ids:
        return TeacherMarkEntryTargets(
            exam_id=exam.id, exam_name=exam.name, targets=[]
        )

    sections = list(
        (
            await session.execute(
                select(Section).where(Section.id.in_(section_ids))
            )
        ).scalars().all()
    )
    class_ids = {s.class_def_id for s in sections if s.class_def_id is not None}
    class_names = {
        cid: name
        for cid, name in (
            await session.execute(
                select(ClassDef.id, ClassDef.name).where(ClassDef.id.in_(class_ids))
            )
        ).all()
    } if class_ids else {}

    exam_subjects = list(
        (
            await session.execute(
                select(ExamSubject).where(ExamSubject.exam_id == exam_id)
            )
        ).scalars().all()
    )
    subject_ids = {es.subject_id for es in exam_subjects}
    subject_names = {
        sid: name
        for sid, name in (
            await session.execute(
                select(Subject.id, Subject.name).where(Subject.id.in_(subject_ids))
            )
        ).all()
    } if subject_ids else {}

    # Index exam subjects by class so we only pair a section with the
    # papers set for that section's class.
    by_class: dict[int, list[ExamSubject]] = {}
    for es in exam_subjects:
        by_class.setdefault(es.class_def_id, []).append(es)

    targets: list[TeacherMarkEntryTarget] = []
    for sec in sections:
        for es in by_class.get(sec.class_def_id, []):
            targets.append(
                TeacherMarkEntryTarget(
                    exam_subject_id=es.id,
                    section_id=sec.id,
                    section_name=sec.name,
                    class_label=class_names.get(sec.class_def_id),
                    subject_id=es.subject_id,
                    subject_name=subject_names.get(es.subject_id, "Subject"),
                    max_marks=es.max_marks,
                    passing_marks=es.passing_marks,
                    exam_date=es.exam_date,
                )
            )
    # Stable order: by section, then subject name.
    targets.sort(key=lambda t: (t.section_name, t.subject_name))
    return TeacherMarkEntryTargets(
        exam_id=exam.id, exam_name=exam.name, targets=targets
    )


@router.get("/exams/exam-subjects/{exam_subject_id}/roster")
async def teacher_exam_roster_route(
    exam_subject_id: int,
    section_id: int = Query(...),
    principal: AuthPrincipal = Depends(_teacher),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    """Roster for a paper + section with any marks already saved. Gated
    to sections the teacher actually teaches."""
    from app.services.exams import section_roster as exam_section_roster

    await assert_section_access(
        session, user_id=principal.user_id, section_id=section_id,
    )
    return await exam_section_roster(session, exam_subject_id, section_id)


@router.post("/exams/marks/bulk")
async def teacher_bulk_marks_route(
    payload: MarkBulkRequest,
    section_id: int = Query(...),
    principal: AuthPrincipal = Depends(_teacher),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    """Upsert marks for a paper. section_id is required so we can verify
    the teacher teaches the section before writing."""
    from app.services.exams import upsert_marks

    await assert_section_access(
        session, user_id=principal.user_id, section_id=section_id,
    )
    written = await upsert_marks(
        session, principal.tenant_id, principal.user_id, payload
    )
    return {"written": written}
