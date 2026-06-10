import 'package:flutter_bloc/flutter_bloc.dart';

import '../api/parent_repository.dart';

sealed class AttendanceState {
  const AttendanceState();
}

class AttendanceInitial extends AttendanceState {
  const AttendanceInitial();
}

class AttendanceLoading extends AttendanceState {
  const AttendanceLoading();
}

class AttendanceLoaded extends AttendanceState {
  const AttendanceLoaded(
    this.rows, {
    this.bySubject,
    this.classAverage,
  });

  final List<AttendanceRow> rows;

  /// Subject-wise breakdown (null while still loading, empty-with-note
  /// when the school doesn't use period attendance). Loaded in the
  /// background after the main rows arrive.
  final SubjectAttendanceReport? bySubject;

  /// "Your child vs class avg" comparison. Null while still loading,
  /// non-null when computed (may have classSize == 0 for invalid).
  final ClassAverage? classAverage;

  AttendanceLoaded copyWith({
    List<AttendanceRow>? rows,
    SubjectAttendanceReport? bySubject,
    ClassAverage? classAverage,
  }) =>
      AttendanceLoaded(
        rows ?? this.rows,
        bySubject: bySubject ?? this.bySubject,
        classAverage: classAverage ?? this.classAverage,
      );
}

class AttendanceError extends AttendanceState {
  const AttendanceError(this.message);
  final String message;
}

/// Phase 9: per-child attendance history. Caller passes the selected
/// `studentId` whenever it changes (`load(studentId)`) — the cubit doesn't
/// listen to ChildrenCubit directly to keep the dependency arrow one-way.
class AttendanceCubit extends Cubit<AttendanceState> {
  AttendanceCubit(this._repo) : super(const AttendanceInitial());

  final ParentRepository _repo;
  int? _lastStudentId;

  Future<void> load(int studentId, {bool force = false}) async {
    if (!force && _lastStudentId == studentId && state is AttendanceLoaded) {
      return;
    }
    _lastStudentId = studentId;
    emit(const AttendanceLoading());
    try {
      final rows = await _repo.attendance(studentId, limit: 60);
      // Emit the main rows first so the calendar / today card render
      // immediately. The subject breakdown + class average are slower
      // (they hit the timetable + a per-section aggregate) and don't
      // block the rest of the UI.
      emit(AttendanceLoaded(rows));

      final results = await Future.wait<dynamic>([
        _repo.attendanceBySubject(studentId, windowDays: 90),
        _repo.attendanceClassAverage(studentId, windowDays: 30),
      ]);
      if (_lastStudentId != studentId) return; // user switched kid mid-flight
      final current = state;
      if (current is AttendanceLoaded) {
        emit(current.copyWith(
          bySubject: results[0] as SubjectAttendanceReport,
          classAverage: results[1] as ClassAverage?,
        ));
      }
    } catch (e) {
      emit(AttendanceError(e.toString()));
    }
  }

  Future<void> refresh(int studentId) => load(studentId, force: true);
}
