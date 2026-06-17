import 'package:dio/dio.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../api/parent_repository.dart';

/// Best-effort extraction of the backend's `detail` string from a Dio
/// error. Falls back to the raw e.toString() for non-HTTP errors so we
/// never lose information.
String _readableError(Object e) {
  if (e is DioException) {
    final status = e.response?.statusCode;
    final data = e.response?.data;
    String? detail;
    if (data is Map && data['detail'] != null) {
      detail = data['detail'].toString();
    }
    if (status == 401) return 'Session expired — please sign in again.';
    if (status == 403) return 'You don\'t have access to this child\'s fees.';
    if (status == 404) return 'Fee data not found for this child.';
    if (status != null && detail != null) return '$status: $detail';
    if (detail != null) return detail;
    if (status != null) return 'Server returned $status';
    if (e.type == DioExceptionType.connectionTimeout ||
        e.type == DioExceptionType.receiveTimeout) {
      return 'Network timeout. Check your connection and retry.';
    }
    return 'Network error: ${e.message ?? e.type.name}';
  }
  return e.toString();
}

sealed class FeesState {
  const FeesState();
}

class FeesInitial extends FeesState {
  const FeesInitial();
}

class FeesLoading extends FeesState {
  const FeesLoading();
}

class FeesLoaded extends FeesState {
  const FeesLoaded(this.view);
  final ChildFeeView view;
}

class FeesError extends FeesState {
  const FeesError(this.message);
  final String message;
}

/// Phase 11: per-child fee invoices + roll-up.
class FeesCubit extends Cubit<FeesState> {
  FeesCubit(this._repo) : super(const FeesInitial());

  final ParentRepository _repo;
  int? _lastStudentId;

  Future<void> load(int studentId, {bool force = false}) async {
    if (!force && _lastStudentId == studentId && state is FeesLoaded) return;
    _lastStudentId = studentId;
    emit(const FeesLoading());
    try {
      final view = await _repo.fees(studentId);
      emit(FeesLoaded(view));
    } catch (e) {
      emit(FeesError(_readableError(e)));
    }
  }

  Future<void> refresh(int studentId) => load(studentId, force: true);

  /// Stubs the Razorpay handoff. Returns the backend's order_id +
  /// metadata; the actual SDK launch will live in the page once a merchant
  /// account is provisioned (see PHASE_PROGRESS.md Phase 11 deferred).
  Future<Map<String, dynamic>> initiatePayment({
    required int invoiceId,
    required int studentId,
  }) =>
      _repo.initiatePayment(invoiceId: invoiceId, studentId: studentId);
}
