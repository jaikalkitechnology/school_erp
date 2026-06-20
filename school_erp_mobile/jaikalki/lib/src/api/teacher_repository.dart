import 'package:dio/dio.dart';

import 'api_client.dart';

/// Repository for the teacher-app surface (/v1/teacher/*).
class TeacherRepository {
  TeacherRepository(this._api);
  final ApiClient _api;

  Future<TeacherMe> me() async {
    final res = await _api.dio.get<Map<String, dynamic>>('/v1/teacher/me');
    return TeacherMe.fromJson(res.data ?? const {});
  }

  // ---- Chat / messages ---------------------------------------------------

  Future<List<ChatContact>> chatContacts() async {
    try {
      final res = await _api.dio.get<List<dynamic>>(
        '/v1/teacher/messages/contacts',
      );
      return (res.data ?? const [])
          .map((e) => ChatContact.fromJson(e as Map<String, dynamic>))
          .toList();
    } on DioException {
      return const [];
    }
  }

  Future<List<ChatMessage>> inbox() async {
    try {
      final res = await _api.dio.get<List<dynamic>>(
        '/v1/teacher/messages/inbox',
      );
      return (res.data ?? const [])
          .map((e) => ChatMessage.fromJson(e as Map<String, dynamic>))
          .toList();
    } on DioException {
      return const [];
    }
  }

  Future<List<ChatMessage>> sent() async {
    try {
      final res = await _api.dio.get<List<dynamic>>(
        '/v1/teacher/messages/sent',
      );
      return (res.data ?? const [])
          .map((e) => ChatMessage.fromJson(e as Map<String, dynamic>))
          .toList();
    } on DioException {
      return const [];
    }
  }

  Future<ChatMessage> sendMessage({
    required int recipientUserId,
    required String body,
    String? subject,
  }) async {
    final res = await _api.dio.post<Map<String, dynamic>>(
      '/v1/teacher/messages/send',
      data: {
        'recipient_user_id': recipientUserId,
        'body': body,
        if (subject != null && subject.isNotEmpty) 'subject': subject,
      },
    );
    return ChatMessage.fromJson(res.data ?? const {});
  }

  Future<void> markMessageRead(int messageId) async {
    await _api.dio.post('/v1/teacher/messages/$messageId/read');
  }

  // ---- Student marks (Phase X tab on drill-down) -------------------------

  Future<List<StudentExamRow>> studentMarks(int studentId) async {
    try {
      final res = await _api.dio.get<Map<String, dynamic>>(
        '/v1/teacher/students/$studentId/marks',
      );
      return ((res.data?['exams'] as List<dynamic>?) ?? const [])
          .map((e) => StudentExamRow.fromJson(e as Map<String, dynamic>))
          .toList();
    } on DioException {
      return const [];
    }
  }

  /// Today's own-attendance row for the logged-in teacher (or null
  /// status when nothing's marked yet). Powers the "Mark me present"
  /// pill on the Today screen.
  Future<MyAttendance> myAttendanceToday() async {
    final res = await _api.dio.get<Map<String, dynamic>>(
      '/v1/teacher/me/attendance/today',
    );
    return MyAttendance.fromJson(res.data ?? const {});
  }

  Future<MyAttendance> markMyAttendance({String status = 'present'}) async {
    final res = await _api.dio.post<Map<String, dynamic>>(
      '/v1/teacher/me/attendance/mark',
      data: {'status': status},
    );
    return MyAttendance.fromJson(res.data ?? const {});
  }

  Future<TeacherToday> today() async {
    final res = await _api.dio.get<Map<String, dynamic>>('/v1/teacher/today');
    return TeacherToday.fromJson(res.data ?? const {});
  }

  Future<List<RosterStudent>> roster(int sectionId) async {
    try {
      final res = await _api.dio.get<List<dynamic>>(
        '/v1/teacher/sections/$sectionId/roster',
      );
      return (res.data ?? const [])
          .map((e) => RosterStudent.fromJson(e as Map<String, dynamic>))
          .toList();
    } on DioException {
      return const [];
    }
  }

  Future<SectionRoll> attendanceFor(
    int sectionId, {
    String? date,
    String period = 'day',
  }) async {
    final res = await _api.dio.get<Map<String, dynamic>>(
      '/v1/teacher/sections/$sectionId/attendance',
      queryParameters: {
        if (date != null) 'date': date,
        'period': period,
      },
    );
    return SectionRoll.fromJson(res.data ?? const {});
  }

  Future<SectionRoll> markAttendance({
    required int sectionId,
    required String date,
    required List<MarkEntry> entries,
    String period = 'day',
  }) async {
    final res = await _api.dio.post<Map<String, dynamic>>(
      '/v1/teacher/sections/$sectionId/attendance',
      data: {
        'section_id': sectionId,
        'date': date,
        'period': period,
        'entries': entries.map((e) => e.toJson()).toList(),
        'default_status': 'present',
      },
    );
    return SectionRoll.fromJson(res.data ?? const {});
  }

  Future<TeacherWeekTimetable> timetable() async {
    final res = await _api.dio.get<Map<String, dynamic>>(
      '/v1/teacher/timetable',
    );
    return TeacherWeekTimetable.fromJson(res.data ?? const {});
  }

  Future<String> downloadIdCard(String savePath) async {
    await _api.dio.download('/v1/teacher/me/id-card.pdf', savePath);
    return savePath;
  }

  // ---- Homework -----------------------------------------------------------

  Future<List<TeacherHomework>> myHomework() async {
    try {
      final res = await _api.dio.get<List<dynamic>>('/v1/teacher/homework');
      return (res.data ?? const [])
          .map((e) => TeacherHomework.fromJson(e as Map<String, dynamic>))
          .toList();
    } on DioException {
      return const [];
    }
  }

  Future<List<HomeworkSubmissionRow>> submissionsFor(int homeworkId) async {
    try {
      final res = await _api.dio.get<List<dynamic>>(
        '/v1/teacher/homework/$homeworkId/submissions',
      );
      return (res.data ?? const [])
          .map((e) => HomeworkSubmissionRow.fromJson(e as Map<String, dynamic>))
          .toList();
    } on DioException {
      return const [];
    }
  }

  Future<HomeworkStatusReport> homeworkReport(int homeworkId) async {
    final res = await _api.dio.get<Map<String, dynamic>>(
      '/v1/teacher/homework/$homeworkId/report',
    );
    return HomeworkStatusReport.fromJson(res.data ?? const {});
  }

  Future<HomeworkSubmissionRow> gradeSubmission({
    required int submissionId,
    required double marks,
    String? feedback,
  }) async {
    final res = await _api.dio.post<Map<String, dynamic>>(
      '/v1/teacher/homework/submissions/$submissionId/grade',
      data: {
        'marks': marks,
        if (feedback != null && feedback.isNotEmpty) 'feedback': feedback,
      },
    );
    return HomeworkSubmissionRow.fromJson(res.data ?? const {});
  }

  // ---- Leaves -------------------------------------------------------------

  Future<List<LeaveRowForTeacher>> pendingLeaves({bool onlyPending = true}) async {
    try {
      final res = await _api.dio.get<List<dynamic>>(
        '/v1/teacher/leaves',
        queryParameters: {'only_pending': onlyPending},
      );
      return (res.data ?? const [])
          .map((e) => LeaveRowForTeacher.fromJson(e as Map<String, dynamic>))
          .toList();
    } on DioException {
      return const [];
    }
  }

  Future<LeaveRowForTeacher> decideLeave({
    required int leaveId,
    required String status, // approved / rejected
    String? note,
  }) async {
    final res = await _api.dio.post<Map<String, dynamic>>(
      '/v1/teacher/leaves/$leaveId/decide',
      data: {
        'status': status,
        if (note != null && note.isNotEmpty) 'decision_note': note,
      },
    );
    return LeaveRowForTeacher.fromJson(res.data ?? const {});
  }

  // ---- Student drill-down ------------------------------------------------

  Future<StudentDrill> studentDrill(int studentId) async {
    final res = await _api.dio.get<Map<String, dynamic>>(
      '/v1/teacher/students/$studentId',
    );
    return StudentDrill.fromJson(res.data ?? const {});
  }

  // ---- Behaviour notes ---------------------------------------------------

  Future<BehaviourNote> addBehaviourNote({
    required int studentId,
    required String headline,
    String kind = 'neutral',
    String? detail,
    String? occurredOn,
    bool visibleToParent = true,
  }) async {
    final res = await _api.dio.post<Map<String, dynamic>>(
      '/v1/teacher/behaviour-notes',
      data: {
        'student_id': studentId,
        'kind': kind,
        'headline': headline,
        if (detail != null && detail.isNotEmpty) 'detail': detail,
        if (occurredOn != null) 'occurred_on': occurredOn,
        'visible_to_parent': visibleToParent,
      },
    );
    return BehaviourNote.fromJson(res.data ?? const {});
  }

  // ---- My own staff leave ----------------------------------------------

  Future<List<StaffLeaveRow>> myLeaves() async {
    try {
      final res = await _api.dio.get<List<dynamic>>('/v1/teacher/my-leaves');
      return (res.data ?? const [])
          .map((e) => StaffLeaveRow.fromJson(e as Map<String, dynamic>))
          .toList();
    } on DioException {
      return const [];
    }
  }

  Future<StaffLeaveRow> applyMyLeave({
    required String startDate,
    required String endDate,
    required String reason,
    String kind = 'casual',
  }) async {
    final res = await _api.dio.post<Map<String, dynamic>>(
      '/v1/teacher/my-leaves',
      data: {
        'start_date': startDate,
        'end_date': endDate,
        'reason': reason,
        'kind': kind,
      },
    );
    return StaffLeaveRow.fromJson(res.data ?? const {});
  }

  Future<List<StaffLeaveRow>> pendingStaffLeaves() async {
    try {
      final res = await _api.dio.get<List<dynamic>>(
        '/v1/teacher/staff-leaves/pending',
      );
      return (res.data ?? const [])
          .map((e) => StaffLeaveRow.fromJson(e as Map<String, dynamic>))
          .toList();
    } on DioException {
      return const [];
    }
  }

  Future<StaffLeaveRow> decideStaffLeave({
    required int leaveId,
    required String status,
    String? remarks,
  }) async {
    final res = await _api.dio.post<Map<String, dynamic>>(
      '/v1/teacher/staff-leaves/$leaveId/decide',
      data: {
        'status': status,
        if (remarks != null && remarks.isNotEmpty) 'decision_remarks': remarks,
      },
    );
    return StaffLeaveRow.fromJson(res.data ?? const {});
  }

  // ---- Holidays + events -----------------------------------------------

  Future<List<Holiday>> holidays() async {
    try {
      final res = await _api.dio.get<List<dynamic>>('/v1/teacher/holidays');
      return (res.data ?? const [])
          .map((e) => Holiday.fromJson(e as Map<String, dynamic>))
          .toList();
    } on DioException {
      return const [];
    }
  }

  Future<List<SchoolEvent>> events() async {
    try {
      final res = await _api.dio.get<List<dynamic>>('/v1/teacher/events');
      return (res.data ?? const [])
          .map((e) => SchoolEvent.fromJson(e as Map<String, dynamic>))
          .toList();
    } on DioException {
      return const [];
    }
  }

  Future<List<ExamCalendarRow>> exams() async {
    try {
      final res = await _api.dio.get<List<dynamic>>('/v1/teacher/exams');
      return (res.data ?? const [])
          .map((e) => ExamCalendarRow.fromJson(e as Map<String, dynamic>))
          .toList();
    } on DioException {
      return const [];
    }
  }

  // ---- Create homework -------------------------------------------------

  Future<String> uploadFile({
    required String localPath,
    String category = 'homework',
    String subcategory = 'assignments',
  }) async {
    final filename = localPath.split('/').last;
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

  Future<TeacherHomework> createHomework({
    required int sectionId,
    int? subjectId,
    required String title,
    String? description,
    required String dueDate,
    required double maxMarks,
    List<String>? attachments,
  }) async {
    final res = await _api.dio.post<Map<String, dynamic>>(
      '/v1/teacher/homework',
      data: {
        'section_id': sectionId,
        if (subjectId != null) 'subject_id': subjectId,
        'title': title,
        if (description != null && description.isNotEmpty)
          'description': description,
        'due_date': dueDate,
        'max_marks': maxMarks,
        if (attachments != null && attachments.isNotEmpty)
          'attachments': attachments,
      },
    );
    return TeacherHomework.fromJson(res.data ?? const {});
  }
}

// ---- Models --------------------------------------------------------------

class TeacherProfile {
  const TeacherProfile({
    required this.userId,
    required this.teacherId,
    required this.employeeNo,
    required this.fullName,
    required this.photoUrl,
    required this.designation,
    required this.phone,
    required this.email,
    required this.isClassTeacher,
    required this.qualifications,
    required this.experienceYears,
    required this.schoolName,
    required this.schoolAddress,
    required this.schoolPhone,
    required this.schoolLogoUrl,
  });

  final int userId;
  final int teacherId;
  final String employeeNo;
  final String fullName;
  final String? photoUrl;
  final String? designation;
  final String? phone;
  final String? email;
  final bool isClassTeacher;
  final List<String> qualifications;
  final int experienceYears;
  final String? schoolName;
  final String? schoolAddress;
  final String? schoolPhone;
  final String? schoolLogoUrl;

  factory TeacherProfile.fromJson(Map<String, dynamic> j) => TeacherProfile(
        userId: (j['user_id'] as num?)?.toInt() ?? 0,
        teacherId: (j['teacher_id'] as num?)?.toInt() ?? 0,
        employeeNo: (j['employee_no'] as String?) ?? '',
        fullName: (j['full_name'] as String?) ?? '',
        photoUrl: j['photo_url'] as String?,
        designation: j['designation'] as String?,
        phone: j['phone'] as String?,
        email: j['email'] as String?,
        isClassTeacher: (j['is_class_teacher'] as bool?) ?? false,
        qualifications: ((j['qualifications'] as List<dynamic>?) ?? const [])
            .map((e) => e.toString())
            .toList(),
        experienceYears: (j['experience_years'] as num?)?.toInt() ?? 0,
        schoolName: j['school_name'] as String?,
        schoolAddress: j['school_address'] as String?,
        schoolPhone: j['school_phone'] as String?,
        schoolLogoUrl: j['school_logo_url'] as String?,
      );
}

class SectionAccess {
  const SectionAccess({
    required this.sectionId,
    required this.sectionName,
    required this.classLabel,
    required this.isClassTeacher,
    required this.subjects,
    required this.studentCount,
  });

  final int sectionId;
  final String sectionName;
  final String? classLabel;
  final bool isClassTeacher;
  final List<String> subjects;
  final int studentCount;

  String get displayLabel =>
      '${classLabel ?? ''} ${sectionName}'.trim();

  factory SectionAccess.fromJson(Map<String, dynamic> j) => SectionAccess(
        sectionId: (j['section_id'] as num).toInt(),
        sectionName: (j['section_name'] as String?) ?? '',
        classLabel: j['class_label'] as String?,
        isClassTeacher: (j['is_class_teacher'] as bool?) ?? false,
        subjects: ((j['subjects'] as List<dynamic>?) ?? const [])
            .map((e) => e.toString())
            .toList(),
        studentCount: (j['student_count'] as num?)?.toInt() ?? 0,
      );
}

class TeacherMe {
  const TeacherMe({required this.profile, required this.sections});
  final TeacherProfile profile;
  final List<SectionAccess> sections;

  factory TeacherMe.fromJson(Map<String, dynamic> j) => TeacherMe(
        profile: TeacherProfile.fromJson(
            (j['profile'] as Map<String, dynamic>?) ?? const {}),
        sections: ((j['sections'] as List<dynamic>?) ?? const [])
            .map((e) => SectionAccess.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
}

class TodayPeriod {
  const TodayPeriod({
    required this.periodNumber,
    required this.sectionId,
    required this.sectionLabel,
    required this.subjectId,
    required this.subjectName,
    required this.room,
  });

  final int periodNumber;
  final int sectionId;
  final String sectionLabel;
  final int? subjectId;
  final String? subjectName;
  final String? room;

  factory TodayPeriod.fromJson(Map<String, dynamic> j) => TodayPeriod(
        periodNumber: (j['period_number'] as num).toInt(),
        sectionId: (j['section_id'] as num).toInt(),
        sectionLabel: (j['section_label'] as String?) ?? '',
        subjectId: (j['subject_id'] as num?)?.toInt(),
        subjectName: j['subject_name'] as String?,
        room: j['room'] as String?,
      );
}

class TeacherToday {
  const TeacherToday({
    required this.date,
    required this.dayOfWeek,
    required this.periods,
    required this.pendingHomeworkCount,
    required this.pendingLeavesCount,
    required this.sectionsToMarkAttendance,
    required this.totalStudentsCount,
    required this.upcomingExamsCount,
    required this.myPendingLeavesCount,
  });

  final String date;
  final int dayOfWeek;
  final List<TodayPeriod> periods;
  final int pendingHomeworkCount;
  final int pendingLeavesCount;
  final int sectionsToMarkAttendance;
  final int totalStudentsCount;
  final int upcomingExamsCount;
  final int myPendingLeavesCount;

  factory TeacherToday.fromJson(Map<String, dynamic> j) => TeacherToday(
        date: (j['date'] as String?) ?? '',
        dayOfWeek: (j['day_of_week'] as num?)?.toInt() ?? 0,
        periods: ((j['periods'] as List<dynamic>?) ?? const [])
            .map((e) => TodayPeriod.fromJson(e as Map<String, dynamic>))
            .toList(),
        pendingHomeworkCount:
            (j['pending_homework_count'] as num?)?.toInt() ?? 0,
        pendingLeavesCount: (j['pending_leaves_count'] as num?)?.toInt() ?? 0,
        sectionsToMarkAttendance:
            (j['sections_to_mark_attendance'] as num?)?.toInt() ?? 0,
        totalStudentsCount:
            (j['total_students_count'] as num?)?.toInt() ?? 0,
        upcomingExamsCount:
            (j['upcoming_exams_count'] as num?)?.toInt() ?? 0,
        myPendingLeavesCount:
            (j['my_pending_leaves_count'] as num?)?.toInt() ?? 0,
      );
}

class RosterStudent {
  const RosterStudent({
    required this.studentId,
    required this.fullName,
    required this.admissionNumber,
    required this.rollNo,
    required this.photoUrl,
    required this.parentPhone,
    required this.gender,
  });

  final int studentId;
  final String fullName;
  final String admissionNumber;
  final String? rollNo;
  final String? photoUrl;
  final String? parentPhone;
  final String? gender;

  factory RosterStudent.fromJson(Map<String, dynamic> j) => RosterStudent(
        studentId: (j['student_id'] as num).toInt(),
        fullName: (j['full_name'] as String?) ?? '',
        admissionNumber: (j['admission_number'] as String?) ?? '',
        rollNo: j['roll_no'] as String?,
        photoUrl: j['photo_url'] as String?,
        parentPhone: j['parent_phone'] as String?,
        gender: j['gender'] as String?,
      );
}

class StudentRollEntry {
  const StudentRollEntry({
    required this.studentId,
    required this.fullName,
    required this.admissionNumber,
    required this.rollNo,
    required this.status,
    required this.remarks,
  });

  final int studentId;
  final String fullName;
  final String admissionNumber;
  final String? rollNo;
  final String status; // present / absent / late / half_day / on_leave
  final String? remarks;

  factory StudentRollEntry.fromJson(Map<String, dynamic> j) => StudentRollEntry(
        studentId: (j['student_id'] as num).toInt(),
        fullName: (j['full_name'] as String?) ?? '',
        admissionNumber: (j['admission_number'] as String?) ?? '',
        rollNo: j['roll_no'] as String?,
        status: (j['status'] as String?) ?? 'present',
        remarks: j['remarks'] as String?,
      );
}

class SectionRoll {
  const SectionRoll({
    required this.sectionId,
    required this.date,
    required this.period,
    required this.students,
    required this.counts,
  });

  final int sectionId;
  final String date;
  final String period;
  final List<StudentRollEntry> students;
  final Map<String, int> counts;

  factory SectionRoll.fromJson(Map<String, dynamic> j) => SectionRoll(
        sectionId: (j['section_id'] as num?)?.toInt() ?? 0,
        date: (j['date'] as String?) ?? '',
        period: (j['period'] as String?) ?? 'day',
        students: ((j['students'] as List<dynamic>?) ?? const [])
            .map((e) => StudentRollEntry.fromJson(e as Map<String, dynamic>))
            .toList(),
        counts: ((j['counts'] as Map<String, dynamic>?) ?? const {})
            .map((k, v) => MapEntry(k, (v as num).toInt())),
      );
}

class MarkEntry {
  const MarkEntry({required this.studentId, required this.status, this.remarks});
  final int studentId;
  final String status;
  final String? remarks;

  Map<String, dynamic> toJson() => {
        'student_id': studentId,
        'status': status,
        if (remarks != null && remarks!.isNotEmpty) 'remarks': remarks,
      };
}

// ---- Weekly timetable ----------------------------------------------------

class WeekPeriod {
  const WeekPeriod({
    required this.dayOfWeek,
    required this.periodNumber,
    required this.startsAt,
    required this.endsAt,
    required this.sectionId,
    required this.sectionLabel,
    required this.subjectId,
    required this.subjectName,
    required this.room,
    required this.isBreak,
  });

  final int dayOfWeek;
  final int periodNumber;
  final String? startsAt;
  final String? endsAt;
  final int? sectionId;
  final String? sectionLabel;
  final int? subjectId;
  final String? subjectName;
  final String? room;
  final bool isBreak;

  factory WeekPeriod.fromJson(Map<String, dynamic> j) => WeekPeriod(
        dayOfWeek: (j['day_of_week'] as num).toInt(),
        periodNumber: (j['period_number'] as num).toInt(),
        startsAt: j['starts_at'] as String?,
        endsAt: j['ends_at'] as String?,
        sectionId: (j['section_id'] as num?)?.toInt(),
        sectionLabel: j['section_label'] as String?,
        subjectId: (j['subject_id'] as num?)?.toInt(),
        subjectName: j['subject_name'] as String?,
        room: j['room'] as String?,
        isBreak: (j['is_break'] as bool?) ?? false,
      );
}

class TeacherWeekTimetable {
  const TeacherWeekTimetable({required this.days, required this.rows});
  final List<int> days;
  final List<WeekPeriod> rows;

  factory TeacherWeekTimetable.fromJson(Map<String, dynamic> j) =>
      TeacherWeekTimetable(
        days: ((j['days'] as List<dynamic>?) ?? const [])
            .map((e) => (e as num).toInt())
            .toList(),
        rows: ((j['rows'] as List<dynamic>?) ?? const [])
            .map((e) => WeekPeriod.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
}

// ---- Homework grading ----------------------------------------------------

double? _toDoubleOrNull(dynamic v) {
  if (v == null) return null;
  if (v is num) return v.toDouble();
  if (v is String) return double.tryParse(v);
  return null;
}

class TeacherHomework {
  const TeacherHomework({
    required this.id,
    required this.sectionId,
    required this.subjectId,
    required this.title,
    required this.description,
    required this.assignedOn,
    required this.dueDate,
    required this.maxMarks,
    required this.attachments,
  });

  final int id;
  final int sectionId;
  final int? subjectId;
  final String title;
  final String? description;
  final String assignedOn;
  final String dueDate;
  final double maxMarks;
  final List<String> attachments;

  factory TeacherHomework.fromJson(Map<String, dynamic> j) => TeacherHomework(
        id: (j['id'] as num).toInt(),
        sectionId: (j['section_id'] as num).toInt(),
        subjectId: (j['subject_id'] as num?)?.toInt(),
        title: (j['title'] as String?) ?? '',
        description: j['description'] as String?,
        assignedOn: (j['assigned_on'] as String?) ?? '',
        dueDate: (j['due_date'] as String?) ?? '',
        maxMarks: _toDoubleOrNull(j['max_marks']) ?? 0,
        attachments: ((j['attachments'] as List<dynamic>?) ?? const [])
            .map((e) => e.toString())
            .toList(),
      );
}

class HomeworkSubmissionRow {
  const HomeworkSubmissionRow({
    required this.id,
    required this.homeworkId,
    required this.studentId,
    required this.submittedAt,
    required this.content,
    required this.attachments,
    required this.status,
    required this.marks,
    required this.feedback,
  });

  final int id;
  final int homeworkId;
  final int studentId;
  final String? submittedAt;
  final String? content;
  final List<String> attachments;
  /// submitted / graded / late / missing
  final String status;
  final double? marks;
  final String? feedback;

  bool get isGraded => status == 'graded';

  factory HomeworkSubmissionRow.fromJson(Map<String, dynamic> j) =>
      HomeworkSubmissionRow(
        id: (j['id'] as num).toInt(),
        homeworkId: (j['homework_id'] as num).toInt(),
        studentId: (j['student_id'] as num).toInt(),
        submittedAt: j['submitted_at'] as String?,
        content: j['content'] as String?,
        attachments: ((j['attachments'] as List<dynamic>?) ?? const [])
            .map((e) => e.toString())
            .toList(),
        status: (j['status'] as String?) ?? 'submitted',
        marks: _toDoubleOrNull(j['marks']),
        feedback: j['feedback'] as String?,
      );
}

class HomeworkStatusReport {
  const HomeworkStatusReport({
    required this.homeworkId,
    required this.title,
    required this.dueDate,
    required this.maxMarks,
    required this.totalStudents,
    required this.submittedCount,
    required this.rows,
  });

  final int homeworkId;
  final String title;
  final String dueDate;
  final double maxMarks;
  final int totalStudents;
  final int submittedCount;
  final List<StudentStatusRow> rows;

  factory HomeworkStatusReport.fromJson(Map<String, dynamic> j) =>
      HomeworkStatusReport(
        homeworkId: (j['homework_id'] as num?)?.toInt() ?? 0,
        title: (j['title'] as String?) ?? '',
        dueDate: (j['due_date'] as String?) ?? '',
        maxMarks: _toDoubleOrNull(j['max_marks']) ?? 0,
        totalStudents: (j['total_students'] as num?)?.toInt() ?? 0,
        submittedCount: (j['submitted_count'] as num?)?.toInt() ?? 0,
        rows: ((j['rows'] as List<dynamic>?) ?? const [])
            .map((e) => StudentStatusRow.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
}

class StudentStatusRow {
  const StudentStatusRow({
    required this.studentId,
    required this.fullName,
    required this.admissionNumber,
    required this.submitted,
    required this.submittedAt,
    required this.status,
    required this.marks,
  });

  final int studentId;
  final String fullName;
  final String admissionNumber;
  final bool submitted;
  final String? submittedAt;
  final String? status;
  final double? marks;

  factory StudentStatusRow.fromJson(Map<String, dynamic> j) => StudentStatusRow(
        studentId: (j['student_id'] as num).toInt(),
        fullName: (j['full_name'] as String?) ?? '',
        admissionNumber: (j['admission_number'] as String?) ?? '',
        submitted: (j['submitted'] as bool?) ?? false,
        submittedAt: j['submitted_at'] as String?,
        status: j['status'] as String?,
        marks: _toDoubleOrNull(j['marks']),
      );
}

// ---- Leaves --------------------------------------------------------------

class LeaveRowForTeacher {
  const LeaveRowForTeacher({
    required this.id,
    required this.studentId,
    required this.startDate,
    required this.endDate,
    required this.reason,
    required this.status,
    required this.appliedByUserId,
    required this.createdAt,
    required this.studentName,
  });

  final int id;
  final int studentId;
  final String startDate;
  final String endDate;
  final String reason;
  /// pending / approved / rejected
  final String status;
  final int? appliedByUserId;
  final String createdAt;
  // Optional — backend may or may not populate, depending on schema.
  final String? studentName;

  bool get isPending => status == 'pending';

  factory LeaveRowForTeacher.fromJson(Map<String, dynamic> j) =>
      LeaveRowForTeacher(
        id: (j['id'] as num).toInt(),
        studentId: (j['student_id'] as num).toInt(),
        startDate: (j['start_date'] as String?) ?? '',
        endDate: (j['end_date'] as String?) ?? '',
        reason: (j['reason'] as String?) ?? '',
        status: (j['status'] as String?) ?? 'pending',
        appliedByUserId: (j['applied_by_user_id'] as num?)?.toInt(),
        createdAt: (j['created_at'] as String?) ?? '',
        studentName: j['student_name'] as String?,
      );
}

// ---- Student drill-down / behaviour notes --------------------------------

class BehaviourNote {
  const BehaviourNote({
    required this.id,
    required this.studentId,
    required this.occurredOn,
    required this.kind,
    required this.headline,
    required this.detail,
    required this.visibleToParent,
  });

  final int id;
  final int studentId;
  final String occurredOn;
  /// positive / concern / neutral
  final String kind;
  final String headline;
  final String? detail;
  final bool visibleToParent;

  factory BehaviourNote.fromJson(Map<String, dynamic> j) => BehaviourNote(
        id: (j['id'] as num?)?.toInt() ?? 0,
        studentId: (j['student_id'] as num?)?.toInt() ?? 0,
        occurredOn: (j['occurred_on'] as String?) ?? '',
        kind: (j['kind'] as String?) ?? 'neutral',
        headline: (j['headline'] as String?) ?? '',
        detail: j['detail'] as String?,
        visibleToParent: (j['visible_to_parent'] as bool?) ?? true,
      );
}

class StudentDrill {
  const StudentDrill({
    required this.studentId,
    required this.fullName,
    required this.admissionNumber,
    required this.rollNo,
    required this.photoUrl,
    required this.dateOfBirth,
    required this.gender,
    required this.bloodGroup,
    required this.classLabel,
    required this.sectionName,
    required this.address,
    required this.parentPhone,
    required this.parentEmail,
    required this.fatherName,
    required this.motherName,
    required this.emergencyPhone,
    required this.medicalConditions,
    required this.allergies,
    required this.attendance30dPct,
    required this.behaviourNotes,
  });

  final int studentId;
  final String fullName;
  final String admissionNumber;
  final String? rollNo;
  final String? photoUrl;
  final String? dateOfBirth;
  final String? gender;
  final String? bloodGroup;
  final String? classLabel;
  final String? sectionName;
  final String? address;
  final String? parentPhone;
  final String? parentEmail;
  final String? fatherName;
  final String? motherName;
  final String? emergencyPhone;
  final String? medicalConditions;
  final String? allergies;
  final double? attendance30dPct;
  final List<BehaviourNote> behaviourNotes;

  factory StudentDrill.fromJson(Map<String, dynamic> j) => StudentDrill(
        studentId: (j['student_id'] as num).toInt(),
        fullName: (j['full_name'] as String?) ?? '',
        admissionNumber: (j['admission_number'] as String?) ?? '',
        rollNo: j['roll_no'] as String?,
        photoUrl: j['photo_url'] as String?,
        dateOfBirth: j['date_of_birth'] as String?,
        gender: j['gender'] as String?,
        bloodGroup: j['blood_group'] as String?,
        classLabel: j['class_label'] as String?,
        sectionName: j['section_name'] as String?,
        address: j['address'] as String?,
        parentPhone: j['parent_phone'] as String?,
        parentEmail: j['parent_email'] as String?,
        fatherName: j['father_name'] as String?,
        motherName: j['mother_name'] as String?,
        emergencyPhone: j['emergency_phone'] as String?,
        medicalConditions: j['medical_conditions'] as String?,
        allergies: j['allergies'] as String?,
        attendance30dPct: _toDoubleOrNull(j['attendance_30d_pct']),
        behaviourNotes: ((j['behaviour_notes'] as List<dynamic>?) ?? const [])
            .map((e) => BehaviourNote.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
}

// ---- Staff (my own) leave ------------------------------------------------

class StaffLeaveRow {
  const StaffLeaveRow({
    required this.id,
    required this.userId,
    required this.startDate,
    required this.endDate,
    required this.reason,
    required this.kind,
    required this.status,
    required this.decisionRemarks,
    required this.decidedAt,
  });

  final int id;
  final int userId;
  final String startDate;
  final String endDate;
  final String reason;
  final String kind;
  /// pending / approved / rejected / cancelled
  final String status;
  final String? decisionRemarks;
  final String? decidedAt;

  bool get isPending => status == 'pending';

  factory StaffLeaveRow.fromJson(Map<String, dynamic> j) => StaffLeaveRow(
        id: (j['id'] as num).toInt(),
        userId: (j['user_id'] as num).toInt(),
        startDate: (j['start_date'] as String?) ?? '',
        endDate: (j['end_date'] as String?) ?? '',
        reason: (j['reason'] as String?) ?? '',
        kind: (j['kind'] as String?) ?? 'casual',
        status: (j['status'] as String?) ?? 'pending',
        decisionRemarks: j['decision_remarks'] as String?,
        decidedAt: j['decided_at'] as String?,
      );
}

// ---- Holidays + events (reuse same shape as parent feed) ----------------

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

void _addProfileSchoolFields(TeacherProfile _) {}

/// My own attendance row for today. Null status ⇒ not marked yet
/// ⇒ Today page shows "Mark me present" button.
class MyAttendance {
  const MyAttendance({
    required this.date,
    required this.teacherId,
    required this.status,
    required this.remarks,
  });

  final String date;
  final int? teacherId;
  /// present / absent / leave / half_day / null (=unmarked)
  final String? status;
  final String? remarks;

  bool get isMarked => status != null && status!.isNotEmpty;

  factory MyAttendance.fromJson(Map<String, dynamic> j) => MyAttendance(
        date: (j['date'] as String?) ?? '',
        teacherId: (j['teacher_id'] as num?)?.toInt(),
        status: j['status'] as String?,
        remarks: j['remarks'] as String?,
      );
}

// ---- Chat models ---------------------------------------------------------

class ChatContact {
  const ChatContact({
    required this.userId,
    required this.fullName,
    required this.kind,
    required this.email,
    required this.phone,
  });

  final int userId;
  final String fullName;
  /// "admin" | "parent"
  final String kind;
  final String? email;
  final String? phone;

  factory ChatContact.fromJson(Map<String, dynamic> j) => ChatContact(
        userId: (j['user_id'] as num).toInt(),
        fullName: (j['full_name'] as String?) ?? '',
        kind: (j['kind'] as String?) ?? 'admin',
        email: j['email'] as String?,
        phone: j['phone'] as String?,
      );
}

class ChatMessage {
  const ChatMessage({
    required this.id,
    required this.senderUserId,
    required this.recipientUserId,
    required this.subject,
    required this.body,
    required this.readAt,
    required this.createdAt,
  });

  final int id;
  final int? senderUserId;
  final int recipientUserId;
  final String? subject;
  final String body;
  final String? readAt;
  final String? createdAt;

  bool get isRead => readAt != null;

  factory ChatMessage.fromJson(Map<String, dynamic> j) => ChatMessage(
        id: (j['id'] as num?)?.toInt() ?? 0,
        senderUserId: (j['sender_user_id'] as num?)?.toInt(),
        recipientUserId: (j['recipient_user_id'] as num?)?.toInt() ?? 0,
        subject: j['subject'] as String?,
        body: (j['body'] as String?) ?? '',
        readAt: j['read_at'] as String?,
        createdAt: j['created_at'] as String?,
      );
}

// ---- Student exam history -------------------------------------------------

class StudentExamRow {
  const StudentExamRow({
    required this.examId,
    required this.examName,
    required this.totalMax,
    required this.totalObtained,
    required this.percentage,
    required this.overallGrade,
    required this.overallStatus,
    required this.subjects,
  });

  final int examId;
  final String examName;
  final double totalMax;
  final double totalObtained;
  final double percentage;
  final String? overallGrade;
  final String? overallStatus;
  final List<Map<String, dynamic>> subjects;

  factory StudentExamRow.fromJson(Map<String, dynamic> j) => StudentExamRow(
        examId: (j['exam_id'] as num?)?.toInt() ?? 0,
        examName: (j['exam_name'] as String?) ?? '',
        totalMax: _toNumDouble(j['total_max']),
        totalObtained: _toNumDouble(j['total_obtained']),
        percentage: _toNumDouble(j['percentage']),
        overallGrade: j['overall_grade'] as String?,
        overallStatus: j['overall_status'] as String?,
        subjects: ((j['subjects'] as List<dynamic>?) ?? const [])
            .map((e) => (e as Map<String, dynamic>))
            .toList(),
      );
}

double _toNumDouble(dynamic v) {
  if (v == null) return 0.0;
  if (v is num) return v.toDouble();
  if (v is String) return double.tryParse(v) ?? 0.0;
  return 0.0;
}

/// Published exam row for the teacher Calendar's Exams tab.
class ExamCalendarRow {
  const ExamCalendarRow({
    required this.id,
    required this.name,
    required this.kind,
    required this.startDate,
    required this.endDate,
    required this.status,
    required this.notes,
  });

  final int id;
  final String name;
  final String kind;
  final String? startDate;
  final String? endDate;
  final String status;
  final String? notes;

  factory ExamCalendarRow.fromJson(Map<String, dynamic> j) => ExamCalendarRow(
        id: (j['id'] as num?)?.toInt() ?? 0,
        name: (j['name'] as String?) ?? '',
        kind: (j['kind'] as String?) ?? 'unit_test',
        startDate: j['start_date'] as String?,
        endDate: j['end_date'] as String?,
        status: (j['status'] as String?) ?? 'draft',
        notes: j['notes'] as String?,
      );
}
