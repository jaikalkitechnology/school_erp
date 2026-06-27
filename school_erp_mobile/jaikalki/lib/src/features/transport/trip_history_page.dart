import 'package:flutter/material.dart';

import '../../api/parent_repository.dart';
import '../../core/children_cubit.dart';
import '../../core/service_locator.dart';
import '../../theme/brand.dart';

/// Last 30 days of bus trips on the child's route. Each row shows
/// date, phase, start/end time, direction, and the child's pickup +
/// drop boarding events inline. Pull-to-refresh; "Open in Maps" deep
/// link if the row carried lat/lng (not yet in the payload — slot
/// for the next iteration once we persist a polyline).
class TripHistoryPage extends StatefulWidget {
  const TripHistoryPage({super.key});

  @override
  State<TripHistoryPage> createState() => _TripHistoryPageState();
}

class _TripHistoryPageState extends State<TripHistoryPage> {
  Future<List<TransportTripHistoryRow>>? _future;
  int? _loadedFor;

  @override
  void initState() {
    super.initState();
    final s = locator<ChildrenCubit>().state;
    if (s is ChildrenLoaded && s.selectedId != null) {
      _loadedFor = s.selectedId;
      _future = locator<ParentRepository>().transportTripHistory(s.selectedId!);
    }
  }

  Future<void> _refresh() async {
    final s = locator<ChildrenCubit>().state;
    if (s is! ChildrenLoaded || s.selectedId == null) return;
    setState(() {
      _loadedFor = s.selectedId;
      _future = locator<ParentRepository>().transportTripHistory(s.selectedId!);
    });
    await _future;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Trip history')),
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: FutureBuilder<List<TransportTripHistoryRow>>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState != ConnectionState.done) {
              return ListView(children: const [
                SizedBox(height: 120),
                Center(child: CircularProgressIndicator()),
              ]);
            }
            final rows = snap.data ?? const <TransportTripHistoryRow>[];
            if (rows.isEmpty) {
              return ListView(children: const [
                SizedBox(height: 80),
                Center(
                  child: Padding(
                    padding: EdgeInsets.all(24),
                    child: Text(
                      'No trips logged yet.\n'
                      'Past runs appear here once the bus completes a trip.',
                      textAlign: TextAlign.center,
                      style: TextStyle(color: JaikalkiBrand.textSecondary),
                    ),
                  ),
                ),
              ]);
            }
            return ListView.separated(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
              itemCount: rows.length,
              separatorBuilder: (_, __) => const SizedBox(height: 10),
              itemBuilder: (_, i) => _TripRow(row: rows[i]),
            );
          },
        ),
      ),
    );
  }
}

class _TripRow extends StatelessWidget {
  const _TripRow({required this.row});
  final TransportTripHistoryRow row;

  String _phaseLabel(String p) {
    switch (p) {
      case 'in_progress':
        return 'LIVE';
      case 'scheduled':
        return 'SCHEDULED';
      case 'completed':
        return 'COMPLETED';
      case 'cancelled':
        return 'CANCELLED';
      default:
        return p.toUpperCase();
    }
  }

  Color _phaseTone(String p) {
    switch (p) {
      case 'in_progress':
        return JaikalkiBrand.tealDark;
      case 'completed':
        return JaikalkiBrand.teal;
      case 'cancelled':
        return const Color(0xFFD32F2F);
      default:
        return JaikalkiBrand.marigold;
    }
  }

  String _hm(String? iso) {
    if (iso == null) return '—';
    try {
      final dt = DateTime.parse(iso).toLocal();
      final h = dt.hour.toString().padLeft(2, '0');
      final m = dt.minute.toString().padLeft(2, '0');
      return '$h:$m';
    } catch (_) {
      return iso;
    }
  }

  String _boardingLabel(TripBoardingEvent e) {
    switch (e.event) {
      case 'boarded':
        return 'Boarded ${_hm(e.capturedAt)}';
      case 'deboarded':
        return 'Dropped ${_hm(e.capturedAt)}';
      case 'no_show':
        return 'No show';
      default:
        return '${e.event} ${_hm(e.capturedAt)}';
    }
  }

  @override
  Widget build(BuildContext context) {
    final tone = _phaseTone(row.phase);
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: JaikalkiBrand.warmWhite,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: tone.withOpacity(0.35)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(
                    horizontal: 8, vertical: 2),
                decoration: BoxDecoration(
                  color: tone.withOpacity(0.18),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  _phaseLabel(row.phase),
                  style: TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.w800,
                    color: tone,
                    letterSpacing: 0.4,
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  '${row.tripDate}${row.direction != null ? " · ${row.direction!.toUpperCase()}" : ""}',
                  style: const TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                    color: JaikalkiBrand.indigoDark,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            row.routeName ?? 'Route',
            style: const TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w800,
              color: JaikalkiBrand.indigoDark,
            ),
          ),
          const SizedBox(height: 6),
          Row(
            children: [
              const Icon(Icons.play_circle_outlined,
                  size: 13, color: JaikalkiBrand.textSecondary),
              const SizedBox(width: 4),
              Text(
                'Start ${_hm(row.startedAt)}',
                style: const TextStyle(
                  fontSize: 12,
                  color: JaikalkiBrand.textSecondary,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(width: 12),
              const Icon(Icons.flag_outlined,
                  size: 13, color: JaikalkiBrand.textSecondary),
              const SizedBox(width: 4),
              Text(
                'End ${_hm(row.completedAt)}',
                style: const TextStyle(
                  fontSize: 12,
                  color: JaikalkiBrand.textSecondary,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
          if (row.boardings.isNotEmpty) ...[
            const SizedBox(height: 8),
            Wrap(
              spacing: 6,
              runSpacing: 4,
              children: [
                for (final b in row.boardings)
                  Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(
                      color: b.event == 'boarded'
                          ? JaikalkiBrand.tealPale
                          : JaikalkiBrand.saffronPale,
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Text(
                      _boardingLabel(b),
                      style: const TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w700,
                        color: JaikalkiBrand.indigoDark,
                      ),
                    ),
                  ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}
