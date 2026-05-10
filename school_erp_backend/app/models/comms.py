"""Communication (Phase 12).

Pieces:
    NotificationTemplate  - reusable subject + body per language and channel set
    Announcement          - school-wide / class / role-targeted notice board entry
    Notification          - per-recipient row (the in-app inbox)
    NotificationOutbox    - queued external delivery (sms / email / push / whatsapp)
    Message               - lightweight 1-1 direct message between users
    MessageRead           - per-recipient read receipt
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
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import TenantBase


class Channel(str, enum.Enum):
    IN_APP = "in_app"
    SMS = "sms"
    EMAIL = "email"
    PUSH = "push"
    WHATSAPP = "whatsapp"


class DeliveryStatus(str, enum.Enum):
    QUEUED = "queued"
    SENT = "sent"
    FAILED = "failed"
    SKIPPED = "skipped"


class AnnouncementAudience(str, enum.Enum):
    ALL = "all"           # everyone in the school
    STAFF = "staff"       # any teacher / coordinator / admin role
    PARENTS = "parents"   # parents only
    STUDENTS = "students"
    CLASS = "class"       # audience_id = class_def_id
    SECTION = "section"   # audience_id = section_id


class NotificationTemplate(TenantBase):
    __tablename__ = "notification_templates"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_notification_templates_code"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    code = Column(String(80), nullable=False)  # leave.decided / announcement.posted ...
    subject_en = Column(String(255), nullable=False, default="")
    body_en = Column(Text, nullable=False, default="")
    subject_hi = Column(String(255), nullable=True)
    body_hi = Column(Text, nullable=True)
    subject_mr = Column(String(255), nullable=True)
    body_mr = Column(Text, nullable=True)
    channels = Column(JSON, nullable=False, default=list)  # list of Channel codes
    is_active = Column(Boolean, nullable=False, default=True)


class Announcement(TenantBase):
    __tablename__ = "announcements"
    __table_args__ = (
        Index("ix_announcements_tenant_published", "tenant_id", "published_at"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    title = Column(String(180), nullable=False)
    body = Column(Text, nullable=False)
    audience = Column(String(20), nullable=False, default=AnnouncementAudience.ALL.value)
    audience_id = Column(Integer, nullable=True)  # class_def_id / section_id when scoped
    author_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    published_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    is_pinned = Column(Boolean, nullable=False, default=False)


class Notification(TenantBase):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_tenant_user_read", "tenant_id", "recipient_user_id", "read_at"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    recipient_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False, default="")
    kind = Column(String(40), nullable=False, default="generic")
    deeplink = Column(String(500), nullable=True)
    source_type = Column(String(40), nullable=True)
    source_id = Column(Integer, nullable=True)
    read_at = Column(DateTime, nullable=True)


class NotificationOutbox(TenantBase):
    __tablename__ = "notification_outbox"
    __table_args__ = (
        Index("ix_notification_outbox_tenant_status", "tenant_id", "status"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    notification_id = Column(Integer, ForeignKey("notifications.id", ondelete="CASCADE"), nullable=True)
    recipient_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    channel = Column(String(20), nullable=False)
    address = Column(String(255), nullable=True)  # phone / email / push token / wa number
    subject = Column(String(255), nullable=True)
    body = Column(Text, nullable=False, default="")
    status = Column(String(12), nullable=False, default=DeliveryStatus.QUEUED.value)
    provider_ref = Column(String(120), nullable=True)
    error = Column(Text, nullable=True)


class Message(TenantBase):
    __tablename__ = "direct_messages"
    __table_args__ = (
        Index("ix_messages_tenant_recipient", "tenant_id", "recipient_user_id"),
        Index("ix_messages_tenant_sender", "tenant_id", "sender_user_id"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"},
    )

    sender_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    recipient_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    subject = Column(String(180), nullable=True)
    body = Column(Text, nullable=False)
    read_at = Column(DateTime, nullable=True)
