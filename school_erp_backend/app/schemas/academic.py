"""Pydantic schemas for the school admin academic-setup module."""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.academic import ClassStage, HolidayKind


# ---- Department -------------------------------------------------------------


class DepartmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    code: Optional[str]
    description: Optional[str]
    head_user_id: Optional[int]


class DepartmentWrite(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    code: Optional[str] = Field(default=None, max_length=20)
    description: Optional[str] = Field(default=None, max_length=255)
    head_user_id: Optional[int] = None


# ---- Academic year + term ---------------------------------------------------


class AcademicTermRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    year_id: int
    name: str
    start_date: date
    end_date: date


class AcademicTermWrite(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    start_date: date
    end_date: date


class AcademicYearRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str
    start_date: date
    end_date: date
    is_active: bool
    terms: list[AcademicTermRead] = Field(default_factory=list)


class AcademicYearWrite(BaseModel):
    code: str = Field(min_length=2, max_length=20)
    name: str = Field(min_length=2, max_length=80)
    start_date: date
    end_date: date
    is_active: bool = False


# ---- Class + section --------------------------------------------------------


class ClassDefRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str
    stage: ClassStage
    sequence: int
    department_id: Optional[int]


class ClassDefWrite(BaseModel):
    code: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=80)
    stage: ClassStage = ClassStage.PRIMARY
    sequence: int = 0
    department_id: Optional[int] = None


class SectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    class_def_id: int
    name: str
    capacity: int
    in_charge_user_id: Optional[int]


class SectionWrite(BaseModel):
    class_def_id: int
    name: str = Field(min_length=1, max_length=20)
    capacity: int = Field(default=40, ge=1, le=200)
    in_charge_user_id: Optional[int] = None


# ---- Subject ----------------------------------------------------------------


class SubjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str
    is_core: bool
    is_language: bool
    has_practical: bool
    department_id: Optional[int]


class SubjectWrite(BaseModel):
    code: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=80)
    is_core: bool = True
    is_language: bool = False
    has_practical: bool = False
    department_id: Optional[int] = None


# ---- Holiday ----------------------------------------------------------------


class HolidayRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    date: date
    name: str
    kind: HolidayKind
    description: Optional[str]
    year_id: Optional[int]


class HolidayWrite(BaseModel):
    date: date
    name: str = Field(min_length=1, max_length=120)
    kind: HolidayKind = HolidayKind.PUBLIC
    description: Optional[str] = None
    year_id: Optional[int] = None


# ---- Dashboard --------------------------------------------------------------


class SchoolDashboard(BaseModel):
    school_name: str
    subdomain: str
    students_count: int
    teachers_count: int
    classes_count: int
    sections_count: int
    subjects_count: int
    departments_count: int
    active_year: Optional[AcademicYearRead] = None
    storage_used_mb: float
    storage_limit_mb: int


class SchoolSettings(BaseModel):
    school_name: str
    primary_color: str
    secondary_color: str
    logo_url: Optional[str] = None
    timezone: str
    affiliation_board: Optional[str] = None
    medium: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


class SchoolSettingsUpdate(BaseModel):
    school_name: Optional[str] = Field(default=None, min_length=2, max_length=180)
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    logo_url: Optional[str] = None
    timezone: Optional[str] = None
    affiliation_board: Optional[str] = None
    medium: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
