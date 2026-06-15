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
  });

  final String date;
  final int dayOfWeek;
  final List<TodayPeriod> periods;
  final int pendingHomeworkCount;
  final int pendingLeavesCount;
  final int sectionsToMarkAttendance;

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
