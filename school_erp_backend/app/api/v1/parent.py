"""Parent module endpoints + school-admin parent management (Phase 8)."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import AuthPrincipal, require_roles
from app.core.tenant_session import platform_session, tenant_scoped_session
from app.models.parent import LeaveStatus
from app.schemas.parent import (
    ChildDashboard,
    ChildSummary,
    ChildSwitch,
    LeaveCreate,
    LeaveDecide,
    LeaveRead,
    ParentCreate,
    ParentLink,
    ParentLinkRead,
    ParentPasswordReset,
    ParentPasswordResetResult,
    ParentSelfRead,
    StudentDocSummary,
    StudentProfileView,
)
from app.services.student_id_card import render_id_card_pdf
from app.schemas.academic import HolidayRead
from app.schemas.curriculum import CalendarEventRead
from app.services.parents import (
    apply_leave,
    attendance_history_for_parent,
    class_average_for_parent,
    create_parent_user,
    dashboard_for_child,
    decide_leave,
    directory_for_parent,
    link_parent_to_student,
    list_children,
    list_documents_for_child,
    list_events_for_parent,
    list_holidays_for_parent,
    list_leaves_for_user,
    profile_for_parent,
    subject_attendance_for_parent,
    list_parent_links,
    list_school_leaves,
    parent_self,
    select_child,
    set_parent_password,
    timetable_for_parent,
    unlink_parent_from_student,
)


# ---- Parent-facing router ---------------------------------------------------


_parent_role = require_roles("parent")


router = APIRouter(
    prefix="/parent",
    tags=["parent"],
    dependencies=[Depends(_parent_role)],
)


@router.get("/me", response_model=ParentSelfRead)
async def me(
    principal: AuthPrincipal = Depends(_parent_role),
    session: AsyncSession = Depends(platform_session),
):
    return await parent_self(session, principal.tenant_id, principal.user_id)


@router.get("/children", response_model=list[ChildSummary])
async def children(
    principal: AuthPrincipal = Depends(_parent_role),
    session: AsyncSession = Depends(platform_session),
):
    return await list_children(session, principal.tenant_id, principal.user_id)


@router.post("/select-child")
async def select_child_route(
    payload: ChildSwitch,
    principal: AuthPrincipal = Depends(_parent_role),
    session: AsyncSession = Depends(platform_session),
):
    sid = await select_child(session, principal.tenant_id, principal.user_id, payload.student_id)
    return {"current_child_id": sid}


@router.get("/dashboard/{student_id}", response_model=ChildDashboard)
async def child_dashboard(
    student_id: int,
    principal: AuthPrincipal = Depends(_parent_role),
    session: AsyncSession = Depends(platform_session),
):
    return await dashboard_for_child(session, principal.tenant_id, principal.user_id, student_id)


@router.get("/children/{student_id}/documents", response_model=list[StudentDocSummary])
async def child_documents(
    student_id: int,
    principal: AuthPrincipal = Depends(_parent_role),
    session: AsyncSession = Depends(platform_session),
):
    return await list_documents_for_child(session, principal.tenant_id, principal.user_id, student_id)


@router.get("/children/{student_id}/attendance")
async def child_attendance(
    student_id: int,
    limit: int = 60,
    principal: AuthPrincipal = Depends(_parent_role),
    session: AsyncSession = Depends(platform_session),
):
    return await attendance_history_for_parent(
        session,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        student_id=student_id,
        limit=limit,
    )


@router.get("/children/{student_id}/attendance/by-subject")
async def child_attendance_by_subject(
    student_id: int,
    window_days: int = Query(default=90, ge=7, le=365),
    principal: AuthPrincipal = Depends(_parent_role),
    session: AsyncSession = Depends(platform_session),
):
    return await subject_attendance_for_parent(
        session,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        student_id=student_id,
        window_days=window_days,
    )


@router.get("/children/{student_id}/attendance/class-average")
async def child_attendance_class_average(
    student_id: int,
    window_days: int = Query(default=30, ge=7, le=180),
    principal: AuthPrincipal = Depends(_parent_role),
    session: AsyncSession = Depends(platform_session),
):
    return await class_average_for_parent(
        session,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        student_id=student_id,
        window_days=window_days,
    )


@router.get("/children/{student_id}/timetable")
async def child_timetable(
    student_id: int,
    principal: AuthPrincipal = Depends(_parent_role),
    session: AsyncSession = Depends(platform_session),
):
    return await timetable_for_parent(
        session,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        student_id=student_id,
    )


@router.get("/leave-applications", response_model=list[LeaveRead])
async def my_leaves(
    principal: AuthPrincipal = Depends(_parent_role),
    session: AsyncSession = Depends(platform_session),
):
    return await list_leaves_for_user(session, principal.tenant_id, principal.user_id)


@router.post("/leave-applications", response_model=LeaveRead, status_code=status.HTTP_201_CREATED)
async def apply_leave_route(
    payload: LeaveCreate,
    principal: AuthPrincipal = Depends(_parent_role),
    session: AsyncSession = Depends(platform_session),
):
    return await apply_leave(session, principal.tenant_id, principal.user_id, payload)


# ---- Calendar feeds: parent-visible holidays + events ---------------------


@router.get("/holidays", response_model=list[HolidayRead])
async def parent_holidays_route(
    days_back: int = Query(7, ge=0, le=60),
    days_forward: int = Query(180, ge=1, le=365),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await list_holidays_for_parent(
        session, days_back=days_back, days_forward=days_forward
    )


@router.get("/events", response_model=list[CalendarEventRead])
async def parent_events_route(
    days_back: int = Query(7, ge=0, le=60),
    days_forward: int = Query(180, ge=1, le=365),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await list_events_for_parent(
        session, days_back=days_back, days_forward=days_forward
    )


@router.get("/children/{student_id}/directory")
async def parent_directory_route(
    student_id: int,
    principal: AuthPrincipal = Depends(_parent_role),
    session: AsyncSession = Depends(platform_session),
):
    """Read-only teacher directory for the selected child's section.
    Returns name + designation + subject + photo only — never phone or
    email until the Teacher model grows a per-row visibility flag."""
    return await directory_for_parent(
        session,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        student_id=student_id,
    )


@router.get("/children/{student_id}/profile", response_model=StudentProfileView)
async def parent_profile_route(
    student_id: int,
    principal: AuthPrincipal = Depends(_parent_role),
    session: AsyncSession = Depends(platform_session),
):
    return await profile_for_parent(
        session,
        user_id=principal.user_id,
        student_id=student_id,
        tenant_id=principal.tenant_id,
    )


@router.get("/children/{student_id}/id-card.pdf")
async def parent_id_card_pdf(
    student_id: int,
    principal: AuthPrincipal = Depends(_parent_role),
    session: AsyncSession = Depends(platform_session),
):
    profile = await profile_for_parent(
        session,
        user_id=principal.user_id,
        student_id=student_id,
        tenant_id=principal.tenant_id,
    )
    target = render_id_card_pdf(profile, tenant_id=principal.tenant_id)
    return FileResponse(
        target,
        media_type="application/pdf",
        filename=f"id_card_{profile.admission_number}.pdf",
    )


# ---- School-admin parent management ----------------------------------------


_school_admin = require_roles("school_admin", "principal", "vice_principal", "office_staff")
_decision_role = require_roles("school_admin", "principal", "vice_principal", "class_teacher")


sa_router = APIRouter(
    prefix="/school-admin",
    tags=["school-admin"],
    dependencies=[Depends(_school_admin)],
)


@sa_router.post("/parents", response_model=ParentSelfRead, status_code=status.HTTP_201_CREATED)
async def create_parent_route(
    payload: ParentCreate,
    principal: AuthPrincipal = Depends(_school_admin),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    parent = await create_parent_user(session, principal.tenant_id, payload)
    return ParentSelfRead(
        parent_id=parent.id,
        user_id=parent.user_id,
        full_name=parent.full_name,
        phone=parent.phone,
        email=parent.email,
        relation=payload.relation,
        current_child_id=None,
    )


@sa_router.get("/students/{student_id}/parents", response_model=list[ParentLinkRead])
async def list_parents_for_student(
    student_id: int,
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await list_parent_links(session, student_id)


@sa_router.post("/students/{student_id}/parents", response_model=ParentLinkRead)
async def link_parent_route(
    student_id: int,
    payload: ParentLink,
    principal: AuthPrincipal = Depends(_school_admin),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    mapping = await link_parent_to_student(session, principal.tenant_id, student_id, payload)
    parents = await list_parent_links(session, student_id)
    # Return the freshly upserted row.
    for p in parents:
        if p.mapping_id == mapping.id:
            return p
    return parents[0]


@sa_router.delete(
    "/students/{student_id}/parents/{mapping_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def unlink_parent_route(
    student_id: int,
    mapping_id: int,
    principal: AuthPrincipal = Depends(_school_admin),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    await unlink_parent_from_student(session, mapping_id)


@sa_router.post(
    "/parents/{parent_user_id}/set-password",
    response_model=ParentPasswordResetResult,
)
async def set_parent_password_route(
    parent_user_id: int,
    payload: ParentPasswordReset,
    principal: AuthPrincipal = Depends(_school_admin),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    """Force-set a parent's login password from the school admin UI.

    Useful for parents auto-created during student admission (their
    password_hash is NULL until either Phase 12 OTP login lands or an
    admin sets one here). Restricted to school admin / principal /
    vice principal / office staff via the router-level dep; further
    locked to users that actually hold the 'parent' role inside
    set_parent_password() itself.
    """
    user = await set_parent_password(
        session,
        tenant_id=principal.tenant_id,
        parent_user_id=parent_user_id,
        new_password=payload.new_password,
    )
    return ParentPasswordResetResult(
        user_id=user.id,
        full_name=user.full_name,
        email=user.email,
        phone=user.phone,
        is_active=user.is_active,
    )


# ---- School-admin leave queue ---------------------------------------------


@sa_router.get("/leave-applications", response_model=list[LeaveRead])
async def list_school_leaves_route(
    student_id: Optional[int] = None,
    status_filter: Optional[LeaveStatus] = Query(default=None, alias="status"),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await list_school_leaves(session, student_id=student_id, status_filter=status_filter)


@sa_router.post("/leave-applications/{leave_id}/decide", response_model=LeaveRead)
async def decide_leave_route(
    leave_id: int,
    payload: LeaveDecide,
    principal: AuthPrincipal = Depends(_decision_role),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await decide_leave(
        session, leave_id, decided_by_user_id=principal.user_id, payload=payload
    )
