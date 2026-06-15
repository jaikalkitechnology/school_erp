"""Staff leave + per-student behaviour notes — new models for the
teacher-app surface.

* ``StaffLeave``: teacher / staff applying for their own leave. Goes
  to the principal or vice_principal for decision. Distinct from
  ``LeaveApplication`` which is always student-scoped.
* ``BehaviourNote``: class teacher's day-to-day notes on student
  conduct — positive (good behaviour / merit) or concern (incidents,
  homework not done, etc.). Surfaces on the student drill-down in
  both teacher and parent apps.
"""

from __future__ import annotations

import enum

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
)

from app.database import TenantBase


class StaffLeaveStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class StaffLeave(TenantBase):
    """Teacher / staff applying for their own leave."""

    __tablename__ = "staff_leaves"
    __table_args__ = (
        Index(
            "ix_staff_leaves_tenant_user_status",
            "tenant_id", "user_id", "status",
        ),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    user_id = Column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    reason = Column(Text, nullable=False)
    kind = Column(String(40), nullable=False, default="casual")  # casual / sick / earned / unpaid / other
    status = Column(
        String(20), nullable=False, default=StaffLeaveStatus.PENDING.value,
    )
    decision_remarks = Column(Text, nullable=True)
    decided_by_user_id = Column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    decided_at = Column(DateTime, nullable=True)


class BehaviourNoteKind(str, enum.Enum):
    POSITIVE = "positive"
    CONCERN = "concern"
    NEUTRAL = "neutral"


class BehaviourNote(TenantBase):
    """Per-student behaviour log entry, written by a teacher."""

    __tablename__ = "behaviour_notes"
    __table_args__ = (
        Index(
            "ix_behaviour_notes_tenant_student",
            "tenant_id", "student_id",
        ),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    student_id = Column(
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    teacher_user_id = Column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    occurred_on = Column(Date, nullable=False)
    kind = Column(
        String(20), nullable=False, default=BehaviourNoteKind.NEUTRAL.value,
    )
    headline = Column(String(180), nullable=False)
    detail = Column(Text, nullable=True)
    visible_to_parent = Column(Boolean, nullable=False, default=True)
