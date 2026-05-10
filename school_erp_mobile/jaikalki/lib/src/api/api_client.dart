import 'package:dio/dio.dart';

/// Single Dio instance for the entire app.
/// Phase 2 will add auth + tenant interceptors.
class ApiClient {
  ApiClient({String baseUrl = 'http://10.0.2.2:8000'})
      : dio = Dio(
          BaseOptions(
            baseUrl: baseUrl,
            connectTimeout: const Duration(seconds: 10),
            receiveTimeout: const Duration(seconds: 15),
            contentType: 'application/json',
          ),
        );

  final Dio dio;

  Future<Map<String, dynamic>> health() async {
    final res = await dio.get('/v1/health');
    return Map<String, dynamic>.from(res.data as Map);
  }
}
