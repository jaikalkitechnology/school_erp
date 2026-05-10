"""Phase 20 analytics schemas."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel


class TrendPoint(BaseModel):
    label: str
    value: float


class AttendanceTrend(BaseModel):
    points: List[TrendPoint]
    average_pct: float


class FeeOverview(BaseModel):
    total_billed: Decimal
    total_collected: Decimal
    pending: Decimal
    overdue_count: int
    by_method: List[TrendPoint]
    by_category: List[TrendPoint]


class ExamSummary(BaseModel):
    exam_id: int
    exam_name: str
    section_id: Optional[int]
    section_name: Optional[str]
    average_pct: float
    pass_pct: float
    student_count: int


class ExamAnalytics(BaseModel):
    rows: List[ExamSummary]
    grade_distribution: List[TrendPoint]


class LibraryUsage(BaseModel):
    issued_today: int
    overdue: int
    most_loaned: List[TrendPoint]


class TransportSummary(BaseModel):
    routes: int
    buses: int
    drivers: int
    students_allocated: int
    active_trips_today: int


class HostelSummary(BaseModel):
    occupied: int
    available_seats: int
    pending_leaves: int


class TopRow(BaseModel):
    label: str
    value: float


class AnalyticsOverview(BaseModel):
    students: int
    teachers: int
    classes: int
    sections: int
    attendance_today_pct: float
    fee_collected_this_month: Decimal
    fee_pending: Decimal
    overdue_loans: int
    by_class_strength: List[TrendPoint]


class StudentReportRow(BaseModel):
    student_id: int
    admission_number: str
    full_name: str
    class_label: Optional[str]
    section_name: Optional[str]
    parent_phone: Optional[str]
    status: str


class StudentReport(BaseModel):
    rows: List[StudentReportRow]
