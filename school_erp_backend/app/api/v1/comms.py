"""Communication endpoints (Phase 12)."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import AuthPrincipal, get_current_principal, require_roles
from app.core.tenant_session import platform_session, tenant_scoped_session
from app.models.comms import AnnouncementAudience, DeliveryStatus
from app.schemas.comms import (
    AnnouncementRead,
    AnnouncementWrite,
    MessageRead,
    MessageSend,
    NotificationOutboxRead,
    NotificationRead,
    PublishResult,
    TemplateRead,
    TemplateWrite,
)
from app.services.comms import (
    create_announcement,
    inbox_for,
    list_announcements,
    list_notifications_for,
    list_outbox,
    list_templates,
    mark_all_read,
    mark_message_read,
    mark_notification_read,
    send_message,
    sent_for,
    upsert_template,
)


_school_admin = require_roles("school_admin", "principal", "vice_principal")
_school_staff = require_roles(
    "school_admin", "principal", "vice_principal", "coordinator",
    "class_teacher", "subject_teacher", "office_staff",
)


# ---- School admin (templates + announcements + outbox) --------------------


sa_router = APIRouter(
    prefix="/school-admin/communication",
    tags=["school-admin"],
    dependencies=[Depends(_school_staff)],
)


@sa_router.get("/templates", response_model=list[TemplateRead])
async def list_templates_route(session: AsyncSession = Depends(tenant_scoped_session)):
    return await list_templates(session)


@sa_router.put("/templates/{code}", response_model=TemplateRead)
async def upsert_template_route(
    code: str,
    payload: TemplateWrite,
    principal: AuthPrincipal = Depends(_school_admin),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    if payload.code != code:
        # Allow renaming via PUT body if needed; otherwise enforce match.
        payload = payload.model_copy(update={"code": code})
    return await upsert_template(session, principal.tenant_id, payload)


@sa_router.get("/announcements", response_model=list[AnnouncementRead])
async def list_announcements_route(
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await list_announcements(session)


@sa_router.post(
    "/announcements", response_model=PublishResult, status_code=status.HTTP_201_CREATED
)
async def create_announcement_route(
    payload: AnnouncementWrite,
    principal: AuthPrincipal = Depends(_school_admin),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    obj, fanned = await create_announcement(
        session, principal.tenant_id, principal.user_id, payload
    )
    return PublishResult(announcement_id=obj.id, fanned_out_to=fanned)


@sa_router.get("/outbox", response_model=list[NotificationOutboxRead])
async def list_outbox_route(
    status_filter: Optional[DeliveryStatus] = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await list_outbox(session, status_filter=status_filter, limit=limit)


# ---- Public announcements feed (any authenticated user) -------------------


router = APIRouter(prefix="", tags=["comms"])


@router.get("/announcements", response_model=list[AnnouncementRead])
async def feed(
    principal: AuthPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(platform_session),
):
    """Anyone in the tenant gets the published announcements they're targeted by.
    The fan-out already filtered into Notification rows; this endpoint gives the
    school's own bulletin-board view."""
    from sqlalchemy import select
    from app.models.comms import Announcement

    rows = list(
        (
            await session.execute(
                select(Announcement)
                .where(
                    Announcement.tenant_id == principal.tenant_id,
                    Announcement.published_at.is_not(None),
                )
                .order_by(Announcement.is_pinned.desc(), Announcement.published_at.desc())
                .limit(50)
            )
        ).scalars().all()
    )
    return rows


# ---- Direct messaging ------------------------------------------------------


messages_router = APIRouter(prefix="/messages", tags=["comms"])


@messages_router.get("", response_model=list[MessageRead])
async def my_inbox(
    principal: AuthPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(platform_session),
):
    return await inbox_for(session, principal.user_id)


@messages_router.get("/sent", response_model=list[MessageRead])
async def my_sent(
    principal: AuthPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(platform_session),
):
    return await sent_for(session, principal.user_id)


@messages_router.post("", response_model=MessageRead, status_code=status.HTTP_201_CREATED)
async def send_route(
    payload: MessageSend,
    principal: AuthPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(platform_session),
):
    return await send_message(session, principal.tenant_id, principal.user_id, payload)


@messages_router.post("/{message_id}/read", response_model=MessageRead)
async def mark_read_route(
    message_id: int,
    principal: AuthPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(platform_session),
):
    return await mark_message_read(session, message_id, principal.user_id)


# ---- Notifications (replaces Phase 10 stub) -------------------------------


notif_router = APIRouter(prefix="/notifications", tags=["notifications"])


@notif_router.get("", response_model=list[NotificationRead])
async def list_route(
    only_unread: bool = False,
    limit: int = Query(default=50, ge=1, le=200),
    principal: AuthPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(platform_session),
):
    return await list_notifications_for(
        session, principal.user_id, only_unread=only_unread, limit=limit
    )


@notif_router.post("/{notif_id}/read", response_model=NotificationRead)
async def read_route(
    notif_id: int,
    principal: AuthPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(platform_session),
):
    return await mark_notification_read(session, notif_id, principal.user_id)


@notif_router.post("/read-all")
async def read_all_route(
    principal: AuthPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(platform_session),
):
    n = await mark_all_read(session, principal.user_id)
    return {"marked": n}
