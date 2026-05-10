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

  final int id;
  final String title;
  final String body;
  final String kind;
  final DateTime createdAt;
  final String? deeplink;
  final bool read;

  factory NotificationItem.fromJson(Map<String, dynamic> j) => NotificationItem(
        id: (j['id'] as num).toInt(),
        title: j['title'] as String,
        body: j['body'] as String,
        kind: j['kind'] as String,
        createdAt: DateTime.parse(j['created_at'] as String),
        deeplink: j['deeplink'] as String?,
        read: j['read_at'] != null,
      );
}

class NotificationsRepository {
  NotificationsRepository(this._api);
  final ApiClient _api;

  Future<List<NotificationItem>> list({bool onlyUnread = false}) async {
    try {
      final res = await _api.dio.get<List<dynamic>>(
        '/v1/notifications',
        queryParameters: {if (onlyUnread) 'only_unread': true},
      );
      return (res.data ?? const [])
          .map((e) => NotificationItem.fromJson(e as Map<String, dynamic>))
          .toList();
    } on DioException {
      return const [];
    }
  }

  Future<void> markRead(int id) async {
    try {
      await _api.dio.post<dynamic>('/v1/notifications/$id/read');
    } on DioException {
      // best-effort; ignore
    }
  }

  Future<int> markAllRead() async {
    try {
      final res = await _api.dio.post<Map<String, dynamic>>('/v1/notifications/read-all');
      return (res.data?['marked'] as num?)?.toInt() ?? 0;
    } on DioException {
      return 0;
    }
  }
}

class Announcement {
  Announcement({required this.id, required this.title, required this.body, required this.isPinned, required this.publishedAt});
  final int id;
  final String title;
  final String body;
  final bool isPinned;
  final DateTime? publishedAt;

  factory Announcement.fromJson(Map<String, dynamic> j) => Announcement(
        id: j['id'] as int,
        title: j['title'] as String,
        body: j['body'] as String,
        isPinned: (j['is_pinned'] as bool?) ?? false,
        publishedAt: j['published_at'] == null ? null : DateTime.parse(j['published_at'] as String),
      );
}

class AnnouncementsRepository {
  AnnouncementsRepository(this._api);
  final ApiClient _api;

  Future<List<Announcement>> list() async {
    try {
      final res = await _api.dio.get<List<dynamic>>('/v1/announcements');
      return (res.data ?? const [])
          .map((e) => Announcement.fromJson(e as Map<String, dynamic>))
          .toList();
    } on DioException {
      return const [];
    }
  }
}
