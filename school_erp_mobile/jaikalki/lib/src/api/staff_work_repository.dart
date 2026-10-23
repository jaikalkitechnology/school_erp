import 'package:dio/dio.dart';

import 'api_client.dart';
import 'notifications_repository.dart' show LoadError, parseServerTime;

/// Work tabs for non-teaching staff: Fees (accountant), Library
/// (librarian) and Hostel (hostel warden). Summaries come from
/// /v1/staff/<area>/today with names filled in.
class StaffWorkRepository {
  StaffWorkRepository(this._api);
  final ApiClient _api;

  Future<Map<String, dynamic>> _get(String path) async {
    try {
      final res = await _api.dio.get<Map<String, dynamic>>(path);
      return res.data ?? const {};
    } on DioException catch (e) {
      throw LoadError.from(e);
    }
  }

  Future<Map<String, dynamic>> _post(String path, [Map<String, dynamic>? data]) async {
    try {
      final res = await _api.dio.post<Map<String, dynamic>>(path, data: data);
      return res.data ?? const {};
    } on DioException catch (e) {
      throw LoadError.from(e);
    }
  }

  // ---- Accountant ----
  Future<FeesDay> feesToday() async => FeesDay.fromJson(await _get('/v1/staff/fees/today'));

  // ---- Librarian ----
  Future<LibraryDay> libraryToday() async => LibraryDay.fromJson(await _get('/v1/staff/library/today'));

  /// Returns the title of the book that was checked in, and any fine.
  Future<({String title, double fine})> returnByBarcode(String barcode) async {
    final r = await _post('/v1/staff/library/return-by-barcode', {'barcode': barcode});
    return (title: (r['title'] as String?) ?? 'Book', fine: _num(r['fine_amount']));
  }

  // ---- Hostel warden ----
  Future<HostelDay> hostelToday() async => HostelDay.fromJson(await _get('/v1/staff/hostel/today'));

  /// [decision] is "approved" or "rejected".
  Future<void> decideHostelLeave(int leaveId, String decision) =>
      _post('/v1/school-admin/hostel/leaves/$leaveId/decide', {'decision': decision});

  Future<void> checkOutVisitor(int visitorId) => _post('/v1/school-admin/hostel/visitors/$visitorId/checkout');
}

/// Money comes as a string ("1234.50") from the API.
double _num(Object? v) => v is num ? v.toDouble() : double.tryParse('${v ?? ''}') ?? 0;

List<Map<String, dynamic>> _list(Object? v) =>
    ((v as List<dynamic>?) ?? const []).map((e) => e as Map<String, dynamic>).toList();

class FeesDay {
  const FeesDay({
    required this.collectedToday,
    required this.collectedMonth,
    required this.pending,
    required this.overdue,
    required this.byMethodToday,
    required this.defaulters,
  });

  final double collectedToday;
  final double collectedMonth;
  final double pending;
  final double overdue;
  final Map<String, double> byMethodToday;
  final List<Defaulter> defaulters;

  factory FeesDay.fromJson(Map<String, dynamic> j) => FeesDay(
        collectedToday: _num(j['collected_today']),
        collectedMonth: _num(j['collected_month']),
        pending: _num(j['pending']),
        overdue: _num(j['overdue']),
        byMethodToday: ((j['by_method_today'] as Map<String, dynamic>?) ?? const {})
            .map((k, v) => MapEntry(k, _num(v))),
        defaulters: _list(j['defaulters']).map(Defaulter.fromJson).toList(),
      );
}

class Defaulter {
  const Defaulter({
    required this.name,
    required this.admissionNumber,
    required this.classLabel,
    required this.invoicesOverdue,
    required this.amountOverdue,
    required this.parentPhone,
  });

  final String name;
  final String admissionNumber;
  final String classLabel;
  final int invoicesOverdue;
  final double amountOverdue;
  final String? parentPhone;

  factory Defaulter.fromJson(Map<String, dynamic> j) => Defaulter(
        name: (j['name'] as String?) ?? '',
        admissionNumber: (j['admission_number'] as String?) ?? '',
        classLabel: (j['class_label'] as String?) ?? '',
        invoicesOverdue: (j['invoices_overdue'] as num?)?.toInt() ?? 0,
        amountOverdue: _num(j['amount_overdue']),
        parentPhone: j['parent_phone'] as String?,
      );
}

class LibraryDay {
  const LibraryDay({
    required this.issuedToday,
    required this.returnedToday,
    required this.onLoan,
    required this.overdue,
    required this.reservations,
  });

  final int issuedToday;
  final int returnedToday;
  final int onLoan;
  final List<OverdueLoan> overdue;
  final List<WaitingReservation> reservations;

  factory LibraryDay.fromJson(Map<String, dynamic> j) => LibraryDay(
        issuedToday: (j['issued_today'] as num?)?.toInt() ?? 0,
        returnedToday: (j['returned_today'] as num?)?.toInt() ?? 0,
        onLoan: (j['on_loan'] as num?)?.toInt() ?? 0,
        overdue: _list(j['overdue']).map(OverdueLoan.fromJson).toList(),
        reservations: _list(j['reservations']).map(WaitingReservation.fromJson).toList(),
      );
}

class OverdueLoan {
  const OverdueLoan({required this.title, required this.barcode, required this.borrower, required this.daysOverdue});

  final String title;
  final String barcode;
  final String borrower;
  final int daysOverdue;

  factory OverdueLoan.fromJson(Map<String, dynamic> j) => OverdueLoan(
        title: (j['title'] as String?) ?? '',
        barcode: (j['barcode'] as String?) ?? '',
        borrower: (j['borrower'] as String?) ?? '',
        daysOverdue: (j['days_overdue'] as num?)?.toInt() ?? 0,
      );
}

class WaitingReservation {
  const WaitingReservation({required this.title, required this.borrower, required this.status});

  final String title;
  final String borrower;

  /// pending (waiting for a copy) / ready (a copy is set aside).
  final String status;

  factory WaitingReservation.fromJson(Map<String, dynamic> j) => WaitingReservation(
        title: (j['title'] as String?) ?? '',
        borrower: (j['borrower'] as String?) ?? '',
        status: (j['status'] as String?) ?? 'pending',
      );
}

class HostelDay {
  const HostelDay({
    required this.capacity,
    required this.occupied,
    required this.available,
    required this.awayOnLeave,
    required this.pendingLeaves,
    required this.visitorsIn,
  });

  final int capacity;
  final int occupied;
  final int available;
  final int awayOnLeave;
  final List<HostelLeaveRequest> pendingLeaves;
  final List<HostelVisitor> visitorsIn;

  factory HostelDay.fromJson(Map<String, dynamic> j) => HostelDay(
        capacity: (j['total_capacity'] as num?)?.toInt() ?? 0,
        occupied: (j['occupied'] as num?)?.toInt() ?? 0,
        available: (j['available_seats'] as num?)?.toInt() ?? 0,
        awayOnLeave: (j['away_on_leave'] as num?)?.toInt() ?? 0,
        pendingLeaves: _list(j['pending_leaves']).map(HostelLeaveRequest.fromJson).toList(),
        visitorsIn: _list(j['visitors_in']).map(HostelVisitor.fromJson).toList(),
      );
}

class HostelLeaveRequest {
  const HostelLeaveRequest({
    required this.id,
    required this.studentName,
    required this.classLabel,
    required this.fromDate,
    required this.toDate,
    required this.reason,
    required this.contactPhone,
  });

  final int id;
  final String studentName;
  final String classLabel;
  final String fromDate;
  final String toDate;
  final String reason;
  final String? contactPhone;

  factory HostelLeaveRequest.fromJson(Map<String, dynamic> j) => HostelLeaveRequest(
        id: (j['id'] as num).toInt(),
        studentName: (j['student_name'] as String?) ?? '',
        classLabel: (j['class_label'] as String?) ?? '',
        fromDate: (j['from_date'] as String?) ?? '',
        toDate: (j['to_date'] as String?) ?? '',
        reason: (j['reason'] as String?) ?? '',
        contactPhone: j['contact_phone'] as String?,
      );
}

class HostelVisitor {
  const HostelVisitor({
    required this.id,
    required this.visitorName,
    required this.relation,
    required this.studentName,
    required this.inAt,
  });

  final int id;
  final String visitorName;
  final String? relation;
  final String studentName;
  final DateTime? inAt;

  factory HostelVisitor.fromJson(Map<String, dynamic> j) => HostelVisitor(
        id: (j['id'] as num).toInt(),
        visitorName: (j['visitor_name'] as String?) ?? '',
        relation: j['relation'] as String?,
        studentName: (j['student_name'] as String?) ?? '',
        inAt: j['in_at'] == null ? null : parseServerTime(j['in_at'] as String),
      );
}
