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
    # Per-announcement push override. When None we use whatever the
    # ``announcement.posted`` template has configured. Set to False to
    # silence push for one specific announcement (eg. low-priority
    # notice that shouldn't buzz everyone's phone).
    send_push: Optional[bool] = None
    # Only these people (who must be in the audience) get it. Used with
    # the staff / parents / students audiences; empty = everyone in it.
    recipient_user_ids: Optional[List[int]] = None


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
    recipient_user_ids: Optional[List[int]] = None


class PublishResult(BaseModel):
    announcement_id: int
    fanned_out_to: int
    # Phones actually reached via FCM (drain ran synchronously inside
    # the publish handler). Zero if every recipient has no active
    # device, or if FCM is misconfigured.
    push_sent: int = 0
    # FCM rejected sends (dead token, mismatched-credential, etc).
    # Surfaces in the admin UI as " - N pushes failed" so silent
    # rot is impossible to miss.
    push_failed: int = 0
    # Recipients who got no push: no phone signed in to the app, or FCM
    # is off on the server (then push_unavailable_reason says why).
    push_skipped: int = 0
    push_unavailable_reason: Optional[str] = None


class PushStatus(BaseModel):
    """Whether this server can send phone pushes, and how many phones in
    the school have registered for them."""

    available: bool
    reason: Optional[str] = None
    active_devices: int
    users_with_devices: int


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
