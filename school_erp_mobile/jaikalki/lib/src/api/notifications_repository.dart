import 'package:dio/dio.dart';

import 'api_client.dart';

/// Server timestamps are UTC but sent without a zone ("2026-10-22T09:00:00").
/// DateTime.parse would read that as phone-local time, so read it as UTC
/// and convert to local.
DateTime parseServerTime(String s) {
  final hasZone = RegExp(r'([zZ]|[+-]\d\d:?\d\d)$').hasMatch(s);
  return DateTime.parse(hasZone ? s : '${s}Z').toLocal();
}

/// A load failure the page can show instead of looking empty.
class LoadError implements Exception {
  LoadError(this.message);
  final String message;

  factory LoadError.from(DioException e) {
    final code = e.response?.statusCode;
    final data = e.response?.data;
    final detail = data is Map && data['detail'] is String ? data['detail'] as String : null;
    if (code == null) {
      return LoadError("Couldn't reach the server. Check your internet connection.");
    }
    return LoadError('Server error $code${detail != null ? ': $detail' : ''}');
  }

  @override
  String toString() => message;
}

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
        createdAt: parseServerTime(j['created_at'] as String),
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
    } on DioException catch (e) {
      // Surface it: an empty list here used to hide server errors.
      throw LoadError.from(e);
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
        publishedAt: j['published_at'] == null ? null : parseServerTime(j['published_at'] as String),
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
    } on DioException catch (e) {
      throw LoadError.from(e);
    }
  }
}
