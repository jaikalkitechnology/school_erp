"""Communication schemas (Phase 12)."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.comms import AnnouncementAudience, Channel, DeliveryStatus


# ---- Templates -------------------------------------------------------------


class TemplateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    subject_en: str
    body_en: str
    subject_hi: Optional[str]
    body_hi: Optional[str]
    subject_mr: Optional[str]
    body_mr: Optional[str]
    channels: List[Channel]
    is_active: bool


class TemplateWrite(BaseModel):
    code: str = Field(min_length=2, max_length=80)
    subject_en: str
    body_en: str
    subject_hi: Optional[str] = None
    body_hi: Optional[str] = None
    subject_mr: Optional[str] = None
    body_mr: Optional[str] = None
    channels: List[Channel] = Field(default_factory=lambda: [Channel.IN_APP])


# ---- Announcements ---------------------------------------------------------


class AnnouncementWrite(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    body: str = Field(min_length=1)
    audience: AnnouncementAudience = AnnouncementAudience.ALL
    audience_id: Optional[int] = None
    expires_at: Optional[datetime] = None
    is_pinned: bool = False
    publish: bool = True


class AnnouncementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    body: str
    audience: AnnouncementAudience
    audience_id: Optional[int]
    author_user_id: Optional[int]
    published_at: Optional[datetime]
    expires_at: Optional[datetime]
    is_pinned: bool


class PublishResult(BaseModel):
    announcement_id: int
    fanned_out_to: int


# ---- Notifications ---------------------------------------------------------


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    body: str
    kind: str
    deeplink: Optional[str]
    source_type: Optional[str]
    source_id: Optional[int]
    read_at: Optional[datetime]
    created_at: datetime


class NotificationOutboxRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    notification_id: Optional[int]
    recipient_user_id: int
    channel: Channel
    address: Optional[str]
    subject: Optional[str]
    body: str
    status: DeliveryStatus
    provider_ref: Optional[str]
    error: Optional[str]
    created_at: datetime


# ---- Messages --------------------------------------------------------------


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    sender_user_id: Optional[int]
    recipient_user_id: int
    subject: Optional[str]
    body: str
    read_at: Optional[datetime]
    created_at: datetime
    # Optional, populated by the inbox/sent endpoints when they can
    # cheaply join User. Lets the parent / admin UIs render the sender's
    # display name without a second round-trip.
    sender_name: Optional[str] = None


class MessageSend(BaseModel):
    recipient_user_id: int
    subject: Optional[str] = Field(default=None, max_length=180)
    body: str = Field(min_length=1)
