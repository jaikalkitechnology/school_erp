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


class SubjectAttendanceRow(BaseModel):
    """One row per subject the child has timetabled. Counts come from
    student_attendance rows whose `period` matches a timetable slot for
    that subject; if the school only uses day-level attendance, this
    endpoint returns an empty list."""

    subject_id: int
    subject_name: str
    present: int
    late: int
    half_day: int
    absent: int
    total: int
    percentage: float  # (present + late + 0.5*half_day) / total * 100


class SubjectAttendanceReport(BaseModel):
    rows: list[SubjectAttendanceRow]
    window_days: int
    note: Optional[str] = None  # populated when day-level attendance is in use


class ClassAverageRow(BaseModel):
    """Comparison view: how the child compares to their section's average."""

    child_pct: float
    class_pct: float
    class_size: int
    window_days: int
    child_attendance_days: int


class ParentTimetableCell(BaseModel):
    """One period in the parent-facing timetable view. IDs are resolved
    server-side to names + period start/end times so the mobile UI can
    render without a fan-out fetch."""

    day_of_week: int  # 0=Mon..6=Sun
    period_number: int
    subject_id: Optional[int] = None
    subject_name: Optional[str] = None
    teacher_user_id: Optional[int] = None
    teacher_name: Optional[str] = None
    room: Optional[str] = None
    start_time: Optional[str] = None  # "08:00:00"
    end_time: Optional[str] = None    # "08:45:00"


class ParentTimetable(BaseModel):
    section_id: Optional[int] = None
    section_name: Optional[str] = None
    class_name: Optional[str] = None
    cells: list[ParentTimetableCell]
    note: Optional[str] = None  # populated when no timetable exists yet
