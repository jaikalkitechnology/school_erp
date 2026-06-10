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
  const AttendanceLoaded(this.rows);
  final List<AttendanceRow> rows;
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
      // Pull 60 days so the calendar can render two full months without
      // a second request when the user pages back.
      final rows = await _repo.attendance(studentId, limit: 60);
      emit(AttendanceLoaded(rows));
    } catch (e) {
      emit(AttendanceError(e.toString()));
    }
  }

  Future<void> refresh(int studentId) => load(studentId, force: true);
}
