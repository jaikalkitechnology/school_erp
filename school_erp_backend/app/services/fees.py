"""Fee management service (Phase 11)."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models.fees import (
    DiscountKind,
    FeeCategory,
    FeeDiscount,
    FeeInvoice,
    FeeInvoiceStatus,
    FeePayment,
    FeeStructure,
    PaymentMethod,
    PaymentStatus,
)
from app.models.parent import Student
from app.schemas.fees import (
    CollectPaymentRequest,
    CollectionSummary,
    ConfirmPaymentRequest,
    DailyCollectionRow,
    DefaulterRow,
    FeeCategoryWrite,
    FeeDiscountWrite,
    FeeStructureWrite,
    GenerateInvoicesRequest,
    GenerateInvoicesResult,
    InitiatePaymentRequest,
    InitiatePaymentResponse,
    ReceiptPayload,
    StudentFeeView,
)


def _today() -> date:
    return datetime.now(timezone.utc).date()


def _D(value) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value or "0"))


def _refresh_invoice_status(invoice: FeeInvoice) -> None:
    paid = _D(invoice.paid_amount)
    total = _D(invoice.total_amount)
    if invoice.status == FeeInvoiceStatus.WAIVED.value:
        return
    if paid >= total and total > 0:
        invoice.status = FeeInvoiceStatus.PAID.value
    elif paid > 0:
        invoice.status = FeeInvoiceStatus.PARTIAL.value
    elif invoice.due_date < _today():
        invoice.status = FeeInvoiceStatus.OVERDUE.value
    else:
        invoice.status = FeeInvoiceStatus.PENDING.value


def _next_invoice_number(tenant_id: int) -> str:
    yy = _today().strftime("%y")
    rand = secrets.token_hex(3).upper()
    return f"INV-{yy}-{rand}"


# ---- Categories ------------------------------------------------------------


async def list_categories(session: AsyncSession) -> list[FeeCategory]:
    return list(
        (await session.execute(select(FeeCategory).order_by(FeeCategory.code))).scalars().all()
    )


async def create_category(
    session: AsyncSession, tenant_id: int, payload: FeeCategoryWrite
) -> FeeCategory:
    from sqlalchemy.exc import IntegrityError

    # Pre-flight uniqueness check so we return a specific 409 instead of
    # letting the IntegrityError bubble up later.
    existing = (
        await session.execute(
            select(FeeCategory).where(
                FeeCategory.tenant_id == tenant_id,
                FeeCategory.code == payload.code,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Category code '{payload.code}' already exists in this school",
        )

    obj = FeeCategory(tenant_id=tenant_id, **payload.model_dump())
    session.add(obj)
    try:
        await session.commit()
    except IntegrityError as e:
        await session.rollback()
        # Race with another concurrent create.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Category code already exists ({getattr(e, 'orig', e)})",
        )
    await session.refresh(obj)
    return obj


async def update_category(
    session: AsyncSession, category_id: int, payload: FeeCategoryWrite
) -> FeeCategory:
    obj = (
        await session.execute(select(FeeCategory).where(FeeCategory.id == category_id))
    ).scalar_one_or_none()
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await session.commit()
    await session.refresh(obj)
    return obj


# ---- Structures ------------------------------------------------------------


async def list_structures(
    session: AsyncSession, *, class_def_id: Optional[int] = None
) -> list[FeeStructure]:
    stmt = select(FeeStructure).order_by(FeeStructure.class_def_id, FeeStructure.category_id)
    if class_def_id is not None:
        stmt = stmt.where(FeeStructure.class_def_id == class_def_id)
    return list((await session.execute(stmt)).scalars().all())


async def create_structure(
    session: AsyncSession, tenant_id: int, payload: FeeStructureWrite
) -> FeeStructure:
    from sqlalchemy.exc import IntegrityError

    from app.models.academic import ClassDef

    # Validate referenced FKs so we return precise 404/400 instead of an
    # opaque "already exists" when the real cause is a missing class /
    # category.
    cls = (
        await session.execute(
            select(ClassDef).where(
                ClassDef.id == payload.class_def_id,
                ClassDef.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()
    if cls is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Class #{payload.class_def_id} not found in this school",
        )
    cat = (
        await session.execute(
            select(FeeCategory).where(
                FeeCategory.id == payload.category_id,
                FeeCategory.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()
    if cat is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fee category #{payload.category_id} not found",
        )

    # Same race-safe uniqueness check as create_category.
    existing = (
        await session.execute(
            select(FeeStructure).where(
                FeeStructure.tenant_id == tenant_id,
                FeeStructure.class_def_id == payload.class_def_id,
                FeeStructure.category_id == payload.category_id,
                FeeStructure.period == payload.period.value,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"A {payload.period.value} structure for "
                f"'{cat.name}' in '{cls.name}' already exists. "
                "Edit the existing one instead."
            ),
        )

    obj = FeeStructure(tenant_id=tenant_id, **payload.model_dump())
    session.add(obj)
    try:
        await session.commit()
    except IntegrityError as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not save structure: {getattr(e, 'orig', e)}",
        )
    await session.refresh(obj)
    return obj


async def update_structure(
    session: AsyncSession, structure_id: int, payload: FeeStructureWrite
) -> FeeStructure:
    obj = (
        await session.execute(select(FeeStructure).where(FeeStructure.id == structure_id))
    ).scalar_one_or_none()
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Structure not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await session.commit()
    await session.refresh(obj)
    return obj


# ---- Sibling discount math + invoice generation ----------------------------


def _structure_due_date(structure: FeeStructure, period_start: date) -> date:
    day = min(structure.due_day_of_month or 10, 28)
    return date(period_start.year, period_start.month, day)


async def _sibling_count_in_tenant(session: AsyncSession, student: Student) -> int:
    if student.sibling_group_id is None:
        return 0
    count = int(
        (
            await session.execute(
                select(func.count(Student.id)).where(
                    Student.sibling_group_id == student.sibling_group_id,
                    Student.is_active.is_(True),
                )
            )
        ).scalar_one()
    )
    return max(0, count - 1)


async def _resolve_explicit_discount(
    session: AsyncSession, student_id: int, on_date: date, base_amount: Decimal
) -> Decimal:
    """Pick the highest active explicit discount for a student on the given date."""
    rows = list(
        (
            await session.execute(
                select(FeeDiscount).where(
                    FeeDiscount.student_id == student_id,
                    FeeDiscount.is_active.is_(True),
                )
            )
        ).scalars().all()
    )
    best = Decimal("0")
    for d in rows:
        if d.applies_from and on_date < d.applies_from:
            continue
        if d.applies_to and on_date > d.applies_to:
            continue
        if d.amount is not None:
            best = max(best, _D(d.amount))
        elif d.percent is not None:
            best = max(best, base_amount * _D(d.percent) / Decimal("100"))
    return best


async def generate_invoices(
    session: AsyncSession,
    tenant_id: int,
    structure_id: int,
    payload: GenerateInvoicesRequest,
) -> GenerateInvoicesResult:
    structure = (
        await session.execute(select(FeeStructure).where(FeeStructure.id == structure_id))
    ).scalar_one_or_none()
    if structure is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Structure not found")
    if payload.period_end < payload.period_start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="period_end must be on or after period_start",
        )

    students = list(
        (
            await session.execute(
                select(Student).where(
                    Student.class_def_id == structure.class_def_id,
                    Student.is_active.is_(True),
                )
            )
        ).scalars().all()
    )

    base_amount = _D(structure.amount)
    due_date = _structure_due_date(structure, payload.period_start)
    created = 0
    skipped = 0
    for student in students:
        existing = (
            await session.execute(
                select(FeeInvoice).where(
                    FeeInvoice.student_id == student.id,
                    FeeInvoice.structure_id == structure.id,
                    FeeInvoice.period_start == payload.period_start,
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            skipped += 1
            continue

        explicit_discount = await _resolve_explicit_discount(
            session, student.id, payload.period_start, base_amount
        )
        sibling_discount = Decimal("0")
        if payload.apply_sibling_discount:
            sibling_count = await _sibling_count_in_tenant(session, student)
            if sibling_count >= 1:
                sibling_discount = base_amount * _D(payload.sibling_discount_pct) / Decimal("100")

        discount = (explicit_discount + sibling_discount).quantize(Decimal("0.01"))
        if discount > base_amount:
            discount = base_amount
        total = (base_amount - discount).quantize(Decimal("0.01"))

        invoice = FeeInvoice(
            tenant_id=tenant_id,
            student_id=student.id,
            structure_id=structure.id,
            category_id=structure.category_id,
            invoice_number=_next_invoice_number(tenant_id),
            period_start=payload.period_start,
            period_end=payload.period_end,
            due_date=due_date,
            base_amount=base_amount,
            discount_amount=discount,
            late_fee_amount=Decimal("0"),
            total_amount=total,
            paid_amount=Decimal("0"),
            status=FeeInvoiceStatus.PENDING.value,
        )
        session.add(invoice)
        created += 1
    await session.commit()
    return GenerateInvoicesResult(created=created, skipped=skipped, structure_id=structure.id)


# ---- Discount CRUD ---------------------------------------------------------


async def upsert_discount(
    session: AsyncSession, tenant_id: int, payload: FeeDiscountWrite
) -> FeeDiscount:
    if payload.percent is None and payload.amount is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either percent or amount is required",
        )
    obj = FeeDiscount(tenant_id=tenant_id, **payload.model_dump(), is_active=True)
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return obj


async def deactivate_discount(session: AsyncSession, discount_id: int) -> None:
    obj = (
        await session.execute(select(FeeDiscount).where(FeeDiscount.id == discount_id))
    ).scalar_one_or_none()
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discount not found")
    obj.is_active = False
    await session.commit()


# ---- Invoices + payments ---------------------------------------------------


async def list_student_fees(
    session: AsyncSession, student_id: int
) -> StudentFeeView:
    student = (
        await session.execute(select(Student).where(Student.id == student_id))
    ).scalar_one_or_none()
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    invoices = list(
        (
            await session.execute(
                select(FeeInvoice)
                .where(FeeInvoice.student_id == student_id)
                .order_by(FeeInvoice.due_date.desc())
            )
        ).scalars().all()
    )
    today = _today()
    total_due = Decimal("0")
    total_paid = Decimal("0")
    overdue_count = 0
    for inv in invoices:
        # Refresh status lazily so listings always show the correct overdue state.
        # Precedence: PAID > PARTIAL > OVERDUE > PENDING (a payment in flight
        # overrides the "overdue" label).
        if inv.status not in {
            FeeInvoiceStatus.PAID.value,
            FeeInvoiceStatus.WAIVED.value,
            FeeInvoiceStatus.CANCELLED.value,
        }:
            paid = _D(inv.paid_amount)
            total = _D(inv.total_amount)
            if paid >= total and total > 0:
                inv.status = FeeInvoiceStatus.PAID.value
            elif paid > 0:
                inv.status = FeeInvoiceStatus.PARTIAL.value
            elif inv.due_date < today:
                inv.status = FeeInvoiceStatus.OVERDUE.value
            else:
                inv.status = FeeInvoiceStatus.PENDING.value
        total_due += max(_D(inv.total_amount) - _D(inv.paid_amount), Decimal("0"))
        total_paid += _D(inv.paid_amount)
        if inv.status == FeeInvoiceStatus.OVERDUE.value:
            overdue_count += 1
    if invoices:
        await session.commit()
    return StudentFeeView(
        student_id=student.id,
        full_name=student.full_name,
        invoices=invoices,
        total_due=total_due,
        total_paid=total_paid,
        overdue_count=overdue_count,
    )


async def collect_payment(
    session: AsyncSession,
    tenant_id: int,
    user_id: int,
    payload: CollectPaymentRequest,
) -> FeePayment:
    invoice = (
        await session.execute(select(FeeInvoice).where(FeeInvoice.id == payload.invoice_id))
    ).scalar_one_or_none()
    if invoice is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    if invoice.status in {FeeInvoiceStatus.WAIVED.value, FeeInvoiceStatus.CANCELLED.value}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invoice is {invoice.status}; cannot collect",
        )
    remaining = _D(invoice.total_amount) - _D(invoice.paid_amount)
    if payload.amount > remaining:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Amount exceeds remaining due ({remaining})",
        )

    payment = FeePayment(
        tenant_id=tenant_id,
        invoice_id=invoice.id,
        amount=payload.amount,
        method=payload.method.value,
        status=PaymentStatus.SUCCESS.value,
        reference=payload.reference,
        paid_at=datetime.now(timezone.utc).replace(tzinfo=None),
        received_by_user_id=user_id,
        notes=payload.notes,
    )
    session.add(payment)
    invoice.paid_amount = _D(invoice.paid_amount) + payload.amount
    _refresh_invoice_status(invoice)
    await session.commit()
    await session.refresh(payment)
    return payment


# ---- Online payment stub (Razorpay-style) ---------------------------------


def _gateway_secret() -> str:
    return settings.RAZORPAY_KEY_SECRET or "phase11-stub-secret"


def _signature(order_id: str, payment_id: str) -> str:
    return hmac.new(
        _gateway_secret().encode(),
        f"{order_id}|{payment_id}".encode(),
        hashlib.sha256,
    ).hexdigest()


async def initiate_online_payment(
    session: AsyncSession,
    tenant_id: int,
    user_id: int,
    payload: InitiatePaymentRequest,
) -> InitiatePaymentResponse:
    invoice = (
        await session.execute(select(FeeInvoice).where(FeeInvoice.id == payload.invoice_id))
    ).scalar_one_or_none()
    if invoice is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    remaining = _D(invoice.total_amount) - _D(invoice.paid_amount)
    if remaining <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invoice already settled",
        )
    amount = _D(payload.amount) if payload.amount is not None else remaining
    if amount > remaining:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Amount exceeds remaining due ({remaining})",
        )
    order_id = "order_" + secrets.token_hex(8)
    pending = FeePayment(
        tenant_id=tenant_id,
        invoice_id=invoice.id,
        amount=amount,
        method=PaymentMethod.UPI.value,
        status=PaymentStatus.INITIATED.value,
        gateway_order_id=order_id,
        received_by_user_id=user_id,
    )
    session.add(pending)
    await session.commit()
    return InitiatePaymentResponse(
        order_id=order_id,
        invoice_id=invoice.id,
        amount_due=amount,
    )


async def confirm_online_payment(
    session: AsyncSession, payload: ConfirmPaymentRequest
) -> FeePayment:
    expected = _signature(payload.order_id, payload.razorpay_payment_id)
    if not hmac.compare_digest(expected, payload.razorpay_signature):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payment signature",
        )
    payment = (
        await session.execute(
            select(FeePayment).where(FeePayment.gateway_order_id == payload.order_id)
        )
    ).scalar_one_or_none()
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if payment.status == PaymentStatus.SUCCESS.value:
        return payment

    invoice = (
        await session.execute(select(FeeInvoice).where(FeeInvoice.id == payment.invoice_id))
    ).scalar_one()

    payment.status = PaymentStatus.SUCCESS.value
    payment.gateway_payment_id = payload.razorpay_payment_id
    payment.paid_at = datetime.now(timezone.utc).replace(tzinfo=None)
    invoice.paid_amount = _D(invoice.paid_amount) + _D(payment.amount)
    _refresh_invoice_status(invoice)
    await session.commit()
    await session.refresh(payment)
    return payment


# ---- Receipts --------------------------------------------------------------


async def receipt_payload(
    session: AsyncSession,
    *,
    school_name: str,
    school_subdomain: str,
    payment_id: int,
) -> ReceiptPayload:
    payment = (
        await session.execute(select(FeePayment).where(FeePayment.id == payment_id))
    ).scalar_one_or_none()
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    invoice = (
        await session.execute(select(FeeInvoice).where(FeeInvoice.id == payment.invoice_id))
    ).scalar_one()
    student = (
        await session.execute(select(Student).where(Student.id == invoice.student_id))
    ).scalar_one()
    return ReceiptPayload(
        payment_id=payment.id,
        invoice_number=invoice.invoice_number,
        student_name=student.full_name,
        school_name=school_name,
        school_subdomain=school_subdomain,
        paid_at=payment.paid_at,
        amount=_D(payment.amount),
        method=PaymentMethod(payment.method),
        reference=payment.reference,
        invoice_total=_D(invoice.total_amount),
        invoice_paid_total=_D(invoice.paid_amount),
        invoice_balance=max(_D(invoice.total_amount) - _D(invoice.paid_amount), Decimal("0")),
    )


# ---- Reports ----------------------------------------------------------------


async def collection_summary(
    session: AsyncSession,
    *,
    start: date,
    end: date,
) -> CollectionSummary:
    payments = list(
        (
            await session.execute(
                select(FeePayment).where(
                    FeePayment.status == PaymentStatus.SUCCESS.value,
                    FeePayment.paid_at >= datetime.combine(start, datetime.min.time()),
                    FeePayment.paid_at <= datetime.combine(end, datetime.max.time()),
                )
            )
        ).scalars().all()
    )
    by_day: dict[date, dict[str, Decimal]] = {}
    by_method: dict[str, Decimal] = {}
    for p in payments:
        d = p.paid_at.date() if p.paid_at else start
        bucket = by_day.setdefault(d, {"count": Decimal("0"), "amount": Decimal("0")})
        bucket["count"] += Decimal("1")
        bucket["amount"] += _D(p.amount)
        by_method[p.method] = by_method.get(p.method, Decimal("0")) + _D(p.amount)
    daily = [
        DailyCollectionRow(date=d, payments=int(v["count"]), amount=v["amount"])
        for d, v in sorted(by_day.items())
    ]

    # Pending + overdue across all tenants - already filtered by tenant_scoped session.
    invoices = list(
        (
            await session.execute(
                select(FeeInvoice).options(selectinload(FeeInvoice.payments))
            )
        ).scalars().all()
    )
    today = _today()
    total_pending = Decimal("0")
    overdue = Decimal("0")
    by_category: dict[str, Decimal] = {}
    for inv in invoices:
        balance = max(_D(inv.total_amount) - _D(inv.paid_amount), Decimal("0"))
        if balance > 0:
            total_pending += balance
            if inv.due_date < today and inv.status not in {FeeInvoiceStatus.PAID.value, FeeInvoiceStatus.WAIVED.value}:
                overdue += balance
        # Category breakdown of collected amounts in window.
        if inv.category_id:
            cat_paid = Decimal("0")
            for p in inv.payments:
                if p.status == PaymentStatus.SUCCESS.value and p.paid_at:
                    if start <= p.paid_at.date() <= end:
                        cat_paid += _D(p.amount)
            if cat_paid > 0:
                key = str(inv.category_id)
                by_category[key] = by_category.get(key, Decimal("0")) + cat_paid

    return CollectionSummary(
        start=start,
        end=end,
        total_collected=sum((_D(p.amount) for p in payments), Decimal("0")),
        total_pending=total_pending,
        overdue_amount=overdue,
        daily=daily,
        by_method={k: v for k, v in by_method.items()},
        by_category=by_category,
    )


async def defaulters(session: AsyncSession) -> list[DefaulterRow]:
    today = _today()
    rows = list(
        (
            await session.execute(
                select(FeeInvoice, Student)
                .join(Student, Student.id == FeeInvoice.student_id)
                .where(FeeInvoice.due_date < today)
                .where(FeeInvoice.status != FeeInvoiceStatus.PAID.value)
                .where(FeeInvoice.status != FeeInvoiceStatus.WAIVED.value)
            )
        ).all()
    )
    bucket: dict[int, dict] = {}
    for inv, student in rows:
        balance = max(_D(inv.total_amount) - _D(inv.paid_amount), Decimal("0"))
        if balance <= 0:
            continue
        b = bucket.setdefault(student.id, {"name": student.full_name, "adm": student.admission_number, "count": 0, "amount": Decimal("0")})
        b["count"] += 1
        b["amount"] += balance
    return [
        DefaulterRow(
            student_id=sid,
            full_name=v["name"],
            admission_number=v["adm"],
            invoices_overdue=v["count"],
            amount_overdue=v["amount"],
        )
        for sid, v in sorted(bucket.items(), key=lambda kv: -kv[1]["amount"])
    ]


# ---- Parent dashboard helper -----------------------------------------------


async def fee_due_for_student(session: AsyncSession, student_id: int) -> Decimal:
    rows = list(
        (
            await session.execute(
                select(FeeInvoice.total_amount, FeeInvoice.paid_amount).where(
                    FeeInvoice.student_id == student_id,
                    FeeInvoice.status != FeeInvoiceStatus.PAID.value,
                    FeeInvoice.status != FeeInvoiceStatus.WAIVED.value,
                    FeeInvoice.status != FeeInvoiceStatus.CANCELLED.value,
                )
            )
        ).all()
    )
    return sum((max(_D(t) - _D(p), Decimal("0")) for (t, p) in rows), Decimal("0"))
