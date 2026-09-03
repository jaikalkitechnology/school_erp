"""Exam schemas (Phase 15)."""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.exams import ExamStatus, ExamType, MarkStatus


# ---- Exam ------------------------------------------------------------------


class ExamRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    year_id: Optional[int]
    term_id: Optional[int]
    name: str
    kind: ExamType
    start_date: Optional[date]
    end_date: Optional[date]
    default_max_marks: Decimal
    status: ExamStatus
    published_at: Optional[datetime]
    notes: Optional[str]


class ExamWrite(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    kind: ExamType = ExamType.UNIT_TEST
    year_id: Optional[int] = None
    term_id: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    default_max_marks: Decimal = Field(default=Decimal("100"), gt=0)
    notes: Optional[str] = None


# ---- ExamSubject -----------------------------------------------------------


class ExamSubjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    exam_id: int
    class_def_id: int
    subject_id: int
    max_marks: Decimal
    passing_marks: Decimal
    exam_date: Optional[date]
    starts_at: Optional[time]
    ends_at: Optional[time]


class ExamSubjectWrite(BaseModel):
    class_def_id: int
    subject_id: int
    max_marks: Decimal = Field(default=Decimal("100"), gt=0)
    passing_marks: Decimal = Field(default=Decimal("33"), ge=0)
    exam_date: Optional[date] = None
    starts_at: Optional[time] = None
    ends_at: Optional[time] = None


# ---- Marks -----------------------------------------------------------------


class MarkEntry(BaseModel):
    student_id: int
    # Defense-in-depth: marks can't be negative. The per-paper upper bound
    # (<= max_marks) is enforced in the service, which knows the paper.
    obtained_marks: Optional[Decimal] = Field(default=None, ge=0)
    status: Optional[MarkStatus] = None
    remarks: Optional[str] = Field(default=None, max_length=255)


class MarkBulkRequest(BaseModel):
    exam_subject_id: int
    entries: List[MarkEntry]


class MarkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    exam_subject_id: int
    student_id: int
    obtained_marks: Optional[Decimal]
    status: MarkStatus
    remarks: Optional[str]


class SectionRoster(BaseModel):
    exam_subject_id: int
    rows: List[MarkEntry]
    max_marks: Decimal
    passing_marks: Decimal
    student_names: dict  # student_id -> full_name


class TeacherMarkEntryTarget(BaseModel):
    """One gradeable {section × exam-subject} the teacher can enter marks
    for. Carries every name + id the mobile screen needs so it can load a
    roster and post marks without extra lookups."""
    exam_subject_id: int
    section_id: int
    section_name: str
    class_label: Optional[str] = None
    subject_id: int
    subject_name: str
    max_marks: Decimal
    passing_marks: Decimal
    exam_date: Optional[date] = None


class TeacherMarkEntryTargets(BaseModel):
    exam_id: int
    exam_name: str
    targets: List[TeacherMarkEntryTarget]


# ---- Grade scale -----------------------------------------------------------


class GradeBand(BaseModel):
    min_pct: float = Field(ge=0, le=100)
    grade: str
    gpa: Optional[float] = None


class GradeScaleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str
    bands: List[GradeBand]
    is_default: bool


class GradeScaleWrite(BaseModel):
    code: str = Field(min_length=2, max_length=40)
    name: str = Field(min_length=2, max_length=120)
    bands: List[GradeBand]
    is_default: bool = False


# ---- Results ---------------------------------------------------------------


class StudentSubjectResult(BaseModel):
    subject_id: int
    max_marks: Decimal
    obtained: Optional[Decimal]
    status: MarkStatus
    grade: Optional[str] = None


class StudentExamResult(BaseModel):
    student_id: int
    full_name: str
    admission_number: str
    subjects: List[StudentSubjectResult]
    total_max: Decimal
    total_obtained: Decimal
    percentage: float
    overall_grade: Optional[str]
    rank_in_section: Optional[int]
    overall_status: MarkStatus


class ExamResults(BaseModel):
    exam_id: int
    section_id: int
    students: List[StudentExamResult]
    section_average_pct: float


class ParentChildExamRow(BaseModel):
    exam_id: int
    exam_name: str
    published: bool
    total_max: Decimal
    total_obtained: Decimal
    percentage: float
    overall_grade: Optional[str]
    overall_status: MarkStatus


class ParentChildExams(BaseModel):
    student_id: int
    rows: List[ParentChildExamRow]
