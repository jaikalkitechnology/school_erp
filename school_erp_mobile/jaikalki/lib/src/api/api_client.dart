import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../core/error_bus.dart';

const _kAccessKey = 'jaikalki.access_token';
const _kRefreshKey = 'jaikalki.refresh_token';
const _kSubdomainKey = 'jaikalki.subdomain';

/// Default points at the production API. Override per build with
/// `--dart-define=API_BASE_URL=http://10.0.2.2:8000` for the Android emulator,
/// `http://localhost:8000` for an iOS simulator, or any other host.
const _defaultApiBaseUrl = String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: 'https://api.campus.jaikalki.in',
);

/// Single Dio instance for the entire app, with auth + tenant interceptor
/// + a coalesced 401 → /auth/refresh → retry loop so the user isn't booted
/// to the login screen every time the access token expires.
class ApiClient {
  ApiClient({String baseUrl = _defaultApiBaseUrl, FlutterSecureStorage? storage})
      : storage = storage ?? const FlutterSecureStorage(),
        _baseUrl = baseUrl,
        dio = Dio(
          BaseOptions(
            baseUrl: baseUrl,
            connectTimeout: const Duration(seconds: 10),
            receiveTimeout: const Duration(seconds: 15),
            contentType: 'application/json',
          ),
        ) {
    debugPrint('[ApiClient] baseUrl=$baseUrl');
    dio.interceptors.add(
      InterceptorsWrapper(onRequest: (options, handler) async {
        final token = await this.storage.read(key: _kAccessKey);
        final subdomain = await this.storage.read(key: _kSubdomainKey);
        if (token != null) options.headers['Authorization'] = 'Bearer $token';
        if (subdomain != null) options.headers['X-Tenant-Subdomain'] = subdomain;
        debugPrint(
          '[ApiClient] -> ${options.method} ${options.uri} '
          'subdomain=$subdomain',
        );
        handler.next(options);
      }, onError: (err, handler) async {
        // Coalesced refresh: a 401 from any endpoint except /auth/* gets
        // a single retry after we successfully exchange the refresh
        // token for a new access token. The Completer ensures concurrent
        // 401s only fire one refresh — all callers wait for the same
        // future, then retry against the new token.
        if (await _maybeRefreshAndRetry(err, handler)) return;
        debugPrint(
          '[ApiClient] !! ${err.requestOptions.method} ${err.requestOptions.uri} '
          '-> ${err.type} ${err.response?.statusCode ?? ""} ${err.message}',
        );
        handler.next(err);
      }),
    );
    dio.interceptors.add(ErrorInterceptor(fallback: 'Could not reach the school server.'));
  }

  /// The base URL this client is talking to. Surfaced so debug UIs can show
  /// the user what host their requests are hitting.
  final String _baseUrl;
  String get baseUrl => _baseUrl;

  final Dio dio;
  final FlutterSecureStorage storage;

  // ----- Coalesced refresh ---------------------------------------------------

  Completer<String?>? _refreshInFlight;

  bool _isAuthEndpoint(String? path) {
    if (path == null) return false;
    return path.contains('/v1/auth/login') ||
        path.contains('/v1/auth/refresh') ||
        path.contains('/v1/auth/logout');
  }

  /// Returns true if the error was a 401 we successfully refreshed
  /// + retried — caller should not propagate the error in that case.
  Future<bool> _maybeRefreshAndRetry(
    DioException err,
    ErrorInterceptorHandler handler,
  ) async {
    if (err.response?.statusCode != 401) return false;
    final req = err.requestOptions;
    if (_isAuthEndpoint(req.path)) return false;
    // One retry per request — second 401 means the refresh genuinely
    // didn't help and the user has to sign in again.
    if (req.extra['__retried'] == true) return false;

    final newAccess = await _runRefresh();
    if (newAccess == null) return false;

    req.extra['__retried'] = true;
    req.headers['Authorization'] = 'Bearer $newAccess';
    try {
      final response = await dio.fetch(req);
      handler.resolve(response);
      return true;
    } on DioException catch (retryErr) {
      handler.next(retryErr);
      return true;
    }
  }

  Future<String?> _runRefresh() async {
    final pending = _refreshInFlight;
    if (pending != null) return pending.future;

    final c = Completer<String?>();
    _refreshInFlight = c;

    try {
      final refresh = await storage.read(key: _kRefreshKey);
      if (refresh == null) {
        c.complete(null);
        return null;
      }
      // Bare http client so we don't recurse through this interceptor.
      final bare = Dio(BaseOptions(baseUrl: _baseUrl, contentType: 'application/json'));
      final subdomain = await storage.read(key: _kSubdomainKey);
      final res = await bare.post<Map<String, dynamic>>(
        '/v1/auth/refresh',
        data: {'refresh_token': refresh},
        options: Options(headers: {
          if (subdomain != null) 'X-Tenant-Subdomain': subdomain,
        }),
      );
      final data = res.data ?? const {};
      final newAccess = data['access_token'] as String?;
      final newRefresh = data['refresh_token'] as String?;
      if (newAccess != null) {
        await storage.write(key: _kAccessKey, value: newAccess);
      }
      if (newRefresh != null) {
        await storage.write(key: _kRefreshKey, value: newRefresh);
      }
      c.complete(newAccess);
      return newAccess;
    } catch (_) {
      c.complete(null);
      return null;
    } finally {
      // Let the queue drain, then clear so the next 401 starts a fresh
      // refresh attempt.
      Future<void>.microtask(() => _refreshInFlight = null);
    }
  }

  Future<Map<String, dynamic>> health() async {
    final res = await dio.get<Map<String, dynamic>>('/v1/health');
    return res.data ?? <String, dynamic>{};
  }
}
