"""Pydantic schemas for the attendance module (Phase 9)."""

from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.attendance import StudentAttendanceStatus


class AttendanceRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    student_id: int
    section_id: Optional[int]
    class_def_id: Optional[int]
    date: date
    period: str
    status: StudentAttendanceStatus
    marked_by_user_id: Optional[int]
    remarks: Optional[str]


class AttendanceMarkEntry(BaseModel):
    student_id: int
    status: StudentAttendanceStatus = StudentAttendanceStatus.PRESENT
    remarks: Optional[str] = Field(default=None, max_length=255)


class AttendanceMarkRequest(BaseModel):
    section_id: int
    date: date
    period: str = "day"
    entries: List[AttendanceMarkEntry] = Field(default_factory=list)
    default_status: StudentAttendanceStatus = StudentAttendanceStatus.PRESENT


class StudentRollEntry(BaseModel):
    student_id: int
    full_name: str
    admission_number: str
    roll_no: Optional[str]
    status: StudentAttendanceStatus
    remarks: Optional[str]


class SectionRoll(BaseModel):
    section_id: int
    date: date
    period: str
    students: List[StudentRollEntry]
    counts: dict


class StudentMonthlySummary(BaseModel):
    student_id: int
    full_name: str
    admission_number: str
    total_days: int
    present: int
    absent: int
    late: int
    leave: int
    half_day: int
    attendance_pct: float


class SectionMonthlyReport(BaseModel):
    section_id: int
    year: int
    month: int
    working_days: int
    students: List[StudentMonthlySummary]


class DefaulterRow(BaseModel):
    student_id: int
    full_name: str
    admission_number: str
    section_id: Optional[int]
    class_def_id: Optional[int]
    total_days: int
    present_days: int
    attendance_pct: float


class StudentHistoryRow(BaseModel):
    date: date
    period: str
    status: StudentAttendanceStatus
    remarks: Optional[str]
    marked_by_user_id: Optional[int] = None
    marked_by_name: Optional[str] = None
    marked_at: Optional[datetime] = None
