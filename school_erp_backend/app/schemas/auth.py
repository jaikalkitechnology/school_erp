"""Pydantic schemas for the auth API."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class LoginRequest(BaseModel):
    identifier: str = Field(min_length=3, max_length=180, description="Email or phone")
    password: str = Field(min_length=4, max_length=128)
    subdomain: Optional[str] = Field(
        default=None,
        max_length=63,
        description="Optional explicit tenant when the request didn't come through a tenant subdomain.",
    )

    @field_validator("identifier")
    @classmethod
    def _strip_identifier(cls, v: str) -> str:
        return v.strip().lower()


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = None  # If omitted, all sessions revoked


class RoleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    code: str
    name: str
    level: int


class CurrentUser(BaseModel):
    id: int
    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    tenant_id: int
    tenant_subdomain: Optional[str] = None
    school_name: Optional[str] = None
    roles: List[str]
    permissions: List[str]
    primary_role: Optional[str] = None
    # Empty list ⇒ no admin web access. The sidebar is filtered against
    # this on every render so non-admin users (parents, app-only staff)
    # can't accidentally land on /students etc. Implicitly considered
    # "all pages" when the user is a school_admin / principal — that
    # check lives client-side because those roles bypass page gating.
    granted_admin_pages: List[str] = []


class LoginResponse(BaseModel):
    user: CurrentUser
    tokens: TokenPair


class ParentChildRead(BaseModel):
    student_id: int
    full_name: str
    admission_number: str
    current_class_label: Optional[str] = None
    is_primary: bool = False


class ParentChildSwitch(BaseModel):
    student_id: int


class ForgotPasswordRequest(BaseModel):
    identifier: str
    subdomain: Optional[str] = None


class ResetPasswordRequest(BaseModel):
    identifier: str
    subdomain: Optional[str] = None
    otp: str = Field(min_length=4, max_length=12)
    new_password: str = Field(min_length=6, max_length=128)
