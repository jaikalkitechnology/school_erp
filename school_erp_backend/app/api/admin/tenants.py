"""Super Admin tenant management endpoints.

All routes here use ``platform_session`` (no auto tenant filter) because the
super admin operates across tenants. Phase 2 will gate them with
``require_role("super_admin")``.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import create_access_token
from app.core.tenant import require_platform
from app.core.tenant_session import platform_session
from app.models.tenant import TenantStatus
from app.schemas.tenant import (
    ImpersonationToken,
    SubscriptionPlanRead,
    TenantCreate,
    TenantHealth,
    TenantRead,
    TenantUpdate,
)
from app.services.tenants import (
    collect_health,
    create_tenant,
    get_tenant,
    list_plans,
    list_tenants,
    set_status,
    update_tenant,
)

router = APIRouter(prefix="/tenants", tags=["super-admin"], dependencies=[Depends(require_platform)])


@router.get("", response_model=list[TenantRead])
async def list_all(
    session: AsyncSession = Depends(platform_session),
    status_filter: Optional[TenantStatus] = Query(default=None, alias="status"),
    search: Optional[str] = Query(default=None, max_length=100),
):
    return await list_tenants(session, status_filter=status_filter, search=search)


@router.post("", response_model=TenantRead, status_code=status.HTTP_201_CREATED)
async def create(payload: TenantCreate, session: AsyncSession = Depends(platform_session)):
    return await create_tenant(session, payload)


@router.get("/{tenant_id}", response_model=TenantRead)
async def get_one(tenant_id: int, session: AsyncSession = Depends(platform_session)):
    return await get_tenant(session, tenant_id)


@router.patch("/{tenant_id}", response_model=TenantRead)
async def update_one(
    tenant_id: int,
    payload: TenantUpdate,
    session: AsyncSession = Depends(platform_session),
):
    return await update_tenant(session, tenant_id, payload)


@router.post("/{tenant_id}/suspend", response_model=TenantRead)
async def suspend(tenant_id: int, session: AsyncSession = Depends(platform_session)):
    return await set_status(session, tenant_id, TenantStatus.SUSPENDED)


@router.post("/{tenant_id}/activate", response_model=TenantRead)
async def activate(tenant_id: int, session: AsyncSession = Depends(platform_session)):
    tenant = await get_tenant(session, tenant_id)
    if tenant.status == TenantStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cancelled tenants cannot be re-activated; create a new one",
        )
    return await set_status(session, tenant_id, TenantStatus.ACTIVE)


@router.get("/{tenant_id}/health", response_model=TenantHealth)
async def health(tenant_id: int, session: AsyncSession = Depends(platform_session)):
    return await collect_health(session, tenant_id)


@router.post("/{tenant_id}/impersonate", response_model=ImpersonationToken)
async def impersonate(tenant_id: int, session: AsyncSession = Depends(platform_session)):
    """Mint a short-lived JWT scoped to a tenant for super-admin investigation.

    Phase 2 will add audit logging and require an explicit reason; for now the
    token simply carries ``tenant_id`` and an ``impersonation`` flag.
    """
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
    return ImpersonationToken(
        token=token,
        tenant_id=tenant.id,
        subdomain=tenant.subdomain,
        expires_in_seconds=int(timedelta(minutes=expires_minutes).total_seconds()),
    )


# ----- Plans (read-only here; admin UI in Phase 21 manages these) ------------

plans_router = APIRouter(prefix="/plans", tags=["super-admin"], dependencies=[Depends(require_platform)])


@plans_router.get("", response_model=list[SubscriptionPlanRead])
async def list_plans_route(session: AsyncSession = Depends(platform_session)):
    return await list_plans(session)
