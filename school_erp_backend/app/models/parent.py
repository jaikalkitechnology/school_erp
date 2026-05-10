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
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from app.database import TenantBase


class Relation(str, enum.Enum):
    FATHER = "father"
    MOTHER = "mother"
    GUARDIAN = "guardian"


class Student(TenantBase):
    """Minimal student row.

    Phase 6 (SIS) will add demographics, admission flow, documents, etc.
    For now we just need an entity to map parents onto.
    """

    __tablename__ = "students"
    __table_args__ = (
        UniqueConstraint("tenant_id", "admission_number", name="uq_students_tenant_admission"),
        Index("ix_students_tenant_active", "tenant_id", "is_active"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    admission_number = Column(String(40), nullable=False)
    full_name = Column(String(180), nullable=False)
    date_of_birth = Column(Date, nullable=True)
    current_class_label = Column(String(40), nullable=True)  # "Class 5 - A" until Phase 5
    is_active = Column(Boolean, nullable=False, default=True)


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
