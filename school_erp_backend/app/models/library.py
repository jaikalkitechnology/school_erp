"""Library entities (Phase 17)."""

from __future__ import annotations

import enum

from sqlalchemy import (
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


class CopyStatus(str, enum.Enum):
    AVAILABLE = "available"
    ISSUED = "issued"
    RESERVED = "reserved"
    LOST = "lost"
    DAMAGED = "damaged"


class LoanStatus(str, enum.Enum):
    ACTIVE = "active"
    RETURNED = "returned"
    OVERDUE = "overdue"
    LOST = "lost"


class ReservationStatus(str, enum.Enum):
    PENDING = "pending"
    READY = "ready"
    FULFILLED = "fulfilled"
    CANCELLED = "cancelled"


class BorrowerKind(str, enum.Enum):
    STUDENT = "student"
    TEACHER = "teacher"


class Book(TenantBase):
    __tablename__ = "library_books"
    __table_args__ = (
        UniqueConstraint("tenant_id", "isbn", name="uq_books_isbn"),
        Index("ix_books_tenant_title", "tenant_id", "title"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    isbn = Column(String(20), nullable=True)
    title = Column(String(200), nullable=False)
    author = Column(String(160), nullable=True)
    publisher = Column(String(160), nullable=True)
    edition = Column(String(40), nullable=True)
    category = Column(String(60), nullable=True)
    language = Column(String(20), nullable=True, default="english")
    cover_path = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    default_fine_per_day = Column(Numeric(7, 2), nullable=False, default=0)
    default_loan_days = Column(Integer, nullable=False, default=14)


class BookCopy(TenantBase):
    __tablename__ = "library_copies"
    __table_args__ = (
        UniqueConstraint("tenant_id", "barcode", name="uq_copies_barcode"),
        Index("ix_copies_book", "book_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    book_id = Column(Integer, ForeignKey("library_books.id", ondelete="CASCADE"), nullable=False)
    barcode = Column(String(60), nullable=False)
    accession_number = Column(String(60), nullable=True)
    status = Column(String(15), nullable=False, default=CopyStatus.AVAILABLE.value)
    notes = Column(String(255), nullable=True)


class Loan(TenantBase):
    __tablename__ = "library_loans"
    __table_args__ = (
        Index("ix_loans_borrower", "borrower_kind", "borrower_id"),
        Index("ix_loans_status", "tenant_id", "status"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    copy_id = Column(Integer, ForeignKey("library_copies.id", ondelete="CASCADE"), nullable=False)
    book_id = Column(Integer, ForeignKey("library_books.id", ondelete="CASCADE"), nullable=False)
    borrower_kind = Column(String(10), nullable=False)
    borrower_id = Column(Integer, nullable=False)  # student.id OR user.id (for staff)
    issued_on = Column(Date, nullable=False)
    due_on = Column(Date, nullable=False)
    returned_on = Column(Date, nullable=True)
    status = Column(String(10), nullable=False, default=LoanStatus.ACTIVE.value)
    fine_amount = Column(Numeric(8, 2), nullable=False, default=0)
    fine_paid = Column(Numeric(8, 2), nullable=False, default=0)
    issued_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    returned_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes = Column(String(255), nullable=True)


class Reservation(TenantBase):
    __tablename__ = "library_reservations"
    __table_args__ = (
        Index("ix_reservations_book", "book_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    book_id = Column(Integer, ForeignKey("library_books.id", ondelete="CASCADE"), nullable=False)
    borrower_kind = Column(String(10), nullable=False)
    borrower_id = Column(Integer, nullable=False)
    requested_at = Column(DateTime, nullable=False)
    ready_at = Column(DateTime, nullable=True)
    fulfilled_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    status = Column(String(15), nullable=False, default=ReservationStatus.PENDING.value)
