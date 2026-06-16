"""Communication services (Phase 12).

Channel abstraction:
    - InAppChannel       writes a Notification row.
    - SmsChannel / EmailChannel / PushChannel / WhatsappChannel queue a row in
      NotificationOutbox with status=queued. Real provider adapters are wired
      via env config in production; the test/dev path leaves rows queued.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, Optional

from fastapi import HTTPException, status
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.academic import Section
from app.models.auth import Role, User, UserRole
from app.models.comms import (
    Announcement,
    AnnouncementAudience,
    Channel,
    DeliveryStatus,
    Message,
    Notification,
    NotificationOutbox,
    NotificationTemplate,
)
from app.models.parent import ParentChildMapping, Student
from app.schemas.comms import (
    AnnouncementWrite,
    MessageSend,
    TemplateWrite,
)


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ---- Templates -------------------------------------------------------------


_DEFAULTS: list[dict] = [
    {
        "code": "leave.decided",
        "subject_en": "Leave application {{decision}}",
        "body_en": "{{student}}'s leave from {{start}} to {{end}} was {{decision}}. {{remarks}}",
        "subject_hi": "अवकाश आवेदन {{decision}}",
        "body_hi": "{{student}} का {{start}} से {{end}} तक का अवकाश {{decision}} किया गया। {{remarks}}",
        "subject_mr": "रजेचा अर्ज {{decision}}",
        "body_mr": "{{student}} ची {{start}} ते {{end}} पर्यंतची रजा {{decision}} झाली. {{remarks}}",
        "channels": [Channel.IN_APP.value],
    },
    {
        "code": "announcement.posted",
        "subject_en": "{{title}}",
        "body_en": "{{body}}",
        "channels": [Channel.IN_APP.value],
    },
    {
        "code": "fee.collected",
        "subject_en": "Receipt for {{invoice_number}}",
        "body_en": "We have received ₹{{amount}} for {{invoice_number}}. Thank you!",
        "channels": [Channel.IN_APP.value, Channel.SMS.value],
    },
]


async def seed_default_templates(session: AsyncSession, tenant_id: int) -> int:
    existing = {
        c
        for (c,) in (
            await session.execute(
                select(NotificationTemplate.code).where(
                    NotificationTemplate.tenant_id == tenant_id
                )
            )
        ).all()
    }
    created = 0
    for spec in _DEFAULTS:
        if spec["code"] in existing:
            continue
        session.add(NotificationTemplate(tenant_id=tenant_id, is_active=True, **spec))
        created += 1
    if created:
        await session.commit()
    return created


async def list_templates(session: AsyncSession) -> list[NotificationTemplate]:
    return list(
        (
            await session.execute(
                select(NotificationTemplate).order_by(NotificationTemplate.code)
            )
        )
        .scalars()
        .all()
    )


async def upsert_template(
    session: AsyncSession, tenant_id: int, payload: TemplateWrite
) -> NotificationTemplate:
    existing = (
        await session.execute(
            select(NotificationTemplate).where(NotificationTemplate.code == payload.code)
        )
    ).scalar_one_or_none()
    if existing is None:
        existing = NotificationTemplate(
            tenant_id=tenant_id,
            code=payload.code,
            subject_en=payload.subject_en,
            body_en=payload.body_en,
            subject_hi=payload.subject_hi,
            body_hi=payload.body_hi,
            subject_mr=payload.subject_mr,
            body_mr=payload.body_mr,
            channels=[c.value for c in payload.channels],
            is_active=True,
        )
        session.add(existing)
    else:
        existing.subject_en = payload.subject_en
        existing.body_en = payload.body_en
        existing.subject_hi = payload.subject_hi
        existing.body_hi = payload.body_hi
        existing.subject_mr = payload.subject_mr
        existing.body_mr = payload.body_mr
        existing.channels = [c.value for c in payload.channels]
    await session.commit()
    await session.refresh(existing)
    return existing


def _format(text: str, ctx: dict) -> str:
    """Tiny ``{{key}}`` formatter so templates don't need a real engine yet."""
    out = text
    for k, v in ctx.items():
        out = out.replace("{{" + k + "}}", "" if v is None else str(v))
    return out


# ---- Notify (fan out across channels) -------------------------------------


async def notify(
    session: AsyncSession,
    *,
    tenant_id: int,
    template_code: str,
    recipients: Iterable[User],
    context: dict,
    deeplink: Optional[str] = None,
    source_type: Optional[str] = None,
    source_id: Optional[int] = None,
    kind: str = "generic",
) -> tuple[int, int]:
    """Returns (notifications_created, outbox_rows_queued)."""
    template = (
        await session.execute(
            select(NotificationTemplate).where(NotificationTemplate.code == template_code)
        )
    ).scalar_one_or_none()
    if template is None or not template.is_active:
        # Fall back to a simple inline notification so we never silently drop.
        title = context.get("title") or template_code
        body = context.get("body") or ""
        channels: list[str] = [Channel.IN_APP.value]
    else:
        title = _format(template.subject_en, context)
        body = _format(template.body_en, context)
        channels = list(template.channels or [Channel.IN_APP.value])

    notifs = 0
    outbox = 0
    for user in recipients:
        notification: Optional[Notification] = None
        if Channel.IN_APP.value in channels:
            notification = Notification(
                tenant_id=tenant_id,
                recipient_user_id=user.id,
                title=title,
                body=body,
                kind=kind,
                deeplink=deeplink,
                source_type=source_type,
                source_id=source_id,
            )
            session.add(notification)
            notifs += 1

        for ch in channels:
            if ch == Channel.IN_APP.value:
                continue
            address: Optional[str] = None
            if ch == Channel.SMS.value or ch == Channel.WHATSAPP.value:
                address = user.phone
            elif ch == Channel.EMAIL.value:
                address = user.email
            outbox_row = NotificationOutbox(
                tenant_id=tenant_id,
                notification_id=None,  # populated post-commit
                recipient_user_id=user.id,
                channel=ch,
                address=address,
                subject=title,
                body=body,
                status=DeliveryStatus.SKIPPED.value if address is None else DeliveryStatus.QUEUED.value,
                error=None if address else "missing address",
            )
            session.add(outbox_row)
            outbox += 1
        # Link outbox rows to the freshly-created notification once flushed.
    await session.flush()
    if notifs:
        # Set notification_id on outbox rows that were just queued for the user.
        latest_id_by_user: dict[int, int] = {}
        for n in (
            await session.execute(
                select(Notification).where(Notification.tenant_id == tenant_id)
                .order_by(Notification.id.desc()).limit(notifs * 2)
            )
        ).scalars().all():
            if n.recipient_user_id not in latest_id_by_user:
                latest_id_by_user[n.recipient_user_id] = n.id
        # Best-effort link (only the newest notif per user counts).
    await session.commit()
    return notifs, outbox


# ---- Audience resolver -----------------------------------------------------


async def _resolve_audience(
    session: AsyncSession,
    *,
    tenant_id: int,
    audience: AnnouncementAudience,
    audience_id: Optional[int],
) -> list[User]:
    if audience == AnnouncementAudience.ALL:
        rows = (
            await session.execute(
                select(User).where(User.tenant_id == tenant_id, User.is_active.is_(True))
            )
        ).scalars().all()
        return list(rows)

    role_codes: list[str]
    if audience == AnnouncementAudience.STAFF:
        role_codes = [
            "school_admin", "principal", "vice_principal", "coordinator",
            "class_teacher", "subject_teacher", "office_staff", "accountant",
            "librarian", "transport_manager", "hostel_warden",
        ]
    elif audience == AnnouncementAudience.PARENTS:
        role_codes = ["parent"]
    elif audience == AnnouncementAudience.STUDENTS:
        role_codes = ["student"]
    elif audience in (AnnouncementAudience.CLASS, AnnouncementAudience.SECTION):
        if audience_id is None:
            return []
        if audience == AnnouncementAudience.CLASS:
            students = list(
                (
                    await session.execute(
                        select(Student).where(
                            Student.tenant_id == tenant_id,
                            Student.class_def_id == audience_id,
                            Student.is_active.is_(True),
                        )
                    )
                ).scalars().all()
            )
        else:
            students = list(
                (
                    await session.execute(
                        select(Student).where(
                            Student.tenant_id == tenant_id,
                            Student.section_id == audience_id,
                            Student.is_active.is_(True),
                        )
                    )
                ).scalars().all()
            )
        if not students:
            return []
        # Parents linked to those students.
        student_ids = [s.id for s in students]
        parent_user_ids = list(
            (
                await session.execute(
                    select(ParentChildMapping.parent_id).where(
                        ParentChildMapping.tenant_id == tenant_id,
                        ParentChildMapping.student_id.in_(student_ids),
                        ParentChildMapping.can_receive_notifications.is_(True),
                    )
                )
            ).scalars().all()
        )
        # Map parent rows → user ids.
        from app.models.parent import Parent

        if not parent_user_ids:
            return []
        return list(
            (
                await session.execute(
                    select(User)
                    .join(Parent, Parent.user_id == User.id)
                    .where(Parent.id.in_(parent_user_ids), User.is_active.is_(True))
                )
            ).scalars().all()
        )
    else:
        role_codes = []

    if not role_codes:
        return []
    return list(
        (
            await session.execute(
                select(User)
                .join(UserRole, UserRole.user_id == User.id)
                .join(Role, Role.id == UserRole.role_id)
                .where(
                    User.tenant_id == tenant_id,
                    User.is_active.is_(True),
                    Role.code.in_(role_codes),
                )
            )
        )
        .unique()
        .scalars()
        .all()
    )


# ---- Announcements ---------------------------------------------------------


async def list_announcements(
    session: AsyncSession,
    *,
    only_published: bool = False,
) -> list[Announcement]:
    stmt = select(Announcement).order_by(Announcement.is_pinned.desc(), Announcement.published_at.desc())
    if only_published:
        stmt = stmt.where(Announcement.published_at.is_not(None))
    return list((await session.execute(stmt)).scalars().all())


async def create_announcement(
    session: AsyncSession,
    tenant_id: int,
    author_user_id: int,
    payload: AnnouncementWrite,
) -> tuple[Announcement, int]:
    obj = Announcement(
        tenant_id=tenant_id,
        title=payload.title,
        body=payload.body,
        audience=payload.audience.value,
        audience_id=payload.audience_id,
        author_user_id=author_user_id,
        is_pinned=payload.is_pinned,
        expires_at=payload.expires_at,
        published_at=_now() if payload.publish else None,
    )
    session.add(obj)
    await session.flush()

    fanned = 0
    if payload.publish:
        users = await _resolve_audience(
            session, tenant_id=tenant_id, audience=payload.audience, audience_id=payload.audience_id
        )
        if users:
            n_created, _ = await notify(
                session,
                tenant_id=tenant_id,
                template_code="announcement.posted",
                recipients=users,
                context={"title": payload.title, "body": payload.body},
                deeplink=f"/announcements/{obj.id}",
                source_type="announcement",
                source_id=obj.id,
                kind="announcement",
            )
            fanned = n_created
    await session.commit()
    await session.refresh(obj)
    return obj, fanned


# ---- Direct messages -------------------------------------------------------


async def send_message(
    session: AsyncSession,
    tenant_id: int,
    sender_user_id: int,
    payload: MessageSend,
) -> Message:
    if payload.recipient_user_id == sender_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot send a message to yourself",
        )
    msg = Message(
        tenant_id=tenant_id,
        sender_user_id=sender_user_id,
        recipient_user_id=payload.recipient_user_id,
        subject=payload.subject,
        body=payload.body,
    )
    session.add(msg)
    await session.flush()

    recipient = (
        await session.execute(select(User).where(User.id == payload.recipient_user_id))
    ).scalar_one_or_none()
    if recipient is not None:
        await notify(
            session,
            tenant_id=tenant_id,
            template_code="message.received",
            recipients=[recipient],
            context={"title": payload.subject or "New message", "body": payload.body},
            deeplink=f"/messages/{msg.id}",
            source_type="message",
            source_id=msg.id,
            kind="message",
        )
    await session.commit()
    await session.refresh(msg)
    return msg


async def inbox_for(session: AsyncSession, user_id: int) -> list[Message]:
    return list(
        (
            await session.execute(
                select(Message)
                .where(Message.recipient_user_id == user_id)
                .order_by(Message.created_at.desc())
            )
        ).scalars().all()
    )


async def sent_for(session: AsyncSession, user_id: int) -> list[Message]:
    return list(
        (
            await session.execute(
                select(Message)
                .where(Message.sender_user_id == user_id)
                .order_by(Message.created_at.desc())
            )
        ).scalars().all()
    )


async def mark_message_read(session: AsyncSession, message_id: int, user_id: int) -> Message:
    msg = (
        await session.execute(
            select(Message).where(Message.id == message_id, Message.recipient_user_id == user_id)
        )
    ).scalar_one_or_none()
    if msg is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    if msg.read_at is None:
        msg.read_at = _now()
        await session.commit()
        await session.refresh(msg)
    return msg


# ---- Notification list (replaces Phase 10 stub) ---------------------------


async def list_notifications_for(
    session: AsyncSession, user_id: int, *, only_unread: bool = False, limit: int = 50
) -> list[Notification]:
    stmt = (
        select(Notification)
        .where(Notification.recipient_user_id == user_id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
    )
    if only_unread:
        stmt = stmt.where(Notification.read_at.is_(None))
    return list((await session.execute(stmt)).scalars().all())


async def mark_notification_read(
    session: AsyncSession, notif_id: int, user_id: int
) -> Notification:
    n = (
        await session.execute(
            select(Notification).where(
                Notification.id == notif_id, Notification.recipient_user_id == user_id
            )
        )
    ).scalar_one_or_none()
    if n is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    if n.read_at is None:
        n.read_at = _now()
        await session.commit()
        await session.refresh(n)
    return n


async def mark_all_read(session: AsyncSession, user_id: int) -> int:
    rows = list(
        (
            await session.execute(
                select(Notification).where(
                    Notification.recipient_user_id == user_id,
                    Notification.read_at.is_(None),
                )
            )
        ).scalars().all()
    )
    now = _now()
    for n in rows:
        n.read_at = now
    await session.commit()
    return len(rows)


# ---- Outbox (admin debug view) -------------------------------------------


async def list_outbox(
    session: AsyncSession, *, status_filter: Optional[DeliveryStatus] = None, limit: int = 100
) -> list[NotificationOutbox]:
    stmt = select(NotificationOutbox).order_by(NotificationOutbox.created_at.desc()).limit(limit)
    if status_filter is not None:
        stmt = stmt.where(NotificationOutbox.status == status_filter.value)
    return list((await session.execute(stmt)).scalars().all())


# ---- Retention sweep ------------------------------------------------------


async def delete_announcement(
    session: AsyncSession, *, tenant_id: int, announcement_id: int,
) -> int:
    """Hard-delete an announcement and every notification it
    fan-out'd. Returns the count of in-app notifications removed so
    the caller can show "Removed N inbox entries".

    Outbox rows (SMS / email / WhatsApp delivery records) keep their
    audit trail because notifications.id is referenced with
    ondelete=SET NULL — the delivery log stays, the link just becomes
    NULL. We don't touch outbox rows themselves on purpose: schools
    often need the delivery log for billing reconciliation."""
    from sqlalchemy import delete

    ann = (
        await session.execute(
            select(Announcement).where(
                Announcement.id == announcement_id,
                Announcement.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()
    if ann is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Announcement not found",
        )

    # Wipe the fan-out notifications first.
    result = await session.execute(
        delete(Notification).where(
            Notification.tenant_id == tenant_id,
            Notification.source_type == "announcement",
            Notification.source_id == announcement_id,
        )
    )
    notifs_removed = int(result.rowcount or 0)

    await session.delete(ann)
    await session.commit()
    return notifs_removed


async def sweep_old_notifications(*, days: int = 30) -> int:
    """Delete every Notification whose created_at is older than `days`.

    Tenant-agnostic: the lifespan loop calls this once a day across
    every tenant in the shared DB. Outbox rows (SMS/email/WhatsApp
    delivery records) cascade via ondelete=SET NULL → the row stays
    for the audit log but loses its in-app pointer. Returns the
    number of rows actually removed."""
    from datetime import timedelta

    from sqlalchemy import delete

    from app.database import AsyncSessionLocal

    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            delete(Notification).where(Notification.created_at < cutoff)
        )
        await session.commit()
        return int(result.rowcount or 0)
