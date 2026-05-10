import 'package:dio/dio.dart';

import 'api_client.dart';

class NotificationItem {
  NotificationItem({
    required this.id,
    required this.title,
    required this.body,
    required this.kind,
    required this.createdAt,
    this.deeplink,
    this.read = false,
  });

  final String id;
  final String title;
  final String body;
  final String kind;
  final DateTime createdAt;
  final String? deeplink;
  final bool read;

  factory NotificationItem.fromJson(Map<String, dynamic> j) => NotificationItem(
        id: j['id'] as String,
        title: j['title'] as String,
        body: j['body'] as String,
        kind: j['kind'] as String,
        createdAt: DateTime.parse(j['created_at'] as String),
        deeplink: j['deeplink'] as String?,
        read: (j['read'] as bool?) ?? false,
      );
}

class NotificationsRepository {
  NotificationsRepository(this._api);
  final ApiClient _api;

  Future<List<NotificationItem>> list() async {
    try {
      final res = await _api.dio.get<List<dynamic>>('/v1/notifications');
      return (res.data ?? const [])
          .map((e) => NotificationItem.fromJson(e as Map<String, dynamic>))
          .toList();
    } on DioException {
      return const [];
    }
  }
}
