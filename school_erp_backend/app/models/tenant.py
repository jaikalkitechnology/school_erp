"""Tenant + subscription tables.

These four tables are the spine of the SaaS:
    - SubscriptionPlan: catalogue (Basic / Standard / Premium / Enterprise)
    - Tenant          : one row per school (one subdomain, one logo, one plan)
    - Subscription    : tenant <-> plan over time (history of upgrades)
    - TenantSettings  : free-form per-tenant kv store

Tenant is the *one* table that does NOT inherit TenantBase — it has no
``tenant_id`` because it *is* the tenant.
"""

from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from app.database import Base, TenantBase, TimestampMixin


class TenantStatus(str, enum.Enum):
    TRIAL = "trial"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"


class SchoolType(str, enum.Enum):
    PRESCHOOL = "preschool"
    PRIMARY = "primary"
    SECONDARY = "secondary"
    SENIOR_SECONDARY = "senior_secondary"
    K12 = "k12"


class BillingCycle(str, enum.Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class SubscriptionPlan(Base, TimestampMixin):
    """Catalogue of plans Jaikalki sells."""

    __tablename__ = "subscription_plans"
    __table_args__ = (
        UniqueConstraint("code", name="uq_plans_code"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(80), nullable=False)
    code = Column(String(40), nullable=False)  # basic / standard / premium / enterprise
    monthly_price = Column(Numeric(10, 2), nullable=False, default=0)
    annual_price = Column(Numeric(10, 2), nullable=False, default=0)
    student_limit = Column(Integer, nullable=False, default=0)  # 0 = unlimited
    teacher_limit = Column(Integer, nullable=False, default=0)
    storage_gb = Column(Integer, nullable=False, default=5)
    sms_quota = Column(Integer, nullable=False, default=0)
    modules_included = Column(JSON, nullable=False, default=list)
    features_json = Column(JSON, nullable=False, default=dict)
    is_active = Column(Boolean, nullable=False, default=True)


class Tenant(Base, TimestampMixin):
    """One row per school. All other tenant-scoped tables FK back to ``id``."""

    __tablename__ = "tenants"
    __table_args__ = (
        UniqueConstraint("subdomain", name="uq_tenants_subdomain"),
        UniqueConstraint("school_code", name="uq_tenants_school_code"),
        Index("ix_tenants_status", "status"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Identity
    school_name = Column(String(180), nullable=False)
    school_code = Column(String(40), nullable=False)
    subdomain = Column(String(63), nullable=False)

    # Profile
    affiliation_board = Column(String(80), nullable=True)  # CBSE / ICSE / State
    school_type = Column(Enum(SchoolType, native_enum=False), nullable=True)
    medium = Column(String(40), nullable=True)  # English / Hindi / Marathi …
    address = Column(Text, nullable=True)
    city = Column(String(80), nullable=True)
    state = Column(String(80), nullable=True)
    pincode = Column(String(12), nullable=True)
    phone = Column(String(20), nullable=True)
    email = Column(String(180), nullable=True)
    timezone = Column(String(40), nullable=False, default="Asia/Kolkata")

    # Branding
    logo_url = Column(String(500), nullable=True)
    primary_color = Column(String(9), nullable=False, default="#E85D2E")
    secondary_color = Column(String(9), nullable=False, default="#0F766E")

    # Plan + lifecycle
    plan_id = Column(Integer, ForeignKey("subscription_plans.id", ondelete="RESTRICT"), nullable=True)
    subscription_start = Column(DateTime, nullable=True)
    subscription_end = Column(DateTime, nullable=True)
    student_limit = Column(Integer, nullable=False, default=500)
    teacher_limit = Column(Integer, nullable=False, default=50)
    storage_limit_mb = Column(Integer, nullable=False, default=5120)
    status = Column(Enum(TenantStatus, native_enum=False), nullable=False, default=TenantStatus.TRIAL)

    modules_enabled = Column(JSON, nullable=False, default=list)
    onboarded_by = Column(Integer, nullable=True)  # super-admin user id (Phase 2)

    plan = relationship("SubscriptionPlan", lazy="joined")
    subscriptions = relationship("Subscription", back_populates="tenant", cascade="all, delete-orphan")
    settings = relationship("TenantSettings", back_populates="tenant", cascade="all, delete-orphan")

    @property
    def is_active(self) -> bool:
        return self.status in {TenantStatus.TRIAL, TenantStatus.ACTIVE}

    def is_within_subscription(self, now: datetime | None = None) -> bool:
        now = now or datetime.now(timezone.utc).replace(tzinfo=None)
        if self.subscription_end is None:
            return self.status == TenantStatus.TRIAL
        return self.subscription_end >= now


class Subscription(TenantBase):
    """History of plan assignments. The latest active row drives entitlement."""

    __tablename__ = "subscriptions"

    plan_id = Column(Integer, ForeignKey("subscription_plans.id", ondelete="RESTRICT"), nullable=False, index=True)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    billing_cycle = Column(Enum(BillingCycle, native_enum=False), nullable=False, default=BillingCycle.MONTHLY)
    status = Column(Enum(SubscriptionStatus, native_enum=False), nullable=False, default=SubscriptionStatus.ACTIVE)
    auto_renew = Column(Boolean, nullable=False, default=True)
    paid_until = Column(DateTime, nullable=True)
    amount = Column(Numeric(10, 2), nullable=False, default=0)

    tenant = relationship("Tenant", back_populates="subscriptions")
    plan = relationship("SubscriptionPlan")


class TenantSettings(TenantBase):
    """Free-form per-tenant key/value bag.

    Categories: ``branding``, ``academic``, ``communication``, ``finance``…
    """

    __tablename__ = "tenant_settings"
    __table_args__ = (
        UniqueConstraint("tenant_id", "category", "key", name="uq_settings_tenant_category_key"),
        Index("ix_settings_tenant_category", "tenant_id", "category"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    category = Column(String(40), nullable=False, default="general")
    key = Column(String(80), nullable=False)
    value = Column(JSON, nullable=True)

    tenant = relationship("Tenant", back_populates="settings")


class TenantUsageSnapshot(TenantBase):
    """Periodic snapshot of usage. Filled by Phase 1 background sweep."""

    __tablename__ = "tenant_usage_snapshots"

    students_count = Column(Integer, nullable=False, default=0)
    teachers_count = Column(Integer, nullable=False, default=0)
    storage_used_mb = Column(BigInteger, nullable=False, default=0)
    sms_sent_30d = Column(Integer, nullable=False, default=0)
    api_calls_24h = Column(Integer, nullable=False, default=0)
    last_active_at = Column(DateTime, nullable=True, server_default=func.now())
