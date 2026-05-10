"""Academic structure: departments, classes, sections, subjects,
academic years + terms, holidays.

All tenant-scoped (auto-filtered when accessed via tenant_scoped_session).
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


class ClassStage(str, enum.Enum):
    PRE_PRIMARY = "pre_primary"
    PRIMARY = "primary"
    MIDDLE = "middle"
    SECONDARY = "secondary"
    SENIOR_SECONDARY = "senior_secondary"


class HolidayKind(str, enum.Enum):
    PUBLIC = "public"
    SCHOOL = "school"
    OPTIONAL = "optional"
    VACATION = "vacation"


class Department(TenantBase):
    __tablename__ = "departments"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_departments_tenant_name"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    name = Column(String(80), nullable=False)
    code = Column(String(20), nullable=True)
    description = Column(String(255), nullable=True)
    head_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    head = relationship("User", foreign_keys=[head_user_id])


class AcademicYear(TenantBase):
    __tablename__ = "academic_years"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_academic_years_tenant_code"),
        Index("ix_academic_years_tenant_active", "tenant_id", "is_active"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    code = Column(String(20), nullable=False)  # "2025-26"
    name = Column(String(80), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    is_active = Column(Boolean, nullable=False, default=False)

    terms = relationship("AcademicTerm", back_populates="year", cascade="all, delete-orphan")


class AcademicTerm(TenantBase):
    __tablename__ = "academic_terms"
    __table_args__ = (
        UniqueConstraint("tenant_id", "year_id", "name", name="uq_terms_year_name"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    year_id = Column(Integer, ForeignKey("academic_years.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(40), nullable=False)  # Term 1 / Mid / Final
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)

    year = relationship("AcademicYear", back_populates="terms")


class ClassDef(TenantBase):
    """A class definition (Nursery, 1, 2, …, 12). Sections live below this."""

    __tablename__ = "class_defs"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_class_defs_tenant_code"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    code = Column(String(20), nullable=False)  # "1", "10", "LKG"
    name = Column(String(80), nullable=False)  # "Class 1"
    stage = Column(String(30), nullable=False, default=ClassStage.PRIMARY.value)
    sequence = Column(Integer, nullable=False, default=0)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)

    department = relationship("Department")
    sections = relationship("Section", back_populates="class_def", cascade="all, delete-orphan")


class Section(TenantBase):
    __tablename__ = "sections"
    __table_args__ = (
        UniqueConstraint("tenant_id", "class_def_id", "name", name="uq_sections_class_name"),
        Index("ix_sections_tenant_class", "tenant_id", "class_def_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    class_def_id = Column(Integer, ForeignKey("class_defs.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(20), nullable=False)  # "A", "B"
    capacity = Column(Integer, nullable=False, default=40)
    in_charge_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    class_def = relationship("ClassDef", back_populates="sections")
    in_charge = relationship("User", foreign_keys=[in_charge_user_id])


class Subject(TenantBase):
    __tablename__ = "subjects"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_subjects_tenant_code"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    code = Column(String(20), nullable=False)  # MATH, ENG, HIN, SCI
    name = Column(String(80), nullable=False)
    is_core = Column(Boolean, nullable=False, default=True)
    is_language = Column(Boolean, nullable=False, default=False)
    has_practical = Column(Boolean, nullable=False, default=False)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)

    department = relationship("Department")


class ClassSubject(TenantBase):
    """Which subjects are taught at which class level."""

    __tablename__ = "class_subjects"
    __table_args__ = (
        UniqueConstraint("tenant_id", "class_def_id", "subject_id", name="uq_class_subject"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    class_def_id = Column(Integer, ForeignKey("class_defs.id", ondelete="CASCADE"), nullable=False, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True)
    is_optional = Column(Boolean, nullable=False, default=False)


class Holiday(TenantBase):
    __tablename__ = "holidays"
    __table_args__ = (
        UniqueConstraint("tenant_id", "date", "kind", "name", name="uq_holidays_tenant_date_kind_name"),
        Index("ix_holidays_tenant_date", "tenant_id", "date"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    date = Column(Date, nullable=False)
    name = Column(String(120), nullable=False)
    kind = Column(String(20), nullable=False, default=HolidayKind.PUBLIC.value)
    description = Column(Text, nullable=True)
    year_id = Column(Integer, ForeignKey("academic_years.id", ondelete="SET NULL"), nullable=True, index=True)
