"""Multi-tenancy primitives: subdomain detection middleware + request-state tenant.

Phase 0 establishes the *plumbing*. The actual Tenant DB model and lookup logic
land in Phase 1 — until then, the middleware just extracts the subdomain and
attaches it to ``request.state`` so endpoints can rely on the contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.config import settings


@dataclass
class TenantContext:
    subdomain: Optional[str]
    tenant_id: Optional[int]
    is_platform_request: bool


def _extract_subdomain(host: str) -> Optional[str]:
    host = (host or "").split(":")[0].lower()
    if not host or host in settings.PLATFORM_HOSTS:
        return None
    parts = host.split(".")
    if len(parts) < 3:
        # `example.com` or `localhost` -> platform-level request, no tenant.
        return None
    sub = parts[0]
    if sub in {"www", "admin", "api"}:
        return None
    return sub


class TenantMiddleware(BaseHTTPMiddleware):
    """Attach a ``TenantContext`` to every request based on the Host header.

    Resolution sequence:
      1. ``X-Tenant-Subdomain`` header (handy for local dev with curl/Postman).
      2. Subdomain extracted from ``Host``.
      3. None -> platform-level request (Super Admin / health checks).

    Phase 1 will plug in DB lookup that maps subdomain -> tenant_id.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        host = request.headers.get("host", "")
        override = request.headers.get("x-tenant-subdomain")
        subdomain = override.lower() if override else _extract_subdomain(host)

        request.state.tenant = TenantContext(
            subdomain=subdomain,
            tenant_id=None,  # Phase 1 will populate from DB.
            is_platform_request=subdomain is None,
        )
        return await call_next(request)


def get_tenant(request: Request) -> TenantContext:
    """FastAPI dependency to retrieve the current tenant context."""
    return getattr(request.state, "tenant", TenantContext(None, None, True))
