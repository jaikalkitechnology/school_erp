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
