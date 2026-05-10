"""Pydantic schemas for Phase 5 (curriculum + houses + calendar)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.curriculum import CalendarEventKind


# ---- Houses ----------------------------------------------------------------


class HouseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    code: Optional[str]
    color: str
    motto: Optional[str]
    captain_user_id: Optional[int]


class HouseWrite(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    code: Optional[str] = Field(default=None, max_length=20)
    color: str = "#E85D2E"
    motto: Optional[str] = Field(default=None, max_length=200)
    captain_user_id: Optional[int] = None


# ---- SectionSubject --------------------------------------------------------


class SectionSubjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    section_id: int
    subject_id: int
    teacher_user_id: Optional[int]
    weekly_periods: int
    is_optional: bool


class SectionSubjectWrite(BaseModel):
    section_id: int
    subject_id: int
    teacher_user_id: Optional[int] = None
    weekly_periods: int = Field(default=4, ge=1, le=20)
    is_optional: bool = False


class SectionSubjectBulkLink(BaseModel):
    section_id: int
    subject_ids: list[int] = Field(default_factory=list)
    weekly_periods: int = 4


# ---- Calendar events -------------------------------------------------------


class CalendarEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    description: Optional[str]
    kind: CalendarEventKind
    starts_at: datetime
    ends_at: Optional[datetime]
    is_all_day: bool
    year_id: Optional[int]
    term_id: Optional[int]
    audience: str


class CalendarEventWrite(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    description: Optional[str] = None
    kind: CalendarEventKind = CalendarEventKind.GENERAL
    starts_at: datetime
    ends_at: Optional[datetime] = None
    is_all_day: bool = True
    year_id: Optional[int] = None
    term_id: Optional[int] = None
    audience: str = "all"


# ---- Syllabus + chapters ---------------------------------------------------


class ChapterRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    syllabus_id: int
    sequence: int
    title: str
    summary: Optional[str]
    expected_periods: int
    target_completion_date: Optional[date]
    completion_pct: float
    completed_on: Optional[date]


class ChapterWrite(BaseModel):
    sequence: int = 0
    title: str = Field(min_length=1, max_length=180)
    summary: Optional[str] = None
    expected_periods: int = Field(default=4, ge=1, le=200)
    target_completion_date: Optional[date] = None


class ChapterProgress(BaseModel):
    completion_pct: float = Field(ge=0, le=100)
    completed_on: Optional[date] = None


class SyllabusRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    year_id: int
    class_def_id: int
    subject_id: int
    title: str
    description: Optional[str]
    chapters: list[ChapterRead] = Field(default_factory=list)
    overall_completion_pct: float = 0.0


class SyllabusWrite(BaseModel):
    year_id: int
    class_def_id: int
    subject_id: int
    title: str = Field(min_length=1, max_length=180)
    description: Optional[str] = None
