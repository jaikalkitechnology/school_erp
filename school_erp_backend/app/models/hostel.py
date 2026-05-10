"""Hostel entities (Phase 19)."""

from __future__ import annotations

import enum

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

from app.database import TenantBase


class HostelKind(str, enum.Enum):
    BOYS = "boys"
    GIRLS = "girls"
    MIXED = "mixed"


class RoomStatus(str, enum.Enum):
    AVAILABLE = "available"
    FULL = "full"
    UNDER_MAINTENANCE = "under_maintenance"


class HostelLeaveStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    RETURNED = "returned"


class DisciplinarySeverity(str, enum.Enum):
    NOTE = "note"
    WARNING = "warning"
    SUSPENSION = "suspension"


class MealType(str, enum.Enum):
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    SNACKS = "snacks"
    DINNER = "dinner"


class Hostel(TenantBase):
    __tablename__ = "hostels"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_hostels_code"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    code = Column(String(40), nullable=False)
    name = Column(String(120), nullable=False)
    kind = Column(String(10), nullable=False, default=HostelKind.BOYS.value)
    warden_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    address = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)


class Room(TenantBase):
    __tablename__ = "hostel_rooms"
    __table_args__ = (
        UniqueConstraint("tenant_id", "hostel_id", "number", name="uq_rooms_hostel_number"),
        Index("ix_rooms_hostel", "hostel_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    hostel_id = Column(Integer, ForeignKey("hostels.id", ondelete="CASCADE"), nullable=False)
    number = Column(String(40), nullable=False)
    floor = Column(String(20), nullable=True)
    capacity = Column(Integer, nullable=False, default=2)
    monthly_fee = Column(Numeric(8, 2), nullable=False, default=0)
    status = Column(String(20), nullable=False, default=RoomStatus.AVAILABLE.value)


class HostelAllocation(TenantBase):
    """One row per student. Re-allocation overwrites."""

    __tablename__ = "hostel_allocations"
    __table_args__ = (
        UniqueConstraint("tenant_id", "student_id", name="uq_hostel_alloc_student"),
        Index("ix_hostel_alloc_room", "room_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    hostel_id = Column(Integer, ForeignKey("hostels.id", ondelete="CASCADE"), nullable=False)
    room_id = Column(Integer, ForeignKey("hostel_rooms.id", ondelete="CASCADE"), nullable=False)
    occupied_from = Column(Date, nullable=False)
    occupied_until = Column(Date, nullable=True)
    monthly_fee = Column(Numeric(8, 2), nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)


class MessMenu(TenantBase):
    __tablename__ = "hostel_mess_menus"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "hostel_id", "menu_date", "meal",
            name="uq_mess_menu_unique",
        ),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    hostel_id = Column(Integer, ForeignKey("hostels.id", ondelete="CASCADE"), nullable=False)
    menu_date = Column(Date, nullable=False)
    meal = Column(String(15), nullable=False)
    items = Column(Text, nullable=False)


class VisitorLog(TenantBase):
    __tablename__ = "hostel_visitors"
    __table_args__ = (
        Index("ix_visitor_student", "student_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    hostel_id = Column(Integer, ForeignKey("hostels.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    visitor_name = Column(String(120), nullable=False)
    visitor_phone = Column(String(20), nullable=True)
    relation = Column(String(40), nullable=True)
    in_at = Column(DateTime, nullable=False)
    out_at = Column(DateTime, nullable=True)
    purpose = Column(String(200), nullable=True)
    captured_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class DisciplinaryRecord(TenantBase):
    __tablename__ = "hostel_disciplinary"
    __table_args__ = (
        Index("ix_disc_student", "student_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    hostel_id = Column(Integer, ForeignKey("hostels.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    incident_on = Column(Date, nullable=False)
    severity = Column(String(20), nullable=False, default=DisciplinarySeverity.NOTE.value)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    action_taken = Column(Text, nullable=True)
    recorded_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class HostelLeave(TenantBase):
    """Overnight / weekend pass. Distinct from the Phase 8 academic
    leave flow."""

    __tablename__ = "hostel_leaves"
    __table_args__ = (
        Index("ix_hostel_leave_student", "student_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    hostel_id = Column(Integer, ForeignKey("hostels.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    from_date = Column(Date, nullable=False)
    to_date = Column(Date, nullable=False)
    reason = Column(Text, nullable=False)
    contact_phone = Column(String(20), nullable=True)
    status = Column(String(15), nullable=False, default=HostelLeaveStatus.PENDING.value)
    decided_at = Column(DateTime, nullable=True)
    decided_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    returned_at = Column(DateTime, nullable=True)
    decision_notes = Column(Text, nullable=True)
