"""Unified user/credential management for the school admin.

Each role has its own onboarding flow (teachers create teacher rows,
parents auto-create on admission, etc.) but there was no single place
where the school admin could see *every* login on the tenant and reset
a password / activate / deactivate / delete. This module covers that
gap. Role-specific records (Teacher, Parent, etc.) are NOT touched
here — this is purely the User + UserRole side.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import HTTPException, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import hash_password
from app.models.auth import Role, User, UserRole

# Roles the school admin is allowed to create / manage through this UI.
#
# Platform-level roles (super_admin) and students are deliberately
# excluded — students don't log in via this surface, and super_admin is
# created by the platform owner only.
#
# These roles are also intentionally NOT assignable here:
#   * school_admin    — bootstrapped once at tenant onboarding; you don't
#                       create a second one via this generic users panel.
#   * principal       — high-trust role, onboarded via Teachers → Onboard
#                       with role_codes=["principal"] so the Teacher row
#                       lands too.
#   * subject_teacher — Teachers → Onboard (creates User + Teacher pair).
#   * class_teacher   — Teachers → Onboard (creates User + Teacher pair).
#   * office_staff    — onboarded via Teachers → Onboard.
#   * parent          — auto-created on student admission; passwords are
#                       set from Students → Family panel ("Set password"),
#                       not from a generic Add-user form.
#
# Everything else (vice_principal, coordinator, accountant, librarian,
# transport_manager, hostel_warden, bus_staff, supervisor, visitor_desk)
# genuinely belongs on this screen — these are pure-login users with no
# separate domain row that the dedicated Teachers / Students flows
# would otherwise create.
ASSIGNABLE_ROLES: set[str] = {
    "vice_principal",
    "coordinator",
    "accountant",
    "librarian",
    "transport_manager",
    "hostel_warden",
    "supervisor",
    "visitor_desk",
    # Phase 27 org-chart additions.
    "hod",
    "receptionist",
}


# ---- Schemas --------------------------------------------------------------


class UserRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    is_active: bool
    is_email_verified: bool
    last_login_at: Optional[datetime] = None
    avatar_url: Optional[str] = None
    role_codes: list[str] = Field(default_factory=list)
    granted_admin_pages: list[str] = Field(default_factory=list)


class UserCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=180)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, max_length=20)
    password: str = Field(min_length=6, max_length=128)
    role_codes: list[str] = Field(min_length=1)
    granted_admin_pages: Optional[list[str]] = None


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, max_length=180)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, max_length=20)
    role_codes: Optional[list[str]] = None
    granted_admin_pages: Optional[list[str]] = None


class SetPassword(BaseModel):
    new_password: str = Field(min_length=6, max_length=128)


class PasswordResult(BaseModel):
    user_id: int
    full_name: str


# ---- Helpers --------------------------------------------------------------


def _validate_roles(role_codes: list[str]) -> list[str]:
    unique = list(dict.fromkeys(role_codes))
    bad = [c for c in unique if c not in ASSIGNABLE_ROLES]
    if bad:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Roles not assignable: {bad}",
        )
    return unique


async def _resolve_roles(
    session: AsyncSession, tenant_id: int, codes: list[str]
) -> list[Role]:
    if not codes:
        return []
    rows = list(
        (
            await session.execute(
                select(Role).where(Role.tenant_id == tenant_id, Role.code.in_(codes))
            )
        ).scalars().all()
    )
    found = {r.code for r in rows}
    missing = [c for c in codes if c not in found]
    if missing:
        # Almost certainly means the tenant hasn't been re-seeded after a
        # new role landed in the catalogue. Tell the caller specifically
        # so they know what to fix.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Tenant is missing roles {missing}. "
                "Re-run the role seed for this tenant."
            ),
        )
    return rows


def _as_row(user: User) -> UserRow:
    return UserRow(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        phone=user.phone,
        is_active=user.is_active,
        is_email_verified=user.is_email_verified,
        last_login_at=user.last_login_at,
        avatar_url=user.avatar_url,
        role_codes=[ur.role.code for ur in (user.role_assignments or [])],
        granted_admin_pages=list(user.granted_admin_pages or []),
    )


# ---- Service --------------------------------------------------------------


async def list_users(
    session: AsyncSession,
    *,
    tenant_id: int,
    q: Optional[str] = None,
    role_code: Optional[str] = None,
    only_active: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[UserRow], int]:
    stmt = (
        select(User)
        .options(selectinload(User.role_assignments).joinedload(UserRole.role))
        .where(User.tenant_id == tenant_id)
    )
    if only_active:
        stmt = stmt.where(User.is_active.is_(True))
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            (User.full_name.ilike(like))
            | (User.email.ilike(like))
            | (User.phone.ilike(like))
        )
    if role_code:
        stmt = stmt.join(UserRole, UserRole.user_id == User.id).join(
            Role, Role.id == UserRole.role_id
        ).where(Role.code == role_code, UserRole.tenant_id == tenant_id)

    stmt = stmt.order_by(User.full_name).limit(limit).offset(offset)
    rows = (await session.execute(stmt)).unique().scalars().all()

    # Count without paging; cheaper as a separate query than scanning all rows.
    count_stmt = select(User.id).where(User.tenant_id == tenant_id)
    if only_active:
        count_stmt = count_stmt.where(User.is_active.is_(True))
    if q:
        like = f"%{q.strip()}%"
        count_stmt = count_stmt.where(
            (User.full_name.ilike(like))
            | (User.email.ilike(like))
            | (User.phone.ilike(like))
        )
    if role_code:
        count_stmt = count_stmt.join(UserRole, UserRole.user_id == User.id).join(
            Role, Role.id == UserRole.role_id
        ).where(Role.code == role_code, UserRole.tenant_id == tenant_id)
    total = len((await session.execute(count_stmt)).scalars().all())

    return [_as_row(u) for u in rows], total


async def create_user(
    session: AsyncSession, *, tenant_id: int, payload: UserCreate
) -> UserRow:
    codes = _validate_roles(payload.role_codes)
    roles = await _resolve_roles(session, tenant_id, codes)

    if payload.email:
        clash = (
            await session.execute(
                select(User.id).where(
                    User.tenant_id == tenant_id, User.email == payload.email
                )
            )
        ).scalar_one_or_none()
        if clash:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Email already in use (user #{clash})",
            )

    # Default page set from the role catalogue if the admin didn't
    # send one. The Users panel UI pre-populates this from the same
    # mapping so the client and server stay aligned, but defending
    # the default here means a curl POST gets sane behaviour too.
    from app.core.admin_pages import default_pages_for_roles, sanitize_pages

    pages: list[str]
    if payload.granted_admin_pages is None:
        pages = default_pages_for_roles(codes)
    else:
        pages = sanitize_pages(payload.granted_admin_pages)

    user = User(
        tenant_id=tenant_id,
        full_name=payload.full_name,
        email=payload.email,
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        is_active=True,
        is_email_verified=True,
        granted_admin_pages=pages,
    )
    session.add(user)
    await session.flush()

    for r in roles:
        session.add(UserRole(tenant_id=tenant_id, user_id=user.id, role_id=r.id))
    await session.commit()

    refreshed = (
        await session.execute(
            select(User)
            .options(selectinload(User.role_assignments).joinedload(UserRole.role))
            .where(User.id == user.id)
        )
    ).unique().scalar_one()
    return _as_row(refreshed)


async def _get(session: AsyncSession, tenant_id: int, user_id: int) -> User:
    user = (
        await session.execute(
            select(User)
            .options(selectinload(User.role_assignments).joinedload(UserRole.role))
            .where(User.id == user_id, User.tenant_id == tenant_id)
        )
    ).unique().scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return user


async def update_user(
    session: AsyncSession,
    *,
    tenant_id: int,
    user_id: int,
    payload: UserUpdate,
) -> UserRow:
    from app.core.admin_pages import sanitize_pages

    user = await _get(session, tenant_id, user_id)
    data = payload.model_dump(exclude_unset=True)
    new_codes = data.pop("role_codes", None)
    new_pages = data.pop("granted_admin_pages", None)
    if new_pages is not None:
        # Filter typos / removed pages before they hit the JSON column.
        user.granted_admin_pages = sanitize_pages(new_pages)

    if "email" in data and data["email"] and data["email"] != user.email:
        clash = (
            await session.execute(
                select(User.id).where(
                    User.tenant_id == tenant_id,
                    User.email == data["email"],
                    User.id != user.id,
                )
            )
        ).scalar_one_or_none()
        if clash:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Email already in use (user #{clash})",
            )

    for k, v in data.items():
        setattr(user, k, v)

    if new_codes is not None:
        codes = _validate_roles(new_codes)
        roles = await _resolve_roles(session, tenant_id, codes)
        # Wipe current assignments and re-create. Cheap for the row sizes
        # we expect and avoids a diff dance.
        await session.execute(
            UserRole.__table__.delete().where(UserRole.user_id == user.id)
        )
        for r in roles:
            session.add(UserRole(tenant_id=tenant_id, user_id=user.id, role_id=r.id))

    await session.commit()
    refreshed = await _get(session, tenant_id, user_id)
    return _as_row(refreshed)


async def set_password(
    session: AsyncSession,
    *,
    tenant_id: int,
    user_id: int,
    new_password: str,
) -> PasswordResult:
    user = await _get(session, tenant_id, user_id)
    user.password_hash = hash_password(new_password)
    user.is_active = True
    user.is_email_verified = True
    user.failed_login_count = 0
    await session.commit()
    return PasswordResult(user_id=user.id, full_name=user.full_name)


async def set_active(
    session: AsyncSession,
    *,
    tenant_id: int,
    user_id: int,
    active: bool,
) -> UserRow:
    user = await _get(session, tenant_id, user_id)
    user.is_active = active
    await session.commit()
    return _as_row(user)


async def delete_user(
    session: AsyncSession, *, tenant_id: int, user_id: int
) -> None:
    user = await _get(session, tenant_id, user_id)
    await session.delete(user)
    await session.commit()
