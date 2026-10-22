"""Tenant lifecycle service.

Pure functions over an ``AsyncSession`` so they can be reused by HTTP
endpoints, background jobs, and tests.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable, Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.file_storage import ensure_tenant_dirs, get_tenant_storage_used_mb
from app.core.security import hash_password
from app.models.auth import Role, User, UserRole
from app.models.tenant import (
    BillingCycle,
    Subscription,
    SubscriptionPlan,
    SubscriptionStatus,
    Tenant,
    TenantStatus,
)
from app.schemas.tenant import TenantCreate, TenantUpdate


async def list_plans(session: AsyncSession) -> list[SubscriptionPlan]:
    rows = (await session.execute(select(SubscriptionPlan).order_by(SubscriptionPlan.id))).scalars().all()
    return list(rows)


async def get_plan_by_code(session: AsyncSession, code: str) -> SubscriptionPlan:
    plan = (await session.execute(select(SubscriptionPlan).where(SubscriptionPlan.code == code))).scalar_one_or_none()
    if plan is None or not plan.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Plan '{code}' not found")
    return plan


async def list_tenants(
    session: AsyncSession,
    *,
    status_filter: Optional[TenantStatus] = None,
    search: Optional[str] = None,
) -> list[Tenant]:
    stmt = select(Tenant).order_by(Tenant.created_at.desc())
    if status_filter is not None:
        stmt = stmt.where(Tenant.status == status_filter)
    if search:
        like = f"%{search.lower()}%"
        stmt = stmt.where(
            (func.lower(Tenant.school_name).like(like))
            | (func.lower(Tenant.subdomain).like(like))
            | (func.lower(Tenant.school_code).like(like))
        )
    return list((await session.execute(stmt)).scalars().all())


async def get_tenant(session: AsyncSession, tenant_id: int) -> Tenant:
    tenant = (await session.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return tenant


async def get_tenant_by_subdomain(session: AsyncSession, subdomain: str) -> Tenant:
    tenant = (
        await session.execute(select(Tenant).where(Tenant.subdomain == subdomain))
    ).scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return tenant


async def create_tenant(session: AsyncSession, payload: TenantCreate) -> Tenant:
    plan = await get_plan_by_code(session, payload.plan_code)

    # Reject duplicates up-front for nicer 4xx responses.
    dup = (
        await session.execute(
            select(Tenant.id).where(
                (Tenant.subdomain == payload.subdomain) | (Tenant.school_code == payload.school_code)
            )
        )
    ).first()
    if dup:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Subdomain or school_code already in use",
        )

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    trial_end = now + timedelta(days=settings.TRIAL_PERIOD_DAYS)

    tenant = Tenant(
        school_name=payload.school_name,
        school_code=payload.school_code,
        subdomain=payload.subdomain.lower(),
        affiliation_board=payload.affiliation_board,
        school_type=payload.school_type,
        medium=payload.medium,
        address=payload.address,
        city=payload.city,
        state=payload.state,
        pincode=payload.pincode,
        phone=payload.phone,
        email=payload.email,
        timezone=payload.timezone,
        primary_color=payload.primary_color,
        secondary_color=payload.secondary_color,
        plan_id=plan.id,
        subscription_start=now,
        subscription_end=trial_end,
        student_limit=plan.student_limit or settings.DEFAULT_TENANT_LIMIT_STUDENTS,
        teacher_limit=plan.teacher_limit or 50,
        storage_limit_mb=(plan.storage_gb or 5) * 1024,
        status=TenantStatus.TRIAL,
        modules_enabled=list(plan.modules_included or []),
    )
    session.add(tenant)
    await session.flush()  # populate tenant.id

    sub = Subscription(
        tenant_id=tenant.id,
        plan_id=plan.id,
        start_date=now,
        end_date=trial_end,
        billing_cycle=BillingCycle.MONTHLY,
        status=SubscriptionStatus.ACTIVE,
        auto_renew=True,
        amount=plan.monthly_price,
    )
    session.add(sub)

    await session.commit()
    await session.refresh(tenant)

    # Materialize the per-tenant upload tree so the first file upload doesn't 500.
    ensure_tenant_dirs(tenant.id)

    # Roles + permissions used to appear only on the next API restart,
    # so a fresh school couldn't get users until then. Seed them now.
    from app.services.seed import seed_rbac_for_tenant

    await seed_rbac_for_tenant(session, tenant.id)
    if payload.admin is not None:
        await set_school_admin(
            session,
            tenant.id,
            full_name=payload.admin.full_name,
            email=payload.admin.email,
            password=payload.admin.password,
        )
    await session.refresh(tenant)
    return tenant


SCHOOL_ADMIN_ROLE = "school_admin"


async def list_school_admins(session: AsyncSession, tenant_id: int) -> list[User]:
    """Users holding the school_admin role in this school."""
    stmt = (
        select(User)
        .join(UserRole, UserRole.user_id == User.id)
        .join(Role, Role.id == UserRole.role_id)
        .where(User.tenant_id == tenant_id, Role.code == SCHOOL_ADMIN_ROLE)
        .order_by(User.id)
    )
    return list((await session.execute(stmt)).scalars().unique().all())


async def set_school_admin(
    session: AsyncSession,
    tenant_id: int,
    *,
    full_name: str,
    email: str,
    password: str,
) -> User:
    """Create the school's admin login, or — if a user with this email
    already exists in the school — reset its name and password and make
    sure it is an active school admin."""
    from app.core.admin_pages import default_pages_for_roles

    email = email.strip().lower()
    role = (
        await session.execute(
            select(Role).where(Role.tenant_id == tenant_id, Role.code == SCHOOL_ADMIN_ROLE)
        )
    ).scalar_one_or_none()
    if role is None:
        from app.services.seed import seed_rbac_for_tenant

        await seed_rbac_for_tenant(session, tenant_id)
        role = (
            await session.execute(
                select(Role).where(Role.tenant_id == tenant_id, Role.code == SCHOOL_ADMIN_ROLE)
            )
        ).scalar_one()

    user = (
        await session.execute(
            select(User).where(User.tenant_id == tenant_id, User.email == email)
        )
    ).scalar_one_or_none()
    if user is None:
        user = User(
            tenant_id=tenant_id,
            full_name=full_name,
            email=email,
            password_hash=hash_password(password),
            is_active=True,
            is_email_verified=True,
            granted_admin_pages=default_pages_for_roles([SCHOOL_ADMIN_ROLE]),
        )
        session.add(user)
        await session.flush()
    else:
        user.full_name = full_name
        user.password_hash = hash_password(password)
        user.is_active = True
        user.failed_login_count = 0

    has_role = (
        await session.execute(
            select(UserRole.id).where(UserRole.user_id == user.id, UserRole.role_id == role.id)
        )
    ).first()
    if not has_role:
        session.add(UserRole(tenant_id=tenant_id, user_id=user.id, role_id=role.id))

    await session.commit()
    await session.refresh(user)
    return user


async def update_tenant(session: AsyncSession, tenant_id: int, payload: TenantUpdate) -> Tenant:
    tenant = await get_tenant(session, tenant_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(tenant, field, value)
    await session.commit()
    await session.refresh(tenant)
    return tenant


async def set_status(session: AsyncSession, tenant_id: int, new_status: TenantStatus) -> Tenant:
    tenant = await get_tenant(session, tenant_id)
    tenant.status = new_status
    await session.commit()
    await session.refresh(tenant)
    return tenant


async def extend_trial(session: AsyncSession, tenant_id: int, days: int) -> Tenant:
    tenant = await get_tenant(session, tenant_id)
    base = tenant.subscription_end or datetime.now(timezone.utc).replace(tzinfo=None)
    tenant.subscription_end = base + timedelta(days=days)
    if tenant.status == TenantStatus.SUSPENDED:
        tenant.status = TenantStatus.TRIAL
    await session.commit()
    await session.refresh(tenant)
    return tenant


async def change_plan(session: AsyncSession, tenant_id: int, plan_code: str) -> Tenant:
    tenant = await get_tenant(session, tenant_id)
    plan = await get_plan_by_code(session, plan_code)
    tenant.plan_id = plan.id
    tenant.student_limit = plan.student_limit or settings.DEFAULT_TENANT_LIMIT_STUDENTS
    tenant.teacher_limit = plan.teacher_limit or 50
    tenant.storage_limit_mb = (plan.storage_gb or 5) * 1024
    tenant.modules_enabled = list(plan.modules_included or [])
    if tenant.status == TenantStatus.TRIAL:
        tenant.status = TenantStatus.ACTIVE
    await session.commit()
    await session.refresh(tenant)
    return tenant


async def count_users(session: AsyncSession, tenant_id: int) -> int:
    from app.models.auth import User

    return int(
        (
            await session.execute(
                select(func.count(User.id)).where(User.tenant_id == tenant_id)
            )
        ).scalar_one()
    )


async def collect_health(session: AsyncSession, tenant_id: int) -> dict:
    tenant = await get_tenant(session, tenant_id)
    used_mb = get_tenant_storage_used_mb(tenant_id)
    pct = (used_mb / tenant.storage_limit_mb * 100) if tenant.storage_limit_mb else 0.0
    return {
        "tenant_id": tenant.id,
        "subdomain": tenant.subdomain,
        "status": tenant.status,
        "storage_used_mb": round(used_mb, 2),
        "storage_limit_mb": tenant.storage_limit_mb,
        "storage_used_pct": round(pct, 2),
        "student_limit": tenant.student_limit,
        "teacher_limit": tenant.teacher_limit,
        "last_active_at": None,
    }


async def assert_storage_room(session: AsyncSession, tenant_id: int, incoming_bytes: int) -> None:
    """Raise 413 if the upload would push the tenant over its storage cap."""
    tenant = await get_tenant(session, tenant_id)
    used_mb = get_tenant_storage_used_mb(tenant_id)
    incoming_mb = incoming_bytes / (1024 * 1024)
    if used_mb + incoming_mb > tenant.storage_limit_mb:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"Storage limit reached: {used_mb:.1f}MB used of {tenant.storage_limit_mb}MB. "
                "Upgrade the plan to add headroom."
            ),
        )


def applicable_codes(plans: Iterable[SubscriptionPlan]) -> list[str]:
    return [p.code for p in plans if p.is_active]
