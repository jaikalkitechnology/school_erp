"""Auth endpoints: login, refresh, logout, me, parent child-switching."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import AuthPrincipal, get_current_principal
from app.core.tenant import TenantContext, get_tenant
from app.core.tenant_session import platform_session
from app.schemas.auth import (
    ChangePasswordRequest,
    CurrentUser,
    DeviceRegisterRequest,
    DeviceUnregisterRequest,
    ForgotPasswordRequest,
    LoginOtpRequestBody,
    LoginOtpVerifyBody,
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
    change_password as change_password_service,
    list_children_of_user,
    login as login_service,
    logout as logout_service,
    refresh as refresh_service,
    select_child,
)
from app.services.auth_otp import (
    register_device,
    request_login_otp,
    request_password_reset_otp,
    unregister_device,
    verify_login_otp_and_issue_tokens,
    verify_otp_and_reset_password,
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


# ---- In-app password change (logged-in user) ------------------------------


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password_route(
    payload: ChangePasswordRequest,
    principal: AuthPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(platform_session),
):
    """Rotate the signed-in user's password. Requires the current
    password so a stolen bearer token alone can't change credentials.
    Active refresh tokens for the user are revoked on success so other
    sessions (other devices / the web admin) are forced to sign back in
    with the new password."""
    await change_password_service(
        session,
        user_id=principal.user_id,
        current_password=payload.current_password,
        new_password=payload.new_password,
    )


# ---- Passwordless login via OTP -------------------------------------------


@router.post("/login/otp/request", status_code=status.HTTP_202_ACCEPTED)
async def login_otp_request(
    payload: LoginOtpRequestBody,
    session: AsyncSession = Depends(platform_session),
    ctx: TenantContext = Depends(get_tenant),
):
    """Send a one-time login code to the email/phone on file. Returns
    202 unconditionally so callers can't enumerate which accounts
    exist. In dev (ENVIRONMENT != "production") the response includes
    ``dev_otp`` so testers can finish the flow without a real SMS
    gateway."""
    tenant = await _tenant_for_reset(payload.subdomain, ctx.tenant_id, session)
    return await request_login_otp(
        session, tenant=tenant, identifier=payload.identifier,
    )


@router.post("/login/otp/verify", response_model=LoginResponse)
async def login_otp_verify(
    payload: LoginOtpVerifyBody,
    request: Request,
    session: AsyncSession = Depends(platform_session),
    ctx: TenantContext = Depends(get_tenant),
):
    """Trade an OTP for a fresh access + refresh token pair. Response
    shape mirrors ``/v1/auth/login`` so the mobile cubit's happy path
    works unchanged."""
    tenant = await _tenant_for_reset(payload.subdomain, ctx.tenant_id, session)
    return await verify_login_otp_and_issue_tokens(
        session,
        tenant=tenant,
        identifier=payload.identifier,
        otp=payload.otp,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )


# ---- password reset (real OTP flow) ---------------------------------------


async def _tenant_for_reset(
    payload_subdomain: Optional[str],
    ctx_tenant_id: Optional[int],
    session: AsyncSession,
):
    """Resolve the tenant the password reset is scoped to: explicit
    subdomain in the payload beats the request's tenant header."""
    from app.models.tenant import Tenant
    from sqlalchemy import select as _select
    from app.services.auth import _get_tenant_by_subdomain

    if payload_subdomain:
        return await _get_tenant_by_subdomain(session, payload_subdomain)
    if ctx_tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context required for password reset",
        )
    tenant = (
        await session.execute(_select(Tenant).where(Tenant.id == ctx_tenant_id))
    ).scalar_one_or_none()
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="School not found",
        )
    return tenant


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
async def forgot_password(
    payload: ForgotPasswordRequest,
    session: AsyncSession = Depends(platform_session),
    ctx: TenantContext = Depends(get_tenant),
):
    """Generate + dispatch a password-reset OTP. Always returns 202 so
    the response can't be used to enumerate which accounts exist. In
    dev (ENVIRONMENT != "production") the response also carries the OTP
    under ``dev_otp`` so the mobile flow can be tested end-to-end
    without a real SMS gateway."""
    tenant = await _tenant_for_reset(payload.subdomain, ctx.tenant_id, session)
    return await request_password_reset_otp(
        session, tenant=tenant, identifier=payload.identifier,
    )


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password_endpoint(
    payload: ResetPasswordRequest,
    request: Request,
    session: AsyncSession = Depends(platform_session),
    ctx: TenantContext = Depends(get_tenant),
):
    """Validate the OTP, set the new password, consume the OTP row."""
    tenant = await _tenant_for_reset(payload.subdomain, ctx.tenant_id, session)
    await verify_otp_and_reset_password(
        session,
        tenant=tenant,
        identifier=payload.identifier,
        otp=payload.otp,
        new_password=payload.new_password,
    )


# ---- device tokens (FCM) --------------------------------------------------


@router.post("/devices/register", status_code=status.HTTP_201_CREATED)
async def register_device_route(
    payload: DeviceRegisterRequest,
    principal: AuthPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(platform_session),
):
    """Upsert the logged-in device's FCM token. Safe to call on every
    cold-start: the (user_id, fcm_token) unique index turns repeated
    registrations into idempotent ``last_seen_at`` bumps."""
    row = await register_device(
        session,
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        fcm_token=payload.fcm_token,
        platform=payload.platform,
        app_version=payload.app_version,
        device_label=payload.device_label,
    )
    return {
        "id": row.id,
        "platform": row.platform,
        "is_active": row.is_active,
    }


@router.post("/devices/unregister", status_code=status.HTTP_204_NO_CONTENT)
async def unregister_device_route(
    payload: DeviceUnregisterRequest,
    principal: AuthPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(platform_session),
):
    """Soft-delete (is_active=False) the token for the current user.
    Called on logout so the server stops pushing to a device the user
    has signed out of."""
    await unregister_device(
        session, user_id=principal.user_id, fcm_token=payload.fcm_token,
    )
