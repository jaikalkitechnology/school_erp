"""Fee management entities (Phase 11).

Hierarchy:
    FeeCategory  ─── tuition / transport / lab / hostel ...
        ▲
        │
    FeeStructure  ──── per (class_def, category, period)
        │  amount, due_day_of_month, late_fee_per_day
        ▼
    FeeInvoice    ──── per (student, structure, period_instance)
        │  base_amount, discount, late_fee, total, paid, status
        ▼
    FeePayment    ──── per (invoice, method, ref, gateway_*)

    FeeDiscount   ──── manual / scholarship / staff-ward overrides per student.
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
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import TenantBase


class FeePeriod(str, enum.Enum):
    ONE_TIME = "one_time"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


class FeeInvoiceStatus(str, enum.Enum):
    PENDING = "pending"
    PARTIAL = "partial"
    PAID = "paid"
    OVERDUE = "overdue"
    WAIVED = "waived"
    CANCELLED = "cancelled"


class PaymentMethod(str, enum.Enum):
    CASH = "cash"
    UPI = "upi"
    CARD = "card"
    NETBANKING = "netbanking"
    CHEQUE = "cheque"
    BANK_TRANSFER = "bank_transfer"


class PaymentStatus(str, enum.Enum):
    INITIATED = "initiated"
    SUCCESS = "success"
    FAILED = "failed"
    REFUNDED = "refunded"


class DiscountKind(str, enum.Enum):
    SIBLING = "sibling"
    SCHOLARSHIP = "scholarship"
    STAFF_WARD = "staff_ward"
    MANUAL = "manual"


class FeeCategory(TenantBase):
    __tablename__ = "fee_categories"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_fee_categories_tenant_code"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    code = Column(String(40), nullable=False)
    name = Column(String(120), nullable=False)
    is_recurring = Column(Boolean, nullable=False, default=True)
    description = Column(String(255), nullable=True)


class FeeStructure(TenantBase):
    __tablename__ = "fee_structures"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "class_def_id", "category_id", "period",
            name="uq_fee_structures_target",
        ),
        Index("ix_fee_structures_tenant_class", "tenant_id", "class_def_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    class_def_id = Column(Integer, ForeignKey("class_defs.id", ondelete="CASCADE"), nullable=False)
    category_id = Column(Integer, ForeignKey("fee_categories.id", ondelete="CASCADE"), nullable=False)
    period = Column(String(20), nullable=False, default=FeePeriod.MONTHLY.value)
    amount = Column(Numeric(12, 2), nullable=False, default=0)
    due_day_of_month = Column(Integer, nullable=False, default=10)
    late_fee_per_day = Column(Numeric(10, 2), nullable=False, default=0)
    grace_days = Column(Integer, nullable=False, default=5)
    notes = Column(Text, nullable=True)

    category = relationship("FeeCategory", lazy="joined")


class FeeInvoice(TenantBase):
    __tablename__ = "fee_invoices"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "student_id", "structure_id", "period_start",
            name="uq_fee_invoices_period",
        ),
        Index("ix_fee_invoices_tenant_student_status", "tenant_id", "student_id", "status"),
        Index("ix_fee_invoices_due_date", "due_date"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    structure_id = Column(Integer, ForeignKey("fee_structures.id", ondelete="SET NULL"), nullable=True)
    category_id = Column(Integer, ForeignKey("fee_categories.id", ondelete="SET NULL"), nullable=True)

    invoice_number = Column(String(40), nullable=False)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False)

    base_amount = Column(Numeric(12, 2), nullable=False, default=0)
    discount_amount = Column(Numeric(12, 2), nullable=False, default=0)
    late_fee_amount = Column(Numeric(12, 2), nullable=False, default=0)
    total_amount = Column(Numeric(12, 2), nullable=False, default=0)
    paid_amount = Column(Numeric(12, 2), nullable=False, default=0)
    status = Column(String(12), nullable=False, default=FeeInvoiceStatus.PENDING.value)
    notes = Column(Text, nullable=True)

    payments = relationship("FeePayment", back_populates="invoice", cascade="all, delete-orphan")


class FeePayment(TenantBase):
    __tablename__ = "fee_payments"
    __table_args__ = (
        Index("ix_fee_payments_tenant_invoice", "tenant_id", "invoice_id"),
        Index("ix_fee_payments_tenant_paid_at", "tenant_id", "paid_at"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    invoice_id = Column(Integer, ForeignKey("fee_invoices.id", ondelete="CASCADE"), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False, default=0)
    method = Column(String(20), nullable=False, default=PaymentMethod.CASH.value)
    status = Column(String(12), nullable=False, default=PaymentStatus.SUCCESS.value)
    reference = Column(String(120), nullable=True)
    gateway_order_id = Column(String(120), nullable=True, index=True)
    gateway_payment_id = Column(String(120), nullable=True)
    paid_at = Column(DateTime, nullable=True)
    received_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes = Column(Text, nullable=True)

    invoice = relationship("FeeInvoice", back_populates="payments")


class FeeDiscount(TenantBase):
    __tablename__ = "fee_discounts"
    __table_args__ = (
        Index("ix_fee_discounts_tenant_student", "tenant_id", "student_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    kind = Column(String(20), nullable=False, default=DiscountKind.MANUAL.value)
    percent = Column(Numeric(5, 2), nullable=True)
    amount = Column(Numeric(12, 2), nullable=True)
    reason = Column(Text, nullable=True)
    applies_from = Column(Date, nullable=True)
    applies_to = Column(Date, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
