"""Fee management schemas (Phase 11)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.fees import (
    DiscountKind,
    FeeInvoiceStatus,
    FeePeriod,
    PaymentMethod,
    PaymentStatus,
)


# ---- Categories ------------------------------------------------------------


class FeeCategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str
    is_recurring: bool
    description: Optional[str]


class FeeCategoryWrite(BaseModel):
    code: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=120)
    is_recurring: bool = True
    description: Optional[str] = Field(default=None, max_length=255)


# ---- Structures ------------------------------------------------------------


class FeeStructureRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    class_def_id: int
    category_id: int
    period: FeePeriod
    amount: Decimal
    due_day_of_month: int
    late_fee_per_day: Decimal
    grace_days: int
    notes: Optional[str]


class FeeStructureWrite(BaseModel):
    class_def_id: int
    category_id: int
    period: FeePeriod = FeePeriod.MONTHLY
    amount: Decimal = Field(default=Decimal("0"), ge=0)
    due_day_of_month: int = Field(default=10, ge=1, le=28)
    late_fee_per_day: Decimal = Field(default=Decimal("0"), ge=0)
    grace_days: int = Field(default=5, ge=0, le=60)
    notes: Optional[str] = None


class GenerateInvoicesRequest(BaseModel):
    period_start: date
    period_end: date
    sibling_discount_pct: Decimal = Field(default=Decimal("10"), ge=0, le=100)
    apply_sibling_discount: bool = True


class GenerateInvoicesResult(BaseModel):
    created: int
    skipped: int
    structure_id: int


# ---- Discounts -------------------------------------------------------------


class FeeDiscountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    student_id: int
    kind: DiscountKind
    percent: Optional[Decimal]
    amount: Optional[Decimal]
    reason: Optional[str]
    applies_from: Optional[date]
    applies_to: Optional[date]
    is_active: bool


class FeeDiscountWrite(BaseModel):
    student_id: int
    kind: DiscountKind = DiscountKind.MANUAL
    percent: Optional[Decimal] = Field(default=None, ge=0, le=100)
    amount: Optional[Decimal] = Field(default=None, ge=0)
    reason: Optional[str] = None
    applies_from: Optional[date] = None
    applies_to: Optional[date] = None


# ---- Invoices --------------------------------------------------------------


class FeePaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    invoice_id: int
    amount: Decimal
    method: PaymentMethod
    status: PaymentStatus
    reference: Optional[str]
    gateway_order_id: Optional[str]
    gateway_payment_id: Optional[str]
    paid_at: Optional[datetime]
    notes: Optional[str]


class FeeInvoiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    student_id: int
    structure_id: Optional[int]
    category_id: Optional[int]
    invoice_number: str
    period_start: date
    period_end: date
    due_date: date
    base_amount: Decimal
    discount_amount: Decimal
    late_fee_amount: Decimal
    total_amount: Decimal
    paid_amount: Decimal
    status: FeeInvoiceStatus
    notes: Optional[str]


class FeeInvoiceDetail(FeeInvoiceRead):
    payments: List[FeePaymentRead] = Field(default_factory=list)


class StudentFeeView(BaseModel):
    student_id: int
    full_name: str
    invoices: List[FeeInvoiceRead]
    total_due: Decimal
    total_paid: Decimal
    overdue_count: int


# ---- Cash collection --------------------------------------------------------


class CollectPaymentRequest(BaseModel):
    invoice_id: int
    amount: Decimal = Field(gt=0)
    method: PaymentMethod = PaymentMethod.CASH
    reference: Optional[str] = None
    notes: Optional[str] = None


# ---- Online payment (Razorpay-style stub) ----------------------------------


class InitiatePaymentRequest(BaseModel):
    invoice_id: int
    # gt=0 so a negative / zero payment can't create a bogus FeePayment.
    # The service still caps the upper bound at the remaining due.
    amount: Optional[Decimal] = Field(default=None, gt=0)


class InitiatePaymentResponse(BaseModel):
    order_id: str
    invoice_id: int
    amount_due: Decimal
    currency: str = "INR"
    razorpay_key: str = "rzp_test_stub"


class ConfirmPaymentRequest(BaseModel):
    order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


# ---- Reports ----------------------------------------------------------------


class DailyCollectionRow(BaseModel):
    date: date
    payments: int
    amount: Decimal


class DefaulterRow(BaseModel):
    student_id: int
    full_name: str
    admission_number: str
    invoices_overdue: int
    amount_overdue: Decimal


class CollectionSummary(BaseModel):
    start: date
    end: date
    total_collected: Decimal
    total_pending: Decimal
    overdue_amount: Decimal
    daily: List[DailyCollectionRow]
    by_method: dict[str, Decimal]
    by_category: dict[str, Decimal]


# ---- Receipt payload (PDF in Phase 16) -------------------------------------


class ReceiptPayload(BaseModel):
    payment_id: int
    invoice_number: str
    student_name: str
    school_name: str
    school_subdomain: str
    paid_at: Optional[datetime]
    amount: Decimal
    method: PaymentMethod
    reference: Optional[str]
    invoice_total: Decimal
    invoice_paid_total: Decimal
    invoice_balance: Decimal
