"""Audit log helpers."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import Request
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import AuthPrincipal
from app.models.audit import AuditLog


async def record(
    session: AsyncSession,
    *,
    principal: Optional[AuthPrincipal],
    action: str,
    target_type: Optional[str] = None,
    target_id: Optional[int] = None,
    summary: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
    request: Optional[Request] = None,
    tenant_id_override: Optional[int] = None,
) -> AuditLog:
    tenant_id = tenant_id_override
    if tenant_id is None:
        if principal is not None:
            tenant_id = principal.tenant_id
        elif request is not None:
            tenant_id = getattr(getattr(request.state, "tenant", None), "tenant_id", None) or 0
        else:
            tenant_id = 0

    log = AuditLog(
        tenant_id=tenant_id or 0,
        actor_user_id=principal.user_id if principal else None,
        actor_email=principal.user.email if principal else None,
        actor_role=principal.roles[0] if principal and principal.roles else None,
        action=action,
        target_type=target_type,
        target_id=target_id,
        summary=summary,
        metadata_json=metadata,
        ip_address=request.client.host if request and request.client else None,
        user_agent=(request.headers.get("user-agent") if request else None),
    )
    session.add(log)
    await session.commit()
    await session.refresh(log)
    return log


async def list_logs(
    session: AsyncSession,
    *,
    tenant_id: Optional[int] = None,
    action_prefix: Optional[str] = None,
    limit: int = 100,
) -> list[AuditLog]:
    stmt = select(AuditLog).order_by(desc(AuditLog.created_at)).limit(limit)
    # platform_session is unfiltered, so we apply tenant_id manually if asked.
    if tenant_id is not None:
        stmt = stmt.where(AuditLog.tenant_id == tenant_id)
    if action_prefix:
        stmt = stmt.where(AuditLog.action.like(f"{action_prefix}%"))
    return list((await session.execute(stmt)).scalars().all())
