import 'dart:io' show Platform;

import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';

import '../api/auth_repository.dart';
import 'service_locator.dart';

/// Thin wrapper around firebase_messaging that:
///  - requests notification permission once,
///  - fetches the device's FCM token + posts it to the backend so the
///    push worker can target this device,
///  - listens for foreground messages and re-registers the token when
///    FCM rotates it.
///
/// Intentionally side-effect-light so it can be called from main(): we
/// swallow every failure and log to console. The notification_outbox is
/// the source of truth for whether a message was delivered.
class PushService {
  PushService._();
  static final PushService instance = PushService._();

  bool _started = false;
  String? _lastRegisteredToken;

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
        await _registerWithBackend(token);
      }

      // Re-register when FCM rotates the token.
      messaging.onTokenRefresh.listen((newToken) {
        debugPrint('FCM token refreshed: $newToken');
        _registerWithBackend(newToken);
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

  /// Tells the API server about the FCM token so the push worker can
  /// target this device. No-ops if the user isn't logged in (the
  /// register endpoint requires auth) — the next cold-start after
  /// login will re-register.
  ///
  /// [force] bypasses the "already registered this token" short-circuit.
  /// Use it on a fresh login: even if FCM hands back the same token
  /// string, the *session* is new and the backend needs to (re)upsert
  /// the row against the new user_id.
  Future<void> _registerWithBackend(String token, {bool force = false}) async {
    if (token.isEmpty) return;
    if (!force && token == _lastRegisteredToken) return;
    try {
      await locator<AuthRepository>().registerDevice(
        fcmToken: token,
        platform: _platformLabel(),
      );
      _lastRegisteredToken = token;
      debugPrint('FCM token registered with backend.');
    } catch (e) {
      debugPrint('FCM token register failed (will retry on next start): $e');
    }
  }

  /// Public hook for AuthCubit: called after a successful login (or
  /// session restore) so the backend always sees an up-to-date
  /// (user_id, fcm_token) row for this device.
  ///
  /// Distinct from [start] — that's an idempotent boot hook that
  /// guards with [_started]; this one ignores the guard and forces a
  /// re-register against the freshly-authenticated session. Initialises
  /// the FCM listeners on the first call so a clean "logged out at
  /// app boot → log in" path still works.
  Future<void> registerForCurrentSession() async {
    try {
      // Make sure start() has run so onTokenRefresh / onMessage are
      // hooked up; start()'s own _started guard prevents double-listen.
      await start();
      final token = await FirebaseMessaging.instance.getToken();
      if (token == null) {
        debugPrint('registerForCurrentSession: getToken() returned null');
        return;
      }
      await _registerWithBackend(token, force: true);
    } catch (e, st) {
      debugPrint('registerForCurrentSession failed: $e\n$st');
    }
  }

  String _platformLabel() {
    if (kIsWeb) return 'web';
    try {
      if (Platform.isIOS) return 'ios';
      if (Platform.isAndroid) return 'android';
    } catch (_) {}
    return 'android';
  }

  /// Called by AuthCubit on logout so the server stops pushing to a
  /// device the user has signed out of.
  Future<void> unregisterCurrentDevice() async {
    final token = _lastRegisteredToken;
    if (token == null) return;
    try {
      await locator<AuthRepository>().unregisterDevice(fcmToken: token);
      _lastRegisteredToken = null;
    } catch (_) {
      // Best-effort; swallow.
    }
  }
}
