"""Mobile-scoped views on the Phase 28 operations tables.

The admin surface in ``operations.py`` gives full CRUD to office
staff. The mobile app needs a different shape:

  * **Parent** — reads only their child's health / discipline /
    certificates rows, filtered by the currently selected child.
  * **Teacher** — reads their own payslips (not everyone else's).
  * **Everyone** — sees the notice board (audience-filtered) and
    the sports leaderboard.

Keeping these routes in a separate router file so the ACL story is
obvious — every endpoint here has its own narrow role gate and its
own filter on top of ``tenant_scoped_session``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import AuthPrincipal, require_roles
from app.core.rbac_catalog import STAFF_ROLE_CODES
from app.core.tenant_session import tenant_scoped_session


_parent = require_roles("parent")
_teacher = require_roles(
    "class_teacher", "subject_teacher", "coordinator", "teacher",
    "principal", "vice_principal", "hod", "school_admin",
    "management",
)
_any = require_roles("parent", "student", *sorted(STAFF_ROLE_CODES))


router = APIRouter(prefix="/mobile", tags=["mobile"])


def _row_to_dict(obj) -> dict:
    from datetime import date, datetime
    out = {}
    for c in obj.__table__.columns:
        v = getattr(obj, c.name)
        if isinstance(v, (date, datetime)):
            out[c.name] = v.isoformat()
        else:
            out[c.name] = v
    return out


async def _assert_child_belongs_to_parent(
    session: AsyncSession, parent_user_id: int, student_id: int,
) -> None:
    """403 unless the given ``student_id`` is one of the logged-in
    parent's linked children."""
    from app.models.parent import Parent, ParentChildMapping

    row = (
        await session.execute(
            select(ParentChildMapping.id)
            .join(Parent, Parent.id == ParentChildMapping.parent_id)
            .where(
                Parent.user_id == parent_user_id,
                ParentChildMapping.student_id == student_id,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not your child",
        )


# ---------------------------------------------------------------------------
# Parent: health / discipline / certificates for their child
# ---------------------------------------------------------------------------


@router.get("/parent/children/{student_id}/health-records")
async def parent_health_records(
    student_id: int,
    principal: AuthPrincipal = Depends(_parent),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    from app.models.operations import HealthRecord

    await _assert_child_belongs_to_parent(session, principal.user_id, student_id)
    rows = (
        await session.execute(
            select(HealthRecord)
            .where(HealthRecord.student_id == student_id)
            .order_by(HealthRecord.occurred_on.desc())
            .limit(200)
        )
    ).scalars().all()
    return [_row_to_dict(r) for r in rows]


@router.get("/parent/children/{student_id}/discipline")
async def parent_discipline(
    student_id: int,
    principal: AuthPrincipal = Depends(_parent),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    from app.models.operations import DisciplineIncident

    await _assert_child_belongs_to_parent(session, principal.user_id, student_id)
    rows = (
        await session.execute(
            select(DisciplineIncident)
            .where(
                DisciplineIncident.student_id == student_id,
                # Only rows the school has explicitly flagged as parent-visible
                # (all rows by default; ``parent_informed`` is the audit flag,
                # not a visibility filter). Show everything.
            )
            .order_by(DisciplineIncident.occurred_on.desc())
            .limit(200)
        )
    ).scalars().all()
    return [_row_to_dict(r) for r in rows]


@router.get("/parent/children/{student_id}/certificates")
async def parent_certificates(
    student_id: int,
    principal: AuthPrincipal = Depends(_parent),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    from app.models.operations import IssuedCertificate

    await _assert_child_belongs_to_parent(session, principal.user_id, student_id)
    rows = (
        await session.execute(
            select(IssuedCertificate)
            .where(IssuedCertificate.student_id == student_id)
            .order_by(IssuedCertificate.issued_on.desc())
            .limit(200)
        )
    ).scalars().all()
    return [_row_to_dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Teacher: my payslips
# ---------------------------------------------------------------------------


# Any staff member reads their own slips (the path predates non-teaching
# staff having app screens).
_payslip_reader = require_roles(*sorted(STAFF_ROLE_CODES))


@router.get("/teacher/me/payslips")
async def my_payslips(
    principal: AuthPrincipal = Depends(_payslip_reader),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    from app.models.operations import Payslip

    rows = (
        await session.execute(
            select(Payslip)
            .where(Payslip.user_id == principal.user_id)
            .order_by(Payslip.period.desc())
            .limit(60)
        )
    ).scalars().all()
    return [_row_to_dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Everyone: notices (audience-filtered) + sports
# ---------------------------------------------------------------------------


def _notice_audience_for(roles: list[str]) -> list[str]:
    """Which notice-audience buckets the current user should see."""
    role_set = set(roles)
    buckets = ["all"]
    if "parent" in role_set:
        buckets.append("parents")
    if "student" in role_set:
        buckets.append("students")
    if role_set & STAFF_ROLE_CODES:
        buckets.append("staff")
    return buckets


@router.get("/notices")
async def list_notices(
    principal: AuthPrincipal = Depends(_any),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    """Notices visible to the current user. Published-only, unexpired,
    audience-filtered by the user's roles. Pinned notices first."""
    from app.models.operations import Notice

    now = datetime.utcnow()
    audiences = _notice_audience_for(principal.roles)

    rows = (
        await session.execute(
            select(Notice)
            .where(
                Notice.audience.in_(audiences),
                or_(Notice.published_at.is_(None), Notice.published_at <= now),
                or_(Notice.expires_at.is_(None), Notice.expires_at >= now),
            )
            .order_by(Notice.is_pinned.desc(), Notice.published_at.desc())
            .limit(500)
        )
    ).scalars().all()
    # A notice sent to particular people is shown only to them.
    rows = [r for r in rows if not r.recipient_user_ids or principal.user_id in r.recipient_user_ids]
    return [_row_to_dict(r) for r in rows[:100]]


@router.get("/sports/houses")
async def sports_houses(
    principal: AuthPrincipal = Depends(_any),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    from app.models.operations import SportsHouse

    rows = (
        await session.execute(
            select(SportsHouse).order_by(SportsHouse.points.desc())
        )
    ).scalars().all()
    return [_row_to_dict(r) for r in rows]


@router.get("/sports/events")
async def sports_events(
    upcoming_only: bool = False,
    principal: AuthPrincipal = Depends(_any),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    from datetime import date as _d

    from app.models.operations import SportsEvent

    stmt = select(SportsEvent).order_by(SportsEvent.starts_on.desc())
    if upcoming_only:
        stmt = select(SportsEvent).where(
            SportsEvent.starts_on >= _d.today()
        ).order_by(SportsEvent.starts_on.asc())
    rows = (await session.execute(stmt.limit(60))).scalars().all()
    return [_row_to_dict(r) for r in rows]
