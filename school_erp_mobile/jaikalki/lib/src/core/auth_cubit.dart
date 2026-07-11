import 'dart:async';

import 'package:flutter_bloc/flutter_bloc.dart';

import '../api/auth_repository.dart';
import 'push_service.dart';

sealed class AuthState {
  const AuthState();
}

class AuthInitial extends AuthState {
  const AuthInitial();
}

class AuthAuthenticating extends AuthState {
  const AuthAuthenticating();
}

class AuthAuthenticated extends AuthState {
  const AuthAuthenticated(this.user);
  final AuthUser user;
}

class AuthError extends AuthState {
  const AuthError(this.message);
  final String message;
}

class AuthCubit extends Cubit<AuthState> {
  AuthCubit(this._repo) : super(const AuthInitial());

  final AuthRepository _repo;

  Future<void> bootstrap() async {
    final result = await _repo.tryMe();
    if (result.user != null) {
      emit(AuthAuthenticated(result.user!));
      // Cold-start with a valid session: re-register the FCM token
      // against this session so the backend has a fresh row even if
      // the OS rotated the token while the app was killed.
      unawaited(PushService.instance.registerForCurrentSession());
      return;
    }
    if (result.sessionInvalid) {
      // Token was missing / rejected (401/403/410) — clean sign-out.
      emit(const AuthInitial());
      return;
    }
    // Transient failure (network, 5xx). If we already had an
    // authenticated session, keep it — otherwise stay on the splash /
    // initial state. The user explicitly hitting Sign out is now the
    // only way to actually log out on bad connectivity.
    if (state is! AuthAuthenticated) {
      emit(const AuthInitial());
    }
  }

  Future<void> login({
    required String identifier,
    required String password,
    required String subdomain,
  }) async {
    emit(const AuthAuthenticating());
    try {
      final result = await _repo.login(
        identifier: identifier,
        password: password,
        subdomain: subdomain,
      );
      emit(AuthAuthenticated(result.user));
      // Force a fresh /v1/auth/devices/register against this session.
      // Even when FCM hands back the same token string we saw on the
      // previous user, the backend needs to upsert it against the new
      // user_id (and deactivate the old user's row).
      unawaited(PushService.instance.registerForCurrentSession());
    } on AuthException catch (e) {
      emit(AuthError(e.message));
    } catch (e) {
      emit(AuthError('Sign-in failed: $e'));
    }
  }

  Future<void> loginWithGoogle({
    required String idToken,
    required String subdomain,
  }) async {
    emit(const AuthAuthenticating());
    try {
      final result = await _repo.loginWithGoogle(
        idToken: idToken,
        subdomain: subdomain,
      );
      emit(AuthAuthenticated(result.user));
      unawaited(PushService.instance.registerForCurrentSession());
    } on AuthException catch (e) {
      emit(AuthError(e.message));
    } catch (e) {
      emit(AuthError('Google sign-in failed: $e'));
    }
  }

  Future<void> loginWithOtp({
    required String identifier,
    required String subdomain,
    required String otp,
  }) async {
    emit(const AuthAuthenticating());
    try {
      final result = await _repo.loginWithOtp(
        identifier: identifier,
        subdomain: subdomain,
        otp: otp,
      );
      emit(AuthAuthenticated(result.user));
      unawaited(PushService.instance.registerForCurrentSession());
    } on AuthException catch (e) {
      emit(AuthError(e.message));
    } catch (e) {
      emit(AuthError('Sign-in failed: $e'));
    }
  }

  Future<void> logout() async {
    // Best-effort: tell the server to deactivate the push token for
    // this device first, so the user doesn't keep receiving messages
    // meant for the account they just signed out of.
    await PushService.instance.unregisterCurrentDevice();
    await _repo.logout();
    emit(const AuthInitial());
  }
}
