import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../../api/api_client.dart';
import '../../api/notifications_repository.dart';
import '../../core/service_locator.dart';
import '../../core/settings_cubit.dart';
import '../../theme/brand.dart';

class NotificationsPage extends StatefulWidget {
  const NotificationsPage({super.key});

  @override
  State<NotificationsPage> createState() => _NotificationsPageState();
}

class _NotificationsPageState extends State<NotificationsPage> {
  late final NotificationsRepository _repo;
  late final AnnouncementsRepository _announcements;
  Future<List<NotificationItem>>? _notifFuture;
  Future<List<Announcement>>? _annFuture;

  @override
  void initState() {
    super.initState();
    _repo = NotificationsRepository(locator<ApiClient>());
    _announcements = AnnouncementsRepository(locator<ApiClient>());
    _refresh();
  }

  void _refresh() {
    setState(() {
      _notifFuture = _repo.list();
      _annFuture = _announcements.list();
    });
  }

  Future<void> _markAllRead() async {
    final n = await _repo.markAllRead();
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('Marked $n notifications as read.'), behavior: SnackBarBehavior.floating),
    );
    _refresh();
  }

  @override
  Widget build(BuildContext context) {
    return BlocBuilder<SettingsCubit, SettingsState>(
      builder: (context, settings) {
        final t = Theme.of(context).textTheme;
        return RefreshIndicator(
          onRefresh: () async {
            _refresh();
            await Future.wait([_notifFuture!, _annFuture!]);
          },
          child: ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
            children: [
              FutureBuilder<List<Announcement>>(
                future: _annFuture,
                builder: (context, snap) {
                  final items = snap.data ?? const [];
                  if (items.isEmpty) return const SizedBox.shrink();
                  return Padding(
                    padding: const EdgeInsets.only(bottom: 16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('NOTICE BOARD',
                            style: t.labelSmall?.copyWith(color: JaikalkiBrand.saffronDark)),
                        const SizedBox(height: 8),
                        for (final a in items.take(5))
                          Container(
                            margin: const EdgeInsets.only(bottom: 8),
                            padding: const EdgeInsets.all(14),
                            decoration: BoxDecoration(
                              color: Theme.of(context).colorScheme.surface,
                              borderRadius: BorderRadius.circular(16),
                              border: Border.all(color: Theme.of(context).colorScheme.outline),
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    if (a.isPinned)
                                      const Padding(
                                        padding: EdgeInsets.only(right: 6),
                                        child: Icon(Icons.push_pin, size: 14, color: JaikalkiBrand.saffron),
                                      ),
                                    Expanded(child: Text(a.title, style: t.titleMedium)),
                                  ],
                                ),
                                const SizedBox(height: 4),
                                Text(a.body, style: t.bodyLarge),
                                if (a.publishedAt != null) ...[
                                  const SizedBox(height: 6),
                                  Text(
                                    a.publishedAt!.toLocal().toString().split('.').first,
                                    style: t.bodyMedium?.copyWith(fontSize: 11),
                                  ),
                                ],
                              ],
                            ),
                          ),
                      ],
                    ),
                  );
                },
              ),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text('NOTIFICATIONS',
                      style: t.labelSmall?.copyWith(color: JaikalkiBrand.saffronDark)),
                  TextButton(
                    onPressed: _markAllRead,
                    child: const Text('Mark all read'),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              FutureBuilder<List<NotificationItem>>(
                future: _notifFuture,
                builder: (context, snap) {
                  if (snap.connectionState != ConnectionState.done) {
                    return const Padding(
                      padding: EdgeInsets.all(40),
                      child: Center(child: CircularProgressIndicator()),
                    );
                  }
                  final items = snap.data ?? const [];
                  if (items.isEmpty) {
                    return Padding(
                      padding: const EdgeInsets.symmetric(vertical: 32),
                      child: Center(child: Text(settings.strings.notificationsEmpty, style: t.bodyLarge)),
                    );
                  }
                  return Column(
                    children: items.map((n) {
                      return GestureDetector(
                        onTap: () async {
                          if (n.read) return;
                          await _repo.markRead(n.id);
                          _refresh();
                        },
                        child: Container(
                          margin: const EdgeInsets.only(bottom: 8),
                          padding: const EdgeInsets.all(14),
                          decoration: BoxDecoration(
                            color: n.read
                                ? Theme.of(context).colorScheme.surfaceContainerHighest
                                : Theme.of(context).colorScheme.surface,
                            borderRadius: BorderRadius.circular(16),
                            border: Border.all(
                              color: n.read
                                  ? Theme.of(context).colorScheme.outline
                                  : JaikalkiBrand.saffronPale,
                            ),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                children: [
                                  Text(n.title.toUpperCase(),
                                      style: t.labelSmall?.copyWith(color: JaikalkiBrand.saffronDark)),
                                  Text(_relative(n.createdAt),
                                      style: t.bodyMedium?.copyWith(fontSize: 11)),
                                ],
                              ),
                              const SizedBox(height: 4),
                              Text(n.body, style: t.bodyLarge),
                            ],
                          ),
                        ),
                      );
                    }).toList(),
                  );
                },
              ),
            ],
          ),
        );
      },
    );
  }

  String _relative(DateTime dt) {
    final diff = DateTime.now().difference(dt);
    if (diff.inMinutes < 1) return 'just now';
    if (diff.inMinutes < 60) return '${diff.inMinutes}m';
    if (diff.inHours < 24) return '${diff.inHours}h';
    return '${diff.inDays}d';
  }
}
