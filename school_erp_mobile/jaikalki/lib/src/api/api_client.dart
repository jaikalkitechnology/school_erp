import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../core/error_bus.dart';

const _kAccessKey = 'jaikalki.access_token';
const _kSubdomainKey = 'jaikalki.subdomain';

/// Default points at the production API. Override per build with
/// `--dart-define=API_BASE_URL=http://10.0.2.2:8000` for the Android emulator,
/// `http://localhost:8000` for an iOS simulator, or any other host.
const _defaultApiBaseUrl = String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: 'https://api.campus.jaikalki.in',
);

/// Single Dio instance for the entire app, with auth + tenant interceptor.
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
      }, onError: (err, handler) {
        // Surface the URL + error type so timeouts aren't a black box.
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

  Future<Map<String, dynamic>> health() async {
    final res = await dio.get<Map<String, dynamic>>('/v1/health');
    return res.data ?? <String, dynamic>{};
  }
}
