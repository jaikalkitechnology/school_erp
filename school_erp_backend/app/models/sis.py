"""SIS: full Student model + admission inquiry + document slots.

Phase 6 promotes the Phase 2 Student stub to a real entity. Existing
columns (``admission_number``, ``full_name``, ``date_of_birth``,
``current_class_label``, ``is_active``) are kept for backward compatibility;
``current_class_label`` is now derived (set on promotion) and the source of
truth for placement is ``class_def_id`` + ``section_id``.
"""

from __future__ import annotations

import enum

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import TenantBase


class StudentStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    TRANSFERRED = "transferred"
    PASSED_OUT = "passed_out"


class Gender(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class Category(str, enum.Enum):
    GENERAL = "general"
    OBC = "obc"
    SC = "sc"
    ST = "st"
    EWS = "ews"


class AdmissionStage(str, enum.Enum):
    INQUIRY = "inquiry"
    APPLIED = "applied"
    DOCS_VERIFIED = "docs_verified"
    OFFERED = "offered"
    ADMITTED = "admitted"
    REJECTED = "rejected"


class StudentDocument(TenantBase):
    """Pointer to a file under uploads/tenant_X/students/documents/."""

    __tablename__ = "student_documents"
    __table_args__ = (
        Index("ix_student_documents_student", "student_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    kind = Column(String(40), nullable=False)  # birth_certificate / aadhaar / tc / photo / caste / address
    label = Column(String(120), nullable=True)
    path = Column(String(500), nullable=False)  # relative to uploads/
    is_verified = Column(Boolean, nullable=False, default=False)
    notes = Column(Text, nullable=True)


class Admission(TenantBase):
    """Admission funnel: inquiry -> applied -> admitted.

    Becomes a Student row only when ``stage == ADMITTED``.
    """

    __tablename__ = "admissions"
    __table_args__ = (
        Index("ix_admissions_tenant_stage", "tenant_id", "stage"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    full_name = Column(String(180), nullable=False)
    date_of_birth = Column(Date, nullable=True)
    gender = Column(String(10), nullable=True)
    parent_name = Column(String(180), nullable=True)
    parent_phone = Column(String(20), nullable=True)
    parent_email = Column(String(180), nullable=True)
    desired_class_id = Column(Integer, ForeignKey("class_defs.id", ondelete="SET NULL"), nullable=True)
    previous_school = Column(String(180), nullable=True)
    notes = Column(Text, nullable=True)
    stage = Column(String(20), nullable=False, default=AdmissionStage.INQUIRY.value)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="SET NULL"), nullable=True)


# Note: the Student model continues to live in app.models.parent for now
# because Phase 2's parent module already imports it and the relationships
# point at it. Phase 6 *extends* that table - see the Alembic migration in
# this phase.
