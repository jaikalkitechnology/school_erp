import 'package:flutter_bloc/flutter_bloc.dart';

import '../api/parent_repository.dart' show ParentRepository, Child, ChildDashboard, AttendanceRow;
import 'offline_cache.dart';

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
  ChildrenCubit(this._repo, {OfflineCache? cache})
      : _cache = cache ?? OfflineCache(),
        super(const ChildrenInitial());

  final ParentRepository _repo;
  final OfflineCache _cache;

  Future<void> load() async {
    // Best-effort warm boot from cache so the dashboard renders instantly
    // even without network.
    try {
      final cachedChildren = await _cache.get('children') as List<dynamic>?;
      final cachedSelected = await _cache.get('selected_child_id');
      final cachedDashRaw = await _cache.get('dashboard');
      if (cachedChildren != null) {
        final children = cachedChildren
            .map((e) => Child.fromJson(Map<String, dynamic>.from(e as Map)))
            .toList();
        emit(ChildrenLoaded(
          children: children,
          selectedId: cachedSelected as int?,
          dashboard: cachedDashRaw is Map
              ? ChildDashboard.fromJson(Map<String, dynamic>.from(cachedDashRaw))
              : null,
          dashboardLoading: true,
        ));
      } else {
        emit(const ChildrenLoading());
      }
    } catch (_) {
      emit(const ChildrenLoading());
    }

    try {
      final children = await _repo.children();
      if (children.isEmpty) {
        await _cache.put('children', const []);
        emit(const ChildrenLoaded(children: [], selectedId: null));
        return;
      }
      await _cache.put(
        'children',
        children
            .map((c) => {
                  'student_id': c.studentId,
                  'full_name': c.fullName,
                  'admission_number': c.admissionNumber,
                  'current_class_label': c.classLabel,
                  'relation': c.relation,
                  'access_level': c.accessLevel,
                  'is_primary': c.isPrimary,
                })
            .toList(),
      );
      final initial = children.first.studentId;
      await _cache.put('selected_child_id', initial);
      emit(ChildrenLoaded(
        children: children,
        selectedId: initial,
        dashboardLoading: true,
      ));
      final dash = await _repo.dashboard(initial);
      await _cache.put('dashboard', _dashToJson(dash));
      emit(ChildrenLoaded(
        children: children,
        selectedId: initial,
        dashboard: dash,
        dashboardLoading: false,
      ));
    } catch (e) {
      // Network failed; if we already painted from cache, leave that visible.
      if (state is! ChildrenLoaded) {
        emit(ChildrenError('Could not load children: $e'));
      } else {
        final s = state as ChildrenLoaded;
        emit(s.copyWith(dashboardLoading: false));
      }
    }
  }

  Future<void> select(int studentId) async {
    final s = state;
    if (s is! ChildrenLoaded) return;
    if (s.selectedId == studentId) return;
    emit(s.copyWith(selectedId: studentId, dashboardLoading: true));
    await _cache.put('selected_child_id', studentId);
    try {
      await _repo.selectChild(studentId);
      final dash = await _repo.dashboard(studentId);
      await _cache.put('dashboard', _dashToJson(dash));
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

  Future<List<AttendanceRow>> attendance(int studentId) =>
      _repo.attendance(studentId);
}

Map<String, dynamic> _dashToJson(ChildDashboard d) => {
      'student_id': d.studentId,
      'full_name': d.fullName,
      'admission_number': d.admissionNumber,
      'current_class_label': d.classLabel,
      'is_active': d.isActive,
      'pending_leaves': d.pendingLeaves,
      'documents_count': d.documentsCount,
      'sibling_ids': d.siblingIds,
      'upcoming_events_count': d.upcomingEventsCount,
    };
