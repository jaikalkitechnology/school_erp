import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:intl/intl.dart';

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
            // Failures are shown by the FutureBuilders below.
            try {
              await Future.wait([_notifFuture!, _annFuture!]);
            } catch (_) {}
          },
          child: ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
            children: [
              FutureBuilder<List<Announcement>>(
                future: _annFuture,
                builder: (context, snap) {
                  if (snap.hasError) {
                    return Padding(
                      padding: const EdgeInsets.only(bottom: 16),
                      child: Text("Couldn't load the notice board: ${snap.error}",
                          style: t.bodyMedium?.copyWith(color: Theme.of(context).colorScheme.error)),
                    );
                  }
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
                                    DateFormat('d MMM yyyy, h:mm a').format(a.publishedAt!),
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
                  if (snap.hasError) {
                    return _LoadErrorCard(message: '${snap.error}', onRetry: _refresh);
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

/// Shown instead of "no notifications" when loading failed, so a server
/// problem doesn't look like an empty inbox.
class _LoadErrorCard extends StatelessWidget {
  const _LoadErrorCard({required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    final scheme = Theme.of(context).colorScheme;
    return Container(
      margin: const EdgeInsets.symmetric(vertical: 16),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: scheme.errorContainer,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text("Couldn't load notifications", style: t.titleMedium?.copyWith(color: scheme.onErrorContainer)),
          const SizedBox(height: 4),
          Text(message, style: t.bodyMedium?.copyWith(color: scheme.onErrorContainer)),
          const SizedBox(height: 8),
          OutlinedButton.icon(
            onPressed: onRetry,
            icon: const Icon(Icons.refresh),
            label: const Text('Retry'),
          ),
        ],
      ),
    );
  }
}
