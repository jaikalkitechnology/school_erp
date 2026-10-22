"""Firebase Cloud Messaging adapter.

Lazy-loads the Firebase Admin SDK on first use so the app keeps booting
when ``FIREBASE_CREDENTIALS_PATH`` points at a missing file (dev /
unit-test environments). The Phase 12 ``notification_outbox`` is the
queue; a future worker can call ``send_push`` per row.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Optional

from app.config import settings

_log = logging.getLogger(__name__)
_init_lock = threading.Lock()
_app = None
_messaging = None
_unavailable_reason: Optional[str] = None


def _initialise() -> None:
    """Idempotent Firebase Admin SDK init. Records the failure reason on
    the module instead of raising so callers can decide whether to skip
    the delivery silently or surface an error."""

    global _app, _messaging, _unavailable_reason

    if _app is not None or _unavailable_reason is not None:
        return

    with _init_lock:
        if _app is not None or _unavailable_reason is not None:
            return

        try:
            import firebase_admin
            from firebase_admin import credentials, messaging
        except ImportError as exc:
            _unavailable_reason = f"firebase_admin not installed: {exc}"
            _log.warning("FCM disabled: %s", _unavailable_reason)
            return

        path = Path(settings.FIREBASE_CREDENTIALS_PATH)
        if not path.is_file():
            _unavailable_reason = f"service-account JSON not found at {path}"
            _log.warning("FCM disabled: %s", _unavailable_reason)
            return

        try:
            # firebase_admin.initialize_app is a singleton per process; re-init
            # raises ValueError. Reuse the default app if it exists.
            try:
                _app = firebase_admin.get_app()
            except ValueError:
                cred = credentials.Certificate(str(path))
                _app = firebase_admin.initialize_app(cred)
            _messaging = messaging
            _log.info("FCM initialised from %s", path)
        except Exception as exc:  # noqa: BLE001 - guard the boot
            _unavailable_reason = f"firebase_admin init failed: {exc!r}"
            _log.exception("FCM init failed")
            _app = None
            _messaging = None


def is_available() -> bool:
    _initialise()
    return _messaging is not None


def unavailable_reason() -> Optional[str]:
    _initialise()
    return _unavailable_reason


# Must match the channel the app creates (PushService._channelId) and the
# default in AndroidManifest.xml. High priority + this high-importance
# channel is what makes Android show a heads-up banner when the app is in
# the background or closed.
ANDROID_CHANNEL_ID = "jaikalki_default"


def _android_config():
    return _messaging.AndroidConfig(
        priority="high",
        notification=_messaging.AndroidNotification(
            channel_id=ANDROID_CHANNEL_ID,
            sound="default",
            icon="ic_notification",
            color="#E85D2E",
        ),
    )


def send_push(
    *,
    token: str,
    title: str,
    body: str,
    data: Optional[dict[str, str]] = None,
) -> str:
    """Send a push message to a single FCM device token.

    Returns the FCM message id on success. Raises ``RuntimeError`` if
    Firebase isn't configured, ``firebase_admin.exceptions.FirebaseError``
    on delivery failure. Caller is responsible for catching and writing
    the outcome to ``notification_outbox.status``.
    """

    _initialise()
    if _messaging is None:
        raise RuntimeError(unavailable_reason() or "FCM not available")

    message = _messaging.Message(
        token=token,
        notification=_messaging.Notification(title=title, body=body),
        data={k: str(v) for k, v in (data or {}).items()},
        android=_android_config(),
        apns=_messaging.APNSConfig(
            headers={"apns-priority": "10"},
            payload=_messaging.APNSPayload(
                aps=_messaging.Aps(sound="default", content_available=True),
            ),
        ),
    )
    return _messaging.send(message)


def send_multicast(
    *,
    tokens: list[str],
    title: str,
    body: str,
    data: Optional[dict[str, str]] = None,
) -> dict:
    """Send the same payload to up to 500 device tokens in one call.

    Returns ``{"success_count": int, "failure_count": int,
    "invalid_tokens": [...]}`` — invalid_tokens are the ones FCM said are
    unregistered/expired and should be deleted from your device_tokens
    table.
    """

    _initialise()
    if _messaging is None:
        raise RuntimeError(unavailable_reason() or "FCM not available")
    if not tokens:
        return {"success_count": 0, "failure_count": 0, "invalid_tokens": []}

    msg = _messaging.MulticastMessage(
        tokens=tokens,
        notification=_messaging.Notification(title=title, body=body),
        data={k: str(v) for k, v in (data or {}).items()},
        android=_android_config(),
    )
    resp = _messaging.send_each_for_multicast(msg)

    invalid: list[str] = []
    for token, r in zip(tokens, resp.responses):
        if not r.success and r.exception is not None:
            code = getattr(r.exception, "code", "")
            if code in {"registration-token-not-registered", "invalid-argument"}:
                invalid.append(token)
    return {
        "success_count": resp.success_count,
        "failure_count": resp.failure_count,
        "invalid_tokens": invalid,
    }
