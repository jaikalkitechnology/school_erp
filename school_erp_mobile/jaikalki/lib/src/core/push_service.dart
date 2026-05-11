import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';

/// Thin wrapper around firebase_messaging that:
///  - requests notification permission once,
///  - fetches the device's FCM token + posts it to the backend so server-side
///    Phase 12 push delivery can target it,
///  - listens for foreground messages and re-registers the token when FCM
///    rotates it.
///
/// Intentionally side-effect-light so it can be called from main(): swallow
/// every failure and log to console. The Phase 12 NotificationOutbox is the
/// source of truth for whether a message was delivered.
class PushService {
  PushService._();
  static final PushService instance = PushService._();

  bool _started = false;

  Future<void> start() async {
    if (_started) return;
    _started = true;
    try {
      final messaging = FirebaseMessaging.instance;

      final settings = await messaging.requestPermission(
        alert: true, badge: true, sound: true, provisional: false,
      );
      debugPrint('FCM permission status: ${settings.authorizationStatus}');

      // First-time token; may be null on iOS until APNs is wired.
      final token = await messaging.getToken();
      if (token != null) {
        debugPrint('FCM token: $token');
        // TODO(phase-12-consumer): POST to /v1/notifications/devices once that
        // endpoint lands. For now we just print it.
      }

      // Re-register when FCM rotates the token.
      messaging.onTokenRefresh.listen((newToken) {
        debugPrint('FCM token refreshed: $newToken');
        // TODO(phase-12-consumer): re-POST to /v1/notifications/devices.
      });

      // Foreground messages: log + (later) surface a local notification.
      FirebaseMessaging.onMessage.listen((message) {
        debugPrint(
          'FCM foreground message: title=${message.notification?.title} '
          'body=${message.notification?.body} data=${message.data}',
        );
      });
    } catch (e, st) {
      debugPrint('PushService.start failed: $e\n$st');
    }
  }
}
