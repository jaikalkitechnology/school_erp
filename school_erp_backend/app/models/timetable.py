"""Time table + substitution (Phase 13).

The schema is intentionally simple:

* ``PeriodDef`` is a per-school template row for one period on one weekday
  (Mon..Sat, 0..6). Schools usually share the same period grid across
  classes; per-class deviations live as gaps in ``TimetableEntry``.
* ``TimetableEntry`` slots a (section, day_of_week, period_number) into a
  subject + teacher. The (tenant_id, section_id, day_of_week,
  period_number) tuple is unique - one cell, one entry.
* ``Substitution`` records a date-specific stand-in for an absent teacher.
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
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import TenantBase


class SubstitutionStatus(str, enum.Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PeriodDef(TenantBase):
    __tablename__ = "period_defs"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "day_of_week", "period_number",
            name="uq_period_defs_day_period",
        ),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    day_of_week = Column(Integer, nullable=False)  # 0=Mon ... 6=Sun
    period_number = Column(Integer, nullable=False)  # 1..N
    label = Column(String(40), nullable=True)
    starts_at = Column(Time, nullable=True)
    ends_at = Column(Time, nullable=True)
    is_break = Column(Boolean, nullable=False, default=False)


class TimetableEntry(TenantBase):
    __tablename__ = "timetable_entries"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "section_id", "day_of_week", "period_number",
            name="uq_timetable_cell",
        ),
        Index("ix_timetable_tenant_teacher_day", "tenant_id", "teacher_user_id", "day_of_week"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    section_id = Column(Integer, ForeignKey("sections.id", ondelete="CASCADE"), nullable=False)
    day_of_week = Column(Integer, nullable=False)
    period_number = Column(Integer, nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True)
    teacher_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    room = Column(String(40), nullable=True)
    notes = Column(String(255), nullable=True)


class Substitution(TenantBase):
    __tablename__ = "substitutions"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "date", "section_id", "period_number",
            name="uq_substitution_cell",
        ),
        Index("ix_substitutions_tenant_date_status", "tenant_id", "date", "status"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    date = Column(Date, nullable=False)
    section_id = Column(Integer, ForeignKey("sections.id", ondelete="CASCADE"), nullable=False)
    period_number = Column(Integer, nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True)
    original_teacher_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    substitute_teacher_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(12), nullable=False, default=SubstitutionStatus.PENDING.value)
    reason = Column(String(255), nullable=True)
