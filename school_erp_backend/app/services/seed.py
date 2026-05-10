"""Idempotent seed data: subscription plans + a demo tenant.

Run via ``python -m app.services.seed`` after ``alembic upgrade head``.
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.tenant import SubscriptionPlan, Tenant
from app.schemas.tenant import TenantCreate
from app.services.tenants import create_tenant

_PLANS = [
    {
        "code": "basic",
        "name": "Basic",
        "monthly_price": 15.0,
        "annual_price": 150.0,
        "student_limit": 200,
        "teacher_limit": 25,
        "storage_gb": 5,
        "sms_quota": 500,
        "modules_included": ["sis", "attendance", "communication", "fees"],
    },
    {
        "code": "standard",
        "name": "Standard",
        "monthly_price": 25.0,
        "annual_price": 250.0,
        "student_limit": 1000,
        "teacher_limit": 100,
        "storage_gb": 25,
        "sms_quota": 5000,
        "modules_included": [
            "sis", "attendance", "communication", "fees",
            "exams", "report_cards", "transport",
        ],
    },
    {
        "code": "premium",
        "name": "Premium",
        "monthly_price": 40.0,
        "annual_price": 400.0,
        "student_limit": 0,  # unlimited
        "teacher_limit": 0,
        "storage_gb": 100,
        "sms_quota": 25000,
        "modules_included": [
            "sis", "attendance", "communication", "fees",
            "exams", "report_cards", "transport", "library", "hostel", "analytics",
        ],
    },
]


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


async def seed_demo_tenant(session: AsyncSession) -> int | None:
    existing = (
        await session.execute(select(Tenant.id).where(Tenant.subdomain == "demo"))
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    payload = TenantCreate(
        school_name="Demo Public School",
        school_code="DEMO-001",
        subdomain="demo",
        plan_code="standard",
        affiliation_board="CBSE",
        medium="English",
        city="Mumbai",
        state="Maharashtra",
        timezone="Asia/Kolkata",
    )
    tenant = await create_tenant(session, payload)
    return tenant.id


async def run_all() -> None:
    async with AsyncSessionLocal() as session:
        plans_created = await seed_plans(session)
        tenant_id = await seed_demo_tenant(session)
    print(f"seed: plans_created={plans_created}, demo_tenant_id={tenant_id}")


if __name__ == "__main__":
    asyncio.run(run_all())
