import 'dart:io' show Platform;
import 'dart:ui' show Color;

import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';

import '../api/auth_repository.dart';
import 'service_locator.dart';

/// Top-level so FCM can invoke it from a background isolate when the
/// app is killed. Must be a top-level / static function — not a method
/// — or FCM's plugin host can't find the entry point.
///
/// We intentionally don't do anything heavy here: FCM already shows
/// the system tray notification using the `notification` block in the
/// payload. The handler exists so the plugin's "did you register a
/// background handler?" check passes and `data`-only messages still
/// reach us (useful when we add deep-link routing later).
@pragma('vm:entry-point')
Future<void> firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  debugPrint(
    'FCM background message: title=${message.notification?.title} '
    'body=${message.notification?.body} data=${message.data}',
  );
}

/// Thin wrapper around firebase_messaging + flutter_local_notifications:
///
///  * Requests notification permission (Android 13+, iOS).
///  * Fetches the FCM token and posts it to the backend.
///  * Listens for foreground messages and shows them in the system tray
///    via flutter_local_notifications — FCM does NOT auto-display
///    notifications while the app is foregrounded, so without this the
///    user only sees nothing when the app is open.
///  * Background/killed delivery is handled by Play Services using
///    the `notification` block in the FCM payload (the AndroidManifest
///    declares the default channel id ``jaikalki_default`` so the
///    system tray banner uses our channel).
class PushService {
  PushService._();
  static final PushService instance = PushService._();

  bool _started = false;
  String? _lastRegisteredToken;

  /// Default Android channel id. Must match the value in
  /// AndroidManifest.xml under
  /// ``com.google.firebase.messaging.default_notification_channel_id``.
  static const String _channelId = 'jaikalki_default';
  static const String _channelName = 'General';
  static const String _channelDescription =
      'School updates, announcements, homework, fees, and chat.';

  final FlutterLocalNotificationsPlugin _local =
      FlutterLocalNotificationsPlugin();

  /// Bumped every time a push arrives while the app is open, so an open
  /// Notifications page can reload.
  final ValueNotifier<int> received = ValueNotifier<int>(0);

  /// Bumped when the user taps a notification (foreground banner, tray
  /// notification while backgrounded, or the one that launched the app).
  /// The logged-in home screen listens and opens the Notifications page.
  final ValueNotifier<int> openRequests = ValueNotifier<int>(0);

  /// Small status-bar icon: white silhouette in res/drawable-*dpi.
  static const String _smallIcon = '@drawable/ic_notification';

  Future<void> start() async {
    if (_started) return;
    _started = true;
    try {
      // 1) Local-notifications plugin: needed for foreground banners.
      await _initLocalNotifications();

      // 2) FCM permission + listeners.
      final messaging = FirebaseMessaging.instance;

      final settings = await messaging.requestPermission(
        alert: true, badge: true, sound: true, provisional: false,
      );
      debugPrint('FCM permission status: ${settings.authorizationStatus}');

      // iOS only: allow the OS to show the system banner while we're in
      // the foreground too, in addition to our own local notification.
      // On Android the OS suppresses tray banners for foreground apps no
      // matter what, so the local notification is the only path.
      await messaging.setForegroundNotificationPresentationOptions(
        alert: true, badge: true, sound: true,
      );

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

      // 3) Foreground messages → render a local notification so the
      //    user actually sees the banner instead of nothing.
      FirebaseMessaging.onMessage.listen((message) async {
        debugPrint(
          'FCM foreground message: title=${message.notification?.title} '
          'body=${message.notification?.body} data=${message.data}',
        );
        received.value++;
        // iOS already shows the banner itself (see
        // setForegroundNotificationPresentationOptions above); drawing
        // our own too would show it twice.
        if (defaultTargetPlatform == TargetPlatform.android) {
          await _showLocalNotificationFrom(message);
        }
      });

      // 4) Background / killed: register the top-level handler so the
      //    plugin keeps delivering messages to us even when the isolate
      //    is asleep. The system tray banner is shown by Play Services
      //    from the `notification` payload — not from this handler.
      FirebaseMessaging.onBackgroundMessage(firebaseMessagingBackgroundHandler);

      // 5) Optional: log taps on a tray notification while the app was
      //    in the background. Useful later for deep-link routing.
      FirebaseMessaging.onMessageOpenedApp.listen((message) {
        debugPrint('FCM notification tapped: data=${message.data}');
        openRequests.value++;
      });

      // 6) The app was fully closed and the user launched it by tapping
      //    a notification.
      final initial = await messaging.getInitialMessage();
      if (initial != null) {
        debugPrint('App opened from notification: data=${initial.data}');
        openRequests.value++;
      }
    } catch (e, st) {
      debugPrint('PushService.start failed: $e\n$st');
    }
  }

  Future<void> _initLocalNotifications() async {
    const androidInit = AndroidInitializationSettings(_smallIcon);
    const iosInit = DarwinInitializationSettings(
      requestAlertPermission: false,
      requestBadgePermission: false,
      requestSoundPermission: false,
    );
    const init = InitializationSettings(android: androidInit, iOS: iosInit);

    await _local.initialize(
      init,
      onDidReceiveNotificationResponse: (resp) {
        debugPrint('Local notification tapped: payload=${resp.payload}');
        openRequests.value++;
      },
    );

    // Android needs the channel to exist before we post to it. Idempotent.
    final android =
        _local.resolvePlatformSpecificImplementation<
            AndroidFlutterLocalNotificationsPlugin>();
    await android?.createNotificationChannel(
      const AndroidNotificationChannel(
        _channelId,
        _channelName,
        description: _channelDescription,
        importance: Importance.high,
      ),
    );
    // Android 13+: explicit POST_NOTIFICATIONS permission.
    await android?.requestNotificationsPermission();
  }

  Future<void> _showLocalNotificationFrom(RemoteMessage message) async {
    final notification = message.notification;
    final title = notification?.title ?? message.data['title'] as String?;
    final body = notification?.body ?? message.data['body'] as String?;
    if ((title == null || title.isEmpty) && (body == null || body.isEmpty)) {
      // Data-only push with no human-readable payload — skip.
      return;
    }
    // Not const: the expanded (BigText) view needs this message's body.
    final androidDetails = AndroidNotificationDetails(
      _channelId,
      _channelName,
      channelDescription: _channelDescription,
      importance: Importance.high,
      priority: Priority.high,
      icon: _smallIcon,
      color: const Color(0xFFE85D2E),
      styleInformation: BigTextStyleInformation(body ?? ''),
    );
    const iosDetails = DarwinNotificationDetails(
      presentAlert: true, presentBadge: true, presentSound: true,
    );
    final details = NotificationDetails(android: androidDetails, iOS: iosDetails);

    final id = (message.messageId?.hashCode ?? DateTime.now().millisecondsSinceEpoch)
        .abs()
        .toInt() & 0x7fffffff;

    await _local.show(
      id,
      title ?? '',
      body ?? '',
      details,
      payload: message.data['deeplink'] as String? ?? message.data['screen'] as String?,
    );
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
