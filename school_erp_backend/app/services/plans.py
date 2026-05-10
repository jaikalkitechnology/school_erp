"""Subscription plan CRUD."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import SubscriptionPlan
from app.schemas.tenant import SubscriptionPlanUpdate, SubscriptionPlanWrite


async def list_all(session: AsyncSession) -> list[SubscriptionPlan]:
    return list(
        (await session.execute(select(SubscriptionPlan).order_by(SubscriptionPlan.id))).scalars().all()
    )


async def get_by_id(session: AsyncSession, plan_id: int) -> SubscriptionPlan:
    plan = (
        await session.execute(select(SubscriptionPlan).where(SubscriptionPlan.id == plan_id))
    ).scalar_one_or_none()
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    return plan


async def create(session: AsyncSession, payload: SubscriptionPlanWrite) -> SubscriptionPlan:
    dup = (
        await session.execute(select(SubscriptionPlan).where(SubscriptionPlan.code == payload.code))
    ).scalar_one_or_none()
    if dup is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Plan code already exists")
    plan = SubscriptionPlan(features_json={}, **payload.model_dump())
    session.add(plan)
    await session.commit()
    await session.refresh(plan)
    return plan


async def update(session: AsyncSession, plan_id: int, payload: SubscriptionPlanUpdate) -> SubscriptionPlan:
    plan = await get_by_id(session, plan_id)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(plan, k, v)
    await session.commit()
    await session.refresh(plan)
    return plan


async def disable(session: AsyncSession, plan_id: int) -> SubscriptionPlan:
    return await update(session, plan_id, SubscriptionPlanUpdate(is_active=False))
