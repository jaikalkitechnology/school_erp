"""Teacher Management entities (Phase 7).

A teacher is a User wearing one of {class_teacher, subject_teacher,
coordinator, principal, vice_principal} plus a richer profile row owned by
this module.
"""

from __future__ import annotations

import enum

from sqlalchemy import (
    JSON,
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


class EmploymentStatus(str, enum.Enum):
    ACTIVE = "active"
    ON_LEAVE = "on_leave"
    RESIGNED = "resigned"


class AttendanceStatus(str, enum.Enum):
    PRESENT = "present"
    ABSENT = "absent"
    LEAVE = "leave"
    HALF_DAY = "half_day"


class Teacher(TenantBase):
    __tablename__ = "teachers"
    __table_args__ = (
        UniqueConstraint("tenant_id", "employee_no", name="uq_teachers_tenant_employee_no"),
        UniqueConstraint("tenant_id", "user_id", name="uq_teachers_tenant_user"),
        Index("ix_teachers_tenant_status", "tenant_id", "employment_status"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    employee_no = Column(String(40), nullable=False)
    first_name = Column(String(80), nullable=True)
    last_name = Column(String(80), nullable=True)
    full_name = Column(String(180), nullable=False)
    photo_url = Column(String(500), nullable=True)

    date_of_birth = Column(Date, nullable=True)
    gender = Column(String(10), nullable=True)
    blood_group = Column(String(8), nullable=True)
    phone = Column(String(20), nullable=True)
    email = Column(String(180), nullable=True)
    address = Column(Text, nullable=True)
    emergency_contact = Column(String(180), nullable=True)
    emergency_phone = Column(String(20), nullable=True)

    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    designation = Column(String(80), nullable=True)
    date_of_joining = Column(Date, nullable=True)
    qualifications = Column(JSON, nullable=False, default=list)  # ["B.Ed", "M.Sc Math"]
    experience_years = Column(Integer, nullable=False, default=0)

    employment_status = Column(String(20), nullable=False, default=EmploymentStatus.ACTIVE.value)
    is_class_teacher = Column(Boolean, nullable=False, default=False)
    is_available_for_substitution = Column(Boolean, nullable=False, default=True)
    notes = Column(Text, nullable=True)

    user = relationship("User", foreign_keys=[user_id])
    qualified_subjects = relationship(
        "TeacherSubject",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class TeacherSubject(TenantBase):
    """Subjects this teacher is *qualified* to teach.

    Distinct from `SectionSubject.teacher_user_id`, which records the *actual*
    teacher running a particular section's subject.
    """

    __tablename__ = "teacher_subjects"
    __table_args__ = (
        UniqueConstraint("tenant_id", "teacher_id", "subject_id", name="uq_teacher_subject"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    teacher_id = Column(Integer, ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True)
    is_primary = Column(Boolean, nullable=False, default=False)


class TeacherAttendance(TenantBase):
    """Daily attendance for staff. Phase 9 will reuse the same approach for students."""

    __tablename__ = "teacher_attendance"
    __table_args__ = (
        UniqueConstraint("tenant_id", "teacher_id", "date", name="uq_teacher_attendance_day"),
        Index("ix_teacher_attendance_tenant_date", "tenant_id", "date"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    teacher_id = Column(Integer, ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    status = Column(String(12), nullable=False, default=AttendanceStatus.PRESENT.value)
    remarks = Column(String(255), nullable=True)
