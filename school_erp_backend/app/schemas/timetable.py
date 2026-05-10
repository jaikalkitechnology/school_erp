"""Time table + substitution schemas (Phase 13)."""

from __future__ import annotations

from datetime import date, time
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.timetable import SubstitutionStatus


# ---- Period definitions ----------------------------------------------------


class PeriodDefRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    day_of_week: int
    period_number: int
    label: Optional[str]
    starts_at: Optional[time]
    ends_at: Optional[time]
    is_break: bool


class PeriodDefWrite(BaseModel):
    day_of_week: int = Field(ge=0, le=6)
    period_number: int = Field(ge=1, le=20)
    label: Optional[str] = Field(default=None, max_length=40)
    starts_at: Optional[time] = None
    ends_at: Optional[time] = None
    is_break: bool = False


# ---- Section grid ----------------------------------------------------------


class CellRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[int] = None
    day_of_week: int
    period_number: int
    subject_id: Optional[int]
    teacher_user_id: Optional[int]
    room: Optional[str]
    notes: Optional[str]


class SectionTimetable(BaseModel):
    section_id: int
    cells: List[CellRead]


class CellWrite(BaseModel):
    day_of_week: int = Field(ge=0, le=6)
    period_number: int = Field(ge=1, le=20)
    subject_id: Optional[int] = None
    teacher_user_id: Optional[int] = None
    room: Optional[str] = Field(default=None, max_length=40)
    notes: Optional[str] = Field(default=None, max_length=255)


class SectionTimetableWrite(BaseModel):
    cells: List[CellWrite]


class CellConflict(BaseModel):
    day_of_week: int
    period_number: int
    teacher_user_id: int
    other_section_id: int


class SaveResult(BaseModel):
    saved: int
    conflicts: List[CellConflict]


# ---- Teacher view ----------------------------------------------------------


class TeacherCell(BaseModel):
    day_of_week: int
    period_number: int
    section_id: int
    subject_id: Optional[int]
    room: Optional[str]


class TeacherTimetable(BaseModel):
    teacher_user_id: int
    cells: List[TeacherCell]


# ---- Substitution ----------------------------------------------------------


class SubstitutionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    date: date
    section_id: int
    period_number: int
    subject_id: Optional[int]
    original_teacher_user_id: Optional[int]
    substitute_teacher_user_id: Optional[int]
    status: SubstitutionStatus
    reason: Optional[str]


class SubstitutionWrite(BaseModel):
    date: date
    section_id: int
    period_number: int
    substitute_teacher_user_id: int
    reason: Optional[str] = None


class SubstitutionSuggest(BaseModel):
    date: date
    teacher_user_id: int


class SubSuggestionEntry(BaseModel):
    section_id: int
    period_number: int
    subject_id: Optional[int]
    suggested_substitutes: List[int]


class SubstitutionSuggestion(BaseModel):
    date: date
    absent_teacher_user_id: int
    entries: List[SubSuggestionEntry]
