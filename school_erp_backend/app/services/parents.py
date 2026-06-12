"""Parent module service: child listing, dashboard, leave, parent linking."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.auth import Role, User, UserRole
from app.models.curriculum import CalendarEvent
from app.models.parent import (
    LeaveApplication,
    LeaveStatus,
    Parent,
    ParentAccessLevel,
    ParentChildMapping,
    ParentSession,
    Relation,
    Student,
)
from app.models.sis import StudentDocument
from app.schemas.parent import (
    ChildDashboard,
    ChildSummary,
    LeaveCreate,
    LeaveDecide,
    LeaveRead,
    ParentCreate,
    ParentLink,
    ParentLinkRead,
    ParentSelfRead,
    StudentDocSummary,
)


# ---- Helpers ---------------------------------------------------------------


async def _ensure_role(session: AsyncSession, tenant_id: int, user_id: int, role_code: str) -> None:
    role = (
        await session.execute(
            select(Role).where(Role.tenant_id == tenant_id, Role.code == role_code)
        )
    ).scalar_one_or_none()
    if role is None:
        return
    existing = (
        await session.execute(
            select(UserRole).where(
                UserRole.tenant_id == tenant_id,
                UserRole.user_id == user_id,
                UserRole.role_id == role.id,
            )
        )
    ).scalar_one_or_none()
    if existing is None:
        session.add(UserRole(tenant_id=tenant_id, user_id=user_id, role_id=role.id))


async def _find_parent_for_user(
    session: AsyncSession, tenant_id: int, user_id: int
) -> Optional[Parent]:
    return (
        await session.execute(
            select(Parent).where(Parent.tenant_id == tenant_id, Parent.user_id == user_id)
        )
    ).scalar_one_or_none()


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ---- Auto-link parents on student admit -----------------------------------


async def autolink_parent_for_student(
    session: AsyncSession, tenant_id: int, student: Student
) -> Optional[ParentChildMapping]:
    """If the student row carries parent_phone or parent_email, find or create
    a Parent + map them to this student. Returns the mapping or None."""
    contact = student.parent_phone or student.parent_email
    if not contact:
        return None

    full_name = (
        student.father_name or student.mother_name or student.guardian_name or contact
    )

    # Find an existing Parent row for this contact in the tenant.
    parent = (
        await session.execute(
            select(Parent).where(
                Parent.tenant_id == tenant_id,
                or_(
                    Parent.phone == student.parent_phone if student.parent_phone else False,
                    Parent.email == student.parent_email if student.parent_email else False,
                ),
            )
        )
    ).scalar_one_or_none()

    if parent is None:
        # Find or create the User. Re-use an existing email/phone match.
        user = None
        if student.parent_email:
            user = (
                await session.execute(
                    select(User).where(
                        User.tenant_id == tenant_id, User.email == student.parent_email
                    )
                )
            ).scalar_one_or_none()
        if user is None and student.parent_phone:
            user = (
                await session.execute(
                    select(User).where(
                        User.tenant_id == tenant_id, User.phone == student.parent_phone
                    )
                )
            ).scalar_one_or_none()
        if user is None:
            user = User(
                tenant_id=tenant_id,
                full_name=full_name,
                email=student.parent_email,
                phone=student.parent_phone,
                # Parents log in via OTP in Phase 12; a placeholder hash keeps them inactive-by-password.
                password_hash=None,
                is_active=True,
            )
            session.add(user)
            await session.flush()
        await _ensure_role(session, tenant_id, user.id, "parent")
        relation = (
            Relation.FATHER.value if student.father_name else
            Relation.MOTHER.value if student.mother_name else
            Relation.GUARDIAN.value
        )
        parent = Parent(
            tenant_id=tenant_id,
            user_id=user.id,
            full_name=full_name,
            phone=student.parent_phone,
            email=student.parent_email,
            occupation=student.parent_occupation,
            relation=relation,
        )
        session.add(parent)
        await session.flush()
    else:
        # Make sure the existing user has the parent role.
        await _ensure_role(session, tenant_id, parent.user_id, "parent")

    existing_link = (
        await session.execute(
            select(ParentChildMapping).where(
                ParentChildMapping.tenant_id == tenant_id,
                ParentChildMapping.parent_id == parent.id,
                ParentChildMapping.student_id == student.id,
            )
        )
    ).scalar_one_or_none()
    if existing_link is not None:
        return existing_link

    mapping = ParentChildMapping(
        tenant_id=tenant_id,
        parent_id=parent.id,
        student_id=student.id,
        relation=parent.relation,
        access_level=ParentAccessLevel.PRIMARY.value,
        is_primary=True,
        can_pay_fee=True,
        can_receive_notifications=True,
    )
    session.add(mapping)
    await session.commit()
    return mapping


# ---- Parent-facing helpers -------------------------------------------------


async def parent_self(session: AsyncSession, tenant_id: int, user_id: int) -> ParentSelfRead:
    parent = await _find_parent_for_user(session, tenant_id, user_id)
    if parent is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No parent profile linked to this user",
        )
    sess = (
        await session.execute(
            select(ParentSession).where(ParentSession.parent_id == parent.id)
        )
    ).scalar_one_or_none()
    return ParentSelfRead(
        parent_id=parent.id,
        user_id=parent.user_id,
        full_name=parent.full_name,
        phone=parent.phone,
        email=parent.email,
        relation=Relation(parent.relation),
        current_child_id=sess.current_child_id if sess else None,
    )


async def list_children(
    session: AsyncSession, tenant_id: int, user_id: int
) -> list[ChildSummary]:
    parent = await _find_parent_for_user(session, tenant_id, user_id)
    if parent is None:
        return []
    rows = (
        await session.execute(
            select(ParentChildMapping, Student)
            .join(Student, Student.id == ParentChildMapping.student_id)
            .where(ParentChildMapping.parent_id == parent.id)
            .order_by(Student.full_name)
        )
    ).all()
    return [
        ChildSummary(
            student_id=s.id,
            full_name=s.full_name,
            admission_number=s.admission_number,
            current_class_label=s.current_class_label,
            photo_url=s.photo_url,
            relation=Relation(m.relation),
            access_level=ParentAccessLevel(m.access_level),
            is_primary=m.is_primary,
            can_pay_fee=m.can_pay_fee,
            can_receive_notifications=m.can_receive_notifications,
        )
        for (m, s) in rows
    ]


async def select_child(
    session: AsyncSession, tenant_id: int, user_id: int, student_id: int
) -> int:
    parent = await _find_parent_for_user(session, tenant_id, user_id)
    if parent is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a parent account")

    mapping = (
        await session.execute(
            select(ParentChildMapping).where(
                ParentChildMapping.parent_id == parent.id,
                ParentChildMapping.student_id == student_id,
            )
        )
    ).scalar_one_or_none()
    if mapping is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="That child is not linked to your account",
        )

    sess = (
        await session.execute(
            select(ParentSession).where(ParentSession.parent_id == parent.id)
        )
    ).scalar_one_or_none()
    if sess is None:
        sess = ParentSession(
            tenant_id=tenant_id,
            parent_id=parent.id,
            current_child_id=student_id,
        )
        session.add(sess)
    else:
        sess.current_child_id = student_id
        sess.last_switched_at = _now()
    await session.commit()
    return student_id


async def dashboard_for_child(
    session: AsyncSession, tenant_id: int, user_id: int, student_id: int
) -> ChildDashboard:
    parent = await _find_parent_for_user(session, tenant_id, user_id)
    if parent is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a parent account")
    mapping = (
        await session.execute(
            select(ParentChildMapping).where(
                ParentChildMapping.parent_id == parent.id,
                ParentChildMapping.student_id == student_id,
            )
        )
    ).scalar_one_or_none()
    if mapping is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Child not linked")

    student = (
        await session.execute(select(Student).where(Student.id == student_id))
    ).scalar_one()

    pending_leaves = int(
        (
            await session.execute(
                select(func.count(LeaveApplication.id)).where(
                    LeaveApplication.student_id == student_id,
                    LeaveApplication.status == LeaveStatus.PENDING.value,
                )
            )
        ).scalar_one()
    )
    docs_count = int(
        (
            await session.execute(
                select(func.count(StudentDocument.id)).where(
                    StudentDocument.student_id == student_id
                )
            )
        ).scalar_one()
    )
    upcoming_events = int(
        (
            await session.execute(
                select(func.count(CalendarEvent.id)).where(
                    CalendarEvent.starts_at >= _now()
                )
            )
        ).scalar_one()
    )

    siblings: list[int] = []
    if student.sibling_group_id is not None:
        siblings = list(
            (
                await session.execute(
                    select(Student.id).where(
                        Student.sibling_group_id == student.sibling_group_id,
                        Student.id != student.id,
                    )
                )
            ).scalars().all()
        )

    # Phase 9: today's attendance status if present.
    from app.services.attendance import today_status_for_student

    today_status = await today_status_for_student(session, student.id)

    # Phase 11: outstanding fee due across all open invoices.
    from app.services.fees import fee_due_for_student

    fee_due = await fee_due_for_student(session, student.id)

    # Phase 14: homework pending count.
    from app.services.homework import pending_homework_count

    pending_hw = await pending_homework_count(session, student.id)

    return ChildDashboard(
        student_id=student.id,
        full_name=student.full_name,
        admission_number=student.admission_number,
        current_class_label=student.current_class_label,
        is_active=student.is_active,
        pending_leaves=pending_leaves,
        documents_count=docs_count,
        sibling_ids=siblings,
        upcoming_events_count=upcoming_events,
        today_attendance=today_status,
        fee_due_amount=float(fee_due),
        pending_homework=pending_hw,
    )


async def attendance_history_for_parent(
    session: AsyncSession,
    *,
    tenant_id: int,
    user_id: int,
    student_id: int,
    limit: int = 60,
):
    """Parent-facing history. Verifies the student is linked to the parent."""
    parent = await _find_parent_for_user(session, tenant_id, user_id)
    if parent is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a parent account")
    linked = (
        await session.execute(
            select(ParentChildMapping.id).where(
                ParentChildMapping.parent_id == parent.id,
                ParentChildMapping.student_id == student_id,
            )
        )
    ).scalar_one_or_none()
    if linked is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Child not linked")

    from app.services.attendance import student_history

    return await student_history(session, student_id=student_id, limit=limit)


async def _require_linked_child(
    session: AsyncSession, *, tenant_id: int, user_id: int, student_id: int,
) -> None:
    parent = await _find_parent_for_user(session, tenant_id, user_id)
    if parent is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a parent account")
    linked = (
        await session.execute(
            select(ParentChildMapping.id).where(
                ParentChildMapping.parent_id == parent.id,
                ParentChildMapping.student_id == student_id,
            )
        )
    ).scalar_one_or_none()
    if linked is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Child not linked")


async def subject_attendance_for_parent(
    session: AsyncSession,
    *,
    tenant_id: int,
    user_id: int,
    student_id: int,
    window_days: int = 90,
):
    await _require_linked_child(
        session, tenant_id=tenant_id, user_id=user_id, student_id=student_id,
    )
    from app.services.attendance import student_attendance_by_subject

    return await student_attendance_by_subject(
        session, student_id=student_id, window_days=window_days,
    )


async def class_average_for_parent(
    session: AsyncSession,
    *,
    tenant_id: int,
    user_id: int,
    student_id: int,
    window_days: int = 30,
):
    await _require_linked_child(
        session, tenant_id=tenant_id, user_id=user_id, student_id=student_id,
    )
    from app.services.attendance import student_vs_class_average

    return await student_vs_class_average(
        session, student_id=student_id, window_days=window_days,
    )


async def timetable_for_parent(
    session: AsyncSession,
    *,
    tenant_id: int,
    user_id: int,
    student_id: int,
):
    await _require_linked_child(
        session, tenant_id=tenant_id, user_id=user_id, student_id=student_id,
    )
    from app.services.attendance import student_timetable_view

    return await student_timetable_view(session, student_id=student_id)


async def list_documents_for_child(
    session: AsyncSession, tenant_id: int, user_id: int, student_id: int
) -> list[StudentDocSummary]:
    parent = await _find_parent_for_user(session, tenant_id, user_id)
    if parent is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a parent account")
    linked = (
        await session.execute(
            select(ParentChildMapping.id).where(
                ParentChildMapping.parent_id == parent.id,
                ParentChildMapping.student_id == student_id,
            )
        )
    ).scalar_one_or_none()
    if linked is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Child not linked")
    rows = (
        await session.execute(
            select(StudentDocument).where(StudentDocument.student_id == student_id)
        )
    ).scalars().all()
    return [StudentDocSummary.model_validate(r) for r in rows]


# ---- Leave applications ----------------------------------------------------


async def apply_leave(
    session: AsyncSession, tenant_id: int, user_id: int, payload: LeaveCreate
) -> LeaveApplication:
    parent = await _find_parent_for_user(session, tenant_id, user_id)
    if parent is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a parent account")
    mapping = (
        await session.execute(
            select(ParentChildMapping).where(
                ParentChildMapping.parent_id == parent.id,
                ParentChildMapping.student_id == payload.student_id,
            )
        )
    ).scalar_one_or_none()
    if mapping is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Child not linked")
    if payload.end_date < payload.start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_date must be on or after start_date",
        )
    leave = LeaveApplication(
        tenant_id=tenant_id,
        student_id=payload.student_id,
        parent_id=parent.id,
        applied_by_user_id=user_id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        reason=payload.reason,
        status=LeaveStatus.PENDING.value,
    )
    session.add(leave)
    await session.commit()
    await session.refresh(leave)
    return leave


async def list_leaves_for_user(
    session: AsyncSession, tenant_id: int, user_id: int
) -> list[LeaveApplication]:
    parent = await _find_parent_for_user(session, tenant_id, user_id)
    if parent is None:
        return []
    return list(
        (
            await session.execute(
                select(LeaveApplication)
                .where(LeaveApplication.parent_id == parent.id)
                .order_by(LeaveApplication.start_date.desc())
            )
        ).scalars().all()
    )


async def list_school_leaves(
    session: AsyncSession,
    *,
    student_id: Optional[int] = None,
    status_filter: Optional[LeaveStatus] = None,
) -> list[LeaveApplication]:
    stmt = select(LeaveApplication).order_by(LeaveApplication.created_at.desc())
    if student_id is not None:
        stmt = stmt.where(LeaveApplication.student_id == student_id)
    if status_filter is not None:
        stmt = stmt.where(LeaveApplication.status == status_filter.value)
    return list((await session.execute(stmt)).scalars().all())


async def decide_leave(
    session: AsyncSession,
    leave_id: int,
    *,
    decided_by_user_id: int,
    payload: LeaveDecide,
) -> LeaveApplication:
    leave = (
        await session.execute(select(LeaveApplication).where(LeaveApplication.id == leave_id))
    ).scalar_one_or_none()
    if leave is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Leave not found")
    if payload.decision not in {LeaveStatus.APPROVED, LeaveStatus.REJECTED}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="decision must be approved or rejected",
        )
    leave.status = payload.decision.value
    leave.decision_remarks = payload.decision_remarks
    leave.decided_by_user_id = decided_by_user_id
    leave.decided_at = _now()
    await session.commit()
    await session.refresh(leave)

    # Phase 12: notify the parent who applied. Best-effort; never block the
    # decision if the comms layer hiccups.
    try:
        from app.services.comms import notify

        if leave.parent_id is not None:
            parent = (
                await session.execute(
                    select(Parent).where(Parent.id == leave.parent_id)
                )
            ).scalar_one_or_none()
            student = (
                await session.execute(
                    select(Student).where(Student.id == leave.student_id)
                )
            ).scalar_one_or_none()
            if parent is not None:
                from app.models.auth import User as _User

                user = (
                    await session.execute(
                        select(_User).where(_User.id == parent.user_id)
                    )
                ).scalar_one_or_none()
                if user is not None:
                    await notify(
                        session,
                        tenant_id=leave.tenant_id,
                        template_code="leave.decided",
                        recipients=[user],
                        context={
                            "decision": leave.status,
                            "student": student.full_name if student else "",
                            "start": leave.start_date.isoformat(),
                            "end": leave.end_date.isoformat(),
                            "remarks": leave.decision_remarks or "",
                        },
                        deeplink=f"/parent/dashboard/{leave.student_id}",
                        source_type="leave",
                        source_id=leave.id,
                        kind="leave",
                    )
    except Exception:
        # Comms must never block a school-admin decision.
        pass

    return leave


# ---- School-admin parent linking ------------------------------------------


async def list_parent_links(
    session: AsyncSession, student_id: int
) -> list[ParentLinkRead]:
    rows = (
        await session.execute(
            select(ParentChildMapping, Parent)
            .join(Parent, Parent.id == ParentChildMapping.parent_id)
            .where(ParentChildMapping.student_id == student_id)
        )
    ).all()
    return [
        ParentLinkRead(
            mapping_id=m.id,
            parent_id=p.id,
            parent_user_id=p.user_id,
            parent_name=p.full_name,
            parent_phone=p.phone,
            parent_email=p.email,
            relation=Relation(m.relation),
            access_level=ParentAccessLevel(m.access_level),
            is_primary=m.is_primary,
            can_pay_fee=m.can_pay_fee,
            can_receive_notifications=m.can_receive_notifications,
        )
        for (m, p) in rows
    ]


async def create_parent_user(
    session: AsyncSession, tenant_id: int, payload: ParentCreate
) -> Parent:
    if not payload.email and not payload.phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="email or phone required",
        )
    user_q = select(User).where(User.tenant_id == tenant_id)
    if payload.email:
        user_q = user_q.where(User.email == payload.email)
    elif payload.phone:
        user_q = user_q.where(User.phone == payload.phone)
    existing = (await session.execute(user_q)).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email/phone already exists",
        )
    user = User(
        tenant_id=tenant_id,
        full_name=payload.full_name,
        email=payload.email,
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        is_active=True,
    )
    session.add(user)
    await session.flush()
    await _ensure_role(session, tenant_id, user.id, "parent")
    parent = Parent(
        tenant_id=tenant_id,
        user_id=user.id,
        full_name=payload.full_name,
        phone=payload.phone,
        email=payload.email,
        occupation=payload.occupation,
        relation=payload.relation.value,
    )
    session.add(parent)
    await session.commit()
    await session.refresh(parent)
    return parent


async def link_parent_to_student(
    session: AsyncSession,
    tenant_id: int,
    student_id: int,
    payload: ParentLink,
) -> ParentChildMapping:
    parent = (
        await session.execute(
            select(Parent).where(
                Parent.tenant_id == tenant_id, Parent.user_id == payload.parent_user_id
            )
        )
    ).scalar_one_or_none()
    if parent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No parent profile for that user; create one first",
        )
    existing = (
        await session.execute(
            select(ParentChildMapping).where(
                ParentChildMapping.parent_id == parent.id,
                ParentChildMapping.student_id == student_id,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        existing.relation = payload.relation.value
        existing.access_level = payload.access_level.value
        existing.is_primary = payload.is_primary
        existing.can_pay_fee = payload.can_pay_fee
        existing.can_receive_notifications = payload.can_receive_notifications
        await session.commit()
        await session.refresh(existing)
        return existing
    mapping = ParentChildMapping(
        tenant_id=tenant_id,
        parent_id=parent.id,
        student_id=student_id,
        relation=payload.relation.value,
        access_level=payload.access_level.value,
        is_primary=payload.is_primary,
        can_pay_fee=payload.can_pay_fee,
        can_receive_notifications=payload.can_receive_notifications,
    )
    session.add(mapping)
    await session.commit()
    await session.refresh(mapping)
    return mapping


async def unlink_parent_from_student(
    session: AsyncSession, mapping_id: int
) -> None:
    mapping = (
        await session.execute(
            select(ParentChildMapping).where(ParentChildMapping.id == mapping_id)
        )
    ).scalar_one_or_none()
    if mapping is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mapping not found")
    await session.delete(mapping)
    await session.commit()


async def set_parent_password(
    session: AsyncSession,
    *,
    tenant_id: int,
    parent_user_id: int,
    new_password: str,
) -> User:
    """Force-set the password for a parent user. Used by the school admin
    UI when a parent was auto-created during admit (password_hash=NULL) and
    needs login credentials, or when the parent forgot their password.

    Validates that:
    * the user exists in this tenant (defense-in-depth on top of the
      tenant_scoped_session filter),
    * the user has the 'parent' role (we don't expose this endpoint as a
      generic "reset any user's password" by accident).
    """
    if len(new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters",
        )

    user = (
        await session.execute(
            select(User).where(
                User.id == parent_user_id, User.tenant_id == tenant_id
            )
        )
    ).scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Make sure this is actually a parent — we don't want this endpoint
    # being weaponised to reset a teacher's or admin's password.
    has_parent_role = (
        await session.execute(
            select(UserRole.id)
            .join(Role, Role.id == UserRole.role_id)
            .where(
                UserRole.user_id == user.id,
                UserRole.tenant_id == tenant_id,
                Role.code == "parent",
            )
        )
    ).scalar_one_or_none()
    if has_parent_role is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Target user is not a parent",
        )

    user.password_hash = hash_password(new_password)
    user.is_active = True
    # If the email/phone wasn't verified yet, flip it — the school admin
    # vouching for the credentials counts as verification.
    user.is_email_verified = True
    await session.commit()
    await session.refresh(user)
    return user


# ---- Parent calendar feeds (holidays + events) ----------------------------


async def list_holidays_for_parent(
    session: AsyncSession, *, days_back: int = 7, days_forward: int = 180
) -> list:
    """Return holidays in a window around today. Tenant-scoped via the
    parent session's loader criteria, so no tenant_id filter is needed
    here."""
    from app.models.academic import Holiday

    today = _now().date()
    from datetime import timedelta

    start = today - timedelta(days=days_back)
    end = today + timedelta(days=days_forward)
    rows = (
        await session.execute(
            select(Holiday)
            .where(Holiday.date >= start, Holiday.date <= end)
            .order_by(Holiday.date.asc())
        )
    ).scalars().all()
    return list(rows)


async def list_events_for_parent(
    session: AsyncSession, *, days_back: int = 7, days_forward: int = 180
) -> list:
    """Events visible to parents: audience in ('all', 'parents'). Class-
    scoped events (audience='class:XY') aren't surfaced here yet — they
    need the child's section context which the caller doesn't pass."""
    today = _now().date()
    from datetime import datetime as _dt, timedelta

    start = _dt.combine(today - timedelta(days=days_back), _dt.min.time())
    end = _dt.combine(today + timedelta(days=days_forward), _dt.max.time())
    rows = (
        await session.execute(
            select(CalendarEvent)
            .where(
                CalendarEvent.starts_at >= start,
                CalendarEvent.starts_at <= end,
                CalendarEvent.audience.in_(["all", "parents"]),
            )
            .order_by(CalendarEvent.starts_at.asc())
        )
    ).scalars().all()
    return list(rows)


async def profile_for_parent(
    session: AsyncSession, *, user_id: int, student_id: int, tenant_id: int
):
    """Build a self-contained profile blob with everything the mobile
    side needs to render the profile page *and* the in-app ID card —
    no follow-up calls required."""
    from app.models.academic import ClassDef, Section
    from app.models.curriculum import House
    from app.models.tenant import Tenant
    from app.schemas.parent import ParentContact, StudentProfileView

    await _require_linked_child(
        session, tenant_id=tenant_id, user_id=user_id, student_id=student_id,
    )

    student = (
        await session.execute(select(Student).where(Student.id == student_id))
    ).scalar_one_or_none()
    if student is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Student not found"
        )

    section_name = None
    if student.section_id is not None:
        sec = (
            await session.execute(
                select(Section).where(Section.id == student.section_id)
            )
        ).scalar_one_or_none()
        section_name = sec.name if sec else None

    class_label = student.current_class_label
    if not class_label and student.class_def_id is not None:
        cls = (
            await session.execute(
                select(ClassDef).where(ClassDef.id == student.class_def_id)
            )
        ).scalar_one_or_none()
        class_label = cls.name if cls else None

    house_name = None
    if student.house_id is not None:
        hs = (
            await session.execute(select(House).where(House.id == student.house_id))
        ).scalar_one_or_none()
        house_name = hs.name if hs else None

    parent_rows = list(
        (
            await session.execute(
                select(ParentChildMapping, Parent)
                .join(Parent, Parent.id == ParentChildMapping.parent_id)
                .where(ParentChildMapping.student_id == student_id)
            )
        ).all()
    )
    parents = [
        ParentContact(
            relation=mapping.relation,
            full_name=parent.full_name,
            phone=parent.phone,
            email=parent.email,
            access_level=mapping.access_level,
            is_primary=mapping.is_primary,
        )
        for mapping, parent in parent_rows
    ]

    tenant = (
        await session.execute(select(Tenant).where(Tenant.id == tenant_id))
    ).scalar_one_or_none()

    return StudentProfileView(
        student_id=student.id,
        full_name=student.full_name,
        admission_number=student.admission_number,
        roll_no=student.roll_no,
        photo_url=student.photo_url,
        date_of_birth=student.date_of_birth,
        gender=student.gender,
        blood_group=student.blood_group,
        class_label=class_label,
        section_name=section_name,
        admission_date=student.admission_date,
        house_name=house_name,
        address=student.address,
        phone=student.phone,
        email=student.email,
        emergency_contact_name=student.emergency_contact_name,
        emergency_phone=student.emergency_phone,
        allergies=student.allergies,
        medical_conditions=student.medical_conditions,
        father_name=student.father_name,
        mother_name=student.mother_name,
        guardian_name=student.guardian_name,
        parent_phone=student.parent_phone,
        parent_email=student.parent_email,
        parents=parents,
        school_name=tenant.school_name if tenant else "School",
        school_address=tenant.address if tenant else None,
        school_phone=tenant.phone if tenant else None,
        school_logo_url=tenant.logo_url if tenant else None,
    )


async def directory_for_parent(
    session: AsyncSession, *, tenant_id: int, user_id: int, student_id: int
) -> list[dict]:
    """Returns the teachers actually attached to the child's section:
    every SectionSubject row, plus the section in-charge as the class
    teacher. Deliberately omits phone + email — the Teacher model has no
    visibility flag yet, and exposing personal contacts to every parent
    is a privacy non-starter."""
    from app.models.academic import Section, Subject
    from app.models.curriculum import SectionSubject
    from app.models.teacher import Teacher

    await _require_linked_child(
        session, tenant_id=tenant_id, user_id=user_id, student_id=student_id,
    )

    student = (
        await session.execute(select(Student).where(Student.id == student_id))
    ).scalar_one_or_none()
    if student is None or student.section_id is None:
        return []

    section = (
        await session.execute(select(Section).where(Section.id == student.section_id))
    ).scalar_one_or_none()
    if section is None:
        return []

    assignments = list(
        (
            await session.execute(
                select(SectionSubject, Subject, Teacher)
                .join(Subject, Subject.id == SectionSubject.subject_id)
                .join(Teacher, Teacher.user_id == SectionSubject.teacher_user_id)
                .where(
                    SectionSubject.section_id == section.id,
                    SectionSubject.teacher_user_id.is_not(None),
                )
            )
        ).all()
    )

    entries: list[dict] = []
    seen_teacher_ids: set[int] = set()

    if section.in_charge_user_id is not None:
        in_charge = (
            await session.execute(
                select(Teacher).where(Teacher.user_id == section.in_charge_user_id)
            )
        ).scalar_one_or_none()
        if in_charge is not None:
            entries.append({
                "teacher_id": in_charge.id,
                "full_name": in_charge.full_name,
                "designation": in_charge.designation,
                "photo_url": in_charge.photo_url,
                "subject_name": None,
                "is_class_teacher": True,
            })
            seen_teacher_ids.add(in_charge.id)

    for _ss, subj, teacher in assignments:
        # A subject teacher who is *also* the class teacher should appear
        # only once but with their subject listed; replace the lonely
        # class-teacher entry instead of duplicating.
        if teacher.id in seen_teacher_ids:
            for e in entries:
                if e["teacher_id"] == teacher.id and e["subject_name"] is None:
                    e["subject_name"] = subj.name
                    break
            continue
        entries.append({
            "teacher_id": teacher.id,
            "full_name": teacher.full_name,
            "designation": teacher.designation,
            "photo_url": teacher.photo_url,
            "subject_name": subj.name,
            "is_class_teacher": False,
        })
        seen_teacher_ids.add(teacher.id)

    return entries
