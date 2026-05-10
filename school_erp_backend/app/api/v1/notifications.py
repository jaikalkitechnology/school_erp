"""Notifications stub (Phase 10).

Real delivery (SMS / WhatsApp / push) lands in Phase 12. For now this surface
exists so Phase 10 mobile UI has something concrete to render. The list is a
mix of real domain events (pending leave decisions, defaulter alerts for
admins) so it isn't fake data.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import AuthPrincipal, get_current_principal
from app.core.tenant_session import platform_session
from app.models.parent import LeaveApplication, LeaveStatus, Parent, ParentChildMapping, Student


class NotificationItem(BaseModel):
    id: str
    title: str
    body: str
    kind: str  # leave / absence / event / generic
    created_at: datetime
    deeplink: Optional[str] = None
    read: bool = False


router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=List[NotificationItem])
async def list_notifications(
    principal: AuthPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(platform_session),
) -> List[NotificationItem]:
    items: list[NotificationItem] = []

    # Parent: surface leave decisions for their kids.
    if "parent" in principal.roles:
        parent = (
            await session.execute(
                select(Parent).where(Parent.user_id == principal.user_id, Parent.tenant_id == principal.tenant_id)
            )
        ).scalar_one_or_none()
        if parent is not None:
            decided = list(
                (
                    await session.execute(
                        select(LeaveApplication, Student)
                        .join(Student, Student.id == LeaveApplication.student_id)
                        .where(
                            LeaveApplication.parent_id == parent.id,
                            LeaveApplication.status.in_([LeaveStatus.APPROVED.value, LeaveStatus.REJECTED.value]),
                        )
                        .order_by(LeaveApplication.decided_at.desc())
                        .limit(10)
                    )
                ).all()
            )
            for leave, student in decided:
                verb = "approved" if leave.status == LeaveStatus.APPROVED.value else "rejected"
                items.append(
                    NotificationItem(
                        id=f"leave:{leave.id}",
                        title=f"Leave {verb}",
                        body=f"{student.full_name} · {leave.start_date} → {leave.end_date}",
                        kind="leave",
                        created_at=leave.decided_at or leave.updated_at,
                        deeplink=f"/parent/dashboard/{student.id}",
                    )
                )

    # School staff: surface pending leave queue for visibility.
    elif {"school_admin", "principal", "vice_principal", "class_teacher"} & set(principal.roles):
        pending = list(
            (
                await session.execute(
                    select(LeaveApplication, Student)
                    .join(Student, Student.id == LeaveApplication.student_id)
                    .where(LeaveApplication.status == LeaveStatus.PENDING.value)
                    .order_by(LeaveApplication.created_at.desc())
                    .limit(10)
                )
            ).all()
        )
        for leave, student in pending:
            items.append(
                NotificationItem(
                    id=f"leave:{leave.id}",
                    title="Pending leave request",
                    body=f"{student.full_name} · {leave.start_date} → {leave.end_date}",
                    kind="leave",
                    created_at=leave.created_at,
                    deeplink=f"/school-admin/leave-applications",
                )
            )

    return items
