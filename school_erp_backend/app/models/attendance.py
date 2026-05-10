"""Student attendance (Phase 9)."""

from __future__ import annotations

import enum

from sqlalchemy import (
    Column,
    Date,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)

from app.database import TenantBase


class StudentAttendanceStatus(str, enum.Enum):
    PRESENT = "present"
    ABSENT = "absent"
    LATE = "late"
    LEAVE = "leave"
    HALF_DAY = "half_day"


class StudentAttendance(TenantBase):
    """One row per (student, date, period). For class teachers without
    period-wise tracking, ``period`` is left at the default 'day'."""

    __tablename__ = "student_attendance"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "student_id", "date", "period",
            name="uq_student_attendance_day",
        ),
        Index("ix_student_attendance_section_date", "section_id", "date"),
        Index("ix_student_attendance_class_date", "class_def_id", "date"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    class_def_id = Column(Integer, ForeignKey("class_defs.id", ondelete="SET NULL"), nullable=True)
    section_id = Column(Integer, ForeignKey("sections.id", ondelete="SET NULL"), nullable=True)
    date = Column(Date, nullable=False)
    period = Column(String(20), nullable=False, default="day")  # "day" | "morning" | "afternoon" | period number
    status = Column(String(12), nullable=False, default=StudentAttendanceStatus.PRESENT.value)
    marked_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    remarks = Column(String(255), nullable=True)
