"""Synchronous push-dispatch helpers.

Wraps ``app.services.fcm.send_push`` so the caller can fire pushes
immediately — without depending on the async ``push_worker`` daemon
draining ``notification_outbox`` later. Used by:

  * ``POST /v1/auth/send-notification`` — one-off admin push.
  * ``create_announcement`` — fans the new notice out to every
    recipient's phone the moment the admin hits Publish, regardless
    of whether the worker is running.

Both paths share the same per-device loop:

  1. Look up active ``user_devices`` rows for the user.
  2. Call ``fcm.send_push`` for each token, collect outcome.
  3. Deactivate tokens FCM marked as dead
     (``registration-token-not-registered`` /  ``invalid-argument``)
     so the next call doesn't keep retrying them.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth_extras import UserDevice
from app.models.comms import Channel, DeliveryStatus, Notification, NotificationOutbox
from app.services import fcm

_log = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class PushResult:
    """Per-call outcome — easier to thread back to the API response
    than juggling a 4-tuple."""

    __slots__ = ("sent", "failed", "skipped", "deactivated", "errors")

    def __init__(self) -> None:
        self.sent: int = 0
        self.failed: int = 0
        self.skipped: int = 0
        self.deactivated: int = 0
        self.errors: list[dict] = []

    def merge(self, other: "PushResult") -> None:
        self.sent += other.sent
        self.failed += other.failed
        self.skipped += other.skipped
        self.deactivated += other.deactivated
        self.errors.extend(other.errors)


async def _send_to_user_devices(
    session: AsyncSession,
    *,
    user_id: int,
    title: str,
    body: str,
    data: Optional[dict[str, Any]] = None,
) -> PushResult:
    """Send the same payload to every active device on the user. Caller
    should already have called ``fcm.is_available()`` — we don't 503
    here because some callers want to fall through silently."""
    result = PushResult()

    devices = list(
        (
            await session.execute(
                select(UserDevice).where(
                    UserDevice.user_id == user_id,
                    UserDevice.is_active.is_(True),
                )
            )
        ).scalars().all()
    )
    if not devices:
        result.skipped += 1
        return result
    if not fcm.is_available():
        result.skipped += len(devices)
        result.errors.append({"user_id": user_id, "error": fcm.unavailable_reason()})
        return result

    invalid_tokens: list[str] = []
    payload_data = {k: str(v) for k, v in (data or {}).items()}

    for device in devices:
        try:
            fcm.send_push(
                token=device.fcm_token,
                title=title or "",
                body=body or "",
                data=payload_data,
            )
            result.sent += 1
        except Exception as exc:  # noqa: BLE001 - FCM raises many types
            result.failed += 1
            err_code = getattr(exc, "code", "") or ""
            _log.warning(
                "FCM send failed user_id=%s device_id=%s code=%s err=%s",
                user_id, device.id, err_code, exc,
            )
            result.errors.append({
                "user_id": user_id,
                "device_id": device.id,
                "code": err_code,
                "error": str(exc),
            })
            if err_code in {
                "registration-token-not-registered",
                "invalid-argument",
            }:
                invalid_tokens.append(device.fcm_token)

    if invalid_tokens:
        await session.execute(
            update(UserDevice)
            .where(UserDevice.fcm_token.in_(invalid_tokens))
            .values(is_active=False)
        )
        await session.commit()
        result.deactivated += len(invalid_tokens)
    return result


async def send_push_to_user(
    session: AsyncSession,
    *,
    user_id: int,
    title: str,
    body: str,
    data: Optional[dict[str, Any]] = None,
) -> PushResult:
    """Public wrapper for the one-off /send-notification route."""
    return await _send_to_user_devices(
        session, user_id=user_id, title=title, body=body, data=data,
    )


async def drain_pending_push_outbox_ids(
    session: AsyncSession,
    ids: list[int],
) -> PushResult:
    """Drain a specific list of ``notification_outbox.id`` rows.

    Used by ``create_announcement`` after ``notify()`` returns the
    list of push-row ids it just queued. Sends each row's payload via
    FCM right now and updates the row's status — so the admin gets a
    real "pushed to N phones" count in the Publish response even if
    the background ``push_worker`` daemon isn't running.

    Rows that aren't ``channel='push' status='queued'`` are silently
    skipped — a re-run on the same id list is a no-op.
    """
    overall = PushResult()
    if not ids:
        return overall

    rows = list(
        (
            await session.execute(
                select(NotificationOutbox)
                .where(
                    NotificationOutbox.id.in_(ids),
                    NotificationOutbox.channel == Channel.PUSH.value,
                    NotificationOutbox.status == DeliveryStatus.QUEUED.value,
                )
            )
        ).scalars().all()
    )
    if not rows:
        return overall

    if not fcm.is_available():
        # Don't keep failing forever — mark them skipped so the worker
        # (if any) doesn't re-attempt every poll.
        reason = fcm.unavailable_reason() or "FCM not configured"
        for r in rows:
            r.status = DeliveryStatus.SKIPPED.value
            r.error = reason
            r.updated_at = _now()
            overall.skipped += 1
        await session.commit()
        return overall

    # What the app needs to open the right place when the push is tapped.
    notif_ids = [r.notification_id for r in rows if r.notification_id]
    notifs: dict[int, Notification] = {}
    if notif_ids:
        notifs = {
            n.id: n
            for n in (
                await session.execute(select(Notification).where(Notification.id.in_(notif_ids)))
            ).scalars().all()
        }

    for row in rows:
        n = notifs.get(row.notification_id) if row.notification_id else None
        data: dict[str, Any] = {"outbox_id": row.id}
        if n is not None:
            data.update(notification_id=n.id, kind=n.kind or "", deeplink=n.deeplink or "")
        per_row = await _send_to_user_devices(
            session,
            user_id=row.recipient_user_id,
            title=row.subject or "",
            body=row.body or "",
            data=data,
        )
        overall.merge(per_row)
        if per_row.sent > 0:
            row.status = DeliveryStatus.SENT.value
            row.error = None
        elif per_row.failed > 0:
            row.status = DeliveryStatus.FAILED.value
            row.error = (
                per_row.errors[-1].get("error") if per_row.errors else "unknown"
            )
        else:
            row.status = DeliveryStatus.SKIPPED.value
            row.error = "no active devices"
        row.updated_at = _now()
    await session.commit()
    return overall


