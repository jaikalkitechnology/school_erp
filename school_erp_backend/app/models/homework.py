"""Homework + submission entities (Phase 14)."""

from __future__ import annotations

import enum

from sqlalchemy import (
    JSON,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import TenantBase


class SubmissionStatus(str, enum.Enum):
    SUBMITTED = "submitted"
    GRADED = "graded"
    LATE = "late"
    MISSING = "missing"


class Homework(TenantBase):
    __tablename__ = "homework_assignments"
    __table_args__ = (
        Index("ix_homework_tenant_section_due", "tenant_id", "section_id", "due_date"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    section_id = Column(Integer, ForeignKey("sections.id", ondelete="CASCADE"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True)
    teacher_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(180), nullable=False)
    description = Column(Text, nullable=True)
    assigned_on = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False)
    max_marks = Column(Numeric(6, 2), nullable=False, default=0)
    attachments = Column(JSON, nullable=False, default=list)  # list[str]: per-tenant file paths

    submissions = relationship(
        "HomeworkSubmission",
        back_populates="homework",
        cascade="all, delete-orphan",
    )


class HomeworkSubmission(TenantBase):
    __tablename__ = "homework_submissions"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "homework_id", "student_id",
            name="uq_homework_submission_unique_student",
        ),
        Index("ix_homework_submissions_student", "student_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    homework_id = Column(Integer, ForeignKey("homework_assignments.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    submitted_at = Column(DateTime, nullable=True)
    content = Column(Text, nullable=True)
    attachments = Column(JSON, nullable=False, default=list)
    status = Column(String(12), nullable=False, default=SubmissionStatus.SUBMITTED.value)
    marks = Column(Numeric(6, 2), nullable=True)
    feedback = Column(Text, nullable=True)
    graded_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    graded_at = Column(DateTime, nullable=True)
    submitted_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    homework = relationship("Homework", back_populates="submissions")
