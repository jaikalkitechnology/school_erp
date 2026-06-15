import 'package:flutter/material.dart';

import '../../api/teacher_repository.dart';
import '../../core/service_locator.dart';
import '../../theme/brand.dart';

/// Pending leave applications on the teacher's sections. Approve/reject
/// inline with an optional decision note.
class LeavesPage extends StatefulWidget {
  const LeavesPage({super.key});

  @override
  State<LeavesPage> createState() => _LeavesPageState();
}

class _LeavesPageState extends State<LeavesPage> {
  late Future<List<LeaveRowForTeacher>> _future;
  bool _onlyPending = true;

  @override
  void initState() {
    super.initState();
    _future = locator<TeacherRepository>().pendingLeaves(onlyPending: _onlyPending);
  }

  Future<void> _reload() async {
    setState(() {
      _future = locator<TeacherRepository>()
          .pendingLeaves(onlyPending: _onlyPending);
    });
    await _future;
  }

  void _onDecided(LeaveRowForTeacher updated) {
    setState(() {
      _future = _future.then((rows) => rows
          .map((r) => r.id == updated.id ? updated : r)
          .where((r) => !_onlyPending || r.isPending)
          .toList());
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Leave applications'),
        actions: [
          PopupMenuButton<bool>(
            initialValue: _onlyPending,
            onSelected: (v) {
              setState(() {
                _onlyPending = v;
                _future = locator<TeacherRepository>()
                    .pendingLeaves(onlyPending: _onlyPending);
              });
            },
            itemBuilder: (_) => const [
              PopupMenuItem(value: true, child: Text('Pending only')),
              PopupMenuItem(value: false, child: Text('All recent')),
            ],
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _reload,
        child: FutureBuilder<List<LeaveRowForTeacher>>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState != ConnectionState.done) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snap.hasError) {
              return Padding(
                padding: const EdgeInsets.all(24),
                child: Text('Could not load: ${snap.error}',
                    style: const TextStyle(color: Color(0xFFD32F2F))),
              );
            }
            final rows = snap.data ?? const <LeaveRowForTeacher>[];
            if (rows.isEmpty) {
              return ListView(children: const [
                SizedBox(height: 80),
                Center(
                  child: Padding(
                    padding: EdgeInsets.all(24),
                    child: Text(
                      'No leave applications to review.',
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
              itemBuilder: (_, i) => _LeaveCard(
                row: rows[i],
                onDecided: _onDecided,
              ),
            );
          },
        ),
      ),
    );
  }
}

class _LeaveCard extends StatefulWidget {
  const _LeaveCard({required this.row, required this.onDecided});
  final LeaveRowForTeacher row;
  final void Function(LeaveRowForTeacher) onDecided;

  @override
  State<_LeaveCard> createState() => _LeaveCardState();
}

class _LeaveCardState extends State<_LeaveCard> {
  bool _saving = false;
  String? _error;
  String _note = '';

  Future<void> _decide(String status) async {
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      final updated = await locator<TeacherRepository>().decideLeave(
        leaveId: widget.row.id,
        status: status,
        note: _note.trim().isEmpty ? null : _note.trim(),
      );
      widget.onDecided(updated);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Leave $status')),
      );
    } catch (e) {
      setState(() => _error = 'Action failed: $e');
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Color _toneFor(String status) {
    switch (status) {
      case 'approved':
        return JaikalkiBrand.teal;
      case 'rejected':
        return const Color(0xFFD32F2F);
      default:
        return JaikalkiBrand.marigold;
    }
  }

  @override
  Widget build(BuildContext context) {
    final r = widget.row;
    final tone = _toneFor(r.status);
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: JaikalkiBrand.warmWhite,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: tone.withOpacity(0.4)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  r.studentName ?? 'Student #${r.studentId}',
                  style: const TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.w700,
                    color: JaikalkiBrand.indigoDark,
                  ),
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(
                    horizontal: 8, vertical: 2),
                decoration: BoxDecoration(
                  color: tone.withOpacity(0.18),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  r.status.toUpperCase(),
                  style: TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.w800,
                    color: tone,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          Text(
            '${r.startDate} → ${r.endDate}',
            style: const TextStyle(
              fontSize: 12,
              color: JaikalkiBrand.textSecondary,
              fontWeight: FontWeight.w600,
            ),
          ),
          if (r.reason.isNotEmpty) ...[
            const SizedBox(height: 6),
            Text(r.reason, style: const TextStyle(fontSize: 13, height: 1.4)),
          ],
          if (r.isPending) ...[
            const SizedBox(height: 10),
            TextField(
              onChanged: (v) => _note = v,
              decoration: InputDecoration(
                hintText: 'Decision note (optional)',
                isDense: true,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                ),
              ),
            ),
            if (_error != null)
              Padding(
                padding: const EdgeInsets.only(top: 6),
                child: Text(_error!,
                    style: const TextStyle(
                        fontSize: 12, color: Color(0xFFD32F2F))),
              ),
            const SizedBox(height: 10),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: _saving ? null : () => _decide('rejected'),
                    icon: const Icon(Icons.close, size: 16),
                    label: const Text('Reject'),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: const Color(0xFFD32F2F),
                      side: const BorderSide(color: Color(0xFFD32F2F)),
                      padding: const EdgeInsets.symmetric(vertical: 10),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(10),
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: _saving ? null : () => _decide('approved'),
                    icon: const Icon(Icons.check, size: 16),
                    label: const Text('Approve'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: JaikalkiBrand.teal,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 10),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(10),
                      ),
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
