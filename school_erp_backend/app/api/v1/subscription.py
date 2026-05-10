"""Tenant-facing subscription endpoint (Phase 21).

The school admin can see their plan + invoice history; super admin still
holds the keys for plan changes / payment recording (those live under
/admin/billing).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import AuthPrincipal, require_roles
from app.core.tenant_session import platform_session
from app.schemas.billing import SubscriptionStatus
from app.services.billing import tenant_subscription


_school_admin = require_roles("school_admin", "principal", "vice_principal", "accountant")


router = APIRouter(
    prefix="/school-admin/subscription",
    tags=["school-admin"],
    dependencies=[Depends(_school_admin)],
)


@router.get("", response_model=SubscriptionStatus)
async def my_subscription(
    principal: AuthPrincipal = Depends(_school_admin),
    session: AsyncSession = Depends(platform_session),
):
    return await tenant_subscription(session, principal.tenant_id)
