"""Student attendance endpoints (Phase 9)."""

from __future__ import annotations

from datetime import date as _date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import AuthPrincipal, require_roles
from app.core.tenant_session import tenant_scoped_session
from app.schemas.attendance import (
    AttendanceMarkRequest,
    DefaulterRow,
    SectionMonthlyReport,
    SectionRoll,
    StudentHistoryRow,
)
from app.services.attendance import (
    defaulters,
    mark_section_attendance,
    section_monthly,
    section_roll,
    student_history,
)


_school_staff = require_roles(
    "school_admin", "principal", "vice_principal", "coordinator",
    "class_teacher", "subject_teacher",
)
_school_admin = require_roles(
    "school_admin", "principal", "vice_principal", "coordinator", "class_teacher"
)


router = APIRouter(
    prefix="/school-admin/attendance",
    tags=["school-admin"],
    dependencies=[Depends(_school_staff)],
)


@router.get("/section/{section_id}", response_model=SectionRoll)
async def section_roll_route(
    section_id: int,
    target_date: _date = Query(default_factory=_date.today, alias="date"),
    period: str = "day",
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await section_roll(
        session, section_id=section_id, target_date=target_date, period=period
    )


@router.post("/mark", response_model=SectionRoll)
async def mark_route(
    payload: AttendanceMarkRequest,
    principal: AuthPrincipal = Depends(_school_admin),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await mark_section_attendance(
        session, principal.tenant_id, principal.user_id, payload
    )


@router.get("/section/{section_id}/monthly", response_model=SectionMonthlyReport)
async def section_monthly_route(
    section_id: int,
    year: int,
    month: int,
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await section_monthly(
        session, section_id=section_id, year=year, month=month
    )


@router.get("/defaulters", response_model=list[DefaulterRow])
async def defaulters_route(
    threshold_pct: float = Query(default=75.0, ge=0, le=100),
    section_id: Optional[int] = None,
    start: Optional[_date] = None,
    end: Optional[_date] = None,
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await defaulters(
        session,
        threshold_pct=threshold_pct,
        start=start,
        end=end,
        section_id=section_id,
    )


@router.get("/student/{student_id}", response_model=list[StudentHistoryRow])
async def student_history_route(
    student_id: int,
    start: Optional[_date] = None,
    end: Optional[_date] = None,
    limit: int = Query(default=60, ge=1, le=400),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await student_history(
        session, student_id=student_id, start=start, end=end, limit=limit
    )
