"""Principal-side aggregation endpoints.

A single thin router that powers the Principal mobile app. We don't
duplicate business logic here — leaves still decide through the
existing services, fee lists still come from fees.py, etc. This module
just stitches the data the principal needs to glance at into compact
JSON payloads so the app doesn't fan out 12 requests per screen.

Every endpoint is gated on the senior-staff roles:
  principal, vice_principal, school_admin
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import AuthPrincipal, require_roles
from app.core.tenant_session import tenant_scoped_session


_senior = require_roles("principal", "vice_principal", "school_admin")


router = APIRouter(
    prefix="/principal",
    tags=["principal"],
    dependencies=[Depends(_senior)],
)


# ---------------------------------------------------------------------------
# 1.  Dashboard summary
# ---------------------------------------------------------------------------


@router.get("/dashboard")
async def dashboard_summary(
    session: AsyncSession = Depends(tenant_scoped_session),
):
    """One-shot home screen payload.

    Counts that drive the Today widgets:
      - attendance: students_present / students_marked / total_students
      - staff:      total_staff, staff_on_leave_today
      - fees:       collected_today, collected_mtd, outstanding_total
      - transport:  trips_in_progress
      - approvals:  pending counts split by kind
      - alerts:     overdue_invoices_count, behaviour_concerns_today
    """
    from app.models.attendance import StudentAttendance, StudentAttendanceStatus
    from app.models.auth import Role, User, UserRole
    from app.models.fees import FeeInvoice, FeeInvoiceStatus, FeePayment
    from app.models.parent import LeaveApplication, LeaveStatus, Student
    from app.models.staff_extras import (
        BehaviourNote, BehaviourNoteKind,
        StaffLeave, StaffLeaveStatus,
    )
    from app.models.transport import Trip, TripPhase

    today = date.today()
    first_of_month = today.replace(day=1)

    # --- students roster ----
    total_students = (
        await session.execute(
            select(func.count(Student.id)).where(Student.is_active.is_(True))
        )
    ).scalar_one()

    # --- attendance today ----
    att_q = await session.execute(
        select(
            StudentAttendance.status,
            func.count(StudentAttendance.id),
        )
        .where(StudentAttendance.date == today)
        .group_by(StudentAttendance.status)
    )
    att_by_status = {row[0]: int(row[1]) for row in att_q.all()}
    marked = sum(att_by_status.values())
    present = (
        att_by_status.get(StudentAttendanceStatus.PRESENT.value, 0)
        + att_by_status.get(StudentAttendanceStatus.LATE.value, 0)
        + att_by_status.get(StudentAttendanceStatus.HALF_DAY.value, 0)
    )

    # --- staff size + on-leave today ----
    staff_role_codes = (
        "principal", "vice_principal", "coordinator",
        "class_teacher", "subject_teacher", "accountant",
        "librarian", "transport_manager", "school_admin",
    )
    total_staff_q = await session.execute(
        select(func.count(func.distinct(User.id)))
        .join(UserRole, UserRole.user_id == User.id)
        .join(Role, Role.id == UserRole.role_id)
        .where(
            User.is_active.is_(True),
            Role.code.in_(staff_role_codes),
        )
    )
    total_staff = total_staff_q.scalar_one()

    on_leave_today = (
        await session.execute(
            select(func.count(func.distinct(StaffLeave.user_id))).where(
                StaffLeave.status == StaffLeaveStatus.APPROVED.value,
                StaffLeave.start_date <= today,
                StaffLeave.end_date >= today,
            )
        )
    ).scalar_one()

    # --- fees ----
    collected_today = (
        await session.execute(
            select(func.coalesce(func.sum(FeePayment.amount), 0))
            .where(func.date(FeePayment.paid_at) == today)
        )
    ).scalar_one()
    collected_mtd = (
        await session.execute(
            select(func.coalesce(func.sum(FeePayment.amount), 0))
            .where(func.date(FeePayment.paid_at) >= first_of_month)
        )
    ).scalar_one()
    outstanding_total = (
        await session.execute(
            select(
                func.coalesce(
                    func.sum(FeeInvoice.total_amount - FeeInvoice.paid_amount),
                    0,
                )
            ).where(FeeInvoice.status != FeeInvoiceStatus.PAID.value)
        )
    ).scalar_one()
    overdue_count = (
        await session.execute(
            select(func.count(FeeInvoice.id)).where(
                FeeInvoice.status != FeeInvoiceStatus.PAID.value,
                FeeInvoice.due_date < today,
            )
        )
    ).scalar_one()

    # --- transport ----
    trips_in_progress = (
        await session.execute(
            select(func.count(Trip.id))
            .where(Trip.phase == TripPhase.IN_PROGRESS.value)
        )
    ).scalar_one()

    # --- approvals: pending count by kind ----
    pending_student_leaves = (
        await session.execute(
            select(func.count(LeaveApplication.id)).where(
                LeaveApplication.status == LeaveStatus.PENDING.value,
            )
        )
    ).scalar_one()
    pending_staff_leaves = (
        await session.execute(
            select(func.count(StaffLeave.id)).where(
                StaffLeave.status == StaffLeaveStatus.PENDING.value,
            )
        )
    ).scalar_one()

    # --- discipline alerts ----
    behaviour_concerns_today = (
        await session.execute(
            select(func.count(BehaviourNote.id)).where(
                BehaviourNote.kind == BehaviourNoteKind.CONCERN.value,
                BehaviourNote.occurred_on == today,
            )
        )
    ).scalar_one()

    pending_total = pending_student_leaves + pending_staff_leaves

    return {
        "as_of": datetime.utcnow().isoformat() + "Z",
        "attendance": {
            "total_students": int(total_students),
            "students_marked": marked,
            "students_present": present,
            "students_absent": int(
                att_by_status.get(StudentAttendanceStatus.ABSENT.value, 0)
            ),
            "percent": round((present / marked * 100), 1) if marked else 0,
        },
        "staff": {
            "total": int(total_staff),
            "on_leave_today": int(on_leave_today),
        },
        "fees": {
            "collected_today": float(collected_today or 0),
            "collected_mtd": float(collected_mtd or 0),
            "outstanding_total": float(outstanding_total or 0),
            "overdue_invoices": int(overdue_count),
        },
        "transport": {
            "trips_in_progress": int(trips_in_progress),
        },
        "approvals": {
            "pending_total": int(pending_total),
            "pending_student_leaves": int(pending_student_leaves),
            "pending_staff_leaves": int(pending_staff_leaves),
        },
        "alerts": {
            "behaviour_concerns_today": int(behaviour_concerns_today),
            "overdue_invoices": int(overdue_count),
        },
    }


# ---------------------------------------------------------------------------
# 2.  Approvals inbox
# ---------------------------------------------------------------------------


@router.get("/approvals")
async def list_approvals(
    kind: Optional[str] = None,
    session: AsyncSession = Depends(tenant_scoped_session),
):
    """Single unified pending queue.

    ``kind`` filter: ``student_leave`` | ``staff_leave`` | ``all`` (default).
    Each row carries enough context to render a one-line card with an
    accept / reject button; the app calls
    ``POST /v1/principal/approvals/{kind}/{id}/decide`` to act on a row.
    """
    from app.models.auth import User
    from app.models.parent import LeaveApplication, LeaveStatus, Student
    from app.models.staff_extras import StaffLeave, StaffLeaveStatus

    out: list[dict] = []

    if kind in (None, "all", "student_leave"):
        rows = (
            await session.execute(
                select(LeaveApplication, Student.full_name)
                .join(Student, Student.id == LeaveApplication.student_id)
                .where(LeaveApplication.status == LeaveStatus.PENDING.value)
                .order_by(LeaveApplication.start_date.desc())
                .limit(200)
            )
        ).all()
        for leave, student_name in rows:
            out.append({
                "kind": "student_leave",
                "id": leave.id,
                "title": f"{student_name} · student leave",
                "subtitle": leave.reason[:80] if leave.reason else "",
                "start_date": leave.start_date.isoformat(),
                "end_date": leave.end_date.isoformat(),
                "applied_at": leave.created_at.isoformat()
                if leave.created_at else None,
            })

    if kind in (None, "all", "staff_leave"):
        rows = (
            await session.execute(
                select(StaffLeave, User.full_name)
                .join(User, User.id == StaffLeave.user_id)
                .where(StaffLeave.status == StaffLeaveStatus.PENDING.value)
                .order_by(StaffLeave.start_date.desc())
                .limit(200)
            )
        ).all()
        for leave, staff_name in rows:
            out.append({
                "kind": "staff_leave",
                "id": leave.id,
                "title": f"{staff_name} · {leave.kind} leave",
                "subtitle": (leave.reason or "")[:80],
                "start_date": leave.start_date.isoformat(),
                "end_date": leave.end_date.isoformat(),
                "applied_at": leave.created_at.isoformat()
                if leave.created_at else None,
            })

    out.sort(key=lambda r: r.get("applied_at") or "", reverse=True)
    return out


@router.post("/approvals/{kind}/{row_id}/decide")
async def decide_approval(
    kind: str,
    row_id: int,
    decision: str,                 # "approve" | "reject"
    remarks: Optional[str] = None,
    principal: AuthPrincipal = Depends(_senior),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    """Approve or reject one row from the inbox. Routes by ``kind``:

      * ``student_leave`` → updates ``leave_applications``
      * ``staff_leave``   → updates ``staff_leaves``
    """
    if decision not in ("approve", "reject"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="decision must be 'approve' or 'reject'",
        )

    if kind == "student_leave":
        from app.models.parent import LeaveApplication, LeaveStatus
        row = await session.get(LeaveApplication, row_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Leave not found")
        row.status = (
            LeaveStatus.APPROVED.value
            if decision == "approve" else LeaveStatus.REJECTED.value
        )
        row.decision_remarks = remarks
        row.decided_by_user_id = principal.user_id
        row.decided_at = datetime.utcnow()
        await session.commit()
        return {"ok": True, "kind": kind, "id": row_id, "status": row.status}

    if kind == "staff_leave":
        from app.models.staff_extras import StaffLeave, StaffLeaveStatus
        row = await session.get(StaffLeave, row_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Leave not found")
        row.status = (
            StaffLeaveStatus.APPROVED.value
            if decision == "approve" else StaffLeaveStatus.REJECTED.value
        )
        row.decision_remarks = remarks
        row.decided_by_user_id = principal.user_id
        row.decided_at = datetime.utcnow()
        await session.commit()
        return {"ok": True, "kind": kind, "id": row_id, "status": row.status}

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Unsupported approval kind: {kind}",
    )


# ---------------------------------------------------------------------------
# 3.  Academics oversight
# ---------------------------------------------------------------------------


@router.get("/academics/attendance-by-class")
async def attendance_by_class(
    on: Optional[date] = None,
    session: AsyncSession = Depends(tenant_scoped_session),
):
    """Per-class attendance breakdown for a given day (defaults to today)."""
    from app.models.academic import ClassDef
    from app.models.attendance import StudentAttendance, StudentAttendanceStatus
    from app.models.parent import Student

    target = on or date.today()

    # students per class (active)
    pop_q = await session.execute(
        select(
            ClassDef.id,
            ClassDef.name,
            ClassDef.sequence,
            func.count(Student.id),
        )
        .outerjoin(Student, and_(
            Student.class_def_id == ClassDef.id,
            Student.is_active.is_(True),
        ))
        .group_by(ClassDef.id, ClassDef.name, ClassDef.sequence)
        .order_by(ClassDef.sequence, ClassDef.name)
    )
    pop = {row[0]: {
        "class_def_id": row[0],
        "name": row[1],
        "sequence": int(row[2]),
        "total_students": int(row[3]),
        "marked": 0,
        "present": 0,
        "absent": 0,
    } for row in pop_q.all()}

    att_q = await session.execute(
        select(
            StudentAttendance.class_def_id,
            StudentAttendance.status,
            func.count(StudentAttendance.id),
        )
        .where(StudentAttendance.date == target)
        .group_by(StudentAttendance.class_def_id, StudentAttendance.status)
    )
    for class_id, st, cnt in att_q.all():
        if class_id is None or class_id not in pop:
            continue
        pop[class_id]["marked"] += int(cnt)
        if st in (
            StudentAttendanceStatus.PRESENT.value,
            StudentAttendanceStatus.LATE.value,
            StudentAttendanceStatus.HALF_DAY.value,
        ):
            pop[class_id]["present"] += int(cnt)
        elif st == StudentAttendanceStatus.ABSENT.value:
            pop[class_id]["absent"] += int(cnt)

    out = []
    for row in pop.values():
        out.append({
            **row,
            "percent": (
                round(row["present"] / row["marked"] * 100, 1)
                if row["marked"] else 0
            ),
        })
    return {"date": target.isoformat(), "classes": out}


# ---------------------------------------------------------------------------
# 4.  Staff overview
# ---------------------------------------------------------------------------


@router.get("/staff")
async def staff_overview(
    session: AsyncSession = Depends(tenant_scoped_session),
):
    """Staff directory + today's leaves. Used by the Staff tab."""
    from app.models.auth import Role, User, UserRole
    from app.models.staff_extras import StaffLeave, StaffLeaveStatus

    staff_role_codes = (
        "principal", "vice_principal", "coordinator",
        "class_teacher", "subject_teacher", "accountant",
        "librarian", "transport_manager", "school_admin",
    )
    today = date.today()

    rows = (
        await session.execute(
            select(User.id, User.full_name, User.phone, User.email,
                   User.is_active, Role.code)
            .join(UserRole, UserRole.user_id == User.id)
            .join(Role, Role.id == UserRole.role_id)
            .where(Role.code.in_(staff_role_codes))
            .order_by(User.full_name)
        )
    ).all()

    by_user: dict[int, dict] = {}
    for uid, name, phone, email, active, role in rows:
        e = by_user.setdefault(uid, {
            "user_id": uid,
            "full_name": name,
            "phone": phone,
            "email": email,
            "is_active": bool(active),
            "roles": [],
            "on_leave_today": False,
            "leave_kind": None,
            "leave_end": None,
        })
        e["roles"].append(role)

    if by_user:
        leaves = (
            await session.execute(
                select(StaffLeave.user_id, StaffLeave.kind, StaffLeave.end_date)
                .where(
                    StaffLeave.user_id.in_(list(by_user.keys())),
                    StaffLeave.status == StaffLeaveStatus.APPROVED.value,
                    StaffLeave.start_date <= today,
                    StaffLeave.end_date >= today,
                )
            )
        ).all()
        for uid, leave_kind, end in leaves:
            if uid in by_user:
                by_user[uid]["on_leave_today"] = True
                by_user[uid]["leave_kind"] = leave_kind
                by_user[uid]["leave_end"] = end.isoformat() if end else None

    return list(by_user.values())


# ---------------------------------------------------------------------------
# 5.  Finance snapshot
# ---------------------------------------------------------------------------


@router.get("/finance/snapshot")
async def finance_snapshot(
    days_back: int = 30,
    session: AsyncSession = Depends(tenant_scoped_session),
):
    """Collection by class + defaulter top list + last-N-days collection
    series. The series powers the line chart on the Finance tab."""
    from app.models.academic import ClassDef
    from app.models.fees import FeeInvoice, FeeInvoiceStatus, FeePayment
    from app.models.parent import Student

    today = date.today()
    since = today - timedelta(days=max(1, min(days_back, 180)))

    # --- collection by class (paid_amount sums) ----
    cls_rows = (
        await session.execute(
            select(
                ClassDef.id,
                ClassDef.name,
                ClassDef.sequence,
                func.coalesce(func.sum(FeeInvoice.total_amount), 0),
                func.coalesce(func.sum(FeeInvoice.paid_amount), 0),
            )
            .join(Student, Student.class_def_id == ClassDef.id)
            .join(FeeInvoice, FeeInvoice.student_id == Student.id)
            .group_by(ClassDef.id, ClassDef.name, ClassDef.sequence)
            .order_by(ClassDef.sequence, ClassDef.name)
        )
    ).all()
    by_class = [
        {
            "class_def_id": cid,
            "name": cname,
            "sequence": int(cseq),
            "billed": float(billed),
            "collected": float(paid),
            "outstanding": float((billed or 0) - (paid or 0)),
        }
        for cid, cname, cseq, billed, paid in cls_rows
    ]

    # --- top defaulters ----
    def_rows = (
        await session.execute(
            select(
                Student.id, Student.full_name, Student.admission_number,
                func.coalesce(
                    func.sum(FeeInvoice.total_amount - FeeInvoice.paid_amount),
                    0,
                ).label("due"),
            )
            .join(FeeInvoice, FeeInvoice.student_id == Student.id)
            .where(
                FeeInvoice.status != FeeInvoiceStatus.PAID.value,
                FeeInvoice.due_date < today,
            )
            .group_by(Student.id, Student.full_name, Student.admission_number)
            .order_by(func.sum(
                FeeInvoice.total_amount - FeeInvoice.paid_amount
            ).desc())
            .limit(20)
        )
    ).all()
    defaulters = [
        {
            "student_id": sid,
            "full_name": fname,
            "admission_number": admn,
            "amount_due": float(due),
        }
        for sid, fname, admn, due in def_rows
    ]

    # --- daily collection series ----
    series_rows = (
        await session.execute(
            select(
                func.date(FeePayment.paid_at).label("d"),
                func.coalesce(func.sum(FeePayment.amount), 0),
            )
            .where(func.date(FeePayment.paid_at) >= since)
            .group_by(func.date(FeePayment.paid_at))
            .order_by(func.date(FeePayment.paid_at))
        )
    ).all()
    series = [
        {"date": d.isoformat() if hasattr(d, "isoformat") else str(d),
         "amount": float(amount)}
        for d, amount in series_rows
    ]

    return {
        "as_of": datetime.utcnow().isoformat() + "Z",
        "by_class": by_class,
        "top_defaulters": defaulters,
        "daily_collection": series,
    }


# ---------------------------------------------------------------------------
# 6.  Discipline + wellbeing
# ---------------------------------------------------------------------------


@router.get("/discipline/recent")
async def recent_discipline(
    days_back: int = 7,
    session: AsyncSession = Depends(tenant_scoped_session),
):
    """Recent behaviour concerns. Powers the Discipline tab."""
    from app.models.auth import User
    from app.models.parent import Student
    from app.models.staff_extras import BehaviourNote, BehaviourNoteKind

    since = date.today() - timedelta(days=max(1, min(days_back, 90)))
    rows = (
        await session.execute(
            select(BehaviourNote, Student.full_name, User.full_name)
            .join(Student, Student.id == BehaviourNote.student_id)
            .outerjoin(User, User.id == BehaviourNote.teacher_user_id)
            .where(
                BehaviourNote.kind == BehaviourNoteKind.CONCERN.value,
                BehaviourNote.occurred_on >= since,
            )
            .order_by(BehaviourNote.occurred_on.desc())
            .limit(200)
        )
    ).all()
    return [
        {
            "id": note.id,
            "student_id": note.student_id,
            "student_name": student_name,
            "teacher_name": teacher_name,
            "occurred_on": note.occurred_on.isoformat(),
            "headline": note.headline,
            "detail": note.detail,
        }
        for note, student_name, teacher_name in rows
    ]


# ---------------------------------------------------------------------------
# 7.  Transport oversight (reuses transport models)
# ---------------------------------------------------------------------------


@router.get("/transport/fleet-status")
async def transport_fleet_status(
    session: AsyncSession = Depends(tenant_scoped_session),
):
    """Quick fleet glance: trips in progress, scheduled, completed today."""
    from app.models.transport import Trip, TripPhase

    today = date.today()
    rows = (
        await session.execute(
            select(Trip.phase, func.count(Trip.id))
            .where(Trip.trip_date == today)
            .group_by(Trip.phase)
        )
    ).all()
    by_phase = {p: int(c) for p, c in rows}
    return {
        "date": today.isoformat(),
        "scheduled": by_phase.get(TripPhase.SCHEDULED.value, 0),
        "in_progress": by_phase.get(TripPhase.IN_PROGRESS.value, 0),
        "completed": by_phase.get(TripPhase.COMPLETED.value, 0),
        "cancelled": by_phase.get(TripPhase.CANCELLED.value, 0)
        if hasattr(TripPhase, "CANCELLED") else 0,
    }
