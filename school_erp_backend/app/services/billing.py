"""Subscription billing service (Phase 21)."""

from __future__ import annotations

import secrets
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.billing import (
    BillingInvoice,
    BillingInvoiceStatus,
    BillingPayment,
    BillingPaymentStatus,
    BillingRefund,
)
from app.models.tenant import (
    SubscriptionPlan,
    Tenant,
    TenantStatus,
)
from app.schemas.billing import (
    BillingPaymentCreate,
    BillingRefundCreate,
    BulkRenewRequest,
    GenerateInvoiceRequest,
    PlanChangeRequest,
)


def _D(v) -> Decimal:
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v or "0"))


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _add_months(d: date, months: int) -> date:
    m = d.month - 1 + months
    year = d.year + m // 12
    month = m % 12 + 1
    # Clamp day to month length.
    import calendar

    last = calendar.monthrange(year, month)[1]
    return date(year, month, min(d.day, last))


def _next_invoice_number() -> str:
    return f"INV-{date.today().strftime('%y%m')}-{secrets.token_hex(3).upper()}"


# ---- Invoice generation --------------------------------------------------


async def generate_invoice(
    session: AsyncSession,
    payload: GenerateInvoiceRequest,
) -> BillingInvoice:
    if payload.period_end < payload.period_start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="period_end must be on or after period_start",
        )
    tenant = (
        await session.execute(select(Tenant).where(Tenant.id == payload.tenant_id))
    ).scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    plan_id = payload.plan_id or tenant.plan_id
    plan = None
    if plan_id is not None:
        plan = (
            await session.execute(select(SubscriptionPlan).where(SubscriptionPlan.id == plan_id))
        ).scalar_one_or_none()
    if plan is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Plan not resolved")

    # Subtotal = monthly price prorated to the period (in months).
    days = (payload.period_end - payload.period_start).days + 1
    months = Decimal(str(days)) / Decimal("30")
    subtotal = (_D(plan.monthly_price) * months).quantize(Decimal("0.01"))
    discount = _D(payload.discount_amount)
    net = max(subtotal - discount, Decimal("0"))

    # GST split.
    gst_pct = _D(payload.gst_rate_pct)
    if payload.gst_treatment == "exempt":
        cgst = sgst = igst = tax = Decimal("0")
    elif payload.gst_treatment == "inter":
        igst = (net * gst_pct / Decimal("100")).quantize(Decimal("0.01"))
        cgst = sgst = Decimal("0")
        tax = igst
    else:  # intra
        half = (net * gst_pct / Decimal("200")).quantize(Decimal("0.01"))
        cgst = sgst = half
        igst = Decimal("0")
        tax = cgst + sgst

    total = net + tax
    today = date.today()
    invoice = BillingInvoice(
        tenant_id=tenant.id,
        plan_id=plan.id,
        invoice_number=_next_invoice_number(),
        period_start=payload.period_start,
        period_end=payload.period_end,
        issued_on=today,
        due_date=payload.due_date or (today + timedelta(days=14)),
        subtotal=subtotal,
        discount_amount=discount,
        tax_amount=tax,
        cgst_amount=cgst,
        sgst_amount=sgst,
        igst_amount=igst,
        total_amount=total,
        gst_treatment=payload.gst_treatment,
        place_of_supply=payload.place_of_supply,
        notes=payload.notes,
        status=BillingInvoiceStatus.PENDING.value,
    )
    session.add(invoice)
    await session.commit()
    await session.refresh(invoice)
    return invoice


async def list_invoices(
    session: AsyncSession,
    *,
    tenant_id: Optional[int] = None,
    status_filter: Optional[str] = None,
) -> list[BillingInvoice]:
    stmt = select(BillingInvoice)
    if tenant_id is not None:
        stmt = stmt.where(BillingInvoice.tenant_id == tenant_id)
    if status_filter:
        stmt = stmt.where(BillingInvoice.status == status_filter)
    return list((await session.execute(stmt.order_by(BillingInvoice.id.desc()))).scalars().all())


async def get_invoice(session: AsyncSession, invoice_id: int) -> BillingInvoice:
    obj = (
        await session.execute(
            select(BillingInvoice).where(BillingInvoice.id == invoice_id)
        )
    ).scalar_one_or_none()
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    return obj


async def void_invoice(session: AsyncSession, invoice_id: int) -> BillingInvoice:
    inv = await get_invoice(session, invoice_id)
    if inv.status == BillingInvoiceStatus.PAID.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot void a paid invoice; refund instead",
        )
    inv.status = BillingInvoiceStatus.VOID.value
    await session.commit()
    await session.refresh(inv)
    return inv


# ---- Auto-renew ----------------------------------------------------------


async def auto_renew(
    session: AsyncSession, payload: BulkRenewRequest
) -> dict:
    today = date.today()
    horizon = today + timedelta(days=payload.due_in_days)
    tenants = list(
        (
            await session.execute(
                select(Tenant).where(
                    Tenant.status == TenantStatus.ACTIVE.value,
                    Tenant.plan_id.is_not(None),
                    Tenant.subscription_end.is_not(None),
                    Tenant.subscription_end <= horizon,
                )
            )
        ).scalars().all()
    )
    generated_ids: list[int] = []
    skipped = 0
    for t in tenants:
        end_date = (
            t.subscription_end.date()
            if hasattr(t.subscription_end, "date") else t.subscription_end
        )
        period_start = end_date + timedelta(days=1)
        period_end = _add_months(period_start, payload.period_months) - timedelta(days=1)
        # Skip if there's already a non-void invoice covering this period.
        existing = (
            await session.execute(
                select(BillingInvoice).where(
                    BillingInvoice.tenant_id == t.id,
                    BillingInvoice.period_start == period_start,
                    BillingInvoice.status != BillingInvoiceStatus.VOID.value,
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            skipped += 1
            continue
        inv = await generate_invoice(
            session,
            GenerateInvoiceRequest(
                tenant_id=t.id,
                plan_id=t.plan_id,
                period_start=period_start,
                period_end=period_end,
                due_date=period_start + timedelta(days=payload.due_in_days),
                gst_rate_pct=payload.gst_rate_pct,
                gst_treatment="intra",
            ),
        )
        generated_ids.append(inv.id)
    return {"generated": len(generated_ids), "skipped": skipped, "invoice_ids": generated_ids}


# ---- Payments ------------------------------------------------------------


def _refresh_invoice_status(inv: BillingInvoice) -> None:
    paid = _D(inv.paid_amount)
    refunded = _D(inv.refunded_amount)
    total = _D(inv.total_amount)
    if refunded >= total and paid > 0:
        inv.status = BillingInvoiceStatus.REFUNDED.value
    elif paid >= total:
        inv.status = BillingInvoiceStatus.PAID.value
    elif paid > 0:
        inv.status = BillingInvoiceStatus.PARTIAL.value
    else:
        inv.status = BillingInvoiceStatus.PENDING.value


async def record_payment(
    session: AsyncSession,
    user_id: Optional[int],
    payload: BillingPaymentCreate,
) -> BillingPayment:
    inv = await get_invoice(session, payload.invoice_id)
    if inv.status == BillingInvoiceStatus.VOID.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invoice is void",
        )
    new_paid = _D(inv.paid_amount) + _D(payload.amount)
    if new_paid > _D(inv.total_amount):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment exceeds outstanding balance",
        )
    pay = BillingPayment(
        invoice_id=inv.id,
        amount=payload.amount,
        method=payload.method.value,
        status=BillingPaymentStatus.SUCCESS.value,
        reference=payload.reference,
        received_on=_now(),
        received_by_user_id=user_id,
        notes=payload.notes,
    )
    session.add(pay)
    inv.paid_amount = new_paid
    _refresh_invoice_status(inv)
    await session.commit()
    await session.refresh(pay)
    return pay


async def list_payments(session: AsyncSession, invoice_id: int) -> list[BillingPayment]:
    return list(
        (
            await session.execute(
                select(BillingPayment)
                .where(BillingPayment.invoice_id == invoice_id)
                .order_by(BillingPayment.id)
            )
        ).scalars().all()
    )


# ---- Refunds -------------------------------------------------------------


async def record_refund(
    session: AsyncSession,
    user_id: Optional[int],
    payload: BillingRefundCreate,
) -> BillingRefund:
    inv = await get_invoice(session, payload.invoice_id)
    if _D(payload.amount) > _D(inv.paid_amount) - _D(inv.refunded_amount):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refund exceeds net paid amount",
        )
    refund = BillingRefund(
        invoice_id=inv.id,
        amount=payload.amount,
        reason=payload.reason,
        refunded_on=_now(),
        refunded_by_user_id=user_id,
    )
    session.add(refund)
    inv.refunded_amount = _D(inv.refunded_amount) + _D(payload.amount)
    _refresh_invoice_status(inv)
    await session.commit()
    await session.refresh(refund)
    return refund


# ---- Plan upgrade / downgrade with proration -----------------------------


async def change_plan(
    session: AsyncSession,
    payload: PlanChangeRequest,
) -> dict:
    tenant = (
        await session.execute(select(Tenant).where(Tenant.id == payload.tenant_id))
    ).scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    new_plan = (
        await session.execute(
            select(SubscriptionPlan).where(SubscriptionPlan.id == payload.new_plan_id)
        )
    ).scalar_one_or_none()
    if new_plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    old_plan = None
    if tenant.plan_id:
        old_plan = (
            await session.execute(
                select(SubscriptionPlan).where(SubscriptionPlan.id == tenant.plan_id)
            )
        ).scalar_one_or_none()

    effective = payload.effective_on or date.today()
    days_remaining = 0
    pro_rated = Decimal("0")
    invoice_id: Optional[int] = None

    sub_end = (
        tenant.subscription_end.date()
        if tenant.subscription_end and hasattr(tenant.subscription_end, "date")
        else tenant.subscription_end
    )
    if (
        payload.pro_rate
        and sub_end is not None
        and sub_end >= effective
        and old_plan is not None
    ):
        days_remaining = (sub_end - effective).days + 1
        # Daily price = monthly / 30. Charge difference for remaining days.
        old_daily = _D(old_plan.monthly_price) / Decimal("30")
        new_daily = _D(new_plan.monthly_price) / Decimal("30")
        diff = (new_daily - old_daily) * Decimal(str(days_remaining))
        pro_rated = diff.quantize(Decimal("0.01"))
        if pro_rated > 0:
            inv = await generate_invoice(
                session,
                GenerateInvoiceRequest(
                    tenant_id=tenant.id,
                    plan_id=new_plan.id,
                    period_start=effective,
                    period_end=sub_end,
                    discount_amount=Decimal("0"),
                    gst_rate_pct=Decimal("18"),
                    gst_treatment="intra",
                    notes=f"Proration: upgrade from {old_plan.code} to {new_plan.code}",
                ),
            )
            # Override the auto-computed subtotal with the pro-rated diff.
            inv.subtotal = pro_rated
            half = (pro_rated * Decimal("18") / Decimal("200")).quantize(Decimal("0.01"))
            inv.cgst_amount = half
            inv.sgst_amount = half
            inv.tax_amount = half * 2
            inv.total_amount = pro_rated + half * 2
            await session.commit()
            await session.refresh(inv)
            invoice_id = inv.id

    tenant.plan_id = new_plan.id
    tenant.student_limit = new_plan.student_limit
    tenant.teacher_limit = new_plan.teacher_limit
    tenant.storage_limit_mb = new_plan.storage_gb * 1024
    tenant.modules_enabled = new_plan.modules_included
    await session.commit()

    return {
        "invoice_id": invoice_id,
        "pro_rated_charge": pro_rated if pro_rated > 0 else Decimal("0"),
        "days_remaining": days_remaining,
        "old_plan_id": old_plan.id if old_plan else None,
        "new_plan_id": new_plan.id,
    }


# ---- Reports -------------------------------------------------------------


async def reports(session: AsyncSession) -> dict:
    total_billed = (
        await session.execute(select(func.coalesce(func.sum(BillingInvoice.total_amount), 0)))
    ).scalar_one() or 0
    total_collected = (
        await session.execute(
            select(func.coalesce(func.sum(BillingInvoice.paid_amount), 0))
        )
    ).scalar_one() or 0
    refunded = (
        await session.execute(
            select(func.coalesce(func.sum(BillingInvoice.refunded_amount), 0))
        )
    ).scalar_one() or 0
    pending = (
        await session.execute(
            select(
                func.coalesce(
                    func.sum(BillingInvoice.total_amount - BillingInvoice.paid_amount), 0
                )
            ).where(
                BillingInvoice.status.in_(
                    [
                        BillingInvoiceStatus.PENDING.value,
                        BillingInvoiceStatus.PARTIAL.value,
                    ]
                )
            )
        )
    ).scalar_one() or 0
    today = date.today()
    overdue = (
        await session.execute(
            select(func.count(BillingInvoice.id)).where(
                BillingInvoice.due_date < today,
                BillingInvoice.status.in_(
                    [
                        BillingInvoiceStatus.PENDING.value,
                        BillingInvoiceStatus.PARTIAL.value,
                    ]
                ),
            )
        )
    ).scalar_one()

    # MRR: sum of monthly_price across active subscriptions on active tenants.
    mrr = (
        await session.execute(
            select(func.coalesce(func.sum(SubscriptionPlan.monthly_price), 0))
            .join(Tenant, Tenant.plan_id == SubscriptionPlan.id)
            .where(Tenant.status == TenantStatus.ACTIVE.value)
        )
    ).scalar_one() or 0
    arr = _D(mrr) * Decimal("12")

    return {
        "total_billed": _D(total_billed),
        "total_collected": _D(total_collected),
        "pending": _D(pending),
        "refunded": _D(refunded),
        "overdue_count": int(overdue),
        "mrr": _D(mrr),
        "arr": arr,
    }


# ---- Tenant view ---------------------------------------------------------


async def tenant_subscription(
    session: AsyncSession, tenant_id: int
) -> dict:
    tenant = (
        await session.execute(select(Tenant).where(Tenant.id == tenant_id))
    ).scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    plan = None
    if tenant.plan_id:
        plan = (
            await session.execute(
                select(SubscriptionPlan).where(SubscriptionPlan.id == tenant.plan_id)
            )
        ).scalar_one_or_none()
    invoices = list(
        (
            await session.execute(
                select(BillingInvoice)
                .where(BillingInvoice.tenant_id == tenant_id)
                .order_by(BillingInvoice.id.desc())
                .limit(12)
            )
        ).scalars().all()
    )
    return {
        "plan_id": tenant.plan_id,
        "plan_code": plan.code if plan else None,
        "plan_name": plan.name if plan else None,
        "monthly_price": _D(plan.monthly_price) if plan else None,
        "subscription_start": tenant.subscription_start,
        "subscription_end": tenant.subscription_end,
        "status": tenant.status,
        "invoices": invoices,
    }
