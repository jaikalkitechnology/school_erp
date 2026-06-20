import 'package:flutter/material.dart';

import '../../api/auth_repository.dart';
import '../../api/messages_repository.dart';
import '../../core/service_locator.dart';
import '../../theme/brand.dart';

/// 1-on-1 messages inbox for the signed-in user (parent or admin
/// reading on mobile). Renders teacher → parent / teacher → admin
/// messages that land in the platform-level `messages` table, and lets
/// the recipient tap a thread to read + reply.
class MessagesPage extends StatefulWidget {
  const MessagesPage({super.key});

  @override
  State<MessagesPage> createState() => _MessagesPageState();
}

class _MessagesPageState extends State<MessagesPage> {
  late Future<_InboxBundle> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<_InboxBundle> _load() async {
    final repo = locator<MessagesRepository>();
    final me = await locator<AuthRepository>().me();
    final inbox = await repo.inbox();
    final sent = await repo.sent();
    return _InboxBundle(inbox: inbox, sent: sent, meUserId: me?.id ?? 0);
  }

  Future<void> _reload() async {
    setState(() => _future = _load());
    await _future;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Messages')),
      body: FutureBuilder<_InboxBundle>(
        future: _future,
        builder: (context, snap) {
          if (snap.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          final b = snap.data ??
              _InboxBundle(inbox: const [], sent: const [], meUserId: 0);
          final threads = _threadList(b);
          if (threads.isEmpty) {
            return RefreshIndicator(
              onRefresh: _reload,
              child: ListView(children: const [
                SizedBox(height: 80),
                Center(
                  child: Padding(
                    padding: EdgeInsets.all(24),
                    child: Text(
                      'No messages yet.\nWhen a teacher writes to you, '
                      "it'll appear here.",
                      textAlign: TextAlign.center,
                      style: TextStyle(color: JaikalkiBrand.textSecondary),
                    ),
                  ),
                ),
              ]),
            );
          }
          return RefreshIndicator(
            onRefresh: _reload,
            child: ListView.separated(
              padding: const EdgeInsets.symmetric(vertical: 8),
              itemCount: threads.length,
              separatorBuilder: (_, __) =>
                  const Divider(height: 0, indent: 72),
              itemBuilder: (_, i) {
                final th = threads[i];
                return _ThreadTile(
                  thread: th,
                  onTap: () => Navigator.of(context).push(
                    MaterialPageRoute(
                      builder: (_) => _MessageThreadPage(
                        peerUserId: th.peerUserId,
                        peerName: th.peerName,
                        meUserId: b.meUserId,
                      ),
                    ),
                  ).then((_) => _reload()),
                );
              },
            ),
          );
        },
      ),
    );
  }

  List<_Thread> _threadList(_InboxBundle b) {
    final Map<int, _Thread> grouped = {};
    for (final m in b.inbox) {
      final peer = m.senderUserId ?? 0;
      if (peer == 0) continue;
      grouped.putIfAbsent(
        peer,
        () => _Thread(peerUserId: peer, peerName: m.senderName ?? 'School'),
      );
      grouped[peer]!.add(m, fromMe: false);
    }
    for (final m in b.sent) {
      final peer = m.recipientUserId;
      grouped.putIfAbsent(peer, () => _Thread(peerUserId: peer, peerName: 'You'));
      grouped[peer]!.add(m, fromMe: true);
    }
    final list = grouped.values.toList();
    list.sort((a, b) =>
        (b.lastAt ?? '').compareTo(a.lastAt ?? ''));
    return list;
  }
}

class _InboxBundle {
  const _InboxBundle({
    required this.inbox,
    required this.sent,
    required this.meUserId,
  });
  final List<MessageItem> inbox;
  final List<MessageItem> sent;
  final int meUserId;
}

class _Thread {
  _Thread({required this.peerUserId, required this.peerName});
  final int peerUserId;
  String peerName;
  String? lastBody;
  String? lastAt;
  int unread = 0;

  void add(MessageItem m, {required bool fromMe}) {
    if (!fromMe && (peerName.isEmpty || peerName == 'School')) {
      peerName = m.senderName ?? peerName;
    }
    final at = m.createdAt ?? '';
    if (lastAt == null || at.compareTo(lastAt!) > 0) {
      lastAt = at;
      lastBody = (fromMe ? 'You: ' : '') + m.body;
    }
    if (!fromMe && !m.isRead) unread += 1;
  }
}

class _ThreadTile extends StatelessWidget {
  const _ThreadTile({required this.thread, required this.onTap});
  final _Thread thread;
  final VoidCallback onTap;

  String _initials(String n) {
    final parts = n.trim().split(RegExp(r'\s+'));
    if (parts.isEmpty || parts[0].isEmpty) return '?';
    if (parts.length == 1) return parts[0][0].toUpperCase();
    return '${parts.first[0]}${parts.last[0]}'.toUpperCase();
  }

  @override
  Widget build(BuildContext context) {
    return ListTile(
      onTap: onTap,
      leading: CircleAvatar(
        backgroundColor: JaikalkiBrand.teal,
        foregroundColor: Colors.white,
        child: Text(
          _initials(thread.peerName),
          style: const TextStyle(fontWeight: FontWeight.w700),
        ),
      ),
      title: Text(
        thread.peerName,
        style: TextStyle(
          fontWeight:
              thread.unread > 0 ? FontWeight.w800 : FontWeight.w600,
          color: JaikalkiBrand.indigoDark,
        ),
      ),
      subtitle: thread.lastBody == null
          ? null
          : Text(
              thread.lastBody!,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontSize: 12),
            ),
      trailing: thread.unread > 0
          ? Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
              decoration: BoxDecoration(
                color: JaikalkiBrand.saffron,
                borderRadius: BorderRadius.circular(10),
              ),
              child: Text(
                '${thread.unread}',
                style: const TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.w700,
                  fontSize: 11,
                ),
              ),
            )
          : const Icon(Icons.chevron_right,
              color: JaikalkiBrand.textSecondary),
    );
  }
}

class _MessageThreadPage extends StatefulWidget {
  const _MessageThreadPage({
    required this.peerUserId,
    required this.peerName,
    required this.meUserId,
  });
  final int peerUserId;
  final String peerName;
  final int meUserId;

  @override
  State<_MessageThreadPage> createState() => _MessageThreadPageState();
}

class _MessageThreadPageState extends State<_MessageThreadPage> {
  final _input = TextEditingController();
  final _scroll = ScrollController();
  late Future<List<MessageItem>> _future;
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

  Future<List<MessageItem>> _load() async {
    final repo = locator<MessagesRepository>();
    final inbox = await repo.inbox();
    final sent = await repo.sent();
    final mine = <MessageItem>[];
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
          await repo.markRead(m.id);
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
      await locator<MessagesRepository>().send(
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
              child: FutureBuilder<List<MessageItem>>(
                future: _future,
                builder: (context, snap) {
                  if (snap.connectionState != ConnectionState.done) {
                    return const Center(child: CircularProgressIndicator());
                  }
                  final msgs = snap.data ?? const <MessageItem>[];
                  if (msgs.isEmpty) {
                    return ListView(children: const [
                      SizedBox(height: 80),
                      Center(
                        child: Padding(
                          padding: EdgeInsets.all(24),
                          child: Text(
                            "No messages yet.\nReply below.",
                            textAlign: TextAlign.center,
                            style:
                                TextStyle(color: JaikalkiBrand.textSecondary),
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
                        width: 44, height: 44,
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
  final MessageItem message;
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
