import 'dart:async';
import 'dart:convert';

import 'package:dio/dio.dart';

import 'api_client.dart';

/// Single GPS frame from the SSE stream.
class TripPositionFrame {
  const TripPositionFrame({
    required this.tripId,
    required this.phase,
    required this.lat,
    required this.lng,
    required this.speedKph,
    required this.lastPingAt,
  });

  final int tripId;
  /// scheduled / in_progress / completed / cancelled
  final String phase;
  final double? lat;
  final double? lng;
  final double? speedKph;
  final String? lastPingAt;

  bool get isLive => phase == 'in_progress';

  factory TripPositionFrame.fromJson(Map<String, dynamic> j) =>
      TripPositionFrame(
        tripId: (j['trip_id'] as num?)?.toInt() ?? 0,
        phase: (j['phase'] as String?) ?? 'scheduled',
        lat: _toD(j['last_lat']),
        lng: _toD(j['last_lng']),
        speedKph: _toD(j['last_speed_kph']),
        lastPingAt: j['last_ping_at'] as String?,
      );

  static double? _toD(dynamic v) {
    if (v == null) return null;
    if (v is num) return v.toDouble();
    if (v is String) return double.tryParse(v);
    return null;
  }
}

/// Subscribes to the trip SSE stream (`GET /transport/trips/{id}/stream`).
/// Emits a [TripPositionFrame] every time the backend pushes one;
/// closes the stream when the backend emits the `event: end` signal or
/// the connection dies. Caller is responsible for cancelling the
/// subscription when the page is disposed.
class TripStream {
  TripStream(this._api);
  final ApiClient _api;

  Stream<TripPositionFrame> subscribe(int tripId) async* {
    final response = await _api.dio.get<ResponseBody>(
      '/v1/school-admin/transport/trips/$tripId/stream',
      options: Options(
        responseType: ResponseType.stream,
        headers: {'Accept': 'text/event-stream'},
      ),
    );
    final body = response.data;
    if (body == null) return;

    final buffer = StringBuffer();
    await for (final chunk in body.stream) {
      buffer.write(utf8.decode(chunk, allowMalformed: true));
      // SSE frames are separated by a blank line. Process every
      // complete frame currently in the buffer.
      while (true) {
        final s = buffer.toString();
        final boundary = s.indexOf('\n\n');
        if (boundary < 0) break;
        final frame = s.substring(0, boundary);
        buffer.clear();
        buffer.write(s.substring(boundary + 2));

        String? data;
        String? event;
        for (final line in frame.split('\n')) {
          if (line.startsWith('data:')) {
            data = line.substring(5).trim();
          } else if (line.startsWith('event:')) {
            event = line.substring(6).trim();
          }
        }
        if (event == 'end') return;
        if (data == null || data.isEmpty) continue;
        try {
          final json = jsonDecode(data) as Map<String, dynamic>;
          yield TripPositionFrame.fromJson(json);
        } catch (_) {
          // Skip malformed frames.
        }
      }
    }
  }
}
