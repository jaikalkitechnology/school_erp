import 'package:dio/dio.dart';

import 'api_client.dart';
import 'notifications_repository.dart' show LoadError;

/// The coordinator's day (/v1/coordinator/today) + assigning cover via the
/// timetable substitutions endpoint.
class CoordinatorRepository {
  CoordinatorRepository(this._api);
  final ApiClient _api;

  Future<CoordinatorDay> today({DateTime? on}) async {
    try {
      final res = await _api.dio.get<Map<String, dynamic>>(
        '/v1/coordinator/today',
        queryParameters: {if (on != null) 'on': _ymd(on)},
      );
      return CoordinatorDay.fromJson(res.data ?? const {});
    } on DioException catch (e) {
      throw LoadError.from(e);
    }
  }

  /// Puts [substituteUserId] in for [period] of [sectionId] on [date].
  Future<void> assignCover({
    required String date,
    required int sectionId,
    required int period,
    required int substituteUserId,
    String? reason,
  }) async {
    try {
      await _api.dio.post<Map<String, dynamic>>(
        '/v1/school-admin/timetable/substitutions',
        data: {
          'date': date,
          'section_id': sectionId,
          'period_number': period,
          'substitute_teacher_user_id': substituteUserId,
          if (reason != null && reason.isNotEmpty) 'reason': reason,
        },
      );
    } on DioException catch (e) {
      throw LoadError.from(e);
    }
  }

  static String _ymd(DateTime d) =>
      '${d.year}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';
}

class CoordinatorDay {
  const CoordinatorDay({
    required this.date,
    required this.sections,
    required this.markedSections,
    required this.present,
    required this.absent,
    required this.percent,
    required this.sectionRows,
    required this.absentTeachers,
    required this.coverNeeded,
    required this.coverCovered,
  });

  final String date;
  final int sections;
  final int markedSections;
  final int present;
  final int absent;
  final double? percent;
  final List<SectionDay> sectionRows;
  final List<AbsentTeacher> absentTeachers;
  final int coverNeeded;
  final int coverCovered;

  factory CoordinatorDay.fromJson(Map<String, dynamic> j) {
    final att = (j['attendance'] as Map<String, dynamic>?) ?? const {};
    final cover = (j['cover'] as Map<String, dynamic>?) ?? const {};
    return CoordinatorDay(
      date: (j['date'] as String?) ?? '',
      sections: (att['sections'] as num?)?.toInt() ?? 0,
      markedSections: (att['marked_sections'] as num?)?.toInt() ?? 0,
      present: (att['present'] as num?)?.toInt() ?? 0,
      absent: (att['absent'] as num?)?.toInt() ?? 0,
      percent: (att['percent'] as num?)?.toDouble(),
      sectionRows: ((j['sections'] as List<dynamic>?) ?? const [])
          .map((e) => SectionDay.fromJson(e as Map<String, dynamic>))
          .toList(),
      absentTeachers: ((j['absent_teachers'] as List<dynamic>?) ?? const [])
          .map((e) => AbsentTeacher.fromJson(e as Map<String, dynamic>))
          .toList(),
      coverNeeded: (cover['needed'] as num?)?.toInt() ?? 0,
      coverCovered: (cover['covered'] as num?)?.toInt() ?? 0,
    );
  }
}

class SectionDay {
  const SectionDay({
    required this.sectionId,
    required this.label,
    required this.classTeacher,
    required this.strength,
    required this.marked,
    required this.present,
    required this.absent,
  });

  final int sectionId;
  final String label;
  final String? classTeacher;
  final int strength;
  final bool marked;
  final int present;
  final int absent;

  factory SectionDay.fromJson(Map<String, dynamic> j) => SectionDay(
        sectionId: (j['section_id'] as num).toInt(),
        label: (j['label'] as String?) ?? '',
        classTeacher: j['class_teacher'] as String?,
        strength: (j['strength'] as num?)?.toInt() ?? 0,
        marked: (j['marked'] as bool?) ?? false,
        present: (j['present'] as num?)?.toInt() ?? 0,
        absent: (j['absent'] as num?)?.toInt() ?? 0,
      );
}

class AbsentTeacher {
  const AbsentTeacher({required this.userId, required this.name, required this.reason, required this.periods});

  final int userId;
  final String name;
  final String reason;
  final List<CoverPeriod> periods;

  int get uncovered => periods.where((p) => !p.covered).length;

  factory AbsentTeacher.fromJson(Map<String, dynamic> j) => AbsentTeacher(
        userId: (j['user_id'] as num).toInt(),
        name: (j['name'] as String?) ?? '',
        reason: (j['reason'] as String?) ?? '',
        periods: ((j['periods'] as List<dynamic>?) ?? const [])
            .map((e) => CoverPeriod.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
}

class CoverPeriod {
  const CoverPeriod({
    required this.sectionId,
    required this.sectionLabel,
    required this.period,
    required this.subject,
    required this.substituteName,
    required this.suggestions,
  });

  final int sectionId;
  final String sectionLabel;
  final int period;
  final String? subject;

  /// Who is covering, if anyone has been assigned yet.
  final String? substituteName;
  final List<({int userId, String name})> suggestions;

  bool get covered => substituteName != null;

  factory CoverPeriod.fromJson(Map<String, dynamic> j) {
    final sub = j['substitution'] as Map<String, dynamic>?;
    return CoverPeriod(
      sectionId: (j['section_id'] as num).toInt(),
      sectionLabel: (j['section_label'] as String?) ?? '',
      period: (j['period_number'] as num).toInt(),
      subject: j['subject'] as String?,
      substituteName: sub == null || sub['substitute_user_id'] == null
          ? null
          : ((sub['substitute_name'] as String?) ?? 'Assigned'),
      suggestions: ((j['suggestions'] as List<dynamic>?) ?? const [])
          .map((e) => e as Map<String, dynamic>)
          .map((e) => (userId: (e['user_id'] as num).toInt(), name: (e['name'] as String?) ?? ''))
          .toList(),
    );
  }
}
