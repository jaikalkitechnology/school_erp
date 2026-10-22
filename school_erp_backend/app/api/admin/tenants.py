"""Super Admin tenant management endpoints (Phase 1+3).

All routes are gated behind ``require_super_admin`` and use the unfiltered
``platform_session`` (the super admin operates across tenants).
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.auth_deps import AuthPrincipal, require_super_admin
from app.core.file_storage import save_upload
from app.core.security import create_access_token
from app.core.tenant_session import platform_session
from app.models.tenant import TenantStatus
from app.schemas.tenant import (
    AnalyticsOverview,
    AuditLogRead,
    ImpersonationToken,
    PlanChange,
    SchoolAdminRead,
    SchoolAdminSet,
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
    list_school_admins,
    list_tenants,
    set_school_admin,
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
        # Never the password.
        metadata={
            "plan_code": payload.plan_code,
            "admin_email": payload.admin.email if payload.admin else None,
        },
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


@router.get("/{tenant_id}/admins", response_model=list[SchoolAdminRead])
async def list_admins(tenant_id: int, session: AsyncSession = Depends(platform_session)):
    """The school's admin logins (users with the school_admin role)."""
    await get_tenant(session, tenant_id)
    return await list_school_admins(session, tenant_id)


@router.put("/{tenant_id}/admin", response_model=SchoolAdminRead)
async def set_admin(
    tenant_id: int,
    payload: SchoolAdminSet,
    request: Request,
    session: AsyncSession = Depends(platform_session),
    principal: AuthPrincipal = Depends(require_super_admin()),
):
    """Set a school admin's login: creates it, or for an email that
    already exists in the school, resets its name and password."""
    tenant = await get_tenant(session, tenant_id)
    user = await set_school_admin(
        session,
        tenant_id,
        full_name=payload.full_name,
        email=payload.email,
        password=payload.password,
    )
    await audit.record(
        session,
        principal=principal,
        action="tenant.admin_set",
        target_type="user",
        target_id=user.id,
        summary=f"Set admin login {user.email} for {tenant.school_name}",
        request=request,
        tenant_id_override=tenant_id,
    )
    return user


@router.post("/{tenant_id}/logo", response_model=TenantRead)
async def upload_logo(
    tenant_id: int,
    request: Request,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(platform_session),
    principal: AuthPrincipal = Depends(require_super_admin()),
):
    """Set a school's logo / profile image (PNG, JPG or SVG). The file is
    stored in that school's own upload folder — the only place its staff
    can read it from — and becomes the tenant's logo_url (shown in the
    school-admin sidebar and on printed ID cards)."""
    tenant = await get_tenant(session, tenant_id)
    rel, _size = await save_upload(file, tenant_id, "school", "branding")
    tenant.logo_url = rel
    await session.commit()
    await session.refresh(tenant)
    await audit.record(
        session,
        principal=principal,
        action="tenant.logo",
        target_type="tenant",
        target_id=tenant_id,
        summary=f"Set logo for {tenant.school_name}",
        request=request,
        tenant_id_override=tenant_id,
    )
    return await get_tenant(session, tenant_id)


@router.get("/{tenant_id}/logo")
async def get_logo(tenant_id: int, session: AsyncSession = Depends(platform_session)):
    """Serve a school's logo to the super admin. /v1/uploads only reads
    from the caller's own tenant folder, so the Schools list needs this
    to show other schools' images."""
    tenant = await get_tenant(session, tenant_id)
    if not tenant.logo_url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No logo")
    base = (Path(settings.UPLOAD_DIR) / f"tenant_{tenant_id}").resolve()
    prefix = f"tenant_{tenant_id}/"
    rel = tenant.logo_url[len(prefix):] if tenant.logo_url.startswith(prefix) else tenant.logo_url
    target = (base / rel).resolve()
    if not str(target).startswith(str(base) + "/") or not target.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Logo file not found")
    return FileResponse(target)


@router.delete("/{tenant_id}", response_model=TenantRead)
async def delete_one(
    tenant_id: int,
    request: Request,
    session: AsyncSession = Depends(platform_session),
    principal: AuthPrincipal = Depends(require_super_admin()),
):
    """Delete a school from the platform. This is a soft delete: the tenant
    moves to CANCELLED, which blocks every login and API call for it, but
    its students, fees and other records are kept (a hard delete would
    orphan rows in tables that have no FK cascade). Cancelled schools
    can't be re-activated."""
    tenant = await get_tenant(session, tenant_id)
    if tenant.status != TenantStatus.CANCELLED:
        tenant = await set_status(session, tenant_id, TenantStatus.CANCELLED)
        await audit.record(
            session,
            principal=principal,
            action="tenant.delete",
            target_type="tenant",
            target_id=tenant_id,
            summary=f"Deleted {tenant.school_name} ({tenant.subdomain})",
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
