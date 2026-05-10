"""FastAPI dependencies for the authenticated user + role/permission checks."""

from __future__ import annotations

from typing import Iterable, Optional, Sequence

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.security import decode_token
from app.core.tenant import TenantContext, get_tenant
from app.core.tenant_session import platform_session
from app.models.auth import User, UserRole
from app.models.tenant import Tenant


_bearer = HTTPBearer(auto_error=False)


class AuthPrincipal:
    """Lightweight container - everything the request handler needs from the JWT."""

    def __init__(
        self,
        *,
        user: User,
        tenant: Tenant,
        roles: Sequence[str],
        permissions: Sequence[str],
        is_impersonation: bool = False,
    ) -> None:
        self.user = user
        self.tenant = tenant
        self.roles = list(roles)
        self.permissions = list(permissions)
        self.is_impersonation = is_impersonation

    @property
    def user_id(self) -> int:
        return self.user.id

    @property
    def tenant_id(self) -> int:
        return self.tenant.id

    def has_role(self, *codes: str) -> bool:
        return any(c in self.roles for c in codes)

    def has_permission(self, code: str) -> bool:
        return code in self.permissions or "platform.*" in self.permissions


async def get_current_principal(
    request: Request,
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    session: AsyncSession = Depends(platform_session),
    ctx: TenantContext = Depends(get_tenant),
) -> AuthPrincipal:
    if creds is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_token(creds.credentials)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    if payload.get("type") not in {"access", None}:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Wrong token type")

    user_id = int(payload.get("sub", 0))
    tenant_id = int(payload.get("tenant_id", 0))
    if not user_id or not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed token")

    # Reject mismatch between subdomain context and token (defense-in-depth).
    if ctx.tenant_id is not None and ctx.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token does not match the requested tenant",
        )

    user = (
        await session.execute(
            select(User)
            .options(joinedload(User.role_assignments).joinedload(UserRole.role))
            .where(User.id == user_id, User.tenant_id == tenant_id)
        )
    ).unique().scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or disabled")

    tenant = (await session.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one()

    return AuthPrincipal(
        user=user,
        tenant=tenant,
        roles=payload.get("roles", []) or [],
        permissions=payload.get("perms", []) or [],
        is_impersonation=bool(payload.get("impersonation", False)),
    )


def require_roles(*role_codes: str):
    """Dependency factory - require ANY of the supplied role codes."""

    async def _dep(principal: AuthPrincipal = Depends(get_current_principal)) -> AuthPrincipal:
        if not principal.has_role(*role_codes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of: {', '.join(role_codes)}",
            )
        return principal

    return _dep


def require_permission(code: str):
    """Dependency factory - require a specific permission code."""

    async def _dep(principal: AuthPrincipal = Depends(get_current_principal)) -> AuthPrincipal:
        if not principal.has_permission(code):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {code}",
            )
        return principal

    return _dep


def require_super_admin():
    return require_roles("super_admin")
