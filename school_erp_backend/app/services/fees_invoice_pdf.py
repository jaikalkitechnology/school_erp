"""Render a fee invoice as a PDF on disk under the tenant's reports folder.

We deliberately render on demand rather than caching: invoice totals can shift
(late fees roll on, partial payments roll in), so a stale cached PDF is worse
than a fresh one. The cost is small — single-page document, no images.
"""

from __future__ import annotations

import io
import secrets
import uuid
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, status
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.file_storage import ensure_tenant_dirs
from app.models.academic import ClassDef, Section
from app.models.fees import (
    FeeCategory,
    FeeInvoice,
    FeeInvoiceStatus,
    FeePayment,
    PaymentStatus,
)
from app.models.parent import Student
from app.models.tenant import Tenant


def _money(v) -> str:
    return f"₹{Decimal(v or 0):,.2f}"


async def _build_invoice_snapshot(
    session: AsyncSession, *, tenant_id: int, invoice_id: int
) -> dict:
    invoice = (
        await session.execute(select(FeeInvoice).where(FeeInvoice.id == invoice_id))
    ).scalar_one_or_none()
    if invoice is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

    student = (
        await session.execute(select(Student).where(Student.id == invoice.student_id))
    ).scalar_one_or_none()
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

    category = (
        await session.execute(
            select(FeeCategory).where(FeeCategory.id == invoice.category_id)
        )
    ).scalar_one_or_none()

    section = None
    class_label = ""
    if student.section_id:
        section = (
            await session.execute(select(Section).where(Section.id == student.section_id))
        ).scalar_one_or_none()
        if section:
            cls = (
                await session.execute(
                    select(ClassDef).where(ClassDef.id == section.class_def_id)
                )
            ).scalar_one_or_none()
            class_label = cls.name if cls else ""

    tenant = (
        await session.execute(select(Tenant).where(Tenant.id == tenant_id))
    ).scalar_one_or_none()

    payments = list(
        (
            await session.execute(
                select(FeePayment)
                .where(
                    FeePayment.invoice_id == invoice.id,
                    FeePayment.status == PaymentStatus.SUCCESS.value,
                )
                .order_by(FeePayment.paid_at)
            )
        ).scalars().all()
    )

    return {
        "school": {
            "name": tenant.school_name if tenant else "School",
            "address": tenant.address if tenant else "",
        },
        "invoice": {
            "number": invoice.invoice_number,
            "category": category.name if category else "Fee",
            "period_start": invoice.period_start.isoformat(),
            "period_end": invoice.period_end.isoformat(),
            "due_date": invoice.due_date.isoformat(),
            "base": invoice.base_amount,
            "discount": invoice.discount_amount,
            "late_fee": invoice.late_fee_amount,
            "total": invoice.total_amount,
            "paid": invoice.paid_amount,
            "balance": max(
                Decimal(invoice.total_amount or 0) - Decimal(invoice.paid_amount or 0),
                Decimal("0"),
            ),
            "status": invoice.status,
            "is_paid": invoice.status == FeeInvoiceStatus.PAID.value,
        },
        "student": {
            "full_name": student.full_name,
            "admission_number": student.admission_number,
            "class_label": class_label,
            "section_name": section.name if section else "",
        },
        "payments": [
            {
                "paid_at": p.paid_at.strftime("%d %b %Y, %H:%M") if p.paid_at else "",
                "method": p.method,
                "amount": p.amount,
                "reference": p.reference or "",
            }
            for p in payments
        ],
    }


def _render_pdf(snapshot: dict, tenant_id: int) -> Path:
    ensure_tenant_dirs(tenant_id)
    base = Path(settings.UPLOAD_DIR) / f"tenant_{tenant_id}" / "fees" / "receipts"
    base.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{secrets.token_hex(2)}.pdf"
    target = base / filename

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm,
    )
    styles = getSampleStyleSheet()
    story: list = []

    school = snapshot["school"]
    story.append(Paragraph(f"<b>{school['name']}</b>", styles["Title"]))
    if school.get("address"):
        story.append(Paragraph(school["address"], styles["Normal"]))
    story.append(Spacer(1, 6))

    inv = snapshot["invoice"]
    title = "Receipt" if inv["is_paid"] else "Fee Invoice"
    story.append(Paragraph(f"<b>{title} — {inv['number']}</b>", styles["Heading2"]))
    story.append(Spacer(1, 6))

    student = snapshot["student"]
    student_table = Table(
        [
            ["Name", student["full_name"], "Adm. No.", student["admission_number"]],
            ["Class", student["class_label"], "Section", student["section_name"]],
        ],
        colWidths=[25 * mm, 65 * mm, 25 * mm, 55 * mm],
    )
    student_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#FFF7E6")),
        ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#FFF7E6")),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))
    story.append(student_table)
    story.append(Spacer(1, 10))

    detail_rows = [
        ["Category", inv["category"]],
        ["Period", f"{inv['period_start']} — {inv['period_end']}"],
        ["Due date", inv["due_date"]],
        ["Status", inv["status"].upper()],
    ]
    detail_table = Table(detail_rows, colWidths=[35 * mm, 135 * mm])
    detail_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#FFF7E6")),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))
    story.append(detail_table)
    story.append(Spacer(1, 10))

    money_rows = [
        ["Base amount", _money(inv["base"])],
        ["Discount", f"- {_money(inv['discount'])}"],
        ["Late fee", _money(inv["late_fee"])],
        ["Total", _money(inv["total"])],
        ["Paid", _money(inv["paid"])],
        ["Balance", _money(inv["balance"])],
    ]
    money_table = Table(money_rows, colWidths=[100 * mm, 70 * mm])
    money_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ("BACKGROUND", (0, 3), (-1, 3), colors.HexColor("#1F1248")),
        ("TEXTCOLOR", (0, 3), (-1, 3), colors.white),
        ("BACKGROUND", (0, 5), (-1, 5), colors.HexColor("#FFE4B8")),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
    ]))
    story.append(money_table)
    story.append(Spacer(1, 10))

    payments = snapshot.get("payments") or []
    if payments:
        story.append(Paragraph("<b>Payments</b>", styles["Heading4"]))
        rows = [["Date", "Method", "Reference", "Amount"]]
        for p in payments:
            rows.append([p["paid_at"], p["method"], p["reference"], _money(p["amount"])])
        ptable = Table(rows, colWidths=[40 * mm, 30 * mm, 60 * mm, 40 * mm])
        ptable.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F766E")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (-1, 0), (-1, -1), "RIGHT"),
        ]))
        story.append(ptable)

    story.append(Spacer(1, 20))
    story.append(Paragraph(
        f"<font size=8 color='#666666'>Generated {datetime.utcnow().strftime('%d %b %Y, %H:%M UTC')}</font>",
        styles["Normal"],
    ))

    doc.build(story)
    target.write_bytes(buf.getvalue())
    return target


async def render_invoice_pdf(
    session: AsyncSession, *, tenant_id: int, invoice_id: int
) -> tuple[Path, str]:
    snap = await _build_invoice_snapshot(
        session, tenant_id=tenant_id, invoice_id=invoice_id
    )
    path = _render_pdf(snap, tenant_id)
    invoice_number = snap["invoice"]["number"]
    return path, invoice_number
