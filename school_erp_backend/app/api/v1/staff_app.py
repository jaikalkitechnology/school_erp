"""Self-service for any staff member in the mobile app.

The /teacher router is limited to teaching roles, so non-teaching staff
(accountant, librarian, hostel warden, office staff, receptionist, bus
staff, ...) had nothing they could call. These endpoints only touch the
caller's own data (their leave) or school-wide calendars, so every staff
role may use them.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import AuthPrincipal, require_roles
from app.core.rbac_catalog import STAFF_ROLE_CODES
from app.core.tenant_session import tenant_scoped_session
from app.services.parents import (
    event_to_dict,
    holiday_to_dict,
    list_events_for_parent,
    list_holidays_for_parent,
)
from app.services.teacher_app import (
    StaffLeaveRead,
    StaffLeaveWrite,
    apply_staff_leave,
    list_my_staff_leaves,
)

_staff = require_roles(*sorted(STAFF_ROLE_CODES))

router = APIRouter(prefix="/staff", tags=["staff"], dependencies=[Depends(_staff)])


@router.get("/my-leaves", response_model=list[StaffLeaveRead])
async def my_leaves(
    principal: AuthPrincipal = Depends(_staff),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await list_my_staff_leaves(session, user_id=principal.user_id)


@router.post("/my-leaves", response_model=StaffLeaveRead, status_code=status.HTTP_201_CREATED)
async def apply_my_leave(
    payload: StaffLeaveWrite,
    principal: AuthPrincipal = Depends(_staff),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await apply_staff_leave(
        session, tenant_id=principal.tenant_id, user_id=principal.user_id, payload=payload,
    )


@router.get("/holidays")
async def holidays(
    days_back: int = Query(7, ge=0, le=60),
    days_forward: int = Query(180, ge=1, le=365),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    rows = await list_holidays_for_parent(session, days_back=days_back, days_forward=days_forward)
    return [holiday_to_dict(r) for r in rows]


@router.get("/events")
async def events(
    days_back: int = Query(7, ge=0, le=60),
    days_forward: int = Query(180, ge=1, le=365),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    rows = await list_events_for_parent(session, days_back=days_back, days_forward=days_forward)
    return [event_to_dict(r) for r in rows]
