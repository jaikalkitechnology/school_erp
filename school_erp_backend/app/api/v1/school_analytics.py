"""Phase 20 school-admin analytics endpoints."""

from __future__ import annotations

import csv
import io
from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import require_roles
from app.core.tenant_session import tenant_scoped_session
from app.schemas.analytics import (
    AnalyticsOverview,
    AttendanceTrend,
    ExamAnalytics,
    FeeOverview,
    HostelSummary,
    LibraryUsage,
    StudentReport,
    TransportSummary,
)
from app.services import school_analytics


_reader = require_roles(
    "school_admin", "principal", "vice_principal", "coordinator",
    "accountant", "class_teacher", "subject_teacher",
)


router = APIRouter(
    prefix="/school-admin/analytics",
    tags=["school-admin"],
    dependencies=[Depends(_reader)],
)


@router.get("/overview", response_model=AnalyticsOverview)
async def overview_route(session: AsyncSession = Depends(tenant_scoped_session)):
    return await school_analytics.overview(session)


@router.get("/attendance-trend", response_model=AttendanceTrend)
async def attendance_trend_route(
    days: int = 14, session: AsyncSession = Depends(tenant_scoped_session)
):
    return await school_analytics.attendance_trend(session, days=days)


@router.get("/fees", response_model=FeeOverview)
async def fees_route(session: AsyncSession = Depends(tenant_scoped_session)):
    return await school_analytics.fees(session)


@router.get("/exams", response_model=ExamAnalytics)
async def exams_route(
    exam_id: Optional[int] = None,
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await school_analytics.exam_analytics(session, exam_id=exam_id)


@router.get("/library", response_model=LibraryUsage)
async def library_route(session: AsyncSession = Depends(tenant_scoped_session)):
    return await school_analytics.library_usage(session)


@router.get("/transport", response_model=TransportSummary)
async def transport_route(session: AsyncSession = Depends(tenant_scoped_session)):
    return await school_analytics.transport_summary(session)


@router.get("/hostel", response_model=HostelSummary)
async def hostel_route(session: AsyncSession = Depends(tenant_scoped_session)):
    return await school_analytics.hostel_summary(session)


# ---- Standard reports + CSV export -----------------------------------------


@router.get("/reports/students", response_model=StudentReport)
async def students_report_route(
    class_def_id: Optional[int] = None,
    section_id: Optional[int] = None,
    only_active: bool = True,
    session: AsyncSession = Depends(tenant_scoped_session),
):
    rows = await school_analytics.student_report(
        session,
        class_def_id=class_def_id,
        section_id=section_id,
        only_active=only_active,
    )
    return {"rows": rows}


@router.get("/reports/students.csv")
async def students_report_csv_route(
    class_def_id: Optional[int] = None,
    section_id: Optional[int] = None,
    only_active: bool = True,
    session: AsyncSession = Depends(tenant_scoped_session),
):
    rows = await school_analytics.student_report(
        session,
        class_def_id=class_def_id,
        section_id=section_id,
        only_active=only_active,
    )
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        ["student_id", "admission_number", "full_name", "class", "section", "parent_phone", "status"]
    )
    for r in rows:
        writer.writerow(
            [
                r["student_id"],
                r["admission_number"],
                r["full_name"],
                r.get("class_label") or "",
                r.get("section_name") or "",
                r.get("parent_phone") or "",
                r["status"],
            ]
        )
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="students.csv"'},
    )
