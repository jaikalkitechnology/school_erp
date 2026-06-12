"""Homework schemas (Phase 14)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.homework import SubmissionStatus


# ---- Homework --------------------------------------------------------------


class HomeworkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    section_id: int
    subject_id: Optional[int]
    teacher_user_id: Optional[int]
    title: str
    description: Optional[str]
    assigned_on: date
    due_date: date
    max_marks: Decimal
    attachments: List[str]


class HomeworkWrite(BaseModel):
    section_id: int
    subject_id: Optional[int] = None
    title: str = Field(min_length=1, max_length=180)
    description: Optional[str] = None
    assigned_on: Optional[date] = None  # defaults to today
    due_date: date
    max_marks: Decimal = Field(default=Decimal("0"), ge=0)
    attachments: List[str] = Field(default_factory=list)


class HomeworkUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[date] = None
    max_marks: Optional[Decimal] = Field(default=None, ge=0)
    attachments: Optional[List[str]] = None


# ---- Submission ------------------------------------------------------------


class SubmissionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    homework_id: int
    student_id: int
    submitted_at: Optional[datetime]
    content: Optional[str]
    attachments: List[str]
    status: SubmissionStatus
    marks: Optional[Decimal]
    feedback: Optional[str]
    graded_at: Optional[datetime]


class SubmissionWrite(BaseModel):
    homework_id: int
    content: Optional[str] = None
    attachments: List[str] = Field(default_factory=list)


class GradeWrite(BaseModel):
    marks: Decimal = Field(ge=0)
    feedback: Optional[str] = None


# ---- Reports ---------------------------------------------------------------


class StudentSubmissionStatus(BaseModel):
    student_id: int
    full_name: str
    admission_number: str
    submitted: bool
    submitted_at: Optional[datetime]
    status: Optional[SubmissionStatus]
    marks: Optional[Decimal]


class HomeworkStatusReport(BaseModel):
    homework_id: int
    section_id: int
    title: str
    due_date: date
    max_marks: Optional[Decimal] = None
    rows: List[StudentSubmissionStatus]
    submitted_count: int
    total_students: int


class StudentHomeworkRow(BaseModel):
    homework_id: int
    title: str
    description: Optional[str] = None
    assigned_on: Optional[date] = None
    due_date: date
    subject_id: Optional[int]
    subject_name: Optional[str] = None
    max_marks: Optional[Decimal] = None
    teacher_attachments: List[str] = Field(default_factory=list)
    submission_status: Optional[SubmissionStatus]
    submitted: bool
    submitted_at: Optional[date] = None
    # Echo back what the student actually sent in so the parent app can
    # show "here's what you submitted" instead of just a timestamp pill.
    submission_content: Optional[str] = None
    submission_attachments: List[str] = Field(default_factory=list)
    marks: Optional[Decimal]
    feedback: Optional[str] = None
