"""Super Admin tenant management endpoints (Phase 1+3).

All routes are gated behind ``require_super_admin`` and use the unfiltered
``platform_session`` (the super admin operates across tenants).
"""

from __future__ import annotations

from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.auth_deps import AuthPrincipal, require_super_admin
from app.core.security import create_access_token
from app.core.tenant_session import platform_session
from app.models.tenant import TenantStatus
from app.schemas.tenant import (
    AnalyticsOverview,
    AuditLogRead,
    ImpersonationToken,
    PlanChange,
    SubscriptionPlanRead,
    SubscriptionPlanUpdate,
    SubscriptionPlanWrite,
    TenantCreate,
    TenantHealth,
    TenantRead,
    TenantUpdate,
    TrialExtension,
)
from app.services import analytics, audit, plans
from app.services.tenants import (
    change_plan,
    collect_health,
    count_users,
    create_tenant,
    extend_trial,
    get_tenant,
    list_plans,
    list_tenants,
    set_status,
    update_tenant,
)

router = APIRouter(
    prefix="/tenants",
    tags=["super-admin"],
    dependencies=[Depends(require_super_admin())],
)


@router.get("", response_model=list[TenantRead])
async def list_all(
    session: AsyncSession = Depends(platform_session),
    status_filter: Optional[TenantStatus] = Query(default=None, alias="status"),
    search: Optional[str] = Query(default=None, max_length=100),
):
    return await list_tenants(session, status_filter=status_filter, search=search)


@router.post("", response_model=TenantRead, status_code=status.HTTP_201_CREATED)
async def create(
    payload: TenantCreate,
    request: Request,
    session: AsyncSession = Depends(platform_session),
    principal: AuthPrincipal = Depends(require_super_admin()),
):
    tenant = await create_tenant(session, payload)
    await audit.record(
        session,
        principal=principal,
        action="tenant.create",
        target_type="tenant",
        target_id=tenant.id,
        summary=f"Onboarded {tenant.school_name} ({tenant.subdomain})",
        metadata={"plan_code": payload.plan_code},
        request=request,
        tenant_id_override=tenant.id,
    )
    return tenant


@router.get("/{tenant_id}", response_model=TenantRead)
async def get_one(tenant_id: int, session: AsyncSession = Depends(platform_session)):
    return await get_tenant(session, tenant_id)


@router.patch("/{tenant_id}", response_model=TenantRead)
async def update_one(
    tenant_id: int,
    payload: TenantUpdate,
    request: Request,
    session: AsyncSession = Depends(platform_session),
    principal: AuthPrincipal = Depends(require_super_admin()),
):
    tenant = await update_tenant(session, tenant_id, payload)
    await audit.record(
        session,
        principal=principal,
        action="tenant.update",
        target_type="tenant",
        target_id=tenant_id,
        summary=f"Updated {tenant.school_name}",
        metadata=payload.model_dump(exclude_unset=True),
        request=request,
        tenant_id_override=tenant_id,
    )
    return tenant


@router.post("/{tenant_id}/suspend", response_model=TenantRead)
async def suspend(
    tenant_id: int,
    request: Request,
    session: AsyncSession = Depends(platform_session),
    principal: AuthPrincipal = Depends(require_super_admin()),
):
    tenant = await set_status(session, tenant_id, TenantStatus.SUSPENDED)
    await audit.record(
        session,
        principal=principal,
        action="tenant.suspend",
        target_type="tenant",
        target_id=tenant_id,
        summary=f"Suspended {tenant.school_name}",
        request=request,
        tenant_id_override=tenant_id,
    )
    return tenant


@router.post("/{tenant_id}/activate", response_model=TenantRead)
async def activate(
    tenant_id: int,
    request: Request,
    session: AsyncSession = Depends(platform_session),
    principal: AuthPrincipal = Depends(require_super_admin()),
):
    tenant = await get_tenant(session, tenant_id)
    if tenant.status == TenantStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cancelled tenants cannot be re-activated; create a new one",
        )
    tenant = await set_status(session, tenant_id, TenantStatus.ACTIVE)
    await audit.record(
        session,
        principal=principal,
        action="tenant.activate",
        target_type="tenant",
        target_id=tenant_id,
        summary=f"Activated {tenant.school_name}",
        request=request,
        tenant_id_override=tenant_id,
    )
    return tenant


@router.post("/{tenant_id}/extend-trial", response_model=TenantRead)
async def extend_trial_route(
    tenant_id: int,
    payload: TrialExtension,
    request: Request,
    session: AsyncSession = Depends(platform_session),
    principal: AuthPrincipal = Depends(require_super_admin()),
):
    tenant = await extend_trial(session, tenant_id, payload.days)
    await audit.record(
        session,
        principal=principal,
        action="tenant.trial_extend",
        target_type="tenant",
        target_id=tenant_id,
        summary=f"Extended trial by {payload.days} days",
        metadata={"days": payload.days, "reason": payload.reason},
        request=request,
        tenant_id_override=tenant_id,
    )
    return tenant


@router.post("/{tenant_id}/change-plan", response_model=TenantRead)
async def change_plan_route(
    tenant_id: int,
    payload: PlanChange,
    request: Request,
    session: AsyncSession = Depends(platform_session),
    principal: AuthPrincipal = Depends(require_super_admin()),
):
    tenant = await change_plan(session, tenant_id, payload.plan_code)
    await audit.record(
        session,
        principal=principal,
        action="tenant.plan_change",
        target_type="tenant",
        target_id=tenant_id,
        summary=f"Plan -> {payload.plan_code}",
        metadata={"plan_code": payload.plan_code},
        request=request,
        tenant_id_override=tenant_id,
    )
    return tenant


@router.get("/{tenant_id}/health", response_model=TenantHealth)
async def health(tenant_id: int, session: AsyncSession = Depends(platform_session)):
    return await collect_health(session, tenant_id)


@router.get("/{tenant_id}/usage")
async def usage(tenant_id: int, session: AsyncSession = Depends(platform_session)):
    """Detail bundle the React tenant page renders."""
    health_data = await collect_health(session, tenant_id)
    users = await count_users(session, tenant_id)
    return {**health_data, "users_count": users}


@router.get("/{tenant_id}/audit", response_model=list[AuditLogRead])
async def tenant_audit(
    tenant_id: int,
    session: AsyncSession = Depends(platform_session),
    limit: int = Query(default=50, ge=1, le=500),
):
    return await audit.list_logs(session, tenant_id=tenant_id, limit=limit)


@router.post("/{tenant_id}/impersonate", response_model=ImpersonationToken)
async def impersonate(
    tenant_id: int,
    request: Request,
    session: AsyncSession = Depends(platform_session),
    principal: AuthPrincipal = Depends(require_super_admin()),
):
    tenant = await get_tenant(session, tenant_id)
    expires_minutes = 30
    token = create_access_token(
        {
            "sub": "super_admin_impersonation",
            "tenant_id": tenant.id,
            "subdomain": tenant.subdomain,
            "impersonation": True,
        },
        expires_minutes=expires_minutes,
    )
    await audit.record(
        session,
        principal=principal,
        action="tenant.impersonate",
        target_type="tenant",
        target_id=tenant_id,
        summary=f"Impersonated {tenant.school_name}",
        request=request,
        tenant_id_override=tenant_id,
    )
    return ImpersonationToken(
        token=token,
        tenant_id=tenant.id,
        subdomain=tenant.subdomain,
        expires_in_seconds=int(timedelta(minutes=expires_minutes).total_seconds()),
    )


# ----- Plans (CRUD) ----------------------------------------------------------

plans_router = APIRouter(
    prefix="/plans",
    tags=["super-admin"],
    dependencies=[Depends(require_super_admin())],
)


@plans_router.get("", response_model=list[SubscriptionPlanRead])
async def list_plans_route(session: AsyncSession = Depends(platform_session)):
    return await plans.list_all(session)


@plans_router.post("", response_model=SubscriptionPlanRead, status_code=status.HTTP_201_CREATED)
async def create_plan(
    payload: SubscriptionPlanWrite,
    request: Request,
    session: AsyncSession = Depends(platform_session),
    principal: AuthPrincipal = Depends(require_super_admin()),
):
    plan = await plans.create(session, payload)
    await audit.record(
        session,
        principal=principal,
        action="plan.create",
        target_type="plan",
        target_id=plan.id,
        summary=f"Created plan {plan.code}",
        request=request,
    )
    return plan


@plans_router.patch("/{plan_id}", response_model=SubscriptionPlanRead)
async def update_plan(
    plan_id: int,
    payload: SubscriptionPlanUpdate,
    request: Request,
    session: AsyncSession = Depends(platform_session),
    principal: AuthPrincipal = Depends(require_super_admin()),
):
    plan = await plans.update(session, plan_id, payload)
    await audit.record(
        session,
        principal=principal,
        action="plan.update",
        target_type="plan",
        target_id=plan_id,
        summary=f"Updated plan {plan.code}",
        metadata=payload.model_dump(exclude_unset=True),
        request=request,
    )
    return plan


# ----- Analytics + audit feed -----------------------------------------------

extras_router = APIRouter(
    prefix="",
    tags=["super-admin"],
    dependencies=[Depends(require_super_admin())],
)


@extras_router.get("/analytics/overview", response_model=AnalyticsOverview)
async def analytics_overview(session: AsyncSession = Depends(platform_session)):
    return await analytics.overview(session)


@extras_router.get("/audit", response_model=list[AuditLogRead])
async def global_audit(
    session: AsyncSession = Depends(platform_session),
    limit: int = Query(default=100, ge=1, le=500),
    action_prefix: Optional[str] = Query(default=None),
):
    return await audit.list_logs(session, limit=limit, action_prefix=action_prefix)
