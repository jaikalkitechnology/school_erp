import 'package:flutter/material.dart';

import '../../api/teacher_repository.dart';
import '../../core/service_locator.dart';
import '../../theme/brand.dart';

/// 1-on-1 chat thread between the logged-in teacher and a single
/// counterparty (admin / parent / student). Loads inbox + sent, filters
/// to the pair, renders as a chat bubble timeline, and lets the teacher
/// send a new message.
class ChatThreadPage extends StatefulWidget {
  const ChatThreadPage({
    super.key,
    required this.peerUserId,
    required this.peerName,
    required this.meUserId,
  });

  final int peerUserId;
  final String peerName;
  final int meUserId;

  @override
  State<ChatThreadPage> createState() => _ChatThreadPageState();
}

class _ChatThreadPageState extends State<ChatThreadPage> {
  final _input = TextEditingController();
  final _scroll = ScrollController();
  late Future<List<ChatMessage>> _future;
  bool _sending = false;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  @override
  void dispose() {
    _input.dispose();
    _scroll.dispose();
    super.dispose();
  }

  Future<List<ChatMessage>> _load() async {
    final repo = locator<TeacherRepository>();
    final inbox = await repo.inbox();
    final sent = await repo.sent();
    final mine = <ChatMessage>[];
    for (final m in inbox) {
      if (m.senderUserId == widget.peerUserId) mine.add(m);
    }
    for (final m in sent) {
      if (m.recipientUserId == widget.peerUserId) mine.add(m);
    }
    mine.sort((a, b) => (a.createdAt ?? '').compareTo(b.createdAt ?? ''));
    for (final m in mine) {
      if (!m.isRead && m.senderUserId == widget.peerUserId) {
        try {
          await repo.markMessageRead(m.id);
        } catch (_) {}
      }
    }
    return mine;
  }

  Future<void> _reload() async {
    setState(() => _future = _load());
    await _future;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scroll.hasClients) {
        _scroll.jumpTo(_scroll.position.maxScrollExtent);
      }
    });
  }

  Future<void> _send() async {
    final body = _input.text.trim();
    if (body.isEmpty || _sending) return;
    setState(() => _sending = true);
    try {
      await locator<TeacherRepository>().sendMessage(
        recipientUserId: widget.peerUserId,
        body: body,
      );
      _input.clear();
      await _reload();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to send: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(widget.peerName)),
      body: Column(
        children: [
          Expanded(
            child: RefreshIndicator(
              onRefresh: _reload,
              child: FutureBuilder<List<ChatMessage>>(
                future: _future,
                builder: (context, snap) {
                  if (snap.connectionState != ConnectionState.done) {
                    return const Center(child: CircularProgressIndicator());
                  }
                  final msgs = snap.data ?? const <ChatMessage>[];
                  if (msgs.isEmpty) {
                    return ListView(children: const [
                      SizedBox(height: 80),
                      Center(
                        child: Padding(
                          padding: EdgeInsets.all(24),
                          child: Text(
                            'No messages yet.\nSay hello below.',
                            textAlign: TextAlign.center,
                            style: TextStyle(
                              color: JaikalkiBrand.textSecondary,
                            ),
                          ),
                        ),
                      ),
                    ]);
                  }
                  WidgetsBinding.instance.addPostFrameCallback((_) {
                    if (_scroll.hasClients) {
                      _scroll.jumpTo(_scroll.position.maxScrollExtent);
                    }
                  });
                  return ListView.builder(
                    controller: _scroll,
                    padding: const EdgeInsets.fromLTRB(12, 12, 12, 12),
                    itemCount: msgs.length,
                    itemBuilder: (_, i) {
                      final m = msgs[i];
                      final mine = m.senderUserId == widget.meUserId;
                      return _Bubble(message: m, mine: mine);
                    },
                  );
                },
              ),
            ),
          ),
          SafeArea(
            top: false,
            child: Container(
              padding: const EdgeInsets.fromLTRB(12, 8, 12, 8),
              decoration: const BoxDecoration(
                color: JaikalkiBrand.warmWhite,
                border: Border(
                  top: BorderSide(color: JaikalkiBrand.saffronPale),
                ),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Expanded(
                    child: TextField(
                      controller: _input,
                      enabled: !_sending,
                      minLines: 1,
                      maxLines: 4,
                      textInputAction: TextInputAction.send,
                      decoration: const InputDecoration(
                        hintText: 'Type a message…',
                        contentPadding: EdgeInsets.symmetric(
                            horizontal: 14, vertical: 10),
                      ),
                      onSubmitted: (_) => _send(),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Material(
                    color: JaikalkiBrand.saffron,
                    shape: const CircleBorder(),
                    child: InkWell(
                      customBorder: const CircleBorder(),
                      onTap: _sending ? null : _send,
                      child: SizedBox(
                        width: 44,
                        height: 44,
                        child: Center(
                          child: _sending
                              ? const SizedBox(
                                  width: 18, height: 18,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2, color: Colors.white,
                                  ),
                                )
                              : const Icon(Icons.send, color: Colors.white),
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _Bubble extends StatelessWidget {
  const _Bubble({required this.message, required this.mine});
  final ChatMessage message;
  final bool mine;

  String _time(String? iso) {
    if (iso == null || iso.isEmpty) return '';
    try {
      final dt = DateTime.parse(iso).toLocal();
      final h = dt.hour.toString().padLeft(2, '0');
      final m = dt.minute.toString().padLeft(2, '0');
      return '$h:$m';
    } catch (_) {
      return '';
    }
  }

  @override
  Widget build(BuildContext context) {
    final bg = mine ? JaikalkiBrand.saffron : JaikalkiBrand.warmWhite;
    final fg = mine ? Colors.white : JaikalkiBrand.indigoDark;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment:
            mine ? MainAxisAlignment.end : MainAxisAlignment.start,
        children: [
          ConstrainedBox(
            constraints: BoxConstraints(
              maxWidth: MediaQuery.of(context).size.width * 0.72,
            ),
            child: Container(
              padding: const EdgeInsets.symmetric(
                  horizontal: 12, vertical: 8),
              decoration: BoxDecoration(
                color: bg,
                borderRadius: BorderRadius.only(
                  topLeft: const Radius.circular(14),
                  topRight: const Radius.circular(14),
                  bottomLeft: Radius.circular(mine ? 14 : 2),
                  bottomRight: Radius.circular(mine ? 2 : 14),
                ),
                border: Border.all(
                  color: mine
                      ? JaikalkiBrand.saffronDark
                      : JaikalkiBrand.saffronPale,
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (message.subject != null &&
                      message.subject!.isNotEmpty) ...[
                    Text(
                      message.subject!,
                      style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w800,
                        letterSpacing: 0.4,
                        color: mine
                            ? Colors.white.withOpacity(0.9)
                            : JaikalkiBrand.textSecondary,
                      ),
                    ),
                    const SizedBox(height: 2),
                  ],
                  Text(
                    message.body,
                    style: TextStyle(fontSize: 14, height: 1.35, color: fg),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    _time(message.createdAt),
                    style: TextStyle(
                      fontSize: 10,
                      color: mine
                          ? Colors.white.withOpacity(0.85)
                          : JaikalkiBrand.textSecondary,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
