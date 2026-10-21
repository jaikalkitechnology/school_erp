"""Auth endpoints: login, refresh, logout, me, parent child-switching."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
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

from app.models.auth_extras import UserDevice
from app.schemas.auth import SendNotificationRequest
from app.services import fcm

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


class GoogleLoginRequest(__import__("pydantic").BaseModel):
    id_token: str
    subdomain: Optional[str] = None
    platform: Optional[str] = None  # accepted for parity; not gated


@router.post("/google", response_model=LoginResponse)
async def login_google(
    payload: GoogleLoginRequest,
    request: Request,
    session: AsyncSession = Depends(platform_session),
    ctx: TenantContext = Depends(get_tenant),
):
    """Subdomain-first Google Sign-In. The client sends the Google ID
    token + the school subdomain; we verify the token against Google's
    public keys, find the user inside that tenant, and issue our own
    access/refresh pair (same shape as /login)."""
    from app.services.auth import login_with_google

    return await login_with_google(
        session,
        id_token=payload.id_token,
        subdomain=payload.subdomain,
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


@router.get("/branding")
async def branding(principal: AuthPrincipal = Depends(get_current_principal)):
    """School name + logo + colours for the signed-in user's school. Open
    to every signed-in role (unlike /school-admin/settings), so the admin
    sidebar can show the logo to librarians, accountants, etc."""
    t = principal.tenant
    if t is None:
        return {"school_name": None, "logo_url": None, "primary_color": None}
    return {
        "school_name": t.school_name,
        "logo_url": t.logo_url,
        "primary_color": t.primary_color,
    }


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
#
# Canonical paths are /devices/fcm/register and /devices/fcm/unregister.
# The bare /devices/register and /devices/unregister are kept as aliases
# so already-released client builds keep working until they're updated.


@router.post("/devices/fcm/register", status_code=status.HTTP_201_CREATED)
@router.post("/devices/register", status_code=status.HTTP_201_CREATED)
async def register_device_route(
    payload: DeviceRegisterRequest,
    principal: AuthPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(platform_session),
):
    """Upsert the logged-in device's FCM token against this session.

    The mobile client calls this on every successful login so a fresh
    user always replaces whoever was previously bound to the same
    token on the same phone. ``register_device`` deactivates any other
    user's row holding this fcm_token before upserting, so future
    pushes targeted at the previous user stop landing on this device."""
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


@router.post("/devices/fcm/unregister", status_code=status.HTTP_204_NO_CONTENT)
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


@router.post("/send-notification")
async def send_notification(
    payload: SendNotificationRequest,
    session: AsyncSession = Depends(platform_session),
):
    """Fire a one-off push to every active device the user has.

    Per-device errors are collected and returned rather than raised —
    we don't want a single dead token to fail the whole fan-out.
    Shares the implementation with the admin Communication page's
    announcement publish path so behaviour is identical."""
    from app.services.push_dispatch import send_push_to_user

    # Guard before we even query devices so the 404 vs 503 distinction
    # is preserved.
    if not fcm.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"FCM not configured: {fcm.unavailable_reason()}",
        )

    devices_count = (
        await session.execute(
            select(UserDevice).where(
                UserDevice.user_id == payload.user_id,
                UserDevice.is_active.is_(True),
            )
        )
    ).scalars().all()
    if not devices_count:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active devices found",
        )

    result = await send_push_to_user(
        session,
        user_id=payload.user_id,
        title=payload.title,
        body=payload.body,
        data={
            "screen": payload.screen or "",
            **{k: str(v) for k, v in payload.data.items()},
        },
    )
    success = result.sent
    failed = result.failed
    errors = result.errors

    return {
        "success": success > 0,
        "sent_count": success,
        "failed_count": failed,
        "total_devices": len(devices_count),
        "deactivated": result.deactivated,
        "errors": errors,
    }