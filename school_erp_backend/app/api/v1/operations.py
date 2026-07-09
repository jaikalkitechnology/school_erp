"""Phase 28: operational modules — one router, 12 sub-groups.

Kept in one file so the CRUD boilerplate is easy to compare across
modules. Every endpoint is gated to senior staff via ``_staff`` and
takes tenant-scoped sessions. Payloads use plain dicts + Pydantic
where a real schema helps; most modules keep it dict-shaped to
avoid a hundred trivial schema classes.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import AuthPrincipal, require_roles
from app.core.tenant_session import tenant_scoped_session


_staff = require_roles(
    "school_admin", "super_admin", "principal", "vice_principal",
    "management", "hod", "coordinator", "office_admin", "office_staff",
    "accountant", "accounts", "payroll", "receptionist", "librarian",
    "class_teacher", "subject_teacher", "supervisor", "visitor_desk",
    "hostel_warden", "transport_manager",
)


router = APIRouter(prefix="/operations", tags=["operations"])


def _to_dict(obj: Any) -> dict:
    """SQLAlchemy row → JSON-safe dict."""
    out: dict = {}
    for c in obj.__table__.columns:
        v = getattr(obj, c.name)
        if isinstance(v, (date, datetime)):
            out[c.name] = v.isoformat()
        elif hasattr(v, "value") and not isinstance(v, (int, float, str, bool)):
            out[c.name] = v.value
        else:
            out[c.name] = v
    return out


def _coerce(col_type_name: str, v: Any) -> Any:
    """Convert JSON-friendly primitives to SQLAlchemy-friendly values.

    The frontend always sends dates/times as ISO strings and numbers
    as strings from form inputs. Silently coercing them here means
    every router doesn't have to.
    """
    if v is None or v == "":
        return None
    tn = col_type_name.upper()
    try:
        if tn.startswith("DATETIME"):
            if isinstance(v, datetime):
                return v
            return datetime.fromisoformat(str(v).replace("Z", "+00:00").replace(" ", "T"))
        if tn.startswith("DATE"):
            if isinstance(v, date):
                return v
            return date.fromisoformat(str(v)[:10])
        if tn.startswith("BOOL") or tn.startswith("TINYINT"):
            if isinstance(v, bool):
                return v
            return str(v).lower() in {"1", "true", "yes", "on"}
        if tn.startswith("NUMERIC") or tn.startswith("DECIMAL") or tn.startswith("FLOAT") or tn.startswith("REAL"):
            from decimal import Decimal
            return Decimal(str(v))
        if tn.startswith("INTEGER") or tn.startswith("BIGINT") or tn.startswith("SMALLINT"):
            return int(v) if str(v).strip() != "" else None
    except (ValueError, TypeError):
        return v
    return v


def _apply(obj: Any, payload: dict, allowed: set[str]) -> None:
    columns = {c.name: c for c in obj.__table__.columns}
    for k, v in (payload or {}).items():
        if k not in allowed:
            continue
        col = columns.get(k)
        if col is not None:
            v = _coerce(str(col.type), v)
        setattr(obj, k, v)


# ---------------------------------------------------------------------------
# 1. Admissions
# ---------------------------------------------------------------------------

_ADM_FIELDS = {
    "child_full_name", "child_dob", "class_applying_for", "parent_name",
    "parent_phone", "parent_email", "source", "stage", "notes",
    "test_date", "test_score",
}


@router.get("/admissions")
async def list_admissions(
    stage: Optional[str] = None,
    q: Optional[str] = None,
    session: AsyncSession = Depends(tenant_scoped_session),
    principal: AuthPrincipal = Depends(_staff),
):
    from app.models.operations import AdmissionInquiry

    stmt = select(AdmissionInquiry).order_by(AdmissionInquiry.id.desc())
    if stage:
        stmt = stmt.where(AdmissionInquiry.stage == stage)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(AdmissionInquiry.child_full_name.ilike(like))
    rows = (await session.execute(stmt.limit(500))).scalars().all()
    return [_to_dict(r) for r in rows]


@router.post("/admissions", status_code=status.HTTP_201_CREATED)
async def create_admission(
    payload: dict,
    session: AsyncSession = Depends(tenant_scoped_session),
    principal: AuthPrincipal = Depends(_staff),
):
    from app.models.operations import AdmissionInquiry

    obj = AdmissionInquiry(
        tenant_id=principal.tenant_id,
        handled_by_user_id=principal.user_id,
    )
    _apply(obj, payload, _ADM_FIELDS)
    if not obj.child_full_name:
        raise HTTPException(400, "child_full_name required")
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return _to_dict(obj)


@router.patch("/admissions/{row_id}")
async def update_admission(
    row_id: int, payload: dict,
    session: AsyncSession = Depends(tenant_scoped_session),
    principal: AuthPrincipal = Depends(_staff),
):
    from app.models.operations import AdmissionInquiry

    obj = await session.get(AdmissionInquiry, row_id)
    if obj is None:
        raise HTTPException(404, "Not found")
    _apply(obj, payload, _ADM_FIELDS)
    await session.commit()
    await session.refresh(obj)
    return _to_dict(obj)


@router.delete("/admissions/{row_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_admission(
    row_id: int,
    session: AsyncSession = Depends(tenant_scoped_session),
    principal: AuthPrincipal = Depends(_staff),
):
    from app.models.operations import AdmissionInquiry

    obj = await session.get(AdmissionInquiry, row_id)
    if obj is None:
        return
    await session.delete(obj)
    await session.commit()


@router.get("/admissions/stats")
async def admissions_stats(
    session: AsyncSession = Depends(tenant_scoped_session),
    principal: AuthPrincipal = Depends(_staff),
):
    from app.models.operations import AdmissionInquiry

    rows = (
        await session.execute(
            select(AdmissionInquiry.stage, func.count(AdmissionInquiry.id))
            .group_by(AdmissionInquiry.stage)
        )
    ).all()
    return {stage: count for stage, count in rows}


# ---------------------------------------------------------------------------
# 2. Finance — Vendors + Expenses
# ---------------------------------------------------------------------------

_VENDOR_FIELDS = {
    "name", "contact_person", "phone", "email", "gst_number", "address",
    "notes", "is_active",
}
_EXPENSE_FIELDS = {
    "category", "vendor_id", "amount", "spent_on", "paid_from",
    "invoice_ref", "description", "status",
}


def _simple_list_create_update_delete(prefix: str, Model, fields: set[str],
                                       list_extra_filter=None):
    """Register a batch of GET / POST / PATCH / DELETE endpoints for
    the given model. Cuts the router file in half."""

    @router.get(f"/{prefix}")
    async def _list(
        session: AsyncSession = Depends(tenant_scoped_session),
        principal: AuthPrincipal = Depends(_staff),
    ):
        rows = (
            await session.execute(select(Model).order_by(Model.id.desc()).limit(500))
        ).scalars().all()
        return [_to_dict(r) for r in rows]

    @router.post(f"/{prefix}", status_code=status.HTTP_201_CREATED)
    async def _create(
        payload: dict,
        session: AsyncSession = Depends(tenant_scoped_session),
        principal: AuthPrincipal = Depends(_staff),
    ):
        obj = Model(tenant_id=principal.tenant_id)
        _apply(obj, payload, fields)
        session.add(obj)
        await session.commit()
        await session.refresh(obj)
        return _to_dict(obj)

    @router.patch(f"/{prefix}/{{row_id}}")
    async def _update(
        row_id: int, payload: dict,
        session: AsyncSession = Depends(tenant_scoped_session),
        principal: AuthPrincipal = Depends(_staff),
    ):
        obj = await session.get(Model, row_id)
        if obj is None:
            raise HTTPException(404, "Not found")
        _apply(obj, payload, fields)
        await session.commit()
        await session.refresh(obj)
        return _to_dict(obj)

    @router.delete(f"/{prefix}/{{row_id}}", status_code=status.HTTP_204_NO_CONTENT)
    async def _delete(
        row_id: int,
        session: AsyncSession = Depends(tenant_scoped_session),
        principal: AuthPrincipal = Depends(_staff),
    ):
        obj = await session.get(Model, row_id)
        if obj is not None:
            await session.delete(obj)
            await session.commit()


# Register the simple-CRUD modules --------------------------------------
def _register_all():
    from app.models.operations import (
        Alumnus,
        CertificateTemplate,
        DisciplineIncident,
        Expense,
        HealthRecord,
        InventoryItem,
        Notice,
        SalaryStructure,
        SportsEvent,
        SportsHouse,
        Vendor,
        VisitorLog,
    )

    _simple_list_create_update_delete("vendors", Vendor, _VENDOR_FIELDS)
    _simple_list_create_update_delete(
        "expenses", Expense, _EXPENSE_FIELDS,
    )
    _simple_list_create_update_delete(
        "salary-structures",
        SalaryStructure,
        {
            "user_id", "basic", "hra", "allowances", "deductions",
            "effective_from", "notes",
        },
    )
    _simple_list_create_update_delete(
        "inventory-items",
        InventoryItem,
        {
            "code", "name", "category", "unit", "on_hand", "reorder_level",
            "unit_cost", "location", "notes",
        },
    )
    _simple_list_create_update_delete(
        "visitor-logs",
        VisitorLog,
        {
            "full_name", "phone", "company", "purpose", "host_user_id",
            "id_proof_type", "id_proof_ref", "badge_no", "photo_url",
            "checked_in_at", "checked_out_at", "notes",
        },
    )
    _simple_list_create_update_delete(
        "health-records",
        HealthRecord,
        {
            "student_id", "kind", "title", "description", "occurred_on",
            "severity", "treatment", "medication", "follow_up_on",
        },
    )
    _simple_list_create_update_delete(
        "certificate-templates",
        CertificateTemplate,
        {"code", "name", "body_html", "signatory_label", "is_active"},
    )
    _simple_list_create_update_delete(
        "discipline-incidents",
        DisciplineIncident,
        {
            "student_id", "occurred_on", "location", "severity", "headline",
            "description", "action_taken", "parent_informed",
        },
    )
    _simple_list_create_update_delete(
        "notices",
        Notice,
        {
            "title", "body", "audience", "is_pinned", "published_at",
            "expires_at", "attachments",
        },
    )
    _simple_list_create_update_delete(
        "alumni",
        Alumnus,
        {
            "student_id", "full_name", "graduation_year", "current_role",
            "current_company", "email", "phone", "city", "linkedin_url",
            "notes",
        },
    )
    _simple_list_create_update_delete(
        "sports-houses",
        SportsHouse,
        {"name", "color", "motto", "captain_student_id", "points"},
    )
    _simple_list_create_update_delete(
        "sports-events",
        SportsEvent,
        {
            "name", "kind", "sport", "starts_on", "ends_on", "venue",
            "winner_house_id", "notes",
        },
    )


_register_all()


# ---------------------------------------------------------------------------
# Specialised endpoints — beyond flat CRUD
# ---------------------------------------------------------------------------


# --- Inventory movement (auto-updates on_hand) ---------------------------


@router.post("/inventory-movements", status_code=status.HTTP_201_CREATED)
async def create_inventory_movement(
    payload: dict,
    session: AsyncSession = Depends(tenant_scoped_session),
    principal: AuthPrincipal = Depends(_staff),
):
    from app.models.operations import (
        InventoryItem, InventoryMovement, InventoryMovementKind,
    )

    item_id = int(payload.get("item_id") or 0)
    qty = int(payload.get("quantity") or 0)
    kind = str(payload.get("kind") or "in")
    if item_id <= 0 or qty <= 0:
        raise HTTPException(400, "item_id and quantity > 0 required")
    if kind not in {k.value for k in InventoryMovementKind}:
        raise HTTPException(400, "kind must be in / out / adjust")
    item = await session.get(InventoryItem, item_id)
    if item is None:
        raise HTTPException(404, "Item not found")

    signed = qty if kind == "in" else (-qty if kind == "out" else qty)
    if kind == "adjust":
        item.on_hand = qty
    else:
        item.on_hand = max(0, (item.on_hand or 0) + signed)

    mov = InventoryMovement(
        tenant_id=principal.tenant_id,
        item_id=item.id,
        kind=kind,
        quantity=abs(qty) if kind != "adjust" else qty,
        reference=payload.get("reference"),
        occurred_on=payload.get("occurred_on") or date.today().isoformat(),
        by_user_id=principal.user_id,
        notes=payload.get("notes"),
    )
    # Parse date if a string was sent.
    if isinstance(mov.occurred_on, str):
        mov.occurred_on = date.fromisoformat(mov.occurred_on)
    session.add(mov)
    await session.commit()
    await session.refresh(mov)
    await session.refresh(item)
    return {"movement": _to_dict(mov), "item": _to_dict(item)}


@router.get("/inventory-movements")
async def list_inventory_movements(
    item_id: Optional[int] = None,
    session: AsyncSession = Depends(tenant_scoped_session),
    principal: AuthPrincipal = Depends(_staff),
):
    from app.models.operations import InventoryMovement

    stmt = select(InventoryMovement).order_by(InventoryMovement.id.desc())
    if item_id:
        stmt = stmt.where(InventoryMovement.item_id == item_id)
    rows = (await session.execute(stmt.limit(500))).scalars().all()
    return [_to_dict(r) for r in rows]


# --- Visitor check-out ----------------------------------------------------


@router.post("/visitor-logs/{row_id}/checkout")
async def visitor_checkout(
    row_id: int,
    session: AsyncSession = Depends(tenant_scoped_session),
    principal: AuthPrincipal = Depends(_staff),
):
    from app.models.operations import VisitorLog

    v = await session.get(VisitorLog, row_id)
    if v is None:
        raise HTTPException(404, "Not found")
    v.checked_out_at = datetime.utcnow()
    await session.commit()
    await session.refresh(v)
    return _to_dict(v)


# --- Payslip generation from a salary structure --------------------------


@router.post("/payslips/generate", status_code=status.HTTP_201_CREATED)
async def generate_payslip(
    payload: dict,
    session: AsyncSession = Depends(tenant_scoped_session),
    principal: AuthPrincipal = Depends(_staff),
):
    """Payload: ``{"user_id": 12, "period": "2026-06"}``. Reads the
    latest ``SalaryStructure`` effective on the first of the period,
    computes the totals, writes a Payslip row."""
    from decimal import Decimal

    from app.models.operations import Payslip, SalaryStructure

    try:
        user_id = int(payload.get("user_id"))
    except (TypeError, ValueError):
        raise HTTPException(400, "user_id required")
    period = str(payload.get("period") or "")
    if len(period) != 7 or period[4] != "-":
        raise HTTPException(400, "period must be 'YYYY-MM'")

    exists = (
        await session.execute(
            select(Payslip).where(
                Payslip.user_id == user_id, Payslip.period == period,
            )
        )
    ).scalar_one_or_none()
    if exists is not None:
        raise HTTPException(400, "Payslip already exists for this period")

    struct = (
        await session.execute(
            select(SalaryStructure)
            .where(SalaryStructure.user_id == user_id)
            .order_by(SalaryStructure.effective_from.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if struct is None:
        raise HTTPException(404, "No salary structure on record for this user")

    def _sum_json(data):
        return sum(
            Decimal(str(v)) for v in (data or {}).values()
            if isinstance(v, (int, float, str))
        )

    other = _sum_json(struct.allowances)
    ded = _sum_json(struct.deductions)
    basic = Decimal(str(struct.basic or 0))
    hra = Decimal(str(struct.hra or 0))
    gross = basic + hra + other
    net = gross - ded
    slip = Payslip(
        tenant_id=principal.tenant_id,
        user_id=user_id,
        period=period,
        basic=basic,
        hra=hra,
        other_earnings=other,
        total_deductions=ded,
        net_pay=net,
        breakdown={
            "allowances": struct.allowances,
            "deductions": struct.deductions,
        },
        status="issued",
    )
    session.add(slip)
    await session.commit()
    await session.refresh(slip)
    return _to_dict(slip)


@router.get("/payslips")
async def list_payslips(
    user_id: Optional[int] = None,
    period: Optional[str] = None,
    session: AsyncSession = Depends(tenant_scoped_session),
    principal: AuthPrincipal = Depends(_staff),
):
    from app.models.operations import Payslip

    stmt = select(Payslip).order_by(Payslip.id.desc())
    if user_id:
        stmt = stmt.where(Payslip.user_id == user_id)
    if period:
        stmt = stmt.where(Payslip.period == period)
    rows = (await session.execute(stmt.limit(500))).scalars().all()
    return [_to_dict(r) for r in rows]


@router.post("/payslips/{row_id}/mark-paid")
async def payslip_mark_paid(
    row_id: int,
    session: AsyncSession = Depends(tenant_scoped_session),
    principal: AuthPrincipal = Depends(_staff),
):
    from app.models.operations import Payslip

    slip = await session.get(Payslip, row_id)
    if slip is None:
        raise HTTPException(404, "Not found")
    slip.status = "paid"
    slip.paid_on = date.today()
    await session.commit()
    await session.refresh(slip)
    return _to_dict(slip)


# --- Certificate issue (renders template) --------------------------------


@router.post("/certificates/issue", status_code=status.HTTP_201_CREATED)
async def issue_certificate(
    payload: dict,
    session: AsyncSession = Depends(tenant_scoped_session),
    principal: AuthPrincipal = Depends(_staff),
):
    """Payload: ``{"template_code": "bonafide", "student_id": 12,
    "for_name": "Aarav Sharma", "context": {...}}``. Renders the
    template's ``body_html`` with ``{{key}}`` substitution and writes
    the immutable rendered snapshot to ``issued_certificates``."""
    from app.models.operations import (
        CertificateTemplate, IssuedCertificate,
    )

    code = str(payload.get("template_code") or "").strip()
    for_name = str(payload.get("for_name") or "").strip()
    if not code or not for_name:
        raise HTTPException(400, "template_code + for_name required")
    tpl = (
        await session.execute(
            select(CertificateTemplate).where(CertificateTemplate.code == code)
        )
    ).scalar_one_or_none()
    if tpl is None or not tpl.is_active:
        raise HTTPException(404, "Template not found or inactive")

    context = payload.get("context") or {}
    body = tpl.body_html
    for k, v in context.items():
        body = body.replace("{{" + str(k) + "}}", "" if v is None else str(v))

    # Auto-number: LIB-YYYY-NNN style ref.
    year = date.today().year
    seq = (
        await session.execute(
            select(func.count(IssuedCertificate.id)).where(
                IssuedCertificate.template_code == code,
            )
        )
    ).scalar_one() + 1
    ref = f"{code.upper()}-{year}-{seq:04d}"

    obj = IssuedCertificate(
        tenant_id=principal.tenant_id,
        template_code=code,
        student_id=payload.get("student_id"),
        for_name=for_name,
        reference_no=ref,
        issued_on=date.today(),
        issued_by_user_id=principal.user_id,
        rendered_body=body,
        notes=payload.get("notes"),
    )
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return _to_dict(obj)


@router.get("/issued-certificates")
async def list_issued_certificates(
    student_id: Optional[int] = None,
    session: AsyncSession = Depends(tenant_scoped_session),
    principal: AuthPrincipal = Depends(_staff),
):
    from app.models.operations import IssuedCertificate

    stmt = select(IssuedCertificate).order_by(IssuedCertificate.id.desc())
    if student_id:
        stmt = stmt.where(IssuedCertificate.student_id == student_id)
    rows = (await session.execute(stmt.limit(500))).scalars().all()
    return [_to_dict(r) for r in rows]


# --- Finance dashboard ---------------------------------------------------


@router.get("/finance/summary")
async def finance_summary(
    session: AsyncSession = Depends(tenant_scoped_session),
    principal: AuthPrincipal = Depends(_staff),
):
    from app.models.operations import Expense
    from app.models.fees import FeePayment

    today = date.today()
    month_start = today.replace(day=1)

    exp_month = (
        await session.execute(
            select(func.coalesce(func.sum(Expense.amount), 0))
            .where(Expense.spent_on >= month_start)
        )
    ).scalar_one()
    exp_pending = (
        await session.execute(
            select(func.coalesce(func.sum(Expense.amount), 0))
            .where(Expense.status == "pending")
        )
    ).scalar_one()
    inc_month = (
        await session.execute(
            select(func.coalesce(func.sum(FeePayment.amount), 0))
            .where(func.date(FeePayment.paid_at) >= month_start)
        )
    ).scalar_one()

    return {
        "month": month_start.isoformat(),
        "income_month": float(inc_month or 0),
        "expenses_month": float(exp_month or 0),
        "expenses_pending": float(exp_pending or 0),
        "net_month": float((inc_month or 0) - (exp_month or 0)),
    }
