"""Time table + substitution endpoints (Phase 13)."""

from __future__ import annotations

from datetime import date as _date
from typing import Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import AuthPrincipal, require_roles
from app.core.tenant_session import tenant_scoped_session
from app.schemas.timetable import (
    PeriodDefRead,
    PeriodDefWrite,
    SaveResult,
    SectionTimetable,
    SectionTimetableWrite,
    SubstitutionRead,
    SubstitutionSuggest,
    SubstitutionSuggestion,
    SubstitutionWrite,
    TeacherTimetable,
)
from app.services.timetable import (
    assign_substitution,
    cancel_substitution,
    complete_substitution,
    delete_period,
    list_periods,
    list_substitutions_for_date,
    replace_section_timetable,
    section_timetable,
    suggest_substitutes,
    teacher_timetable,
    upsert_period,
)


_school_admin = require_roles(
    "school_admin", "principal", "vice_principal", "coordinator", "hod",
)
_school_view = require_roles(
    "school_admin", "principal", "vice_principal", "coordinator", "hod",
    "class_teacher", "subject_teacher", "office_staff",
)


router = APIRouter(
    prefix="/school-admin/timetable",
    tags=["school-admin"],
    dependencies=[Depends(_school_view)],
)


# ---- Period definitions ----------------------------------------------------


@router.get("/periods", response_model=list[PeriodDefRead])
async def list_periods_route(session: AsyncSession = Depends(tenant_scoped_session)):
    return await list_periods(session)


@router.put("/periods", response_model=PeriodDefRead)
async def upsert_period_route(
    payload: PeriodDefWrite,
    principal: AuthPrincipal = Depends(_school_admin),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await upsert_period(session, principal.tenant_id, payload)


@router.delete("/periods/{period_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_period_route(
    period_id: int,
    principal: AuthPrincipal = Depends(_school_admin),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    await delete_period(session, period_id)


# ---- Section grid ----------------------------------------------------------


@router.get("/sections/{section_id}", response_model=SectionTimetable)
async def section_route(
    section_id: int,
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await section_timetable(session, section_id)


@router.put("/sections/{section_id}", response_model=SaveResult)
async def replace_section_route(
    section_id: int,
    payload: SectionTimetableWrite,
    principal: AuthPrincipal = Depends(_school_admin),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await replace_section_timetable(
        session, principal.tenant_id, section_id, payload
    )


# ---- Teacher view ----------------------------------------------------------


@router.get("/teachers/{teacher_user_id}", response_model=TeacherTimetable)
async def teacher_route(
    teacher_user_id: int,
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await teacher_timetable(session, teacher_user_id)


# ---- Substitutions ---------------------------------------------------------


@router.post("/substitutions/suggest", response_model=SubstitutionSuggestion)
async def suggest_route(
    payload: SubstitutionSuggest,
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await suggest_substitutes(session, payload)


@router.get("/substitutions", response_model=list[SubstitutionRead])
async def list_subs_route(
    target_date: _date,
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await list_substitutions_for_date(session, target_date)


@router.post(
    "/substitutions",
    response_model=SubstitutionRead,
    status_code=status.HTTP_201_CREATED,
)
async def assign_sub_route(
    payload: SubstitutionWrite,
    principal: AuthPrincipal = Depends(_school_admin),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await assign_substitution(session, principal.tenant_id, payload)


@router.post("/substitutions/{sub_id}/complete", response_model=SubstitutionRead)
async def complete_sub_route(
    sub_id: int,
    principal: AuthPrincipal = Depends(_school_admin),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await complete_substitution(session, sub_id)


@router.post("/substitutions/{sub_id}/cancel", response_model=SubstitutionRead)
async def cancel_sub_route(
    sub_id: int,
    principal: AuthPrincipal = Depends(_school_admin),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await cancel_substitution(session, sub_id)
