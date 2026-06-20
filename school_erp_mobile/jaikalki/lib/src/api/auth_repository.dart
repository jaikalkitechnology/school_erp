import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../models/user_role.dart';
import 'api_client.dart';

class AuthUser {
  AuthUser({
    required this.id,
    required this.fullName,
    required this.email,
    required this.tenantId,
    required this.tenantSubdomain,
    required this.schoolName,
    required this.roles,
    required this.permissions,
    required this.primaryRole,
  });

  final int id;
  final String fullName;
  final String? email;
  final int tenantId;
  final String? tenantSubdomain;
  final String? schoolName;
  final List<String> roles;
  final List<String> permissions;
  final String? primaryRole;

  factory AuthUser.fromJson(Map<String, dynamic> j) => AuthUser(
        id: j['id'] as int,
        fullName: j['full_name'] as String,
        email: j['email'] as String?,
        tenantId: j['tenant_id'] as int,
        tenantSubdomain: j['tenant_subdomain'] as String?,
        schoolName: j['school_name'] as String?,
        roles: (j['roles'] as List<dynamic>).cast<String>(),
        permissions: (j['permissions'] as List<dynamic>).cast<String>(),
        primaryRole: j['primary_role'] as String?,
      );
}

class TokenPair {
  const TokenPair({required this.accessToken, required this.refreshToken, required this.expiresIn});
  final String accessToken;
  final String refreshToken;
  final int expiresIn;

  factory TokenPair.fromJson(Map<String, dynamic> j) => TokenPair(
        accessToken: j['access_token'] as String,
        refreshToken: j['refresh_token'] as String,
        expiresIn: (j['expires_in'] as num).toInt(),
      );
}

class LoginResult {
  const LoginResult({required this.user, required this.tokens});
  final AuthUser user;
  final TokenPair tokens;
}

const _kAccessKey = 'jaikalki.access_token';
const _kRefreshKey = 'jaikalki.refresh_token';
const _kSubdomainKey = 'jaikalki.subdomain';

class AuthRepository {
  AuthRepository(this._api, {FlutterSecureStorage? storage})
      : _storage = storage ?? const FlutterSecureStorage();

  final ApiClient _api;
  final FlutterSecureStorage _storage;

  Future<String?> readSubdomain() => _storage.read(key: _kSubdomainKey);
  Future<String?> readAccessToken() => _storage.read(key: _kAccessKey);

  /// Hook called by ApiClient interceptor. Returns headers to attach.
  Future<Map<String, String>> authHeaders() async {
    final token = await _storage.read(key: _kAccessKey);
    final subdomain = await _storage.read(key: _kSubdomainKey);
    return {
      if (token != null) 'Authorization': 'Bearer $token',
      if (subdomain != null) 'X-Tenant-Subdomain': subdomain,
    };
  }

  Future<LoginResult> login({
    required String identifier,
    required String password,
    required String subdomain,
  }) async {
    try {
      final res = await _api.dio.post<Map<String, dynamic>>(
        '/v1/auth/login',
        data: {
          'identifier': identifier.trim().toLowerCase(),
          'password': password,
          'subdomain': subdomain.trim().toLowerCase(),
        },
      );
      final body = res.data!;
      final tokens = TokenPair.fromJson(body['tokens'] as Map<String, dynamic>);
      final user = AuthUser.fromJson(body['user'] as Map<String, dynamic>);
      await _storage.write(key: _kAccessKey, value: tokens.accessToken);
      await _storage.write(key: _kRefreshKey, value: tokens.refreshToken);
      await _storage.write(key: _kSubdomainKey, value: user.tenantSubdomain ?? subdomain);
      return LoginResult(user: user, tokens: tokens);
    } on DioException catch (e) {
      final detail = e.response?.data is Map ? (e.response!.data as Map)['detail'] : null;
      throw AuthException(detail?.toString() ?? 'Sign-in failed. Please try again.');
    }
  }

  /// Outcome of an attempted "who am I" check at app startup or
  /// whenever the app comes back to the foreground.
  ///
  /// Drives the cubit's decision tree:
  ///   * [user] non-null         → user is signed in.
  ///   * [user] null +
  ///     [sessionInvalid] true   → token is gone or the server returned
  ///                               401/403; bounce to the login screen.
  ///   * [user] null +
  ///     [sessionInvalid] false  → network blip, 5xx, timeout, anything
  ///                               transient — **keep the user signed
  ///                               in** and try again later. This is
  ///                               the whole point of the new path: a
  ///                               flaky wi-fi shouldn't kick the
  ///                               parent out of the app.
  Future<({AuthUser? user, bool sessionInvalid})> tryMe() async {
    final token = await _storage.read(key: _kAccessKey);
    if (token == null) {
      // No credentials persisted — they're not signed in.
      return (user: null, sessionInvalid: true);
    }
    try {
      final res = await _api.dio.get<Map<String, dynamic>>('/v1/auth/me');
      return (user: AuthUser.fromJson(res.data!), sessionInvalid: false);
    } on DioException catch (e) {
      final code = e.response?.statusCode;
      // 401/403 means the bearer token was definitively rejected
      // (after the api client already tried to refresh once). 410
      // means the tenant is gone. Either way, sign out cleanly.
      if (code == 401 || code == 403 || code == 410) {
        return (user: null, sessionInvalid: true);
      }
      // Anything else — connection error, timeout, 5xx — is transient.
      // Hold the existing session so the user doesn't get bumped to the
      // login form for an unrelated reason.
      return (user: null, sessionInvalid: false);
    }
  }

  /// Backwards-compatible shape: returns null on auth failure OR
  /// transient errors. Prefer [tryMe] for new code so callers can
  /// distinguish "session ended" from "couldn't reach the server".
  Future<AuthUser?> me() async => (await tryMe()).user;

  Future<void> logout() async {
    final refresh = await _storage.read(key: _kRefreshKey);
    try {
      await _api.dio.post<dynamic>('/v1/auth/logout', data: {'refresh_token': refresh});
    } on DioException {
      // Best-effort; we still clear locally.
    } finally {
      await _storage.delete(key: _kAccessKey);
      await _storage.delete(key: _kRefreshKey);
    }
  }

  /// Step 1 of passwordless login: ask the server to send a one-time
  /// login code to the identifier (email or phone). Same response
  /// shape as [requestPasswordResetOtp] — including the dev_otp echo
  /// — so the mobile UI can render both flows from a single widget.
  Future<ForgotPasswordResult> requestLoginOtp({
    required String identifier,
    required String subdomain,
  }) async {
    try {
      final res = await _api.dio.post<Map<String, dynamic>>(
        '/v1/auth/login/otp/request',
        data: {
          'identifier': identifier.trim().toLowerCase(),
          'subdomain': subdomain.trim().toLowerCase(),
        },
      );
      final body = res.data ?? const {};
      return ForgotPasswordResult(
        channel: (body['channel'] as String?) ?? 'sms',
        expiresInMinutes:
            (body['expires_in_minutes'] as num?)?.toInt() ?? 10,
        devOtp: body['dev_otp'] as String?,
      );
    } on DioException catch (e) {
      final detail =
          e.response?.data is Map ? (e.response!.data as Map)['detail'] : null;
      throw AuthException(
        detail?.toString() ?? 'Could not send a login code. Try again.',
      );
    }
  }

  /// Step 2 of passwordless login: trade the OTP for the same
  /// LoginResponse shape as [login]. On success the tokens are
  /// persisted in secure storage so subsequent calls authenticate
  /// transparently.
  Future<LoginResult> loginWithOtp({
    required String identifier,
    required String subdomain,
    required String otp,
  }) async {
    try {
      final res = await _api.dio.post<Map<String, dynamic>>(
        '/v1/auth/login/otp/verify',
        data: {
          'identifier': identifier.trim().toLowerCase(),
          'subdomain': subdomain.trim().toLowerCase(),
          'otp': otp.trim(),
        },
      );
      final body = res.data!;
      final tokens = TokenPair.fromJson(body['tokens'] as Map<String, dynamic>);
      final user = AuthUser.fromJson(body['user'] as Map<String, dynamic>);
      await _storage.write(key: _kAccessKey, value: tokens.accessToken);
      await _storage.write(key: _kRefreshKey, value: tokens.refreshToken);
      await _storage.write(
        key: _kSubdomainKey,
        value: user.tenantSubdomain ?? subdomain,
      );
      return LoginResult(user: user, tokens: tokens);
    } on DioException catch (e) {
      final detail =
          e.response?.data is Map ? (e.response!.data as Map)['detail'] : null;
      throw AuthException(
        detail?.toString() ?? 'Invalid or expired code.',
      );
    }
  }

  /// Step 1 of forgot-password: request that the server send a one-time
  /// code to the identifier (email or phone). The body returned by the
  /// server includes ``channel`` (sms/email) and, in dev builds only,
  /// the actual ``dev_otp`` so testers can complete the flow without a
  /// real SMS gateway.
  Future<ForgotPasswordResult> requestPasswordResetOtp({
    required String identifier,
    required String subdomain,
  }) async {
    try {
      final res = await _api.dio.post<Map<String, dynamic>>(
        '/v1/auth/forgot-password',
        data: {
          'identifier': identifier.trim().toLowerCase(),
          'subdomain': subdomain.trim().toLowerCase(),
        },
      );
      final body = res.data ?? const {};
      return ForgotPasswordResult(
        channel: (body['channel'] as String?) ?? 'sms',
        expiresInMinutes:
            (body['expires_in_minutes'] as num?)?.toInt() ?? 10,
        devOtp: body['dev_otp'] as String?,
      );
    } on DioException catch (e) {
      final detail =
          e.response?.data is Map ? (e.response!.data as Map)['detail'] : null;
      throw AuthException(
        detail?.toString() ?? 'Could not send a reset code. Try again.',
      );
    }
  }

  /// Step 2 of forgot-password: verify the OTP and set a new password.
  /// On success the server returns 204; the caller should send the user
  /// back to the login screen.
  Future<void> resetPasswordWithOtp({
    required String identifier,
    required String subdomain,
    required String otp,
    required String newPassword,
  }) async {
    try {
      await _api.dio.post<dynamic>(
        '/v1/auth/reset-password',
        data: {
          'identifier': identifier.trim().toLowerCase(),
          'subdomain': subdomain.trim().toLowerCase(),
          'otp': otp.trim(),
          'new_password': newPassword,
        },
      );
    } on DioException catch (e) {
      final detail =
          e.response?.data is Map ? (e.response!.data as Map)['detail'] : null;
      throw AuthException(
        detail?.toString() ?? 'Invalid or expired code.',
      );
    }
  }

  /// Best-effort FCM token registration. Safe to call on every cold
  /// start — the server upserts on (user_id, fcm_token). Failures are
  /// swallowed: push notifications aren't critical to using the app.
  Future<void> registerDevice({
    required String fcmToken,
    String platform = 'android',
    String? appVersion,
    String? deviceLabel,
  }) async {
    if (fcmToken.isEmpty) return;
    try {
      await _api.dio.post<dynamic>(
        '/v1/auth/devices/register',
        data: {
          'fcm_token': fcmToken,
          'platform': platform,
          if (appVersion != null) 'app_version': appVersion,
          if (deviceLabel != null) 'device_label': deviceLabel,
        },
      );
    } on DioException {
      // Push registration is best-effort; never break the login UX.
    }
  }

  Future<void> unregisterDevice({required String fcmToken}) async {
    if (fcmToken.isEmpty) return;
    try {
      await _api.dio.post<dynamic>(
        '/v1/auth/devices/unregister',
        data: {'fcm_token': fcmToken},
      );
    } on DioException {
      // Ignored.
    }
  }

  /// Resolve the canonical role for routing.
  UserRole? mapRole(String? code) {
    if (code == null) return null;
    return switch (code) {
      'school_admin' => UserRole.schoolAdmin,
      'principal' => UserRole.principal,
      'vice_principal' => UserRole.vicePrincipal,
      'coordinator' => UserRole.coordinator,
      'class_teacher' => UserRole.classTeacher,
      'subject_teacher' => UserRole.subjectTeacher,
      'accountant' => UserRole.accountant,
      'librarian' => UserRole.librarian,
      'transport_manager' => UserRole.transportManager,
      'hostel_warden' => UserRole.hostelWarden,
      'office_staff' => UserRole.officeStaff,
      'parent' => UserRole.parent,
      'student' => UserRole.student,
      _ => null,
    };
  }
}

class AuthException implements Exception {
  AuthException(this.message);
  final String message;

  @override
  String toString() => message;
}

/// Response from /v1/auth/forgot-password.
class ForgotPasswordResult {
  const ForgotPasswordResult({
    required this.channel,
    required this.expiresInMinutes,
    this.devOtp,
  });

  /// "sms" | "email"
  final String channel;
  final int expiresInMinutes;

  /// Echoed only when the backend is running with ENVIRONMENT != "production".
  /// Mobile UI may surface it under a "Dev OTP" hint so testers can finish
  /// the flow without a real SMS provider.
  final String? devOtp;
}
