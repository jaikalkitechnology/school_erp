import 'package:dio/dio.dart';

import 'api_client.dart';

/// Read-only mobile wrapper for the Phase 28 operations endpoints.
/// Everything the shells + more-pages need: notices, sports,
/// payslips (teachers), health / discipline / certificates
/// (parents, per child).
class OperationsRepository {
  OperationsRepository(this._api);
  final ApiClient _api;

  Future<List<NoticeItem>> notices() async {
    try {
      final res = await _api.dio.get<List<dynamic>>('/v1/mobile/notices');
      return (res.data ?? const [])
          .map((e) => NoticeItem.fromJson(e as Map<String, dynamic>))
          .toList();
    } on DioException {
      return const [];
    }
  }

  Future<List<HouseRow>> sportsHouses() async {
    try {
      final res =
          await _api.dio.get<List<dynamic>>('/v1/mobile/sports/houses');
      return (res.data ?? const [])
          .map((e) => HouseRow.fromJson(e as Map<String, dynamic>))
          .toList();
    } on DioException {
      return const [];
    }
  }

  Future<List<SportsEventRow>> sportsEvents({bool upcomingOnly = false}) async {
    try {
      final res = await _api.dio.get<List<dynamic>>(
        '/v1/mobile/sports/events',
        queryParameters: upcomingOnly ? {'upcoming_only': true} : null,
      );
      return (res.data ?? const [])
          .map((e) => SportsEventRow.fromJson(e as Map<String, dynamic>))
          .toList();
    } on DioException {
      return const [];
    }
  }

  Future<List<PayslipRow>> myPayslips() async {
    try {
      final res =
          await _api.dio.get<List<dynamic>>('/v1/mobile/teacher/me/payslips');
      return (res.data ?? const [])
          .map((e) => PayslipRow.fromJson(e as Map<String, dynamic>))
          .toList();
    } on DioException {
      return const [];
    }
  }

  Future<List<HealthRow>> childHealth(int studentId) async {
    try {
      final res = await _api.dio.get<List<dynamic>>(
        '/v1/mobile/parent/children/$studentId/health-records',
      );
      return (res.data ?? const [])
          .map((e) => HealthRow.fromJson(e as Map<String, dynamic>))
          .toList();
    } on DioException {
      return const [];
    }
  }

  Future<List<DisciplineRow>> childDiscipline(int studentId) async {
    try {
      final res = await _api.dio.get<List<dynamic>>(
        '/v1/mobile/parent/children/$studentId/discipline',
      );
      return (res.data ?? const [])
          .map((e) => DisciplineRow.fromJson(e as Map<String, dynamic>))
          .toList();
    } on DioException {
      return const [];
    }
  }

  Future<List<CertificateRow>> childCertificates(int studentId) async {
    try {
      final res = await _api.dio.get<List<dynamic>>(
        '/v1/mobile/parent/children/$studentId/certificates',
      );
      return (res.data ?? const [])
          .map((e) => CertificateRow.fromJson(e as Map<String, dynamic>))
          .toList();
    } on DioException {
      return const [];
    }
  }
}

// ---- Models ---------------------------------------------------------------

class NoticeItem {
  const NoticeItem({
    required this.id,
    required this.title,
    required this.body,
    required this.audience,
    required this.isPinned,
    required this.publishedAt,
    required this.expiresAt,
  });

  final int id;
  final String title;
  final String body;
  final String audience;
  final bool isPinned;
  final String? publishedAt;
  final String? expiresAt;

  factory NoticeItem.fromJson(Map<String, dynamic> j) => NoticeItem(
        id: (j['id'] as num?)?.toInt() ?? 0,
        title: (j['title'] as String?) ?? '',
        body: (j['body'] as String?) ?? '',
        audience: (j['audience'] as String?) ?? 'all',
        isPinned: (j['is_pinned'] as bool?) ?? false,
        publishedAt: j['published_at'] as String?,
        expiresAt: j['expires_at'] as String?,
      );
}

class HouseRow {
  const HouseRow({
    required this.id,
    required this.name,
    required this.color,
    required this.motto,
    required this.points,
  });
  final int id;
  final String name;
  final String? color;
  final String? motto;
  final int points;

  factory HouseRow.fromJson(Map<String, dynamic> j) => HouseRow(
        id: (j['id'] as num?)?.toInt() ?? 0,
        name: (j['name'] as String?) ?? '',
        color: j['color'] as String?,
        motto: j['motto'] as String?,
        points: (j['points'] as num?)?.toInt() ?? 0,
      );
}

class SportsEventRow {
  const SportsEventRow({
    required this.id,
    required this.name,
    required this.kind,
    required this.sport,
    required this.startsOn,
    required this.endsOn,
    required this.venue,
    required this.winnerHouseId,
  });
  final int id;
  final String name;
  final String kind;
  final String? sport;
  final String startsOn;
  final String? endsOn;
  final String? venue;
  final int? winnerHouseId;

  factory SportsEventRow.fromJson(Map<String, dynamic> j) => SportsEventRow(
        id: (j['id'] as num?)?.toInt() ?? 0,
        name: (j['name'] as String?) ?? '',
        kind: (j['kind'] as String?) ?? 'match',
        sport: j['sport'] as String?,
        startsOn: (j['starts_on'] as String?) ?? '',
        endsOn: j['ends_on'] as String?,
        venue: j['venue'] as String?,
        winnerHouseId: (j['winner_house_id'] as num?)?.toInt(),
      );
}

class PayslipRow {
  const PayslipRow({
    required this.id,
    required this.period,
    required this.basic,
    required this.hra,
    required this.otherEarnings,
    required this.totalDeductions,
    required this.netPay,
    required this.status,
    required this.paidOn,
  });
  final int id;
  final String period;
  final double basic;
  final double hra;
  final double otherEarnings;
  final double totalDeductions;
  final double netPay;
  final String status;
  final String? paidOn;

  factory PayslipRow.fromJson(Map<String, dynamic> j) => PayslipRow(
        id: (j['id'] as num?)?.toInt() ?? 0,
        period: (j['period'] as String?) ?? '',
        basic: (j['basic'] as num?)?.toDouble() ?? 0,
        hra: (j['hra'] as num?)?.toDouble() ?? 0,
        otherEarnings: (j['other_earnings'] as num?)?.toDouble() ?? 0,
        totalDeductions: (j['total_deductions'] as num?)?.toDouble() ?? 0,
        netPay: (j['net_pay'] as num?)?.toDouble() ?? 0,
        status: (j['status'] as String?) ?? 'draft',
        paidOn: j['paid_on'] as String?,
      );
}

class HealthRow {
  const HealthRow({
    required this.id,
    required this.kind,
    required this.title,
    required this.description,
    required this.occurredOn,
    required this.severity,
    required this.treatment,
    required this.medication,
    required this.followUpOn,
  });
  final int id;
  final String kind;
  final String title;
  final String? description;
  final String occurredOn;
  final String? severity;
  final String? treatment;
  final String? medication;
  final String? followUpOn;

  factory HealthRow.fromJson(Map<String, dynamic> j) => HealthRow(
        id: (j['id'] as num?)?.toInt() ?? 0,
        kind: (j['kind'] as String?) ?? 'visit',
        title: (j['title'] as String?) ?? '',
        description: j['description'] as String?,
        occurredOn: (j['occurred_on'] as String?) ?? '',
        severity: j['severity'] as String?,
        treatment: j['treatment'] as String?,
        medication: j['medication'] as String?,
        followUpOn: j['follow_up_on'] as String?,
      );
}

class DisciplineRow {
  const DisciplineRow({
    required this.id,
    required this.occurredOn,
    required this.severity,
    required this.headline,
    required this.description,
    required this.actionTaken,
    required this.location,
    required this.parentInformed,
  });
  final int id;
  final String occurredOn;
  final String severity;
  final String headline;
  final String? description;
  final String? actionTaken;
  final String? location;
  final bool parentInformed;

  factory DisciplineRow.fromJson(Map<String, dynamic> j) => DisciplineRow(
        id: (j['id'] as num?)?.toInt() ?? 0,
        occurredOn: (j['occurred_on'] as String?) ?? '',
        severity: (j['severity'] as String?) ?? 'minor',
        headline: (j['headline'] as String?) ?? '',
        description: j['description'] as String?,
        actionTaken: j['action_taken'] as String?,
        location: j['location'] as String?,
        parentInformed: (j['parent_informed'] as bool?) ?? false,
      );
}

class CertificateRow {
  const CertificateRow({
    required this.id,
    required this.templateCode,
    required this.forName,
    required this.referenceNo,
    required this.issuedOn,
    required this.renderedBody,
  });
  final int id;
  final String templateCode;
  final String forName;
  final String referenceNo;
  final String issuedOn;
  final String renderedBody;

  factory CertificateRow.fromJson(Map<String, dynamic> j) => CertificateRow(
        id: (j['id'] as num?)?.toInt() ?? 0,
        templateCode: (j['template_code'] as String?) ?? '',
        forName: (j['for_name'] as String?) ?? '',
        referenceNo: (j['reference_no'] as String?) ?? '',
        issuedOn: (j['issued_on'] as String?) ?? '',
        renderedBody: (j['rendered_body'] as String?) ?? '',
      );
}
