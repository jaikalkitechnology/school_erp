import 'package:flutter_bloc/flutter_bloc.dart';

import '../api/auth_repository.dart';

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
    final user = await _repo.me();
    if (user != null) {
      emit(AuthAuthenticated(user));
    } else {
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
    } on AuthException catch (e) {
      emit(AuthError(e.message));
    } catch (e) {
      emit(AuthError('Sign-in failed: $e'));
    }
  }

  Future<void> logout() async {
    await _repo.logout();
    emit(const AuthInitial());
  }
}
