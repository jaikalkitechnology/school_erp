"""Student self-service helpers.

A logged-in *student* (User linked to a Student row via ``Student.user_id``)
gets read access to their own academic data. These helpers resolve the
caller's own Student record and then delegate to the same underlying
query functions the parent module uses — the only difference is the
authorisation gate (self, not parent-child linkage).
"""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.parent import Student
from app.schemas.parent import ChildDashboard


async def resolve_self_student(session: AsyncSession, user_id: int) -> Student:
    """Return the Student row owned by this user, or 403 if none.

    The session is tenant-scoped, so this can only ever resolve a student
    inside the caller's own tenant.
    """
    student = (
        await session.execute(
            select(Student).where(Student.user_id == user_id)
        )
    ).scalar_one_or_none()
    if student is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No student profile linked to this account",
        )
    return student


async def dashboard_for_self(
    session: AsyncSession, student: Student
) -> ChildDashboard:
    """Compact home-screen summary for the student's own record."""
    from app.services.attendance import today_status_for_student
    from app.services.fees import fee_due_for_student
    from app.services.homework import pending_homework_count

    today_status = await today_status_for_student(session, student.id)
    fee_due = await fee_due_for_student(session, student.id)
    pending_hw = await pending_homework_count(session, student.id)

    return ChildDashboard(
        student_id=student.id,
        full_name=student.full_name,
        admission_number=student.admission_number,
        current_class_label=student.current_class_label,
        is_active=student.is_active,
        pending_leaves=0,
        documents_count=0,
        sibling_ids=[],
        today_attendance=today_status,
        fee_due_amount=float(fee_due),
        pending_homework=pending_hw,
    )
