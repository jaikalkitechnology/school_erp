"""Idempotent seed data:
- subscription plans
- a platform tenant (tenant_id=1) for super admins
- per-tenant role + permission catalogue
- a default super-admin user
- a demo school tenant
- a demo school admin user

Usage:
    python -m app.services.seed
"""

from __future__ import annotations

import asyncio
import os
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac_catalog import PERMISSIONS, ROLES, expand_grants
from app.core.security import hash_password
from app.database import AsyncSessionLocal
from app.models.auth import Permission, Role, RolePermission, User, UserRole
from app.models.tenant import SubscriptionPlan, Tenant, TenantStatus
from app.schemas.tenant import TenantCreate
from app.services.tenants import create_tenant

PLATFORM_TENANT_SUBDOMAIN = "platform"
DEFAULT_SUPER_ADMIN_EMAIL = os.getenv("SEED_SUPER_ADMIN_EMAIL", "admin@jaikalki.com")
DEFAULT_SUPER_ADMIN_PASSWORD = os.getenv("SEED_SUPER_ADMIN_PASSWORD", "Admin@123")
DEFAULT_SCHOOL_ADMIN_EMAIL = os.getenv("SEED_SCHOOL_ADMIN_EMAIL", "admin@demo.school")
DEFAULT_SCHOOL_ADMIN_PASSWORD = os.getenv("SEED_SCHOOL_ADMIN_PASSWORD", "School@123")


_PLANS = [
    {
        "code": "basic", "name": "Basic",
        "monthly_price": 15.0, "annual_price": 150.0,
        "student_limit": 200, "teacher_limit": 25,
        "storage_gb": 5, "sms_quota": 500,
        "modules_included": ["sis", "attendance", "communication", "fees"],
    },
    {
        "code": "standard", "name": "Standard",
        "monthly_price": 25.0, "annual_price": 250.0,
        "student_limit": 1000, "teacher_limit": 100,
        "storage_gb": 25, "sms_quota": 5000,
        "modules_included": [
            "sis", "attendance", "communication", "fees",
            "exams", "report_cards", "transport",
        ],
    },
    {
        "code": "premium", "name": "Premium",
        "monthly_price": 40.0, "annual_price": 400.0,
        "student_limit": 0, "teacher_limit": 0,
        "storage_gb": 100, "sms_quota": 25000,
        "modules_included": [
            "sis", "attendance", "communication", "fees",
            "exams", "report_cards", "transport", "library", "hostel", "analytics",
        ],
    },
]


# ---- helpers ----------------------------------------------------------------


async def seed_plans(session: AsyncSession) -> int:
    existing = {p.code for p in (await session.execute(select(SubscriptionPlan))).scalars().all()}
    created = 0
    for spec in _PLANS:
        if spec["code"] in existing:
            continue
        session.add(SubscriptionPlan(is_active=True, features_json={}, **spec))
        created += 1
    if created:
        await session.commit()
    return created


async def seed_rbac_for_tenant(session: AsyncSession, tenant_id: int) -> tuple[int, int]:
    """Seed roles + permissions + grants for one tenant. Idempotent."""
    # --- permissions
    existing_perm_codes = {
        c
        for (c,) in (
            await session.execute(
                select(Permission.code).where(Permission.tenant_id == tenant_id)
            )
        ).all()
    }
    perms_added = 0
    for spec in PERMISSIONS:
        if spec.code in existing_perm_codes:
            continue
        session.add(
            Permission(
                tenant_id=tenant_id,
                code=spec.code,
                name=spec.name,
                category=spec.category,
                description=spec.description,
            )
        )
        perms_added += 1
    if perms_added:
        await session.flush()

    # --- roles + grants
    perms_by_code = {
        p.code: p
        for p in (
            await session.execute(select(Permission).where(Permission.tenant_id == tenant_id))
        ).scalars().all()
    }

    existing_roles = {
        r.code: r
        for r in (
            await session.execute(select(Role).where(Role.tenant_id == tenant_id))
        ).scalars().all()
    }
    roles_added = 0
    for spec in ROLES:
        role = existing_roles.get(spec.code)
        if role is None:
            role = Role(
                tenant_id=tenant_id,
                code=spec.code,
                name=spec.name,
                description=spec.description,
                level=spec.level,
                is_system=True,
            )
            session.add(role)
            await session.flush()
            roles_added += 1
        else:
            # Refresh the human-readable bits in case the catalogue evolved.
            role.name = spec.name
            role.description = spec.description
            role.level = spec.level

        # Reset grants to match catalogue.
        await session.execute(
            RolePermission.__table__.delete().where(RolePermission.role_id == role.id)
        )
        for code in expand_grants(spec.grants):
            perm = perms_by_code.get(code)
            if perm is None:
                continue
            session.add(RolePermission(tenant_id=tenant_id, role_id=role.id, permission_id=perm.id))

    await session.commit()
    return perms_added, roles_added


async def _ensure_user(
    session: AsyncSession,
    *,
    tenant_id: int,
    email: str,
    full_name: str,
    password: str,
    role_codes: Iterable[str],
) -> User:
    from sqlalchemy.orm import selectinload

    user = (
        await session.execute(
            select(User)
            .options(selectinload(User.role_assignments))
            .where(User.tenant_id == tenant_id, User.email == email)
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
        )
        session.add(user)
        await session.flush()
        existing_role_ids: set[int] = set()
    else:
        existing_role_ids = {ur.role_id for ur in user.role_assignments}

    roles = (
        await session.execute(
            select(Role).where(Role.tenant_id == tenant_id, Role.code.in_(list(role_codes)))
        )
    ).scalars().all()
    for role in roles:
        if role.id in existing_role_ids:
            continue
        session.add(UserRole(tenant_id=tenant_id, user_id=user.id, role_id=role.id))
    await session.commit()
    return user


async def seed_platform_tenant(session: AsyncSession) -> int:
    tenant = (
        await session.execute(
            select(Tenant).where(Tenant.subdomain == PLATFORM_TENANT_SUBDOMAIN)
        )
    ).scalar_one_or_none()
    if tenant is not None:
        return tenant.id

    plan = (
        await session.execute(select(SubscriptionPlan).where(SubscriptionPlan.code == "premium"))
    ).scalar_one()
    tenant = Tenant(
        school_name="Jaikalki Platform",
        school_code="JAIKALKI",
        subdomain=PLATFORM_TENANT_SUBDOMAIN,
        plan_id=plan.id,
        student_limit=0,
        teacher_limit=0,
        storage_limit_mb=0,
        status=TenantStatus.ACTIVE,
    )
    session.add(tenant)
    await session.commit()
    await session.refresh(tenant)
    return tenant.id


async def seed_demo_tenant(session: AsyncSession) -> int:
    tenant = (
        await session.execute(select(Tenant).where(Tenant.subdomain == "demo"))
    ).scalar_one_or_none()
    if tenant is not None:
        return tenant.id

    payload = TenantCreate(
        school_name="Demo Public School",
        school_code="DEMO-001",
        subdomain="demo",
        plan_code="standard",
        affiliation_board="CBSE",
        medium="English",
        city="Mumbai",
        state="Maharashtra",
    )
    tenant = await create_tenant(session, payload)
    return tenant.id


async def run_all() -> None:
    async with AsyncSessionLocal() as session:
        await seed_plans(session)

        from app.services.comms import seed_default_templates as _seed_templates

        platform_id = await seed_platform_tenant(session)
        await seed_rbac_for_tenant(session, platform_id)
        await _seed_templates(session, platform_id)
        await _ensure_user(
            session,
            tenant_id=platform_id,
            email=DEFAULT_SUPER_ADMIN_EMAIL,
            full_name="Jaikalki Super Admin",
            password=DEFAULT_SUPER_ADMIN_PASSWORD,
            role_codes=["super_admin"],
        )

        demo_id = await seed_demo_tenant(session)
        await seed_rbac_for_tenant(session, demo_id)
        await _seed_templates(session, demo_id)
        await _ensure_user(
            session,
            tenant_id=demo_id,
            email=DEFAULT_SCHOOL_ADMIN_EMAIL,
            full_name="Demo School Admin",
            password=DEFAULT_SCHOOL_ADMIN_PASSWORD,
            role_codes=["school_admin"],
        )

    print(
        "seed: ok\n"
        f"  super-admin: tenant_id={platform_id} email={DEFAULT_SUPER_ADMIN_EMAIL} pwd={DEFAULT_SUPER_ADMIN_PASSWORD}\n"
        f"  school-admin (demo subdomain): tenant_id={demo_id} email={DEFAULT_SCHOOL_ADMIN_EMAIL} pwd={DEFAULT_SCHOOL_ADMIN_PASSWORD}"
    )


if __name__ == "__main__":
    asyncio.run(run_all())
