import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

const _kAccessKey = 'jaikalki.access_token';
const _kSubdomainKey = 'jaikalki.subdomain';

/// Single Dio instance for the entire app, with auth + tenant interceptor.
class ApiClient {
  ApiClient({String baseUrl = 'http://10.0.2.2:8000', FlutterSecureStorage? storage})
      : storage = storage ?? const FlutterSecureStorage(),
        dio = Dio(
          BaseOptions(
            baseUrl: baseUrl,
            connectTimeout: const Duration(seconds: 10),
            receiveTimeout: const Duration(seconds: 15),
            contentType: 'application/json',
          ),
        ) {
    dio.interceptors.add(
      InterceptorsWrapper(onRequest: (options, handler) async {
        final token = await this.storage.read(key: _kAccessKey);
        final subdomain = await this.storage.read(key: _kSubdomainKey);
        if (token != null) options.headers['Authorization'] = 'Bearer $token';
        if (subdomain != null) options.headers['X-Tenant-Subdomain'] = subdomain;
        handler.next(options);
      }),
    );
  }

  final Dio dio;
  final FlutterSecureStorage storage;

  Future<Map<String, dynamic>> health() async {
    final res = await dio.get<Map<String, dynamic>>('/v1/health');
    return res.data ?? <String, dynamic>{};
  }
}
