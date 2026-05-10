"""Subscription billing entities (Phase 21).

These are *platform* billing rows — what the platform charges each tenant
for the SaaS plan. Distinct from Phase 11's `fee_invoices` which model
the school billing its parents.
"""

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
from sqlalchemy.orm import relationship

from app.database import Base, TimestampMixin


class BillingInvoiceStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING = "pending"
    PARTIAL = "partial"
    PAID = "paid"
    VOID = "void"
    REFUNDED = "refunded"


class BillingPaymentStatus(str, enum.Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    REFUNDED = "refunded"


class BillingPaymentMethod(str, enum.Enum):
    BANK_TRANSFER = "bank_transfer"
    UPI = "upi"
    RAZORPAY = "razorpay"
    CREDIT_NOTE = "credit_note"
    OTHER = "other"


class BillingInvoice(Base, TimestampMixin):
    """Platform → tenant invoice for a subscription period.

    *Not* a TenantBase row: super admin can read across all tenants.
    """

    __tablename__ = "billing_invoices"
    __table_args__ = (
        UniqueConstraint("invoice_number", name="uq_billing_invoices_number"),
        Index("ix_billing_invoices_tenant", "tenant_id"),
        Index("ix_billing_invoices_status", "status"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    plan_id = Column(Integer, ForeignKey("subscription_plans.id", ondelete="SET NULL"), nullable=True)
    invoice_number = Column(String(40), nullable=False)

    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    issued_on = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False)

    # Money: subtotal -> tax -> total. Paid amount tracked for partial pays.
    subtotal = Column(Numeric(12, 2), nullable=False, default=0)
    discount_amount = Column(Numeric(12, 2), nullable=False, default=0)
    tax_amount = Column(Numeric(12, 2), nullable=False, default=0)
    cgst_amount = Column(Numeric(12, 2), nullable=False, default=0)
    sgst_amount = Column(Numeric(12, 2), nullable=False, default=0)
    igst_amount = Column(Numeric(12, 2), nullable=False, default=0)
    total_amount = Column(Numeric(12, 2), nullable=False, default=0)
    paid_amount = Column(Numeric(12, 2), nullable=False, default=0)
    refunded_amount = Column(Numeric(12, 2), nullable=False, default=0)

    gst_treatment = Column(String(20), nullable=False, default="intra")  # intra | inter | exempt
    place_of_supply = Column(String(80), nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(String(15), nullable=False, default=BillingInvoiceStatus.PENDING.value)

    payments = relationship(
        "BillingPayment", back_populates="invoice", cascade="all, delete-orphan"
    )
    refunds = relationship(
        "BillingRefund", back_populates="invoice", cascade="all, delete-orphan"
    )


class BillingPayment(Base, TimestampMixin):
    __tablename__ = "billing_payments"
    __table_args__ = (
        Index("ix_billing_payments_invoice", "invoice_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_id = Column(Integer, ForeignKey("billing_invoices.id", ondelete="CASCADE"), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False, default=0)
    method = Column(String(20), nullable=False, default=BillingPaymentMethod.BANK_TRANSFER.value)
    status = Column(String(12), nullable=False, default=BillingPaymentStatus.SUCCESS.value)
    reference = Column(String(120), nullable=True)
    received_on = Column(DateTime, nullable=False)
    received_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes = Column(Text, nullable=True)

    invoice = relationship("BillingInvoice", back_populates="payments")


class BillingRefund(Base, TimestampMixin):
    __tablename__ = "billing_refunds"
    __table_args__ = (
        Index("ix_billing_refunds_invoice", "invoice_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_id = Column(Integer, ForeignKey("billing_invoices.id", ondelete="CASCADE"), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False, default=0)
    reason = Column(String(255), nullable=True)
    refunded_on = Column(DateTime, nullable=False)
    refunded_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    invoice = relationship("BillingInvoice", back_populates="refunds")
