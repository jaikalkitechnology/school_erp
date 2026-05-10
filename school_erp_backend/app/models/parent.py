"""Parent + multi-child plumbing.

Phase 2 ships the data model + auth flow. Phase 8 builds out the parent UI.
A minimal ``Student`` table is created here so the FK chain compiles; Phase 6
will replace it with the real SIS table.
"""

from __future__ import annotations

import enum
from datetime import date

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from app.database import TenantBase


class Relation(str, enum.Enum):
    FATHER = "father"
    MOTHER = "mother"
    GUARDIAN = "guardian"
    OTHER = "other"


class ParentAccessLevel(str, enum.Enum):
    """How much a parent row can do for a particular child.

    primary    - full access (everything secondary can do + fee.collect, leave apply)
    secondary  - read everything, can NOT pay fees
    guardian   - read attendance + fees, no notifications by default
    """
    PRIMARY = "primary"
    SECONDARY = "secondary"
    GUARDIAN = "guardian"


class LeaveStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class Student(TenantBase):
    """SIS student row - extended in Phase 6 from the Phase 2 stub.

    Source of truth for placement: ``class_def_id`` + ``section_id``.
    ``current_class_label`` is kept for legacy code and refreshed on promotion.
    """

    __tablename__ = "students"
    __table_args__ = (
        UniqueConstraint("tenant_id", "admission_number", name="uq_students_tenant_admission"),
        Index("ix_students_tenant_active", "tenant_id", "is_active"),
        Index("ix_students_tenant_section", "tenant_id", "section_id"),
        Index("ix_students_tenant_status", "tenant_id", "status"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Identity
    admission_number = Column(String(40), nullable=False)
    roll_no = Column(String(20), nullable=True)
    full_name = Column(String(180), nullable=False)
    first_name = Column(String(80), nullable=True)
    last_name = Column(String(80), nullable=True)
    date_of_birth = Column(Date, nullable=True)
    gender = Column(String(10), nullable=True)
    blood_group = Column(String(8), nullable=True)
    photo_url = Column(String(500), nullable=True)

    # Academic
    class_def_id = Column(Integer, ForeignKey("class_defs.id", ondelete="SET NULL"), nullable=True)
    section_id = Column(Integer, ForeignKey("sections.id", ondelete="SET NULL"), nullable=True)
    house_id = Column(Integer, ForeignKey("houses.id", ondelete="SET NULL"), nullable=True)
    admission_date = Column(Date, nullable=True)
    previous_school = Column(String(180), nullable=True)
    transferred_from = Column(String(180), nullable=True)
    current_class_label = Column(String(40), nullable=True)

    # Personal
    address = Column(Text, nullable=True)
    phone = Column(String(20), nullable=True)
    email = Column(String(180), nullable=True)
    aadhaar = Column(String(20), nullable=True)
    religion = Column(String(40), nullable=True)
    caste = Column(String(80), nullable=True)
    category = Column(String(20), nullable=True)  # general / obc / sc / st / ews

    # Family - denormalized for the admission flow; canonical source is the Parent rows.
    father_name = Column(String(180), nullable=True)
    mother_name = Column(String(180), nullable=True)
    guardian_name = Column(String(180), nullable=True)
    parent_phone = Column(String(20), nullable=True)
    parent_email = Column(String(180), nullable=True)
    parent_occupation = Column(String(120), nullable=True)

    # Medical
    allergies = Column(Text, nullable=True)
    medical_conditions = Column(Text, nullable=True)
    emergency_contact_name = Column(String(180), nullable=True)
    emergency_phone = Column(String(20), nullable=True)

    # Status
    is_active = Column(Boolean, nullable=False, default=True)
    status = Column(String(20), nullable=False, default="active")
    exit_date = Column(Date, nullable=True)
    remarks = Column(Text, nullable=True)

    # Sibling group: a synthetic id shared by linked siblings.
    sibling_group_id = Column(Integer, nullable=True, index=True)

    documents = relationship(
        "StudentDocument",
        cascade="all, delete-orphan",
    )


class Parent(TenantBase):
    __tablename__ = "parents"
    __table_args__ = (
        Index("ix_parents_tenant_user", "tenant_id", "user_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    full_name = Column(String(180), nullable=False)
    phone = Column(String(20), nullable=True)
    email = Column(String(180), nullable=True)
    occupation = Column(String(120), nullable=True)
    relation = Column(String(20), nullable=False, default=Relation.GUARDIAN.value)

    user = relationship("User")
    children = relationship("ParentChildMapping", back_populates="parent", cascade="all, delete-orphan")
    session = relationship("ParentSession", back_populates="parent", uselist=False, cascade="all, delete-orphan")


class ParentChildMapping(TenantBase):
    __tablename__ = "parent_child_mappings"
    __table_args__ = (
        UniqueConstraint("tenant_id", "parent_id", "student_id", name="uq_parent_child"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    parent_id = Column(Integer, ForeignKey("parents.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    relation = Column(String(20), nullable=False, default=Relation.GUARDIAN.value)
    access_level = Column(String(20), nullable=False, default=ParentAccessLevel.PRIMARY.value)
    is_primary = Column(Boolean, nullable=False, default=False)
    can_pay_fee = Column(Boolean, nullable=False, default=True)
    can_receive_notifications = Column(Boolean, nullable=False, default=True)

    parent = relationship("Parent", back_populates="children")
    student = relationship("Student")


class ParentSession(TenantBase):
    """Tracks the *currently selected* child for a multi-child parent.

    Mobile app reads + flips this when the parent uses the child switcher.
    """

    __tablename__ = "parent_sessions"
    __table_args__ = (
        UniqueConstraint("tenant_id", "parent_id", name="uq_parent_session"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    parent_id = Column(Integer, ForeignKey("parents.id", ondelete="CASCADE"), nullable=False)
    current_child_id = Column(Integer, ForeignKey("students.id", ondelete="SET NULL"), nullable=True)
    last_switched_at = Column(DateTime, server_default=func.now(), nullable=False)

    parent = relationship("Parent", back_populates="session")


class LeaveApplication(TenantBase):
    """Leave applied for a child by a parent (or by school staff on behalf)."""

    __tablename__ = "leave_applications"
    __table_args__ = (
        Index("ix_leave_tenant_student_status", "tenant_id", "student_id", "status"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_id = Column(Integer, ForeignKey("parents.id", ondelete="SET NULL"), nullable=True)
    applied_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default=LeaveStatus.PENDING.value)
    decision_remarks = Column(Text, nullable=True)
    decided_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    decided_at = Column(DateTime, nullable=True)
