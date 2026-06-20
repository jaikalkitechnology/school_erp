"""Auth extras: password-reset OTPs + per-user device tokens for FCM.

Both tables are tenant-scoped so OTPs / devices can't leak across
schools, and so a tenant teardown drops them cleanly.
"""

from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)

from app.database import TenantBase


class PasswordResetOtp(TenantBase):
    """One row per "Forgot password" request.

    The OTP itself is stored only as a salted hash; we never persist the
    plaintext code. ``consumed_at`` flips to non-null the moment the user
    successfully resets — the row is kept around for audit / rate
    limiting but can never be reused. Service code rejects rows that are
    consumed, expired (``expires_at < now``), or whose attempt counter
    has tripped (``attempt_count >= 5``).
    """

    __tablename__ = "password_reset_otps"
    __table_args__ = (
        Index("ix_pwd_otp_user", "tenant_id", "user_id"),
        Index("ix_pwd_otp_active", "user_id", "consumed_at", "expires_at"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    code_hash = Column(String(128), nullable=False)
    delivery_channel = Column(String(16), nullable=False)  # "sms" | "email"
    expires_at = Column(DateTime, nullable=False)
    consumed_at = Column(DateTime, nullable=True)
    attempt_count = Column(Integer, nullable=False, default=0)


class UserDevice(TenantBase):
    """A logged-in device's FCM push token.

    Same (user_id, fcm_token) → upsert: re-registration just updates the
    ``last_seen_at`` / ``app_version`` / ``platform`` fields instead of
    creating duplicate rows, which is what FCM gives us anyway (each
    install has exactly one token at a time).
    """

    __tablename__ = "user_devices"
    __table_args__ = (
        UniqueConstraint("user_id", "fcm_token", name="uq_user_device_token"),
        Index("ix_user_device_user", "tenant_id", "user_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    fcm_token = Column(String(255), nullable=False)
    platform = Column(String(16), nullable=False, default="android")  # android | ios | web
    app_version = Column(String(32), nullable=True)
    device_label = Column(String(128), nullable=True)
    last_seen_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
