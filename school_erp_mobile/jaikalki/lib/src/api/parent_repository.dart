import 'dart:io' show Platform;

import 'package:dio/dio.dart';

import 'api_client.dart';

/// Pydantic v2 serialises Decimal columns as JSON *strings* (e.g.
/// `"10.00"`) to preserve precision. Dart's `as num?` cast fails on
/// strings, so every field that maps to a backend Decimal goes through
/// this helper. Accepts num, string, or null; returns null on bad data.
double? _toDouble(dynamic v) {
  if (v == null) return null;
  if (v is num) return v.toDouble();
  if (v is String) return double.tryParse(v);
  return null;
}

double _toDoubleOrZero(dynamic v) => _toDouble(v) ?? 0.0;

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
    required this.todayAttendance,
    required this.feeDueAmount,
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
  final String? todayAttendance;
  final double feeDueAmount;

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
        todayAttendance: j['today_attendance'] as String?,
        feeDueAmount: _toDoubleOrZero(j['fee_due_amount']),
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

  Future<List<AttendanceRow>> attendance(int studentId, {int limit = 30}) async {
    try {
      final res = await _api.dio.get<List<dynamic>>(
        '/v1/parent/children/$studentId/attendance',
        queryParameters: {'limit': limit},
      );
      return (res.data ?? const [])
          .map((e) => AttendanceRow.fromJson(e as Map<String, dynamic>))
          .toList();
    } on DioException {
      return const [];
    }
  }

  Future<SubjectAttendanceReport> attendanceBySubject(
    int studentId, {
    int windowDays = 90,
  }) async {
    try {
      final res = await _api.dio.get<Map<String, dynamic>>(
        '/v1/parent/children/$studentId/attendance/by-subject',
        queryParameters: {'window_days': windowDays},
      );
      return SubjectAttendanceReport.fromJson(res.data ?? const {});
    } on DioException {
      return const SubjectAttendanceReport(rows: [], windowDays: 0, note: null);
    }
  }

  Future<ClassAverage?> attendanceClassAverage(
    int studentId, {
    int windowDays = 30,
  }) async {
    try {
      final res = await _api.dio.get<Map<String, dynamic>>(
        '/v1/parent/children/$studentId/attendance/class-average',
        queryParameters: {'window_days': windowDays},
      );
      return ClassAverage.fromJson(res.data ?? const {});
    } on DioException {
      return null;
    }
  }

  Future<TimetableView?> timetable(int studentId) async {
    try {
      final res = await _api.dio.get<Map<String, dynamic>>(
        '/v1/parent/children/$studentId/timetable',
      );
      return TimetableView.fromJson(res.data ?? const {});
    } on DioException {
      return null;
    }
  }

  // ----- Phase 11: Fees -----------------------------------------------------

  Future<ChildFeeView> fees(int studentId) async {
    final res = await _api.dio.get<Map<String, dynamic>>(
      '/v1/parent/children/$studentId/fees',
    );
    return ChildFeeView.fromJson(res.data ?? const {});
  }

  Future<Map<String, dynamic>> initiatePayment({
    required int invoiceId,
    required int studentId,
  }) async {
    final res = await _api.dio.post<Map<String, dynamic>>(
      '/v1/parent/payments/initiate',
      data: {'invoice_id': invoiceId, 'student_id': studentId},
    );
    return res.data ?? const {};
  }

  // ----- Phase 14: Homework -----------------------------------------------

  Future<List<HomeworkItem>> homework(int studentId) async {
    try {
      final res = await _api.dio.get<List<dynamic>>(
        '/v1/parent/children/$studentId/homework',
      );
      return (res.data ?? const [])
          .map((e) => HomeworkItem.fromJson(e as Map<String, dynamic>))
          .toList();
    } on DioException {
      return const [];
    }
  }

  Future<void> submitHomework({
    required int homeworkId,
    required int studentId,
    required String content,
    List<String>? attachmentPaths,
  }) async {
    // Backend route is POST /v1/parent/children/{student_id}/homework/submit
    // with body { homework_id, content?, attachments[] } — student_id lives
    // in the path, not the body.
    await _api.dio.post<dynamic>(
      '/v1/parent/children/$studentId/homework/submit',
      data: {
        'homework_id': homeworkId,
        'content': content,
        if (attachmentPaths != null && attachmentPaths.isNotEmpty)
          'attachments': attachmentPaths,
      },
    );
  }

  /// Uploads a single local file via /v1/uploads and returns the server-
  /// side relative path (tenant_X/homework/submissions/<filename>). The
  /// upload endpoint is gated by require_tenant only — parents have a
  /// resolved TenantContext on every request via their bearer token, so
  /// they can call this without a school-admin role.
  Future<String> uploadFile({
    required String localPath,
    String category = 'homework',
    String subcategory = 'submissions',
  }) async {
    final filename = localPath.split(Platform.pathSeparator).last;
    final form = FormData.fromMap({
      'category': category,
      'subcategory': subcategory,
      'file': await MultipartFile.fromFile(localPath, filename: filename),
    });
    final res = await _api.dio.post<Map<String, dynamic>>(
      '/v1/uploads',
      data: form,
      options: Options(contentType: 'multipart/form-data'),
    );
    return (res.data?['path'] as String?) ?? '';
  }

  /// Downloads the per-invoice PDF receipt/invoice into [savePath] and
  /// returns that path. Caller is responsible for picking a temp/cache
  /// location (typically getTemporaryDirectory + invoice_number.pdf).
  Future<String> downloadInvoicePdf({
    required int studentId,
    required int invoiceId,
    required String savePath,
  }) async {
    await _api.dio.download(
      '/v1/parent/children/$studentId/fees/invoices/$invoiceId/pdf',
      savePath,
    );
    return savePath;
  }

  /// Lists every *published* report card for a child (one per exam/term).
  Future<List<ResultCardRow>> resultCards(int studentId) async {
    try {
      final res = await _api.dio.get<Map<String, dynamic>>(
        '/v1/parent/children/$studentId/report-cards',
      );
      final rows = (res.data?['rows'] as List<dynamic>?) ?? const [];
      return rows
          .map((e) => ResultCardRow.fromJson(e as Map<String, dynamic>))
          .toList();
    } on DioException {
      return const [];
    }
  }

  Future<String> downloadResultCard({
    required int cardId,
    required String savePath,
  }) async {
    await _api.dio.download(
      '/v1/parent/report-cards/$cardId/pdf',
      savePath,
    );
    return savePath;
  }

  Future<List<Holiday>> holidays({int daysBack = 7, int daysForward = 180}) async {
    try {
      final res = await _api.dio.get<List<dynamic>>(
        '/v1/parent/holidays',
        queryParameters: {'days_back': daysBack, 'days_forward': daysForward},
      );
      return (res.data ?? const [])
          .map((e) => Holiday.fromJson(e as Map<String, dynamic>))
          .toList();
    } on DioException {
      return const [];
    }
  }

  Future<List<SchoolEvent>> events({int daysBack = 7, int daysForward = 180}) async {
    try {
      final res = await _api.dio.get<List<dynamic>>(
        '/v1/parent/events',
        queryParameters: {'days_back': daysBack, 'days_forward': daysForward},
      );
      return (res.data ?? const [])
          .map((e) => SchoolEvent.fromJson(e as Map<String, dynamic>))
          .toList();
    } on DioException {
      return const [];
    }
  }

  Future<List<LibraryBookSummary>> libraryCatalog({String? q, String? category}) async {
    try {
      final res = await _api.dio.get<List<dynamic>>(
        '/v1/parent/library/catalog',
        queryParameters: {
          if (q != null && q.isNotEmpty) 'q': q,
          if (category != null && category.isNotEmpty) 'category': category,
        },
      );
      return (res.data ?? const [])
          .map((e) => LibraryBookSummary.fromJson(e as Map<String, dynamic>))
          .toList();
    } on DioException {
      return const [];
    }
  }

  Future<List<DirectoryEntry>> directory(int studentId) async {
    try {
      final res = await _api.dio.get<List<dynamic>>(
        '/v1/parent/children/$studentId/directory',
      );
      return (res.data ?? const [])
          .map((e) => DirectoryEntry.fromJson(e as Map<String, dynamic>))
          .toList();
    } on DioException {
      return const [];
    }
  }
}

class AttendanceRow {
  AttendanceRow({
    required this.date,
    required this.period,
    required this.status,
    required this.remarks,
    required this.markedByName,
    required this.markedAt,
  });

  final String date;
  final String period;
  final String status;
  final String? remarks;
  final String? markedByName;
  final String? markedAt;

  factory AttendanceRow.fromJson(Map<String, dynamic> j) => AttendanceRow(
        date: j['date'] as String,
        period: j['period'] as String,
        status: j['status'] as String,
        remarks: j['remarks'] as String?,
        markedByName: j['marked_by_name'] as String?,
        markedAt: j['marked_at'] as String?,
      );
}

class SubjectAttendanceRow {
  const SubjectAttendanceRow({
    required this.subjectId,
    required this.subjectName,
    required this.present,
    required this.late,
    required this.halfDay,
    required this.absent,
    required this.total,
    required this.percentage,
  });

  final int subjectId;
  final String subjectName;
  final int present;
  final int late;
  final int halfDay;
  final int absent;
  final int total;
  final double percentage;

  factory SubjectAttendanceRow.fromJson(Map<String, dynamic> j) =>
      SubjectAttendanceRow(
        subjectId: (j['subject_id'] as num).toInt(),
        subjectName: j['subject_name'] as String? ?? '',
        present: (j['present'] as num?)?.toInt() ?? 0,
        late: (j['late'] as num?)?.toInt() ?? 0,
        halfDay: (j['half_day'] as num?)?.toInt() ?? 0,
        absent: (j['absent'] as num?)?.toInt() ?? 0,
        total: (j['total'] as num?)?.toInt() ?? 0,
        percentage: _toDoubleOrZero(j['percentage']),
      );
}

class SubjectAttendanceReport {
  const SubjectAttendanceReport({
    required this.rows,
    required this.windowDays,
    required this.note,
  });

  final List<SubjectAttendanceRow> rows;
  final int windowDays;
  final String? note;

  bool get isEmpty => rows.isEmpty;

  factory SubjectAttendanceReport.fromJson(Map<String, dynamic> j) =>
      SubjectAttendanceReport(
        rows: ((j['rows'] as List<dynamic>?) ?? const [])
            .map((e) => SubjectAttendanceRow.fromJson(e as Map<String, dynamic>))
            .toList(),
        windowDays: (j['window_days'] as num?)?.toInt() ?? 0,
        note: j['note'] as String?,
      );
}

class ClassAverage {
  const ClassAverage({
    required this.childPct,
    required this.classPct,
    required this.classSize,
    required this.windowDays,
    required this.childAttendanceDays,
  });

  final double childPct;
  final double classPct;
  final int classSize;
  final int windowDays;
  final int childAttendanceDays;

  double get gap => childPct - classPct;
  bool get isAboveAverage => gap >= 0;
  bool get isMeaningful => childAttendanceDays > 0 && classSize > 1;

  factory ClassAverage.fromJson(Map<String, dynamic> j) => ClassAverage(
        childPct: _toDoubleOrZero(j['child_pct']),
        classPct: _toDoubleOrZero(j['class_pct']),
        classSize: (j['class_size'] as num?)?.toInt() ?? 0,
        windowDays: (j['window_days'] as num?)?.toInt() ?? 0,
        childAttendanceDays: (j['child_attendance_days'] as num?)?.toInt() ?? 0,
      );
}

class TimetableCell {
  const TimetableCell({
    required this.dayOfWeek,
    required this.periodNumber,
    required this.subjectName,
    required this.teacherName,
    required this.room,
    required this.startTime,
    required this.endTime,
  });

  final int dayOfWeek; // 0=Mon..6=Sun
  final int periodNumber;
  final String? subjectName;
  final String? teacherName;
  final String? room;
  final String? startTime; // "08:00:00"
  final String? endTime;

  factory TimetableCell.fromJson(Map<String, dynamic> j) => TimetableCell(
        dayOfWeek: (j['day_of_week'] as num).toInt(),
        periodNumber: (j['period_number'] as num).toInt(),
        subjectName: j['subject_name'] as String?,
        teacherName: j['teacher_name'] as String?,
        room: j['room'] as String?,
        startTime: j['start_time'] as String?,
        endTime: j['end_time'] as String?,
      );
}

class TimetableView {
  const TimetableView({
    required this.sectionId,
    required this.sectionName,
    required this.className,
    required this.cells,
    required this.note,
  });

  final int? sectionId;
  final String? sectionName;
  final String? className;
  final List<TimetableCell> cells;
  final String? note;

  bool get hasData => cells.isNotEmpty;

  /// Cells for one weekday, sorted by period_number.
  List<TimetableCell> dayCells(int weekday) {
    final out = cells.where((c) => c.dayOfWeek == weekday).toList()
      ..sort((a, b) => a.periodNumber.compareTo(b.periodNumber));
    return out;
  }

  factory TimetableView.fromJson(Map<String, dynamic> j) => TimetableView(
        sectionId: (j['section_id'] as num?)?.toInt(),
        sectionName: j['section_name'] as String?,
        className: j['class_name'] as String?,
        cells: ((j['cells'] as List<dynamic>?) ?? const [])
            .map((e) => TimetableCell.fromJson(e as Map<String, dynamic>))
            .toList(),
        note: j['note'] as String?,
      );
}

// ---- Phase 11 models ------------------------------------------------------

class FeeInvoice {
  FeeInvoice({
    required this.id,
    required this.invoiceNumber,
    required this.categoryName,
    required this.periodStart,
    required this.periodEnd,
    required this.dueDate,
    required this.totalAmount,
    required this.paidAmount,
    required this.status,
  });

  final int id;
  final String invoiceNumber;
  final String? categoryName;
  final String periodStart;
  final String periodEnd;
  final String dueDate;
  final double totalAmount;
  final double paidAmount;
  final String status; // pending / partial / paid / overdue / cancelled

  double get balance => totalAmount - paidAmount;
  bool get isPaid => status == 'paid';

  factory FeeInvoice.fromJson(Map<String, dynamic> j) => FeeInvoice(
        id: (j['id'] as num).toInt(),
        invoiceNumber: (j['invoice_number'] as String?) ?? '',
        categoryName: j['category_name'] as String?,
        periodStart: (j['period_start'] as String?) ?? '',
        periodEnd: (j['period_end'] as String?) ?? '',
        dueDate: (j['due_date'] as String?) ?? '',
        totalAmount: _toDoubleOrZero(j['total_amount']),
        paidAmount: _toDoubleOrZero(j['paid_amount']),
        status: (j['status'] as String?) ?? 'pending',
      );
}

class ChildFeeView {
  ChildFeeView({
    required this.totalDue,
    required this.totalPaid,
    required this.overdueCount,
    required this.invoices,
  });

  final double totalDue;
  final double totalPaid;
  final int overdueCount;
  final List<FeeInvoice> invoices;

  factory ChildFeeView.fromJson(Map<String, dynamic> j) => ChildFeeView(
        totalDue: _toDoubleOrZero(j['total_due']),
        totalPaid: _toDoubleOrZero(j['total_paid']),
        overdueCount: (j['overdue_count'] as num?)?.toInt() ?? 0,
        invoices: ((j['invoices'] as List<dynamic>?) ?? const [])
            .map((e) => FeeInvoice.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
}

// ---- Phase 16 models (report cards / per-semester results) -----------------

class ResultCardRow {
  const ResultCardRow({
    required this.reportCardId,
    required this.examId,
    required this.examName,
    required this.status,
    required this.percentage,
    required this.overallGrade,
    required this.rankInSection,
    required this.publishedAt,
  });

  final int reportCardId;
  final int examId;
  final String examName;
  /// Backend enum: draft / generated / published. Only "published" cards
  /// are returned from the parent list endpoint, but we keep the field so
  /// future statuses (eg. revised) show up explicitly.
  final String status;
  final double? percentage;
  final String? overallGrade;
  final int? rankInSection;
  final String? publishedAt;

  factory ResultCardRow.fromJson(Map<String, dynamic> j) => ResultCardRow(
        reportCardId: (j['report_card_id'] as num).toInt(),
        examId: (j['exam_id'] as num).toInt(),
        examName: (j['exam_name'] as String?) ?? '',
        status: (j['status'] as String?) ?? 'published',
        percentage: _toDouble(j['percentage']),
        overallGrade: j['overall_grade'] as String?,
        rankInSection: (j['rank_in_section'] as num?)?.toInt(),
        publishedAt: j['published_at'] as String?,
      );
}

// ---- Phase 14 models ------------------------------------------------------

class HomeworkItem {
  HomeworkItem({
    required this.id,
    required this.title,
    required this.description,
    required this.subjectName,
    required this.assignedOn,
    required this.dueDate,
    required this.maxMarks,
    required this.teacherAttachments,
    required this.submissionStatus,
    required this.submittedAt,
    required this.marksObtained,
    required this.feedback,
  });

  final int id;
  final String title;
  final String? description;
  final String? subjectName;
  final String assignedOn;
  final String dueDate;
  final double? maxMarks;
  /// Files attached by the teacher when posting the homework (worksheet
  /// PDFs, reference notes). Server-side relative paths under
  /// uploads/tenant_X/...
  final List<String> teacherAttachments;
  final String submissionStatus; // open / submitted / late / missing / graded
  final String? submittedAt;
  final double? marksObtained;
  final String? feedback;

  bool get isOpen => submissionStatus == 'open';
  bool get isSubmitted =>
      submissionStatus == 'submitted' || submissionStatus == 'late';
  bool get isGraded => submissionStatus == 'graded';

  factory HomeworkItem.fromJson(Map<String, dynamic> j) => HomeworkItem(
        id: ((j['homework_id'] ?? j['id']) as num).toInt(),
        title: (j['title'] as String?) ?? '',
        description: j['description'] as String?,
        subjectName: j['subject_name'] as String?,
        assignedOn: (j['assigned_on'] as String?) ?? '',
        dueDate: (j['due_date'] as String?) ?? '',
        maxMarks: _toDouble(j['max_marks']),
        teacherAttachments: ((j['teacher_attachments'] as List<dynamic>?) ?? const [])
            .map((e) => e.toString())
            .toList(),
        // Backend uses "open" implicitly when null + not overdue, else "missing".
        submissionStatus: (j['submission_status'] as String?) ??
            ((j['submitted'] as bool?) == true ? 'submitted' : 'open'),
        submittedAt: j['submitted_at'] as String?,
        // Backend field is `marks` (not `marks_obtained`).
        marksObtained: _toDouble(j['marks']),
        feedback: j['feedback'] as String?,
      );
}

// ---- Calendar feeds: holidays + events ------------------------------------

class Holiday {
  const Holiday({
    required this.id,
    required this.date,
    required this.name,
    required this.kind,
    required this.description,
  });

  final int id;
  final String date;
  final String name;
  /// public / school / optional / vacation
  final String kind;
  final String? description;

  factory Holiday.fromJson(Map<String, dynamic> j) => Holiday(
        id: (j['id'] as num).toInt(),
        date: (j['date'] as String?) ?? '',
        name: (j['name'] as String?) ?? '',
        kind: (j['kind'] as String?) ?? 'public',
        description: j['description'] as String?,
      );
}

class SchoolEvent {
  const SchoolEvent({
    required this.id,
    required this.title,
    required this.description,
    required this.kind,
    required this.startsAt,
    required this.endsAt,
    required this.isAllDay,
    required this.audience,
  });

  final int id;
  final String title;
  final String? description;
  /// general / exam / sports / cultural / parent_teacher / holiday
  final String kind;
  final String startsAt;
  final String? endsAt;
  final bool isAllDay;
  final String audience;

  factory SchoolEvent.fromJson(Map<String, dynamic> j) => SchoolEvent(
        id: (j['id'] as num).toInt(),
        title: (j['title'] as String?) ?? '',
        description: j['description'] as String?,
        kind: (j['kind'] as String?) ?? 'general',
        startsAt: (j['starts_at'] as String?) ?? '',
        endsAt: j['ends_at'] as String?,
        isAllDay: (j['is_all_day'] as bool?) ?? true,
        audience: (j['audience'] as String?) ?? 'all',
      );
}

// ---- Library catalog + contact directory ----------------------------------

class LibraryBookSummary {
  const LibraryBookSummary({
    required this.id,
    required this.title,
    required this.author,
    required this.category,
    required this.language,
    required this.totalCopies,
    required this.availableCopies,
  });

  final int id;
  final String title;
  final String? author;
  final String? category;
  final String? language;
  final int totalCopies;
  final int availableCopies;

  bool get hasStock => availableCopies > 0;

  factory LibraryBookSummary.fromJson(Map<String, dynamic> j) => LibraryBookSummary(
        id: (j['id'] as num).toInt(),
        title: (j['title'] as String?) ?? '',
        author: j['author'] as String?,
        category: j['category'] as String?,
        language: j['language'] as String?,
        totalCopies: (j['total_copies'] as num?)?.toInt() ?? 0,
        availableCopies: (j['available_copies'] as num?)?.toInt() ?? 0,
      );
}

class DirectoryEntry {
  const DirectoryEntry({
    required this.teacherId,
    required this.fullName,
    required this.designation,
    required this.photoUrl,
    required this.subjectName,
    required this.isClassTeacher,
  });

  final int teacherId;
  final String fullName;
  final String? designation;
  final String? photoUrl;
  final String? subjectName;
  final bool isClassTeacher;

  factory DirectoryEntry.fromJson(Map<String, dynamic> j) => DirectoryEntry(
        teacherId: (j['teacher_id'] as num).toInt(),
        fullName: (j['full_name'] as String?) ?? '',
        designation: j['designation'] as String?,
        photoUrl: j['photo_url'] as String?,
        subjectName: j['subject_name'] as String?,
        isClassTeacher: (j['is_class_teacher'] as bool?) ?? false,
      );
}
