"""Multi-tenancy: subdomain extraction, DB lookup, request-state context.

Resolution order on every request:
    1. ``X-Tenant-Subdomain`` header  - dev/test override.
    2. ``X-Tenant-Id`` header         - dev/test override (numeric).
    3. Subdomain from ``Host`` header - production path.
    4. None                           - platform-level request (super admin).

Successful lookup populates ``request.state.tenant`` with a ``TenantContext``
the rest of the codebase can rely on.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fastapi import HTTPException, Request, status
from sqlalchemy import select
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.config import settings
from app.database import AsyncSessionLocal


@dataclass
class TenantContext:
    subdomain: Optional[str]
    tenant_id: Optional[int]
    is_platform_request: bool
    status: Optional[str] = None
    storage_limit_mb: Optional[int] = None
    student_limit: Optional[int] = None
    teacher_limit: Optional[int] = None


def _extract_subdomain(host: str) -> Optional[str]:
    host = (host or "").split(":")[0].lower()
    if not host or host in settings.PLATFORM_HOSTS:
        return None
    parts = host.split(".")
    if len(parts) < 3:
        return None
    sub = parts[0]
    if sub in {"www", "admin", "api"}:
        return None
    return sub


async def _resolve_tenant(subdomain: Optional[str], tenant_id_hint: Optional[int]) -> TenantContext:
    """Look up the tenant; returns a platform context if no hints given."""
    if subdomain is None and tenant_id_hint is None:
        return TenantContext(None, None, True)

    # Local import keeps the dependency graph clean - middleware doesn't import models at module load.
    from app.models.tenant import Tenant, TenantStatus

    async with AsyncSessionLocal() as session:
        stmt = select(Tenant)
        if tenant_id_hint is not None:
            stmt = stmt.where(Tenant.id == tenant_id_hint)
        else:
            stmt = stmt.where(Tenant.subdomain == subdomain)

        tenant = (await session.execute(stmt)).scalar_one_or_none()

    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    if tenant.status == TenantStatus.SUSPENDED:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant suspended")
    if tenant.status == TenantStatus.CANCELLED:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Tenant cancelled")

    return TenantContext(
        subdomain=tenant.subdomain,
        tenant_id=tenant.id,
        is_platform_request=False,
        status=tenant.status.value if tenant.status else None,
        storage_limit_mb=tenant.storage_limit_mb,
        student_limit=tenant.student_limit,
        teacher_limit=tenant.teacher_limit,
    )


class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        host = request.headers.get("host", "")
        sub_override = request.headers.get("x-tenant-subdomain")
        id_override = request.headers.get("x-tenant-id")
        subdomain = sub_override.lower() if sub_override else _extract_subdomain(host)
        tenant_id_hint: Optional[int] = None
        if id_override and id_override.isdigit():
            tenant_id_hint = int(id_override)

        try:
            request.state.tenant = await _resolve_tenant(subdomain, tenant_id_hint)
        except HTTPException as exc:
            from starlette.responses import JSONResponse

            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail, "request_id": getattr(request.state, "request_id", None)},
            )

        return await call_next(request)


def get_tenant(request: Request) -> TenantContext:
    """FastAPI dependency to retrieve the current tenant context."""
    return getattr(request.state, "tenant", TenantContext(None, None, True))


def require_tenant(request: Request) -> TenantContext:
    """Dependency that 400s if the request is platform-level (no tenant)."""
    ctx = get_tenant(request)
    if ctx.is_platform_request or ctx.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context required (use a school subdomain or X-Tenant-Id header)",
        )
    return ctx


def require_platform(request: Request) -> TenantContext:
    """Dependency that 403s if the request is from a tenant subdomain."""
    ctx = get_tenant(request)
    if not ctx.is_platform_request:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform-level (super admin) request required",
        )
    return ctx
