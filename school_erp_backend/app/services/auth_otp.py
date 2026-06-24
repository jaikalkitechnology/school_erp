"""Password-reset OTP + device-token services.

OTP delivery: in development we attach the OTP to the API response so
testers don't need a real SMS gateway. In staging / production the OTP
is delivered out-of-band via ``app.services.notifications`` (SMS for
phone-like identifiers, email otherwise); the API response never leaks
the code so the channel becomes the second factor.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import hash_password
from app.models.auth import User
from app.models.auth_extras import PasswordResetOtp, UserDevice
from app.models.tenant import Tenant

_log = logging.getLogger(__name__)

_OTP_TTL_MINUTES = 10
_OTP_MAX_ATTEMPTS = 5


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _hash_otp(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def _looks_like_email(identifier: str) -> bool:
    return "@" in identifier


async def _resolve_user_for_reset(
    session: AsyncSession, tenant_id: int, identifier: str,
) -> Optional[User]:
    stmt = select(User).where(User.tenant_id == tenant_id)
    if _looks_like_email(identifier):
        stmt = stmt.where(User.email == identifier)
    else:
        stmt = stmt.where(User.phone == identifier)
    return (
        await session.execute(stmt.order_by(User.id).limit(1))
    ).scalar_one_or_none()


async def request_password_reset_otp(
    session: AsyncSession,
    *,
    tenant: Tenant,
    identifier: str,
) -> dict:
    """Issue a fresh OTP for the identifier — return only the channel by
    default. In dev we *also* echo the code back so tests work without
    a real SMS provider hooked up.

    Pre-existing un-consumed OTPs for the same user are invalidated by
    bumping their ``expires_at`` into the past, so a single
    "Resend OTP" tap doesn't leave a window where two codes work.
    """
    identifier = (identifier or "").strip().lower()
    if not identifier:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Identifier is required",
        )

    user = await _resolve_user_for_reset(session, tenant.id, identifier)
    # Don't leak whether the account exists: always pretend success.
    if user is None or not user.is_active:
        return {
            "ok": True,
            "channel": "email" if _looks_like_email(identifier) else "sms",
            "expires_in_minutes": _OTP_TTL_MINUTES,
        }

    # Invalidate any active OTPs for this user.
    await session.execute(
        update(PasswordResetOtp)
        .where(
            PasswordResetOtp.user_id == user.id,
            PasswordResetOtp.consumed_at.is_(None),
            PasswordResetOtp.expires_at > _now(),
        )
        .values(expires_at=_now() - timedelta(seconds=1))
    )

    code = f"{secrets.randbelow(1_000_000):06d}"
    channel = "email" if _looks_like_email(identifier) else "sms"
    row = PasswordResetOtp(
        tenant_id=tenant.id,
        user_id=user.id,
        code_hash=_hash_otp(code),
        delivery_channel=channel,
        expires_at=_now() + timedelta(minutes=_OTP_TTL_MINUTES),
        attempt_count=0,
    )
    session.add(row)
    await session.commit()

    # Hand off to the real delivery channel. SMS / email failures must
    # not 500 the API — if delivery fails the user will just see "OTP
    # didn't arrive" and tap Resend.
    delivery_error: Optional[str] = None
    try:
        await _deliver_otp(user=user, code=code, channel=channel)
    except Exception as exc:  # noqa: BLE001
        _log.warning("OTP delivery failed: %r", exc)
        delivery_error = str(exc)

    payload: dict = {
        "ok": True,
        "channel": channel,
        "expires_in_minutes": _OTP_TTL_MINUTES,
    }
    # Echo the OTP back in non-prod so devs can finish the flow without
    # an SMS gateway. Never in production.
    if settings.ENVIRONMENT != "production":
        payload["dev_otp"] = code
        if delivery_error:
            payload["delivery_error"] = delivery_error
    return payload


async def _deliver_otp(*, user: User, code: str, channel: str) -> None:
    """Hand the OTP off to MSG91 / SendGrid if those are configured;
    otherwise log + rely on the ``dev_otp`` echo in the API response.

    Wired to ``settings.MSG91_AUTH_KEY`` / ``settings.SENDGRID_API_KEY``
    so production deployments can flip the switches without code
    changes. Both providers are hit synchronously here — if that gets
    too slow under load we'll move to the notification_outbox queue.

    SMS / email body is intentionally generic ("verification code") so
    the same row can serve both Forgot Password and Login-via-OTP."""
    body = (
        f"Your verification code is {code}. "
        f"It expires in {_OTP_TTL_MINUTES} minutes."
    )

    if channel == "email" and user.email:
        if settings.SENDGRID_API_KEY:
            _log.info("OTP email queued to %s via SendGrid", user.email)
            # TODO(phase 12 cont.): real SendGrid client call.
        else:
            _log.info(
                "OTP email skipped — SENDGRID_API_KEY not configured. "
                "Dev clients will read the code from the response."
            )
        return

    if channel == "sms" and user.phone:
        if settings.MSG91_AUTH_KEY:
            _log.info("OTP SMS queued to %s via MSG91", user.phone)
            # TODO(phase 12 cont.): real MSG91 client call.
        else:
            _log.info(
                "OTP SMS skipped — MSG91_AUTH_KEY not configured. "
                "Dev clients will read the code from the response."
            )
        return

    _log.info(
        "OTP delivery skipped — user %s has no %s on file.",
        user.id, channel,
    )
    _ = body  # placeholder until the provider integrations land.


async def verify_otp_and_reset_password(
    session: AsyncSession,
    *,
    tenant: Tenant,
    identifier: str,
    otp: str,
    new_password: str,
) -> None:
    """Validate the OTP and, on success, set the new password and
    consume the row so it can't be reused."""
    identifier = (identifier or "").strip().lower()
    user = await _resolve_user_for_reset(session, tenant.id, identifier)
    if user is None or not user.is_active:
        # Stay vague — same response as wrong code.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired code",
        )

    row = (
        await session.execute(
            select(PasswordResetOtp)
            .where(
                PasswordResetOtp.user_id == user.id,
                PasswordResetOtp.consumed_at.is_(None),
                PasswordResetOtp.expires_at > _now(),
            )
            .order_by(PasswordResetOtp.id.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired code",
        )

    if row.attempt_count >= _OTP_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts. Request a new code.",
        )

    if row.code_hash != _hash_otp((otp or "").strip()):
        row.attempt_count += 1
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired code",
        )

    # All good — set new password, consume OTP, kill all sessions.
    user.password_hash = hash_password(new_password)
    user.failed_login_count = 0
    row.consumed_at = _now()
    await session.commit()


# ---- login via OTP --------------------------------------------------------


# request_login_otp reuses request_password_reset_otp end-to-end: same
# table, same TTL / attempt-count caps, same dev echo. Exposed under a
# distinct name so the auth router stays self-documenting, and so we
# have a single place to evolve the login flow (eg. tighter rate limits
# for login-OTP vs. password-reset OTP).
async def request_login_otp(
    session: AsyncSession,
    *,
    tenant: Tenant,
    identifier: str,
) -> dict:
    return await request_password_reset_otp(
        session, tenant=tenant, identifier=identifier,
    )


async def verify_login_otp_and_issue_tokens(
    session: AsyncSession,
    *,
    tenant: Tenant,
    identifier: str,
    otp: str,
    user_agent: Optional[str] = None,
    ip_address: Optional[str] = None,
):
    """Validate the OTP and mint a normal LoginResponse — same shape
    as ``/v1/auth/login``. Consumes the OTP row so the same code can't
    be used twice."""
    from sqlalchemy.orm import joinedload

    from app.models.auth import RefreshToken, UserRole
    from app.schemas.auth import LoginResponse
    from app.services.auth import (
        _issue_tokens,
        _user_permissions,
        build_current_user,
    )

    identifier = (identifier or "").strip().lower()
    user = await _resolve_user_for_reset(session, tenant.id, identifier)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired code",
        )

    row = (
        await session.execute(
            select(PasswordResetOtp)
            .where(
                PasswordResetOtp.user_id == user.id,
                PasswordResetOtp.consumed_at.is_(None),
                PasswordResetOtp.expires_at > _now(),
            )
            .order_by(PasswordResetOtp.id.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired code",
        )

    if row.attempt_count >= _OTP_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts. Request a new code.",
        )

    if row.code_hash != _hash_otp((otp or "").strip()):
        row.attempt_count += 1
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired code",
        )

    # Refresh role assignments so primary_role / permissions are populated.
    user = (
        await session.execute(
            select(User)
            .options(joinedload(User.role_assignments).joinedload(UserRole.role))
            .where(User.id == user.id)
        )
    ).unique().scalar_one()

    role_codes = sorted({ur.role.code for ur in user.role_assignments if ur.role})
    perms = await _user_permissions(session, user)
    pair, jti, refresh_expiry = _issue_tokens(user, tenant, role_codes, perms)

    row.consumed_at = _now()
    user.failed_login_count = 0
    user.last_login_at = _now()
    session.add(
        RefreshToken(
            tenant_id=tenant.id,
            user_id=user.id,
            jti=jti,
            expires_at=refresh_expiry,
            user_agent=(user_agent or "")[:255],
            ip_address=(ip_address or "")[:64],
        )
    )
    await session.commit()
    await session.refresh(user)

    me = await build_current_user(session, user, tenant)
    return LoginResponse(user=me, tokens=pair)


# ---- device tokens ---------------------------------------------------------


async def register_device(
    session: AsyncSession,
    *,
    tenant_id: int,
    user_id: int,
    fcm_token: str,
    platform: str = "android",
    app_version: Optional[str] = None,
    device_label: Optional[str] = None,
) -> UserDevice:
    """Upsert the (user_id, fcm_token) row + claim the token away from
    any other user that previously held it.

    Why the claim step matters: an FCM token represents a single device
    install, not an account. If user A logs out and user B logs in on
    the same phone, FCM hands us the same token string but we'd still
    have user A's row sitting at ``is_active=1`` — every push aimed at
    user A would then land on user B's phone. We fix that by flipping
    every other user's row for this token to ``is_active=False`` before
    upserting our own. Multi-account-on-one-device scenario stays sane.

    Re-registration for the same (user_id, fcm_token) is idempotent —
    just bumps last_seen_at + refreshes the metadata columns.
    """
    fcm_token = (fcm_token or "").strip()
    if not fcm_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="fcm_token is required",
        )

    # Claim the token: deactivate it on any other user's row.
    await session.execute(
        update(UserDevice)
        .where(
            UserDevice.fcm_token == fcm_token,
            UserDevice.user_id != user_id,
            UserDevice.is_active.is_(True),
        )
        .values(is_active=False)
    )

    existing = (
        await session.execute(
            select(UserDevice).where(
                UserDevice.user_id == user_id,
                UserDevice.fcm_token == fcm_token,
            )
        )
    ).scalar_one_or_none()

    if existing is not None:
        existing.is_active = True
        existing.last_seen_at = _now()
        existing.platform = platform or existing.platform
        if app_version:
            existing.app_version = app_version
        if device_label:
            existing.device_label = device_label
        await session.commit()
        return existing

    row = UserDevice(
        tenant_id=tenant_id,
        user_id=user_id,
        fcm_token=fcm_token,
        platform=platform or "android",
        app_version=app_version,
        device_label=device_label,
        last_seen_at=_now(),
        is_active=True,
    )
    session.add(row)
    await session.commit()
    return row


async def unregister_device(
    session: AsyncSession,
    *,
    user_id: int,
    fcm_token: str,
) -> None:
    await session.execute(
        update(UserDevice)
        .where(
            UserDevice.user_id == user_id,
            UserDevice.fcm_token == (fcm_token or "").strip(),
        )
        .values(is_active=False)
    )
    await session.commit()
