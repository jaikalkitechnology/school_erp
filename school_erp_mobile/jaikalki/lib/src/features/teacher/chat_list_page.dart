import 'package:flutter/material.dart';

import '../../api/teacher_repository.dart';
import '../../core/service_locator.dart';
import '../../theme/brand.dart';
import 'chat_thread_page.dart';

/// Chat home for teachers: shows the list of available contacts
/// (admins + parents of accessible students) and the unread inbox
/// indicator per contact. Tapping a contact opens a 1-on-1 thread.
class ChatListPage extends StatefulWidget {
  const ChatListPage({super.key});

  @override
  State<ChatListPage> createState() => _ChatListPageState();
}

class _ChatListPageState extends State<ChatListPage>
    with SingleTickerProviderStateMixin {
  late final TabController _tab;
  late Future<_ChatBundle> _future;

  @override
  void initState() {
    super.initState();
    _tab = TabController(length: 2, vsync: this);
    _future = _load();
  }

  @override
  void dispose() {
    _tab.dispose();
    super.dispose();
  }

  Future<_ChatBundle> _load() async {
    final repo = locator<TeacherRepository>();
    final contacts = await repo.chatContacts();
    final inbox = await repo.inbox();
    final me = await repo.me();
    return _ChatBundle(
      contacts: contacts,
      inbox: inbox,
      meUserId: me.profile.userId,
    );
  }

  Future<void> _reload() async {
    setState(() => _future = _load());
    await _future;
  }

  void _openThread(_ChatBundle b, ChatContact c) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => ChatThreadPage(
          peerUserId: c.userId,
          peerName: c.fullName,
          meUserId: b.meUserId,
        ),
      ),
    ).then((_) => _reload());
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Chat'),
        bottom: TabBar(
          controller: _tab,
          labelColor: JaikalkiBrand.saffron,
          unselectedLabelColor: JaikalkiBrand.textSecondary,
          indicatorColor: JaikalkiBrand.saffron,
          tabs: const [
            Tab(text: 'Admins'),
            Tab(text: 'Parents'),
          ],
        ),
      ),
      body: FutureBuilder<_ChatBundle>(
        future: _future,
        builder: (context, snap) {
          if (snap.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          final b = snap.data ?? _ChatBundle(
            contacts: const [], inbox: const [], meUserId: 0,
          );
          final admins =
              b.contacts.where((c) => c.kind == 'admin').toList();
          final parents =
              b.contacts.where((c) => c.kind == 'parent').toList();
          return RefreshIndicator(
            onRefresh: _reload,
            child: TabBarView(
              controller: _tab,
              children: [
                _ContactList(
                  contacts: admins,
                  bundle: b,
                  onTap: (c) => _openThread(b, c),
                  emptyText: 'No school admins available.',
                ),
                _ContactList(
                  contacts: parents,
                  bundle: b,
                  onTap: (c) => _openThread(b, c),
                  emptyText: 'No parent contacts yet — they appear once '
                      'students are assigned to your sections.',
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}

class _ChatBundle {
  const _ChatBundle({
    required this.contacts,
    required this.inbox,
    required this.meUserId,
  });
  final List<ChatContact> contacts;
  final List<ChatMessage> inbox;
  final int meUserId;
}

class _ContactList extends StatelessWidget {
  const _ContactList({
    required this.contacts,
    required this.bundle,
    required this.onTap,
    required this.emptyText,
  });
  final List<ChatContact> contacts;
  final _ChatBundle bundle;
  final void Function(ChatContact) onTap;
  final String emptyText;

  int _unreadFrom(int userId) => bundle.inbox
      .where((m) => m.senderUserId == userId && !m.isRead)
      .length;

  ChatMessage? _latest(int userId) {
    final mine = bundle.inbox
        .where((m) => m.senderUserId == userId)
        .toList();
    if (mine.isEmpty) return null;
    mine.sort((a, b) => (b.createdAt ?? '').compareTo(a.createdAt ?? ''));
    return mine.first;
  }

  String _initials(String n) {
    final parts = n.trim().split(RegExp(r'\s+'));
    if (parts.isEmpty || parts[0].isEmpty) return '?';
    if (parts.length == 1) return parts[0][0].toUpperCase();
    return '${parts.first[0]}${parts.last[0]}'.toUpperCase();
  }

  @override
  Widget build(BuildContext context) {
    if (contacts.isEmpty) {
      return ListView(children: [
        const SizedBox(height: 80),
        Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Text(
              emptyText,
              textAlign: TextAlign.center,
              style: const TextStyle(color: JaikalkiBrand.textSecondary),
            ),
          ),
        ),
      ]);
    }
    return ListView.separated(
      padding: const EdgeInsets.symmetric(vertical: 8),
      itemCount: contacts.length,
      separatorBuilder: (_, __) => const Divider(height: 0, indent: 72),
      itemBuilder: (_, i) {
        final c = contacts[i];
        final unread = _unreadFrom(c.userId);
        final latest = _latest(c.userId);
        return ListTile(
          leading: CircleAvatar(
            backgroundColor: c.kind == 'admin'
                ? JaikalkiBrand.indigoDark
                : JaikalkiBrand.teal,
            foregroundColor: Colors.white,
            child: Text(
              _initials(c.fullName),
              style: const TextStyle(fontWeight: FontWeight.w700),
            ),
          ),
          title: Text(
            c.fullName,
            style: TextStyle(
              fontWeight: unread > 0 ? FontWeight.w800 : FontWeight.w600,
              color: JaikalkiBrand.indigoDark,
            ),
          ),
          subtitle: Text(
            latest?.body ??
                (c.phone ?? c.email ?? 'Tap to start a conversation'),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(fontSize: 12),
          ),
          trailing: unread > 0
              ? Container(
                  padding: const EdgeInsets.symmetric(
                      horizontal: 8, vertical: 2),
                  decoration: BoxDecoration(
                    color: JaikalkiBrand.saffron,
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Text(
                    '$unread',
                    style: const TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.w700,
                      fontSize: 11,
                    ),
                  ),
                )
              : const Icon(Icons.chevron_right,
                  color: JaikalkiBrand.textSecondary),
          onTap: () => onTap(c),
        );
      },
    );
  }
}
