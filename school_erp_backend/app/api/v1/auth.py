"""Auth endpoints: login, refresh, logout, me, parent child-switching."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import AuthPrincipal, get_current_principal
from app.core.tenant import TenantContext, get_tenant
from app.core.tenant_session import platform_session
from app.schemas.auth import (
    CurrentUser,
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    ParentChildRead,
    ParentChildSwitch,
    RefreshRequest,
    ResetPasswordRequest,
    TokenPair,
)
from app.services.auth import (
    build_current_user,
    list_children_of_user,
    login as login_service,
    logout as logout_service,
    refresh as refresh_service,
    reset_password,
    select_child,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(platform_session),
    ctx: TenantContext = Depends(get_tenant),
):
    return await login_service(
        session,
        payload,
        tenant_id_from_request=ctx.tenant_id,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )


@router.post("/refresh", response_model=TokenPair)
async def refresh(
    payload: RefreshRequest,
    session: AsyncSession = Depends(platform_session),
):
    return await refresh_service(session, payload.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    payload: LogoutRequest,
    principal: AuthPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(platform_session),
):
    await logout_service(session, payload.refresh_token, principal.user_id, principal.tenant_id)


@router.get("/me", response_model=CurrentUser)
async def me(
    principal: AuthPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(platform_session),
):
    return await build_current_user(session, principal.user, principal.tenant)


# ---- multi-child parent ----------------------------------------------------


@router.get("/parent/children", response_model=list[ParentChildRead])
async def parent_children(
    principal: AuthPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(platform_session),
):
    return await list_children_of_user(session, principal.user_id, principal.tenant_id)


@router.post("/parent/select-child")
async def parent_select_child(
    payload: ParentChildSwitch,
    principal: AuthPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(platform_session),
):
    student_id = await select_child(session, principal.user_id, principal.tenant_id, payload.student_id)
    return {"current_child_id": student_id}


# ---- password reset (skeleton; OTP delivery wired in Phase 12) -------------


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
async def forgot_password(payload: ForgotPasswordRequest):
    """Triggers an OTP send. Phase 12 plugs in MSG91/SendGrid."""
    return {
        "ok": True,
        "message": "If that account exists, an OTP has been queued. (SMS/Email delivery lands in Phase 12.)",
    }


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password_endpoint(
    payload: ResetPasswordRequest,
    request: Request,
    session: AsyncSession = Depends(platform_session),
    ctx: TenantContext = Depends(get_tenant),
):
    """Phase 2 stub: trusts any OTP. Phase 12 will validate against the OTP store."""
    if payload.subdomain:
        # Lazy import to keep this file decoupled.
        from app.services.auth import _get_tenant_by_subdomain

        tenant = await _get_tenant_by_subdomain(session, payload.subdomain)
        tenant_id = tenant.id
    elif ctx.tenant_id is not None:
        tenant_id = ctx.tenant_id
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context required for password reset",
        )
    await reset_password(
        session, tenant_id=tenant_id, identifier=payload.identifier, new_password=payload.new_password
    )
