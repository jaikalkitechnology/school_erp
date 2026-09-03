"""Pydantic schemas for the SIS module."""

from __future__ import annotations

import re
from datetime import date
from typing import Annotated, List, Optional

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    EmailStr,
    Field,
)

from app.models.sis import AdmissionStage, Category, Gender, StudentStatus


def _blank_to_none(v):
    """Treat empty / whitespace-only strings as None. Lets an optional
    email field come in blank from a form or CSV import without tripping
    EmailStr validation."""
    if v is None:
        return None
    if isinstance(v, str) and v.strip() == "":
        return None
    return v


def _clean_phone(v):
    """Blank → None; otherwise normalise to a 10-digit number (tolerating
    spaces, dashes, a +91 or leading-0 prefix) and reject anything else."""
    v = _blank_to_none(v)
    if v is None:
        return None
    digits = re.sub(r"\D", "", str(v))
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    if len(digits) != 10:
        raise ValueError("Phone must be a 10-digit number")
    return digits


def _clean_aadhaar(v):
    """Blank → None; otherwise require exactly 12 digits."""
    v = _blank_to_none(v)
    if v is None:
        return None
    digits = re.sub(r"\D", "", str(v))
    if len(digits) != 12:
        raise ValueError("Aadhaar must be a 12-digit number")
    return digits


# Optional email that (a) maps blank → None, (b) validates format when
# a value is present. Used for every student/parent email field so a
# malformed address can't silently persist into login / notify flows.
OptionalEmail = Annotated[Optional[EmailStr], BeforeValidator(_blank_to_none)]
# Optional phone / aadhaar with the same blank→None + format guarantees.
OptionalPhone = Annotated[Optional[str], BeforeValidator(_clean_phone)]
OptionalAadhaar = Annotated[Optional[str], BeforeValidator(_clean_aadhaar)]


# ---- Documents -------------------------------------------------------------


class StudentDocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    student_id: int
    kind: str
    label: Optional[str]
    path: str
    is_verified: bool
    notes: Optional[str]


class StudentDocumentWrite(BaseModel):
    kind: str = Field(min_length=1, max_length=40)
    label: Optional[str] = Field(default=None, max_length=120)
    path: str = Field(min_length=1, max_length=500)
    notes: Optional[str] = None


# ---- Student ---------------------------------------------------------------


class StudentBase(BaseModel):
    full_name: str = Field(min_length=2, max_length=180)
    first_name: Optional[str] = Field(default=None, max_length=90)
    last_name: Optional[str] = Field(default=None, max_length=90)
    date_of_birth: Optional[date] = None
    gender: Optional[Gender] = None
    blood_group: Optional[str] = Field(default=None, max_length=8)
    photo_url: Optional[str] = Field(default=None, max_length=500)

    class_def_id: Optional[int] = None
    section_id: Optional[int] = None
    house_id: Optional[int] = None
    admission_date: Optional[date] = None
    previous_school: Optional[str] = Field(default=None, max_length=180)

    address: Optional[str] = Field(default=None, max_length=500)
    phone: OptionalPhone = None
    email: OptionalEmail = None
    aadhaar: OptionalAadhaar = None
    religion: Optional[str] = Field(default=None, max_length=60)
    caste: Optional[str] = Field(default=None, max_length=60)
    category: Optional[Category] = None

    father_name: Optional[str] = Field(default=None, max_length=120)
    mother_name: Optional[str] = Field(default=None, max_length=120)
    guardian_name: Optional[str] = Field(default=None, max_length=120)
    parent_phone: OptionalPhone = None
    parent_email: OptionalEmail = None
    parent_occupation: Optional[str] = Field(default=None, max_length=120)

    allergies: Optional[str] = Field(default=None, max_length=500)
    medical_conditions: Optional[str] = Field(default=None, max_length=1000)
    emergency_contact_name: Optional[str] = Field(default=None, max_length=120)
    emergency_phone: OptionalPhone = None

    roll_no: Optional[str] = Field(default=None, max_length=20)
    remarks: Optional[str] = Field(default=None, max_length=1000)


class StudentCreate(StudentBase):
    admission_number: Optional[str] = Field(
        default=None,
        max_length=40,
        description="Auto-generated when omitted (ADM-YY-NNNN format).",
    )


class StudentUpdate(StudentBase):
    full_name: Optional[str] = None
    status: Optional[StudentStatus] = None
    is_active: Optional[bool] = None


class StudentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    admission_number: str
    roll_no: Optional[str]
    full_name: str
    first_name: Optional[str]
    last_name: Optional[str]
    date_of_birth: Optional[date]
    gender: Optional[str]
    blood_group: Optional[str]
    photo_url: Optional[str]

    class_def_id: Optional[int]
    section_id: Optional[int]
    house_id: Optional[int]
    admission_date: Optional[date]
    previous_school: Optional[str]
    current_class_label: Optional[str]

    address: Optional[str]
    phone: Optional[str]
    email: Optional[str]  # read side: tolerate legacy malformed data
    aadhaar: Optional[str]
    religion: Optional[str]
    caste: Optional[str]
    category: Optional[str]

    father_name: Optional[str]
    mother_name: Optional[str]
    guardian_name: Optional[str]
    parent_phone: Optional[str]
    parent_email: Optional[str]  # read side: tolerate legacy malformed data
    parent_occupation: Optional[str]

    allergies: Optional[str]
    medical_conditions: Optional[str]
    emergency_contact_name: Optional[str]
    emergency_phone: Optional[str]

    is_active: bool
    status: StudentStatus
    exit_date: Optional[date]
    remarks: Optional[str]
    sibling_group_id: Optional[int]


class StudentDetail(StudentRead):
    documents: List[StudentDocumentRead] = Field(default_factory=list)
    sibling_ids: List[int] = Field(default_factory=list)


class StudentListPage(BaseModel):
    items: List[StudentRead]
    total: int
    limit: int
    offset: int


class WithdrawRequest(BaseModel):
    status: StudentStatus = StudentStatus.TRANSFERRED
    exit_date: Optional[date] = None
    remarks: Optional[str] = None


class TransferCertificate(BaseModel):
    """Phase 6 returns the data needed to print a TC. PDF rendering is Phase 16."""

    student: StudentRead
    issued_on: date
    school_name: str
    school_subdomain: str
    last_class_label: Optional[str]
    reason: Optional[str]


class PromotionRequest(BaseModel):
    student_ids: list[int]
    target_class_def_id: int
    target_section_id: Optional[int] = None
    new_admission_year_label: Optional[str] = None  # e.g. "2025-26"


class PromotionResult(BaseModel):
    promoted: list[int]
    skipped: list[dict]


# ---- Admission -------------------------------------------------------------


class AdmissionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    full_name: str
    date_of_birth: Optional[date]
    gender: Optional[str]
    parent_name: Optional[str]
    parent_phone: Optional[str]
    parent_email: Optional[str]  # read side: tolerate legacy malformed data
    desired_class_id: Optional[int]
    previous_school: Optional[str]
    notes: Optional[str]
    stage: AdmissionStage
    student_id: Optional[int]


class AdmissionWrite(BaseModel):
    full_name: str = Field(min_length=2, max_length=180)
    date_of_birth: Optional[date] = None
    gender: Optional[Gender] = None
    parent_name: Optional[str] = None
    parent_phone: Optional[str] = None
    parent_email: OptionalEmail = None
    desired_class_id: Optional[int] = None
    previous_school: Optional[str] = None
    notes: Optional[str] = None
    stage: AdmissionStage = AdmissionStage.INQUIRY


class AdmissionStageUpdate(BaseModel):
    stage: AdmissionStage


class SiblingLinkRequest(BaseModel):
    student_ids: list[int] = Field(min_length=2, description="At least 2 student ids")
