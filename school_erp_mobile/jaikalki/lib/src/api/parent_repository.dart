import 'package:dio/dio.dart';

import 'api_client.dart';

class Child {
  Child({
    required this.studentId,
    required this.fullName,
    required this.admissionNumber,
    required this.classLabel,
    required this.relation,
    required this.accessLevel,
    required this.isPrimary,
  });

  final int studentId;
  final String fullName;
  final String admissionNumber;
  final String? classLabel;
  final String relation;
  final String accessLevel;
  final bool isPrimary;

  factory Child.fromJson(Map<String, dynamic> j) => Child(
        studentId: j['student_id'] as int,
        fullName: j['full_name'] as String,
        admissionNumber: j['admission_number'] as String,
        classLabel: j['current_class_label'] as String?,
        relation: j['relation'] as String,
        accessLevel: j['access_level'] as String,
        isPrimary: (j['is_primary'] as bool?) ?? false,
      );
}

class ChildDashboard {
  ChildDashboard({
    required this.studentId,
    required this.fullName,
    required this.admissionNumber,
    required this.classLabel,
    required this.isActive,
    required this.pendingLeaves,
    required this.documentsCount,
    required this.siblingIds,
    required this.upcomingEventsCount,
  });

  final int studentId;
  final String fullName;
  final String admissionNumber;
  final String? classLabel;
  final bool isActive;
  final int pendingLeaves;
  final int documentsCount;
  final List<int> siblingIds;
  final int upcomingEventsCount;

  factory ChildDashboard.fromJson(Map<String, dynamic> j) => ChildDashboard(
        studentId: j['student_id'] as int,
        fullName: j['full_name'] as String,
        admissionNumber: j['admission_number'] as String,
        classLabel: j['current_class_label'] as String?,
        isActive: (j['is_active'] as bool?) ?? true,
        pendingLeaves: (j['pending_leaves'] as num?)?.toInt() ?? 0,
        documentsCount: (j['documents_count'] as num?)?.toInt() ?? 0,
        siblingIds: ((j['sibling_ids'] as List<dynamic>?) ?? const [])
            .cast<num>()
            .map((n) => n.toInt())
            .toList(),
        upcomingEventsCount: (j['upcoming_events_count'] as num?)?.toInt() ?? 0,
      );
}

class ParentRepository {
  ParentRepository(this._api);

  final ApiClient _api;

  Future<List<Child>> children() async {
    try {
      final res = await _api.dio.get<List<dynamic>>('/v1/parent/children');
      return (res.data ?? const [])
          .map((e) => Child.fromJson(e as Map<String, dynamic>))
          .toList();
    } on DioException {
      return const [];
    }
  }

  Future<int> selectChild(int studentId) async {
    final res = await _api.dio.post<Map<String, dynamic>>(
      '/v1/parent/select-child',
      data: {'student_id': studentId},
    );
    return (res.data?['current_child_id'] as num?)?.toInt() ?? studentId;
  }

  Future<ChildDashboard> dashboard(int studentId) async {
    final res = await _api.dio.get<Map<String, dynamic>>('/v1/parent/dashboard/$studentId');
    return ChildDashboard.fromJson(res.data!);
  }

  Future<void> applyLeave({
    required int studentId,
    required String startDate,
    required String endDate,
    required String reason,
  }) async {
    await _api.dio.post<dynamic>(
      '/v1/parent/leave-applications',
      data: {
        'student_id': studentId,
        'start_date': startDate,
        'end_date': endDate,
        'reason': reason,
      },
    );
  }
}
