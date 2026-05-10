"""Tenant-scoped DB session.

Phase 1 enforces multi-tenant isolation at the *query* layer. Every ORM query
issued through a tenant-scoped session is automatically rewritten with a
``WHERE tenant_id = :tenant_id`` clause for every model that subclasses
``TenantBase``. The mechanism is SQLAlchemy's ``with_loader_criteria`` event,
applied via ``do_orm_execute`` so it covers ``select``, ``update``, ``delete``.

Why this matters:
    Even if a developer forgets the explicit filter, queries cannot leak rows
    from another tenant. The escape hatch is ``execution_options(unsafe_cross_tenant=True)``,
    which super-admin code uses on purpose.
"""

from __future__ import annotations

from typing import AsyncGenerator

from fastapi import Depends, HTTPException, status
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, with_loader_criteria

from app.core.tenant import TenantContext, get_tenant
from app.database import AsyncSessionLocal, TenantBase


def _install_filter(session: Session, tenant_id: int) -> None:
    """Attach a session-wide loader criterion for every TenantBase subclass."""

    @event.listens_for(session, "do_orm_execute")
    def _do_orm_execute(execute_state) -> None:
        if execute_state.execution_options.get("unsafe_cross_tenant"):
            return
        if not (execute_state.is_select or execute_state.is_update or execute_state.is_delete):
            return
        execute_state.statement = execute_state.statement.options(
            with_loader_criteria(
                TenantBase,
                lambda cls: cls.tenant_id == tenant_id,
                include_aliases=True,
            )
        )


async def tenant_scoped_session(
    ctx: TenantContext = Depends(get_tenant),
) -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yields an AsyncSession with the auto-filter installed.

    Raises 400 if there is no tenant in context (use ``platform_session`` for
    super-admin endpoints instead).
    """
    if ctx.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context required for this endpoint",
        )

    async with AsyncSessionLocal() as session:
        _install_filter(session.sync_session, ctx.tenant_id)
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def platform_session() -> AsyncGenerator[AsyncSession, None]:
    """Unfiltered session used by Super Admin endpoints. NEVER expose to tenant routes."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
