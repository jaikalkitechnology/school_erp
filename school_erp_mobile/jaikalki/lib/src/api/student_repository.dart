import 'package:dio/dio.dart';

import 'api_client.dart';
import 'parent_repository.dart'
    show
        AttendanceRow,
        ChildDashboard,
        HomeworkItem,
        ResultCardRow,
        StudentProfile;

/// Student self-service wrapper around the /v1/student/* endpoints.
///
/// A student login sees only their own data — the backend resolves the
/// caller's Student row via ``Student.user_id`` under a tenant-scoped
/// session, so no student_id is ever sent from the client.
class StudentRepository {
  StudentRepository(this._api);
  final ApiClient _api;

  Future<ChildDashboard?> dashboard() async {
    try {
      final res = await _api.dio.get<Map<String, dynamic>>(
        '/v1/student/dashboard',
      );
      final data = res.data;
      if (data == null) return null;
      return ChildDashboard.fromJson(data);
    } on DioException {
      return null;
    }
  }

  Future<StudentProfile?> me() async {
    try {
      final res = await _api.dio.get<Map<String, dynamic>>('/v1/student/me');
      final data = res.data;
      if (data == null) return null;
      return StudentProfile.fromJson(data);
    } on DioException {
      return null;
    }
  }

  Future<List<AttendanceRow>> attendance({int limit = 60}) async {
    try {
      final res = await _api.dio.get<List<dynamic>>(
        '/v1/student/attendance',
        queryParameters: {'limit': limit},
      );
      return (res.data ?? const [])
          .map((e) => AttendanceRow.fromJson(e as Map<String, dynamic>))
          .toList();
    } on DioException {
      return const [];
    }
  }

  Future<List<HomeworkItem>> homework() async {
    try {
      final res = await _api.dio.get<List<dynamic>>('/v1/student/homework');
      return (res.data ?? const [])
          .map((e) => HomeworkItem.fromJson(e as Map<String, dynamic>))
          .toList();
    } on DioException {
      return const [];
    }
  }

  Future<void> submitHomework({
    required int homeworkId,
    required String content,
    List<String>? attachmentPaths,
  }) async {
    await _api.dio.post<dynamic>(
      '/v1/student/homework/submit',
      data: {
        'homework_id': homeworkId,
        'content': content,
        if (attachmentPaths != null && attachmentPaths.isNotEmpty)
          'attachments': attachmentPaths,
      },
    );
  }

  Future<List<ResultCardRow>> reportCards() async {
    try {
      final res = await _api.dio.get<Map<String, dynamic>>(
        '/v1/student/report-cards',
      );
      final rows = (res.data?['rows'] as List<dynamic>?) ?? const [];
      return rows
          .map((e) => ResultCardRow.fromJson(e as Map<String, dynamic>))
          .toList();
    } on DioException {
      return const [];
    }
  }

  /// Weekly timetable as returned by the backend. Kept as raw maps because
  /// the shape mirrors the parent timetable view, which the UI renders
  /// generically.
  Future<List<Map<String, dynamic>>> timetable() async {
    try {
      final res = await _api.dio.get<dynamic>('/v1/student/timetable');
      final data = res.data;
      if (data is List) {
        return data.cast<Map<String, dynamic>>();
      }
      if (data is Map && data['slots'] is List) {
        return (data['slots'] as List).cast<Map<String, dynamic>>();
      }
      return const [];
    } on DioException {
      return const [];
    }
  }
}
