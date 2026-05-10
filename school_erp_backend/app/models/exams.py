"""Exam + marks + grade-scale entities (Phase 15)."""

from __future__ import annotations

import enum

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import TenantBase


class ExamType(str, enum.Enum):
    UNIT_TEST = "unit_test"
    QUARTERLY = "quarterly"
    HALF_YEARLY = "half_yearly"
    ANNUAL = "annual"
    OTHER = "other"


class ExamStatus(str, enum.Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    PUBLISHED = "published"


class MarkStatus(str, enum.Enum):
    PASS = "pass"
    FAIL = "fail"
    ABSENT = "absent"
    EXEMPT = "exempt"


class Exam(TenantBase):
    __tablename__ = "exams"
    __table_args__ = (
        UniqueConstraint("tenant_id", "year_id", "name", name="uq_exams_year_name"),
        Index("ix_exams_tenant_status", "tenant_id", "status"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    year_id = Column(Integer, ForeignKey("academic_years.id", ondelete="SET NULL"), nullable=True)
    term_id = Column(Integer, ForeignKey("academic_terms.id", ondelete="SET NULL"), nullable=True)
    name = Column(String(120), nullable=False)
    kind = Column(String(20), nullable=False, default=ExamType.UNIT_TEST.value)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    default_max_marks = Column(Numeric(6, 2), nullable=False, default=100)
    status = Column(String(15), nullable=False, default=ExamStatus.DRAFT.value)
    published_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)

    subjects = relationship(
        "ExamSubject",
        back_populates="exam",
        cascade="all, delete-orphan",
    )


class ExamSubject(TenantBase):
    __tablename__ = "exam_subjects"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "exam_id", "class_def_id", "subject_id",
            name="uq_exam_subject_target",
        ),
        Index("ix_exam_subjects_class", "class_def_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    exam_id = Column(Integer, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False)
    class_def_id = Column(Integer, ForeignKey("class_defs.id", ondelete="CASCADE"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    max_marks = Column(Numeric(6, 2), nullable=False, default=100)
    passing_marks = Column(Numeric(6, 2), nullable=False, default=33)
    exam_date = Column(Date, nullable=True)
    starts_at = Column(Time, nullable=True)
    ends_at = Column(Time, nullable=True)

    exam = relationship("Exam", back_populates="subjects")


class ExamMarks(TenantBase):
    __tablename__ = "exam_marks"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "exam_subject_id", "student_id",
            name="uq_exam_marks_unique",
        ),
        Index("ix_exam_marks_student", "student_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    exam_subject_id = Column(Integer, ForeignKey("exam_subjects.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    obtained_marks = Column(Numeric(6, 2), nullable=True)
    status = Column(String(10), nullable=False, default=MarkStatus.PASS.value)
    remarks = Column(String(255), nullable=True)
    entered_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class GradeScale(TenantBase):
    """A named grading rubric. ``bands`` is an ordered JSON list of:
        {"min_pct": 90, "grade": "A+", "gpa": 10}
    """

    __tablename__ = "grade_scales"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_grade_scales_code"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    code = Column(String(40), nullable=False)
    name = Column(String(120), nullable=False)
    bands = Column(JSON, nullable=False, default=list)
    is_default = Column(Boolean, nullable=False, default=False)
