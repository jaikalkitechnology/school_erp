import 'package:dio/dio.dart';

import 'api_client.dart';

/// Driver-app wrapper around the existing /v1/school-admin/transport
/// router. Same backend endpoints, scoped to the ``transport_manager``
/// role so the mobile driver shell can drive trips end-to-end:
///
///   - List today's routes / pick one
///   - Start trip
///   - Push GPS pings every 15-30 s while the trip is running
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

  /// Roster of students currently allocated to a route — used by the
  /// Boarding scan page to render tap-to-mark rows.
  Future<List<DriverAllocation>> routeAllocations(int routeId) async {
    try {
      final res = await _api.dio.get<List<dynamic>>(
        '/v1/school-admin/transport/routes/$routeId/allocations',
      );
      return (res.data ?? const [])
          .map((e) => DriverAllocation.fromJson(e as Map<String, dynamic>))
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

  /// Driver's full student roster across every route — used by the
  /// Students tab. Each row carries parent / emergency contact +
  /// medical info + today's skip flag.
  Future<List<DriverStudent>> students() async {
    try {
      final res = await _api.dio.get<List<dynamic>>(
        '/v1/school-admin/transport/driver/students',
      );
      return (res.data ?? const [])
          .map((e) => DriverStudent.fromJson(e as Map<String, dynamic>))
          .toList();
    } on DioException {
      return const [];
    }
  }

  Future<List<TransportStopSimple>> routeStops(int routeId) async {
    try {
      final res = await _api.dio.get<List<dynamic>>(
        '/v1/school-admin/transport/routes/$routeId/stops',
      );
      return (res.data ?? const [])
          .map((e) => TransportStopSimple.fromJson(e as Map<String, dynamic>))
          .toList();
    } on DioException {
      return const [];
    }
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

/// One row of the route roster: a student allocated to this route,
/// plus their pickup stop. The Boarding page renders these as
/// tap-to-mark rows.
class DriverAllocation {
  const DriverAllocation({
    required this.id,
    required this.studentId,
    required this.studentName,
    required this.routeId,
    required this.pickupStopId,
    required this.dropStopId,
  });

  final int id;
  final int studentId;
  final String studentName;
  final int routeId;
  final int? pickupStopId;
  final int? dropStopId;

  factory DriverAllocation.fromJson(Map<String, dynamic> j) =>
      DriverAllocation(
        id: (j['id'] as num?)?.toInt() ?? 0,
        studentId: (j['student_id'] as num?)?.toInt() ?? 0,
        studentName: (j['student_name'] as String?) ??
            (j['full_name'] as String?) ??
            'Student #${j['student_id']}',
        routeId: (j['route_id'] as num?)?.toInt() ?? 0,
        pickupStopId: (j['pickup_stop_id'] as num?)?.toInt(),
        dropStopId: (j['drop_stop_id'] as num?)?.toInt(),
      );
}

class DriverStudent {
  const DriverStudent({
    required this.allocationId,
    required this.studentId,
    required this.studentName,
    required this.admissionNumber,
    required this.rollNo,
    required this.parentPhone,
    required this.emergencyPhone,
    required this.address,
    required this.medicalConditions,
    required this.allergies,
    required this.routeId,
    required this.routeName,
    required this.pickupStopName,
    required this.dropStopName,
    required this.skippedToday,
  });

  final int allocationId;
  final int studentId;
  final String studentName;
  final String? admissionNumber;
  final String? rollNo;
  final String? parentPhone;
  final String? emergencyPhone;
  final String? address;
  final String? medicalConditions;
  final String? allergies;
  final int routeId;
  final String? routeName;
  final String? pickupStopName;
  final String? dropStopName;
  final bool skippedToday;

  factory DriverStudent.fromJson(Map<String, dynamic> j) => DriverStudent(
        allocationId: (j['allocation_id'] as num?)?.toInt() ?? 0,
        studentId: (j['student_id'] as num?)?.toInt() ?? 0,
        studentName: (j['student_name'] as String?) ?? '',
        admissionNumber: j['admission_number'] as String?,
        rollNo: j['roll_no'] as String?,
        parentPhone: j['parent_phone'] as String?,
        emergencyPhone: j['emergency_phone'] as String?,
        address: j['address'] as String?,
        medicalConditions: j['medical_conditions'] as String?,
        allergies: j['allergies'] as String?,
        routeId: (j['route_id'] as num?)?.toInt() ?? 0,
        routeName: j['route_name'] as String?,
        pickupStopName: j['pickup_stop_name'] as String?,
        dropStopName: j['drop_stop_name'] as String?,
        skippedToday: (j['skipped_today'] as bool?) ?? false,
      );
}

class TransportStopSimple {
  const TransportStopSimple({
    required this.id,
    required this.name,
    required this.sequence,
    required this.latitude,
    required this.longitude,
    required this.scheduledArrival,
  });
  final int id;
  final String name;
  final int sequence;
  final double? latitude;
  final double? longitude;
  final String? scheduledArrival;

  factory TransportStopSimple.fromJson(Map<String, dynamic> j) =>
      TransportStopSimple(
        id: (j['id'] as num?)?.toInt() ?? 0,
        name: (j['name'] as String?) ?? '',
        sequence: (j['sequence'] as num?)?.toInt() ?? 0,
        latitude: (j['latitude'] as num?)?.toDouble(),
        longitude: (j['longitude'] as num?)?.toDouble(),
        scheduledArrival: j['scheduled_arrival'] as String?,
      );
}
