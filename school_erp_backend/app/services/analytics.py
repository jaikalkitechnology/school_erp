"""Cross-school analytics for the Super Admin dashboard."""

from __future__ import annotations

from collections import Counter

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.file_storage import get_tenant_storage_used_mb
from app.models.auth import Role, User, UserRole
from app.models.parent import Student
from app.models.tenant import (
    BillingCycle,
    Subscription,
    SubscriptionPlan,
    SubscriptionStatus,
    Tenant,
    TenantStatus,
)


async def overview(session: AsyncSession) -> dict:
    tenants = list((await session.execute(select(Tenant))).scalars().all())
    plans = {p.id: p for p in (await session.execute(select(SubscriptionPlan))).scalars().all()}

    # Status breakdown.
    by_status = Counter(t.status.value if t.status else "unknown" for t in tenants)

    # Geographic.
    by_state = Counter(t.state for t in tenants if t.state)

    # By plan code.
    by_plan: Counter[str] = Counter()
    for t in tenants:
        plan = plans.get(t.plan_id) if t.plan_id else None
        by_plan[plan.code if plan else "unassigned"] += 1

    # Student + teacher totals across all tenants (lightweight count).
    total_students = int(
        (await session.execute(select(func.count(Student.id)))).scalar_one()
    )
    teacher_role_ids = (
        await session.execute(
            select(Role.id).where(Role.code.in_(["class_teacher", "subject_teacher"]))
        )
    ).scalars().all()
    if teacher_role_ids:
        total_teachers = int(
            (
                await session.execute(
                    select(func.count(func.distinct(UserRole.user_id))).where(
                        UserRole.role_id.in_(list(teacher_role_ids))
                    )
                )
            ).scalar_one()
        )
    else:
        total_teachers = 0

    # MRR: sum of latest active subscription monthly equivalent per tenant.
    subs = (
        await session.execute(
            select(Subscription).where(Subscription.status == SubscriptionStatus.ACTIVE)
        )
    ).scalars().all()
    mrr = 0.0
    for s in subs:
        amount = float(s.amount or 0)
        if s.billing_cycle == BillingCycle.ANNUAL:
            mrr += amount / 12.0
        elif s.billing_cycle == BillingCycle.QUARTERLY:
            mrr += amount / 3.0
        else:
            mrr += amount

    # Storage: cheapish file walk per tenant. Skip in CI where dirs are empty.
    total_storage = sum(get_tenant_storage_used_mb(t.id) for t in tenants)

    return {
        "total_tenants": len(tenants),
        "active_tenants": by_status.get(TenantStatus.ACTIVE.value, 0),
        "trial_tenants": by_status.get(TenantStatus.TRIAL.value, 0),
        "suspended_tenants": by_status.get(TenantStatus.SUSPENDED.value, 0),
        "total_students": total_students,
        "total_teachers": total_teachers,
        "total_storage_used_mb": round(total_storage, 2),
        "mrr": round(mrr, 2),
        "by_state": dict(by_state),
        "by_plan": dict(by_plan),
    }
