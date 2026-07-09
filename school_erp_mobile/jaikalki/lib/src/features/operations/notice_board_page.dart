import 'package:flutter/material.dart';

import '../../api/operations_repository.dart';
import '../../core/service_locator.dart';
import '../../theme/brand.dart';

/// Notice board — audience-filtered list of school notices. Pinned
/// items float to the top with a saffron pin badge.
class NoticeBoardPage extends StatefulWidget {
  const NoticeBoardPage({super.key});

  @override
  State<NoticeBoardPage> createState() => _NoticeBoardPageState();
}

class _NoticeBoardPageState extends State<NoticeBoardPage> {
  late Future<List<NoticeItem>> _future;

  @override
  void initState() {
    super.initState();
    _future = locator<OperationsRepository>().notices();
  }

  Future<void> _refresh() async {
    setState(() {
      _future = locator<OperationsRepository>().notices();
    });
    await _future;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Notices')),
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: FutureBuilder<List<NoticeItem>>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState != ConnectionState.done) {
              return const Center(child: CircularProgressIndicator());
            }
            final rows = snap.data ?? const <NoticeItem>[];
            if (rows.isEmpty) {
              return ListView(children: const [
                SizedBox(height: 160),
                Center(
                  child: Padding(
                    padding: EdgeInsets.all(24),
                    child: Text(
                      'No notices on the board right now.',
                      textAlign: TextAlign.center,
                      style: TextStyle(color: JaikalkiBrand.textSecondary),
                    ),
                  ),
                ),
              ]);
            }
            return ListView.separated(
              padding: const EdgeInsets.all(12),
              itemCount: rows.length,
              separatorBuilder: (_, __) => const SizedBox(height: 10),
              itemBuilder: (_, i) {
                final n = rows[i];
                return Card(
                  child: Padding(
                    padding: const EdgeInsets.all(14),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            if (n.isPinned)
                              Container(
                                margin: const EdgeInsets.only(right: 6),
                                padding: const EdgeInsets.symmetric(
                                    horizontal: 6, vertical: 2),
                                decoration: BoxDecoration(
                                  color: JaikalkiBrand.saffronPale,
                                  borderRadius: BorderRadius.circular(4),
                                ),
                                child: const Text(
                                  'PINNED',
                                  style: TextStyle(
                                    fontSize: 9,
                                    fontWeight: FontWeight.w800,
                                    color: JaikalkiBrand.saffronDarker,
                                    letterSpacing: 1,
                                  ),
                                ),
                              ),
                            Expanded(
                              child: Text(
                                n.title,
                                style: const TextStyle(
                                  fontWeight: FontWeight.w700,
                                  fontSize: 15,
                                ),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 6),
                        Text(
                          n.body,
                          style: const TextStyle(fontSize: 13, height: 1.4),
                        ),
                        const SizedBox(height: 8),
                        Row(
                          children: [
                            Text(
                              n.audience.toUpperCase(),
                              style: const TextStyle(
                                fontSize: 10,
                                letterSpacing: 1,
                                color: JaikalkiBrand.textSecondary,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                            const Spacer(),
                            if (n.publishedAt != null)
                              Text(
                                _formatDate(n.publishedAt!),
                                style: const TextStyle(
                                  fontSize: 11,
                                  color: JaikalkiBrand.textSecondary,
                                ),
                              ),
                          ],
                        ),
                      ],
                    ),
                  ),
                );
              },
            );
          },
        ),
      ),
    );
  }
}

String _formatDate(String iso) {
  final d = DateTime.tryParse(iso);
  if (d == null) return iso;
  return '${d.year}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';
}
