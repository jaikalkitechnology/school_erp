"""Pydantic schemas for the SIS module."""

from __future__ import annotations

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.sis import AdmissionStage, Category, Gender, StudentStatus


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
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[Gender] = None
    blood_group: Optional[str] = None
    photo_url: Optional[str] = None

    class_def_id: Optional[int] = None
    section_id: Optional[int] = None
    house_id: Optional[int] = None
    admission_date: Optional[date] = None
    previous_school: Optional[str] = None

    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    aadhaar: Optional[str] = None
    religion: Optional[str] = None
    caste: Optional[str] = None
    category: Optional[Category] = None

    father_name: Optional[str] = None
    mother_name: Optional[str] = None
    guardian_name: Optional[str] = None
    parent_phone: Optional[str] = None
    parent_email: Optional[str] = None
    parent_occupation: Optional[str] = None

    allergies: Optional[str] = None
    medical_conditions: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_phone: Optional[str] = None

    roll_no: Optional[str] = None
    remarks: Optional[str] = None


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
    email: Optional[str]
    aadhaar: Optional[str]
    religion: Optional[str]
    caste: Optional[str]
    category: Optional[str]

    father_name: Optional[str]
    mother_name: Optional[str]
    guardian_name: Optional[str]
    parent_phone: Optional[str]
    parent_email: Optional[str]
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
    parent_email: Optional[str]
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
    parent_email: Optional[str] = None
    desired_class_id: Optional[int] = None
    previous_school: Optional[str] = None
    notes: Optional[str] = None
    stage: AdmissionStage = AdmissionStage.INQUIRY


class AdmissionStageUpdate(BaseModel):
    stage: AdmissionStage


class SiblingLinkRequest(BaseModel):
    student_ids: list[int] = Field(min_length=2, description="At least 2 student ids")
