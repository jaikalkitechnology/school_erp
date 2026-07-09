import 'package:flutter/material.dart';

import '../../api/operations_repository.dart';
import '../../core/service_locator.dart';
import '../../theme/brand.dart';

/// Sports & clubs — house leaderboard + upcoming events. Open to
/// everyone. Two tabs: Leaderboard (points ordered), Events
/// (upcoming first, then past).
class SportsPage extends StatefulWidget {
  const SportsPage({super.key});

  @override
  State<SportsPage> createState() => _SportsPageState();
}

class _SportsPageState extends State<SportsPage>
    with SingleTickerProviderStateMixin {
  late final TabController _tab;
  late Future<List<HouseRow>> _housesFuture;
  late Future<List<SportsEventRow>> _eventsFuture;

  @override
  void initState() {
    super.initState();
    _tab = TabController(length: 2, vsync: this);
    _housesFuture = locator<OperationsRepository>().sportsHouses();
    _eventsFuture = locator<OperationsRepository>().sportsEvents();
  }

  @override
  void dispose() {
    _tab.dispose();
    super.dispose();
  }

  Future<void> _refresh() async {
    setState(() {
      _housesFuture = locator<OperationsRepository>().sportsHouses();
      _eventsFuture = locator<OperationsRepository>().sportsEvents();
    });
    await Future.wait([_housesFuture, _eventsFuture]);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Sports & clubs'),
        bottom: TabBar(
          controller: _tab,
          tabs: const [
            Tab(text: 'Leaderboard'),
            Tab(text: 'Events'),
          ],
        ),
      ),
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: TabBarView(
          controller: _tab,
          children: [
            _LeaderboardTab(future: _housesFuture),
            _EventsTab(future: _eventsFuture),
          ],
        ),
      ),
    );
  }
}

class _LeaderboardTab extends StatelessWidget {
  const _LeaderboardTab({required this.future});
  final Future<List<HouseRow>> future;

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<HouseRow>>(
      future: future,
      builder: (context, snap) {
        if (snap.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        final rows = snap.data ?? const <HouseRow>[];
        if (rows.isEmpty) {
          return ListView(children: const [
            SizedBox(height: 160),
            Center(child: Text('No houses set up yet.')),
          ]);
        }
        final max = rows.first.points == 0 ? 1 : rows.first.points;
        return ListView.separated(
          padding: const EdgeInsets.all(12),
          itemCount: rows.length,
          separatorBuilder: (_, __) => const SizedBox(height: 8),
          itemBuilder: (_, i) {
            final r = rows[i];
            final color = _parseColor(r.color);
            final ratio = (r.points / max).clamp(0.0, 1.0);
            return Card(
              child: Padding(
                padding: const EdgeInsets.all(14),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        CircleAvatar(
                          radius: 14,
                          backgroundColor: color,
                          child: Text(
                            '${i + 1}',
                            style: const TextStyle(
                              color: Colors.white,
                              fontWeight: FontWeight.w800,
                            ),
                          ),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            r.name,
                            style: const TextStyle(
                              fontWeight: FontWeight.w800,
                              fontSize: 16,
                            ),
                          ),
                        ),
                        Text(
                          '${r.points} pts',
                          style: const TextStyle(
                            fontWeight: FontWeight.w800,
                            color: JaikalkiBrand.saffronDarker,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    ClipRRect(
                      borderRadius: BorderRadius.circular(4),
                      child: LinearProgressIndicator(
                        value: ratio,
                        minHeight: 8,
                        backgroundColor: color.withOpacity(0.15),
                        valueColor: AlwaysStoppedAnimation<Color>(color),
                      ),
                    ),
                    if (r.motto != null && r.motto!.isNotEmpty) ...[
                      const SizedBox(height: 6),
                      Text(
                        '“${r.motto!}”',
                        style: const TextStyle(
                          fontStyle: FontStyle.italic,
                          fontSize: 12,
                          color: JaikalkiBrand.textSecondary,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            );
          },
        );
      },
    );
  }
}

class _EventsTab extends StatelessWidget {
  const _EventsTab({required this.future});
  final Future<List<SportsEventRow>> future;

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<SportsEventRow>>(
      future: future,
      builder: (context, snap) {
        if (snap.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        final rows = snap.data ?? const <SportsEventRow>[];
        if (rows.isEmpty) {
          return ListView(children: const [
            SizedBox(height: 160),
            Center(child: Text('No events on the calendar.')),
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
                padding: const EdgeInsets.all(14),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            r.name,
                            style: const TextStyle(
                              fontWeight: FontWeight.w700,
                              fontSize: 15,
                            ),
                          ),
                        ),
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 6, vertical: 2),
                          decoration: BoxDecoration(
                            color: JaikalkiBrand.saffronPale,
                            borderRadius: BorderRadius.circular(4),
                          ),
                          child: Text(
                            r.kind.toUpperCase(),
                            style: const TextStyle(
                              fontSize: 9,
                              fontWeight: FontWeight.w800,
                              color: JaikalkiBrand.saffronDarker,
                              letterSpacing: 1,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 4),
                    Text(
                      [
                        r.startsOn,
                        if (r.endsOn != null && r.endsOn != r.startsOn) '→ ${r.endsOn}',
                        if (r.sport != null) '· ${r.sport}',
                        if (r.venue != null) '· ${r.venue}',
                      ].join(' '),
                      style: const TextStyle(
                        fontSize: 12,
                        color: JaikalkiBrand.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
            );
          },
        );
      },
    );
  }
}

Color _parseColor(String? s) {
  if (s == null || s.isEmpty) return JaikalkiBrand.saffron;
  final hex = s.replaceFirst('#', '');
  final v = int.tryParse(hex, radix: 16);
  if (v == null) {
    // Named colour fallback.
    const named = {
      'red': Color(0xFFDC2626),
      'blue': Color(0xFF2563EB),
      'green': Color(0xFF16A34A),
      'yellow': Color(0xFFEAB308),
      'orange': Color(0xFFEA580C),
      'purple': Color(0xFF7C3AED),
    };
    return named[s.toLowerCase()] ?? JaikalkiBrand.saffron;
  }
  return Color(hex.length == 6 ? 0xFF000000 | v : v);
}
