"""Communication endpoints (Phase 12)."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel
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
    refresh_default_template_channels,
    seed_default_templates,
    create_announcement,
    delete_announcement,
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


@sa_router.post("/templates/sync-defaults")
async def sync_default_templates_route(
    principal: AuthPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    """Idempotent: inserts any predefined template rows the tenant
    doesn't have yet (eg. homework.assigned was added after the tenant
    was seeded) AND merges the default channel list into existing rows
    so a newly-added channel like ``push`` lights up without losing the
    tenant's own customisations (eg. they added SMS).

    Call this once per tenant after deploying a new channel. Safe to
    re-run."""
    created = await seed_default_templates(session, principal.tenant_id)
    refreshed = await refresh_default_template_channels(
        session, tenant_id=principal.tenant_id,
    )
    return {"created": created, "channels_refreshed": refreshed}


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


@sa_router.delete(
    "/announcements/{announcement_id}", status_code=status.HTTP_200_OK,
)
async def delete_announcement_route(
    announcement_id: int,
    principal: AuthPrincipal = Depends(_school_admin),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    """Delete one announcement + every notification it fan-out'd."""
    notifs_removed = await delete_announcement(
        session,
        tenant_id=principal.tenant_id,
        announcement_id=announcement_id,
    )
    return {"deleted": announcement_id, "notifications_removed": notifs_removed}


class _BulkDeleteBody(BaseModel):
    ids: list[int]


@sa_router.post("/announcements/bulk-delete")
async def bulk_delete_announcements_route(
    payload: _BulkDeleteBody,
    principal: AuthPrincipal = Depends(_school_admin),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    """Tick-and-delete from the list. Skips IDs that aren't this
    tenant's. Returns per-id success + cumulative notification cleanup
    count."""
    deleted: list[int] = []
    skipped: list[int] = []
    total_notifs = 0
    for aid in payload.ids:
        try:
            n = await delete_announcement(
                session,
                tenant_id=principal.tenant_id,
                announcement_id=aid,
            )
            deleted.append(aid)
            total_notifs += n
        except Exception:
            skipped.append(aid)
    return {
        "deleted": deleted,
        "skipped": skipped,
        "notifications_removed": total_notifs,
    }


@sa_router.get("/outbox", response_model=list[NotificationOutboxRead])
async def list_outbox_route(
    status_filter: Optional[DeliveryStatus] = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(tenant_scoped_session),
):
    return await list_outbox(session, status_filter=status_filter, limit=limit)


@sa_router.post("/notifications/sweep")
async def sweep_notifications_route(
    days: int = Query(default=30, ge=1, le=365),
):
    """Force a retention sweep right now. The lifespan task runs this
    every 24 hours automatically; this endpoint exists so the admin
    can clear out old notifications on demand."""
    from app.services.comms import sweep_old_notifications

    removed = await sweep_old_notifications(days=days)
    return {"removed": removed, "older_than_days": days}


# ---- Public announcements feed (any authenticated user) -------------------


router = APIRouter(prefix="", tags=["comms"])


@router.get("/announcements", response_model=list[AnnouncementRead])
async def feed(
    principal: AuthPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(platform_session),
):
    """Bulletin-board view of the announcements *this user is actually
    targeted by*.

    Previously this endpoint returned every published announcement on
    the tenant — so a parent picking ``Audience: Parents`` for a notice
    would still find their staff-only notices listed because the
    bulletin feed didn't filter. The fan-out already wrote per-user
    Notification rows; mirror the same audience logic here so the feed
    matches what they actually got pushed."""
    from sqlalchemy import select
    from app.models.comms import Announcement, AnnouncementAudience
    from app.models.auth import Role, UserRole
    from app.models.parent import ParentChildMapping, Parent, Student

    # Resolve the caller's role codes + (if a parent) the linked
    # children's class + section ids. We compute these once and use
    # them to decide which announcement rows to surface.
    role_codes = set(principal.roles or [])

    student_class_ids: set[int] = set()
    student_section_ids: set[int] = set()
    if "parent" in role_codes:
        parent = (
            await session.execute(
                select(Parent).where(
                    Parent.tenant_id == principal.tenant_id,
                    Parent.user_id == principal.user_id,
                )
            )
        ).scalar_one_or_none()
        if parent is not None:
            kids = list(
                (
                    await session.execute(
                        select(Student)
                        .join(
                            ParentChildMapping,
                            ParentChildMapping.student_id == Student.id,
                        )
                        .where(
                            ParentChildMapping.tenant_id == principal.tenant_id,
                            ParentChildMapping.parent_id == parent.id,
                        )
                    )
                ).scalars().all()
            )
            for k in kids:
                if k.class_def_id is not None:
                    student_class_ids.add(k.class_def_id)
                if k.section_id is not None:
                    student_section_ids.add(k.section_id)

    # If the caller is the student themselves, surface their own
    # class/section too.
    if "student" in role_codes:
        me = (
            await session.execute(
                select(Student).where(
                    Student.tenant_id == principal.tenant_id,
                    Student.user_id == principal.user_id,
                )
            )
        ).scalar_one_or_none()
        if me is not None:
            if me.class_def_id is not None:
                student_class_ids.add(me.class_def_id)
            if me.section_id is not None:
                student_section_ids.add(me.section_id)

    staff_role_codes = {
        "school_admin", "principal", "vice_principal", "coordinator",
        "class_teacher", "subject_teacher", "office_staff", "accountant",
        "librarian", "transport_manager", "hostel_warden",
    }
    is_staff = bool(role_codes & staff_role_codes)
    is_parent = "parent" in role_codes
    is_student = "student" in role_codes

    rows = list(
        (
            await session.execute(
                select(Announcement)
                .where(
                    Announcement.tenant_id == principal.tenant_id,
                    Announcement.published_at.is_not(None),
                )
                .order_by(
                    Announcement.is_pinned.desc(),
                    Announcement.published_at.desc(),
                )
                .limit(200)
            )
        ).scalars().all()
    )

    def visible(a: Announcement) -> bool:
        aud = a.audience
        if aud == AnnouncementAudience.ALL.value:
            return True
        if aud == AnnouncementAudience.STAFF.value:
            return is_staff
        if aud == AnnouncementAudience.PARENTS.value:
            return is_parent
        if aud == AnnouncementAudience.STUDENTS.value:
            return is_student
        if aud == AnnouncementAudience.CLASS.value:
            # Class-scoped notice → parents of students in that class
            # or the student themselves. Staff don't see class notices
            # unless they're also class teacher of a section in that
            # class — keeping it simple: only parents + students see
            # class notices.
            return (
                a.audience_id is not None
                and a.audience_id in student_class_ids
            )
        if aud == AnnouncementAudience.SECTION.value:
            return (
                a.audience_id is not None
                and a.audience_id in student_section_ids
            )
        return False

    return [a for a in rows if visible(a)][:50]


# ---- Direct messaging ------------------------------------------------------


messages_router = APIRouter(prefix="/messages", tags=["comms"])


async def _attach_sender_names(
    session: AsyncSession, rows: list, *, key: str,
) -> list[MessageRead]:
    """Decorate the inbox/sent rows with sender_name (or, for the sent
    list, recipient_name) so the consumer UI can render the counterpart
    in a single round trip."""
    from sqlalchemy import select

    from app.models.auth import User

    ids = {getattr(r, key) for r in rows if getattr(r, key) is not None}
    name_by_id: dict[int, str] = {}
    if ids:
        for u in (
            (
                await session.execute(
                    select(User.id, User.full_name).where(User.id.in_(ids))
                )
            ).all()
        ):
            name_by_id[u.id] = u.full_name
    out: list[MessageRead] = []
    for r in rows:
        peer_id = getattr(r, key)
        out.append(
            MessageRead(
                id=r.id,
                sender_user_id=r.sender_user_id,
                recipient_user_id=r.recipient_user_id,
                subject=r.subject,
                body=r.body,
                read_at=r.read_at,
                created_at=r.created_at,
                sender_name=name_by_id.get(peer_id) if peer_id else None,
            )
        )
    return out


@messages_router.get("", response_model=list[MessageRead])
async def my_inbox(
    principal: AuthPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(platform_session),
):
    rows = await inbox_for(session, principal.user_id)
    return await _attach_sender_names(session, rows, key="sender_user_id")


@messages_router.get("/sent", response_model=list[MessageRead])
async def my_sent(
    principal: AuthPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(platform_session),
):
    rows = await sent_for(session, principal.user_id)
    # On the sent list, "sender_name" carries the *recipient* name so
    # the same field is meaningful — i.e. "who am I talking to?".
    return await _attach_sender_names(session, rows, key="recipient_user_id")


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
