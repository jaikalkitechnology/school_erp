import 'dart:async';
import 'dart:convert';
import 'dart:io' show HttpClient;
import 'dart:ui';

import 'package:flutter/foundation.dart';
import 'package:flutter_background_service/flutter_background_service.dart';
import 'package:geolocator/geolocator.dart';

/// Driver-side foreground service. Once a trip is started, the
/// flutter_background_service plugin spawns a separate isolate that
/// keeps running after the app is backgrounded / the phone is locked,
/// and POSTs GPS pings to the backend every 15 s while the trip is
/// live.
///
/// The service shows a persistent foreground notification ("Bus
/// tracking active") which Android requires for any location-type
/// foreground service on API 34+.
///
/// API used by the DriverPage:
///   * await BusTrackingService.init() — registers the background
///     isolate handler. Call once at app boot.
///   * await BusTrackingService.startForTrip(tripId, accessToken,
///       baseUrl, subdomain) — starts the service and tells it which
///       trip + API to ping.
///   * await BusTrackingService.stop() — stops pinging and dismisses
///     the foreground notification.
///
/// We deliberately use bare ``HttpClient`` here instead of Dio: the
/// background isolate doesn't have access to our service_locator's
/// Dio instance + interceptors, and a tiny POST every 15 s doesn't
/// need any of that machinery.
class BusTrackingService {
  static const String _serviceNotifId = 'jaikalki_bus_tracking';
  static const String _serviceNotifTitle = 'Bus tracking active';
  static const String _serviceNotifBody =
      'Posting your location to the school every 15 s.';

  static Future<void> init() async {
    final svc = FlutterBackgroundService();
    await svc.configure(
      androidConfiguration: AndroidConfiguration(
        onStart: _onServiceStart,
        autoStart: false,
        isForegroundMode: true,
        notificationChannelId: _serviceNotifId,
        initialNotificationTitle: _serviceNotifTitle,
        initialNotificationContent: _serviceNotifBody,
        foregroundServiceNotificationId: 9911,
        foregroundServiceTypes: const [
          AndroidForegroundType.location,
        ],
      ),
      iosConfiguration: IosConfiguration(
        autoStart: false,
        onForeground: _onServiceStart,
      ),
    );
  }

  static Future<void> startForTrip({
    required int tripId,
    required String accessToken,
    required String baseUrl,
    String? subdomain,
  }) async {
    final svc = FlutterBackgroundService();
    final isRunning = await svc.isRunning();
    if (!isRunning) {
      await svc.startService();
    }
    svc.invoke('config', {
      'trip_id': tripId,
      'access_token': accessToken,
      'base_url': baseUrl,
      if (subdomain != null) 'subdomain': subdomain,
    });
  }

  static Future<void> stop() async {
    FlutterBackgroundService().invoke('stop');
  }
}

/// Background-isolate entry point. Runs in a separate isolate, so
/// service_locator / Dio / state cubits are NOT available here.
@pragma('vm:entry-point')
void _onServiceStart(ServiceInstance service) async {
  DartPluginRegistrant.ensureInitialized();

  int? tripId;
  String? accessToken;
  String? baseUrl;
  String? subdomain;
  Timer? loop;

  service.on('config').listen((event) {
    tripId = (event?['trip_id'] as num?)?.toInt();
    accessToken = event?['access_token'] as String?;
    baseUrl = event?['base_url'] as String?;
    subdomain = event?['subdomain'] as String?;
  });

  service.on('stop').listen((_) async {
    loop?.cancel();
    await service.stopSelf();
  });

  // Tick every 15 s. Each tick takes the freshest GPS reading and
  // posts it to /trips/{id}/ping.
  loop = Timer.periodic(const Duration(seconds: 15), (_) async {
    final id = tripId;
    final token = accessToken;
    final url = baseUrl;
    if (id == null || token == null || url == null) return;
    try {
      final pos = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.high,
          timeLimit: Duration(seconds: 8),
        ),
      );
      final client = HttpClient()
        ..connectionTimeout = const Duration(seconds: 10);
      final req = await client.postUrl(
        Uri.parse('$url/v1/school-admin/transport/trips/$id/ping'),
      );
      req.headers
        ..add('Authorization', 'Bearer $token')
        ..add('Content-Type', 'application/json');
      if (subdomain != null) req.headers.add('X-Tenant-Subdomain', subdomain!);
      req.write(jsonEncode({
        'lat': pos.latitude,
        'lng': pos.longitude,
        'speed_kph': pos.speed * 3.6,
      }));
      final resp = await req.close();
      await resp.drain();
      client.close();
    } catch (e) {
      // Service stays alive. We just miss this tick.
      debugPrint('bus_tracking ping failed: $e');
    }
  });
}
