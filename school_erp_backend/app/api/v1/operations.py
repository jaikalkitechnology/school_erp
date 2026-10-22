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


@router.post("/_bootstrap-tables")
async def bootstrap_operations_tables(
    principal: AuthPrincipal = Depends(
        require_roles("school_admin", "super_admin", "principal"),
    ),
):
    """One-shot fallback: create every Phase 28 operations table if
    the Alembic migration hasn't been applied yet.

    Idempotent — uses ``checkfirst=True`` so tables that already
    exist are left alone. Safe to hit from a browser / curl by any
    school_admin. Returns the list of tables that got created (may
    be empty if everything is already in place)."""
    from sqlalchemy import inspect as sync_inspect

    from app.database import engine
    from app.models import operations as ops_module

    wanted = {
        "admission_inquiries", "vendors", "expenses",
        "salary_structures", "payslips", "inventory_items",
        "inventory_movements", "visitor_logs",
        "health_records", "certificate_templates",
        "issued_certificates", "discipline_incidents",
        "notices", "alumni", "sports_houses", "sports_events",
    }
    tables = [
        t for t in ops_module.TenantBase.metadata.tables.values()
        if t.name in wanted
    ]

    before: set[str] = set()
    async with engine.connect() as conn:
        def _get(sync_conn):
            return set(sync_inspect(sync_conn).get_table_names())
        before = await conn.run_sync(_get)

    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: ops_module.TenantBase.metadata.create_all(
                sync_conn, tables=tables, checkfirst=True,
            )
        )

    async with engine.connect() as conn:
        def _get(sync_conn):
            return set(sync_inspect(sync_conn).get_table_names())
        after = await conn.run_sync(_get)

    created = sorted(after - before)
    already = sorted(wanted & before)
    return {
        "created": created,
        "already_present": already,
        "missing_still": sorted(wanted - after),
    }


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


# ---- Validation catalogue -------------------------------------------------
# Enum-like string columns: value must be one of the set. Keyed by the
# column name (columns are plain String in the DB so we validate here).
_ENUM_FIELDS: dict[str, set[str]] = {
    "stage": {
        "enquiry", "applied", "tested", "offered", "confirmed",
        "converted", "rejected", "withdrawn",
    },
    "status": {
        # shared across expenses (pending/approved/paid/rejected) and
        # payslips (draft/issued/paid) — union is safe since neither
        # model reuses the other's values in a conflicting way.
        "pending", "approved", "paid", "rejected", "draft", "issued",
    },
    "audience": {"all", "staff", "parents", "students"},
    "severity": {"minor", "moderate", "major"},
    "kind": {
        # health-record kinds + inventory-movement kinds + sports-event
        # kinds. Union; each endpoint's own logic narrows further.
        "visit", "vaccination", "allergy", "note",
        "in", "out", "adjust",
        "tournament", "match", "practice", "annual_day", "club",
    },
}

# Numeric columns that must never be negative.
_NON_NEGATIVE_FIELDS: set[str] = {
    "amount", "basic", "hra", "other_earnings", "total_deductions",
    "net_pay", "unit_cost", "on_hand", "reorder_level", "points",
    "quantity", "test_score", "capacity", "graduation_year",
}


class _FieldError(Exception):
    """Raised by _coerce/_apply for a bad field value. The router turns
    it into a clean 400 naming the field."""

    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")


def _coerce(field: str, col_type_name: str, v: Any) -> Any:
    """Convert JSON-friendly primitives to SQLAlchemy-friendly values.

    Raises ``_FieldError`` (→ 400) on malformed input instead of
    silently returning garbage that would crash at commit time with an
    opaque 500. The frontend sends dates as ISO strings and numbers as
    strings from form inputs; we parse them strictly here."""
    if v is None or (isinstance(v, str) and v.strip() == ""):
        return None
    if field == "recipient_user_ids":
        if not isinstance(v, list) or not all(isinstance(x, int) and not isinstance(x, bool) for x in v):
            raise _FieldError(field, "must be a list of user ids")
        return sorted(set(v)) or None
    tn = col_type_name.upper()

    if tn.startswith("DATETIME"):
        if isinstance(v, datetime):
            return v
        try:
            return datetime.fromisoformat(
                str(v).replace("Z", "+00:00").replace(" ", "T")
            )
        except (ValueError, TypeError):
            raise _FieldError(field, "must be a valid date/time (YYYY-MM-DDTHH:MM)")
    if tn.startswith("DATE"):
        if isinstance(v, date):
            return v
        try:
            return date.fromisoformat(str(v)[:10])
        except (ValueError, TypeError):
            raise _FieldError(field, "must be a valid date (YYYY-MM-DD)")
    if tn.startswith("BOOL") or tn.startswith("TINYINT"):
        if isinstance(v, bool):
            return v
        return str(v).lower() in {"1", "true", "yes", "on"}
    if tn.startswith(("NUMERIC", "DECIMAL", "FLOAT", "REAL")):
        from decimal import Decimal, InvalidOperation
        try:
            return Decimal(str(v))
        except (InvalidOperation, ArithmeticError, ValueError, TypeError):
            raise _FieldError(field, "must be a number")
    if tn.startswith(("INTEGER", "BIGINT", "SMALLINT")):
        try:
            return int(str(v).strip())
        except (ValueError, TypeError):
            raise _FieldError(field, "must be a whole number")
    return v


def _apply(obj: Any, payload: dict, allowed: set[str]) -> None:
    """Assign whitelisted payload fields to the ORM object, coercing +
    validating each value. Raises ``_FieldError`` on any bad value; the
    router wraps that into a 400 with the field name."""
    columns = {c.name: c for c in obj.__table__.columns}
    for k, v in (payload or {}).items():
        if k not in allowed:
            continue
        col = columns.get(k)
        if col is not None:
            v = _coerce(k, str(col.type), v)
            # Length cap for VARCHAR columns — avoids a MySQL 1406
            # DataError 500 (or silent truncation under non-strict mode).
            length = getattr(col.type, "length", None)
            if length and isinstance(v, str) and len(v) > length:
                raise _FieldError(k, f"must be {length} characters or fewer")
            # Enum-like string membership.
            if v is not None and k in _ENUM_FIELDS and isinstance(v, str):
                if v not in _ENUM_FIELDS[k]:
                    allowed_vals = ", ".join(sorted(_ENUM_FIELDS[k]))
                    raise _FieldError(k, f"must be one of: {allowed_vals}")
            # Non-negative numbers.
            if v is not None and k in _NON_NEGATIVE_FIELDS:
                try:
                    if float(v) < 0:
                        raise _FieldError(k, "cannot be negative")
                except (ValueError, TypeError):
                    pass
        setattr(obj, k, v)


import re as _re

_FK_PATTERN = _re.compile(
    r"FOREIGN KEY \(`(?P<col>[^`]+)`\) REFERENCES `(?P<ref>[^`]+)`",
    _re.IGNORECASE,
)
_DUP_PATTERN = _re.compile(r"Duplicate entry '(?P<val>[^']+)' for key '(?P<key>[^']+)'")


async def _commit_with_fk_translation(session: AsyncSession) -> None:
    """Commit + translate MySQL FK / duplicate errors to a clean 400
    with the exact column at fault. Otherwise SQLAlchemy bubbles a
    500 and the user sees a stack-tracey error string that says
    nothing about which field to fix."""
    from sqlalchemy.exc import DataError, IntegrityError

    try:
        await session.commit()
    except DataError as exc:
        # MySQL 1406 (value too long), 1264 (out of range), 1366 (bad
        # value for a column). _apply guards most of these now, but this
        # is a belt-and-braces so a slip never becomes a 500.
        await session.rollback()
        msg = str(exc.orig) if getattr(exc, "orig", None) else str(exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "A value is too long or out of range for its field. "
                f"({msg[:150]})"
            ),
        )
    except IntegrityError as exc:
        await session.rollback()
        msg = str(exc.orig) if getattr(exc, "orig", None) else str(exc)

        # ---- MySQL 1452: FK constraint --------------------------------
        if "1452" in msg or "foreign key constraint fails" in msg.lower():
            m = _FK_PATTERN.search(msg)
            if m:
                col = m.group("col")
                ref = m.group("ref")
                detail = (
                    f"'{col}' must point to an existing row in {ref}. "
                    f"The value you entered doesn't match any {ref} row — "
                    f"either pick from the dropdown or leave it blank if "
                    f"the field is optional."
                )
            else:
                detail = (
                    "One of the referenced rows doesn't exist. Check that "
                    "every foreign-key field points to a row that's "
                    "already been created."
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=detail,
            )

        # ---- MySQL 1062: duplicate unique -----------------------------
        if "1062" in msg or "Duplicate entry" in msg:
            dup = _DUP_PATTERN.search(msg)
            if dup:
                val = dup.group("val")
                key = dup.group("key")
                detail = (
                    f"A row with '{val}' already exists (constraint '{key}'). "
                    f"Change the value or edit the existing row instead."
                )
            else:
                detail = "A row with that unique value already exists."
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=detail,
            )

        # ---- Everything else — surface first 200 chars ---------------
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Save failed: {msg[:200]}",
        )


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
    await _commit_with_fk_translation(session)
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
    await _commit_with_fk_translation(session)
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
    await _commit_with_fk_translation(session)


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
        await _commit_with_fk_translation(session)
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
        await _commit_with_fk_translation(session)
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
            await _commit_with_fk_translation(session)


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
            "expires_at", "attachments", "recipient_user_ids",
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


# --- Notice recipients (people picker for a notice's audience) -----------


@router.get("/notices/recipients")
async def notice_recipients(
    audience: str = Query(..., pattern="^(staff|parents|students)$"),
    session: AsyncSession = Depends(tenant_scoped_session),
    principal: AuthPrincipal = Depends(_staff),
):
    """People who can be picked as particular recipients of a notice:
    [{user_id, name, detail}]. Only people with an app login are listed,
    since a notice is read in the app."""
    from app.core.rbac_catalog import STAFF_ROLE_CODES
    from app.models.auth import Role, User, UserRole
    from app.models.parent import Parent, ParentChildMapping, Student

    def class_label(st: "Student") -> str:
        return st.current_class_label or ""

    out: list[dict] = []
    if audience == "students":
        # Logins with the student role (that's what the notice feed checks),
        # with class / admission number when linked to a student record.
        rows = (
            await session.execute(
                select(User.id, User.full_name, Student)
                .join(UserRole, UserRole.user_id == User.id)
                .join(Role, Role.id == UserRole.role_id)
                .outerjoin(Student, Student.user_id == User.id)
                .where(User.is_active.is_(True), Role.code == "student")
                .order_by(User.full_name)
            )
        ).all()
        seen: set[int] = set()
        for uid, name, st in rows:
            if uid in seen:
                continue
            seen.add(uid)
            bits = [class_label(st), f"Adm {st.admission_number}"] if st is not None else []
            out.append({
                "user_id": uid,
                "name": st.full_name if st is not None else name,
                "detail": " · ".join(b for b in bits if b),
            })
    elif audience == "parents":
        parents = (await session.execute(select(Parent).order_by(Parent.full_name))).scalars().all()
        kids: dict[int, list[str]] = {}
        maps = (
            await session.execute(
                select(ParentChildMapping.parent_id, Student.full_name, Student.current_class_label)
                .join(Student, Student.id == ParentChildMapping.student_id)
            )
        ).all()
        for pid, name, label in maps:
            kids.setdefault(pid, []).append(f"{name} ({label})" if label else name)
        for pa in parents:
            children = kids.get(pa.id, [])
            out.append({
                "user_id": pa.user_id,
                "name": pa.full_name,
                "detail": ("Parent of " + ", ".join(children)) if children else (pa.phone or ""),
            })
    else:
        rows = (
            await session.execute(
                select(User.id, User.full_name, Role.name, Role.code)
                .join(UserRole, UserRole.user_id == User.id)
                .join(Role, Role.id == UserRole.role_id)
                .where(User.is_active.is_(True), Role.code.in_(list(STAFF_ROLE_CODES)))
                .order_by(User.full_name)
            )
        ).all()
        by_user: dict[int, dict] = {}
        for uid, name, role_name, _code in rows:
            entry = by_user.setdefault(uid, {"user_id": uid, "name": name, "roles": []})
            entry["roles"].append(role_name)
        out = [
            {"user_id": e["user_id"], "name": e["name"], "detail": ", ".join(e["roles"])}
            for e in by_user.values()
        ]
    return out


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
    await _commit_with_fk_translation(session)
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
    await _commit_with_fk_translation(session)
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
    # Strict YYYY-MM: 4-digit year + valid month 01-12.
    m = _re.fullmatch(r"(\d{4})-(0[1-9]|1[0-2])", period)
    if not m:
        raise HTTPException(400, "period must be 'YYYY-MM' with a month between 01 and 12")

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
    await _commit_with_fk_translation(session)
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
    await _commit_with_fk_translation(session)
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

    # Auto-number: CODE-YYYY-NNNN style ref. reference_no is String(40),
    # so cap the code prefix — the "-YYYY-NNNN" suffix is 10 chars, and
    # for_name isn't part of the ref, so 28 chars of code leaves headroom.
    year = date.today().year
    seq = (
        await session.execute(
            select(func.count(IssuedCertificate.id)).where(
                IssuedCertificate.template_code == code,
            )
        )
    ).scalar_one() + 1
    code_prefix = code.upper()[:28]
    ref = f"{code_prefix}-{year}-{seq:04d}"

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
    await _commit_with_fk_translation(session)
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


# ---------------------------------------------------------------------------
# Staff-user options — powers the FK pickers on Salary / Payslip / Visitor.
# Gated to the broad operations staff set (not just school_admin), so a
# payroll / accounts user who can see the Salary page can also populate
# its "Staff member" dropdown.
# ---------------------------------------------------------------------------


@router.get("/_staff-options")
async def staff_options(
    q: Optional[str] = None,
    session: AsyncSession = Depends(tenant_scoped_session),
    principal: AuthPrincipal = Depends(_staff),
):
    """Every user account in the tenant (id + name + email + roles).
    Teachers appear here because onboarding a teacher creates a User
    row; salary structures / payslips FK on users.id, so this is the
    right source for the picker."""
    from app.models.auth import Role, User, UserRole

    stmt = (
        select(User)
        .where(User.is_active.is_(True))
        .order_by(User.full_name)
        .limit(1000)
    )
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            User.full_name.ilike(like) | User.email.ilike(like)
        )
    users = list((await session.execute(stmt)).scalars().all())

    # Bulk-load role codes per user in one query.
    roles_by_user: dict[int, list[str]] = {}
    if users:
        rows = (
            await session.execute(
                select(UserRole.user_id, Role.code)
                .join(Role, Role.id == UserRole.role_id)
                .where(UserRole.user_id.in_([u.id for u in users]))
            )
        ).all()
        for uid, code in rows:
            roles_by_user.setdefault(uid, []).append(code)

    return [
        {
            "id": u.id,
            "full_name": u.full_name,
            "email": u.email,
            "role_codes": roles_by_user.get(u.id, []),
        }
        for u in users
    ]
