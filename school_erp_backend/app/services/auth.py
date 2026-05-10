"""Auth service: identifier+password login, JWT issuance, refresh, logout.

Tokens carry these claims:
    sub        : user id (string)
    tenant_id  : tenant the user belongs to
    subdomain  : convenience for the client
    roles      : list[str] of role codes
    perms      : list[str] of permission codes
    type       : "access" | "refresh"
    jti        : unique id for refresh tokens (used for revocation)

Refresh tokens are *also* persisted in the ``refresh_tokens`` table so logout
and forced-revocation are real, not just client-side discards.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.auth import RefreshToken, Role, User, UserRole
from app.models.parent import Parent, ParentChildMapping, ParentSession, Student
from app.models.tenant import Tenant, TenantStatus
from app.schemas.auth import (
    CurrentUser,
    LoginRequest,
    LoginResponse,
    ParentChildRead,
    TokenPair,
)


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ---- helpers ----------------------------------------------------------------


async def _get_tenant_by_subdomain(session: AsyncSession, subdomain: str) -> Tenant:
    tenant = (
        await session.execute(select(Tenant).where(Tenant.subdomain == subdomain.lower()))
    ).scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="School not found")
    if tenant.status == TenantStatus.SUSPENDED:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="School suspended")
    if tenant.status == TenantStatus.CANCELLED:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="School cancelled")
    return tenant


async def _resolve_user(
    session: AsyncSession, tenant_id: int, identifier: str
) -> Optional[User]:
    stmt = (
        select(User)
        .options(joinedload(User.role_assignments).joinedload(UserRole.role))
        .where(User.tenant_id == tenant_id)
        .where(or_(User.email == identifier, User.phone == identifier))
    )
    return (await session.execute(stmt)).unique().scalar_one_or_none()


async def _user_permissions(session: AsyncSession, user: User) -> list[str]:
    if not user.role_assignments:
        return []
    role_ids = [ur.role_id for ur in user.role_assignments]

    from app.models.auth import Permission, RolePermission

    rows = (
        await session.execute(
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id.in_(role_ids))
        )
    ).all()
    return sorted({code for (code,) in rows})


async def build_current_user(
    session: AsyncSession, user: User, tenant: Tenant
) -> CurrentUser:
    role_codes = sorted({ur.role.code for ur in user.role_assignments if ur.role})
    perms = await _user_permissions(session, user)
    primary = None
    if role_codes:
        # "primary" = highest level
        roles_with_level = [(ur.role.code, ur.role.level) for ur in user.role_assignments if ur.role]
        if roles_with_level:
            primary = max(roles_with_level, key=lambda x: x[1])[0]

    return CurrentUser(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        phone=user.phone,
        tenant_id=tenant.id,
        tenant_subdomain=tenant.subdomain,
        school_name=tenant.school_name,
        roles=role_codes,
        permissions=perms,
        primary_role=primary,
    )


def _issue_tokens(user: User, tenant: Tenant, role_codes: list[str], perms: list[str]) -> tuple[TokenPair, str, datetime]:
    """Mint access + refresh tokens. Returns (pair, jti, refresh_expiry)."""
    base_claims = {
        "sub": str(user.id),
        "tenant_id": tenant.id,
        "subdomain": tenant.subdomain,
        "roles": role_codes,
    }
    access = create_access_token({**base_claims, "perms": perms})
    jti = secrets.token_urlsafe(24)
    refresh = create_refresh_token({**base_claims, "jti": jti})
    refresh_expiry = _now() + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)

    pair = TokenPair(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    return pair, jti, refresh_expiry


# ---- public API -------------------------------------------------------------


async def login(
    session: AsyncSession,
    payload: LoginRequest,
    *,
    tenant_id_from_request: Optional[int] = None,
    user_agent: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> LoginResponse:
    # Tenant resolution: explicit subdomain wins, else request context.
    if payload.subdomain:
        tenant = await _get_tenant_by_subdomain(session, payload.subdomain)
    elif tenant_id_from_request is not None:
        tenant = (
            await session.execute(select(Tenant).where(Tenant.id == tenant_id_from_request))
        ).scalar_one()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context required. Send a subdomain field or call from a tenant subdomain.",
        )

    user = await _resolve_user(session, tenant.id, payload.identifier)
    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
    )
    if user is None or not user.password_hash:
        raise invalid
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled. Contact your school admin."
        )
    if not verify_password(payload.password, user.password_hash):
        user.failed_login_count = (user.failed_login_count or 0) + 1
        await session.commit()
        raise invalid

    user.failed_login_count = 0
    user.last_login_at = _now()

    role_codes = sorted({ur.role.code for ur in user.role_assignments if ur.role})
    perms = await _user_permissions(session, user)
    pair, jti, refresh_expiry = _issue_tokens(user, tenant, role_codes, perms)

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


async def refresh(session: AsyncSession, refresh_token: str) -> TokenPair:
    try:
        payload = decode_token(refresh_token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Wrong token type")
    jti = payload.get("jti")
    user_id = int(payload.get("sub", 0))
    tenant_id = int(payload.get("tenant_id", 0))
    if not jti or not user_id or not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed refresh token")

    rt = (
        await session.execute(
            select(RefreshToken).where(
                RefreshToken.jti == jti,
                RefreshToken.user_id == user_id,
                RefreshToken.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()
    if rt is None or rt.revoked_at is not None or rt.expires_at < _now():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked")

    # Rotate: revoke old, issue new.
    user = (
        await session.execute(
            select(User)
            .options(joinedload(User.role_assignments).joinedload(UserRole.role))
            .where(User.id == user_id)
        )
    ).unique().scalar_one()
    tenant = (await session.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one()

    role_codes = sorted({ur.role.code for ur in user.role_assignments if ur.role})
    perms = await _user_permissions(session, user)
    new_pair, new_jti, new_expiry = _issue_tokens(user, tenant, role_codes, perms)

    rt.revoked_at = _now()
    session.add(
        RefreshToken(
            tenant_id=tenant.id,
            user_id=user.id,
            jti=new_jti,
            expires_at=new_expiry,
            user_agent=rt.user_agent,
            ip_address=rt.ip_address,
        )
    )
    await session.commit()
    return new_pair


async def logout(session: AsyncSession, refresh_token: Optional[str], user_id: int, tenant_id: int) -> None:
    if refresh_token:
        try:
            payload = decode_token(refresh_token)
            jti = payload.get("jti")
        except Exception:
            jti = None
        if jti:
            rt = (
                await session.execute(
                    select(RefreshToken).where(
                        RefreshToken.jti == jti,
                        RefreshToken.user_id == user_id,
                    )
                )
            ).scalar_one_or_none()
            if rt:
                rt.revoked_at = _now()
                await session.commit()
                return
    # No specific token -> revoke every active session for this user.
    rows = (
        await session.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id,
                RefreshToken.tenant_id == tenant_id,
                RefreshToken.revoked_at.is_(None),
            )
        )
    ).scalars().all()
    for r in rows:
        r.revoked_at = _now()
    await session.commit()


# ---- multi-child parent helpers --------------------------------------------


async def list_children_of_user(session: AsyncSession, user_id: int, tenant_id: int) -> list[ParentChildRead]:
    parent = (
        await session.execute(
            select(Parent).where(Parent.user_id == user_id, Parent.tenant_id == tenant_id)
        )
    ).scalar_one_or_none()
    if parent is None:
        return []

    rows = (
        await session.execute(
            select(ParentChildMapping, Student)
            .join(Student, Student.id == ParentChildMapping.student_id)
            .where(ParentChildMapping.parent_id == parent.id)
        )
    ).all()
    return [
        ParentChildRead(
            student_id=s.id,
            full_name=s.full_name,
            admission_number=s.admission_number,
            current_class_label=s.current_class_label,
            is_primary=mapping.is_primary,
        )
        for (mapping, s) in rows
    ]


async def select_child(session: AsyncSession, user_id: int, tenant_id: int, student_id: int) -> int:
    parent = (
        await session.execute(
            select(Parent).where(Parent.user_id == user_id, Parent.tenant_id == tenant_id)
        )
    ).scalar_one_or_none()
    if parent is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a parent account")

    mapping = (
        await session.execute(
            select(ParentChildMapping).where(
                ParentChildMapping.parent_id == parent.id,
                ParentChildMapping.student_id == student_id,
            )
        )
    ).scalar_one_or_none()
    if mapping is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="That child is not linked to your account",
        )

    sess = (
        await session.execute(
            select(ParentSession).where(ParentSession.parent_id == parent.id)
        )
    ).scalar_one_or_none()
    if sess is None:
        sess = ParentSession(
            tenant_id=tenant_id,
            parent_id=parent.id,
            current_child_id=student_id,
        )
        session.add(sess)
    else:
        sess.current_child_id = student_id
        sess.last_switched_at = _now()
    await session.commit()
    return student_id


# ---- password reset (skeleton) ---------------------------------------------


async def reset_password(
    session: AsyncSession,
    *,
    tenant_id: int,
    identifier: str,
    new_password: str,
) -> None:
    user = await _resolve_user(session, tenant_id, identifier.lower())
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.password_hash = hash_password(new_password)
    user.failed_login_count = 0
    await session.commit()
