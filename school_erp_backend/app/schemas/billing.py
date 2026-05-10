"""Subscription billing schemas (Phase 21)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.billing import (
    BillingInvoiceStatus,
    BillingPaymentMethod,
    BillingPaymentStatus,
)


# ---- Invoices -------------------------------------------------------------


class BillingInvoiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    tenant_id: int
    plan_id: Optional[int]
    invoice_number: str
    period_start: date
    period_end: date
    issued_on: date
    due_date: date
    subtotal: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    igst_amount: Decimal
    total_amount: Decimal
    paid_amount: Decimal
    refunded_amount: Decimal
    gst_treatment: str
    place_of_supply: Optional[str]
    notes: Optional[str]
    status: BillingInvoiceStatus


class GenerateInvoiceRequest(BaseModel):
    tenant_id: int
    plan_id: Optional[int] = None  # defaults to tenant's current plan
    period_start: date
    period_end: date
    due_date: Optional[date] = None
    discount_amount: Decimal = Field(default=Decimal("0"), ge=0)
    gst_rate_pct: Decimal = Field(default=Decimal("18"), ge=0, le=50)
    gst_treatment: str = "intra"  # intra | inter | exempt
    place_of_supply: Optional[str] = None
    notes: Optional[str] = None


class BulkRenewRequest(BaseModel):
    period_months: int = Field(default=1, ge=1, le=12)
    due_in_days: int = Field(default=14, ge=0, le=90)
    gst_rate_pct: Decimal = Field(default=Decimal("18"), ge=0, le=50)


class BulkRenewResult(BaseModel):
    generated: int
    skipped: int
    invoice_ids: List[int]


# ---- Payments + refunds --------------------------------------------------


class BillingPaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    invoice_id: int
    amount: Decimal
    method: BillingPaymentMethod
    status: BillingPaymentStatus
    reference: Optional[str]
    received_on: datetime
    notes: Optional[str]


class BillingPaymentCreate(BaseModel):
    invoice_id: int
    amount: Decimal = Field(gt=0)
    method: BillingPaymentMethod = BillingPaymentMethod.BANK_TRANSFER
    reference: Optional[str] = None
    notes: Optional[str] = None


class BillingRefundRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    invoice_id: int
    amount: Decimal
    reason: Optional[str]
    refunded_on: datetime


class BillingRefundCreate(BaseModel):
    invoice_id: int
    amount: Decimal = Field(gt=0)
    reason: Optional[str] = None


# ---- Plan changes --------------------------------------------------------


class PlanChangeRequest(BaseModel):
    tenant_id: int
    new_plan_id: int
    effective_on: Optional[date] = None
    pro_rate: bool = True


class PlanChangeResult(BaseModel):
    invoice_id: Optional[int]
    pro_rated_charge: Decimal
    days_remaining: int
    old_plan_id: Optional[int]
    new_plan_id: int


# ---- Reports -------------------------------------------------------------


class BillingReports(BaseModel):
    total_billed: Decimal
    total_collected: Decimal
    pending: Decimal
    refunded: Decimal
    overdue_count: int
    mrr: Decimal
    arr: Decimal


# ---- Tenant-side view ----------------------------------------------------


class SubscriptionStatus(BaseModel):
    plan_id: Optional[int]
    plan_code: Optional[str]
    plan_name: Optional[str]
    monthly_price: Optional[Decimal]
    subscription_start: Optional[datetime]
    subscription_end: Optional[datetime]
    status: str
    invoices: List[BillingInvoiceRead]
