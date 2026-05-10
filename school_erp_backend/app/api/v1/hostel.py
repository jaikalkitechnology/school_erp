"""Hostel endpoints (Phase 19)."""

from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import AuthPrincipal, require_roles
from app.core.tenant_session import platform_session, tenant_scoped_session
from app.models.parent import Parent, ParentChildMapping
from app.schemas.hostel import (
    AllocationRead,
    AllocationWrite,
    DisciplinaryRead,
    DisciplinaryWrite,
    HostelLeaveApply,
    HostelLeaveDecide,
    HostelLeaveRead,
    HostelRead,
    HostelReports,
    HostelWrite,
    MessMenuRead,
    MessMenuWrite,
    ParentHostel,
    RoomDetail,
    RoomRead,
    RoomWithOccupancy,
    RoomWrite,
    VisitorIn,
    VisitorRead,
)
from app.services.hostel import (
    add_disciplinary,
    apply_leave,
    create_hostel,
    create_room,
    decide_leave,
    list_disciplinary,
    list_hostels,
    list_leaves,
    list_mess,
    list_rooms,
    list_visitors,
    mark_returned,
    parent_hostel,
    reports,
    room_detail,
    update_hostel,
    upsert_allocation,
    upsert_mess,
    vacate,
    visitor_check_in,
    visitor_check_out,
)


_school_admin = require_roles("school_admin", "principal", "vice_principal")
_warden = require_roles(
    "school_admin", "principal", "vice_principal", "hostel_warden", "coordinator",
)
_reader = require_roles(
    "school_admin", "principal", "vice_principal", "hostel_warden",
    "coordinator", "class_teacher",
)
_parent = require_roles("parent")


router = APIRouter(
    prefix="/school-admin/hostel",
    tags=["school-admin"],
    dependencies=[Depends(_reader)],
)


# ---- Hostels --------------------------------------------------------------


@router.get("/hostels", response_model=list[HostelRead])
async def list_hostels_route(session: AsyncSession = Depends(tenant_scoped_session)):
    return await list_hostels(session)


@router.post("/hostels", response_model=HostelRead, status_code=status.HTTP_201_CREATED)
async def create_hostel_route(
    payload: HostelWrite,
    principal: AuthPrincipal = Depends(_school_admin),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await create_hostel(session, principal.tenant_id, payload)


@router.patch("/hostels/{hostel_id}", response_model=HostelRead)
async def update_hostel_route(
    hostel_id: int,
    payload: HostelWrite,
    principal: AuthPrincipal = Depends(_school_admin),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await update_hostel(session, hostel_id, payload)


# ---- Rooms ----------------------------------------------------------------


@router.get("/hostels/{hostel_id}/rooms", response_model=list[RoomWithOccupancy])
async def list_rooms_route(
    hostel_id: int, session: AsyncSession = Depends(tenant_scoped_session)
):
    return await list_rooms(session, hostel_id)


@router.post(
    "/hostels/{hostel_id}/rooms", response_model=RoomRead, status_code=status.HTTP_201_CREATED
)
async def create_room_route(
    hostel_id: int,
    payload: RoomWrite,
    principal: AuthPrincipal = Depends(_warden),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await create_room(session, principal.tenant_id, hostel_id, payload)


@router.get("/rooms/{room_id}", response_model=RoomDetail)
async def room_detail_route(
    room_id: int, session: AsyncSession = Depends(tenant_scoped_session)
):
    return await room_detail(session, room_id)


# ---- Allocations ----------------------------------------------------------


@router.post("/allocations", response_model=AllocationRead)
async def upsert_allocation_route(
    payload: AllocationWrite,
    principal: AuthPrincipal = Depends(_warden),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await upsert_allocation(session, principal.tenant_id, payload)


@router.delete("/allocations/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
async def vacate_route(
    student_id: int,
    principal: AuthPrincipal = Depends(_warden),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    await vacate(session, student_id)


# ---- Mess menu ------------------------------------------------------------


@router.get("/hostels/{hostel_id}/mess", response_model=list[MessMenuRead])
async def list_mess_route(
    hostel_id: int,
    on_date: Optional[date] = None,
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await list_mess(session, hostel_id, on_date=on_date)


@router.put("/hostels/{hostel_id}/mess", response_model=MessMenuRead)
async def upsert_mess_route(
    hostel_id: int,
    payload: MessMenuWrite,
    principal: AuthPrincipal = Depends(_warden),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await upsert_mess(session, principal.tenant_id, hostel_id, payload)


# ---- Visitors -------------------------------------------------------------


@router.post(
    "/hostels/{hostel_id}/visitors",
    response_model=VisitorRead,
    status_code=status.HTTP_201_CREATED,
)
async def visitor_in_route(
    hostel_id: int,
    payload: VisitorIn,
    principal: AuthPrincipal = Depends(_warden),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await visitor_check_in(
        session, principal.tenant_id, principal.user_id, hostel_id, payload
    )


@router.post("/visitors/{visitor_id}/checkout", response_model=VisitorRead)
async def visitor_out_route(
    visitor_id: int,
    principal: AuthPrincipal = Depends(_warden),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await visitor_check_out(session, visitor_id)


@router.get("/hostels/{hostel_id}/visitors", response_model=list[VisitorRead])
async def list_visitors_route(
    hostel_id: int,
    open_only: bool = False,
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await list_visitors(session, hostel_id, open_only=open_only)


# ---- Disciplinary ---------------------------------------------------------


@router.post(
    "/hostels/{hostel_id}/disciplinary",
    response_model=DisciplinaryRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_disciplinary_route(
    hostel_id: int,
    payload: DisciplinaryWrite,
    principal: AuthPrincipal = Depends(_warden),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await add_disciplinary(
        session, principal.tenant_id, principal.user_id, hostel_id, payload
    )


@router.get("/hostels/{hostel_id}/disciplinary", response_model=list[DisciplinaryRead])
async def list_disciplinary_route(
    hostel_id: int,
    student_id: Optional[int] = None,
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await list_disciplinary(session, hostel_id, student_id=student_id)


# ---- Hostel leaves --------------------------------------------------------


@router.post(
    "/hostels/{hostel_id}/leaves",
    response_model=HostelLeaveRead,
    status_code=status.HTTP_201_CREATED,
)
async def apply_leave_route(
    hostel_id: int,
    payload: HostelLeaveApply,
    principal: AuthPrincipal = Depends(_warden),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await apply_leave(session, principal.tenant_id, hostel_id, payload)


@router.post("/leaves/{leave_id}/decide", response_model=HostelLeaveRead)
async def decide_leave_route(
    leave_id: int,
    payload: HostelLeaveDecide,
    principal: AuthPrincipal = Depends(_warden),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await decide_leave(session, principal.user_id, leave_id, payload)


@router.post("/leaves/{leave_id}/return", response_model=HostelLeaveRead)
async def return_leave_route(
    leave_id: int,
    principal: AuthPrincipal = Depends(_warden),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await mark_returned(session, leave_id)


@router.get("/leaves", response_model=list[HostelLeaveRead])
async def list_leaves_route(
    hostel_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    student_id: Optional[int] = None,
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await list_leaves(
        session, hostel_id, status_filter=status_filter, student_id=student_id
    )


# ---- Reports --------------------------------------------------------------


@router.get("/reports", response_model=HostelReports)
async def reports_route(session: AsyncSession = Depends(tenant_scoped_session)):
    return await reports(session)


# ---- Parent view ----------------------------------------------------------


parent_router = APIRouter(
    prefix="/parent", tags=["parent"], dependencies=[Depends(_parent)]
)


@parent_router.get("/children/{student_id}/hostel", response_model=ParentHostel)
async def parent_hostel_route(
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
    return await parent_hostel(session, student_id)
