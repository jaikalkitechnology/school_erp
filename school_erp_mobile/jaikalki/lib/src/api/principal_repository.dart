import 'package:dio/dio.dart';

import 'api_client.dart';

/// Backend wrapper for the Principal mobile shell. Mirrors
/// ``/v1/principal/*``.
class PrincipalRepository {
  PrincipalRepository(this._api);
  final ApiClient _api;

  Future<PrincipalDashboard?> dashboard() async {
    try {
      final res = await _api.dio.get<Map<String, dynamic>>(
        '/v1/principal/dashboard',
      );
      final data = res.data;
      if (data == null) return null;
      return PrincipalDashboard.fromJson(data);
    } on DioException {
      return null;
    }
  }

  Future<List<ApprovalRow>> approvals({String? kind}) async {
    try {
      final res = await _api.dio.get<List<dynamic>>(
        '/v1/principal/approvals',
        queryParameters: kind == null ? null : {'kind': kind},
      );
      return (res.data ?? const [])
          .map((e) => ApprovalRow.fromJson(e as Map<String, dynamic>))
          .toList();
    } on DioException {
      return const [];
    }
  }

  Future<bool> decideApproval({
    required String kind,
    required int rowId,
    required bool approve,
    String? remarks,
  }) async {
    try {
      await _api.dio.post<dynamic>(
        '/v1/principal/approvals/$kind/$rowId/decide',
        queryParameters: {
          'decision': approve ? 'approve' : 'reject',
          if (remarks != null && remarks.isNotEmpty) 'remarks': remarks,
        },
      );
      return true;
    } on DioException {
      return false;
    }
  }

  Future<AttendanceByClass?> attendanceByClass({DateTime? on}) async {
    try {
      final res = await _api.dio.get<Map<String, dynamic>>(
        '/v1/principal/academics/attendance-by-class',
        queryParameters: on == null
            ? null
            : {'on': on.toIso8601String().substring(0, 10)},
      );
      final data = res.data;
      if (data == null) return null;
      return AttendanceByClass.fromJson(data);
    } on DioException {
      return null;
    }
  }

  Future<List<StaffRow>> staff() async {
    try {
      final res = await _api.dio.get<List<dynamic>>(
        '/v1/principal/staff',
      );
      return (res.data ?? const [])
          .map((e) => StaffRow.fromJson(e as Map<String, dynamic>))
          .toList();
    } on DioException {
      return const [];
    }
  }

  Future<FinanceSnapshot?> financeSnapshot({int daysBack = 30}) async {
    try {
      final res = await _api.dio.get<Map<String, dynamic>>(
        '/v1/principal/finance/snapshot',
        queryParameters: {'days_back': daysBack},
      );
      final data = res.data;
      if (data == null) return null;
      return FinanceSnapshot.fromJson(data);
    } on DioException {
      return null;
    }
  }

  Future<List<DisciplineRow>> recentDiscipline({int daysBack = 7}) async {
    try {
      final res = await _api.dio.get<List<dynamic>>(
        '/v1/principal/discipline/recent',
        queryParameters: {'days_back': daysBack},
      );
      return (res.data ?? const [])
          .map((e) => DisciplineRow.fromJson(e as Map<String, dynamic>))
          .toList();
    } on DioException {
      return const [];
    }
  }

  Future<FleetStatus?> fleetStatus() async {
    try {
      final res = await _api.dio.get<Map<String, dynamic>>(
        '/v1/principal/transport/fleet-status',
      );
      final data = res.data;
      if (data == null) return null;
      return FleetStatus.fromJson(data);
    } on DioException {
      return null;
    }
  }
}

// --- models ---------------------------------------------------------------

class PrincipalDashboard {
  const PrincipalDashboard({
    required this.asOf,
    required this.attendance,
    required this.staff,
    required this.fees,
    required this.transport,
    required this.approvals,
    required this.alerts,
  });

  final String asOf;
  final AttendanceSummary attendance;
  final StaffSummary staff;
  final FeesSummary fees;
  final TransportSummary transport;
  final ApprovalsSummary approvals;
  final AlertsSummary alerts;

  factory PrincipalDashboard.fromJson(Map<String, dynamic> j) =>
      PrincipalDashboard(
        asOf: (j['as_of'] as String?) ?? '',
        attendance: AttendanceSummary.fromJson(
            (j['attendance'] as Map?)?.cast<String, dynamic>() ?? const {}),
        staff: StaffSummary.fromJson(
            (j['staff'] as Map?)?.cast<String, dynamic>() ?? const {}),
        fees: FeesSummary.fromJson(
            (j['fees'] as Map?)?.cast<String, dynamic>() ?? const {}),
        transport: TransportSummary.fromJson(
            (j['transport'] as Map?)?.cast<String, dynamic>() ?? const {}),
        approvals: ApprovalsSummary.fromJson(
            (j['approvals'] as Map?)?.cast<String, dynamic>() ?? const {}),
        alerts: AlertsSummary.fromJson(
            (j['alerts'] as Map?)?.cast<String, dynamic>() ?? const {}),
      );
}

class AttendanceSummary {
  const AttendanceSummary({
    required this.totalStudents,
    required this.studentsMarked,
    required this.studentsPresent,
    required this.studentsAbsent,
    required this.percent,
  });
  final int totalStudents;
  final int studentsMarked;
  final int studentsPresent;
  final int studentsAbsent;
  final double percent;

  factory AttendanceSummary.fromJson(Map<String, dynamic> j) =>
      AttendanceSummary(
        totalStudents: (j['total_students'] as num?)?.toInt() ?? 0,
        studentsMarked: (j['students_marked'] as num?)?.toInt() ?? 0,
        studentsPresent: (j['students_present'] as num?)?.toInt() ?? 0,
        studentsAbsent: (j['students_absent'] as num?)?.toInt() ?? 0,
        percent: (j['percent'] as num?)?.toDouble() ?? 0,
      );
}

class StaffSummary {
  const StaffSummary({required this.total, required this.onLeaveToday});
  final int total;
  final int onLeaveToday;

  factory StaffSummary.fromJson(Map<String, dynamic> j) => StaffSummary(
        total: (j['total'] as num?)?.toInt() ?? 0,
        onLeaveToday: (j['on_leave_today'] as num?)?.toInt() ?? 0,
      );
}

class FeesSummary {
  const FeesSummary({
    required this.collectedToday,
    required this.collectedMtd,
    required this.outstandingTotal,
    required this.overdueInvoices,
  });
  final double collectedToday;
  final double collectedMtd;
  final double outstandingTotal;
  final int overdueInvoices;

  factory FeesSummary.fromJson(Map<String, dynamic> j) => FeesSummary(
        collectedToday: (j['collected_today'] as num?)?.toDouble() ?? 0,
        collectedMtd: (j['collected_mtd'] as num?)?.toDouble() ?? 0,
        outstandingTotal: (j['outstanding_total'] as num?)?.toDouble() ?? 0,
        overdueInvoices: (j['overdue_invoices'] as num?)?.toInt() ?? 0,
      );
}

class TransportSummary {
  const TransportSummary({required this.tripsInProgress});
  final int tripsInProgress;
  factory TransportSummary.fromJson(Map<String, dynamic> j) =>
      TransportSummary(
        tripsInProgress: (j['trips_in_progress'] as num?)?.toInt() ?? 0,
      );
}

class ApprovalsSummary {
  const ApprovalsSummary({
    required this.pendingTotal,
    required this.pendingStudentLeaves,
    required this.pendingStaffLeaves,
  });
  final int pendingTotal;
  final int pendingStudentLeaves;
  final int pendingStaffLeaves;

  factory ApprovalsSummary.fromJson(Map<String, dynamic> j) =>
      ApprovalsSummary(
        pendingTotal: (j['pending_total'] as num?)?.toInt() ?? 0,
        pendingStudentLeaves:
            (j['pending_student_leaves'] as num?)?.toInt() ?? 0,
        pendingStaffLeaves:
            (j['pending_staff_leaves'] as num?)?.toInt() ?? 0,
      );
}

class AlertsSummary {
  const AlertsSummary({
    required this.behaviourConcernsToday,
    required this.overdueInvoices,
  });
  final int behaviourConcernsToday;
  final int overdueInvoices;

  factory AlertsSummary.fromJson(Map<String, dynamic> j) => AlertsSummary(
        behaviourConcernsToday:
            (j['behaviour_concerns_today'] as num?)?.toInt() ?? 0,
        overdueInvoices: (j['overdue_invoices'] as num?)?.toInt() ?? 0,
      );
}

class ApprovalRow {
  const ApprovalRow({
    required this.kind,
    required this.id,
    required this.title,
    required this.subtitle,
    required this.startDate,
    required this.endDate,
    required this.appliedAt,
  });

  final String kind;
  final int id;
  final String title;
  final String subtitle;
  final String startDate;
  final String endDate;
  final String? appliedAt;

  factory ApprovalRow.fromJson(Map<String, dynamic> j) => ApprovalRow(
        kind: (j['kind'] as String?) ?? '',
        id: (j['id'] as num?)?.toInt() ?? 0,
        title: (j['title'] as String?) ?? '',
        subtitle: (j['subtitle'] as String?) ?? '',
        startDate: (j['start_date'] as String?) ?? '',
        endDate: (j['end_date'] as String?) ?? '',
        appliedAt: j['applied_at'] as String?,
      );
}

class AttendanceByClass {
  const AttendanceByClass({required this.date, required this.classes});
  final String date;
  final List<ClassAttendanceRow> classes;

  factory AttendanceByClass.fromJson(Map<String, dynamic> j) =>
      AttendanceByClass(
        date: (j['date'] as String?) ?? '',
        classes: ((j['classes'] as List<dynamic>?) ?? const [])
            .map((e) => ClassAttendanceRow.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
}

class ClassAttendanceRow {
  const ClassAttendanceRow({
    required this.classDefId,
    required this.name,
    required this.sequence,
    required this.totalStudents,
    required this.marked,
    required this.present,
    required this.absent,
    required this.percent,
  });
  final int classDefId;
  final String name;
  final int sequence;
  final int totalStudents;
  final int marked;
  final int present;
  final int absent;
  final double percent;

  factory ClassAttendanceRow.fromJson(Map<String, dynamic> j) =>
      ClassAttendanceRow(
        classDefId: (j['class_def_id'] as num?)?.toInt() ?? 0,
        name: (j['name'] as String?) ?? '',
        sequence: (j['sequence'] as num?)?.toInt() ?? 0,
        totalStudents: (j['total_students'] as num?)?.toInt() ?? 0,
        marked: (j['marked'] as num?)?.toInt() ?? 0,
        present: (j['present'] as num?)?.toInt() ?? 0,
        absent: (j['absent'] as num?)?.toInt() ?? 0,
        percent: (j['percent'] as num?)?.toDouble() ?? 0,
      );
}

class StaffRow {
  const StaffRow({
    required this.userId,
    required this.fullName,
    required this.phone,
    required this.email,
    required this.isActive,
    required this.roles,
    required this.onLeaveToday,
    required this.leaveKind,
    required this.leaveEnd,
  });
  final int userId;
  final String fullName;
  final String? phone;
  final String? email;
  final bool isActive;
  final List<String> roles;
  final bool onLeaveToday;
  final String? leaveKind;
  final String? leaveEnd;

  factory StaffRow.fromJson(Map<String, dynamic> j) => StaffRow(
        userId: (j['user_id'] as num?)?.toInt() ?? 0,
        fullName: (j['full_name'] as String?) ?? '',
        phone: j['phone'] as String?,
        email: j['email'] as String?,
        isActive: (j['is_active'] as bool?) ?? true,
        roles: ((j['roles'] as List<dynamic>?) ?? const [])
            .map((e) => e.toString())
            .toList(),
        onLeaveToday: (j['on_leave_today'] as bool?) ?? false,
        leaveKind: j['leave_kind'] as String?,
        leaveEnd: j['leave_end'] as String?,
      );
}

class FinanceSnapshot {
  const FinanceSnapshot({
    required this.byClass,
    required this.topDefaulters,
    required this.dailyCollection,
  });
  final List<ClassFeeRow> byClass;
  final List<DefaulterRow> topDefaulters;
  final List<DailyCollectionPoint> dailyCollection;

  factory FinanceSnapshot.fromJson(Map<String, dynamic> j) => FinanceSnapshot(
        byClass: ((j['by_class'] as List<dynamic>?) ?? const [])
            .map((e) => ClassFeeRow.fromJson(e as Map<String, dynamic>))
            .toList(),
        topDefaulters: ((j['top_defaulters'] as List<dynamic>?) ?? const [])
            .map((e) => DefaulterRow.fromJson(e as Map<String, dynamic>))
            .toList(),
        dailyCollection:
            ((j['daily_collection'] as List<dynamic>?) ?? const [])
                .map((e) =>
                    DailyCollectionPoint.fromJson(e as Map<String, dynamic>))
                .toList(),
      );
}

class ClassFeeRow {
  const ClassFeeRow({
    required this.classDefId,
    required this.name,
    required this.sequence,
    required this.billed,
    required this.collected,
    required this.outstanding,
  });
  final int classDefId;
  final String name;
  final int sequence;
  final double billed;
  final double collected;
  final double outstanding;

  factory ClassFeeRow.fromJson(Map<String, dynamic> j) => ClassFeeRow(
        classDefId: (j['class_def_id'] as num?)?.toInt() ?? 0,
        name: (j['name'] as String?) ?? '',
        sequence: (j['sequence'] as num?)?.toInt() ?? 0,
        billed: (j['billed'] as num?)?.toDouble() ?? 0,
        collected: (j['collected'] as num?)?.toDouble() ?? 0,
        outstanding: (j['outstanding'] as num?)?.toDouble() ?? 0,
      );
}

class DefaulterRow {
  const DefaulterRow({
    required this.studentId,
    required this.fullName,
    required this.admissionNumber,
    required this.amountDue,
  });
  final int studentId;
  final String fullName;
  final String? admissionNumber;
  final double amountDue;

  factory DefaulterRow.fromJson(Map<String, dynamic> j) => DefaulterRow(
        studentId: (j['student_id'] as num?)?.toInt() ?? 0,
        fullName: (j['full_name'] as String?) ?? '',
        admissionNumber: j['admission_number'] as String?,
        amountDue: (j['amount_due'] as num?)?.toDouble() ?? 0,
      );
}

class DailyCollectionPoint {
  const DailyCollectionPoint({required this.date, required this.amount});
  final String date;
  final double amount;

  factory DailyCollectionPoint.fromJson(Map<String, dynamic> j) =>
      DailyCollectionPoint(
        date: (j['date'] as String?) ?? '',
        amount: (j['amount'] as num?)?.toDouble() ?? 0,
      );
}

class DisciplineRow {
  const DisciplineRow({
    required this.id,
    required this.studentId,
    required this.studentName,
    required this.teacherName,
    required this.occurredOn,
    required this.headline,
    required this.detail,
  });
  final int id;
  final int studentId;
  final String studentName;
  final String? teacherName;
  final String occurredOn;
  final String headline;
  final String? detail;

  factory DisciplineRow.fromJson(Map<String, dynamic> j) => DisciplineRow(
        id: (j['id'] as num?)?.toInt() ?? 0,
        studentId: (j['student_id'] as num?)?.toInt() ?? 0,
        studentName: (j['student_name'] as String?) ?? '',
        teacherName: j['teacher_name'] as String?,
        occurredOn: (j['occurred_on'] as String?) ?? '',
        headline: (j['headline'] as String?) ?? '',
        detail: j['detail'] as String?,
      );
}

class FleetStatus {
  const FleetStatus({
    required this.date,
    required this.scheduled,
    required this.inProgress,
    required this.completed,
    required this.cancelled,
  });
  final String date;
  final int scheduled;
  final int inProgress;
  final int completed;
  final int cancelled;

  factory FleetStatus.fromJson(Map<String, dynamic> j) => FleetStatus(
        date: (j['date'] as String?) ?? '',
        scheduled: (j['scheduled'] as num?)?.toInt() ?? 0,
        inProgress: (j['in_progress'] as num?)?.toInt() ?? 0,
        completed: (j['completed'] as num?)?.toInt() ?? 0,
        cancelled: (j['cancelled'] as num?)?.toInt() ?? 0,
      );
}
