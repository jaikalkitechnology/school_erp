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

  Future<AuthUser?> me() async {
    final token = await _storage.read(key: _kAccessKey);
    if (token == null) return null;
    try {
      final res = await _api.dio.get<Map<String, dynamic>>('/v1/auth/me');
      return AuthUser.fromJson(res.data!);
    } on DioException {
      return null;
    }
  }

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
