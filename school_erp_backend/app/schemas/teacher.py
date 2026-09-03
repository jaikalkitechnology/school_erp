"""Pydantic schemas for the Teacher Management module."""

from __future__ import annotations

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.teacher import AttendanceStatus, EmploymentStatus
from app.schemas.sis import OptionalPhone


# ---- Teacher ----------------------------------------------------------------


class TeacherBase(BaseModel):
    full_name: str = Field(min_length=2, max_length=180)
    first_name: Optional[str] = Field(default=None, max_length=90)
    last_name: Optional[str] = Field(default=None, max_length=90)
    photo_url: Optional[str] = Field(default=None, max_length=500)
    date_of_birth: Optional[date] = None
    gender: Optional[str] = Field(default=None, max_length=16)
    blood_group: Optional[str] = Field(default=None, max_length=8)
    phone: OptionalPhone = None
    email: Optional[EmailStr] = None
    address: Optional[str] = Field(default=None, max_length=500)
    emergency_contact: Optional[str] = Field(default=None, max_length=120)
    emergency_phone: OptionalPhone = None
    department_id: Optional[int] = None
    designation: Optional[str] = Field(default=None, max_length=120)
    date_of_joining: Optional[date] = None
    qualifications: List[str] = Field(default_factory=list)
    experience_years: int = Field(default=0, ge=0, le=80)
    is_class_teacher: bool = False
    is_available_for_substitution: bool = True
    notes: Optional[str] = Field(default=None, max_length=2000)


class TeacherCreate(TeacherBase):
    employee_no: Optional[str] = Field(default=None, max_length=40)
    role_codes: List[str] = Field(default_factory=lambda: ["subject_teacher"])
    password: str = Field(min_length=6, max_length=128)


class TeacherUpdate(TeacherBase):
    full_name: Optional[str] = None
    employment_status: Optional[EmploymentStatus] = None


class TeacherRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    employee_no: str
    full_name: str
    first_name: Optional[str]
    last_name: Optional[str]
    photo_url: Optional[str]
    date_of_birth: Optional[date]
    gender: Optional[str]
    blood_group: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    address: Optional[str]
    emergency_contact: Optional[str]
    emergency_phone: Optional[str]
    department_id: Optional[int]
    designation: Optional[str]
    date_of_joining: Optional[date]
    qualifications: List[str]
    experience_years: int
    employment_status: EmploymentStatus
    is_class_teacher: bool
    is_available_for_substitution: bool
    notes: Optional[str]


class TeacherListPage(BaseModel):
    items: List[TeacherRead]
    total: int
    limit: int
    offset: int


# ---- Subject qualification --------------------------------------------------


class TeacherSubjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    teacher_id: int
    subject_id: int
    is_primary: bool


class TeacherSubjectsBulk(BaseModel):
    subject_ids: List[int] = Field(default_factory=list)


# ---- Section / class assignment --------------------------------------------


class AssignSectionSubject(BaseModel):
    section_subject_id: int


class AssignClassTeacher(BaseModel):
    section_id: int


# ---- Workload ---------------------------------------------------------------


class TeacherWorkloadEntry(BaseModel):
    section_subject_id: int
    section_id: int
    section_name: str
    class_def_id: int
    class_name: str
    subject_id: int
    subject_name: str
    weekly_periods: int


class TeacherWorkload(BaseModel):
    teacher_id: int
    user_id: int
    full_name: str
    weekly_periods_total: int
    classes_handled: int
    subjects_taught: int
    is_class_teacher_of_section: Optional[int] = None
    entries: List[TeacherWorkloadEntry]


# ---- Attendance -------------------------------------------------------------


class TeacherAttendanceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    teacher_id: int
    date: date
    status: AttendanceStatus
    remarks: Optional[str]


class TeacherAttendanceWrite(BaseModel):
    date: date
    status: AttendanceStatus = AttendanceStatus.PRESENT
    remarks: Optional[str] = None


class TeacherAttendanceBulkEntry(BaseModel):
    teacher_id: int
    status: AttendanceStatus = AttendanceStatus.PRESENT
    remarks: Optional[str] = None


class TeacherAttendanceBulkWrite(BaseModel):
    date: date
    entries: List[TeacherAttendanceBulkEntry]


# ---- Substitution pool ------------------------------------------------------


class SubstitutionCandidate(BaseModel):
    teacher_id: int
    user_id: int
    full_name: str
    qualifications: List[str]
    weekly_periods_total: int
    is_available_for_substitution: bool
    is_present: bool
