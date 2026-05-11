"""Idempotent seed data:
- subscription plans
- a platform tenant (tenant_id=1) for super admins
- per-tenant role + permission catalogue
- a default super-admin user
- a demo school tenant
- a demo school admin user
- one demo user *per role* on the demo school so QA can sign into the
  mobile app as principal / class_teacher / accountant / parent / student
  etc. without provisioning each one by hand.

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


# ---- Demo users for every role ---------------------------------------------


# Each entry is (role_code, full_name, email_local_part). The email becomes
# `<email_local_part>@demo.school`. All staff accounts share the same password
# so QA can rotate roles quickly; parent + student get their own to make the
# distinction obvious in screenshots.
_DEMO_STAFF_ROLES = [
    ("principal", "Demo Principal", "principal"),
    ("vice_principal", "Demo Vice-Principal", "vice.principal"),
    ("coordinator", "Demo Coordinator", "coordinator"),
    ("class_teacher", "Demo Class Teacher", "class.teacher"),
    ("subject_teacher", "Demo Subject Teacher", "subject.teacher"),
    ("accountant", "Demo Accountant", "accountant"),
    ("librarian", "Demo Librarian", "librarian"),
    ("transport_manager", "Demo Transport Manager", "transport"),
    ("hostel_warden", "Demo Hostel Warden", "warden"),
    ("office_staff", "Demo Office Staff", "office"),
]
DEFAULT_STAFF_PASSWORD = os.getenv("SEED_STAFF_PASSWORD", "Demo@123")
DEFAULT_PARENT_PASSWORD = os.getenv("SEED_PARENT_PASSWORD", "Parent@123")
DEFAULT_STUDENT_PASSWORD = os.getenv("SEED_STUDENT_PASSWORD", "Student@123")
DEMO_PARENT_EMAIL = os.getenv("SEED_PARENT_EMAIL", "parent@demo.school")
DEMO_PARENT_PHONE = os.getenv("SEED_PARENT_PHONE", "+919900099000")
DEMO_STUDENT_EMAIL = os.getenv("SEED_STUDENT_EMAIL", "student@demo.school")


async def _ensure_demo_class_section(
    session: AsyncSession, tenant_id: int
) -> tuple[int, int]:
    """Demo class + section. Both idempotent on (tenant, code/name)."""
    from app.models.academic import ClassDef, Section

    cls = (
        await session.execute(
            select(ClassDef).where(
                ClassDef.tenant_id == tenant_id, ClassDef.code == "5"
            )
        )
    ).scalar_one_or_none()
    if cls is None:
        cls = ClassDef(
            tenant_id=tenant_id, code="5", name="Class 5",
            stage="primary", sequence=5,
        )
        session.add(cls)
        await session.flush()

    sec = (
        await session.execute(
            select(Section).where(
                Section.tenant_id == tenant_id,
                Section.class_def_id == cls.id,
                Section.name == "A",
            )
        )
    ).scalar_one_or_none()
    if sec is None:
        sec = Section(tenant_id=tenant_id, class_def_id=cls.id, name="A")
        session.add(sec)
        await session.flush()
    await session.commit()
    return cls.id, sec.id


async def seed_demo_school_users(session: AsyncSession, tenant_id: int) -> dict:
    """Provision one user per role on the demo school + a real
    parent/student pair linked via the Phase 8 autolink path. Idempotent
    on every step.
    """
    from app.models.parent import Student
    from app.schemas.sis import StudentCreate
    from app.services.sis import admit_student

    # --- staff (10 roles) -----------------------------------------------
    staff_creds: list[tuple[str, str, str, str]] = []
    for role_code, full_name, local in _DEMO_STAFF_ROLES:
        email = f"{local}@demo.school"
        await _ensure_user(
            session,
            tenant_id=tenant_id,
            email=email,
            full_name=full_name,
            password=DEFAULT_STAFF_PASSWORD,
            role_codes=[role_code],
        )
        staff_creds.append((role_code, full_name, email, DEFAULT_STAFF_PASSWORD))

    # --- demo class + section -------------------------------------------
    cls_id, sec_id = await _ensure_demo_class_section(session, tenant_id)

    # --- demo student + autolinked parent -------------------------------
    student = (
        await session.execute(
            select(Student).where(
                Student.tenant_id == tenant_id, Student.parent_email == DEMO_PARENT_EMAIL,
            )
        )
    ).scalar_one_or_none()
    if student is None:
        student = await admit_student(
            session,
            tenant_id,
            StudentCreate(
                full_name="Demo Student",
                class_def_id=cls_id,
                section_id=sec_id,
                parent_phone=DEMO_PARENT_PHONE,
                parent_email=DEMO_PARENT_EMAIL,
                father_name="Demo Father",
            ),
        )

    # Parent user was auto-created by admit_student but with a NULL password
    # hash (Phase 12 OTP login is the intended flow). Set a known password
    # so mobile QA can sign in.
    parent_user = (
        await session.execute(
            select(User).where(
                User.tenant_id == tenant_id, User.email == DEMO_PARENT_EMAIL
            )
        )
    ).scalar_one_or_none()
    if parent_user is not None:
        parent_user.password_hash = hash_password(DEFAULT_PARENT_PASSWORD)
        parent_user.is_active = True
        parent_user.is_email_verified = True

    # --- demo student user (separate login for the kid) -----------------
    await _ensure_user(
        session,
        tenant_id=tenant_id,
        email=DEMO_STUDENT_EMAIL,
        full_name="Demo Student",
        password=DEFAULT_STUDENT_PASSWORD,
        role_codes=["student"],
    )

    await session.commit()

    return {
        "staff": staff_creds,
        "parent": (DEMO_PARENT_EMAIL, DEFAULT_PARENT_PASSWORD, student.id if student else None),
        "student": (DEMO_STUDENT_EMAIL, DEFAULT_STUDENT_PASSWORD),
    }


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
        demo_users = await seed_demo_school_users(session, demo_id)

    # Pretty-print every credential at the end so QA can copy-paste them
    # into the mobile app without grepping the source.
    print("seed: ok")
    print(f"  tenant: platform   id={platform_id}   subdomain=platform")
    print(f"  tenant: demo       id={demo_id}   subdomain=demo")
    print()
    def _row(role: str, sub: str, email: str, pwd: str, extra: str = "") -> str:
        return (
            f"    {f'[{role}]':<20} ({sub:<8}) "
            f"{email:<32} {pwd}{extra}"
        )

    print("  Sign-in credentials:")
    print(_row("super_admin", PLATFORM_TENANT_SUBDOMAIN,
               DEFAULT_SUPER_ADMIN_EMAIL, DEFAULT_SUPER_ADMIN_PASSWORD))
    print(_row("school_admin", "demo",
               DEFAULT_SCHOOL_ADMIN_EMAIL, DEFAULT_SCHOOL_ADMIN_PASSWORD))
    for role, _, email, pwd in demo_users["staff"]:
        print(_row(role, "demo", email, pwd))
    p_email, p_pwd, p_student_id = demo_users["parent"]
    print(_row("parent", "demo", p_email, p_pwd,
               extra=f"   -> child student_id={p_student_id}"))
    s_email, s_pwd = demo_users["student"]
    print(_row("student", "demo", s_email, s_pwd))


if __name__ == "__main__":
    asyncio.run(run_all())
