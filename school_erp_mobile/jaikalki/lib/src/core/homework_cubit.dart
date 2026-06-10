import 'package:flutter_bloc/flutter_bloc.dart';

import '../api/parent_repository.dart';

sealed class HomeworkState {
  const HomeworkState();
}

class HomeworkInitial extends HomeworkState {
  const HomeworkInitial();
}

class HomeworkLoading extends HomeworkState {
  const HomeworkLoading();
}

class HomeworkLoaded extends HomeworkState {
  const HomeworkLoaded(this.items, {this.submitting = false});

  final List<HomeworkItem> items;
  final bool submitting;

  List<HomeworkItem> get open => items.where((h) => h.isOpen).toList();
  List<HomeworkItem> get submitted => items.where((h) => h.isSubmitted).toList();
  List<HomeworkItem> get graded => items.where((h) => h.isGraded).toList();

  HomeworkLoaded copyWith({List<HomeworkItem>? items, bool? submitting}) =>
      HomeworkLoaded(items ?? this.items, submitting: submitting ?? this.submitting);
}

class HomeworkError extends HomeworkState {
  const HomeworkError(this.message);
  final String message;
}

/// Phase 14: per-child homework feed + parent-mediated submission.
class HomeworkCubit extends Cubit<HomeworkState> {
  HomeworkCubit(this._repo) : super(const HomeworkInitial());

  final ParentRepository _repo;
  int? _lastStudentId;

  Future<void> load(int studentId, {bool force = false}) async {
    if (!force && _lastStudentId == studentId && state is HomeworkLoaded) return;
    _lastStudentId = studentId;
    emit(const HomeworkLoading());
    try {
      final items = await _repo.homework(studentId);
      emit(HomeworkLoaded(items));
    } catch (e) {
      emit(HomeworkError(e.toString()));
    }
  }

  Future<void> refresh(int studentId) => load(studentId, force: true);

  /// POSTs a submission and re-fetches the feed so the row flips from
  /// "open" to "submitted" without a manual refresh.
  Future<bool> submit({
    required int homeworkId,
    required int studentId,
    required String content,
  }) async {
    final current = state;
    if (current is! HomeworkLoaded) return false;
    emit(current.copyWith(submitting: true));
    try {
      await _repo.submitHomework(
        homeworkId: homeworkId,
        studentId: studentId,
        content: content,
      );
      await load(studentId, force: true);
      return true;
    } catch (_) {
      emit(current.copyWith(submitting: false));
      return false;
    }
  }
}
