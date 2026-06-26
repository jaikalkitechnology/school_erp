import 'package:dio/dio.dart';

import 'api_client.dart';

/// Driver-app wrapper around the existing /v1/school-admin/transport
/// router. Same backend endpoints, scoped to a `transport_manager` /
/// staff role so the mobile driver shell can drive trips end-to-end:
///
///   - List today's routes / pick one
///   - Start trip
///   - Push GPS pings every 30 s while the trip is running
///   - Mark students boarded / dropped
///   - Complete trip
class DriverRepository {
  DriverRepository(this._api);
  final ApiClient _api;

  Future<List<DriverRoute>> routes() async {
    try {
      final res = await _api.dio.get<List<dynamic>>(
        '/v1/school-admin/transport/routes',
      );
      return (res.data ?? const [])
          .map((e) => DriverRoute.fromJson(e as Map<String, dynamic>))
          .toList();
    } on DioException {
      return const [];
    }
  }

  Future<DriverTrip> startTrip({
    required int routeId,
    required String tripDate,
    String direction = 'pickup',
  }) async {
    final res = await _api.dio.post<Map<String, dynamic>>(
      '/v1/school-admin/transport/trips/start',
      data: {
        'route_id': routeId,
        'trip_date': tripDate,
        'direction': direction,
      },
    );
    return DriverTrip.fromJson(res.data ?? const {});
  }

  Future<DriverTrip> pingTrip({
    required int tripId,
    required double lat,
    required double lng,
    double? speedKph,
  }) async {
    final res = await _api.dio.post<Map<String, dynamic>>(
      '/v1/school-admin/transport/trips/$tripId/ping',
      data: {
        'lat': lat,
        'lng': lng,
        if (speedKph != null) 'speed_kph': speedKph,
      },
    );
    return DriverTrip.fromJson(res.data ?? const {});
  }

  Future<DriverTrip> completeTrip({required int tripId}) async {
    final res = await _api.dio.post<Map<String, dynamic>>(
      '/v1/school-admin/transport/trips/$tripId/complete',
    );
    return DriverTrip.fromJson(res.data ?? const {});
  }

  Future<List<int>> todaySkipStudentIds(int routeId) async {
    try {
      final res = await _api.dio.get<List<dynamic>>(
        '/v1/school-admin/transport/routes/$routeId/skips',
      );
      return (res.data ?? const [])
          .map((e) => ((e as Map<String, dynamic>)['student_id'] as num).toInt())
          .toList();
    } on DioException {
      return const [];
    }
  }

  Future<void> recordBoarding({
    required int tripId,
    required int studentId,
    int? stopId,
    String event = 'boarded',
  }) async {
    await _api.dio.post<dynamic>(
      '/v1/school-admin/transport/trips/$tripId/boardings',
      data: {
        'student_id': studentId,
        if (stopId != null) 'stop_id': stopId,
        'event': event,
      },
    );
  }
}

class DriverRoute {
  const DriverRoute({
    required this.id,
    required this.code,
    required this.name,
    required this.busId,
    required this.driverId,
    required this.studentCount,
    required this.stopCount,
  });

  final int id;
  final String code;
  final String name;
  final int? busId;
  final int? driverId;
  final int studentCount;
  final int stopCount;

  factory DriverRoute.fromJson(Map<String, dynamic> j) => DriverRoute(
        id: (j['id'] as num).toInt(),
        code: (j['code'] as String?) ?? '',
        name: (j['name'] as String?) ?? '',
        busId: (j['bus_id'] as num?)?.toInt(),
        driverId: (j['driver_id'] as num?)?.toInt(),
        studentCount: (j['student_count'] as num?)?.toInt() ?? 0,
        stopCount: (j['stop_count'] as num?)?.toInt() ?? 0,
      );
}

class DriverTrip {
  const DriverTrip({
    required this.id,
    required this.routeId,
    required this.phase,
    required this.direction,
    required this.tripDate,
    required this.startedAt,
    required this.completedAt,
  });

  final int id;
  final int routeId;
  final String phase;
  final String? direction;
  final String? tripDate;
  final String? startedAt;
  final String? completedAt;

  factory DriverTrip.fromJson(Map<String, dynamic> j) => DriverTrip(
        id: (j['id'] as num?)?.toInt() ?? 0,
        routeId: (j['route_id'] as num?)?.toInt() ?? 0,
        phase: (j['phase'] as String?) ?? 'scheduled',
        direction: j['direction'] as String?,
        tripDate: j['trip_date'] as String?,
        startedAt: j['started_at'] as String?,
        completedAt: j['completed_at'] as String?,
      );
}
