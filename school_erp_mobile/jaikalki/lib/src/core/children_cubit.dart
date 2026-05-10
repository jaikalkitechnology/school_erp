import 'package:flutter_bloc/flutter_bloc.dart';

import '../api/parent_repository.dart';

sealed class ChildrenState {
  const ChildrenState();
}

class ChildrenInitial extends ChildrenState {
  const ChildrenInitial();
}

class ChildrenLoading extends ChildrenState {
  const ChildrenLoading();
}

class ChildrenLoaded extends ChildrenState {
  const ChildrenLoaded({
    required this.children,
    required this.selectedId,
    this.dashboard,
    this.dashboardLoading = false,
  });

  final List<Child> children;
  final int? selectedId;
  final ChildDashboard? dashboard;
  final bool dashboardLoading;

  Child? get selected =>
      children.where((c) => c.studentId == selectedId).cast<Child?>().firstWhere(
            (_) => true,
            orElse: () => null,
          );

  ChildrenLoaded copyWith({
    List<Child>? children,
    int? selectedId,
    ChildDashboard? dashboard,
    bool? dashboardLoading,
  }) =>
      ChildrenLoaded(
        children: children ?? this.children,
        selectedId: selectedId ?? this.selectedId,
        dashboard: dashboard ?? this.dashboard,
        dashboardLoading: dashboardLoading ?? this.dashboardLoading,
      );
}

class ChildrenError extends ChildrenState {
  const ChildrenError(this.message);
  final String message;
}

class ChildrenCubit extends Cubit<ChildrenState> {
  ChildrenCubit(this._repo) : super(const ChildrenInitial());

  final ParentRepository _repo;

  Future<void> load() async {
    emit(const ChildrenLoading());
    try {
      final children = await _repo.children();
      if (children.isEmpty) {
        emit(ChildrenLoaded(children: const [], selectedId: null));
        return;
      }
      final initial = children.first.studentId;
      emit(ChildrenLoaded(
        children: children,
        selectedId: initial,
        dashboardLoading: true,
      ));
      final dash = await _repo.dashboard(initial);
      emit(ChildrenLoaded(
        children: children,
        selectedId: initial,
        dashboard: dash,
        dashboardLoading: false,
      ));
    } catch (e) {
      emit(ChildrenError('Could not load children: $e'));
    }
  }

  Future<void> select(int studentId) async {
    final s = state;
    if (s is! ChildrenLoaded) return;
    if (s.selectedId == studentId) return;
    emit(s.copyWith(selectedId: studentId, dashboardLoading: true));
    try {
      await _repo.selectChild(studentId);
      final dash = await _repo.dashboard(studentId);
      emit(s.copyWith(
        selectedId: studentId,
        dashboard: dash,
        dashboardLoading: false,
      ));
    } catch (e) {
      emit(s.copyWith(
        selectedId: studentId,
        dashboard: null,
        dashboardLoading: false,
      ));
    }
  }
}
