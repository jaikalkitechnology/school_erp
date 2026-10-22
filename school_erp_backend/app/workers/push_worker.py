"""FCM push delivery worker.

Drains ``notification_outbox`` rows where ``channel='push'`` and
``status='queued'``, looks up every active ``user_devices`` row for the
recipient, calls ``fcm.send_push`` per token, and writes back the
outcome.

Run as a long-lived process::

    python -m app.workers.push_worker

or as a one-shot pass for testing::

    python -m app.workers.push_worker --once

The loop is deliberately simple — pull a batch, send sequentially,
sleep. We can move to async fan-out / a real queue once the volume
demands it. For now the bottleneck is the FCM HTTP round-trip, and a
single MySQL row lock is more than enough at school-sized fan-out
(tens of thousands of pushes per day at most).
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import signal
import sys
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.auth_extras import UserDevice
from app.models.comms import Channel, DeliveryStatus, Notification, NotificationOutbox
from app.services import fcm

_log = logging.getLogger("push_worker")
_BATCH_SIZE = int(os.getenv("PUSH_WORKER_BATCH", "100"))
_POLL_SECONDS = float(os.getenv("PUSH_WORKER_POLL_SECONDS", "5"))
_shutdown = asyncio.Event()


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def _claim_batch(session: AsyncSession, limit: int) -> list[NotificationOutbox]:
    """Pick up to ``limit`` queued push rows and flip them to
    ``status='sent'`` provisionally so a second worker can't grab the
    same rows. We rewrite to ``failed`` per-row if the actual delivery
    blows up, and back to ``sent`` (no-op) on success.

    This is a simple lease-by-status pattern; if a worker crashes
    mid-delivery the row sticks at ``sent`` with no provider_ref. That's
    a known trade-off — better than double-delivery.
    """
    rows = list(
        (
            await session.execute(
                select(NotificationOutbox)
                .where(
                    NotificationOutbox.channel == Channel.PUSH.value,
                    NotificationOutbox.status == DeliveryStatus.QUEUED.value,
                )
                .order_by(NotificationOutbox.created_at.asc())
                .limit(limit)
                .with_for_update(skip_locked=True)
            )
        ).scalars().all()
    )
    if not rows:
        return []
    ids = [r.id for r in rows]
    await session.execute(
        update(NotificationOutbox)
        .where(NotificationOutbox.id.in_(ids))
        .values(status="processing")
    )
    await session.commit()
    return rows


async def _tokens_for(session: AsyncSession, user_id: int) -> list[str]:
    rows = (
        await session.execute(
            select(UserDevice.fcm_token).where(
                UserDevice.user_id == user_id,
                UserDevice.is_active.is_(True),
            )
        )
    ).all()
    return [t for (t,) in rows if t]


async def _send_one(
    session: AsyncSession, row: NotificationOutbox,
) -> tuple[str, Optional[str], Optional[str]]:
    """Deliver one outbox row to every active device for the user.

    Returns ``(status, provider_ref, error)`` — provider_ref is a CSV
    of FCM message ids on success (or ``""`` if multi-token delivery
    is mixed)."""
    tokens = await _tokens_for(session, row.recipient_user_id)
    if not tokens:
        return (DeliveryStatus.SKIPPED.value, None, "no active devices")

    title = (row.subject or "Notification")[:120]
    body = (row.body or "")[:500]
    data = {"outbox_id": str(row.id)}
    # What the app needs to open the right place when the push is tapped.
    if row.notification_id:
        n = await session.get(Notification, row.notification_id)
        if n is not None:
            data.update(notification_id=str(n.id), kind=n.kind or "", deeplink=n.deeplink or "")

    successes: list[str] = []
    invalid_tokens: list[str] = []
    last_error: Optional[str] = None

    for token in tokens:
        try:
            msg_id = fcm.send_push(token=token, title=title, body=body, data=data)
            successes.append(msg_id)
        except Exception as exc:  # noqa: BLE001 - FCM SDK raises many types
            err_code = getattr(exc, "code", "") or ""
            last_error = f"{type(exc).__name__}: {exc}"
            _log.warning("FCM send failed for token=%s...: %s", token[:10], exc)
            if err_code in {"registration-token-not-registered", "invalid-argument"}:
                invalid_tokens.append(token)

    if invalid_tokens:
        await session.execute(
            update(UserDevice)
            .where(UserDevice.fcm_token.in_(invalid_tokens))
            .values(is_active=False)
        )
        await session.commit()

    if successes:
        return (
            DeliveryStatus.SENT.value,
            ",".join(successes)[:120],
            last_error,
        )
    return (DeliveryStatus.FAILED.value, None, last_error or "delivery failed")


async def _drain_once() -> int:
    """Pull a batch, send, write status. Returns how many rows were
    handled so the caller knows whether to sleep or loop immediately."""
    if not fcm.is_available():
        _log.warning(
            "FCM not configured (%s) — skipping batch", fcm.unavailable_reason(),
        )
        return 0

    async with AsyncSessionLocal() as session:
        rows = await _claim_batch(session, _BATCH_SIZE)
        if not rows:
            return 0
        for row in rows:
            try:
                status, provider_ref, err = await _send_one(session, row)
            except Exception as exc:  # noqa: BLE001
                status, provider_ref, err = (
                    DeliveryStatus.FAILED.value,
                    None,
                    f"{type(exc).__name__}: {exc}",
                )
            row.status = status
            row.provider_ref = provider_ref
            row.error = err
            row.updated_at = _now()
        await session.commit()
        return len(rows)


def _install_signal_handlers(loop: asyncio.AbstractEventLoop) -> None:
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _shutdown.set)
        except NotImplementedError:
            # Windows / non-mainline event loops — fall back to default.
            signal.signal(sig, lambda *_: _shutdown.set())


async def _run_forever() -> None:
    _log.info(
        "push_worker started (batch=%d poll=%.1fs)", _BATCH_SIZE, _POLL_SECONDS,
    )
    while not _shutdown.is_set():
        try:
            handled = await _drain_once()
        except Exception:  # noqa: BLE001
            _log.exception("push_worker drain failed")
            handled = 0
        if handled == 0:
            try:
                await asyncio.wait_for(_shutdown.wait(), timeout=_POLL_SECONDS)
            except asyncio.TimeoutError:
                pass


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Drains notification_outbox push rows via FCM.",
    )
    parser.add_argument(
        "--once", action="store_true",
        help="Drain a single batch and exit (useful for cron / testing).",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="DEBUG logging.",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    _install_signal_handlers(loop)

    try:
        if args.once:
            handled = loop.run_until_complete(_drain_once())
            _log.info("push_worker --once handled=%d", handled)
        else:
            loop.run_until_complete(_run_forever())
    finally:
        loop.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
