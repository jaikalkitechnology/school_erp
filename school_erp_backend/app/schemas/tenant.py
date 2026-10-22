"""Pydantic schemas for tenant + plan APIs."""

import re
from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.tenant import (
    BillingCycle,
    SchoolType,
    SubscriptionStatus,
    TenantStatus,
)


class SubscriptionPlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str
    monthly_price: float
    annual_price: float
    student_limit: int
    teacher_limit: int
    storage_gb: int
    sms_quota: int
    modules_included: List[str] = Field(default_factory=list)
    is_active: bool


class SubscriptionPlanWrite(BaseModel):
    code: str = Field(min_length=2, max_length=40, pattern=r"^[a-z0-9_-]+$")
    name: str = Field(min_length=2, max_length=80)
    monthly_price: float = Field(ge=0)
    annual_price: float = Field(ge=0)
    student_limit: int = Field(ge=0, default=0)
    teacher_limit: int = Field(ge=0, default=0)
    storage_gb: int = Field(ge=0, default=5)
    sms_quota: int = Field(ge=0, default=0)
    modules_included: List[str] = Field(default_factory=list)
    is_active: bool = True


class SubscriptionPlanUpdate(BaseModel):
    name: Optional[str] = None
    monthly_price: Optional[float] = Field(default=None, ge=0)
    annual_price: Optional[float] = Field(default=None, ge=0)
    student_limit: Optional[int] = Field(default=None, ge=0)
    teacher_limit: Optional[int] = Field(default=None, ge=0)
    storage_gb: Optional[int] = Field(default=None, ge=0)
    sms_quota: Optional[int] = Field(default=None, ge=0)
    modules_included: Optional[List[str]] = None
    is_active: Optional[bool] = None


class TrialExtension(BaseModel):
    days: int = Field(ge=1, le=180)
    reason: Optional[str] = None


class PlanChange(BaseModel):
    plan_code: str
    billing_cycle: Optional[str] = "monthly"


class AnalyticsOverview(BaseModel):
    total_tenants: int
    active_tenants: int
    trial_tenants: int
    suspended_tenants: int
    total_students: int
    total_teachers: int
    total_storage_used_mb: float
    mrr: float
    by_state: dict[str, int]
    by_plan: dict[str, int]


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int
    actor_email: Optional[str]
    actor_role: Optional[str]
    action: str
    target_type: Optional[str]
    target_id: Optional[int]
    summary: Optional[str]
    ip_address: Optional[str]
    created_at: datetime


class SchoolAdminSet(BaseModel):
    """The school admin's login, set by the super admin. If a user with
    this email already exists in the school, its name and password are
    updated instead of a second account being created."""

    full_name: str = Field(min_length=2, max_length=180)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def _strong_enough(cls, v: str) -> str:
        if not re.search(r"[A-Za-z]", v) or not re.search(r"\d", v):
            raise ValueError("Password needs at least one letter and one number")
        return v


class SchoolAdminRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: Optional[str]
    is_active: bool
    last_login_at: Optional[datetime] = None


class TenantCreate(BaseModel):
    school_name: str = Field(min_length=2, max_length=180)
    school_code: str = Field(min_length=2, max_length=40)
    subdomain: str = Field(min_length=3, max_length=63, pattern=r"^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$")
    plan_code: str = Field(min_length=2, max_length=40)

    affiliation_board: Optional[str] = None
    school_type: Optional[SchoolType] = None
    medium: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    timezone: str = "Asia/Kolkata"

    primary_color: str = "#E85D2E"
    secondary_color: str = "#0F766E"

    # The school's first admin login. Optional so scripts (eg. the demo
    # seed) can create a school without one.
    admin: Optional[SchoolAdminSet] = None


class TenantUpdate(BaseModel):
    school_name: Optional[str] = None
    affiliation_board: Optional[str] = None
    school_type: Optional[SchoolType] = None
    medium: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    timezone: Optional[str] = None
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None


class TenantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    school_name: str
    school_code: str
    subdomain: str
    affiliation_board: Optional[str]
    school_type: Optional[SchoolType]
    medium: Optional[str]
    address: Optional[str] = None
    city: Optional[str]
    state: Optional[str]
    pincode: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    timezone: str
    primary_color: str
    secondary_color: str
    logo_url: Optional[str]
    plan_id: Optional[int]
    student_limit: int
    teacher_limit: int
    storage_limit_mb: int
    status: TenantStatus
    subscription_start: Optional[datetime]
    subscription_end: Optional[datetime]
    created_at: datetime
    plan: Optional[SubscriptionPlanRead] = None


class TenantHealth(BaseModel):
    tenant_id: int
    subdomain: str
    status: TenantStatus
    storage_used_mb: float
    storage_limit_mb: int
    storage_used_pct: float
    student_limit: int
    teacher_limit: int
    last_active_at: Optional[datetime] = None


class ImpersonationToken(BaseModel):
    token: str
    tenant_id: int
    subdomain: str
    expires_in_seconds: int


class SubscriptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int
    plan_id: int
    start_date: datetime
    end_date: datetime
    billing_cycle: BillingCycle
    status: SubscriptionStatus
    auto_renew: bool
    paid_until: Optional[datetime]
    amount: float


class TenantSettingUpsert(BaseModel):
    category: str = "general"
    key: str
    value: Any
