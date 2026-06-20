import 'package:dio/dio.dart';

import 'api_client.dart';

/// Thin wrapper around the platform-level /v1/messages router. Used by
/// the parent app (and potentially the future student app) to read
/// 1-on-1 messages teachers / admins have sent. The teacher app has
/// its own send/inbox helpers under [TeacherRepository] so it can
/// special-case the contact picker.
class MessagesRepository {
  MessagesRepository(this._api);
  final ApiClient _api;

  Future<List<MessageItem>> inbox() async {
    try {
      final res = await _api.dio.get<List<dynamic>>('/v1/messages');
      return (res.data ?? const [])
          .map((e) => MessageItem.fromJson(e as Map<String, dynamic>))
          .toList();
    } on DioException {
      return const [];
    }
  }

  Future<List<MessageItem>> sent() async {
    try {
      final res = await _api.dio.get<List<dynamic>>('/v1/messages/sent');
      return (res.data ?? const [])
          .map((e) => MessageItem.fromJson(e as Map<String, dynamic>))
          .toList();
    } on DioException {
      return const [];
    }
  }

  Future<MessageItem> send({
    required int recipientUserId,
    required String body,
    String? subject,
  }) async {
    final res = await _api.dio.post<Map<String, dynamic>>(
      '/v1/messages',
      data: {
        'recipient_user_id': recipientUserId,
        'body': body,
        if (subject != null && subject.isNotEmpty) 'subject': subject,
      },
    );
    return MessageItem.fromJson(res.data ?? const {});
  }

  Future<void> markRead(int messageId) async {
    try {
      await _api.dio.post('/v1/messages/$messageId/read');
    } on DioException {
      // Best-effort.
    }
  }
}

class MessageItem {
  const MessageItem({
    required this.id,
    required this.senderUserId,
    required this.recipientUserId,
    required this.subject,
    required this.body,
    required this.senderName,
    required this.readAt,
    required this.createdAt,
  });

  final int id;
  final int? senderUserId;
  final int recipientUserId;
  final String? subject;
  final String body;
  final String? senderName;
  final String? readAt;
  final String? createdAt;

  bool get isRead => readAt != null;

  factory MessageItem.fromJson(Map<String, dynamic> j) => MessageItem(
        id: (j['id'] as num?)?.toInt() ?? 0,
        senderUserId: (j['sender_user_id'] as num?)?.toInt(),
        recipientUserId: (j['recipient_user_id'] as num?)?.toInt() ?? 0,
        subject: j['subject'] as String?,
        body: (j['body'] as String?) ?? '',
        senderName: (j['sender_name'] as String?) ??
            (j['sender_full_name'] as String?),
        readAt: j['read_at'] as String?,
        createdAt: j['created_at'] as String?,
      );
}
