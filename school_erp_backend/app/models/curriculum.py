"""Phase 5 entities: house system, section-subject mapping, calendar events,
syllabus + chapter tracking.

Teacher-subject and student-class mappings ship with their owning phases
(Phase 7 + Phase 6) where the Teacher / Student entities become real.
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
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import TenantBase


class CalendarEventKind(str, enum.Enum):
    GENERAL = "general"
    EXAM = "exam"
    SPORTS = "sports"
    CULTURAL = "cultural"
    PARENT_TEACHER = "parent_teacher"
    HOLIDAY = "holiday"


class House(TenantBase):
    __tablename__ = "houses"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_houses_tenant_name"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    name = Column(String(40), nullable=False)
    code = Column(String(20), nullable=True)  # R / B / G / Y
    color = Column(String(9), nullable=False, default="#E85D2E")
    motto = Column(String(200), nullable=True)
    captain_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    captain = relationship("User", foreign_keys=[captain_user_id])


class SectionSubject(TenantBase):
    """Subject taught in a particular section.

    Phase 7 will add ``teacher_user_id`` FK once the Teacher table lands.
    For now we keep it nullable so school admins can set up the curriculum
    map before staff is in the system.
    """

    __tablename__ = "section_subjects"
    __table_args__ = (
        UniqueConstraint("tenant_id", "section_id", "subject_id", name="uq_section_subject"),
        Index("ix_section_subject_section", "section_id"),
        Index("ix_section_subject_subject", "subject_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    section_id = Column(Integer, ForeignKey("sections.id", ondelete="CASCADE"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    teacher_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    weekly_periods = Column(Integer, nullable=False, default=4)
    is_optional = Column(Boolean, nullable=False, default=False)


class CalendarEvent(TenantBase):
    __tablename__ = "calendar_events"
    __table_args__ = (
        Index("ix_calendar_tenant_date", "tenant_id", "starts_at"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    title = Column(String(180), nullable=False)
    description = Column(Text, nullable=True)
    kind = Column(String(30), nullable=False, default=CalendarEventKind.GENERAL.value)
    starts_at = Column(DateTime, nullable=False)
    ends_at = Column(DateTime, nullable=True)
    is_all_day = Column(Boolean, nullable=False, default=True)
    year_id = Column(Integer, ForeignKey("academic_years.id", ondelete="SET NULL"), nullable=True)
    term_id = Column(Integer, ForeignKey("academic_terms.id", ondelete="SET NULL"), nullable=True)
    audience = Column(String(40), nullable=False, default="all")  # all / staff / parents / class:5A


class Syllabus(TenantBase):
    """Per (class, subject) syllabus for an academic year."""

    __tablename__ = "syllabi"
    __table_args__ = (
        UniqueConstraint("tenant_id", "year_id", "class_def_id", "subject_id", name="uq_syllabus_target"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    year_id = Column(Integer, ForeignKey("academic_years.id", ondelete="CASCADE"), nullable=False, index=True)
    class_def_id = Column(Integer, ForeignKey("class_defs.id", ondelete="CASCADE"), nullable=False, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(180), nullable=False)
    description = Column(Text, nullable=True)

    chapters = relationship(
        "Chapter",
        back_populates="syllabus",
        cascade="all, delete-orphan",
        order_by="Chapter.sequence",
    )


class Chapter(TenantBase):
    __tablename__ = "syllabus_chapters"
    __table_args__ = (
        Index("ix_chapter_syllabus", "syllabus_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    syllabus_id = Column(Integer, ForeignKey("syllabi.id", ondelete="CASCADE"), nullable=False)
    sequence = Column(Integer, nullable=False, default=0)
    title = Column(String(180), nullable=False)
    summary = Column(Text, nullable=True)
    expected_periods = Column(Integer, nullable=False, default=4)
    target_completion_date = Column(Date, nullable=True)
    completion_pct = Column(Numeric(5, 2), nullable=False, default=0)
    completed_on = Column(Date, nullable=True)

    syllabus = relationship("Syllabus", back_populates="chapters")
