import 'package:flutter/material.dart';

import '../../api/principal_repository.dart';
import '../../core/service_locator.dart';
import '../../theme/brand.dart';

/// Recent serious behaviour notes — last 7 days by default. Powers
/// the Discipline tab.
class PrincipalDisciplinePage extends StatefulWidget {
  const PrincipalDisciplinePage({super.key});

  @override
  State<PrincipalDisciplinePage> createState() =>
      _PrincipalDisciplinePageState();
}

class _PrincipalDisciplinePageState extends State<PrincipalDisciplinePage> {
  late Future<List<DisciplineRow>> _future;
  int _days = 7;

  @override
  void initState() {
    super.initState();
    _future = locator<PrincipalRepository>().recentDiscipline(daysBack: _days);
  }

  Future<void> _refresh() async {
    setState(() {
      _future =
          locator<PrincipalRepository>().recentDiscipline(daysBack: _days);
    });
    await _future;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Discipline'),
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(48),
          child: Padding(
            padding: const EdgeInsets.fromLTRB(12, 4, 12, 10),
            child: SegmentedButton<int>(
              segments: const [
                ButtonSegment(value: 7, label: Text('7 days')),
                ButtonSegment(value: 30, label: Text('30 days')),
                ButtonSegment(value: 90, label: Text('90 days')),
              ],
              selected: {_days},
              onSelectionChanged: (s) {
                setState(() => _days = s.first);
                _refresh();
              },
            ),
          ),
        ),
      ),
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: FutureBuilder<List<DisciplineRow>>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState != ConnectionState.done) {
              return const Center(child: CircularProgressIndicator());
            }
            final rows = snap.data ?? const <DisciplineRow>[];
            if (rows.isEmpty) {
              return ListView(children: const [
                SizedBox(height: 160),
                Center(
                  child: Padding(
                    padding: EdgeInsets.all(24),
                    child: Text(
                      'No behaviour concerns logged in this window. \nThings are quiet.',
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
              separatorBuilder: (_, __) => const SizedBox(height: 8),
              itemBuilder: (_, i) {
                final r = rows[i];
                return Card(
                  child: Padding(
                    padding: const EdgeInsets.all(12),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            const Icon(Icons.warning_amber_outlined,
                                color: Color(0xFFC44419), size: 18),
                            const SizedBox(width: 6),
                            Expanded(
                              child: Text(
                                r.headline,
                                style: const TextStyle(
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                            ),
                            Text(r.occurredOn,
                                style: const TextStyle(
                                  fontSize: 11,
                                  color: JaikalkiBrand.textSecondary,
                                )),
                          ],
                        ),
                        const SizedBox(height: 4),
                        Text(
                          '${r.studentName} · by ${r.teacherName ?? "—"}',
                          style: const TextStyle(
                            fontSize: 12,
                            color: JaikalkiBrand.textSecondary,
                          ),
                        ),
                        if (r.detail != null && r.detail!.isNotEmpty) ...[
                          const SizedBox(height: 6),
                          Text(r.detail!),
                        ],
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
