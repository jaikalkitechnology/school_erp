import 'package:flutter/material.dart';

import '../../api/driver_repository.dart';
import '../../core/service_locator.dart';
import '../../theme/brand.dart';

/// One row per student allocated to the route. Driver taps a row to
/// toggle Boarded ↔ not-yet; long-press to mark Dropped (end of trip).
/// Today's skip list is greyed out so the bus operator knows to bypass
/// those students at their stop.
class BoardingScanPage extends StatefulWidget {
  const BoardingScanPage({
    super.key,
    required this.tripId,
    required this.routeId,
  });
  final int tripId;
  final int routeId;

  @override
  State<BoardingScanPage> createState() => _BoardingScanPageState();
}

class _BoardingScanPageState extends State<BoardingScanPage> {
  late Future<_BoardingData> _future;
  // In-process per-student status. Persisted on the backend via the
  // boardings endpoint; the local map is just an optimistic cache so
  // the row flips colour the moment the driver taps it.
  final Map<int, String> _localStatus = {};
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<_BoardingData> _load() async {
    final repo = locator<DriverRepository>();
    final results = await Future.wait([
      repo.routeAllocations(widget.routeId),
      repo.todaySkipStudentIds(widget.routeId),
    ]);
    return _BoardingData(
      allocations: results[0] as List<DriverAllocation>,
      skipStudentIds: (results[1] as List<int>).toSet(),
    );
  }

  Future<void> _mark(DriverAllocation alloc, String event) async {
    if (_busy) return;
    setState(() {
      _busy = true;
      _localStatus[alloc.studentId] = event;
    });
    try {
      await locator<DriverRepository>().recordBoarding(
        tripId: widget.tripId,
        studentId: alloc.studentId,
        stopId: alloc.pickupStopId,
        event: event,
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          duration: const Duration(milliseconds: 800),
          content: Text(
            event == 'boarded'
                ? '${alloc.studentName} marked boarded'
                : event == 'deboarded'
                    ? '${alloc.studentName} marked dropped'
                    : '${alloc.studentName} updated',
          ),
        ),
      );
    } catch (e) {
      if (mounted) {
        setState(() => _localStatus.remove(alloc.studentId));
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text("Couldn't mark: $e")),
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Boarding')),
      body: FutureBuilder<_BoardingData>(
        future: _future,
        builder: (context, snap) {
          if (snap.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snap.hasError) {
            return Padding(
              padding: const EdgeInsets.all(24),
              child: Text(
                'Could not load: ${snap.error}',
                style: const TextStyle(color: Color(0xFFD32F2F)),
              ),
            );
          }
          final data = snap.data ?? _BoardingData.empty();
          if (data.allocations.isEmpty) {
            return const Center(
              child: Padding(
                padding: EdgeInsets.all(24),
                child: Text(
                  'No students allocated to this route yet.',
                  style: TextStyle(color: JaikalkiBrand.textSecondary),
                ),
              ),
            );
          }
          return ListView.separated(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
            itemCount: data.allocations.length,
            separatorBuilder: (_, __) => const SizedBox(height: 8),
            itemBuilder: (_, i) {
              final a = data.allocations[i];
              final skipped = data.skipStudentIds.contains(a.studentId);
              final status = _localStatus[a.studentId] ?? '';
              return _AllocationRow(
                alloc: a,
                skipped: skipped,
                status: status,
                onBoarded: skipped ? null : () => _mark(a, 'boarded'),
                onDropped: skipped ? null : () => _mark(a, 'deboarded'),
              );
            },
          );
        },
      ),
    );
  }
}

class _BoardingData {
  const _BoardingData({
    required this.allocations,
    required this.skipStudentIds,
  });
  factory _BoardingData.empty() =>
      const _BoardingData(allocations: [], skipStudentIds: {});
  final List<DriverAllocation> allocations;
  final Set<int> skipStudentIds;
}

class _AllocationRow extends StatelessWidget {
  const _AllocationRow({
    required this.alloc,
    required this.skipped,
    required this.status,
    required this.onBoarded,
    required this.onDropped,
  });

  final DriverAllocation alloc;
  final bool skipped;
  final String status; // '', 'boarded', 'deboarded'
  final VoidCallback? onBoarded;
  final VoidCallback? onDropped;

  String _initials(String n) {
    final parts = n.trim().split(RegExp(r'\s+'));
    if (parts.isEmpty || parts[0].isEmpty) return '?';
    if (parts.length == 1) return parts[0][0].toUpperCase();
    return '${parts.first[0]}${parts.last[0]}'.toUpperCase();
  }

  @override
  Widget build(BuildContext context) {
    Color tone;
    String chip;
    switch (status) {
      case 'boarded':
        tone = JaikalkiBrand.teal;
        chip = 'BOARDED';
        break;
      case 'deboarded':
        tone = JaikalkiBrand.tealDark;
        chip = 'DROPPED';
        break;
      default:
        tone = skipped ? Colors.grey : JaikalkiBrand.saffron;
        chip = skipped ? 'NOT COMING' : 'PENDING';
    }
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: JaikalkiBrand.warmWhite,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: tone.withOpacity(0.4)),
      ),
      child: Row(
        children: [
          CircleAvatar(
            backgroundColor: tone.withOpacity(0.12),
            foregroundColor: tone,
            child: Text(
              _initials(alloc.studentName),
              style: const TextStyle(fontWeight: FontWeight.w800),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  alloc.studentName,
                  style: TextStyle(
                    fontWeight: FontWeight.w700,
                    color: skipped
                        ? JaikalkiBrand.textSecondary
                        : JaikalkiBrand.indigoDark,
                    decoration: skipped ? TextDecoration.lineThrough : null,
                  ),
                ),
                Container(
                  margin: const EdgeInsets.only(top: 2),
                  padding: const EdgeInsets.symmetric(
                      horizontal: 6, vertical: 1),
                  decoration: BoxDecoration(
                    color: tone.withOpacity(0.15),
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Text(
                    chip,
                    style: TextStyle(
                      fontSize: 9,
                      fontWeight: FontWeight.w800,
                      color: tone,
                      letterSpacing: 0.4,
                    ),
                  ),
                ),
              ],
            ),
          ),
          if (!skipped) ...[
            IconButton(
              tooltip: 'Mark boarded',
              onPressed: onBoarded,
              icon: const Icon(Icons.login),
              color: JaikalkiBrand.teal,
            ),
            IconButton(
              tooltip: 'Mark dropped',
              onPressed: onDropped,
              icon: const Icon(Icons.logout),
              color: JaikalkiBrand.tealDark,
            ),
          ],
        ],
      ),
    );
  }
}
