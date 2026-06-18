"""Auth entities: users, roles, permissions, refresh tokens, multi-role joins.

Notes on scoping:
    - `User`, `Role`, `Permission`, `RolePermission`, `UserRole` are tenant-scoped
      (TenantBase) so each school owns its own users + grants. The Super Admin
      lives on tenant_id = the platform tenant (created by the seed script).
    - Roles are *system* roles (seeded once per tenant from a fixed catalogue)
      plus tenant-defined custom roles in later phases.
"""

from __future__ import annotations

import enum

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import TenantBase


class AuthProvider(str, enum.Enum):
    PASSWORD = "password"
    OTP = "otp"
    GOOGLE = "google"


class User(TenantBase):
    """Anyone who can log in - staff, parent, student.

    Multi-role: a user can hold many roles via UserRole.
    """

    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
        UniqueConstraint("tenant_id", "phone", name="uq_users_tenant_phone"),
        Index("ix_users_tenant_email", "tenant_id", "email"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    full_name = Column(String(180), nullable=False)
    email = Column(String(180), nullable=True)
    phone = Column(String(20), nullable=True)
    password_hash = Column(String(255), nullable=True)  # nullable for OTP-only users
    auth_provider = Column(String(20), nullable=False, default=AuthProvider.PASSWORD.value)

    is_active = Column(Boolean, nullable=False, default=True)
    is_email_verified = Column(Boolean, nullable=False, default=False)
    is_phone_verified = Column(Boolean, nullable=False, default=False)
    last_login_at = Column(DateTime, nullable=True)
    failed_login_count = Column(Integer, nullable=False, default=0)

    # Convenience link for the staff side. Phase 6/7 will model students/teachers properly.
    avatar_url = Column(String(500), nullable=True)

    # Per-user admin web access. Empty list ⇒ no admin web access at
    # all (the user can still log into the mobile app if their role
    # has app-side permissions). Populated by the Users & credentials
    # panel when an admin creates / edits a sub-admin login. Stored as
    # JSON because the page list is fluid (we add admin features
    # often) and putting each page in its own table is heavier than
    # the data warrants.
    granted_admin_pages = Column(JSON, nullable=False, default=list)

    role_assignments = relationship("UserRole", back_populates="user", cascade="all, delete-orphan")

    @property
    def role_codes(self) -> list[str]:
        return [ur.role.code for ur in self.role_assignments if ur.role]


class Role(TenantBase):
    """Named bundle of permissions. Seeded per-tenant from the system catalogue."""

    __tablename__ = "roles"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_roles_tenant_code"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    code = Column(String(40), nullable=False)  # super_admin, school_admin, parent ...
    name = Column(String(80), nullable=False)
    description = Column(String(255), nullable=True)
    level = Column(Integer, nullable=False, default=1)  # L1..L10 hierarchy
    is_system = Column(Boolean, nullable=False, default=True)

    permissions = relationship("RolePermission", back_populates="role", cascade="all, delete-orphan")
    user_assignments = relationship("UserRole", back_populates="role", cascade="all, delete-orphan")

    @property
    def permission_codes(self) -> list[str]:
        return [rp.permission.code for rp in self.permissions if rp.permission]


class Permission(TenantBase):
    """Atomic capability (e.g. ``student.view.all``)."""

    __tablename__ = "permissions"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_permissions_tenant_code"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    code = Column(String(80), nullable=False)
    name = Column(String(120), nullable=False)
    category = Column(String(40), nullable=False)  # student, teacher, fee, ...
    description = Column(String(255), nullable=True)


class RolePermission(TenantBase):
    """Join: role -> permission."""

    __tablename__ = "role_permissions"
    __table_args__ = (
        UniqueConstraint("tenant_id", "role_id", "permission_id", name="uq_role_perm"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True)
    permission_id = Column(Integer, ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False, index=True)

    role = relationship("Role", back_populates="permissions")
    permission = relationship("Permission")


class UserRole(TenantBase):
    """Join: user -> role. Same user can have many roles."""

    __tablename__ = "user_roles"
    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", "role_id", name="uq_user_role"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True)

    # Optional scoping for class teachers / coordinators. Filled in Phase 5/7.
    scope_class_id = Column(Integer, nullable=True)
    scope_department_id = Column(Integer, nullable=True)

    user = relationship("User", back_populates="role_assignments")
    role = relationship("Role", back_populates="user_assignments")


class RefreshToken(TenantBase):
    """Active refresh tokens. Logout = delete row; rotate on use."""

    __tablename__ = "refresh_tokens"
    __table_args__ = (
        Index("ix_refresh_tenant_user", "tenant_id", "user_id"),
        Index("ix_refresh_token_jti", "jti"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    jti = Column(String(64), nullable=False, unique=True)
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    user_agent = Column(String(255), nullable=True)
    ip_address = Column(String(64), nullable=True)
