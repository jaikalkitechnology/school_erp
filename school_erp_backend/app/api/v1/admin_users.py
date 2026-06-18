"""Unified user / login management for the school admin UI."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import AuthPrincipal, require_roles
from app.core.tenant_session import tenant_scoped_session
from app.services.admin_users import (
    ASSIGNABLE_ROLES,
    PasswordResult,
    SetPassword,
    UserCreate,
    UserRow,
    UserUpdate,
    create_user,
    delete_user,
    list_users,
    set_active,
    set_password,
    update_user,
)


_admin = require_roles("school_admin", "principal", "vice_principal")


router = APIRouter(
    prefix="/school-admin/users",
    tags=["school-admin"],
    dependencies=[Depends(_admin)],
)


class UserListPage(BaseModel):
    items: list[UserRow]
    total: int
    limit: int
    offset: int


class RoleOption(BaseModel):
    code: str
    name: str


class AdminPageOption(BaseModel):
    slug: str
    label: str
    group: str


class PagesCatalogue(BaseModel):
    pages: list[AdminPageOption]
    defaults_by_role: dict[str, list[str]]


@router.get("/_pages", response_model=PagesCatalogue)
async def admin_pages_catalogue_route():
    """Static catalogue + per-role default page sets. The Add/Edit
    user dialog uses this to render the page checklist and pre-tick
    boxes when the admin picks a role."""
    from app.core.admin_pages import (
        ADMIN_PAGES,
        DEFAULT_PAGES_BY_ROLE,
    )

    return PagesCatalogue(
        pages=[
            AdminPageOption(slug=s, label=l, group=g)
            for s, l, g in ADMIN_PAGES
        ],
        defaults_by_role={k: list(v) for k, v in DEFAULT_PAGES_BY_ROLE.items()},
    )


@router.get("/_roles", response_model=list[RoleOption])
async def assignable_roles_route(
    session: AsyncSession = Depends(tenant_scoped_session),
):
    """Return the catalogue of roles the school admin can assign,
    pulled from the *tenant's* Role table so locally-renamed roles
    show their actual display name."""
    from sqlalchemy import select

    from app.models.auth import Role

    rows = (
        await session.execute(
            select(Role.code, Role.name).where(Role.code.in_(ASSIGNABLE_ROLES))
            .order_by(Role.level.desc(), Role.code)
        )
    ).all()
    return [RoleOption(code=c, name=n) for c, n in rows]


@router.get("", response_model=UserListPage)
async def list_users_route(
    q: Optional[str] = None,
    role_code: Optional[str] = None,
    only_active: bool = False,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    principal: AuthPrincipal = Depends(_admin),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    items, total = await list_users(
        session,
        tenant_id=principal.tenant_id,
        q=q,
        role_code=role_code,
        only_active=only_active,
        limit=limit,
        offset=offset,
    )
    return UserListPage(items=items, total=total, limit=limit, offset=offset)


@router.post("", response_model=UserRow, status_code=status.HTTP_201_CREATED)
async def create_user_route(
    payload: UserCreate,
    principal: AuthPrincipal = Depends(_admin),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await create_user(session, tenant_id=principal.tenant_id, payload=payload)


@router.patch("/{user_id}", response_model=UserRow)
async def update_user_route(
    user_id: int,
    payload: UserUpdate,
    principal: AuthPrincipal = Depends(_admin),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await update_user(
        session, tenant_id=principal.tenant_id, user_id=user_id, payload=payload
    )


@router.post("/{user_id}/set-password", response_model=PasswordResult)
async def set_password_route(
    user_id: int,
    payload: SetPassword,
    principal: AuthPrincipal = Depends(_admin),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await set_password(
        session,
        tenant_id=principal.tenant_id,
        user_id=user_id,
        new_password=payload.new_password,
    )


@router.post("/{user_id}/activate", response_model=UserRow)
async def activate_route(
    user_id: int,
    principal: AuthPrincipal = Depends(_admin),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await set_active(
        session, tenant_id=principal.tenant_id, user_id=user_id, active=True,
    )


@router.post("/{user_id}/deactivate", response_model=UserRow)
async def deactivate_route(
    user_id: int,
    principal: AuthPrincipal = Depends(_admin),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await set_active(
        session, tenant_id=principal.tenant_id, user_id=user_id, active=False,
    )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_route(
    user_id: int,
    principal: AuthPrincipal = Depends(_admin),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    await delete_user(session, tenant_id=principal.tenant_id, user_id=user_id)
